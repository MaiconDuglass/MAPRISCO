from datetime import timedelta

from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import AreaRisco, RegistroMonitoramento, Alerta, RelatoAlagamento, notificar_novo_relato
from .permissions import LeituraPublicaEscritaSomenteAdmin, RelatoPermissao
from .serializers import (
    AreaRiscoSerializer, RegistroMonitoramentoSerializer, AlertaSerializer, RelatoAlagamentoSerializer,
)


class AreaRiscoViewSet(viewsets.ModelViewSet):
    queryset = AreaRisco.objects.all()
    serializer_class = AreaRiscoSerializer
    permission_classes = [LeituraPublicaEscritaSomenteAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nome', 'bairro', 'cidade', 'descricao', 'nivel_risco']
    ordering_fields = ['nome', 'bairro', 'cidade', 'nivel_risco', 'data_criacao']
    ordering = ['-data_criacao']

    def get_queryset(self):
        # Dados da medição mais recente de cada área na mesma consulta (evita N+1 na listagem)
        ultima = RegistroMonitoramento.objects.filter(area=OuterRef('pk')).order_by('-data_hora', '-pk')
        return super().get_queryset().annotate(
            anot_ultimo_status=Subquery(ultima.values('status')[:1]),
            anot_ultimo_nivel=Subquery(ultima.values('nivel_agua')[:1]),
            anot_ultima_medicao=Subquery(ultima.values('data_hora')[:1]),
        )

    def _check_geocode_failure(self, serializer) -> bool:
        """Verifica se geocodificação falhou por endereço não encontrado."""
        # A flag é armazenada como atributo no serializer
        return getattr(serializer, '_geocode_failed', False)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Verifica falha de geocodificação ANTES de salvar
        if self._check_geocode_failure(serializer):
            return Response(
                {'detail': 'Não foi possível localizar este endereço. Confira o nome da rua e o bairro.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # Verifica falha de geocodificação ANTES de salvar
        if self._check_geocode_failure(serializer):
            return Response(
                {'detail': 'Não foi possível localizar este endereço. Confira o nome da rua e o bairro.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        self.perform_update(serializer)
        return Response(serializer.data)


class RegistroMonitoramentoViewSet(viewsets.ModelViewSet):
    queryset = RegistroMonitoramento.objects.select_related('area').all()
    serializer_class = RegistroMonitoramentoSerializer
    permission_classes = [LeituraPublicaEscritaSomenteAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['area__nome', 'area__bairro', 'status']
    ordering_fields = ['nivel_agua', 'data_hora', 'status']
    ordering = ['-data_hora']

    def get_queryset(self):
        queryset = super().get_queryset()
        # ?area=<id>: medições de uma área (histórico no mapa e filtro na tela de Monitoramento)
        area = self.request.query_params.get('area')
        if area and area.isdigit():
            queryset = queryset.filter(area_id=int(area))
        return queryset


class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.select_related('area').all()
    serializer_class = AlertaSerializer
    permission_classes = [LeituraPublicaEscritaSomenteAdmin]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['area__nome', 'mensagem', 'nivel']
    ordering_fields = ['nivel', 'data_hora', 'resolvido']
    ordering = ['-data_hora']

    @action(detail=True, methods=['post'])
    def resolver(self, request, pk=None):
        """Mark a single alert as resolved."""
        alerta = self.get_object()
        alerta.resolver()
        return Response({'status': 'resolvido', 'id': alerta.pk})


class RelatoAlagamentoViewSet(viewsets.ModelViewSet):
    """
    /api/relatos/ — relatos de alagamento enviados pelos moradores.

    O que cada perfil vê:
    - visitante: só relatos aprovados;
    - usuário comum: aprovados + os seus próprios (qualquer status);
    - administrador: todos.
    Filtros: ?status=pendente|aprovado|rejeitado, ?dias=7 (últimos N dias), ?meus=1, ?area=<id>.
    Apagar (DELETE): só administrador, em qualquer status.
    """

    serializer_class = RelatoAlagamentoSerializer
    permission_classes = [RelatoPermissao]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nome', 'bairro', 'descricao']
    ordering_fields = ['data_hora', 'status', 'bairro']
    ordering = ['-data_hora']
    # Sem PATCH/PUT: ajustes finos são feitos pelo admin do Django
    http_method_names = ['get', 'post', 'delete', 'head', 'options']

    LIMITE_POR_DIA = 5

    def get_queryset(self):
        queryset = RelatoAlagamento.objects.select_related('autor', 'area', 'analisado_por')
        user = self.request.user
        if not (user.is_authenticated and user.is_staff):
            visiveis = Q(status='aprovado')
            if user.is_authenticated:
                visiveis |= Q(autor=user)
            queryset = queryset.filter(visiveis)

        params = self.request.query_params
        status_param = params.get('status')
        if status_param in dict(RelatoAlagamento.STATUS_CHOICES):
            queryset = queryset.filter(status=status_param)
        dias = params.get('dias')
        if dias and dias.isdigit():
            queryset = queryset.filter(data_hora__gte=timezone.now() - timedelta(days=int(dias)))
        if params.get('meus') and user.is_authenticated:
            queryset = queryset.filter(autor=user)
        # ?area=<id>: relatos vinculados a uma área (ex.: aviso ao apagar a área no mapa)
        area = params.get('area')
        if area and area.isdigit():
            queryset = queryset.filter(area_id=int(area))
        return queryset

    def create(self, request, *args, **kwargs):
        # Limite de relatos por usuário, verificado antes de qualquer busca de endereço
        ultimas_24h = RelatoAlagamento.objects.filter(
            autor=request.user, data_hora__gte=timezone.now() - timedelta(hours=24)
        ).count()
        if ultimas_24h >= self.LIMITE_POR_DIA:
            raise Throttled(detail=(
                f'Você já enviou {self.LIMITE_POR_DIA} relatos nas últimas 24 horas. '
                'Obrigado pela colaboração! Tente novamente mais tarde.'
            ))
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        # O autor é sempre quem está logado (ignora qualquer "autor" enviado)
        relato = serializer.save(autor=self.request.user, status='pendente')
        transaction.on_commit(lambda: notificar_novo_relato(relato))

    def _relato_pendente(self):
        relato = self.get_object()
        if relato.status != 'pendente':
            raise ValidationError({'detail': 'Este relato já foi analisado.'})
        return relato

    @action(detail=True, methods=['post'])
    def aprovar(self, request, pk=None):
        """
        Aprova o relato. Corpo: {"area": <id>} para vincular a uma área existente
        ou {"criar_area": true, "nivel_risco": "alto"|"medio"|"baixo"} para criar uma área nova.
        Não cria medição nem alerta: o nível informado pelo morador é só uma estimativa.
        """
        relato = self._relato_pendente()
        area_id = request.data.get('area')
        criar_area = str(request.data.get('criar_area', '')).lower() in ('true', '1', 'on')

        if bool(area_id) == criar_area:
            raise ValidationError({'detail': 'Escolha vincular a uma área existente ou criar uma área nova.'})

        with transaction.atomic():
            if criar_area:
                nivel_risco = request.data.get('nivel_risco')
                if nivel_risco not in dict(AreaRisco.NIVEL_RISCO_CHOICES):
                    raise ValidationError({'nivel_risco': 'Escolha o nível de risco: alto, médio ou baixo.'})
                if AreaRisco.objects.filter(nome__iexact=relato.nome, bairro__iexact=relato.bairro,
                                            cidade__iexact=relato.cidade).exists():
                    raise ValidationError({'detail': 'Já existe uma área com esta rua e bairro. Vincule o relato a ela.'})
                descricao = f'Criada a partir de relato de morador em {timezone.localtime(relato.data_hora):%d/%m/%Y}.'
                if relato.descricao:
                    descricao += f' {relato.descricao}'
                area = AreaRisco.objects.create(
                    nome=relato.nome, bairro=relato.bairro, cidade=relato.cidade,
                    latitude=relato.latitude, longitude=relato.longitude,
                    nivel_risco=nivel_risco, descricao=descricao,
                    foto=relato.foto.name if relato.foto else None,
                )
            else:
                try:
                    area = AreaRisco.objects.get(pk=int(area_id))
                except (AreaRisco.DoesNotExist, TypeError, ValueError):
                    raise ValidationError({'area': 'Área de risco não encontrada.'})

            relato.status = 'aprovado'
            relato.area = area
            relato.analisado_por = request.user
            relato.analisado_em = timezone.now()
            relato.motivo_rejeicao = ''
            relato.save()

        return Response(self.get_serializer(relato).data)

    @action(detail=True, methods=['post'])
    def rejeitar(self, request, pk=None):
        """Rejeita o relato. Corpo: {"motivo": "..."} (obrigatório; o morador vê o motivo)."""
        relato = self._relato_pendente()
        motivo = (request.data.get('motivo') or '').strip()
        if not motivo:
            raise ValidationError({'motivo': 'Informe o motivo da rejeição.'})
        relato.status = 'rejeitado'
        relato.motivo_rejeicao = motivo
        relato.analisado_por = request.user
        relato.analisado_em = timezone.now()
        relato.save()
        return Response(self.get_serializer(relato).data)

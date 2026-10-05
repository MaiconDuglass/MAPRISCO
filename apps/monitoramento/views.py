from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import AreaRisco, RegistroMonitoramento, Alerta
from .permissions import CidadaoCadastraAdminGerencia, SomenteAdminAltera
from .serializers import AreaRiscoSerializer, RegistroMonitoramentoSerializer, AlertaSerializer


class AreaRiscoViewSet(viewsets.ModelViewSet):
    queryset = AreaRisco.objects.all()
    serializer_class = AreaRiscoSerializer
    permission_classes = [CidadaoCadastraAdminGerencia]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nome', 'bairro', 'cidade', 'descricao', 'nivel_risco']
    ordering_fields = ['nome', 'bairro', 'cidade', 'nivel_risco', 'data_criacao']
    ordering = ['-data_criacao']

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
    permission_classes = [CidadaoCadastraAdminGerencia]
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
    permission_classes = [SomenteAdminAltera]
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
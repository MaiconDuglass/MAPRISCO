"""
Cria 3 relatos de alagamento de demonstração (simulados), um de cada status:

- pendente:  aguardando análise (aparece na página Relatos do administrador);
- aprovado:  vinculado a uma área real (aparece no mapa por 7 dias);
- rejeitado: com motivo (o morador vê o motivo em "Meus relatos").

Todos têm a descrição iniciada por "Relato simulado para demonstração", para não
serem confundidos com relatos reais. Rodar de novo não duplica: os relatos que já
existem são mantidos; o aprovado volta a ter a data de agora, para reaparecer no mapa.

Se existir o usuário demo (criar_usuario_demo), ele vira o autor dos relatos.
Não envia e-mails.

Uso:
    python manage.py cadastrar_areas_reais   # antes, se as áreas reais ainda não existirem
    python manage.py relatos_demo
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.monitoramento.models import AreaRisco, RelatoAlagamento

from .cadastrar_areas_reais import AREAS_REAIS
from .criar_usuario_demo import EMAIL_DEMO

MARCA_SIMULADO = 'Relato simulado para demonstração.'

RELATOS_DEMO = [
    {
        'nome': 'Rua Sol Poente',
        'bairro': 'Primavera',
        'latitude': Decimal('-6.071500'),
        'longitude': Decimal('-49.905800'),
        'nivel_estimado': 'tornozelo',
        'descricao': f'{MARCA_SIMULADO} Água cobrindo a calçada depois da chuva da tarde.',
        'status': 'pendente',
    },
    {
        'nome': 'Rua Beira Rio',
        'bairro': 'Liberdade',
        'latitude': Decimal('-6.080600'),
        'longitude': Decimal('-49.909900'),
        'nivel_estimado': 'joelho',
        'descricao': f'{MARCA_SIMULADO} Rua tomada pela água perto da margem do rio.',
        'status': 'aprovado',
        'area_nome': AREAS_REAIS[0]['nome'],  # Margem do Rio Parauapebas - Liberdade
    },
    {
        'nome': 'Avenida dos Ipês',
        'bairro': 'Cidade Nova',
        'latitude': Decimal('-6.067800'),
        'longitude': Decimal('-49.889200'),
        'nivel_estimado': 'rua',
        'descricao': f'{MARCA_SIMULADO} Poça grande em frente à praça.',
        'status': 'rejeitado',
        'motivo_rejeicao': 'Acúmulo de água pontual, sem risco de alagamento. Obrigado pelo aviso!',
    },
]


class Command(BaseCommand):
    help = 'Cria 3 relatos de alagamento simulados (pendente, aprovado e rejeitado), sem duplicar.'

    @transaction.atomic
    def handle(self, *args, **options):
        autor = User.objects.filter(username__iexact=EMAIL_DEMO).first()
        analista = User.objects.filter(is_staff=True, is_active=True).order_by('-is_superuser', 'pk').first()
        criados = 0

        for dados in RELATOS_DEMO:
            dados = dict(dados)
            area_nome = dados.pop('area_nome', None)
            area = None
            if area_nome:
                area = AreaRisco.objects.filter(nome=area_nome).first()
                if area is None:
                    self.stdout.write(self.style.WARNING(
                        f'Área "{area_nome}" não encontrada: rode "python manage.py cadastrar_areas_reais" '
                        f'antes. O relato aprovado não foi criado.'
                    ))
                    continue

            existente = RelatoAlagamento.objects.filter(
                nome=dados['nome'], bairro=dados['bairro'], descricao__startswith=MARCA_SIMULADO
            ).first()
            if existente:
                if existente.status == 'aprovado':
                    # A camada do mapa mostra só os últimos 7 dias: renova a data da demonstração
                    RelatoAlagamento.objects.filter(pk=existente.pk).update(data_hora=timezone.now())
                continue

            relato = RelatoAlagamento.objects.create(autor=autor, area=area, **dados)
            if relato.status != 'pendente':
                relato.analisado_por = analista
                relato.analisado_em = timezone.now()
                relato.save(update_fields=['analisado_por', 'analisado_em'])
            criados += 1

        total = RelatoAlagamento.objects.filter(descricao__startswith=MARCA_SIMULADO).count()
        self.stdout.write(self.style.SUCCESS(
            f'{criados} relato(s) simulado(s) criado(s). Total de relatos simulados: {total}.'
        ))

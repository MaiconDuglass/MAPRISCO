"""
Cadastra áreas reais de risco de alagamento em Parauapebas-PA.

Bairros citados pela imprensa local como atingidos pelas cheias do rio
Parauapebas e de igarapés (DOL, 30/12/2021; Diário do Pará, 06/03/2025).
Coordenadas: centro aproximado de cada bairro no OpenStreetMap (Nominatim).

Uso:
    python manage.py cadastrar_areas_reais
    python manage.py cadastrar_areas_reais --limpar-exemplos   # remove as áreas fictícias antigas
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.monitoramento.models import AreaRisco

AREAS_EXEMPLO = [
    'Bacia do Rio Itacaiúnas',
    'Área Urbana Centro',
    'Vale do Rio Parauapebas',
    'Região de Marabá (proximidade)',
    'Reserva Ambiental Sul',
    'Setor Industrial',
]

AREAS_REAIS = [
    {
        'nome': 'Margem do Rio Parauapebas - Liberdade',
        'bairro': 'Liberdade',
        'latitude': Decimal('-6.081236'),
        'longitude': Decimal('-49.910355'),
        'nivel_risco': 'alto',
        'descricao': (
            'Bairro às margens do rio Parauapebas, um dos mais atingidos nas cheias '
            'de dez/2021 e foco das vistorias da Defesa Civil no alerta de mar/2025.'
        ),
    },
    {
        'nome': 'Margem do Rio Parauapebas - Primavera',
        'bairro': 'Primavera',
        'latitude': Decimal('-6.061735'),
        'longitude': Decimal('-49.910218'),
        'nivel_risco': 'alto',
        'descricao': (
            'Bairro ribeirinho com casas atingidas pela subida do rio Parauapebas '
            'nas cheias de 2021 e de 2025.'
        ),
    },
    {
        'nome': 'Margem do Rio Parauapebas - União',
        'bairro': 'União',
        'latitude': Decimal('-6.070038'),
        'longitude': Decimal('-49.906486'),
        'nivel_risco': 'alto',
        'descricao': (
            'Bairro próximo ao rio Parauapebas, citado entre os mais afetados '
            'pelas cheias de 2021 e de 2025.'
        ),
    },
    {
        'nome': 'Igarapé Ilha do Coco - Novo Brasil',
        'bairro': 'Novo Brasil',
        'latitude': Decimal('-6.090191'),
        'longitude': Decimal('-49.867560'),
        'nivel_risco': 'medio',
        'descricao': (
            'Alagamento causado pelo transbordamento do igarapé Ilha do Coco, '
            'que atingiu residências em mar/2025.'
        ),
    },
]


class Command(BaseCommand):
    help = 'Cadastra áreas reais de risco de alagamento em Parauapebas-PA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpar-exemplos', action='store_true',
            help='Remove as 6 áreas fictícias do populate_parauapebas (e seus registros/alertas).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['limpar_exemplos']:
            removidas, _ = AreaRisco.objects.filter(nome__in=AREAS_EXEMPLO).delete()
            self.stdout.write(f'Removidos {removidas} objetos das áreas de exemplo.')

        criadas = atualizadas = 0
        for dados in AREAS_REAIS:
            dados = {**dados, 'cidade': 'Parauapebas'}
            _, created = AreaRisco.objects.update_or_create(
                nome=dados['nome'], bairro=dados['bairro'], cidade='Parauapebas',
                defaults=dados,
            )
            if created:
                criadas += 1
            else:
                atualizadas += 1

        self.stdout.write(self.style.SUCCESS(
            f'OK: {criadas} áreas reais criadas, {atualizadas} atualizadas.'
        ))

from django.core.management.base import BaseCommand
from apps.monitoramento.models import AreaRisco

class Command(BaseCommand):
    help = 'Popula dados de exemplo de áreas de risco em Parauapebas, Pará'

    def handle(self, *args, **options):
        # Dados de exemplo para Parauapebas, PA
        areas_data = [
            {
                'nome': 'Bacia do Rio Itacaiúnas',
                'latitude': '-6.0645',
                'longitude': '-49.9005',
                'nivel_risco': 'alto',
                'descricao': 'Área com histórico de enchentes. Monitora principais tributários que drenam para a região.'
            },
            {
                'nome': 'Área Urbana Centro',
                'latitude': '-6.0630',
                'longitude': '-49.8995',
                'nivel_risco': 'medio',
                'descricao': 'Região central de Parauapebas com população densa. Requer atenção especial em períodos chuvosos.'
            },
            {
                'nome': 'Vale do Rio Parauapebas',
                'latitude': '-6.0720',
                'longitude': '-49.8900',
                'nivel_risco': 'alto',
                'descricao': 'Zona de confluência próxima a operações de mineração. Sensível a variações hídricas.'
            },
            {
                'nome': 'Região de Marabá (proximidade)',
                'latitude': '-6.0550',
                'longitude': '-49.9100',
                'nivel_risco': 'medio',
                'descricao': 'Área periférica em transição entre Parauapebas e Marabá.'
            },
            {
                'nome': 'Reserva Ambiental Sul',
                'latitude': '-6.1000',
                'longitude': '-49.9000',
                'nivel_risco': 'baixo',
                'descricao': 'Área de preservação ambiental com cobertura vegetal preservada.'
            },
            {
                'nome': 'Setor Industrial',
                'latitude': '-6.0700',
                'longitude': '-49.8850',
                'nivel_risco': 'alto',
                'descricao': 'Zona com atividades de mineração e indústria. Monitoramento contínuo recomendado.'
            },
        ]

        # Criar áreas no banco de dados (sem apagar dados existentes)
        criadas = 0
        for area in areas_data:
            _, created = AreaRisco.objects.get_or_create(
                nome=area['nome'],
                defaults=area,
            )
            if created:
                criadas += 1

        self.stdout.write(self.style.SUCCESS(f'OK: {criadas} areas de risco criadas (existentes mantidas).'))

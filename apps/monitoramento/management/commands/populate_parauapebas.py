"""
Popula o banco com as áreas de risco de Parauapebas-PA.

Mantido por compatibilidade: antes criava 6 áreas fictícias; agora apenas
chama o comando cadastrar_areas_reais, que cadastra os bairros reais
atingidos pelas cheias. Não apaga dados existentes.

Uso:
    python manage.py populate_parauapebas
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Cadastra as áreas reais de risco de Parauapebas-PA (atalho para cadastrar_areas_reais)'

    def handle(self, *args, **options):
        call_command('cadastrar_areas_reais', stdout=self.stdout, stderr=self.stderr)

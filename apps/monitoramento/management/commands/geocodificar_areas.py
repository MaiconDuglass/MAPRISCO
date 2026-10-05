"""
Comando de manutenção para geocodificar áreas sem coordenadas.

Uso:
    python manage.py geocodificar_areas
    python manage.py geocodificar_areas --dry-run
    python manage.py geocodificar_areas --limit 10
"""
import logging
import time

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.monitoramento.geocoding import geocodificar_endereco
from apps.monitoramento.models import AreaRisco

logger = logging.getLogger('apps.monitoramento.geocodificar_areas')


class Command(BaseCommand):
    help = 'Geocodifica áreas de risco que não possuem latitude/longitude.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Apenas simula, não salva no banco.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=0,
            help='Limita o número de áreas a processar (0 = sem limite).',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Re-geocodifica até áreas que já têm coordenadas.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        limit = options['limit']
        force = options['force']

        queryset = AreaRisco.objects.all()

        if not force:
            queryset = queryset.filter(latitude__isnull=True) | queryset.filter(longitude__isnull=True)

        queryset = queryset.order_by('id')

        if limit > 0:
            queryset = queryset[:limit]

        total = queryset.count()
        self.stdout.write(f'Encontradas {total} área(s) para geocodificar.')

        if dry_run:
            self.stdout.write(self.style.WARNING('Modo DRY-RUN: nenhuma alteração será salva.'))

        atualizadas = 0
        falharam = 0
        ja_tinha = 0

        for i, area in enumerate(queryset, 1):
            self.stdout.write(f'[{i}/{total}] Processando: {area.nome} ({area.bairro}, {area.cidade})... ', ending='')

            if not force and area.latitude is not None and area.longitude is not None:
                self.stdout.write(self.style.NOTICE('já possui coordenadas'))
                ja_tinha += 1
                continue

            coords = geocodificar_endereco(area.nome, area.bairro, area.cidade)

            if coords:
                lat, lng = coords
                self.stdout.write(self.style.SUCCESS(f'encontrado -> {lat}, {lng}'))

                if not dry_run:
                    area.latitude = lat
                    area.longitude = lng
                    area.save(update_fields=['latitude', 'longitude'])

                atualizadas += 1
            else:
                self.stdout.write(self.style.ERROR('não encontrado'))
                falharam += 1

            # Respeita rate limit do Nominatim (1 req/s)
            if i < total:
                time.sleep(1.1)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('--- Resumo ---'))
        self.stdout.write(f'Atualizadas: {atualizadas}')
        self.stdout.write(f'Já possuíam: {ja_tinha}')
        self.stdout.write(self.style.ERROR(f'Falharam: {falharam}'))
        self.stdout.write(f'Total: {total}')

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY-RUN: nenhuma alteração foi salva.'))
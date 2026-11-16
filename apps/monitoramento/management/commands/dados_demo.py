"""
Gera medições de nível de água de demonstração para as áreas reais.

Cria uma série de medições nos últimos 7 dias para cada área real
(Liberdade, Primavera, União e Novo Brasil), com valores normais (< 50 cm),
em alerta (50 a 79 cm) e críticos (>= 80 cm), e os alertas correspondentes.
Assim o dashboard, os gráficos e a central de alertas não ficam vazios.

Não duplica dados: áreas que já têm alguma medição são ignoradas.
Não envia e-mails (as medições são gravadas direto, sem passar pelo save()).

Com --recriar, restaura as 4 áreas reais ao estado da demonstração:
- devolve nome, bairro, cidade, coordenadas, risco e descrição de AREAS_REAIS
  (recria a área se foi apagada; se foi renomeada, acha pelas coordenadas e corrige);
- apaga as medições e os alertas SÓ dessas 4 áreas e gera a série de novo.
Outras áreas e os relatos de moradores não são alterados. Pede confirmação
no terminal (use --sim para pular).

Uso:
    python manage.py cadastrar_areas_reais   # antes, se as áreas ainda não existirem
    python manage.py dados_demo
    python manage.py dados_demo --recriar    # restaura as 4 áreas reais
"""
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.monitoramento.models import (
    NIVEL_ALERTA_CM, NIVEL_CRITICO_CM, Alerta, AreaRisco, RegistroMonitoramento, formatar_cm,
)

from .cadastrar_areas_reais import AREAS_REAIS

# (horas atrás, nível em cm) para cada área, da mais antiga para a mais recente
SERIES_DEMO = {
    'Margem do Rio Parauapebas - Liberdade': [
        (150, '35.00'), (126, '48.50'), (102, '62.00'), (78, '81.40'),
        (54, '70.20'), (30, '58.00'), (3, '86.30'),
    ],
    'Margem do Rio Parauapebas - Primavera': [
        (148, '28.00'), (124, '33.50'), (100, '45.00'), (76, '57.30'),
        (52, '64.10'), (28, '52.00'), (5, '61.20'),
    ],
    'Margem do Rio Parauapebas - União': [
        (146, '22.00'), (98, '30.40'), (50, '41.00'), (26, '38.20'), (4, '35.00'),
    ],
    'Igarapé Ilha do Coco - Novo Brasil': [
        (144, '18.00'), (120, '25.30'), (72, '52.40'), (48, '47.00'),
        (24, '31.00'), (6, '27.50'),
    ],
}


def classificar(nivel):
    """Mesma regra do RegistroMonitoramento.save()."""
    if nivel >= NIVEL_CRITICO_CM:
        return 'critico'
    if nivel >= NIVEL_ALERTA_CM:
        return 'alerta'
    return 'normal'


class Command(BaseCommand):
    help = 'Gera medições e alertas de demonstração para as áreas reais (sem duplicar)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--recriar', action='store_true',
            help='Restaura as 4 áreas reais: cadastro original e série de medições/alertas refeita do zero.',
        )
        parser.add_argument('--sim', action='store_true', help='Não pede confirmação (use com --recriar).')

    def handle(self, *args, **options):
        if options['recriar']:
            if not options['sim']:
                resposta = input(
                    'Isto apaga as medições e os alertas das 4 áreas reais e gera a série de demonstração de novo. '
                    'Outras áreas e os relatos não são alterados. Continuar? [s/N] '
                )
                if resposta.strip().lower() not in ('s', 'sim'):
                    self.stdout.write('Cancelado. Nada foi alterado.')
                    return
            self.recriar()
        else:
            self.gerar()

    @transaction.atomic
    def recriar(self):
        # Área real renomeada: reconhece pelas coordenadas originais e devolve o nome (não duplica)
        for dados in AREAS_REAIS:
            if AreaRisco.objects.filter(nome=dados['nome'], bairro=dados['bairro'], cidade='Parauapebas').exists():
                continue
            renomeada = AreaRisco.objects.filter(
                latitude=dados['latitude'], longitude=dados['longitude'],
            ).exclude(nome__in=[a['nome'] for a in AREAS_REAIS]).first()
            if renomeada:
                self.stdout.write(f'Área renomeada corrigida: "{renomeada.nome}" -> "{dados["nome"]}"')
                renomeada.nome, renomeada.bairro, renomeada.cidade = dados['nome'], dados['bairro'], 'Parauapebas'
                renomeada.save(update_fields=['nome', 'bairro', 'cidade'])

        # Cadastro original (recria as apagadas, corrige coordenadas, risco e descrição)
        saida = StringIO()
        call_command('cadastrar_areas_reais', stdout=saida)
        self.stdout.write(saida.getvalue().strip())

        nomes = [a['nome'] for a in AREAS_REAIS]
        areas = AreaRisco.objects.filter(nome__in=nomes, cidade='Parauapebas')
        registros, _ = RegistroMonitoramento.objects.filter(area__in=areas).delete()
        alertas, _ = Alerta.objects.filter(area__in=areas).delete()
        self.stdout.write(f'Apagados das áreas reais: {registros} medições e {alertas} alertas.')
        self.gerar()

    @transaction.atomic
    def gerar(self):
        agora = timezone.now()
        nomes = [a['nome'] for a in AREAS_REAIS]
        areas = {a.nome: a for a in AreaRisco.objects.filter(nome__in=nomes, cidade='Parauapebas')}

        if not areas:
            self.stdout.write(self.style.WARNING(
                'Nenhuma área real encontrada. Rode antes: python manage.py cadastrar_areas_reais'
            ))
            return

        total_registros = total_alertas = 0
        for nome, serie in SERIES_DEMO.items():
            area = areas.get(nome)
            if area is None:
                self.stdout.write(self.style.WARNING(f'Área não encontrada, ignorada: {nome}'))
                continue
            if area.registros.exists():
                self.stdout.write(f'Já possui medições, ignorada: {nome}')
                continue

            status_anterior = None
            criticos = []
            for horas, valor in serie:
                nivel = Decimal(valor)
                status = classificar(nivel)
                momento = agora - timedelta(hours=horas)
                registro = RegistroMonitoramento(area=area, nivel_agua=nivel, status=status)
                # bulk_create não chama save(): evita e-mails; o alerta é criado abaixo
                RegistroMonitoramento.objects.bulk_create([registro])
                # data_hora é auto_now_add, então a data passada é aplicada depois
                RegistroMonitoramento.objects.filter(pk=registro.pk).update(data_hora=momento)
                total_registros += 1

                if status == 'critico' and status_anterior != 'critico':
                    criticos.append((nivel, momento))
                status_anterior = status

            # Um alerta por escalada para o estado crítico; só o mais recente fica em aberto
            for i, (nivel, momento) in enumerate(criticos):
                alerta = Alerta.objects.create(
                    area=area,
                    mensagem=f'Nível de água crítico detectado: {formatar_cm(nivel)} na área {area.nome}.',
                    nivel='critico',
                    resolvido=i < len(criticos) - 1,
                )
                Alerta.objects.filter(pk=alerta.pk).update(data_hora=momento)
                total_alertas += 1

        self.stdout.write(self.style.SUCCESS(
            f'OK: {total_registros} medições e {total_alertas} alertas de demonstração criados.'
        ))

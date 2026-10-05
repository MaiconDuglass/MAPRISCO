"""
Modelos do app monitoramento.

Áreas de risco, registros de nível de água e alertas gerados automaticamente.
"""

import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import models, transaction

logger = logging.getLogger('apps.monitoramento')

# Limites de classificação do nível de água (em centímetros)
NIVEL_CRITICO_CM = 80
NIVEL_ALERTA_CM = 50


def formatar_cm(valor):
    """Formata um número no padrão brasileiro: 85.5 -> '85,50 cm'."""
    return f'{valor:.2f}'.replace('.', ',') + ' cm'


class AreaRisco(models.Model):
    """Área de risco monitorada, com localização e classificação de risco."""

    NIVEL_RISCO_CHOICES = [
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('alto', 'Alto'),
    ]

    nome = models.CharField('rua / endereço', max_length=100, help_text='Nome da rua ou endereço da área de risco.')
    bairro = models.CharField('bairro', max_length=100, blank=True, help_text='Bairro onde a área fica.')
    cidade = models.CharField('cidade', max_length=100, default='Parauapebas', help_text='Cidade onde a área fica.')
    latitude = models.DecimalField('latitude', max_digits=9, decimal_places=6, blank=True, null=True,
                                   help_text='Latitude (preenchida pela busca de endereço ou pelo clique no mapa).')
    longitude = models.DecimalField('longitude', max_digits=9, decimal_places=6, blank=True, null=True,
                                    help_text='Longitude (preenchida pela busca de endereço ou pelo clique no mapa).')
    nivel_risco = models.CharField(
        'nível de risco',
        max_length=10,
        choices=NIVEL_RISCO_CHOICES,
        default='baixo',
        help_text='Classificação de risco da área.'
    )
    descricao = models.TextField('descrição', blank=True, help_text='Descrição opcional da área.')
    foto = models.ImageField('foto', upload_to='areas/', blank=True, null=True, help_text='Foto opcional da área (até 5 MB).')
    data_criacao = models.DateTimeField('data de cadastro', auto_now_add=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = 'Área de Risco'
        verbose_name_plural = 'Áreas de Risco'
        ordering = ['-data_criacao']
        constraints = [
            models.UniqueConstraint(fields=['nome', 'bairro', 'cidade'], name='unique_area_per_location')
        ]


class RegistroMonitoramento(models.Model):
    """Medição do nível de água. Classifica o status e gera alertas automaticamente."""

    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('alerta', 'Alerta'),
        ('critico', 'Crítico'),
    ]

    area = models.ForeignKey(
        AreaRisco,
        on_delete=models.CASCADE,
        related_name='registros',
        verbose_name='área',
        help_text='Área de risco monitorada.'
    )
    nivel_agua = models.DecimalField(
        'nível de água (cm)',
        max_digits=5,
        decimal_places=2,
        help_text='Nível de água medido, em centímetros.'
    )
    status = models.CharField(
        'status',
        max_length=10,
        choices=STATUS_CHOICES,
        default='normal',
        help_text=f'Calculado automaticamente: a partir de {NIVEL_CRITICO_CM} cm = Crítico, '
                  f'a partir de {NIVEL_ALERTA_CM} cm = Alerta.'
    )
    data_hora = models.DateTimeField('data e hora', auto_now_add=True)

    def save(self, *args, **kwargs):
        """Classifica o status automaticamente e gera um alerta ao entrar no estado crítico."""
        with transaction.atomic():
            # Status anterior, para gerar um único alerta por escalada
            previous_status = None
            if self.pk:
                previous_status = RegistroMonitoramento.objects.select_for_update().filter(pk=self.pk).values_list('status', flat=True).first()

            # Classificação automática pelo nível de água
            if self.nivel_agua is not None:
                if self.nivel_agua >= NIVEL_CRITICO_CM:
                    self.status = 'critico'
                elif self.nivel_agua >= NIVEL_ALERTA_CM:
                    self.status = 'alerta'
                else:
                    self.status = 'normal'

            super().save(*args, **kwargs)

            # Também gera alerta se o status for definido como crítico manualmente (admin/API)
            should_create_alert = (
                self.status == 'critico' and previous_status != 'critico'
            ) or (
                self.nivel_agua is not None and self.nivel_agua >= NIVEL_CRITICO_CM and previous_status != 'critico'
            )

            if should_create_alert:
                alerta = Alerta.objects.create(
                    area=self.area,
                    mensagem=f'Nível de água crítico detectado: {formatar_cm(self.nivel_agua)} na área {self.area.nome}.',
                    nivel='critico'
                )
                logger.info('Alerta criado para a área %s (nível %s)', self.area.nome, self.nivel_agua)
                # E-mail só depois que a transação for confirmada no banco
                transaction.on_commit(lambda: notificar_alerta_critico(alerta))

    def __str__(self):
        return f'Registro {self.area.nome} - {self.data_hora}'

    class Meta:
        verbose_name = 'Registro de Monitoramento'
        verbose_name_plural = 'Registros de Monitoramento'
        ordering = ['-data_hora']


class Alerta(models.Model):
    """Alerta gerado a partir das medições (ou criado por um administrador)."""

    NIVEL_CHOICES = [
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('alto', 'Alto'),
        ('critico', 'Crítico'),
    ]

    area = models.ForeignKey(
        AreaRisco,
        on_delete=models.CASCADE,
        related_name='alertas',
        verbose_name='área',
        help_text='Área de risco que gerou o alerta.'
    )
    mensagem = models.TextField('mensagem', help_text='Texto do alerta.')
    nivel = models.CharField(
        'nível',
        max_length=10,
        choices=NIVEL_CHOICES,
        default='baixo',
        help_text='Gravidade do alerta.'
    )
    resolvido = models.BooleanField('resolvido', default=False, help_text='Marque quando o alerta já foi tratado.')
    data_hora = models.DateTimeField('data e hora', auto_now_add=True)

    def resolver(self):
        """Marca o alerta como resolvido."""
        self.resolvido = True
        self.save(update_fields=['resolvido'])

    def __str__(self):
        return f'Alerta {self.area.nome} - {self.get_nivel_display()}'

    class Meta:
        verbose_name = 'Alerta'
        verbose_name_plural = 'Alertas'
        ordering = ['-data_hora']


def notificar_alerta_critico(alerta):
    """Envia e-mail para os administradores (Defesa Civil) que têm e-mail cadastrado."""
    destinatarios = list(
        get_user_model().objects.filter(is_staff=True, is_active=True)
        .exclude(email='').values_list('email', flat=True)
    )
    if not destinatarios:
        return
    try:
        send_mail(
            subject=f'[MAPRISCO] Alerta crítico: {alerta.area.nome}',
            message=(
                f'{alerta.mensagem}\n\n'
                f'Área: {alerta.area.nome}'
                f'{" - " + alerta.area.bairro if alerta.area.bairro else ""} ({alerta.area.cidade})\n\n'
                'Acesse a Central de Alertas do MAPRISCO para acompanhar e resolver o alerta.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=destinatarios,
            fail_silently=False,
        )
    except Exception:
        # Falha no e-mail nunca pode impedir o registro da medição
        logger.exception('Não foi possível enviar o e-mail do alerta %s', alerta.pk)

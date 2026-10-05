"""
Models for the monitoramento app.

This app handles risk area monitoring, water level records, and alert generation.
"""

from django.db import models, transaction
import logging

logger = logging.getLogger('apps.monitoramento')

class AreaRisco(models.Model):
    """
    Model representing a risk area for monitoring.

    Stores geographical information and risk level classification.
    Used as the main entity for monitoring activities.
    """

    # Choice options for risk levels
    NIVEL_RISCO_CHOICES = [
        ('baixo', 'Baixo'),
        ('medio', 'Médio'),
        ('alto', 'Alto'),
    ]

    nome = models.CharField(max_length=100, help_text="Name of the risk area")
    bairro = models.CharField(max_length=100, blank=True, help_text="Neighborhood where the area is located")
    cidade = models.CharField(max_length=100, default='Parauapebas', help_text="City where the area is located")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True, help_text="Longitude coordinate")
    nivel_risco = models.CharField(
        max_length=10,
        choices=NIVEL_RISCO_CHOICES,
        default='baixo',
        help_text="Risk level classification"
    )
    descricao = models.TextField(blank=True, help_text="Optional description of the area")
    foto = models.ImageField(upload_to='areas/', blank=True, null=True, help_text="Optional image of the area")
    data_criacao = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp")

    def __str__(self):
        """String representation of the risk area."""
        return self.nome

    class Meta:
        verbose_name = "Área de Risco"
        verbose_name_plural = "Áreas de Risco"
        ordering = ['-data_criacao']
        constraints = [
            models.UniqueConstraint(fields=['nome', 'bairro', 'cidade'], name='unique_area_per_location')
        ]


class RegistroMonitoramento(models.Model):
    """
    Model representing a monitoring record for water levels.

    Records water level measurements and automatically triggers alerts
    when levels exceed critical thresholds.
    """

    # Choice options for monitoring status
    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('alerta', 'Alerta'),
        ('critico', 'Crítico'),
    ]

    area = models.ForeignKey(
        AreaRisco,
        on_delete=models.CASCADE,
        related_name='registros',
        help_text="Risk area being monitored"
    )
    nivel_agua = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Water level measurement in centimeters"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='normal',
        help_text="Current monitoring status"
    )
    data_hora = models.DateTimeField(auto_now_add=True, help_text="Record timestamp")

    def save(self, *args, **kwargs):
        """Auto-classify the status and generate alerts when thresholds are crossed."""
        with transaction.atomic():
            # Retain the previous status so each escalation generates a single alert.
            previous_status = None
            if self.pk:
                previous_status = RegistroMonitoramento.objects.select_for_update().filter(pk=self.pk).values_list('status', flat=True).first()

            # Automatic classification based on the water level.
            if self.nivel_agua is not None:
                if self.nivel_agua >= 80:
                    self.status = 'critico'
                elif self.nivel_agua >= 50:
                    self.status = 'alerta'
                else:
                    self.status = 'normal'

            super().save(*args, **kwargs)

            # Also generate alert if status is manually set to 'critico' (e.g., via admin/API)
            # and previous status wasn't already 'critico'.
            should_create_alert = (
                self.status == 'critico' and previous_status != 'critico'
            ) or (
                self.nivel_agua is not None and self.nivel_agua >= 80 and previous_status != 'critico'
            )

            if should_create_alert:
                Alerta.objects.create(
                    area=self.area,
                    mensagem=f"Nível de água crítico detectado: {self.nivel_agua} cm na área {self.area.nome}.",
                    nivel='alto'
                )
                logger.info("Alerta criado para a área %s (nível %s)", self.area.nome, self.nivel_agua)

    def __str__(self):
        """String representation of the monitoring record."""
        return f"Registro {self.area.nome} - {self.data_hora}"

    class Meta:
        verbose_name = "Registro de Monitoramento"
        verbose_name_plural = "Registros de Monitoramento"
        ordering = ['-data_hora']


class Alerta(models.Model):
    """
    Model representing an alert generated from monitoring data.

    Alerts are automatically created when water levels exceed thresholds
    or manually created by system administrators.
    """

    # Choice options for alert levels
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
        help_text="Risk area that triggered the alert"
    )
    mensagem = models.TextField(help_text="Alert message content")
    nivel = models.CharField(
        max_length=10,
        choices=NIVEL_CHOICES,
        default='baixo',
        help_text="Alert severity level"
    )
    resolvido = models.BooleanField(default=False, help_text="Whether the alert has been resolved")
    data_hora = models.DateTimeField(auto_now_add=True, help_text="Alert timestamp")

    def resolver(self):
        """Mark the alert as resolved."""
        self.resolvido = True
        self.save(update_fields=['resolvido'])

    def __str__(self):
        """String representation of the alert."""
        return f"Alerta {self.area.nome} - {self.nivel}"

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-data_hora']
"""
Models for the monitoramento app.

This app handles risk area monitoring, water level records, and alert generation.
"""

from django.db import models

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
    latitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Latitude coordinate")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, help_text="Longitude coordinate")
    nivel_risco = models.CharField(
        max_length=10,
        choices=NIVEL_RISCO_CHOICES,
        default='baixo',
        help_text="Risk level classification"
    )
    descricao = models.TextField(blank=True, help_text="Optional description of the area")
    foto = models.FileField(upload_to='areas/', blank=True, null=True, help_text="Optional image or file")
    data_criacao = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp")

    def __str__(self):
        """String representation of the risk area."""
        return self.nome

    class Meta:
        verbose_name = "Área de Risco"
        verbose_name_plural = "Áreas de Risco"
        ordering = ['-data_criacao']


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
        help_text="Water level measurement in meters"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='normal',
        help_text="Current monitoring status"
    )
    data_hora = models.DateTimeField(auto_now_add=True, help_text="Record timestamp")

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
    data_hora = models.DateTimeField(auto_now_add=True, help_text="Alert timestamp")

    def __str__(self):
        """String representation of the alert."""
        return f"Alerta {self.area.nome} - {self.nivel}"

    class Meta:
        verbose_name = "Alerta"
        verbose_name_plural = "Alertas"
        ordering = ['-data_hora']
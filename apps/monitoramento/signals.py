"""
Signals for the monitoramento app.

This module contains signal handlers that automatically trigger actions
based on model events, implementing business logic for alert generation.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RegistroMonitoramento, Alerta


@receiver(post_save, sender=RegistroMonitoramento)
def criar_alerta_critico(sender, instance, created, **kwargs):
    """
    Signal handler for automatic alert creation.

    When a monitoring record is saved with water level > 80:
    1. Updates the record status to 'critico'
    2. Creates a high-level alert for the area

    This implements the core business logic for automatic risk detection.
    """
    if instance.nivel_agua > 80:
        # Update record status to critical
        instance.status = 'critico'
        instance.save(update_fields=['status'])

        # Create high-priority alert
        Alerta.objects.create(
            area=instance.area,
            mensagem=f"Nível de água crítico detectado: {instance.nivel_agua}",
            nivel='alto'
        )
from rest_framework import serializers
from .models import AreaRisco, RegistroMonitoramento, Alerta

class AreaRiscoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AreaRisco
        fields = '__all__'

class RegistroMonitoramentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroMonitoramento
        fields = '__all__'

class AlertaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alerta
        fields = '__all__'
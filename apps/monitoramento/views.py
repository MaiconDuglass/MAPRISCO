from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import AreaRisco, RegistroMonitoramento, Alerta
from .serializers import AreaRiscoSerializer, RegistroMonitoramentoSerializer, AlertaSerializer

class AreaRiscoViewSet(viewsets.ModelViewSet):
    queryset = AreaRisco.objects.all()
    serializer_class = AreaRiscoSerializer
    permission_classes = [AllowAny]  # Permite acesso público ao mapa

class RegistroMonitoramentoViewSet(viewsets.ModelViewSet):
    queryset = RegistroMonitoramento.objects.all()
    serializer_class = RegistroMonitoramentoSerializer
    permission_classes = [IsAuthenticated]

class AlertaViewSet(viewsets.ModelViewSet):
    queryset = Alerta.objects.all()
    serializer_class = AlertaSerializer
    permission_classes = [IsAuthenticated]
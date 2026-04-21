from django.contrib import admin
from .models import AreaRisco, RegistroMonitoramento, Alerta

@admin.register(AreaRisco)
class AreaRiscoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'latitude', 'longitude', 'nivel_risco', 'data_criacao')
    list_filter = ('nivel_risco', 'data_criacao')

@admin.register(RegistroMonitoramento)
class RegistroMonitoramentoAdmin(admin.ModelAdmin):
    list_display = ('area', 'nivel_agua', 'status', 'data_hora')
    list_filter = ('status', 'data_hora')

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('area', 'mensagem', 'nivel', 'data_hora')
    list_filter = ('nivel', 'data_hora')
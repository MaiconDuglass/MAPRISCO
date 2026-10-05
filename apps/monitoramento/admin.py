from django.contrib import admin

from .models import AreaRisco, RegistroMonitoramento, Alerta

admin.site.site_header = 'MAPRISCO - Administração'
admin.site.site_title = 'MAPRISCO'
admin.site.index_title = 'Gestão de áreas de risco'


@admin.register(AreaRisco)
class AreaRiscoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'bairro', 'cidade', 'nivel_risco', 'tem_localizacao', 'data_criacao')
    list_filter = ('nivel_risco', 'cidade', 'bairro')
    search_fields = ('nome', 'bairro', 'cidade', 'descricao')
    date_hierarchy = 'data_criacao'

    @admin.display(boolean=True, description='no mapa')
    def tem_localizacao(self, obj):
        return obj.latitude is not None and obj.longitude is not None


@admin.register(RegistroMonitoramento)
class RegistroMonitoramentoAdmin(admin.ModelAdmin):
    list_display = ('area', 'nivel_agua', 'status', 'data_hora')
    list_filter = ('status', 'area')
    search_fields = ('area__nome', 'area__bairro')
    readonly_fields = ('status',)  # calculado automaticamente pelo nível de água
    date_hierarchy = 'data_hora'
    list_select_related = ('area',)


@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('area', 'mensagem', 'nivel', 'resolvido', 'data_hora')
    list_filter = ('resolvido', 'nivel', 'area')
    search_fields = ('area__nome', 'mensagem')
    date_hierarchy = 'data_hora'
    list_select_related = ('area',)
    actions = ['marcar_resolvido']

    @admin.action(description='Marcar alertas selecionados como resolvidos')
    def marcar_resolvido(self, request, queryset):
        total = queryset.update(resolvido=True)
        self.message_user(request, f'{total} alerta(s) marcado(s) como resolvido(s).')

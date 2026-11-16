from django.conf import settings


def map_settings(request):
    """Provide map configuration to templates."""
    # Format with dot for JavaScript (avoid locale comma)
    lat = getattr(settings, 'MAP_CENTER_LAT', -6.064)
    lng = getattr(settings, 'MAP_CENTER_LNG', -49.9011)
    return {
        'MAP_CENTER_LAT': f'{lat:.6f}'.rstrip('0').rstrip('.'),
        'MAP_CENTER_LNG': f'{lng:.6f}'.rstrip('0').rstrip('.'),
        'MAP_DEFAULT_ZOOM': getattr(settings, 'MAP_DEFAULT_ZOOM', 12),
    }

def navbar(request):
    """Dados da barra superior: primeiro nome do usuário, alertas abertos e relatos pendentes (admin)."""
    from apps.monitoramento.models import Alerta, RelatoAlagamento

    user = getattr(request, 'user', None)
    first_name = ''
    open_alerts_count = 0
    relatos_pendentes_count = 0
    if user is not None and user.is_authenticated:
        # O sino de alertas só aparece para quem está logado
        open_alerts_count = Alerta.objects.filter(resolvido=False).count()
        if user.is_staff:
            # Contador do menu Relatos (só o administrador analisa relatos)
            relatos_pendentes_count = RelatoAlagamento.objects.filter(status='pendente').count()
        if user.first_name.strip():
            first_name = user.first_name.strip().split()[0].title()
        else:
            # Conta sem nome (ex.: criada pelo createsuperuser): usa o que vem antes do @ do e-mail
            first_name = user.username.split('@')[0].strip().capitalize() or user.username
    return {
        'user_first_name': first_name,
        'open_alerts_count': open_alerts_count,
        'relatos_pendentes_count': relatos_pendentes_count,
    }

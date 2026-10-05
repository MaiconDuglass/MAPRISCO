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
    """Dados da barra superior: primeiro nome do usuário e total de alertas abertos."""
    from apps.monitoramento.models import Alerta

    user = getattr(request, 'user', None)
    first_name = ''
    if user is not None and user.is_authenticated:
        nome = (user.first_name or user.username).strip()
        first_name = nome.split()[0].title() if nome else user.username
    return {
        'user_first_name': first_name,
        'open_alerts_count': Alerta.objects.filter(resolvido=False).count(),
    }

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
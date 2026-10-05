"""
Geocodificação usando Nominatim (OpenStreetMap).

Fornece função para converter endereço (rua, bairro, cidade) em coordenadas.
"""
import logging
import time
import urllib.parse
import urllib.request
import json
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple

from django.conf import settings

logger = logging.getLogger('apps.monitoramento.geocoding')


class GeocodingNetworkError(Exception):
    """Erro de rede/timeout ao acessar o serviço de geocodificação."""
    pass

# Constantes
NOMINATIM_URL = 'https://nominatim.openstreetmap.org/search'
DEFAULT_USER_AGENT = 'MAPRISCO-TCC/1.0 (contato@maprisco.local)'
TIMEOUT = 5  # segundos
RATE_LIMIT_DELAY = 1.1  # segundos entre requisições (Nominatim: max 1 req/s)
VIEWBOX_DELTA = 0.3  # graus ao redor do centro de Parauapebas
QUANTIZE_EXP = Decimal('0.000001')  # 6 casas decimais


def _get_user_agent() -> str:
    """Obtém User-Agent do settings ou usa padrão."""
    return getattr(settings, 'GEOCODER_USER_AGENT', DEFAULT_USER_AGENT)


def _build_viewbox() -> str:
    """Constrói viewbox string: min_lon,min_lat,max_lon,max_lat."""
    center_lat = getattr(settings, 'MAP_CENTER_LAT', -6.064)
    center_lng = getattr(settings, 'MAP_CENTER_LNG', -49.9011)
    min_lat = center_lat - VIEWBOX_DELTA
    max_lat = center_lat + VIEWBOX_DELTA
    min_lng = center_lng - VIEWBOX_DELTA
    max_lng = center_lng + VIEWBOX_DELTA
    return f'{min_lng},{min_lat},{max_lng},{max_lat}'


def _make_request(params: dict) -> Optional[list]:
    """Faz requisição ao Nominatim com headers apropriados."""
    query = urllib.parse.urlencode(params)
    url = f'{NOMINATIM_URL}?{query}'

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': _get_user_agent(),
            'Accept': 'application/json',
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
            data = response.read().decode('utf-8')
            return json.loads(data)
    except urllib.error.URLError as e:
        logger.warning('Erro de rede ao geocodificar: %s', e)
        raise GeocodingNetworkError(f'Erro de rede: {e}') from e
    except urllib.error.HTTPError as e:
        logger.warning('Erro HTTP ao geocodificar: %s', e)
        raise GeocodingNetworkError(f'Erro HTTP: {e}') from e
    except json.JSONDecodeError as e:
        logger.warning('Resposta JSON inválida do Nominatim: %s', e)
        raise GeocodingNetworkError(f'Resposta inválida: {e}') from e
    except Exception as e:
        logger.exception('Erro inesperado ao geocodificar: %s', e)
        raise GeocodingNetworkError(f'Erro inesperado: {e}') from e


def _parse_coordinates(data: list) -> Optional[Tuple[Decimal, Decimal]]:
    """Extrai e converte lat/lon do primeiro resultado."""
    if not data:
        return None
    try:
        lat = Decimal(data[0]['lat']).quantize(QUANTIZE_EXP)
        lon = Decimal(data[0]['lon']).quantize(QUANTIZE_EXP)
        return lat, lon
    except (KeyError, InvalidOperation, IndexError) as e:
        logger.warning('Coordenadas inválidas na resposta: %s', e)
    return None


def geocodificar_endereco(rua: str, bairro: str, cidade: str) -> Optional[Tuple[Decimal, Decimal]]:
    """
    Geocodifica endereço usando Nominatim com fallback.

    Estratégias (em ordem):
    1. rua, bairro, cidade, Pará, Brasil
    2. rua, cidade, Pará, Brasil
    3. bairro, cidade, Pará, Brasil

    Args:
        rua: Nome da rua/endereço
        bairro: Nome do bairro
        cidade: Nome da cidade

    Returns:
        Tupla (latitude, longitude) como Decimal ou None se não encontrado.
    """
    # Normaliza entrada
    rua = (rua or '').strip()
    bairro = (bairro or '').strip()
    cidade = (cidade or '').strip()

    if not rua and not bairro:
        logger.warning('Rua e bairro vazios, impossível geocodificar')
        return None

    viewbox = _build_viewbox()
    base_params = {
        'format': 'jsonv2',
        'limit': 1,
        'countrycodes': 'br',
        'viewbox': viewbox,
        'bounded': 1,
        'addressdetails': 0,
    }

    # Estratégias de busca em ordem de prioridade
    strategies = []
    if rua and bairro:
        strategies.append(f'{rua}, {bairro}, {cidade}, Pará, Brasil')
    if rua:
        strategies.append(f'{rua}, {cidade}, Pará, Brasil')
    if bairro:
        strategies.append(f'{bairro}, {cidade}, Pará, Brasil')

    for i, query in enumerate(strategies):
        if i > 0:
            time.sleep(RATE_LIMIT_DELAY)  # Respeita rate limit do Nominatim

        params = {**base_params, 'q': query}
        logger.debug('Geocodificando (tentativa %d): %s', i + 1, query)

        result = _make_request(params)
        coords = _parse_coordinates(result) if result else None

        if coords:
            logger.info('Geocodificado com sucesso: %s -> %s, %s', query, coords[0], coords[1])
            return coords

    logger.warning('Endereço não encontrado após %d tentativas: rua=%s, bairro=%s, cidade=%s',
                   len(strategies), rua, bairro, cidade)
    return None


def geocodificar_rua(rua: str, cidade: str = 'Parauapebas', estado: str = 'Pará') -> Optional[Tuple[Decimal, Decimal]]:
    """
    Geocodifica apenas rua + cidade (helper para buscas mais simples).
    """
    return geocodificar_endereco(rua, '', cidade)
import logging
from rest_framework import serializers
from .models import AreaRisco, RegistroMonitoramento, Alerta

MAX_FOTO_SIZE_MB = 5

logger = logging.getLogger('apps.monitoramento.serializers')

# Chave usada para sinalizar falha de geocodificação (endereço não encontrado)
_GEOCODE_FAILED_KEY = '_geocode_not_found'


class AreaRiscoSerializer(serializers.ModelSerializer):
    area_nome = serializers.CharField(source='nome', read_only=True)

    class Meta:
        model = AreaRisco
        fields = '__all__'
        read_only_fields = ['data_criacao']

    def validate_foto(self, value):
        if value is None:
            return value
        if value.size > MAX_FOTO_SIZE_MB * 1024 * 1024:
            raise serializers.ValidationError(
                f"A imagem deve ter no máximo {MAX_FOTO_SIZE_MB} MB."
            )
        return value

    def validate_latitude(self, value):
        if value is not None and (value < -90 or value > 90):
            raise serializers.ValidationError("Latitude deve estar entre -90 e 90.")
        return value

    def validate_longitude(self, value):
        if value is not None and (value < -180 or value > 180):
            raise serializers.ValidationError("Longitude deve estar entre -180 e 180.")
        return value

    def _geocode_if_needed(self, validated_data: dict, instance: AreaRisco = None) -> dict:
        """
        Geocodifica endereço se latitude/longitude não foram fornecidas.
        Só executa se rua (nome), bairro ou cidade mudaram (ou é criação).
        """
        # Verifica se coordenadas já vieram na requisição
        lat_provided = 'latitude' in validated_data
        lng_provided = 'longitude' in validated_data

        if lat_provided and lng_provided:
            # Usuário enviou coordenadas manualmente, respeita
            return validated_data

        # Obtém valores atuais ou do instance (para update)
        # Usa default do model para cidade quando não fornecida
        cidade_default = AreaRisco._meta.get_field('cidade').default
        rua = validated_data.get('nome', instance.nome if instance else '')
        bairro = validated_data.get('bairro', instance.bairro if instance else '')
        cidade = validated_data.get('cidade', instance.cidade if instance else cidade_default)

        # Para update: só geocodifica se endereço mudou
        if instance:
            endereco_mudou = (
                ('nome' in validated_data and validated_data['nome'] != instance.nome) or
                ('bairro' in validated_data and validated_data.get('bairro', '') != instance.bairro) or
                ('cidade' in validated_data and validated_data.get('cidade', '') != instance.cidade)
            )
            if not endereco_mudou:
                return validated_data

        # Tenta geocodificar
        try:
            from .geocoding import geocodificar_endereco, GeocodingNetworkError
            coords = geocodificar_endereco(rua, bairro, cidade)
        except GeocodingNetworkError as e:
            # Erro de rede/timeout: loga aviso mas permite salvar sem coordenadas
            logger.warning('Erro de rede ao geocodificar %s, %s, %s: %s. Salvando sem coordenadas.', rua, bairro, cidade, e)
            return validated_data
        except Exception as e:
            logger.exception('Erro inesperado ao importar/chamar geocodificação: %s', e)
            coords = None

        if coords:
            lat, lng = coords
            if not lat_provided:
                validated_data['latitude'] = lat
            if not lng_provided:
                validated_data['longitude'] = lng
            logger.info('Coordenadas obtidas via geocodificação: %s, %s', lat, lng)
        else:
            # Endereço não encontrado (API respondeu normalmente mas sem resultados)
            self._geocode_failed = True
            logger.warning('Geocodificação falhou para: %s, %s, %s', rua, bairro, cidade)

        return validated_data

    def validate(self, attrs):
        """Executa geocodificação durante validação para definir flag antes de create/update."""
        attrs = self._geocode_if_needed(attrs, self.instance)
        return attrs

    def create(self, validated_data):
        return super().create(validated_data)

    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class RegistroMonitoramentoSerializer(serializers.ModelSerializer):
    area_nome = serializers.CharField(source='area.nome', read_only=True)

    class Meta:
        model = RegistroMonitoramento
        fields = '__all__'
        read_only_fields = ['status', 'data_hora']

    def validate_nivel_agua(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Nível de água não pode ser negativo.")
        return value


class AlertaSerializer(serializers.ModelSerializer):
    area_nome = serializers.CharField(source='area.nome', read_only=True)

    class Meta:
        model = Alerta
        fields = '__all__'
        read_only_fields = ['data_hora']
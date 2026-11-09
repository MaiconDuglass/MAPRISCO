import logging
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from .models import AreaRisco, RegistroMonitoramento, Alerta

MAX_FOTO_SIZE_MB = 5

logger = logging.getLogger('apps.monitoramento.serializers')

# Chave usada para sinalizar falha de geocodificação (endereço não encontrado)
_GEOCODE_FAILED_KEY = '_geocode_not_found'


class AreaRiscoSerializer(serializers.ModelSerializer):
    area_nome = serializers.CharField(source='nome', read_only=True)
    # Situação atual da área = dados da medição mais recente (null se não houver medição)
    ultimo_status = serializers.SerializerMethodField()
    ultimo_nivel_agua = serializers.SerializerMethodField()
    ultima_medicao_em = serializers.SerializerMethodField()

    class Meta:
        model = AreaRisco
        fields = '__all__'
        read_only_fields = ['data_criacao']

    def _ultima_medicao(self, obj):
        """(status, nivel_agua, data_hora) da medição mais recente.

        Na listagem os valores já vêm anotados pelo AreaRiscoViewSet (uma única consulta).
        Sem anotação (ex.: resposta de um POST), busca a medição diretamente.
        """
        if hasattr(obj, 'anot_ultimo_status'):
            return obj.anot_ultimo_status, obj.anot_ultimo_nivel, obj.anot_ultima_medicao
        if not hasattr(obj, '_cache_ultima_medicao'):
            ultima = (
                RegistroMonitoramento.objects.filter(area=obj)
                .order_by('-data_hora', '-pk')
                .values_list('status', 'nivel_agua', 'data_hora')
                .first()
            ) if obj.pk else None
            obj._cache_ultima_medicao = ultima or (None, None, None)
        return obj._cache_ultima_medicao

    def get_ultimo_status(self, obj):
        return self._ultima_medicao(obj)[0]

    def get_ultimo_nivel_agua(self, obj):
        nivel = self._ultima_medicao(obj)[1]
        # Mesmo formato do nivel_agua em /api/monitoramento/ (texto com 2 casas: "35.00")
        return None if nivel is None else serializers.DecimalField(max_digits=5, decimal_places=2).to_representation(nivel)

    def get_ultima_medicao_em(self, obj):
        data_hora = self._ultima_medicao(obj)[2]
        return None if data_hora is None else serializers.DateTimeField().to_representation(data_hora)

    def get_validators(self):
        # Mensagem amigável para a regra "rua + bairro + cidade" única (o padrão fala em "set único")
        validators = super().get_validators()
        for validator in validators:
            if isinstance(validator, UniqueTogetherValidator):
                validator.message = 'Já existe uma área cadastrada com esta rua, bairro e cidade.'
        return validators

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
from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import AreaRisco, RegistroMonitoramento, Alerta


class AreaRiscoModelTests(TestCase):

    def setUp(self):
        self.area = AreaRisco.objects.create(
            nome='Rio Itacaiúnas',
            bairro='Centro',
            cidade='Parauapebas',
            nivel_risco='alto',
        )

    def test_string_representation(self):
        self.assertEqual(str(self.area), 'Rio Itacaiúnas')


class RegistroMonitoramentoTests(TestCase):

    def setUp(self):
        self.area = AreaRisco.objects.create(nome='Rio Parauapebas', nivel_risco='medio')

    def test_status_auto_classified_as_critico(self):
        registro = RegistroMonitoramento.objects.create(area=self.area, nivel_agua=85.5)
        self.assertEqual(registro.status, 'critico')

    def test_status_auto_classified_as_alerta(self):
        registro = RegistroMonitoramento.objects.create(area=self.area, nivel_agua=65)
        self.assertEqual(registro.status, 'alerta')

    def test_status_normal_for_low_water_level(self):
        registro = RegistroMonitoramento.objects.create(area=self.area, nivel_agua=20)
        self.assertEqual(registro.status, 'normal')

    def test_critico_creates_high_priority_alert(self):
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=90)
        alerts = Alerta.objects.filter(area=self.area)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().nivel, 'alto')

    def test_no_duplicate_alert_within_same_escalation(self):
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=82)
        registro = RegistroMonitoramento.objects.get(area=self.area)
        registro.nivel_agua = 95  # stays critical, no new alert
        registro.status = 'normal'
        registro.save()
        self.assertEqual(Alerta.objects.filter(area=self.area).count(), 1)


class AlertaModelTests(TestCase):

    def setUp(self):
        self.area = AreaRisco.objects.create(nome='Área Teste')
        self.alerta = Alerta.objects.create(area=self.area, mensagem='Alerta de teste', nivel='alto')

    def test_resolver_marks_alert_as_resolved(self):
        self.alerta.resolver()
        self.alerta.refresh_from_db()
        self.assertTrue(self.alerta.resolvido)


class ApiTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='apiuser', password='senha123')
        self.area = AreaRisco.objects.create(nome='Área API', bairro='Centro', nivel_risco='medio')
        self.alerta = Alerta.objects.create(area=self.area, mensagem='Alerta teste', nivel='medio')

    def test_list_is_public(self):
        response = self.client.get(reverse('alerta-list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)

    def test_write_requires_authentication(self):
        response = self.client.post(reverse('arearisco-list'), {
            'nome': 'Área sem auth',
            'bairro': 'Centro',
            'nivel_risco': 'baixo',
        })
        self.assertIn(response.status_code, (401, 403))

    def test_authenticated_can_create_area(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('arearisco-list'), {
            'nome': 'Área autenticada',
            'bairro': 'Centro',
            'nivel_risco': 'baixo',
        })
        self.assertEqual(response.status_code, 201)

    def test_resolver_action_marks_alert_as_resolved(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('alerta-resolver', kwargs={'pk': self.alerta.pk}))
        self.assertEqual(response.status_code, 200)
        self.alerta.refresh_from_db()
        self.assertTrue(self.alerta.resolvido)

    def test_registro_creates_alert_via_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/monitoramento/', {
            'area': self.area.pk,
            'nivel_agua': 88,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Alerta.objects.filter(area=self.area, nivel='alto').count(), 1)


# =============================================================================
# Geocoding Tests
# =============================================================================

class GeocodingTests(TestCase):
    """Testes para a integração de geocodificação no serializer e API."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='geo_user', password='senha123')
        self.client.force_authenticate(user=self.user)

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_create_area_with_geocoding(self, mock_geocode):
        """(a) Cadastro só com rua e bairro preenche lat/lng via geocodificação."""
        mock_geocode.return_value = (Decimal('-6.062623'), Decimal('-49.895450'))

        response = self.client.post('/api/areas/', {
            'nome': 'Rua das Palmeiras',
            'bairro': 'Centro',
            'nivel_risco': 'alto',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['nome'], 'Rua das Palmeiras')
        self.assertEqual(response.data['bairro'], 'Centro')
        self.assertIsNotNone(response.data['latitude'])
        self.assertIsNotNone(response.data['longitude'])
        self.assertEqual(float(response.data['latitude']), -6.062623)
        self.assertEqual(float(response.data['longitude']), -49.895450)

        # Verifica se a geocodificação foi chamada com os parâmetros corretos
        mock_geocode.assert_called_once_with('Rua das Palmeiras', 'Centro', 'Parauapebas')

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_create_area_with_manual_coordinates_preserved(self, mock_geocode):
        """(b) Coordenadas enviadas manualmente são preservadas (não geocodifica)."""
        mock_geocode.return_value = (Decimal('-1.0'), Decimal('-1.0'))  # não deve ser usado

        response = self.client.post('/api/areas/', {
            'nome': 'Rua Teste',
            'bairro': 'Bairro Teste',
            'nivel_risco': 'baixo',
            'latitude': '-10.123456',
            'longitude': '-20.654321',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(float(response.data['latitude']), -10.123456)
        self.assertEqual(float(response.data['longitude']), -20.654321)
        mock_geocode.assert_not_called()

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_create_area_address_not_found_returns_400(self, mock_geocode):
        """(c) Endereço não encontrado retorna 400 com mensagem em português."""
        mock_geocode.return_value = None  # simula endereço não encontrado

        response = self.client.post('/api/areas/', {
            'nome': 'Rua Inexistente XYZ',
            'bairro': 'Bairro Inexistente',
            'nivel_risco': 'medio',
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertIn('Não foi possível localizar', str(response.data))
        mock_geocode.assert_called_once()

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_create_area_network_failure_saves_without_coords(self, mock_geocode):
        """(d) Falha de rede (exception) salva a área com lat/lng nulos."""
        from apps.monitoramento.geocoding import GeocodingNetworkError
        mock_geocode.side_effect = GeocodingNetworkError('Network error')

        response = self.client.post('/api/areas/', {
            'nome': 'Rua com Erro de Rede',
            'bairro': 'Centro',
            'nivel_risco': 'baixo',
        }, format='json')

        # Deve salvar com sucesso (201) mas sem coordenadas
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data['latitude'])
        self.assertIsNone(response.data['longitude'])

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_update_area_changing_street_triggers_regeocode(self, mock_geocode):
        """(e) Update que muda a rua refaz a geocodificação."""
        mock_geocode.return_value = (Decimal('-6.100000'), Decimal('-49.900000'))

        # Cria área inicial
        area = AreaRisco.objects.create(
            nome='Rua Original',
            bairro='Centro',
            nivel_risco='medio'
        )

        # Atualiza mudando o nome (rua)
        response = self.client.patch(f'/api/areas/{area.pk}/', {
            'nome': 'Nova Rua',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['nome'], 'Nova Rua')
        self.assertIsNotNone(response.data['latitude'])
        self.assertIsNotNone(response.data['longitude'])
        self.assertEqual(float(response.data['latitude']), -6.100000)
        self.assertEqual(float(response.data['longitude']), -49.900000)

        # Verifica se geocodificou com o novo nome
        mock_geocode.assert_called_once_with('Nova Rua', 'Centro', 'Parauapebas')

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_update_area_without_address_change_no_regeocode(self, mock_geocode):
        """Update que não muda endereço não re-geocodifica."""
        # Cria área com coordenadas manuais
        area = AreaRisco.objects.create(
            nome='Rua Teste',
            bairro='Centro',
            nivel_risco='baixo',
            latitude=Decimal('-5.000000'),
            longitude=Decimal('-50.000000'),
        )

        # Atualiza apenas descrição
        response = self.client.patch(f'/api/areas/{area.pk}/', {
            'descricao': 'Nova descrição',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(float(response.data['latitude']), -5.000000)
        self.assertEqual(float(response.data['longitude']), -50.000000)
        mock_geocode.assert_not_called()
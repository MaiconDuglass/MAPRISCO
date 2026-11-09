from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.utils import timezone

from .management.commands.cadastrar_areas_reais import AREAS_EXEMPLO, AREAS_REAIS
from .management.commands.dados_demo import SERIES_DEMO
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

    def test_critico_creates_critical_alert(self):
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=90)
        alerts = Alerta.objects.filter(area=self.area)
        self.assertEqual(alerts.count(), 1)
        self.assertEqual(alerts.first().nivel, 'critico')

    def test_alert_message_uses_brazilian_decimal(self):
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=85.5)
        self.assertIn('85,50 cm', Alerta.objects.get(area=self.area).mensagem)

    def test_critical_alert_emails_staff(self):
        from django.core import mail
        User.objects.create_user(username='defesa', password='x', email='defesa@exemplo.com', is_staff=True)
        User.objects.create_user(username='cidadao', password='x', email='cidadao@exemplo.com')
        with self.captureOnCommitCallbacks(execute=True):
            RegistroMonitoramento.objects.create(area=self.area, nivel_agua=90)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['defesa@exemplo.com'])
        self.assertIn('Alerta crítico', mail.outbox[0].subject)

    def test_no_email_for_non_critical_level(self):
        from django.core import mail
        User.objects.create_user(username='defesa', password='x', email='defesa@exemplo.com', is_staff=True)
        with self.captureOnCommitCallbacks(execute=True):
            RegistroMonitoramento.objects.create(area=self.area, nivel_agua=60)
        self.assertEqual(len(mail.outbox), 0)

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
        admin = User.objects.create_user(username='admin', password='senha123', is_staff=True)
        self.client.force_authenticate(user=admin)
        response = self.client.post(reverse('alerta-resolver', kwargs={'pk': self.alerta.pk}))
        self.assertEqual(response.status_code, 200)
        self.alerta.refresh_from_db()
        self.assertTrue(self.alerta.resolvido)

    def test_registros_can_be_filtered_by_area(self):
        outra = AreaRisco.objects.create(nome='Outra área', bairro='Centro')
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=10)
        RegistroMonitoramento.objects.create(area=outra, nivel_agua=20)
        response = self.client.get('/api/monitoramento/', {'area': self.area.pk})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['area'], self.area.pk)

    def test_page_size_can_be_requested(self):
        for i in range(5):
            RegistroMonitoramento.objects.create(area=self.area, nivel_agua=i)
        response = self.client.get('/api/monitoramento/', {'page_size': 2})
        self.assertEqual(len(response.data['results']), 2)
        self.assertEqual(response.data['count'], 5)

    def test_common_user_cannot_resolve_alert(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('alerta-resolver', kwargs={'pk': self.alerta.pk}))
        self.assertEqual(response.status_code, 403)
        self.alerta.refresh_from_db()
        self.assertFalse(self.alerta.resolvido)

    def test_common_user_cannot_delete_area(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(reverse('arearisco-detail', kwargs={'pk': self.area.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(AreaRisco.objects.filter(pk=self.area.pk).exists())

    def test_admin_can_delete_area(self):
        admin = User.objects.create_user(username='admin', password='senha123', is_staff=True)
        self.client.force_authenticate(user=admin)
        response = self.client.delete(reverse('arearisco-detail', kwargs={'pk': self.area.pk}))
        self.assertEqual(response.status_code, 204)
        self.assertFalse(AreaRisco.objects.filter(pk=self.area.pk).exists())

    def test_registro_creates_alert_via_api(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/monitoramento/', {
            'area': self.area.pk,
            'nivel_agua': 88,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Alerta.objects.filter(area=self.area, nivel='critico').count(), 1)


# =============================================================================
# Geocoding Tests
# =============================================================================

class GeocodingTests(TestCase):
    """Testes para a integração de geocodificação no serializer e API."""

    def setUp(self):
        self.client = APIClient()
        # Administrador: os testes de update (PATCH) exigem perfil de administrador
        self.user = User.objects.create_user(username='geo_user', password='senha123', is_staff=True)
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

    def test_duplicate_area_returns_friendly_message(self):
        """Rua + bairro + cidade repetidos: mensagem em português claro, sem 'set único'."""
        dados = {
            'nome': 'Rua Repetida', 'bairro': 'Centro', 'cidade': 'Parauapebas',
            'latitude': '-6.060000', 'longitude': '-49.900000', 'nivel_risco': 'baixo',
        }
        self.assertEqual(self.client.post('/api/areas/', dados, format='json').status_code, 201)
        response = self.client.post('/api/areas/', dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Já existe uma área cadastrada', str(response.data))


class CadastrarAreasReaisCommandTests(TestCase):

    def rodar(self, *args):
        out = StringIO()
        call_command('cadastrar_areas_reais', *args, stdout=out)
        return out.getvalue()

    def test_cria_as_quatro_areas_reais(self):
        self.rodar()
        nomes = set(AreaRisco.objects.values_list('nome', flat=True))
        self.assertEqual(nomes, {a['nome'] for a in AREAS_REAIS})
        liberdade = AreaRisco.objects.get(bairro='Liberdade')
        self.assertEqual(liberdade.cidade, 'Parauapebas')
        self.assertEqual(liberdade.nivel_risco, 'alto')
        self.assertIsNotNone(liberdade.latitude)

    def test_rodar_duas_vezes_nao_duplica(self):
        self.rodar()
        saida = self.rodar()
        self.assertEqual(AreaRisco.objects.count(), 4)
        self.assertIn('0 áreas reais criadas, 4 atualizadas', saida)

    def test_limpar_exemplos_remove_so_as_ficticias(self):
        ficticia = AreaRisco.objects.create(nome='Setor Industrial', nivel_risco='alto')
        RegistroMonitoramento.objects.create(area=ficticia, nivel_agua=90)  # gera alerta
        outra = AreaRisco.objects.create(nome='Rua Cadastrada pelo Usuário', bairro='Centro')

        self.rodar('--limpar-exemplos')

        self.assertFalse(AreaRisco.objects.filter(nome='Setor Industrial').exists())
        self.assertEqual(RegistroMonitoramento.objects.count(), 0)
        self.assertEqual(Alerta.objects.count(), 0)
        self.assertTrue(AreaRisco.objects.filter(pk=outra.pk).exists())
        self.assertEqual(AreaRisco.objects.count(), 5)

    def test_sem_flag_nao_apaga_ficticias(self):
        AreaRisco.objects.create(nome='Setor Industrial', nivel_risco='alto')
        self.rodar()
        self.assertTrue(AreaRisco.objects.filter(nome='Setor Industrial').exists())

    def test_populate_parauapebas_nao_cria_ficticias(self):
        call_command('populate_parauapebas', stdout=StringIO())
        self.assertEqual(AreaRisco.objects.count(), 4)
        self.assertFalse(AreaRisco.objects.filter(nome__in=AREAS_EXEMPLO).exists())


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class DadosDemoCommandTests(TestCase):

    def setUp(self):
        call_command('cadastrar_areas_reais', stdout=StringIO())

    def rodar(self):
        out = StringIO()
        call_command('dados_demo', stdout=out)
        return out.getvalue()

    def test_gera_medicoes_normal_alerta_e_critica(self):
        self.rodar()
        status = set(RegistroMonitoramento.objects.values_list('status', flat=True))
        self.assertEqual(status, {'normal', 'alerta', 'critico'})
        self.assertEqual(RegistroMonitoramento.objects.count(), sum(len(s) for s in SERIES_DEMO.values()))

    def test_status_segue_a_regra_dos_limites(self):
        self.rodar()
        for registro in RegistroMonitoramento.objects.all():
            if registro.nivel_agua >= 80:
                self.assertEqual(registro.status, 'critico')
            elif registro.nivel_agua >= 50:
                self.assertEqual(registro.status, 'alerta')
            else:
                self.assertEqual(registro.status, 'normal')

    def test_medicoes_espalhadas_pelos_ultimos_dias(self):
        self.rodar()
        agora = timezone.now()
        datas = list(RegistroMonitoramento.objects.values_list('data_hora', flat=True))
        self.assertTrue(all(agora - timedelta(days=8) < d <= agora for d in datas))
        self.assertGreaterEqual(len({timezone.localtime(d).date() for d in datas}), 5)

    def test_rodar_duas_vezes_nao_duplica(self):
        self.rodar()
        registros, alertas = RegistroMonitoramento.objects.count(), Alerta.objects.count()
        saida = self.rodar()
        self.assertEqual(RegistroMonitoramento.objects.count(), registros)
        self.assertEqual(Alerta.objects.count(), alertas)
        self.assertIn('0 medições e 0 alertas', saida)

    def test_cria_alertas_criticos_com_um_em_aberto(self):
        self.rodar()
        self.assertTrue(Alerta.objects.exists())
        self.assertFalse(Alerta.objects.exclude(nivel='critico').exists())
        self.assertEqual(Alerta.objects.filter(resolvido=False).count(), 1)

    def test_nao_envia_email(self):
        User.objects.create_user('admin', email='admin@example.com', password='x', is_staff=True)
        self.rodar()
        self.assertEqual(len(mail.outbox), 0)

    def test_nao_mexe_em_area_que_ja_tem_medicao(self):
        liberdade = AreaRisco.objects.get(bairro='Liberdade')
        RegistroMonitoramento.objects.create(area=liberdade, nivel_agua=10)
        self.rodar()
        self.assertEqual(liberdade.registros.count(), 1)

    def test_sem_areas_reais_avisa_e_nao_cria_nada(self):
        AreaRisco.objects.all().delete()
        saida = self.rodar()
        self.assertIn('cadastrar_areas_reais', saida)
        self.assertEqual(RegistroMonitoramento.objects.count(), 0)


class SituacaoAtualDaAreaApiTests(TestCase):
    """Campos ultimo_status, ultimo_nivel_agua e ultima_medicao_em em /api/areas/."""

    def setUp(self):
        self.client = APIClient()
        self.area = AreaRisco.objects.create(nome='Rua do Rio', bairro='União', nivel_risco='alto')

    def medir(self, nivel, horas_atras=0, area=None):
        registro = RegistroMonitoramento.objects.create(area=area or self.area, nivel_agua=Decimal(str(nivel)))
        if horas_atras:
            RegistroMonitoramento.objects.filter(pk=registro.pk).update(
                data_hora=timezone.now() - timedelta(hours=horas_atras))
        return registro

    def detalhe(self, area=None):
        response = self.client.get(f'/api/areas/{(area or self.area).pk}/')
        self.assertEqual(response.status_code, 200)
        return response.data

    def test_area_sem_medicao_retorna_null(self):
        dados = self.detalhe()
        self.assertIsNone(dados['ultimo_status'])
        self.assertIsNone(dados['ultimo_nivel_agua'])
        self.assertIsNone(dados['ultima_medicao_em'])

    def test_varias_medicoes_retorna_a_mais_recente(self):
        self.medir(90, horas_atras=48)   # crítico, antigo
        self.medir(60, horas_atras=24)   # alerta
        self.medir(35, horas_atras=1)    # normal, o mais recente
        dados = self.detalhe()
        self.assertEqual(dados['ultimo_status'], 'normal')
        self.assertEqual(dados['ultimo_nivel_agua'], '35.00')
        self.assertIsNotNone(dados['ultima_medicao_em'])

    def test_nivel_de_risco_cadastrado_nao_muda(self):
        """A área continua 'alto' no cadastro, mesmo com a situação atual normal."""
        self.medir(35)
        dados = self.detalhe()
        self.assertEqual(dados['nivel_risco'], 'alto')
        self.assertEqual(dados['ultimo_status'], 'normal')

    def test_registrar_90_cm_deixa_critico(self):
        self.medir(35, horas_atras=2)
        self.assertEqual(self.detalhe()['ultimo_status'], 'normal')

        user = User.objects.create_user(username='cidadao@exemplo.com', password='senha123')
        self.client.force_authenticate(user)
        response = self.client.post('/api/monitoramento/', {'area': self.area.pk, 'nivel_agua': '90'}, format='json')
        self.assertEqual(response.status_code, 201)

        dados = self.detalhe()
        self.assertEqual(dados['ultimo_status'], 'critico')
        self.assertEqual(dados['ultimo_nivel_agua'], '90.00')

    def test_listagem_traz_a_situacao_de_cada_area(self):
        outra = AreaRisco.objects.create(nome='Rua do Igarapé', bairro='Novo Brasil', nivel_risco='medio')
        self.medir(85, area=outra)
        response = self.client.get('/api/areas/')
        por_id = {a['id']: a for a in response.data['results']}
        self.assertIsNone(por_id[self.area.pk]['ultimo_status'])
        self.assertEqual(por_id[outra.pk]['ultimo_status'], 'critico')

    def test_listagem_sem_n_mais_1(self):
        """O número de consultas não cresce com a quantidade de áreas."""
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        self.medir(40)
        with CaptureQueriesContext(connection) as poucas:
            self.client.get('/api/areas/')
        for i in range(5):
            area = AreaRisco.objects.create(nome=f'Rua {i}', bairro='Centro')
            self.medir(50 + i, area=area)
        with CaptureQueriesContext(connection) as muitas:
            self.client.get('/api/areas/')
        self.assertEqual(len(poucas), len(muitas))

    def test_campos_sao_somente_leitura(self):
        admin = User.objects.create_user(username='admin@exemplo.com', password='x', is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.patch(f'/api/areas/{self.area.pk}/', {'ultimo_status': 'critico'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['ultimo_status'])

    def test_resposta_do_cadastro_traz_os_campos(self):
        user = User.objects.create_user(username='cidadao@exemplo.com', password='senha123')
        self.client.force_authenticate(user)
        response = self.client.post('/api/areas/', {
            'nome': 'Rua Nova', 'bairro': 'Primavera', 'cidade': 'Parauapebas',
            'latitude': '-6.06', 'longitude': '-49.91', 'nivel_risco': 'baixo',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('ultimo_status', response.data)
        self.assertIsNone(response.data['ultimo_status'])
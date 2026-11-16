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
from .models import AreaRisco, RegistroMonitoramento, Alerta, RelatoAlagamento


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

    def test_common_user_cannot_create_area(self):
        """Usuário comum não cadastra área (evita áreas falsas)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('arearisco-list'), {
            'nome': 'Área falsa',
            'bairro': 'Centro',
            'nivel_risco': 'baixo',
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(AreaRisco.objects.filter(nome='Área falsa').exists())

    def test_admin_can_create_area(self):
        admin = User.objects.create_user(username='admin', password='senha123', is_staff=True)
        self.client.force_authenticate(user=admin)
        response = self.client.post(reverse('arearisco-list'), {
            'nome': 'Área do administrador',
            'bairro': 'Centro',
            'nivel_risco': 'baixo',
            'latitude': '-6.06',
            'longitude': '-49.90',
        })
        self.assertEqual(response.status_code, 201)

    def test_common_user_cannot_create_medicao(self):
        """Usuário comum não registra medição (evita alerta crítico falso e e-mail à Defesa Civil)."""
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/monitoramento/', {'area': self.area.pk, 'nivel_agua': 95})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(RegistroMonitoramento.objects.filter(area=self.area).exists())
        self.assertFalse(Alerta.objects.filter(area=self.area, nivel='critico').exists())

    def test_visitor_cannot_create_medicao(self):
        response = self.client.post('/api/monitoramento/', {'area': self.area.pk, 'nivel_agua': 95})
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(RegistroMonitoramento.objects.filter(area=self.area).exists())

    def test_common_user_cannot_change_or_delete_medicao(self):
        registro = RegistroMonitoramento.objects.create(area=self.area, nivel_agua=10)
        self.client.force_authenticate(user=self.user)
        url = f'/api/monitoramento/{registro.pk}/'
        self.assertEqual(self.client.patch(url, {'nivel_agua': 99}).status_code, 403)
        self.assertEqual(self.client.delete(url).status_code, 403)
        self.assertTrue(RegistroMonitoramento.objects.filter(pk=registro.pk).exists())

    def test_areas_e_medicoes_tem_leitura_publica(self):
        RegistroMonitoramento.objects.create(area=self.area, nivel_agua=10)
        self.assertEqual(self.client.get('/api/monitoramento/').status_code, 200)
        self.assertEqual(self.client.get('/api/areas/').status_code, 200)

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
        admin = User.objects.create_user(username='admin', password='senha123', is_staff=True)
        self.client.force_authenticate(user=admin)
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

        admin = User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)
        self.client.force_authenticate(admin)
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
        admin = User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)
        self.client.force_authenticate(admin)
        response = self.client.post('/api/areas/', {
            'nome': 'Rua Nova', 'bairro': 'Primavera', 'cidade': 'Parauapebas',
            'latitude': '-6.06', 'longitude': '-49.91', 'nivel_risco': 'baixo',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('ultimo_status', response.data)
        self.assertIsNone(response.data['ultimo_status'])


class CriarUsuarioDemoCommandTests(TestCase):
    """Comando criar_usuario_demo: usuário comum, senha digitada no terminal."""

    def rodar(self, senha, confirmacao=None):
        respostas = [senha, senha if confirmacao is None else confirmacao]
        out = StringIO()
        with patch('getpass.getpass', side_effect=respostas):
            call_command('criar_usuario_demo', stdout=out)
        return out.getvalue()

    def test_cria_usuario_comum_com_nome_e_email(self):
        saida = self.rodar('DemoForte#2026')
        user = User.objects.get(username='usuario.demo@maprisco.local')
        self.assertEqual(user.email, 'usuario.demo@maprisco.local')
        self.assertEqual(user.first_name, 'Usuário Demo')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('DemoForte#2026'))
        self.assertIn('criado', saida)

    def test_rodar_de_novo_atualiza_senha_e_tira_admin(self):
        self.rodar('DemoForte#2026')
        User.objects.filter(username='usuario.demo@maprisco.local').update(is_staff=True)
        self.rodar('OutraSenha#2026')
        self.assertEqual(User.objects.filter(username='usuario.demo@maprisco.local').count(), 1)
        user = User.objects.get(username='usuario.demo@maprisco.local')
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('OutraSenha#2026'))

    def test_senhas_diferentes_nao_cria(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.rodar('DemoForte#2026', 'Diferente#2026')
        self.assertFalse(User.objects.filter(username='usuario.demo@maprisco.local').exists())

    def test_senha_fraca_nao_cria(self):
        from django.core.management.base import CommandError
        with self.assertRaises(CommandError):
            self.rodar('123')
        self.assertFalse(User.objects.filter(username='usuario.demo@maprisco.local').exists())


# =============================================================================
# Relatos de alagamento (participação cidadã)
# =============================================================================

def png_pequeno(nome='foto.png'):
    """Imagem PNG válida de 1x1 pixel, para testar upload de foto."""
    from django.core.files.uploadedfile import SimpleUploadedFile
    import base64
    dados = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
    )
    return SimpleUploadedFile(nome, dados, content_type='image/png')


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RelatoAlagamentoApiTests(TestCase):

    URL = '/api/relatos/'

    @classmethod
    def setUpTestData(cls):
        # Criados uma vez para a classe toda (criar usuário com senha é lento por causa do hash)
        cls.morador = User.objects.create_user(
            username='morador@exemplo.com', password='x', email='morador@exemplo.com', first_name='Maria Moradora')
        cls.vizinho = User.objects.create_user(username='vizinho@exemplo.com', password='x', first_name='Vizinho')
        cls.admin = User.objects.create_user(
            username='defesa@exemplo.com', password='x', email='defesa@exemplo.com', is_staff=True)
        cls.area = AreaRisco.objects.create(nome='Margem do Rio', bairro='Liberdade', nivel_risco='alto',
                                            latitude=Decimal('-6.081236'), longitude=Decimal('-49.910355'))

    def setUp(self):
        self.client = APIClient()

    def dados(self, **extra):
        base = {
            'nome': 'Rua das Palmeiras', 'bairro': 'Liberdade',
            'latitude': '-6.080000', 'longitude': '-49.910000',
            'nivel_estimado': 'tornozelo', 'descricao': 'Água cobrindo a calçada.',
        }
        base.update(extra)
        return base

    def criar(self, autor=None, status='pendente', **extra):
        campos = {'nome': 'Rua X', 'bairro': 'União', 'latitude': Decimal('-6.07'),
                  'longitude': Decimal('-49.90'), 'nivel_estimado': 'joelho', 'status': status}
        campos.update(extra)
        return RelatoAlagamento.objects.create(autor=autor, **campos)

    # --- Envio ---
    def test_visitante_nao_cria_relato(self):
        response = self.client.post(self.URL, self.dados(), format='json')
        self.assertIn(response.status_code, (401, 403))
        self.assertFalse(RelatoAlagamento.objects.exists())

    def test_usuario_comum_cria_relato_pendente(self):
        self.client.force_authenticate(self.morador)
        response = self.client.post(self.URL, self.dados(), format='json')
        self.assertEqual(response.status_code, 201, response.data)
        relato = RelatoAlagamento.objects.get()
        self.assertEqual(relato.autor, self.morador)
        self.assertEqual(relato.status, 'pendente')
        self.assertEqual(relato.cidade, 'Parauapebas')

    def test_autor_e_sempre_o_usuario_logado(self):
        self.client.force_authenticate(self.morador)
        response = self.client.post(self.URL, self.dados(autor=self.vizinho.pk, status='aprovado'), format='json')
        self.assertEqual(response.status_code, 201)
        relato = RelatoAlagamento.objects.get()
        self.assertEqual(relato.autor, self.morador)
        self.assertEqual(relato.status, 'pendente')

    def test_relato_com_foto(self):
        self.client.force_authenticate(self.morador)
        response = self.client.post(self.URL, {**self.dados(), 'foto': png_pequeno()}, format='multipart')
        self.assertEqual(response.status_code, 201, response.data)
        relato = RelatoAlagamento.objects.get()
        self.assertTrue(relato.foto.name.startswith('relatos/'))
        relato.foto.delete(save=False)

    def test_limite_de_5_relatos_em_24_horas(self):
        self.client.force_authenticate(self.morador)
        for i in range(5):
            response = self.client.post(self.URL, self.dados(nome=f'Rua {i}'), format='json')
            self.assertEqual(response.status_code, 201)
        response = self.client.post(self.URL, self.dados(nome='Rua 6'), format='json')
        self.assertEqual(response.status_code, 429)
        self.assertIn('5 relatos nas últimas 24 horas', str(response.data))
        self.assertEqual(RelatoAlagamento.objects.count(), 5)

    def test_limite_considera_so_as_ultimas_24_horas(self):
        for i in range(5):
            relato = self.criar(autor=self.morador)
            RelatoAlagamento.objects.filter(pk=relato.pk).update(data_hora=timezone.now() - timedelta(hours=25))
        self.client.force_authenticate(self.morador)
        self.assertEqual(self.client.post(self.URL, self.dados(), format='json').status_code, 201)

    def test_coordenadas_fora_de_parauapebas_sao_recusadas(self):
        self.client.force_authenticate(self.morador)
        # Belém-PA
        response = self.client.post(self.URL, self.dados(latitude='-1.455800', longitude='-48.490200'), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('fora da região de Parauapebas', str(response.data))
        self.assertFalse(RelatoAlagamento.objects.exists())

    @patch('apps.monitoramento.geocoding.geocodificar_endereco')
    def test_sem_clique_no_mapa_usa_geocodificacao(self, mock_geocode):
        mock_geocode.return_value = (Decimal('-6.070000'), Decimal('-49.900000'))
        self.client.force_authenticate(self.morador)
        dados = self.dados()
        del dados['latitude'], dados['longitude']
        response = self.client.post(self.URL, dados, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(RelatoAlagamento.objects.get().latitude, Decimal('-6.070000'))

    @patch('apps.monitoramento.geocoding.geocodificar_endereco', return_value=None)
    def test_endereco_nao_encontrado_pede_clique_no_mapa(self, mock_geocode):
        self.client.force_authenticate(self.morador)
        dados = self.dados()
        del dados['latitude'], dados['longitude']
        response = self.client.post(self.URL, dados, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('Marque o local do alagamento no mapa', str(response.data))

    def test_email_para_administradores_ao_criar_relato(self):
        self.client.force_authenticate(self.morador)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(self.URL, self.dados(), format='json')
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['defesa@exemplo.com'])
        self.assertIn('Rua das Palmeiras', mail.outbox[0].subject)

    def test_falha_no_email_nao_impede_o_relato(self):
        self.client.force_authenticate(self.morador)
        with patch('apps.monitoramento.models.send_mail', side_effect=Exception('SMTP fora do ar')):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(self.URL, self.dados(), format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(RelatoAlagamento.objects.count(), 1)

    # --- Leitura por perfil ---
    def test_visitante_ve_so_aprovados_sem_dados_do_autor(self):
        aprovado = self.criar(autor=self.morador, status='aprovado')
        self.criar(autor=self.morador, status='pendente')
        self.criar(autor=self.morador, status='rejeitado', motivo_rejeicao='Duplicado')
        response = self.client.get(self.URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r['id'] for r in response.data['results']], [aprovado.pk])
        texto = str(response.data)
        for proibido in ('autor', 'Maria Moradora', 'morador@exemplo.com', 'motivo_rejeicao'):
            self.assertNotIn(proibido, texto)

    def test_usuario_ve_aprovados_e_os_seus_pendentes(self):
        aprovado_de_outro = self.criar(autor=self.vizinho, status='aprovado')
        pendente_de_outro = self.criar(autor=self.vizinho, status='pendente')
        meu_pendente = self.criar(autor=self.morador, status='pendente')
        meu_rejeitado = self.criar(autor=self.morador, status='rejeitado', motivo_rejeicao='Fora da área')
        self.client.force_authenticate(self.morador)
        response = self.client.get(self.URL)
        ids = {r['id'] for r in response.data['results']}
        self.assertEqual(ids, {aprovado_de_outro.pk, meu_pendente.pk, meu_rejeitado.pk})
        self.assertNotIn(pendente_de_outro.pk, ids)
        por_id = {r['id']: r for r in response.data['results']}
        self.assertEqual(por_id[meu_rejeitado.pk]['motivo_rejeicao'], 'Fora da área')
        self.assertTrue(por_id[meu_pendente.pk]['eh_meu'])
        self.assertNotIn('autor_nome', por_id[aprovado_de_outro.pk])
        self.assertNotIn('Vizinho', str(response.data))

    def test_meus_relatos(self):
        self.criar(autor=self.vizinho, status='aprovado')
        meu = self.criar(autor=self.morador, status='pendente')
        self.client.force_authenticate(self.morador)
        response = self.client.get(self.URL, {'meus': 1})
        self.assertEqual([r['id'] for r in response.data['results']], [meu.pk])

    def test_admin_ve_todos_com_autor(self):
        for status in ('pendente', 'aprovado', 'rejeitado'):
            self.criar(autor=self.morador, status=status)
        self.client.force_authenticate(self.admin)
        response = self.client.get(self.URL)
        self.assertEqual(response.data['count'], 3)
        self.assertEqual(response.data['results'][0]['autor_nome'], 'Maria Moradora')
        self.assertEqual(response.data['results'][0]['autor_email'], 'morador@exemplo.com')
        self.assertEqual(self.client.get(self.URL, {'status': 'pendente'}).data['count'], 1)

    def test_filtro_dos_ultimos_7_dias(self):
        recente = self.criar(status='aprovado')
        antigo = self.criar(status='aprovado')
        RelatoAlagamento.objects.filter(pk=antigo.pk).update(data_hora=timezone.now() - timedelta(days=8))
        response = self.client.get(self.URL, {'status': 'aprovado', 'dias': 7})
        self.assertEqual([r['id'] for r in response.data['results']], [recente.pk])

    # --- Análise (aprovar / rejeitar) ---
    def test_usuario_comum_nao_aprova_nem_rejeita(self):
        relato = self.criar(autor=self.morador)
        self.client.force_authenticate(self.morador)
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'area': self.area.pk}, format='json').status_code, 403)
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/rejeitar/', {'motivo': 'x'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(f'{self.URL}{relato.pk}/').status_code, 403)
        relato.refresh_from_db()
        self.assertEqual(relato.status, 'pendente')

    def test_aprovar_vinculando_area_existente(self):
        relato = self.criar(autor=self.morador)
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'area': self.area.pk}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        relato.refresh_from_db()
        self.assertEqual(relato.status, 'aprovado')
        self.assertEqual(relato.area, self.area)
        self.assertEqual(relato.analisado_por, self.admin)
        self.assertIsNotNone(relato.analisado_em)
        self.assertEqual(response.data['area'], self.area.pk)

    def test_aprovar_criando_area_nova(self):
        relato = self.criar(autor=self.morador, nome='Rua Nova Esperança', bairro='Primavera', descricao='Alaga sempre.')
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'criar_area': True, 'nivel_risco': 'medio'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        area = AreaRisco.objects.get(nome='Rua Nova Esperança')
        self.assertEqual(area.bairro, 'Primavera')
        self.assertEqual(area.nivel_risco, 'medio')
        self.assertEqual(area.latitude, relato.latitude)
        self.assertEqual(area.longitude, relato.longitude)
        data = timezone.localtime(relato.data_hora).strftime('%d/%m/%Y')
        self.assertIn(f'Criada a partir de relato de morador em {data}', area.descricao)
        relato.refresh_from_db()
        self.assertEqual(relato.area, area)

    def test_aprovar_criando_area_exige_nivel_de_risco(self):
        relato = self.criar()
        self.client.force_authenticate(self.admin)
        response = self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'criar_area': True}, format='json')
        self.assertEqual(response.status_code, 400)
        relato.refresh_from_db()
        self.assertEqual(relato.status, 'pendente')

    def test_aprovar_exige_uma_das_opcoes(self):
        relato = self.criar()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/aprovar/', {}, format='json').status_code, 400)
        ambos = {'area': self.area.pk, 'criar_area': True, 'nivel_risco': 'alto'}
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/aprovar/', ambos, format='json').status_code, 400)
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'area': 99999}, format='json').status_code, 400)

    def test_aprovar_nao_cria_medicao_nem_alerta(self):
        relato = self.criar(nivel_estimado='acima_joelho')
        self.client.force_authenticate(self.admin)
        self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'area': self.area.pk}, format='json')
        self.client.post(f'{self.URL}{self.criar().pk}/aprovar/', {'criar_area': True, 'nivel_risco': 'alto'}, format='json')
        self.assertFalse(RegistroMonitoramento.objects.exists())
        self.assertFalse(Alerta.objects.exists())

    def test_rejeitar_exige_motivo(self):
        relato = self.criar(autor=self.morador)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.post(f'{self.URL}{relato.pk}/rejeitar/', {'motivo': '  '}, format='json').status_code, 400)
        response = self.client.post(f'{self.URL}{relato.pk}/rejeitar/', {'motivo': 'Local fora de área de risco.'}, format='json')
        self.assertEqual(response.status_code, 200)
        relato.refresh_from_db()
        self.assertEqual(relato.status, 'rejeitado')
        self.assertEqual(relato.motivo_rejeicao, 'Local fora de área de risco.')
        self.assertEqual(relato.analisado_por, self.admin)

    def test_nao_aprova_nem_rejeita_relato_ja_analisado(self):
        aprovado = self.criar(status='aprovado', area=self.area)
        rejeitado = self.criar(status='rejeitado', motivo_rejeicao='x')
        self.client.force_authenticate(self.admin)
        for relato in (aprovado, rejeitado):
            r1 = self.client.post(f'{self.URL}{relato.pk}/aprovar/', {'area': self.area.pk}, format='json')
            r2 = self.client.post(f'{self.URL}{relato.pk}/rejeitar/', {'motivo': 'y'}, format='json')
            self.assertEqual(r1.status_code, 400)
            self.assertEqual(r2.status_code, 400)
            self.assertIn('já foi analisado', str(r1.data))
        rejeitado.refresh_from_db()
        self.assertEqual(rejeitado.motivo_rejeicao, 'x')

    def test_apagar_usuario_mantem_relato(self):
        relato = self.criar(autor=self.morador, status='aprovado')
        self.morador.delete()
        relato.refresh_from_db()
        self.assertIsNone(relato.autor)


class RelatoTelasTests(TestCase):
    """Menu e páginas dos relatos para visitante, usuário comum e administrador."""

    @classmethod
    def setUpTestData(cls):
        cls.comum = User.objects.create_user(username='comum@exemplo.com', password='senha123')
        cls.admin = User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)

    def html(self, url='/', usuario=None):
        if usuario:
            self.client.force_login(usuario)
        return self.client.get(url).content.decode()

    def menu(self, html):
        inicio = html.index('<nav class="menu">')
        return html[inicio:html.index('</nav>', inicio)]

    def test_menu_relatar_so_para_logado(self):
        self.assertNotIn('href="/relatar/"', self.menu(self.html()))
        self.assertIn('Relatar alagamento', self.menu(self.html(usuario=self.comum)))
        self.assertIn('href="/relatar/"', self.menu(self.html(usuario=self.admin)))

    def test_menu_relatos_so_para_admin(self):
        self.assertNotIn('href="/relatos/"', self.menu(self.html()))
        self.assertNotIn('href="/relatos/"', self.menu(self.html(usuario=self.comum)))
        self.assertIn('href="/relatos/"', self.menu(self.html(usuario=self.admin)))

    def test_contador_de_pendentes_no_menu_do_admin(self):
        RelatoAlagamento.objects.create(nome='Rua A', bairro='B', nivel_estimado='rua')
        RelatoAlagamento.objects.create(nome='Rua C', bairro='D', nivel_estimado='rua', status='aprovado')
        menu = self.menu(self.html(usuario=self.admin))
        self.assertIn('<span class="menu-badge"', menu)
        self.assertIn('>1</span>', menu)
        self.assertNotIn('menu-badge', self.menu(self.html(usuario=self.comum)))

    def test_pagina_relatar(self):
        self.assertRedirects(self.client.get('/relatar/'), '/login/?next=/relatar/')
        html = self.html('/relatar/', self.comum)
        self.assertIn('id="relatoForm"', html)
        self.assertIn('analisado pela Defesa Civil antes de aparecer no mapa', html)
        self.assertIn('Até o joelho (30 a 50 cm)', html)
        self.assertIn('Meus relatos', html)

    def test_pagina_de_analise_so_para_admin(self):
        self.assertRedirects(self.client.get('/relatos/'), '/login/?next=/relatos/')
        self.client.force_login(self.comum)
        response = self.client.get('/relatos/', follow=True)
        self.assertRedirects(response, '/')
        self.assertContains(response, 'Esta função é exclusiva da administração.')
        html = self.html('/relatos/', self.admin)
        self.assertIn('id="aprovarForm"', html)
        self.assertIn('id="rejeitarForm"', html)
        self.assertIn('Registrar medição nesta área', html)

    def test_mapa_convida_visitante_a_entrar_para_relatar(self):
        html = self.html()
        self.assertIn('Viu um alagamento?', html)
        self.assertIn('para relatar', html)
        self.assertIn('Relatos de moradores (últimos 7 dias)', html)
        self.assertIn('Relato de morador', html)

    def test_dashboard_card_de_relatos(self):
        html_comum = self.html('/dashboard/', self.comum)
        self.assertIn('id="total-relatos-aprovados"', html_comum)
        self.assertNotIn('id="total-relatos-pendentes"', html_comum)
        self.assertIn('id="total-relatos-pendentes"', self.html('/dashboard/', self.admin))


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RelatosDemoCommandTests(TestCase):

    def rodar(self):
        out = StringIO()
        call_command('relatos_demo', stdout=out)
        return out.getvalue()

    def setUp(self):
        call_command('cadastrar_areas_reais', stdout=StringIO())

    def test_cria_um_de_cada_status_marcado_como_simulado(self):
        self.rodar()
        relatos = RelatoAlagamento.objects.all()
        self.assertEqual(sorted(r.status for r in relatos), ['aprovado', 'pendente', 'rejeitado'])
        for relato in relatos:
            self.assertTrue(relato.descricao.startswith('Relato simulado para demonstração'))
        aprovado = relatos.get(status='aprovado')
        self.assertEqual(aprovado.area.nome, AREAS_REAIS[0]['nome'])
        self.assertTrue(relatos.get(status='rejeitado').motivo_rejeicao)

    def test_relatos_simulados_ficam_dentro_de_parauapebas(self):
        from .geocoding import dentro_de_parauapebas
        self.rodar()
        for relato in RelatoAlagamento.objects.all():
            self.assertTrue(dentro_de_parauapebas(relato.latitude, relato.longitude), relato.nome)

    def test_rodar_duas_vezes_nao_duplica(self):
        self.rodar()
        saida = self.rodar()
        self.assertEqual(RelatoAlagamento.objects.count(), 3)
        self.assertIn('0 relato(s) simulado(s) criado(s)', saida)

    def test_nao_cria_medicao_alerta_nem_email(self):
        User.objects.create_user('admin', email='admin@example.com', password='x', is_staff=True)
        with self.captureOnCommitCallbacks(execute=True):
            self.rodar()
        self.assertFalse(RegistroMonitoramento.objects.exists())
        self.assertFalse(Alerta.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_aprovado_aparece_no_mapa(self):
        self.rodar()
        response = APIClient().get('/api/relatos/', {'status': 'aprovado', 'dias': 7})
        self.assertEqual(response.data['count'], 1)
        self.assertNotIn('autor', str(response.data))

    def test_sem_areas_reais_avisa_e_nao_cria_aprovado(self):
        AreaRisco.objects.all().delete()
        saida = self.rodar()
        self.assertIn('cadastrar_areas_reais', saida)
        self.assertFalse(RelatoAlagamento.objects.filter(status='aprovado').exists())
        self.assertEqual(RelatoAlagamento.objects.count(), 2)


class ApagarRelatoTests(TestCase):
    """Apagar relato (página Relatos) e aviso ao apagar área com relatos no mapa."""

    @classmethod
    def setUpTestData(cls):
        cls.comum = User.objects.create_user(username='comum@exemplo.com', password='x')
        cls.admin = User.objects.create_user(username='admin@exemplo.com', password='x', is_staff=True)
        cls.area = AreaRisco.objects.create(nome='Rua do Rio', bairro='Liberdade', nivel_risco='alto',
                                            latitude=Decimal('-6.08'), longitude=Decimal('-49.91'))

    def setUp(self):
        self.client = APIClient()

    def criar(self, status='pendente', area=None, autor=None):
        return RelatoAlagamento.objects.create(
            nome='Rua X', bairro='União', latitude=Decimal('-6.07'), longitude=Decimal('-49.90'),
            nivel_estimado='joelho', status=status, area=area, autor=autor)

    def test_admin_apaga_relato_em_qualquer_status(self):
        self.client.force_authenticate(self.admin)
        for status in ('pendente', 'aprovado', 'rejeitado'):
            relato = self.criar(status=status, area=self.area if status == 'aprovado' else None)
            self.assertEqual(self.client.delete(f'/api/relatos/{relato.pk}/').status_code, 204, status)
        self.assertFalse(RelatoAlagamento.objects.exists())

    def test_apagar_relato_nao_apaga_a_area(self):
        relato = self.criar(status='aprovado', area=self.area)
        self.client.force_authenticate(self.admin)
        self.client.delete(f'/api/relatos/{relato.pk}/')
        self.assertTrue(AreaRisco.objects.filter(pk=self.area.pk).exists())

    def test_usuario_comum_e_visitante_nao_apagam(self):
        relato = self.criar(autor=self.comum)
        self.assertIn(self.client.delete(f'/api/relatos/{relato.pk}/').status_code, (401, 403))
        self.client.force_authenticate(self.comum)
        self.assertEqual(self.client.delete(f'/api/relatos/{relato.pk}/').status_code, 403)
        self.assertTrue(RelatoAlagamento.objects.filter(pk=relato.pk).exists())

    def test_filtro_por_area_conta_relatos_do_mapa(self):
        outra = AreaRisco.objects.create(nome='Outra', bairro='Centro')
        self.criar(status='aprovado', area=self.area)
        self.criar(status='aprovado', area=self.area)
        self.criar(status='aprovado', area=outra)
        self.criar(status='pendente', area=None)
        antigo = self.criar(status='aprovado', area=self.area)
        RelatoAlagamento.objects.filter(pk=antigo.pk).update(data_hora=timezone.now() - timedelta(days=8))
        # Mesma consulta que o mapa faz antes de apagar a área (visitante também pode ler)
        response = self.client.get('/api/relatos/', {'status': 'aprovado', 'dias': 7, 'area': self.area.pk})
        self.assertEqual(response.data['count'], 2)

    def test_apagar_area_mantem_relatos_aprovados_no_mapa(self):
        """O aviso do mapa é verdadeiro: o relato continua aprovado (sem área) e segue na camada."""
        relato = self.criar(status='aprovado', area=self.area)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.delete(f'/api/areas/{self.area.pk}/').status_code, 204)
        relato.refresh_from_db()
        self.assertIsNone(relato.area)
        self.assertEqual(relato.status, 'aprovado')
        ids = [r['id'] for r in self.client.get('/api/relatos/', {'status': 'aprovado', 'dias': 7}).data['results']]
        self.assertIn(relato.pk, ids)

    def test_pagina_relatos_tem_apagar_com_confirmacao(self):
        self.client.force_login(self.admin)
        html = self.client.get('/relatos/').content.decode()
        self.assertIn('data-apagar=', html)
        self.assertIn("titulo: 'Apagar relato?'", html)
        self.assertIn("method: 'DELETE'", html)

    def test_mapa_avisa_relatos_ao_apagar_area_e_recarrega_camada(self):
        self.client.force_login(self.admin)
        html = self.client.get('/').content.decode()
        self.assertIn('relato(s) de morador no mapa. Eles continuarão aparecendo por até 7 dias. '
                      'Para removê-los, use a página Relatos.', html)
        trecho = html[html.index("avisar('Área apagada.'") - 200:html.index("avisar('Área apagada.'")]
        self.assertIn('loadRelatos();', trecho)

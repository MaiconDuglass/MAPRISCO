from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class AuthViewsTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_index_page_returns_200(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_internal_pages_require_login(self):
        for name in ('dashboard', 'alertas', 'monitoramento'):
            url = reverse(name)
            response = self.client.get(url)
            self.assertRedirects(response, f"{reverse('login')}?next={url}")

    def test_internal_pages_return_200_when_logged_in(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        self.client.login(username='teste@exemplo.com', password='senha123')
        for name in ('dashboard', 'alertas'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_pages_use_local_libraries_without_cdn(self):
        """Chart.js, Bootstrap e Font Awesome vêm do próprio servidor: a tela funciona sem internet."""
        User.objects.create_user(username='teste@exemplo.com', password='senha123', is_staff=True)
        self.client.login(username='teste@exemplo.com', password='senha123')
        for name in ('index', 'dashboard', 'alertas', 'monitoramento'):
            html = self.client.get(reverse(name)).content.decode()
            self.assertNotIn('cdn.jsdelivr.net', html, name)
            self.assertNotIn('cdnjs.cloudflare.com', html, name)
            self.assertIn('vendor/fontawesome/css/all.min.css', html, name)

    def test_map_page_has_offline_notice(self):
        html = self.client.get(reverse('index')).content.decode()
        self.assertIn('id="mapOffline"', html)
        self.assertIn('Sem conexão com a internet', html)

    def test_login_redirects_to_next(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        response = self.client.post(f"{reverse('login')}?next=/alertas/", {
            'username': 'teste@exemplo.com',
            'password': 'senha123',
            'next': '/alertas/',
        })
        self.assertRedirects(response, reverse('alertas'))

    def test_login_ignores_external_next(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        response = self.client.post(reverse('login'), {
            'username': 'teste@exemplo.com',
            'password': 'senha123',
            'next': 'https://site-malicioso.com/',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_link_only_for_staff(self):
        User.objects.create_user(username='comum@exemplo.com', password='senha123')
        self.client.login(username='comum@exemplo.com', password='senha123')
        self.assertNotContains(self.client.get(reverse('dashboard')), 'href="/admin/"')

        User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)
        self.client.login(username='admin@exemplo.com', password='senha123')
        self.assertContains(self.client.get(reverse('dashboard')), 'href="/admin/"')

    def test_topbar_shows_first_name_and_open_alerts(self):
        from apps.monitoramento.models import AreaRisco, Alerta
        area = AreaRisco.objects.create(nome='Área', bairro='Centro')
        Alerta.objects.create(area=area, mensagem='Aberto', nivel='alto')
        Alerta.objects.create(area=area, mensagem='Resolvido', nivel='alto', resolvido=True)
        User.objects.create_user(username='joao@exemplo.com', password='senha123', first_name='JOÃO DA SILVA')
        self.client.login(username='joao@exemplo.com', password='senha123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Olá, João')
        self.assertContains(response, '<span class="notify-badge">1</span>', html=True)

    def test_user_without_name_shows_part_before_at(self):
        """Conta criada pelo createsuperuser (sem nome) não mostra o e-mail inteiro."""
        User.objects.create_superuser('fulano.silva@gmail.com', 'fulano.silva@gmail.com', 'senha123')
        self.client.login(username='fulano.silva@gmail.com', password='senha123')
        html = self.client.get(reverse('dashboard')).content.decode()
        self.assertIn('Olá, Fulano.silva', html)
        self.assertNotIn('Gmail.Com', html)

    def test_menu_has_cadastrar_area_link_for_admin(self):
        User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)
        self.client.login(username='admin@exemplo.com', password='senha123')
        response = self.client.get(reverse('index'))
        self.assertContains(response, 'href="/dashboard/?nova=1"')

    def test_login_requires_valid_credentials(self):
        user = User.objects.create_user(username='teste@exemplo.com', password='senha123')
        response = self.client.post(reverse('login'), {
            'username': 'teste@exemplo.com',
            'password': 'senha123',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_login_rejects_wrong_credentials(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        response = self.client.post(reverse('login'), {
            'username': 'teste@exemplo.com',
            'password': 'errada',
        })
        self.assertEqual(response.status_code, 200)

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'João da Silva',
            'username': 'joao@exemplo.com',
            'password1': 'SenhaForte#2026',
            'password2': 'SenhaForte#2026',
            'terms': 'on',
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='joao@exemplo.com')
        self.assertEqual(user.first_name, 'João da Silva')
        self.assertEqual(user.email, 'joao@exemplo.com')

    def test_register_requires_terms(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'Ana',
            'username': 'ana@exemplo.com',
            'password1': 'SenhaForte#2026',
            'password2': 'SenhaForte#2026',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='ana@exemplo.com').exists())

    def test_register_saves_email_lowercase_and_blocks_case_duplicates(self):
        dados = {
            'full_name': 'Pedro',
            'username': 'Pedro.Silva@Exemplo.COM',
            'password1': 'SenhaForte#2026',
            'password2': 'SenhaForte#2026',
            'terms': 'on',
        }
        self.client.post(reverse('register'), dados)
        self.assertTrue(User.objects.filter(username='pedro.silva@exemplo.com').exists())

        self.client.logout()
        dados['username'] = 'pedro.silva@exemplo.com'
        response = self.client.post(reverse('register'), dados)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(username__iexact='pedro.silva@exemplo.com').count(), 1)

    def test_login_ignores_email_case(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        response = self.client.post(reverse('login'), {
            'username': 'TESTE@Exemplo.com',
            'password': 'senha123',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_register_requires_matching_passwords(self):
        response = self.client.post(reverse('register'), {
            'full_name': 'Maria',
            'username': 'maria@exemplo.com',
            'password1': 'abc123',
            'password2': 'diferente',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='maria@exemplo.com').exists())

    def test_logout_redirects_to_index(self):
        User.objects.create_user(username='teste@exemplo.com', password='senha123')
        self.client.login(username='teste@exemplo.com', password='senha123')
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('index'))

# Botão "Registrar medição" do cartão da área no mapa (o texto também aparece num comentário do CSS)
BOTAO_REGISTRAR_MEDICAO = 'id="infoMedirLink"'


class PerfisTests(TestCase):
    """O que cada perfil vê: visitante, usuário comum e administrador (is_staff)."""

    MENU = {
        'Dashboard': 'href="/dashboard/"',
        'Cadastrar Área': 'href="/dashboard/?nova=1"',
        'Alertas': 'href="/alertas/"',
        'Monitoramento': 'href="/monitoramento/"',
        'Usuários': 'href="/admin/"',
    }

    def setUp(self):
        User.objects.create_user(username='comum@exemplo.com', password='senha123')
        User.objects.create_user(username='admin@exemplo.com', password='senha123', is_staff=True)

    def entrar(self, perfil):
        self.client.login(username=f'{perfil}@exemplo.com', password='senha123')

    def menu(self, html):
        """Itens do menu lateral presentes na página."""
        inicio = html.index('<nav class="menu">')
        nav = html[inicio:html.index('</nav>', inicio)]
        itens = ['Mapa'] if 'href="/"' in nav else []
        return itens + [nome for nome, href in self.MENU.items() if href in nav]

    # Menu lateral
    def test_menu_do_visitante_so_tem_mapa(self):
        html = self.client.get(reverse('index')).content.decode()
        self.assertEqual(self.menu(html), ['Mapa'])
        self.assertIn('Entrar', html)
        self.assertIn('Criar conta', html)

    def test_menu_do_usuario_comum(self):
        self.entrar('comum')
        html = self.client.get(reverse('index')).content.decode()
        self.assertEqual(self.menu(html), ['Mapa', 'Dashboard', 'Alertas'])

    def test_menu_do_admin_tem_tudo(self):
        self.entrar('admin')
        html = self.client.get(reverse('index')).content.decode()
        self.assertEqual(self.menu(html), ['Mapa', 'Dashboard', 'Cadastrar Área', 'Alertas', 'Monitoramento', 'Usuários'])

    # Sino de alertas
    def test_visitante_nao_ve_sino_de_alertas(self):
        from apps.monitoramento.models import AreaRisco, Alerta
        area = AreaRisco.objects.create(nome='Área', bairro='Centro')
        Alerta.objects.create(area=area, mensagem='Aberto', nivel='critico')
        html = self.client.get(reverse('index')).content.decode()
        self.assertNotIn('class="notify"', html)
        self.assertNotIn('<span class="notify-badge">', html)

    # Mapa: botão "Registrar medição"
    def test_visitante_nao_ve_registrar_medicao_no_mapa(self):
        self.assertNotContains(self.client.get(reverse('index')), BOTAO_REGISTRAR_MEDICAO)

    def test_usuario_comum_nao_ve_registrar_medicao_nem_editar_no_mapa(self):
        self.entrar('comum')
        response = self.client.get(reverse('index'))
        self.assertNotContains(response, BOTAO_REGISTRAR_MEDICAO)
        self.assertNotContains(response, 'id="editArea"')
        self.assertNotContains(response, 'id="deleteArea"')

    def test_admin_ve_registrar_medicao_editar_e_apagar_no_mapa(self):
        self.entrar('admin')
        response = self.client.get(reverse('index'))
        self.assertContains(response, BOTAO_REGISTRAR_MEDICAO)
        self.assertContains(response, 'id="editArea"')
        self.assertContains(response, 'id="deleteArea"')

    # Monitoramento (página só do administrador)
    def test_usuario_comum_e_barrado_no_monitoramento(self):
        self.entrar('comum')
        response = self.client.get(reverse('monitoramento'), follow=True)
        self.assertRedirects(response, reverse('index'))
        self.assertContains(response, 'Esta função é exclusiva da administração.')

    def test_admin_acessa_monitoramento(self):
        self.entrar('admin')
        response = self.client.get(reverse('monitoramento'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="saveMedicaoBtn"')

    # Dashboard
    def test_dashboard_do_usuario_comum_e_so_consulta(self):
        self.entrar('comum')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'id="openCreateArea"')
        self.assertNotContains(response, 'Cadastrar Área de Risco')
        self.assertNotContains(response, 'id="areaForm"')
        self.assertNotContains(response, 'href="/monitoramento/"')
        self.assertContains(response, 'id="total-areas"')

    def test_dashboard_do_admin_tem_cadastro_de_area(self):
        self.entrar('admin')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'id="openCreateArea"')
        self.assertContains(response, 'Cadastrar Área de Risco')
        self.assertContains(response, 'id="areaForm"')

    def test_usuario_comum_e_barrado_no_cadastro_pela_url(self):
        self.entrar('comum')
        response = self.client.get(reverse('dashboard') + '?nova=1', follow=True)
        self.assertRedirects(response, reverse('index'))
        self.assertContains(response, 'Esta função é exclusiva da administração.')

    def test_admin_abre_cadastro_pela_url(self):
        self.entrar('admin')
        self.assertEqual(self.client.get(reverse('dashboard') + '?nova=1').status_code, 200)

    # Alertas
    def test_alertas_so_admin_pode_resolver(self):
        self.entrar('comum')
        self.assertContains(self.client.get(reverse('alertas')), 'const PODE_RESOLVER = false;')
        self.entrar('admin')
        self.assertContains(self.client.get(reverse('alertas')), 'const PODE_RESOLVER = true;')

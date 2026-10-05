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
        for name in ('dashboard', 'alertas', 'monitoramento'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)

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

    def test_menu_has_cadastrar_area_link(self):
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
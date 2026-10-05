from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse


class AuthViewsTests(TestCase):

    def setUp(self):
        self.client = Client()

    def test_index_page_returns_200(self):
        response = self.client.get(reverse('index'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_returns_200(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_alertas_and_monitoramento_pages_return_200(self):
        self.assertEqual(self.client.get(reverse('alertas')).status_code, 200)
        self.assertEqual(self.client.get(reverse('monitoramento')).status_code, 200)

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
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='joao@exemplo.com')
        self.assertEqual(user.first_name, 'João da Silva')
        self.assertEqual(user.email, 'joao@exemplo.com')

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
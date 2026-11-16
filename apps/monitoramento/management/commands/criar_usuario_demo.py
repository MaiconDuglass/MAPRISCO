"""
Cria (ou atualiza) o usuário comum de demonstração, para mostrar a tela de usuário.

    E-mail (login): usuario.demo@maprisco.local
    Nome:           Usuário Demo
    Perfil:         usuário comum (NÃO é administrador)

A senha é digitada no terminal (não fica no código). Se o usuário já existir,
a senha e o nome são atualizados e ele volta a ser usuário comum.

Uso:
    python manage.py criar_usuario_demo
"""
import getpass

from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

EMAIL_DEMO = 'usuario.demo@maprisco.local'
NOME_DEMO = 'Usuário Demo'


class Command(BaseCommand):
    help = 'Cria o usuário comum de demonstração (usuario.demo@maprisco.local), pedindo a senha no terminal.'

    def pedir_senha(self):
        senha = getpass.getpass('Senha do usuário demo: ')
        confirmacao = getpass.getpass('Repita a senha: ')
        if not senha:
            raise CommandError('A senha não pode ficar em branco.')
        if senha != confirmacao:
            raise CommandError('As senhas não conferem.')
        return senha

    def handle(self, *args, **options):
        senha = self.pedir_senha()

        user = User.objects.filter(username__iexact=EMAIL_DEMO).first() or User(username=EMAIL_DEMO)
        try:
            validate_password(senha, user)
        except ValidationError as erro:
            raise CommandError('Senha fraca: ' + ' '.join(erro.messages))

        criado = user.pk is None
        user.email = EMAIL_DEMO
        user.first_name = NOME_DEMO
        user.is_staff = False
        user.is_superuser = False
        user.is_active = True
        user.set_password(senha)
        user.save()

        acao = 'criado' if criado else 'atualizado'
        self.stdout.write(self.style.SUCCESS(
            f'Usuário demo {acao}: {EMAIL_DEMO} (usuário comum, sem acesso de administrador).'
        ))

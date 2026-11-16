from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils.http import url_has_allowed_host_and_scheme
from functools import wraps

from .forms import RegistrationForm

MENSAGEM_SO_ADMIN = 'Esta função é exclusiva da administração.'


def admin_required(view):
    """
    Página exclusiva do administrador (is_staff).
    Visitante: vai para o login. Usuário comum: volta para o mapa com um aviso.
    """
    @wraps(view)
    @login_required
    def _view(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.info(request, MENSAGEM_SO_ADMIN)
            return redirect('index')
        return view(request, *args, **kwargs)
    return _view


def index(request):
    return render(request, 'index.html')

@login_required
def dashboard(request):
    # ?nova=1 abre o cadastro de área, que é só do administrador
    if 'nova' in request.GET and not request.user.is_staff:
        messages.info(request, MENSAGEM_SO_ADMIN)
        return redirect('index')
    return render(request, 'dashboard.html')

@login_required
def alertas(request):
    return render(request, 'alertas.html')

@login_required
def relatar(request):
    """Morador relata um alagamento (analisado pela Defesa Civil antes de aparecer no mapa)."""
    from apps.monitoramento.models import RelatoAlagamento
    return render(request, 'relatar.html', {'niveis_estimados': RelatoAlagamento.NIVEL_ESTIMADO_CHOICES})

@admin_required
def relatos(request):
    """Análise dos relatos de alagamento pelo administrador."""
    from apps.monitoramento.models import AreaRisco
    return render(request, 'relatos.html', {'niveis_risco': AreaRisco.NIVEL_RISCO_CHOICES})

@admin_required
def monitoramento(request):
    return render(request, 'monitoramento.html')

def termos(request):
    return render(request, 'termos.html')

def privacidade(request):
    return render(request, 'privacidade.html')

def login_view(request):
    if request.method == 'POST':
        username = (request.POST.get('email') or request.POST.get('username') or '').strip()
        password = request.POST.get('password')
        # Login sem diferenciar maiúsculas/minúsculas no e-mail (inclusive contas antigas)
        existing = User.objects.filter(username__iexact=username).values_list('username', flat=True).first()
        if existing:
            username = existing
        remember_me = request.POST.get('rememberMe') == 'on'

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard')
        messages.error(request, 'Credenciais inválidas')

    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

def logout_view(request):
    # Clear any pending messages to avoid showing them after logout
    from django.contrib.messages import get_messages
    storage = get_messages(request)
    storage.used = True
    logout(request)
    return redirect('index')
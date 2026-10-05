from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib import messages
from .forms import RegistrationForm

def index(request):
    return render(request, 'index.html')

def dashboard(request):
    return render(request, 'dashboard.html')

def alertas(request):
    return render(request, 'alertas.html')

def monitoramento(request):
    return render(request, 'monitoramento.html')

def termos(request):
    return render(request, 'termos.html')

def privacidade(request):
    return render(request, 'privacidade.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('email') or request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('rememberMe') == 'on'

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if remember_me:
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
            else:
                request.session.set_expiry(0)
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
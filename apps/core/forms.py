from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class RegistrationForm(UserCreationForm):
    full_name = forms.CharField(
        label='Nome Completo',
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'Nome Completo',
            }
        )
    )
    username = forms.EmailField(
        label='E-mail',
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': 'form-control',
                'placeholder': 'E-mail',
            }
        )
    )
    password1 = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '••••••••',
            }
        ),
    )
    password2 = forms.CharField(
        label='Confirme a Senha',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control',
                'placeholder': '••••••••',
            }
        ),
    )

    terms = forms.BooleanField(
        required=True,
        error_messages={'required': 'Você deve concordar com os Termos de Serviço e a Política de Privacidade.'},
    )

    class Meta:
        model = User
        fields = ('full_name', 'username', 'password1', 'password2')

    def clean_username(self):
        # E-mail sempre em minúsculas: "Maria@Exemplo.com" e "maria@exemplo.com" são a mesma conta
        email = self.cleaned_data['username'].strip().lower()
        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        if full_name:
            user.first_name = full_name
        user.email = self.cleaned_data['username']
        if commit:
            user.save()
        return user

const passwordInput = document.getElementById('password');
const togglePasswordBtn = document.getElementById('togglePassword');

const confirmPasswordInput = document.getElementById('confirmPassword');
const toggleConfirmPasswordBtn = document.getElementById('toggleConfirmPassword');

function toggleVisibility(input, button) {
  const isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  button.classList.toggle('active', isPassword);
}

if (togglePasswordBtn) {
  togglePasswordBtn.addEventListener('click', function (e) {
    e.preventDefault();
    toggleVisibility(passwordInput, this);
  });
}

if (toggleConfirmPasswordBtn) {
  toggleConfirmPasswordBtn.addEventListener('click', function (e) {
    e.preventDefault();
    toggleVisibility(confirmPasswordInput, this);
  });
}

const registerForm = document.getElementById('registerForm');
if (registerForm) {
  registerForm.addEventListener('submit', function (e) {
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const terms = document.getElementById('terms').checked;
    const clientError = document.getElementById('clientError');

    // Mostra o erro no próprio formulário (em vez do alert do navegador)
    function mostrarErro(mensagem) {
      e.preventDefault();
      clientError.innerHTML = '';
      const item = document.createElement('li');
      item.textContent = mensagem;
      clientError.appendChild(item);
      clientError.hidden = false;
    }

    clientError.hidden = true;

    if (password !== confirmPassword) {
      mostrarErro('As senhas não correspondem.');
      return;
    }

    if (!terms) {
      mostrarErro('Você deve concordar com os Termos de Serviço e a Política de Privacidade.');
      return;
    }
  });
}

// Links de Termos e Privacidade navegam para páginas reais do sistema.
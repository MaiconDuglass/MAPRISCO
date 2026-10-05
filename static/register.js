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

    if (password !== confirmPassword) {
      e.preventDefault();
      alert('As senhas não correspondem!');
      return;
    }

    if (!terms) {
      e.preventDefault();
      alert('Você deve concordar com os Termos de Serviço');
      return;
    }
  });
}

// Links de Termos e Privacidade navegam para páginas reais do sistema.
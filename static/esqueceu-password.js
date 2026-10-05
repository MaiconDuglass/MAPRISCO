var newPasswordInput = document.getElementById('id_new_password1');
var confirmNewPasswordInput = document.getElementById('id_new_password2');
var toggleNewPasswordBtn = document.getElementById('toggleNewPassword');
var toggleConfirmNewPasswordBtn = document.getElementById('toggleConfirmNewPassword');

function toggleVisibility(input, button) {
  var isPassword = input.type === 'password';
  input.type = isPassword ? 'text' : 'password';
  button.classList.toggle('active', isPassword);
}

if (toggleNewPasswordBtn && newPasswordInput) {
  toggleNewPasswordBtn.addEventListener('click', function (e) {
    e.preventDefault();
    toggleVisibility(newPasswordInput, this);
  });
}

if (toggleConfirmNewPasswordBtn && confirmNewPasswordInput) {
  toggleConfirmNewPasswordBtn.addEventListener('click', function (e) {
    e.preventDefault();
    toggleVisibility(confirmNewPasswordInput, this);
  });
}
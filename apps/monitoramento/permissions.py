from rest_framework.permissions import BasePermission, SAFE_METHODS


def _is_staff(user):
    return bool(user and user.is_authenticated and user.is_staff)


class CidadaoCadastraAdminGerencia(BasePermission):
    """
    Leitura: pública.
    Cadastro (POST): qualquer usuário logado.
    Alterar ou apagar (PUT, PATCH, DELETE): somente administradores (Defesa Civil).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if request.method == 'POST':
            return bool(request.user and request.user.is_authenticated)
        return _is_staff(request.user)


class SomenteAdminAltera(BasePermission):
    """
    Leitura: pública.
    Qualquer alteração (inclusive resolver alertas): somente administradores.
    Os alertas são gerados automaticamente pelo sistema a partir das medições.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return _is_staff(request.user)

from rest_framework.permissions import BasePermission, SAFE_METHODS


def eh_administrador(user):
    """True se o usuário está logado e é administrador (is_staff, Defesa Civil)."""
    return bool(user and user.is_authenticated and user.is_staff)


class LeituraPublicaEscritaSomenteAdmin(BasePermission):
    """
    Leitura (GET, HEAD, OPTIONS): pública, inclusive para visitantes sem login.
    Cadastrar, alterar, apagar ou resolver (POST, PUT, PATCH, DELETE): somente administradores.

    Usada nas áreas de risco, nas medições e nos alertas. Assim um usuário comum
    não consegue criar áreas falsas nem registrar medições que gerariam alertas
    críticos falsos (e e-mails para a Defesa Civil).
    """

    message = 'Esta função é exclusiva da administração.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return eh_administrador(request.user)


class RelatoPermissao(BasePermission):
    """
    Relatos de alagamento (participação cidadã):
    - Ler: público (o que cada perfil enxerga é filtrado no ViewSet).
    - Enviar relato (POST na lista): qualquer usuário logado.
    - Aprovar, rejeitar, alterar ou apagar: somente administradores.
    """

    message = 'Esta função é exclusiva da administração.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if getattr(view, 'action', None) == 'create':
            return bool(request.user and request.user.is_authenticated)
        return eh_administrador(request.user)

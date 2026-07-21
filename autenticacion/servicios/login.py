"""Tabla CRC 16 — Login (lógica de acceso)."""


class Login:
    """Autenticación, redirección por rol y registro de intentos fallidos."""

    PANEL_ADMIN = '/admin/citas/dashboard/'
    PANEL_OFICIAL = '/citas/oficial/'
    PANEL_CAPTURISTA = '/citas/capturista/'
    LOGIN_URL = '/admin/login/'

    @classmethod
    def url_panel_para_usuario(cls, user):
        if user.is_superuser or user.groups.filter(name='Administrador').exists():
            return cls.PANEL_ADMIN
        if user.groups.filter(name='oficial').exists():
            return cls.PANEL_OFICIAL
        if user.groups.filter(name='Capturista').exists():
            return cls.PANEL_CAPTURISTA
        return cls.LOGIN_URL

    @classmethod
    def mensaje_intento_fallido(cls, username):
        return (
            f"Intento fallido de inicio de sesión ({username}). "
            "Contraseña incorrecta o cuenta inactiva."
        )

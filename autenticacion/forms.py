from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from autenticacion.servicios.login import Login


class FormularioAccesoPanel(AuthenticationForm):
    """Formulario de Django auth/admin que reutiliza el bloqueo del panel."""

    def clean(self):
        resultado = getattr(self.request, 'resultado_acceso_panel', None)
        if resultado is None:
            username = self.cleaned_data.get('username')
            password = self.cleaned_data.get('password')
            if username is not None and password:
                resultado = Login.autenticar_panel(self.request, username, password)
                self.request.resultado_acceso_panel = resultado
        if resultado is None:
            return super().clean()
        if resultado.usuario is None:
            raise ValidationError(resultado.mensaje, code='invalid_login')
        self.user_cache = resultado.usuario
        self.confirm_login_allowed(resultado.usuario)
        return self.cleaned_data

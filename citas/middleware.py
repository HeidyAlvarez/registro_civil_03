from django.contrib.auth import logout
from django.shortcuts import redirect
from .utils import set_current_request
from .servicios.bitacora import Bitacora

class RequestAuditMiddleware:
    """Guarda el request actual para auditoría y renueva la sesión en cada petición."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        response = self.get_response(request)
        from .auditoria import registrar_movimiento_generico
        try:
            registrar_movimiento_generico(request)
        except Exception:
            pass
        return response


class SessionTimeoutMiddleware:
    """Cierra sesión tras inactividad definida en SESSION_COOKIE_AGE."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ultima = request.session.get('_ultima_actividad')
            from django.conf import settings
            from django.utils import timezone
            ahora = timezone.now().timestamp()
            limite = getattr(settings, 'SESSION_COOKIE_AGE', 1800)
            if ultima and (ahora - ultima) > limite:
                if Bitacora.usuario_auditado(request.user):
                    Bitacora.registrar(
                        request,
                        'INFO',
                        f"[{Bitacora.rol_usuario(request.user)}] {request.user.username} — sesión cerrada por inactividad.",
                    )
                logout(request)
                return redirect('/admin/login/?session_expired=1')
            request.session['_ultima_actividad'] = ahora
        return self.get_response(request)

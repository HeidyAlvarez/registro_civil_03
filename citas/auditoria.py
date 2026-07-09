"""Registro centralizado en bitácora para personal autorizado."""

from django.contrib.auth import get_user_model

from .models import BitacoraAuditoria
from .utils import obtener_ip

GRUPOS_AUDITADOS = ('Capturista', 'oficial', 'Administrador')

# Polling / lectura — no generan entrada genérica en bitácora
RUTAS_LECTURA_EXCLUIDAS = (
    '/citas/api/dashboard/',
    '/citas/api/citas/',
    '/citas/api/horarios/',
    '/citas/api/tramites/',
    '/admin/jsi18n/',
    '/static/',
    '/media/',
)


def usuario_auditado(user):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return user.groups.filter(name__in=GRUPOS_AUDITADOS).exists()


def rol_usuario(user):
    if user.is_superuser:
        return 'Administrador'
    nombres = set(user.groups.values_list('name', flat=True))
    for grupo in ('Administrador', 'oficial', 'Capturista'):
        if grupo in nombres:
            return grupo
    if user.is_staff:
        return 'Staff'
    return 'Usuario'


def marcar_auditado(request):
    if request is not None:
        request._audit_logged = True


def ya_auditado(request):
    return getattr(request, '_audit_logged', False)


def registrar_evento(request, accion, descripcion, usuario=None):
    if request is not None:
        marcar_auditado(request)
    user = usuario
    if user is None and request is not None and getattr(request.user, 'is_authenticated', False):
        if request.user.is_authenticated:
            user = request.user
    BitacoraAuditoria.objects.create(
        usuario=user,
        accion=accion,
        descripcion=descripcion,
        ip_direccion=obtener_ip(request) if request else None,
    )


def registrar_log(request, accion, descripcion):
    if not usuario_auditado(request.user):
        return
    registrar_evento(request, accion, descripcion)


def registrar_log_seguridad(request, accion, descripcion, username=None):
    usuario = None
    if username:
        usuario = get_user_model().objects.filter(username=username).first()
    registrar_evento(request, accion, descripcion, usuario=usuario)


def registrar_movimiento_generico(request):
    """Respaldo: registra POST/PUT/PATCH/DELETE no capturados en vistas específicas."""
    if not usuario_auditado(request.user):
        return
    if ya_auditado(request):
        return
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return
    path = request.path
    if not (path.startswith('/citas/') or path.startswith('/admin/')):
        return
    if any(path.startswith(excl) for excl in RUTAS_LECTURA_EXCLUIDAS):
        return
    rol = rol_usuario(request.user)
    registrar_evento(
        request,
        'INFO',
        f"[{rol}] {request.user.username} — {request.method} {path}",
    )

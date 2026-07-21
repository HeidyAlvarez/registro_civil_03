"""Registro centralizado en bitácora — delega en la clase Bitacora (capa OO)."""

from citas.servicios.bitacora import Bitacora

GRUPOS_AUDITADOS = Bitacora.GRUPOS_AUDITADOS
RUTAS_LECTURA_EXCLUIDAS = Bitacora.RUTAS_LECTURA_EXCLUIDAS

usuario_auditado = Bitacora.usuario_auditado
rol_usuario = Bitacora.rol_usuario


def marcar_auditado(request):
    if request is not None:
        request._audit_logged = True


def ya_auditado(request):
    return getattr(request, '_audit_logged', False)


def registrar_evento(request, accion, descripcion, usuario=None):
    Bitacora.registrar(request, accion, descripcion, usuario=usuario)


def registrar_log(request, accion, descripcion):
    Bitacora.registrar_si_autorizado(request, accion, descripcion)


def registrar_log_seguridad(request, accion, descripcion, username=None):
    Bitacora.registrar_seguridad(request, accion, descripcion, username=username)


def registrar_movimiento_generico(request):
    Bitacora.registrar_movimiento_generico(request)

"""Tabla CRC 27 — Bitácora (lógica de negocio)."""

from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

from citas.models import BitacoraAuditoria
from citas.utils import obtener_ip


class Bitacora:
    """Crea y consulta registros inmutables de auditoría."""

    GRUPOS_AUDITADOS = ('Capturista', 'oficial', 'Administrador')
    RUTAS_LECTURA_EXCLUIDAS = (
        '/citas/api/dashboard/',
        '/citas/api/citas/',
        '/citas/api/horarios/',
        '/citas/api/tramites/',
        '/admin/jsi18n/',
        '/static/',
        '/media/',
    )

    @classmethod
    def usuario_auditado(cls, user):
        if not user or not user.is_authenticated:
            return False
        if user.is_staff or user.is_superuser:
            return True
        return user.groups.filter(name__in=cls.GRUPOS_AUDITADOS).exists()

    @classmethod
    def rol_usuario(cls, user):
        if user.is_superuser:
            return 'Administrador'
        nombres = set(user.groups.values_list('name', flat=True))
        for grupo in ('Administrador', 'oficial', 'Capturista'):
            if grupo in nombres:
                return grupo
        if user.is_staff:
            return 'Staff'
        return 'Usuario'

    @classmethod
    def registrar(cls, request, accion, descripcion, usuario=None):
        if request is not None:
            request._audit_logged = True
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

    @classmethod
    def registrar_si_autorizado(cls, request, accion, descripcion):
        if cls.usuario_auditado(request.user):
            cls.registrar(request, accion, descripcion)

    @classmethod
    def registrar_seguridad(cls, request, accion, descripcion, username=None):
        usuario = None
        if username:
            usuario = get_user_model().objects.filter(username=username).first()
        cls.registrar(request, accion, descripcion, usuario=usuario)

    @classmethod
    def registrar_movimiento_generico(cls, request):
        if not cls.usuario_auditado(request.user):
            return
        if getattr(request, '_audit_logged', False):
            return
        if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
            return
        path = request.path
        if not (path.startswith('/citas/') or path.startswith('/admin/')):
            return
        if any(path.startswith(excl) for excl in cls.RUTAS_LECTURA_EXCLUIDAS):
            return
        rol = cls.rol_usuario(request.user)
        cls.registrar(
            request,
            'INFO',
            f"[{rol}] {request.user.username} — {request.method} {path}",
        )

    @classmethod
    def consultar(cls, q='', accion='', usuario='', page=1, por_pagina=50):
        try:
            page = int(page) if page else 1
        except (TypeError, ValueError):
            page = 1
        qs = BitacoraAuditoria.objects.select_related('usuario').order_by('-fecha_hora')
        if q:
            qs = qs.filter(
                Q(descripcion__icontains=q)
                | Q(usuario__username__icontains=q)
                | Q(ip_direccion__icontains=q)
            )
        if accion:
            qs = qs.filter(accion=accion)
        if usuario == '__none__':
            qs = qs.filter(usuario__isnull=True)
        elif usuario:
            qs = qs.filter(usuario__username=usuario)
        paginator = Paginator(qs, por_pagina)
        registros = paginator.get_page(page)
        usuarios = (
            BitacoraAuditoria.objects.exclude(usuario__isnull=True)
            .values_list('usuario__username', flat=True)
            .distinct()
            .order_by('usuario__username')
        )
        return registros, list(usuarios)

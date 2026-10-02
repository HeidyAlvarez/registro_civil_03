"""Tabla CRC 16 — Login (lógica de acceso)."""

from datetime import timedelta

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone

from autenticacion.models import IntentoAccesoPanel


class ResultadoAcceso:
    """Resultado de un intento de entrar a un panel interno."""

    def __init__(self, usuario=None, mensaje='', bloqueado=False):
        self.usuario = usuario
        self.mensaje = mensaje
        self.bloqueado = bloqueado


class Login:
    """Autenticación, redirección por rol y bloqueo temporal de intentos."""

    PANEL_ADMIN = '/admin/citas/dashboard/'
    PANEL_OFICIAL = '/citas/oficial/'
    PANEL_CAPTURISTA = '/citas/capturista/'
    LOGIN_URL = '/admin/login/'

    MENSAJE_CREDENCIALES_INVALIDAS = 'Hay un error en el usuario y/o contraseña'
    MENSAJE_BLOQUEO = 'El acceso está temporalmente bloqueado durante 15 minutos.'
    MAX_FALLOS = 3
    VENTANA = timedelta(minutes=15)

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
    def mensaje_intento_fallido(cls, username, bloqueado=False):
        if bloqueado:
            return f'Acceso al panel bloqueado temporalmente ({username}).'
        return f'Intento fallido de inicio de sesión ({username}).'

    @classmethod
    def normalizar_usuario(cls, username):
        return (username or '').strip().casefold()[:300]

    @classmethod
    def ip_origen(cls, request):
        if request is None:
            return '0.0.0.0'
        ip = (request.META.get('REMOTE_ADDR') or '').strip()
        return (ip or '0.0.0.0')[:45]

    @classmethod
    def autenticar_panel(cls, request, username, password):
        """Valida credenciales de panel sin revelar cuál dato falló.

        La cuenta se bloquea cuando hay más de tres fallos. La clave es el
        usuario normalizado y la IP de origen, así un intento no bloquea
        otras cuentas ni el mismo usuario desde otra dirección.
        """
        username_visible = (username or '').strip()
        username_norm = cls.normalizar_usuario(username_visible)
        ip = cls.ip_origen(request)
        ahora = timezone.now()

        with transaction.atomic():
            intento = cls._obtener_intento(username_norm, ip)
            cls._reiniciar_si_expiro(intento, ahora)
            if cls._esta_bloqueado(intento, ahora):
                cls._auditar(request, username_visible, bloqueado=True)
                return ResultadoAcceso(mensaje=cls.MENSAJE_BLOQUEO, bloqueado=True)

        user = authenticate(request, username=username_visible, password=password or '')
        if user is not None and not user.is_active:
            user = None

        with transaction.atomic():
            intento = cls._obtener_intento(username_norm, ip)
            ahora = timezone.now()
            cls._reiniciar_si_expiro(intento, ahora)
            if cls._esta_bloqueado(intento, ahora):
                cls._auditar(request, username_visible, bloqueado=True)
                return ResultadoAcceso(mensaje=cls.MENSAJE_BLOQUEO, bloqueado=True)
            if user is None:
                return cls._registrar_fallo(intento, request, username_visible, ahora)
            intento.intentos_fallidos = 0
            intento.bloqueado_hasta = None
            intento.ultimo_intento = None
            intento.save(update_fields=['intentos_fallidos', 'bloqueado_hasta', 'ultimo_intento'])
            return ResultadoAcceso(usuario=user)

    @classmethod
    def _obtener_intento(cls, username_norm, ip):
        intento, _creado = IntentoAccesoPanel.objects.get_or_create(
            username_normalizado=username_norm,
            direccion_ip=ip,
        )
        return intento

    @classmethod
    def _esta_bloqueado(cls, intento, ahora):
        return intento.bloqueado_hasta is not None and intento.bloqueado_hasta > ahora

    @classmethod
    def _reiniciar_si_expiro(cls, intento, ahora):
        bloqueo_vencido = (
            intento.bloqueado_hasta is not None and intento.bloqueado_hasta <= ahora
        )
        ventana_inactiva = (
            intento.bloqueado_hasta is None
            and intento.intentos_fallidos
            and intento.ultimo_intento is not None
            and ahora - intento.ultimo_intento >= cls.VENTANA
        )
        if not bloqueo_vencido and not ventana_inactiva:
            return
        intento.intentos_fallidos = 0
        intento.bloqueado_hasta = None
        intento.ultimo_intento = None
        intento.save(update_fields=['intentos_fallidos', 'bloqueado_hasta', 'ultimo_intento'])

    @classmethod
    def _registrar_fallo(cls, intento, request, username_visible, ahora):
        intento.intentos_fallidos += 1
        intento.ultimo_intento = ahora
        bloqueado = intento.intentos_fallidos > cls.MAX_FALLOS
        intento.bloqueado_hasta = ahora + cls.VENTANA if bloqueado else None
        intento.save(update_fields=['intentos_fallidos', 'bloqueado_hasta', 'ultimo_intento'])
        cls._auditar(request, username_visible, bloqueado=bloqueado)
        if bloqueado:
            return ResultadoAcceso(mensaje=cls.MENSAJE_BLOQUEO, bloqueado=True)
        return ResultadoAcceso(mensaje=cls.MENSAJE_CREDENCIALES_INVALIDAS)

    @classmethod
    def _auditar(cls, request, username, bloqueado):
        if not username:
            return
        from citas.auditoria import registrar_log_seguridad

        registrar_log_seguridad(
            request,
            'ACCESO_DENEGADO',
            cls.mensaje_intento_fallido(username, bloqueado=bloqueado),
            username=username,
        )

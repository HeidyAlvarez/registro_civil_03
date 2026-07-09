from django.contrib.auth.signals import user_logged_out, user_logged_in
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Tramite, BitacoraAuditoria
from .utils import get_current_request, obtener_ip
from .auditoria import registrar_evento, usuario_auditado, rol_usuario


@receiver(user_logged_out)
def auditar_cierre_sesion(sender, request, user, **kwargs):
    if request and user and usuario_auditado(user):
        registrar_evento(
            request,
            'INFO',
            f"[{rol_usuario(user)}] {user.username} — cierre de sesión.",
            usuario=user,
        )


@receiver(user_logged_in)
def auditar_inicio_sesion(sender, request, user, **kwargs):
    if request and user and usuario_auditado(user):
        registrar_evento(
            request,
            'LOGIN',
            f"Inicio de sesión exitoso ({user.username}).",
            usuario=user,
        )


@receiver(pre_save, sender=Tramite)
def auditar_cambio_costo_tramite(sender, instance, **kwargs):
    """Registra cambios de costo solo cuando hay un usuario autenticado (staff)."""
    if not instance.pk:
        return
    request = get_current_request()
    if not request or not usuario_auditado(request.user):
        return
    tramite_antiguo = Tramite.objects.get(pk=instance.pk)
    if tramite_antiguo.costo != instance.costo:
        registrar_evento(
            request,
            'MODIFICACION_COSTO',
            (
                f"El trámite '{instance.nombre}' cambió su costo oficial "
                f"de ${tramite_antiguo.costo} a ${instance.costo}."
            ),
        )

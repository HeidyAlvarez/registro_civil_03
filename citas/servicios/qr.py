"""Tabla CRC 24 — QR (generación y validación)."""

from io import BytesIO

import qrcode
from django.utils import timezone

from citas.models import Cita


def generar_imagen_qr_bytes(cita):
    """Genera la imagen PNG del QR en memoria (no depende de archivos en /media/)."""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(cita.url_validacion_qr())
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    buffer = BytesIO()
    img.save(buffer, 'PNG')
    buffer.seek(0)
    return buffer.getvalue()


class QR:
    """Validación de tokens QR y transición PENDIENTE → ASISTIDA."""

    @staticmethod
    def token_valido(cita, token):
        return bool(token) and str(cita.qr_codigo) == str(token)

    @staticmethod
    def es_cita_del_dia(cita, fecha=None):
        fecha = fecha or timezone.now().date()
        return cita.fecha == fecha

    @classmethod
    def validar_y_marcar_asistida(cls, cita_id, token, usuario):
        """
        Retorna (ok, payload).
        payload es dict con status/message o datos de éxito.
        """
        try:
            cita = Cita.objects.get(id=cita_id)
        except Cita.DoesNotExist:
            return False, {
                'status': 'error',
                'message': 'Código QR no reconocido.',
                'log': ('SEGURIDAD', f"Intento de validación QR con folio inexistente (#{cita_id})."),
            }

        if not cls.token_valido(cita, token):
            return False, {
                'status': 'error',
                'message': 'Código QR no válido o alterado.',
                'log': ('SEGURIDAD', f"QR rechazado: token inválido para cita #{cita_id}."),
            }

        hoy = timezone.now().date()
        if not cls.es_cita_del_dia(cita, hoy):
            if cita.fecha > hoy:
                mensaje = 'Solo se pueden validar citas del día de hoy. Esta cita es para una fecha futura.'
            else:
                mensaje = 'Solo se pueden validar citas del día de hoy. Esta cita corresponde a un día anterior.'
            return False, {
                'status': 'error',
                'message': mensaje,
                'log': (
                    'MODIFICACION_CITA',
                    f"QR rechazado: cita #{cita.id} con fecha {cita.fecha}, hoy es {hoy}.",
                ),
            }

        if cita.estado == 'PENDIENTE':
            cita.estado = 'ASISTIDA'
            cita.usuario_atendio = usuario
            cita.save()
            return True, {
                'status': 'success',
                'ciudadano': cita.nombre_ciudadano,
                'tramite': cita.tramite.nombre,
                'cita_id': cita.id,
                'nuevo_estado': 'ASISTIDA',
                'log': (
                    'MODIFICACION_CITA',
                    f"Cita #{cita.id} ({cita.nombre_ciudadano}) marcada como ASISTIDA por validación QR.",
                ),
            }

        return False, {
            'status': 'error',
            'message': f'La cita ya está como: {cita.estado}',
            'log': (
                'MODIFICACION_CITA',
                f"Intento QR rechazado: cita #{cita.id} ya en estado {cita.estado}.",
            ),
        }

import uuid
import datetime
from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils import timezone
from .validators import validador_curp, validar_curp
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

class SeccionTramite(models.Model):
    """ Tabla para registrar nuevas secciones dinámicamente (Ej: Matrimonio, Divorcio) """
    nombre = models.CharField(max_length=200, unique=True, verbose_name="Nombre de la Sección")

    class Meta:
        verbose_name = "Sección de Trámite"
        verbose_name_plural = "📂 Secciones del Catálogo"

    def __str__(self):
        return f"📂 {self.nombre}"


class Tramite(models.Model):
    """ HU-5: Catálogo de trámites, costos, duración y requisitos """
    seccion = models.ForeignKey(
        SeccionTramite, on_delete=models.PROTECT, related_name='tramites',
        verbose_name="Sección", null=True, blank=True,
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Trámite")
    duracion_minutos = models.PositiveIntegerField(default=15, help_text="Duración estimada en minutos")
    costo = models.DecimalField(max_digits=10, decimal_places=2, help_text="Costo según tabulador oficial 2026")
    documentos_requeridos = models.TextField(
        blank=True, null=True,
        help_text="Papeles necesarios separados por comas o renglones",
    )
    activo = models.BooleanField(default=True, help_text="Desactivar en lugar de eliminar para proteger el historial")

    class Meta:
        verbose_name = "Trámite"
        verbose_name_plural = "Catálogo de Trámites"
        unique_together = ('seccion', 'nombre')

    def __str__(self):
        if self.seccion:
            return f"{self.seccion.nombre} - {self.nombre}"
        return f"Sin Sección - {self.nombre}"

    def tiene_citas_futuras(self):
        hoy = datetime.date.today()
        return self.cita_set.filter(
            fecha__gte=hoy,
        ).exclude(estado='CANCELADA').exists()

    def tiene_citas_pendientes_futuras(self):
        hoy = datetime.date.today()
        return self.cita_set.filter(fecha__gte=hoy, estado='PENDIENTE').exists()

    def clean(self):
        if self.pk:
            prev = Tramite.objects.filter(pk=self.pk).first()
            if prev and prev.activo and not self.activo and self.tiene_citas_pendientes_futuras():
                raise ValidationError(
                    "No se puede desactivar un trámite con citas futuras en estado Pendiente."
                )

    def delete(self, *args, **kwargs):
        if self.tiene_citas_futuras():
            raise ValidationError(
                "No se puede eliminar un trámite que tenga citas futuras programadas. "
                "Desactívalo en su lugar."
            )
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Cita(models.Model):
    """ HU-1, HU-3, HU-4: Agenda de ciudadanos y validación de asistencia por QR """
    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('ASISTIDA', 'Asistida en Ventanilla'),
        ('PAGADA', 'Pagada (Cobro Registrado)'),
        ('FINALIZADA', 'Finalizada (Trámite Completo)'),
        ('CANCELADA', 'Cancelada'),
    ]

    validador_cp = RegexValidator(
        regex=r'^[0-9]{5}$',
        message="El Código Postal debe ser de exactamente 5 números (ej. 50900)."
    )

    # Datos del Ciudadano
    curp_ciudadano = models.CharField(max_length=18, validators=[validador_curp], verbose_name="CURP")
    nombre_ciudadano = models.CharField(max_length=150, verbose_name="Nombre Completo")
    codigo_postal = models.CharField(max_length=5, validators=[validador_cp], verbose_name="Código Postal")
    direccion = models.TextField(verbose_name="Dirección Completa")
    
    # Relaciones y Horarios
    tramite = models.ForeignKey(Tramite, on_delete=models.PROTECT, verbose_name="Trámite a Realizar")
    fecha = models.DateField(verbose_name="Fecha de la Cita")
    hora = models.TimeField(verbose_name="Hora de la Cita")
    
    # Control de flujo y Token de seguridad para el QR
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='PENDIENTE')
    qr_codigo = models.CharField(
        max_length=64, 
        unique=True, 
        default=uuid.uuid4, 
        editable=False,
        help_text="Token único e infalsificable del código QR"
    )
    
    # Auditoría
    usuario_atendio = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        verbose_name="Atendido por"
    )
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cita"
        verbose_name_plural = "Libreta de Citas (Agenda)"

    def clean(self):
        if self.curp_ciudadano:
            self.curp_ciudadano = validar_curp(self.curp_ciudadano)

        from .utils import parse_hora_str, format_minutes, get_intervalo_cita, intervalos_se_solapan
        hora_str = format_minutes(parse_hora_str(str(self.hora)[:5]))
        duracion = self.tramite.duracion_minutos if self.tramite_id else 15
        otras = Cita.objects.filter(fecha=self.fecha).exclude(id=self.id).exclude(estado='CANCELADA')
        if otras.exists():
            inicio_nuevo = parse_hora_str(hora_str)
            fin_nuevo = inicio_nuevo + duracion
            for cita in otras.select_related('tramite'):
                inicio_o, fin_o = get_intervalo_cita(cita)
                if intervalos_se_solapan(inicio_nuevo, fin_nuevo, inicio_o, fin_o):
                    raise ValidationError(
                        "Horario no disponible. El trámite requiere más tiempo del disponible en ese horario."
                    )

    codigo_qr = models.ImageField(upload_to='qrs/', blank=True, null=True)

    def url_validacion_qr(self):
        return f"/citas/validar/{self.id}/{self.qr_codigo}/"

    def __str__(self):
        return f"Folio #{self.id} - {self.nombre_ciudadano} ({self.fecha})"

    def puede_cancelarse(self):
        """ Pendiente, en caja o pagada (no finalizada). Al cancelar una pagada, el ingreso se descuenta. """
        return self.estado in ('PENDIENTE', 'ASISTIDA', 'PAGADA')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        if not self.codigo_qr:
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(self.url_validacion_qr())
            qr.make(fit=True)
            img = qr.make_image(fill='black', back_color='white')
            buffer = BytesIO()
            img.save(buffer, 'PNG')
            self.codigo_qr.save(f'qr_{self.id}.png', ContentFile(buffer.getvalue()), save=False)
            super().save(update_fields=['codigo_qr'])

class PagoCaja(models.Model):
    """ HU-8: Registro de cobros, control de ingresos mensuales y simulación de caja """
    cita = models.OneToOneField(Cita, on_delete=models.PROTECT, limit_choices_to={'estado': 'ASISTIDA'})
    monto_cobrado = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_pago = models.DateTimeField(default=timezone.now)
    cajero = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    corte_cierre_listo = models.BooleanField(default=False, verbose_name="Incluido en Corte de Caja")

    class Meta:
        verbose_name = "Registro de Pago"
        verbose_name_plural = "Caja Simultánea (Ingresos)"

    def __str__(self):
        return f"Recibo #{self.id} - {self.cita.nombre_ciudadano} (${self.monto_cobrado})"

    def clean(self):
        if self.corte_cierre_listo:
            raise ValidationError("Este registro pertenece a un corte de caja cerrado. No puede ser alterado.")

    def save(self, *args, **kwargs):
        if not self.monto_cobrado:
            self.monto_cobrado = self.cita.tramite.costo
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.corte_cierre_listo:
            raise ValidationError("Este registro pertenece a un corte de caja cerrado y no puede eliminarse.")
        super().delete(*args, **kwargs)


class CorteCajaDiario(models.Model):
    """ HU-8: Corte de caja diario inmutable con desglose por trámite """
    fecha = models.DateField(unique=True, verbose_name="Fecha del corte")
    total_recaudado = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    desglose_tramites = models.JSONField(default=dict, verbose_name="Desglose por trámite")
    cantidad_pagos = models.PositiveIntegerField(default=0)
    cerrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    cerrado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Corte de Caja Diario"
        verbose_name_plural = "Cortes de Caja Diarios"
        ordering = ['-fecha']

    def __str__(self):
        return f"Corte {self.fecha} — ${self.total_recaudado}"

    def clean(self):
        if self.pk:
            raise ValidationError("Los cortes de caja diarios son inmutables.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Los cortes de caja diarios no pueden eliminarse.")


class BitacoraAuditoria(models.Model):
    TIPO_ACCION_CHOICES = [
        ('LOGIN', 'Inicio de Sesión'),
        ('ACCESO_DENEGADO', 'Intento de Acceso No Autorizado'),
        ('MODIFICACION_COSTO', 'Modificación de Tabulador Oficial'),
        ('MODIFICACION_CITA', 'Modificación de Cita'),
        ('CANCELACION_ERROR', 'Cancelación de Asistencia por Error'),
        ('CIERRE_CORTE', 'Cierre de Corte de Caja'),
        ('INFO', 'Informativo'),
        ('TRANSACCION', 'Movimiento Financiero'),
        ('SEGURIDAD', 'Alerta de Seguridad'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, verbose_name="Usuario Ejecutor")
    accion = models.CharField(max_length=25, choices=TIPO_ACCION_CHOICES, verbose_name="Acción Realizada")
    descripcion = models.TextField(verbose_name="Descripción Detallada del Cambio")
    fecha_hora = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora Exacta")
    ip_direccion = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")

    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Bitácora de Auditoría (Logs)"
        ordering = ['-fecha_hora']

    def __str__(self):
        return f"[{self.accion}] - {self.usuario} - {self.fecha_hora}"

    def clase_pill_accion(self):
        return {
            'MODIFICACION_CITA': 'pill-bit-cita',
            'TRANSACCION': 'pill-bit-txn',
            'LOGIN': 'pill-bit-login',
            'ACCESO_DENEGADO': 'pill-bit-deny',
            'MODIFICACION_COSTO': 'pill-bit-costo',
            'CIERRE_CORTE': 'pill-bit-costo',
            'CANCELACION_ERROR': 'pill-bit-deny',
            'INFO': 'pill-bit-costo',
            'SEGURIDAD': 'pill-bit-deny',
        }.get(self.accion, 'pill-bit-costo')

    def nombre_usuario_log(self):
        if self.usuario_id and self.usuario:
            return self.usuario.username
        return 'desconocido'

    def clean(self):
        if self.pk:
            raise ValidationError("Acción denegada. Los registros de la bitácora de auditoría son inmutables.")

    def delete(self, *args, **kwargs):
        raise ValidationError("Acción denegada. La bitácora de auditoría no puede ser borrada por ningún rol.")
    
class HorarioBloqueado(models.Model):
    """ RF-09: Permite al Oficial bloquear días completos o horarios específicos """
    fecha = models.DateField(verbose_name="Fecha bloqueada")
    hora = models.TimeField(null=True, blank=True, verbose_name="Hora específica (vacío = todo el día)")
    motivo = models.CharField(max_length=200, blank=True, verbose_name="Motivo del bloqueo")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Horario Bloqueado"
        verbose_name_plural = "Horarios Bloqueados"
        unique_together = ('fecha', 'hora')
        ordering = ['fecha', 'hora']

    def __str__(self):
        if self.hora:
            return f"{self.fecha} a las {self.hora} - {self.motivo or 'Sin motivo'}"
        return f"{self.fecha} (día completo) - {self.motivo or 'Sin motivo'}"
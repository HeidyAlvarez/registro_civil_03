from django.conf import settings
from django.db import models


class ConversacionAsistente(models.Model):
    clave = models.CharField(max_length=64, unique=True)
    creado_el = models.DateTimeField(auto_now_add=True)
    contexto = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Conversación del asistente'
        verbose_name_plural = 'Conversaciones del asistente'

    def __str__(self):
        return self.clave


class MensajeAsistente(models.Model):
    ROL_CIUDADANO = 'ciudadano'
    ROL_ASISTENTE = 'asistente'

    conversacion = models.ForeignKey(
        ConversacionAsistente, on_delete=models.CASCADE, related_name='mensajes',
    )
    rol = models.CharField(max_length=12)
    texto = models.TextField()
    metadatos = models.JSONField(default=dict, blank=True)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['creado_el', 'id']
        verbose_name = 'Mensaje del asistente'
        verbose_name_plural = 'Mensajes del asistente'


class SolicitudAtencion(models.Model):
    PENDIENTE = 'PENDIENTE'
    EN_ATENCION = 'EN_ATENCION'
    CERRADA = 'CERRADA'

    conversacion = models.ForeignKey(
        ConversacionAsistente, null=True, blank=True, on_delete=models.SET_NULL,
    )
    curp = models.CharField(max_length=18, blank=True)
    nombre = models.CharField(max_length=150, blank=True)
    motivo = models.TextField()
    estado = models.CharField(max_length=20, default=PENDIENTE)
    creado_el = models.DateTimeField(auto_now_add=True)
    atendida_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    atendida_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creado_el']
        verbose_name = 'Solicitud de atención'
        verbose_name_plural = 'Solicitudes de atención a funcionario'

    def __str__(self):
        return f'Solicitud #{self.pk} ({self.estado})'


class NotificacionInteligente(models.Model):
    CIUDADANO = 'CIUDADANO'
    FUNCIONARIO = 'FUNCIONARIO'
    RECORDATORIO = 'RECORDATORIO'
    DOCUMENTACION = 'DOCUMENTACION'
    CAMBIO = 'CAMBIO'
    DISPONIBILIDAD = 'DISPONIBILIDAD'
    DEMANDA = 'DEMANDA'
    PENDIENTES = 'PENDIENTES'

    clave = models.CharField(max_length=140, unique=True)
    destino = models.CharField(max_length=12)
    curp = models.CharField(max_length=18, blank=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
    )
    categoria = models.CharField(max_length=20)
    titulo = models.CharField(max_length=180)
    mensaje = models.TextField()
    cita = models.ForeignKey('citas.Cita', null=True, blank=True, on_delete=models.CASCADE)
    leida = models.BooleanField(default=False)
    creado_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-creado_el']
        verbose_name = 'Notificación inteligente'
        verbose_name_plural = 'Notificaciones inteligentes'

    def __str__(self):
        return self.titulo


class PropuestaOptimizacion(models.Model):
    PROPUESTA = 'PROPUESTA'
    RECHAZADA = 'RECHAZADA'
    APLICADA = 'APLICADA'

    fecha = models.DateField()
    resumen = models.TextField()
    analisis = models.JSONField(default=dict, blank=True)
    movimientos = models.JSONField(default=list, blank=True)
    estado = models.CharField(max_length=12, default=PROPUESTA)
    creada_el = models.DateTimeField(auto_now_add=True)
    revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='propuestas_ia_revisadas',
    )
    revisada_el = models.DateTimeField(null=True, blank=True)
    nota = models.TextField(blank=True)

    class Meta:
        ordering = ['-creada_el']
        verbose_name = 'Propuesta de optimización'
        verbose_name_plural = 'Propuestas de optimización'

    def __str__(self):
        return f'Optimización {self.fecha} ({self.estado})'


class ReglaPrioridad(models.Model):
    nombre = models.CharField(max_length=150)
    palabras_clave = models.CharField(
        max_length=200, blank=True,
        help_text='Fragmento del nombre del trámite. Vacío aplica a todos.',
    )
    minutos_umbral = models.PositiveIntegerField(default=30)
    estados = models.CharField(max_length=80, default='PENDIENTE')
    solo_hoy = models.BooleanField(default=True)
    accion_sugerida = models.CharField(max_length=200, default='Revisar solicitud.')
    activa = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Regla de atención prioritaria'
        verbose_name_plural = 'Reglas de atención prioritaria'

    def __str__(self):
        return self.nombre

    def lista_estados(self):
        return [parte.strip() for parte in self.estados.split(',') if parte.strip()]


class AlertaUrgente(models.Model):
    ABIERTA = 'ABIERTA'
    REVISADA = 'REVISADA'

    clave = models.CharField(max_length=80, unique=True)
    cita = models.ForeignKey('citas.Cita', on_delete=models.CASCADE, related_name='alertas_ia')
    regla = models.ForeignKey(ReglaPrioridad, null=True, blank=True, on_delete=models.SET_NULL)
    titulo = models.CharField(max_length=200)
    detalle = models.TextField(blank=True)
    tiempo_minutos = models.PositiveIntegerField(default=0)
    documentacion = models.CharField(max_length=80, default='completa')
    accion_sugerida = models.CharField(max_length=200)
    estado = models.CharField(max_length=12, default=ABIERTA)
    creada_el = models.DateTimeField(auto_now_add=True)
    revisada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    revisada_el = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-creada_el']
        verbose_name = 'Caso urgente'
        verbose_name_plural = 'Casos urgentes'

    def __str__(self):
        return self.titulo


class Anomalia(models.Model):
    DETECTADA = 'DETECTADA'
    EN_REVISION = 'EN_REVISION'
    REVISADA = 'REVISADA'
    INVESTIGACION = 'INVESTIGACION'
    CERRADA = 'CERRADA'

    ACTIVIDAD = 'ACTIVIDAD'
    MODIFICACIONES = 'MODIFICACIONES'
    ACCESO = 'ACCESO'
    HORARIO = 'HORARIO'
    REGISTROS = 'REGISTROS'

    TIPOS = [
        (ACTIVIDAD, 'Actividad fuera de patrón'),
        (MODIFICACIONES, 'Modificaciones repetitivas'),
        (ACCESO, 'Intentos de acceso'),
        (HORARIO, 'Actividad fuera del horario habitual'),
        (REGISTROS, 'Cambios inusuales en registros'),
    ]

    folio = models.CharField(max_length=20, blank=True, db_index=True)
    clave = models.CharField(max_length=140, unique=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    usuario_texto = models.CharField(max_length=150, blank=True)
    area = models.CharField(max_length=80, default='Oficialía 03')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    descripcion = models.TextField()
    evidencia = models.JSONField(default=dict, blank=True)
    estado = models.CharField(max_length=20, default=DETECTADA)
    clasificacion = models.CharField(max_length=80, blank=True)
    detectada_el = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-detectada_el']
        verbose_name = 'Anomalía'
        verbose_name_plural = 'Anomalías'

    def __str__(self):
        return self.folio or f'Anomalía #{self.pk}'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.folio:
            self.folio = f'AN-{self.pk:04d}'
            super().save(update_fields=['folio'])

    def codigo_usuario(self):
        if self.usuario_id:
            return f'U-{self.usuario_id:04d}'
        return 'No identificado'

    def get_tipo_display_legible(self):
        return dict(self.TIPOS).get(self.tipo, self.tipo)


class EventoInvestigacion(models.Model):
    REVISAR = 'REVISAR'
    CONSULTAR_REGISTROS = 'CONSULTAR_REGISTROS'
    CONSULTAR_HISTORIAL = 'CONSULTAR_HISTORIAL'
    MARCAR_REVISADO = 'MARCAR_REVISADO'
    CLASIFICAR = 'CLASIFICAR'
    SOLICITAR_INVESTIGACION = 'SOLICITAR_INVESTIGACION'
    GENERAR_REPORTE = 'GENERAR_REPORTE'

    anomalia = models.ForeignKey(Anomalia, on_delete=models.CASCADE, related_name='eventos')
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
    )
    accion = models.CharField(max_length=32)
    nota = models.TextField(blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Evento de investigación'
        verbose_name_plural = 'Bitácora de investigación de anomalías'

    def __str__(self):
        return f'{self.anomalia.folio} · {self.accion}'

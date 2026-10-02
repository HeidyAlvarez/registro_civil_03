import datetime
import uuid
from functools import wraps

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from citas.auditoria import registrar_log
from citas.models import BitacoraAuditoria, Tramite
from citas.office_info import OFICINA_REGISTRO_CIVIL
from citas.permisos import es_oficial_o_admin
from citas.validators import validar_curp


def solo_personal(vista):
    """El personal entra al control interno. El portal ciudadano nunca llega al sitio del administrador."""

    @wraps(vista)
    def envuelta(request, *args, **kwargs):
        if not request.user.is_authenticated or not es_oficial_o_admin(request.user):
            return redirect('portal_ciudadano')
        return vista(request, *args, **kwargs)

    return envuelta

from .models import (
    AlertaUrgente,
    Anomalia,
    ConversacionAsistente,
    MensajeAsistente,
    NotificacionInteligente,
    PropuestaOptimizacion,
    SolicitudAtencion,
)
from .servicios.analitica import (
    analisis_temporadas,
    construir_reporte,
    panorama_demanda,
    sugerir_horario,
)
from .servicios.asistente import responder
from .servicios.grok import responder_con_grok
from .servicios.sincronizar import (
    aplicar_propuesta,
    generar_propuesta,
    rechazar_propuesta,
    registrar_evento,
    sincronizar,
    sincronizar_si_hace_falta,
)

CLASIFICACIONES = (
    'Comportamiento habitual',
    'Requiere seguimiento',
    'Falso positivo',
    'Escalado a investigación',
)


def _tramites_activos():
    return list(Tramite.objects.filter(activo=True).select_related('seccion').order_by('nombre'))


def _limpiar_chat(request):
    clave = request.session.pop('ia_conversacion', None)
    if clave:
        ConversacionAsistente.objects.filter(clave=clave).delete()


def _volver_al_chat(request):
    request.session['ia_chat_mostrar'] = True
    return redirect('ia_asistente')


def _conversacion(request):
    clave = request.session.get('ia_conversacion')
    if not clave:
        clave = uuid.uuid4().hex
        request.session['ia_conversacion'] = clave
    conversacion, _ = ConversacionAsistente.objects.get_or_create(clave=clave)
    return conversacion


def _ctx_interno(activo):
    sincronizar_si_hace_falta()
    return {
        'interno': True,
        'ia_activo': activo,
        'alertas_abiertas': AlertaUrgente.objects.filter(estado=AlertaUrgente.ABIERTA).count(),
        'anomalias_abiertas': Anomalia.objects.filter(estado=Anomalia.DETECTADA).count(),
        'propuestas_pendientes': PropuestaOptimizacion.objects.filter(
            estado=PropuestaOptimizacion.PROPUESTA,
        ).count(),
        'solicitudes_pendientes': SolicitudAtencion.objects.filter(
            estado=SolicitudAtencion.PENDIENTE,
        ).count(),
    }


def portal_ia(request):
    _limpiar_chat(request)
    return render(request, 'ia/ciudadano_inicio.html', {
        'interno': False,
        'ia_activo': 'inicio',
        'oficina': OFICINA_REGISTRO_CIVIL,
    })


def asistente(request):
    if request.method == 'GET' and not request.session.pop('ia_chat_mostrar', False):
        _limpiar_chat(request)
    conversacion = _conversacion(request)
    if request.method == 'POST' and request.POST.get('accion') == 'derivar':
        curp = (request.POST.get('curp') or '').strip().upper()
        if curp:
            try:
                curp = validar_curp(curp)
            except Exception:
                messages.error(request, 'La CURP no tiene un formato válido.')
                return _volver_al_chat(request)
        SolicitudAtencion.objects.create(
            conversacion=conversacion,
            curp=curp,
            nombre=(request.POST.get('nombre') or '').strip(),
            motivo=(request.POST.get('motivo') or 'El asistente no pudo resolver la consulta.').strip(),
        )
        messages.success(request, 'Tu solicitud de atención quedó registrada. Un funcionario la revisará.')
        return _volver_al_chat(request)

    if request.method == 'POST':
        pregunta = (request.POST.get('atajo') or request.POST.get('pregunta') or '').strip()
        if pregunta:
            tramites = _tramites_activos()
            historial = list(conversacion.mensajes.values('rol', 'texto'))
            resultado = responder_con_grok(
                pregunta, historial, tramites, OFICINA_REGISTRO_CIVIL, conversacion.contexto,
            )
            if resultado is None:
                resultado = responder(pregunta, conversacion.contexto, tramites, OFICINA_REGISTRO_CIVIL)
            MensajeAsistente.objects.create(conversacion=conversacion, rol=MensajeAsistente.ROL_CIUDADANO, texto=pregunta)
            MensajeAsistente.objects.create(
                conversacion=conversacion,
                rol=MensajeAsistente.ROL_ASISTENTE,
                texto=resultado['texto'],
                metadatos={'opciones': resultado['opciones'], 'derivar': resultado['derivar']},
            )
            conversacion.contexto = resultado['contexto']
            conversacion.save(update_fields=['contexto'])
        return _volver_al_chat(request)

    mensajes = conversacion.mensajes.all()
    respuesta = render(request, 'ia/asistente.html', {
        'interno': False,
        'ia_activo': 'asistente',
        'mensajes': mensajes,
        'ultimo': mensajes.last(),
    })
    respuesta['Cache-Control'] = 'no-store'
    return respuesta


def dias_concurridos(request):
    _limpiar_chat(request)
    return render(request, 'ia/dias.html', {
        'interno': False,
        'ia_activo': 'dias',
        'panorama': panorama_demanda(),
        'titulo': 'Días más concurridos',
        'intro': (
            'Estos datos muestran cuándo se concentra la atención. '
            'Puedes usarlos para elegir un horario con menor demanda.'
        ),
    })


@solo_personal
def dias_concurridos_interno(request):
    ctx = _ctx_interno('dias')
    ctx.update({
        'panorama': panorama_demanda(),
        'titulo': 'Días más concurridos',
        'intro': (
            'El personal puede usar este análisis para distribuir citas, organizar al personal '
            'y anticipar saturaciones.'
        ),
    })
    return render(request, 'ia/dias.html', ctx)


def sugerencia_horario(request):
    _limpiar_chat(request)
    tramites = _tramites_activos()
    resultado = None
    tramite_id = request.GET.get('tramite')
    fecha_txt = request.GET.get('fecha')
    if tramite_id and fecha_txt:
        tramite = next((t for t in tramites if str(t.id) == str(tramite_id)), None)
        try:
            fecha = datetime.datetime.strptime(fecha_txt, '%Y-%m-%d').date()
        except ValueError:
            fecha = None
            messages.error(request, 'La fecha no es válida.')
        if tramite and fecha:
            resultado = sugerir_horario(tramite, fecha)
    return render(request, 'ia/sugerencia.html', {
        'interno': False,
        'ia_activo': 'sugerencia',
        'tramites': tramites,
        'tramite_id': tramite_id,
        'fecha': fecha_txt,
        'resultado': resultado,
        'oficina': OFICINA_REGISTRO_CIVIL,
    })


def notificaciones_ciudadano(request):
    _limpiar_chat(request)
    curp = (request.GET.get('curp') or request.POST.get('curp') or '').strip().upper()
    avisos = []
    error = None
    if curp:
        try:
            curp = validar_curp(curp)
        except Exception:
            error = 'La CURP no tiene un formato válido.'
            curp = ''
        else:
            sincronizar_si_hace_falta()
            avisos = NotificacionInteligente.objects.filter(
                destino=NotificacionInteligente.CIUDADANO,
                curp=curp,
            )
    return render(request, 'ia/notificaciones.html', {
        'interno': False,
        'ia_activo': 'notificaciones',
        'curp': curp,
        'avisos': avisos,
        'error': error,
    })


@require_POST
def marcar_notificacion(request):
    curp = (request.POST.get('curp') or '').strip().upper()
    aviso = get_object_or_404(NotificacionInteligente, pk=request.POST.get('aviso_id'))
    if aviso.destino == NotificacionInteligente.CIUDADANO:
        if aviso.curp != curp:
            messages.error(request, 'No se pudo marcar el aviso.')
            return redirect('ia_notificaciones')
        aviso.leida = True
        aviso.save(update_fields=['leida'])
        return redirect(f"{reverse('ia_notificaciones')}?curp={curp}")
    if not request.user.is_authenticated or not es_oficial_o_admin(request.user):
        return redirect('ia_interno')
    aviso.leida = True
    aviso.save(update_fields=['leida'])
    return redirect('ia_interno')


@solo_personal
def panel_interno(request):
    ctx = _ctx_interno('inicio')
    ctx.update({
        'notificaciones': NotificacionInteligente.objects.filter(
            destino=NotificacionInteligente.FUNCIONARIO,
            leida=False,
        )[:8],
        'solicitudes': SolicitudAtencion.objects.filter(estado=SolicitudAtencion.PENDIENTE)[:8],
        'panorama': panorama_demanda(dias=30),
    })
    return render(request, 'ia/interno_inicio.html', ctx)


@solo_personal
def temporadas(request):
    ctx = _ctx_interno('temporadas')
    ctx['analisis'] = analisis_temporadas()
    return render(request, 'ia/temporadas.html', ctx)


@solo_personal
def optimizacion(request):
    ctx = _ctx_interno('optimizacion')
    if request.method == 'POST':
        fecha_txt = request.POST.get('fecha')
        try:
            fecha = datetime.datetime.strptime(fecha_txt, '%Y-%m-%d').date()
        except (TypeError, ValueError):
            messages.error(request, 'Indica una fecha válida.')
            return redirect('ia_optimizacion')
        propuesta = generar_propuesta(fecha)
        if propuesta:
            messages.success(request, 'La IA generó una propuesta. Revísala antes de autorizarla.')
            return redirect('ia_optimizacion_detalle', propuesta_id=propuesta.id)
        messages.info(request, 'No hay un desbalance de horarios que requiera redistribuir citas en esa fecha.')
        return redirect('ia_optimizacion')
    ctx['propuestas'] = PropuestaOptimizacion.objects.all()[:30]
    ctx['manana'] = (timezone.localdate() + datetime.timedelta(days=1)).isoformat()
    return render(request, 'ia/optimizacion.html', ctx)


@solo_personal
def optimizacion_detalle(request, propuesta_id):
    propuesta = get_object_or_404(PropuestaOptimizacion, pk=propuesta_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        if accion == 'autorizar':
            ok, mensaje = aplicar_propuesta(propuesta, request.user, request)
        else:
            ok, mensaje = rechazar_propuesta(propuesta, request.user, request.POST.get('nota', ''))
        if ok:
            messages.success(request, mensaje)
        else:
            messages.error(request, mensaje)
        return redirect('ia_optimizacion_detalle', propuesta_id=propuesta.id)
    ctx = _ctx_interno('optimizacion')
    ctx['propuesta'] = propuesta
    return render(request, 'ia/optimizacion_detalle.html', ctx)


@solo_personal
def casos_urgentes(request):
    ctx = _ctx_interno('urgentes')
    ctx['alertas'] = AlertaUrgente.objects.select_related('cita', 'cita__tramite', 'regla')
    return render(request, 'ia/urgentes.html', ctx)


@solo_personal
@require_POST
def revisar_urgente(request, alerta_id):
    alerta = get_object_or_404(AlertaUrgente, pk=alerta_id)
    alerta.estado = AlertaUrgente.REVISADA
    alerta.revisada_por = request.user
    alerta.revisada_el = timezone.now()
    alerta.save(update_fields=['estado', 'revisada_por', 'revisada_el'])
    registrar_log(request, 'INFO', f'Caso urgente revisado: {alerta.titulo} (cita #{alerta.cita_id}).')
    messages.success(request, 'El caso quedó marcado como revisado.')
    return redirect('ia_urgentes')


@solo_personal
def anomalias(request):
    ctx = _ctx_interno('anomalias')
    ctx['lista'] = Anomalia.objects.all()[:80]
    return render(request, 'ia/anomalias.html', ctx)


@solo_personal
def anomalia_detalle(request, anomalia_id):
    anomalia = get_object_or_404(Anomalia, pk=anomalia_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        nota = (request.POST.get('nota') or '').strip()
        clasificacion = request.POST.get('clasificacion') or ''
        if accion == Anomalia.REVISADA or accion == 'MARCAR_REVISADO':
            anomalia.estado = Anomalia.REVISADA
            registrar_evento(anomalia, request.user, 'MARCAR_REVISADO', nota)
        elif accion == 'CLASIFICAR' and clasificacion in CLASIFICACIONES:
            anomalia.clasificacion = clasificacion
            anomalia.estado = Anomalia.REVISADA
            registrar_evento(anomalia, request.user, 'CLASIFICAR', clasificacion)
        elif accion == 'SOLICITAR_INVESTIGACION':
            anomalia.estado = Anomalia.INVESTIGACION
            registrar_evento(anomalia, request.user, 'SOLICITAR_INVESTIGACION', nota)
        elif accion == 'GENERAR_REPORTE':
            registrar_evento(anomalia, request.user, 'GENERAR_REPORTE', nota or 'Reporte de la anomalía consultado.')
        elif accion == 'CONSULTAR_REGISTROS':
            registrar_evento(anomalia, request.user, 'CONSULTAR_REGISTROS', nota)
            if anomalia.estado == Anomalia.DETECTADA:
                anomalia.estado = Anomalia.EN_REVISION
        elif accion == 'CONSULTAR_HISTORIAL':
            registrar_evento(anomalia, request.user, 'CONSULTAR_HISTORIAL', nota)
            if anomalia.estado == Anomalia.DETECTADA:
                anomalia.estado = Anomalia.EN_REVISION
        anomalia.save()
        registrar_log(request, 'INFO', f'Investigación de anomalía {anomalia.folio}: {accion}.')
        messages.success(request, 'La bitácora de investigación registró la acción.')
        return redirect('ia_anomalia_detalle', anomalia_id=anomalia.id)

    ids = anomalia.evidencia.get('registros') or []
    registros = BitacoraAuditoria.objects.filter(id__in=ids).select_related('usuario')
    historial = []
    if anomalia.usuario_id:
        historial = BitacoraAuditoria.objects.filter(usuario_id=anomalia.usuario_id).select_related('usuario')[:25]
    ctx = _ctx_interno('anomalias')
    ctx.update({
        'anomalia': anomalia,
        'registros': registros,
        'historial': historial,
        'clasificaciones': CLASIFICACIONES,
        'eventos': anomalia.eventos.select_related('usuario'),
    })
    return render(request, 'ia/anomalia_detalle.html', ctx)


@solo_personal
def reportes(request):
    ctx = _ctx_interno('reportes')
    ctx['panorama'] = panorama_demanda()
    ctx['temporadas'] = analisis_temporadas()
    return render(request, 'ia/reportes.html', ctx)


@solo_personal
def reporte_detalle(request, tipo):
    datos = construir_reporte(tipo)
    if datos is None and tipo != 'anomalias' and tipo != 'ejecutivo':
        return redirect('ia_reportes')
    ctx = _ctx_interno('reportes')
    if tipo == 'anomalias':
        datos = _reporte_anomalias()
    elif tipo == 'ejecutivo':
        datos = _reporte_ejecutivo()
    ctx['reporte'] = datos
    ctx['tipo'] = tipo
    return render(request, 'ia/reporte_detalle.html', ctx)


def _reporte_anomalias():
    lista = Anomalia.objects.all()[:40]
    return {
        'titulo': 'Reporte de anomalías',
        'intro': 'Eventos que se alejan del patrón habitual y su estado de revisión. Una anomalía no es un fraude.',
        'hallazgos': [
            f'{Anomalia.objects.filter(estado=Anomalia.DETECTADA).count()} eventos siguen sin revisión.',
            f'{Anomalia.objects.filter(estado=Anomalia.INVESTIGACION).count()} están en investigación.',
        ],
        'tabla': {
            'titulo': 'Eventos detectados',
            'columnas': ['Folio', 'Tipo', 'Estado', 'Fecha'],
            'filas': [
                [a.folio, a.get_tipo_display_legible(), a.estado, timezone.localtime(a.detectada_el).strftime('%d/%m/%Y %H:%M')]
                for a in lista
            ],
        },
    }


def _reporte_ejecutivo():
    panorama = panorama_demanda()
    temporadas = analisis_temporadas()
    return {
        'titulo': 'Reporte ejecutivo',
        'intro': 'Resumen para dirección. Cada cifra sale del historial del sistema y puede abrirse en su reporte.',
        'hallazgos': panorama['hallazgos'] + temporadas['frases'][:2],
        'tarjetas': [
            {'etiqueta': 'Citas del periodo', 'valor': panorama['total_citas']},
            {'etiqueta': 'Cancelaciones', 'valor': panorama['cancelaciones']},
            {'etiqueta': 'Personas atendidas', 'valor': panorama['personas_atendidas']},
            {'etiqueta': 'Anomalías abiertas', 'valor': Anomalia.objects.filter(estado=Anomalia.DETECTADA).count()},
            {'etiqueta': 'Casos urgentes abiertos', 'valor': AlertaUrgente.objects.filter(estado=AlertaUrgente.ABIERTA).count()},
            {'etiqueta': 'Propuestas por autorizar', 'valor': PropuestaOptimizacion.objects.filter(estado=PropuestaOptimizacion.PROPUESTA).count()},
        ],
        'tabla': {
            'titulo': 'Trámites más solicitados',
            'columnas': ['Trámite', 'Solicitudes'],
            'filas': [[f['nombre'], f['total']] for f in panorama['por_tramite']],
        },
    }


@solo_personal
@require_POST
def forzar_sincronizacion(request):
    sincronizar()
    messages.success(request, 'El análisis del módulo de IA se actualizó.')
    return redirect('ia_interno')


@solo_personal
@require_POST
def atender_solicitud(request, solicitud_id):
    solicitud = get_object_or_404(SolicitudAtencion, pk=solicitud_id)
    solicitud.estado = SolicitudAtencion.CERRADA
    solicitud.atendida_por = request.user
    solicitud.atendida_el = timezone.now()
    solicitud.save(update_fields=['estado', 'atendida_por', 'atendida_el'])
    registrar_log(request, 'INFO', f'Solicitud de atención del asistente #{solicitud.id} marcada como atendida.')
    messages.success(request, 'La solicitud quedó atendida.')
    return redirect('ia_interno')

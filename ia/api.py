import datetime
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from citas.auditoria import registrar_log
from citas.api_v1 import api_permission
from citas.office_info import OFICINA_REGISTRO_CIVIL
from citas.permisos import es_oficial_o_admin
from citas.validators import validar_curp

from .models import (
    AlertaUrgente,
    Anomalia,
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
from .servicios.sincronizar import aplicar_propuesta, generar_propuesta, rechazar_propuesta, registrar_evento, sincronizar
from .views import _conversacion, _limpiar_chat, _tramites_activos, _ctx_interno


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def _serialize_messages(conversation):
    return [
        {
            'id': message.id,
            'role': message.rol,
            'text': message.texto,
            'options': message.metadatos.get('opciones') or [],
            'refer': bool(message.metadatos.get('derivar')),
        }
        for message in conversation.mensajes.all()
    ]


@require_http_methods(['GET', 'DELETE'])
def assistant_conversation(request):
    if request.method == 'DELETE':
        _limpiar_chat(request)
        return JsonResponse({'ok': True})
    conversation = _conversacion(request)
    response = JsonResponse({'messages': _serialize_messages(conversation)})
    response['Cache-Control'] = 'no-store'
    return response


@require_POST
def assistant_message(request):
    data = _body(request)
    question = (data.get('question') or '').strip()
    if not question:
        return JsonResponse({'error': 'Escribe una pregunta para continuar.'}, status=400)
    conversation = _conversacion(request)
    procedures = _tramites_activos()
    history = list(conversation.mensajes.values('rol', 'texto'))
    result = responder_con_grok(
        question, history, procedures, OFICINA_REGISTRO_CIVIL, conversation.contexto,
    )
    if result is None:
        result = responder(question, conversation.contexto, procedures, OFICINA_REGISTRO_CIVIL)
    MensajeAsistente.objects.create(
        conversacion=conversation, rol=MensajeAsistente.ROL_CIUDADANO, texto=question,
    )
    assistant = MensajeAsistente.objects.create(
        conversacion=conversation,
        rol=MensajeAsistente.ROL_ASISTENTE,
        texto=result['texto'],
        metadatos={'opciones': result['opciones'], 'derivar': result['derivar']},
    )
    conversation.contexto = result['contexto']
    conversation.save(update_fields=['contexto'])
    response = JsonResponse({
        'message': {
            'id': assistant.id,
            'role': assistant.rol,
            'text': assistant.texto,
            'options': assistant.metadatos['opciones'],
            'refer': assistant.metadatos['derivar'],
        },
    })
    response['Cache-Control'] = 'no-store'
    return response


@require_GET
def demand_analysis(request):
    return JsonResponse(panorama_demanda())


@require_GET
def schedule_suggestion(request):
    procedure = next(
        (item for item in _tramites_activos() if str(item.id) == request.GET.get('tramite')),
        None,
    )
    try:
        date = datetime.datetime.strptime(request.GET.get('fecha') or '', '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Selecciona una fecha válida.'}, status=400)
    if not procedure:
        return JsonResponse({'error': 'Selecciona un trámite válido.'}, status=400)
    result = sugerir_horario(procedure, date)
    return JsonResponse({
        'error': result['error'],
        'date': date,
        'procedure': {'id': procedure.id, 'name': procedure.nombre},
        'options': result['opciones'],
        'recommended': result.get('recomendado'),
    })


@require_GET
@api_permission(es_oficial_o_admin)
def internal_summary(request):
    context = _ctx_interno('inicio')
    return JsonResponse({
        'alerts': context['alertas_abiertas'],
        'anomalies': context['anomalias_abiertas'],
        'proposals': context['propuestas_pendientes'],
        'requests': context['solicitudes_pendientes'],
        'demand': panorama_demanda(dias=30),
        'seasons': analisis_temporadas(),
    })


@require_GET
def citizen_notifications(request):
    try:
        curp = validar_curp((request.GET.get('curp') or '').strip().upper())
    except Exception:
        return JsonResponse({'error': 'La CURP no tiene un formato válido.'}, status=400)
    notifications = NotificacionInteligente.objects.filter(
        destino=NotificacionInteligente.CIUDADANO,
        curp=curp,
    )
    return JsonResponse({'notifications': [{
        'id': item.id,
        'category': item.categoria,
        'title': item.titulo,
        'message': item.mensaje,
        'read': item.leida,
        'created_at': item.creado_el.isoformat(),
    } for item in notifications]})


@require_GET
@api_permission(es_oficial_o_admin)
def internal_operations(request):
    return JsonResponse({
        'alerts': [{
            'id': item.id,
            'title': item.titulo,
            'detail': item.detalle,
            'action': item.accion_sugerida,
            'status': item.estado,
            'appointment': item.cita_id,
        } for item in AlertaUrgente.objects.select_related('cita')[:50]],
        'anomalies': [{
            'id': item.id,
            'folio': item.folio,
            'type': item.get_tipo_display_legible(),
            'description': item.descripcion,
            'status': item.estado,
            'classification': item.clasificacion,
        } for item in Anomalia.objects.all()[:50]],
        'proposals': [{
            'id': item.id,
            'date': item.fecha.isoformat(),
            'summary': item.resumen,
            'status': item.estado,
            'movements': item.movimientos,
        } for item in PropuestaOptimizacion.objects.all()[:30]],
        'requests': [{
            'id': item.id,
            'name': item.nombre,
            'curp': item.curp,
            'reason': item.motivo,
            'status': item.estado,
        } for item in SolicitudAtencion.objects.all()[:30]],
    })


@require_POST
@api_permission(es_oficial_o_admin)
def internal_action(request):
    data = _body(request)
    action = data.get('action')
    object_id = data.get('id')
    if action == 'sync':
        sincronizar()
        return JsonResponse({'ok': True, 'message': 'El análisis fue actualizado.'})
    if action == 'review_alert':
        item = get_object_or_404(AlertaUrgente, pk=object_id)
        item.estado = AlertaUrgente.REVISADA
        item.revisada_por = request.user
        item.revisada_el = timezone.now()
        item.save(update_fields=['estado', 'revisada_por', 'revisada_el'])
        message = 'El caso quedó revisado.'
    elif action == 'close_request':
        item = get_object_or_404(SolicitudAtencion, pk=object_id)
        item.estado = SolicitudAtencion.CERRADA
        item.atendida_por = request.user
        item.atendida_el = timezone.now()
        item.save(update_fields=['estado', 'atendida_por', 'atendida_el'])
        message = 'La solicitud quedó atendida.'
    elif action in ('authorize_proposal', 'reject_proposal'):
        item = get_object_or_404(PropuestaOptimizacion, pk=object_id)
        if action == 'authorize_proposal':
            ok, message = aplicar_propuesta(item, request.user, request)
        else:
            ok, message = rechazar_propuesta(item, request.user, data.get('note', ''))
        if not ok:
            return JsonResponse({'error': message}, status=400)
    elif action in ('review_anomaly', 'investigate_anomaly'):
        item = get_object_or_404(Anomalia, pk=object_id)
        if action == 'review_anomaly':
            item.estado = Anomalia.REVISADA
            event_action = 'MARCAR_REVISADO'
            message = 'La anomalía quedó revisada.'
        else:
            item.estado = Anomalia.INVESTIGACION
            event_action = 'SOLICITAR_INVESTIGACION'
            message = 'La investigación fue solicitada.'
        item.save(update_fields=['estado'])
        registrar_evento(item, request.user, event_action, data.get('note', ''))
    elif action == 'generate_proposal':
        try:
            date = datetime.datetime.strptime(data.get('date') or '', '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'Selecciona una fecha válida.'}, status=400)
        proposal = generar_propuesta(date)
        if not proposal:
            return JsonResponse({'error': 'No se detectó un desbalance que requiera una propuesta.'}, status=400)
        return JsonResponse({'ok': True, 'message': 'La propuesta fue generada.', 'id': proposal.id})
    else:
        return JsonResponse({'error': 'Acción interna no válida.'}, status=400)
    registrar_log(request, 'INFO', f'Acción IA React: {action} #{object_id}.')
    return JsonResponse({'ok': True, 'message': message})


@require_GET
@api_permission(es_oficial_o_admin)
def internal_report(request, report_type):
    report = construir_reporte(report_type)
    if report is None:
        return JsonResponse({'error': 'El tipo de reporte no existe.'}, status=404)
    return JsonResponse(report)

"""API JSON para el frontend React de Nueva Era Digital."""

import json
from functools import wraps

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from .auditoria import registrar_log
from .models import BitacoraAuditoria
from .permisos import (
    es_administrador,
    es_capturista_o_superior,
    es_oficial_o_admin,
    puede_ver_panel_citas,
)
from .servicios import Bitacora, Caja, Calendario, TramiteNegocio


def _body(request):
    try:
        return json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


def api_permission(test):
    def decorator(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Tu sesión terminó. Inicia sesión nuevamente.'}, status=401)
            if not test(request.user):
                return JsonResponse({'error': 'No tienes permiso para realizar esta acción.'}, status=403)
            return view(request, *args, **kwargs)
        return wrapped
    return decorator


@require_GET
def session_me(request):
    user = request.user
    if not user.is_authenticated:
        return JsonResponse({
            'authenticated': False,
            'permissions': {
                'staff': False,
                'official': False,
                'administrator': False,
                'internal_ai': False,
            },
        })
    return JsonResponse({
        'authenticated': True,
        'username': user.username,
        'full_name': user.get_full_name() or user.username,
        'role': getattr(user, 'rol', ''),
        'permissions': {
            'staff': puede_ver_panel_citas(user),
            'official': es_oficial_o_admin(user),
            'administrator': es_administrador(user),
            'internal_ai': es_oficial_o_admin(user),
        },
    })


@require_POST
def session_login(request):
    data = _body(request)
    user = authenticate(
        request,
        username=(data.get('username') or '').strip(),
        password=data.get('password') or '',
    )
    if user is None or not user.is_active:
        return JsonResponse({'error': 'El usuario o la contraseña no son correctos.'}, status=400)
    if not puede_ver_panel_citas(user):
        return JsonResponse({'error': 'Tu cuenta no tiene acceso al panel operativo.'}, status=403)
    login(request, user)
    return JsonResponse({'ok': True})


@require_POST
def session_logout(request):
    logout(request)
    return JsonResponse({'ok': True})


@require_GET
@api_permission(es_capturista_o_superior)
def navigation(request):
    return JsonResponse({
        'items': [
            {'path': '/panel', 'label': 'Resumen'},
            {'path': '/panel/agenda', 'label': 'Agenda'},
            {'path': '/panel/caja', 'label': 'Caja'},
            {'path': '/panel/historial', 'label': 'Historial'},
        ] + (
            [{'path': '/panel/ia', 'label': 'Módulo IA'}]
            if es_oficial_o_admin(request.user) else []
        ),
    })


@require_GET
@api_permission(puede_ver_panel_citas)
def audit_log(request):
    records, users = Bitacora.consultar(
        q=request.GET.get('q', '').strip(),
        accion=request.GET.get('accion', '').strip(),
        usuario=request.GET.get('usuario', '').strip(),
        page=request.GET.get('page', 1),
        por_pagina=40,
    )
    return JsonResponse({
        'records': [{
            'id': item.id,
            'user': item.usuario.username if item.usuario else 'Sistema',
            'action': item.accion,
            'description': item.descripcion,
            'ip': item.ip_direccion or '',
            'date': timezone.localtime(item.fecha_hora).isoformat(),
        } for item in records],
        'users': users,
        'actions': [{'value': value, 'label': label} for value, label in BitacoraAuditoria.TIPO_ACCION_CHOICES],
        'pagination': {
            'page': records.number,
            'pages': records.paginator.num_pages,
            'total': records.paginator.count,
        },
    })


@require_GET
@api_permission(es_oficial_o_admin)
def financial_report(request):
    report = Caja.reporte_mensual(request.GET.get('year'), request.GET.get('month'))
    return JsonResponse({
        'total': float(report['total_acumulado'] or 0),
        'procedures': report['total_tramites'],
        'active_users': report['usuarios_activos'],
        'average_minutes': report['tiempo_promedio'],
        'month': report['mes_nombre'],
        'year': report['anio'],
        'weekly': json.loads(report['datos_semana_json']),
        'by_procedure': [{
            'section': item['cita__tramite__seccion__nombre'],
            'procedure': item['cita__tramite__nombre'],
            'quantity': item['cantidad_solicitudes'],
            'total': float(item['dinero_recaudado'] or 0),
        } for item in report['reporte_tramites']],
    })


@require_http_methods(['GET', 'POST'])
@api_permission(es_oficial_o_admin)
def schedule_blocks(request):
    if request.method == 'GET':
        return JsonResponse({'blocks': [{
            'id': item.id,
            'date': item.fecha.isoformat(),
            'time': item.hora.strftime('%H:%M') if item.hora else None,
            'reason': item.motivo,
        } for item in Calendario.listar_bloqueos_futuros()]})
    data = _body(request)
    ok, message, _ = Calendario.crear_bloqueo(
        data.get('date'),
        data.get('type'),
        data.get('reason', ''),
        request.user,
        data.get('times') or [],
    )
    if not ok:
        return JsonResponse({'error': message}, status=400)
    registrar_log(request, 'INFO', message)
    return JsonResponse({'ok': True, 'message': message})


@require_http_methods(['DELETE'])
@api_permission(es_oficial_o_admin)
def schedule_block_detail(request, block_id):
    try:
        description = Calendario.eliminar_bloqueo(block_id)
    except Exception:
        return JsonResponse({'error': 'El bloqueo ya no existe.'}, status=404)
    registrar_log(request, 'INFO', f'Bloqueo eliminado: {description}.')
    return JsonResponse({'ok': True})


@require_http_methods(['GET', 'POST'])
@api_permission(es_administrador)
def catalog_management(request):
    if request.method == 'GET':
        sections, procedures = TramiteNegocio.listar_catalogo_admin()
        return JsonResponse({
            'sections': [{'id': item.id, 'name': item.nombre} for item in sections],
            'procedures': [{
                'id': item.id,
                'section_id': item.seccion_id,
                'section': item.seccion.nombre if item.seccion else 'Sin sección',
                'name': item.nombre,
                'cost': float(item.costo),
                'duration': item.duracion_minutos,
                'documents': item.documentos_requeridos or '',
                'active': item.activo,
            } for item in procedures],
        })
    data = _body(request)
    action = data.get('action')
    if action == 'create_section':
        ok, message, _ = TramiteNegocio.crear_seccion(data.get('name'))
    elif action == 'create_procedure':
        ok, message, _ = TramiteNegocio.crear_tramite(
            data.get('section_id'), data.get('name'), data.get('cost'),
            data.get('duration'), data.get('documents', ''),
        )
    elif action == 'toggle_procedure':
        ok, message, _ = TramiteNegocio.alternar_activo(data.get('procedure_id'))
    else:
        return JsonResponse({'error': 'Acción de catálogo no válida.'}, status=400)
    if not ok:
        return JsonResponse({'error': message}, status=400)
    registrar_log(request, 'INFO', message)
    return JsonResponse({'ok': True, 'message': message})

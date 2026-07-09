from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Sum, Count, Avg, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models.functions import TruncMonth, ExtractWeekDay
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction, IntegrityError
import json
import re
from datetime import datetime, date
from .models import BitacoraAuditoria, Cita, PagoCaja, Tramite, SeccionTramite, HorarioBloqueado, CorteCajaDiario
from .office_info import OFICINA_REGISTRO_CIVIL
from .comprobante_pdf import generar_comprobante_pdf
from .utils import (
    generar_slots_dia, citas_ocupadas_en_fecha, horarios_bloqueados_en_fecha,
    slot_disponible, validar_disponibilidad, format_minutes, obtener_ip,
    fin_jornada_minutos, pagos_para_ingresos, validar_fecha_agendado, rango_fechas_agendado,
)
from .auditoria import registrar_log, registrar_log_seguridad
from .validators import validar_curp
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST


# ==========================================
# 🛡️ CONTROL DE ACCESO
# ==========================================

def es_administrador(user):
    return user.is_superuser or user.groups.filter(name='Administrador').exists()

def es_oficial_o_admin(user):
    return user.is_superuser or user.groups.filter(name__in=['oficial', 'Administrador']).exists()

def es_capturista_o_superior(user):
    return user.is_superuser or user.groups.filter(name__in=['Capturista', 'oficial', 'Administrador']).exists()

def puede_cancelar_citas(user):
    return es_oficial_o_admin(user)

def puede_ver_panel_citas(user):
    """ Staff, capturista, oficial o administrador de grupo """
    return user.is_staff or es_capturista_o_superior(user) or es_oficial_o_admin(user)

def es_admin_o_super(user):
    return user.is_superuser or es_administrador(user)


# ==========================================
# 🏠 DASHBOARD DEL ADMINISTRADOR
# ==========================================

@login_required
def dashboard_personalizado(request):
    if not (request.user.is_staff or es_oficial_o_admin(request.user) or es_administrador(request.user)):
        return redirect('/admin/login/')
    hoy = timezone.now().date()
    contexto = {
        'titulo': 'Panel de Control - Registro Civil',
        'total_citas_hoy': Cita.objects.filter(fecha=hoy).count(),
        'citas_pendientes': Cita.objects.filter(fecha=hoy, estado='PENDIENTE').count(),
        'citas_en_caja': Cita.objects.filter(fecha=hoy, estado='ASISTIDA').count(),
        'citas_pagadas': Cita.objects.filter(fecha=hoy, estado='PAGADA').count(),
        'citas_finalizadas': Cita.objects.filter(fecha=hoy, estado='FINALIZADA').count(),
        'ingresos_hoy': pagos_para_ingresos().filter(
            fecha_pago__date=hoy
        ).aggregate(Sum('monto_cobrado'))['monto_cobrado__sum'] or 0,
        'citas_hoy': Cita.objects.filter(fecha=hoy).select_related('tramite').order_by('hora'),
    }
    return render(request, 'citas/dashboard_personalizado.html', contexto)


# ==========================================
# 📅 AGENDA (HU-3)
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def vista_agenda(request):
    hoy = timezone.now().date()
    citas_hoy = Cita.objects.filter(
        estado='PENDIENTE',
    ).select_related('tramite__seccion').order_by('fecha', 'hora')
    return render(request, 'citas/agenda.html', {
        'citas': citas_hoy,
        'hoy': hoy,
        'puede_revertir': es_oficial_o_admin(request.user),
    })


# ==========================================
# 📷 ESCÁNER QR (HU-3)
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def vista_escanear_qr(request, cita_id=None):
    return render(request, 'citas/escanear_qr.html')

def validar_cita(request, cita_id, token=None):
    """ Vista pública de consulta — no modifica el estado de la cita (HU-4). """
    cita = get_object_or_404(Cita, id=cita_id)
    token_valido = None
    if token is not None:
        token_valido = str(cita.qr_codigo) == str(token)
    return render(request, 'citas/validar.html', {
        'cita': cita,
        'token_valido': token_valido,
    })

@login_required
@user_passes_test(es_capturista_o_superior)
@require_POST
def procesar_validacion_qr(request, cita_id):
    try:
        cita = Cita.objects.get(id=cita_id)
        token = (request.POST.get('token') or '').strip()
        if not token or str(cita.qr_codigo) != token:
            registrar_log(
                request, 'SEGURIDAD',
                f"QR rechazado: token inválido para cita #{cita_id}.",
            )
            return JsonResponse({'status': 'error', 'message': 'Código QR no válido o alterado.'})
        if cita.estado == 'PENDIENTE':
            cita.estado = 'ASISTIDA'
            cita.usuario_atendio = request.user
            cita.save()
            registrar_log(
                request, 'MODIFICACION_CITA',
                f"Cita #{cita.id} ({cita.nombre_ciudadano}) marcada como ASISTIDA por validación QR."
            )
            return JsonResponse({
                'status': 'success',
                'ciudadano': cita.nombre_ciudadano,
                'tramite': cita.tramite.nombre,
                'cita_id': cita.id,
                'nuevo_estado': 'ASISTIDA',
            })
        registrar_log(
            request, 'MODIFICACION_CITA',
            f"Intento QR rechazado: cita #{cita.id} ya en estado {cita.estado}.",
        )
        return JsonResponse({'status': 'error', 'message': f'La cita ya está como: {cita.estado}'})
    except Cita.DoesNotExist:
        registrar_log(
            request, 'SEGURIDAD',
            f"Intento de validación QR con folio inexistente (#{cita_id}).",
        )
        return JsonResponse({'status': 'error', 'message': 'Código QR no reconocido.'})


# ==========================================
# 💰 CAJA (HU-4 y HU-8)
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def vista_fila_caja(request):
    fila_espera = Cita.objects.filter(estado='ASISTIDA').select_related('tramite__seccion').order_by('hora')
    return render(request, 'citas/fila_caja.html', {'fila': fila_espera})

@login_required
@user_passes_test(es_capturista_o_superior)
@require_POST
def registrar_pago_ventanilla(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    if cita.estado != 'ASISTIDA':
        registrar_log(
            request, 'TRANSACCION',
            f"Cobro rechazado cita #{cita_id}: estado {cita.estado}.",
        )
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': f'La cita está en estado {cita.estado}.'})
        return redirect('fila_caja')
    try:
        with transaction.atomic():
            PagoCaja.objects.create(
                cita=cita,
                monto_cobrado=cita.tramite.costo,
                cajero=request.user
            )
            cita.estado = 'PAGADA'
            cita.save()
    except IntegrityError:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': 'Esta cita ya tiene un pago registrado.'})
        messages.error(request, 'Esta cita ya tiene un pago registrado.')
        return redirect('fila_caja')
    registrar_log(
        request, 'TRANSACCION',
        f"Cobro de ${cita.tramite.costo} registrado para cita #{cita.id} ({cita.nombre_ciudadano})."
    )
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cita_id': cita.id, 'nuevo_estado': 'PAGADA'})
    return redirect('fila_caja')

@login_required
@user_passes_test(es_oficial_o_admin)
@require_POST
def finalizar_cita(request, cita_id):
    """ El Oficial marca el trámite como completamente finalizado """
    cita = get_object_or_404(Cita, id=cita_id)
    if cita.estado == 'PAGADA':
        cita.estado = 'FINALIZADA'
        cita.save()
        registrar_log(
            request, 'MODIFICACION_CITA',
            f"Cita #{cita.id} ({cita.nombre_ciudadano}) marcada como FINALIZADA."
        )
        messages.success(request, f"Trámite de {cita.nombre_ciudadano} finalizado.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'cita_id': cita.id, 'nuevo_estado': 'FINALIZADA'})
    elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        registrar_log(
            request, 'MODIFICACION_CITA',
            f"Finalización rechazada cita #{cita_id}: estado {cita.estado}.",
        )
        return JsonResponse({'ok': False, 'error': f'La cita está en estado {cita.estado}.'})
    return redirect('vista_citas_pagadas')

@login_required
@user_passes_test(puede_cancelar_citas)
@require_POST
def cancelar_cita(request, cita_id):
    """ Admin u oficial cancela una cita (no permitido si ya está finalizada). """
    cita = get_object_or_404(Cita, id=cita_id)
    if cita.estado == 'FINALIZADA':
        msg = 'No se puede cancelar una cita que ya fue finalizada.'
    elif cita.estado == 'CANCELADA':
        msg = 'Esta cita ya está cancelada.'
    elif not cita.puede_cancelarse():
        msg = f'No se puede cancelar una cita en estado {cita.estado}.'
    else:
        monto_descontado = None
        if cita.estado == 'PAGADA':
            try:
                monto_descontado = cita.pagocaja.monto_cobrado
            except ObjectDoesNotExist:
                pass
        cita.estado = 'CANCELADA'
        cita.save(update_fields=['estado'])
        desc_log = f"Cita #{cita.id} ({cita.nombre_ciudadano}) cancelada por {request.user.username}."
        if monto_descontado is not None:
            desc_log += f" Ingreso descontado: ${monto_descontado}."
        registrar_log(request, 'MODIFICACION_CITA', desc_log)
        ok_msg = 'Cita cancelada correctamente.'
        if monto_descontado is not None:
            ok_msg += f' Se descontó ${monto_descontado} de los ingresos.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'cita_id': cita.id,
                'nuevo_estado': 'CANCELADA',
                'message': ok_msg,
                'ingreso_descontado': float(monto_descontado) if monto_descontado is not None else None,
            })
        messages.success(request, ok_msg)
        return redirect(request.META.get('HTTP_REFERER', 'dashboard_oficial'))

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        registrar_log(request, 'MODIFICACION_CITA', f"Cancelación rechazada cita #{cita_id}: {msg}")
        return JsonResponse({'ok': False, 'error': msg}, status=400)
    registrar_log(request, 'MODIFICACION_CITA', f"Cancelación rechazada cita #{cita_id}: {msg}")
    messages.error(request, msg)
    return redirect(request.META.get('HTTP_REFERER', 'dashboard_oficial'))

@login_required
@user_passes_test(es_oficial_o_admin)
@require_POST
def revertir_asistencia_cita(request, cita_id):
    """ HU-4: Solo Oficial o Administrador revierten una asistencia marcada por error. """
    cita = get_object_or_404(Cita, id=cita_id)
    if cita.estado != 'ASISTIDA':
        msg = f'Solo se puede revertir una cita en estado Asistida (actual: {cita.estado}).'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect(request.META.get('HTTP_REFERER', 'vista_agenda'))
    cita.estado = 'PENDIENTE'
    cita.usuario_atendio = None
    cita.save(update_fields=['estado', 'usuario_atendio'])
    registrar_log(
        request, 'CANCELACION_ERROR',
        f"Asistencia revertida: cita #{cita.id} ({cita.nombre_ciudadano}) regresó a PENDIENTE.",
    )
    ok_msg = 'Asistencia revertida. La cita volvió a estado Pendiente.'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cita_id': cita.id, 'nuevo_estado': 'PENDIENTE', 'message': ok_msg})
    messages.success(request, ok_msg)
    return redirect(request.META.get('HTTP_REFERER', 'vista_agenda'))

@login_required
@user_passes_test(es_oficial_o_admin)
def vista_citas_pagadas(request):
    """ Lista de citas PAGADAS pendientes de finalizar """
    citas = Cita.objects.filter(
        estado='PAGADA'
    ).select_related('tramite__seccion', 'pagocaja').order_by('fecha', 'hora')
    for cita in citas:
        try:
            cita.monto_pagado = cita.pagocaja.monto_cobrado
        except ObjectDoesNotExist:
            cita.monto_pagado = cita.tramite.costo
    return render(request, 'citas/citas_pagadas.html', {'citas': citas})


MESES_ESPANOL = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre',
}


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_historial_finalizadas(request, anio=None, mes=None):
    """ Historial de citas finalizadas agrupado por mes (resumen + detalle). """
    totales_globales = Cita.objects.filter(estado='FINALIZADA').aggregate(
        total_citas=Count('id'),
        total_ingresos=Sum('pagocaja__monto_cobrado'),
    )
    resumen_meses = (
        Cita.objects.filter(estado='FINALIZADA')
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(
            cantidad=Count('id'),
            ingresos=Sum('pagocaja__monto_cobrado'),
        )
        .order_by('-mes')
    )
    meses = []
    for item in resumen_meses:
        dt = item['mes']
        if not dt:
            continue
        meses.append({
            'anio': dt.year,
            'mes': dt.month,
            'etiqueta': f"{MESES_ESPANOL.get(dt.month, 'Mes')} {dt.year}",
            'cantidad': item['cantidad'],
            'ingresos': item['ingresos'] or 0,
        })

    contexto = {
        'meses': meses,
        'total_global_citas': totales_globales['total_citas'] or 0,
        'total_global_ingresos': totales_globales['total_ingresos'] or 0,
        'mes_detalle': None,
        'citas_mes': [],
        'mes_nombre': '',
        'anio': None,
        'mes': None,
        'total_mes_citas': 0,
        'total_mes_ingresos': 0,
    }

    if anio is not None and mes is not None:
        citas_qs = (
            Cita.objects.filter(estado='FINALIZADA', fecha__year=anio, fecha__month=mes)
            .select_related('tramite__seccion')
            .order_by('-fecha', '-hora')
        )
        citas = list(citas_qs)
        total_ingresos = 0
        for cita in citas:
            try:
                cita.monto_pagado = cita.pagocaja.monto_cobrado
            except ObjectDoesNotExist:
                cita.monto_pagado = cita.tramite.costo
            total_ingresos += cita.monto_pagado

        contexto.update({
            'mes_detalle': True,
            'citas_mes': citas,
            'mes_nombre': MESES_ESPANOL.get(mes, 'Mes'),
            'anio': anio,
            'mes': mes,
            'total_mes_citas': len(citas),
            'total_mes_ingresos': total_ingresos,
        })

    return render(request, 'citas/historial_finalizadas.html', contexto)


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_historial_canceladas(request, anio=None, mes=None):
    """ Historial de citas canceladas agrupado por mes (resumen + detalle). """
    total_global = Cita.objects.filter(estado='CANCELADA').count()
    resumen_meses = (
        Cita.objects.filter(estado='CANCELADA')
        .annotate(mes=TruncMonth('fecha'))
        .values('mes')
        .annotate(cantidad=Count('id'))
        .order_by('-mes')
    )
    meses = []
    for item in resumen_meses:
        dt = item['mes']
        if not dt:
            continue
        meses.append({
            'anio': dt.year,
            'mes': dt.month,
            'etiqueta': f"{MESES_ESPANOL.get(dt.month, 'Mes')} {dt.year}",
            'cantidad': item['cantidad'],
        })

    contexto = {
        'meses': meses,
        'total_global_citas': total_global,
        'mes_detalle': None,
        'citas_mes': [],
        'mes_nombre': '',
        'anio': None,
        'mes': None,
        'total_mes_citas': 0,
    }

    if anio is not None and mes is not None:
        citas = list(
            Cita.objects.filter(estado='CANCELADA', fecha__year=anio, fecha__month=mes)
            .select_related('tramite__seccion')
            .order_by('-fecha', '-hora')
        )
        contexto.update({
            'mes_detalle': True,
            'citas_mes': citas,
            'mes_nombre': MESES_ESPANOL.get(mes, 'Mes'),
            'anio': anio,
            'mes': mes,
            'total_mes_citas': len(citas),
        })

    return render(request, 'citas/historial_canceladas.html', contexto)


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_bitacora(request):
    """Bitácora de auditoría — solo lectura, con filtros."""
    qs = BitacoraAuditoria.objects.select_related('usuario').order_by('-fecha_hora')

    q = request.GET.get('q', '').strip()
    accion = request.GET.get('accion', '').strip()
    usuario = request.GET.get('usuario', '').strip()

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

    paginator = Paginator(qs, 50)
    registros = paginator.get_page(request.GET.get('page'))

    usuarios = (
        BitacoraAuditoria.objects.exclude(usuario__isnull=True)
        .values_list('usuario__username', flat=True)
        .distinct()
        .order_by('usuario__username')
    )

    return render(request, 'citas/bitacora.html', {
        'registros': registros,
        'usuarios': usuarios,
        'acciones': BitacoraAuditoria.TIPO_ACCION_CHOICES,
        'filtro_q': q,
        'filtro_accion': accion,
        'filtro_usuario': usuario,
    })


# ==========================================
# ⚙️ CATÁLOGO (HU-5)
# ==========================================

@login_required
@user_passes_test(es_admin_o_super)
def agregar_elemento_catalogo(request):
    if request.method == 'POST':
        if 'btn_crear_seccion' in request.POST:
            nombre_seccion = request.POST.get('nombre_seccion', '').strip()
            if nombre_seccion:
                SeccionTramite.objects.get_or_create(nombre=nombre_seccion)
                registrar_log(request, 'INFO', f"Sección de catálogo creada: '{nombre_seccion}'.")
                messages.success(request, f"Sección '{nombre_seccion}' creada correctamente.")
                return redirect('agregar_elemento_catalogo')

        elif 'btn_crear_tramite' in request.POST:
            seccion_id = request.POST.get('seccion_asociada')
            nombre_tramite = request.POST.get('nombre_tramite', '').strip()
            costo_tramite = request.POST.get('costo_tramite', 0)
            duracion = request.POST.get('duracion_tramite', 15)
            documentos = request.POST.get('documentos_tramite', '').strip()
            if seccion_id and nombre_tramite:
                seccion = SeccionTramite.objects.get(id=seccion_id)
                Tramite.objects.create(
                    seccion=seccion,
                    nombre=nombre_tramite,
                    costo=costo_tramite,
                    duracion_minutos=int(duracion) if duracion else 15,
                    documentos_requeridos=documentos or None,
                )
                registrar_log(
                    request, 'MODIFICACION_COSTO',
                    f"Trámite creado: '{nombre_tramite}' en '{seccion.nombre}' (${costo_tramite}).",
                )
                messages.success(request, f"Opción '{nombre_tramite}' vinculada con éxito.")
                return redirect('agregar_elemento_catalogo')

        elif 'btn_editar_tramite' in request.POST:
            tramite_id = request.POST.get('tramite_id')
            tramite = get_object_or_404(Tramite, id=tramite_id)
            costo_anterior = tramite.costo
            tramite.nombre = request.POST.get('nombre_tramite', tramite.nombre).strip()
            tramite.costo = request.POST.get('costo_tramite', tramite.costo)
            tramite.duracion_minutos = int(request.POST.get('duracion_tramite', tramite.duracion_minutos) or 15)
            tramite.documentos_requeridos = request.POST.get('documentos_tramite', '').strip() or None
            seccion_id = request.POST.get('seccion_asociada')
            if seccion_id:
                tramite.seccion = SeccionTramite.objects.get(id=seccion_id)
            try:
                tramite.save()
            except ValidationError as exc:
                messages.error(request, '; '.join(getattr(exc, 'messages', [str(exc)])))
                return redirect('agregar_elemento_catalogo')
            if costo_anterior != tramite.costo:
                registrar_log(
                    request, 'MODIFICACION_COSTO',
                    f"Trámite '{tramite.nombre}': costo ${costo_anterior} → ${tramite.costo}.",
                )
            else:
                registrar_log(request, 'INFO', f"Trámite actualizado: '{tramite.nombre}'.")
            messages.success(request, f"Trámite '{tramite.nombre}' actualizado.")
            return redirect('agregar_elemento_catalogo')

        elif 'btn_toggle_tramite' in request.POST:
            tramite = get_object_or_404(Tramite, id=request.POST.get('tramite_id'))
            if tramite.activo and tramite.tiene_citas_pendientes_futuras():
                messages.error(
                    request,
                    f"No se puede desactivar '{tramite.nombre}': tiene citas futuras Pendientes.",
                )
                return redirect('agregar_elemento_catalogo')
            tramite.activo = not tramite.activo
            try:
                tramite.save()
            except ValidationError as exc:
                messages.error(request, '; '.join(exc.messages))
                return redirect('agregar_elemento_catalogo')
            estado_txt = 'activado' if tramite.activo else 'desactivado'
            registrar_log(request, 'INFO', f"Trámite '{tramite.nombre}' {estado_txt}.")
            messages.success(request, f"Trámite '{tramite.nombre}' {estado_txt}.")
            return redirect('agregar_elemento_catalogo')

    secciones = SeccionTramite.objects.all().order_by('nombre')
    tramites = Tramite.objects.select_related('seccion').order_by('seccion__nombre', 'nombre', '-activo')
    return render(request, 'citas/agregar_catalogo.html', {
        'secciones': secciones,
        'tramites': tramites,
    })


# ==========================================
# 📊 REPORTES FINANCIEROS (HU-8)
# ==========================================

@login_required
@user_passes_test(es_oficial_o_admin)
def vista_reporte_caja(request, anio=None, mes=None):
    ahora = timezone.now()
    anio_filtrar = int(anio) if anio else ahora.year
    mes_filtrar = int(mes) if mes else ahora.month
    es_mes_actual = (anio_filtrar == ahora.year and mes_filtrar == ahora.month)

    pagos_mes = pagos_para_ingresos().filter(
        fecha_pago__year=anio_filtrar,
        fecha_pago__month=mes_filtrar,
        cita__tramite__isnull=False,
        cita__tramite__seccion__isnull=False
    ).select_related('cita__tramite__seccion', 'cajero')

    total_acumulado = pagos_mes.aggregate(Sum('monto_cobrado'))['monto_cobrado__sum'] or 0
    total_tramites = pagos_mes.count()
    usuarios_activos = pagos_mes.values('cajero').distinct().count()
    promedio_duracion = pagos_mes.aggregate(prom=Avg('cita__tramite__duracion_minutos'))['prom']
    tiempo_promedio = round(promedio_duracion) if promedio_duracion else 0

    citas_por_dia = (
        pagos_mes.annotate(dia_sem=ExtractWeekDay('fecha_pago'))
        .values('dia_sem')
        .annotate(total=Count('id'))
    )
    dias_datos = [0] * 7
    for c in citas_por_dia:
        dias_datos[c['dia_sem'] - 1] = c['total']
    datos_semana_reales = [dias_datos[1], dias_datos[2], dias_datos[3],
                           dias_datos[4], dias_datos[5], dias_datos[6], dias_datos[0]]
    datos_semana_json = json.dumps(datos_semana_reales)

    reporte_por_tramite = (
        pagos_mes.values('cita__tramite__seccion__nombre', 'cita__tramite__nombre')
        .annotate(cantidad_solicitudes=Count('id'), dinero_recaudado=Sum('monto_cobrado'))
        .order_by('-cantidad_solicitudes')
    )

    reporte_por_seccion = (
        pagos_mes.values('cita__tramite__seccion__nombre')
        .annotate(cantidad=Count('id'))
        .order_by('-cantidad')
    )

    labels_top, cantidades_top, otros_total = [], [], 0
    for i, item in enumerate(reporte_por_seccion):
        nombre = item['cita__tramite__seccion__nombre'] or 'General'
        if i < 3:
            labels_top.append(nombre)
            cantidades_top.append(item['cantidad'])
        else:
            otros_total += item['cantidad']
    if otros_total > 0:
        labels_top.append('Otros')
        cantidades_top.append(otros_total)

    meses_con_datos = (
        pagos_para_ingresos().annotate(month=TruncMonth('fecha_pago'))
        .values('month').annotate(total=Count('id')).order_by('-month')
    )

    meses_espanol = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    meses_historial = []
    for item in meses_con_datos:
        dt = item['month']
        meses_historial.append({
            'anio': dt.year,
            'mes': dt.month,
            'etiqueta': f"{meses_espanol.get(dt.month, 'Mes')} {dt.year}",
        })

    hoy = ahora.date()
    pagos_hoy = pagos_para_ingresos().filter(fecha_pago__date=hoy)
    desglose_hoy = list(
        pagos_hoy.values('cita__tramite__nombre', 'cita__tramite__seccion__nombre')
        .annotate(cantidad=Count('id'), total=Sum('monto_cobrado'))
        .order_by('-total')
    )
    total_hoy = pagos_hoy.aggregate(t=Sum('monto_cobrado'))['t'] or 0
    corte_hoy = CorteCajaDiario.objects.filter(fecha=hoy).first()
    cortes_historial = CorteCajaDiario.objects.all().order_by('-fecha')[:12]

    return render(request, 'citas/reporte_caja.html', {
        'total_acumulado': total_acumulado,
        'total_tramites': total_tramites,
        'usuarios_activos': usuarios_activos,
        'tiempo_promedio': tiempo_promedio,
        'reporte_tramites': reporte_por_tramite,
        'mes_nombre': meses_espanol.get(mes_filtrar, "Mes Desconocido"),
        'anio': anio_filtrar,
        'es_mes_actual': es_mes_actual,
        'meses_historial': meses_historial,
        'datos_semana_json': datos_semana_json,
        'labels_grafica_json': json.dumps(labels_top),
        'datos_grafica_json': json.dumps(cantidades_top),
        'corte_hoy': corte_hoy,
        'desglose_hoy': desglose_hoy,
        'total_hoy': total_hoy,
        'fecha_hoy': hoy,
        'cortes_historial': cortes_historial,
    })


@login_required
@user_passes_test(es_oficial_o_admin)
@require_POST
def cerrar_corte_diario(request):
    """ HU-8: Genera corte de caja diario inmutable desglosado por trámite. """
    fecha_str = request.POST.get('fecha')
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
    except ValueError:
        fecha = timezone.now().date()

    if CorteCajaDiario.objects.filter(fecha=fecha).exists():
        messages.warning(request, f'El corte del {fecha} ya fue cerrado.')
        return redirect('reporte_caja')

    pagos = pagos_para_ingresos().filter(fecha_pago__date=fecha, corte_cierre_listo=False)
    if not pagos.exists():
        messages.warning(request, f'No hay pagos pendientes de corte para el {fecha}.')
        return redirect('reporte_caja')

    desglose_qs = (
        pagos.values('cita__tramite__nombre', 'cita__tramite__seccion__nombre')
        .annotate(cantidad=Count('id'), total=Sum('monto_cobrado'))
        .order_by('-total')
    )
    desglose = [
        {
            'tramite': item['cita__tramite__nombre'],
            'seccion': item['cita__tramite__seccion__nombre'],
            'cantidad': item['cantidad'],
            'total': float(item['total'] or 0),
        }
        for item in desglose_qs
    ]
    total = pagos.aggregate(t=Sum('monto_cobrado'))['t'] or 0
    cantidad = pagos.count()

    with transaction.atomic():
        CorteCajaDiario.objects.create(
            fecha=fecha,
            total_recaudado=total,
            desglose_tramites=desglose,
            cantidad_pagos=cantidad,
            cerrado_por=request.user,
        )
        pagos.update(corte_cierre_listo=True)

    registrar_log(
        request, 'CIERRE_CORTE',
        f"Corte diario {fecha}: ${total} en {cantidad} pago(s).",
    )
    messages.success(request, f'Corte del {fecha} cerrado correctamente (${total}).')
    return redirect('reporte_caja')

# ==========================================
# 👤 REGISTRO (HU-6)
# ==========================================

@login_required
@user_passes_test(es_admin_o_super)
def vista_registrar(request):
    return redirect('admin:autenticacion_usuarioregistrocivil_add')


# ==========================================
# 🌐 PORTAL CIUDADANO
# ==========================================

@ensure_csrf_cookie
def portal_agendar(request):
    """ Vista principal del portal ciudadano (sin login) """
    return render(request, 'citas/agendar.html', {'oficina': OFICINA_REGISTRO_CIVIL})


def _serializar_tramite(tramite):
    return {
        'id': tramite.id,
        'nombre': tramite.nombre,
        'costo': float(tramite.costo),
        'duracion_minutos': tramite.duracion_minutos,
        'documentos': tramite.documentos_requeridos or '',
    }


def api_tramites(request):
    """ API: Devuelve todos los trámites activos agrupados por sección """
    tramites_qs = (
        Tramite.objects.filter(activo=True)
        .select_related('seccion')
        .order_by('seccion__nombre', 'nombre')
    )
    grupos = {}
    orden = []
    for tramite in tramites_qs:
        clave = tramite.seccion_id or 0
        if clave not in grupos:
            nombre_sec = tramite.seccion.nombre if tramite.seccion else 'Otros trámites'
            grupos[clave] = {'nombre': nombre_sec, 'tramites': []}
            orden.append(clave)
        grupos[clave]['tramites'].append(_serializar_tramite(tramite))

    response = JsonResponse({'secciones': [grupos[k] for k in orden]})
    response['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return response


def api_horarios(request):
    """ API: Horarios del día respetando la duración del trámite seleccionado """
    fecha = request.GET.get('fecha')
    tramite_id = request.GET.get('tramite_id')
    if not fecha:
        return JsonResponse({'error': 'Falta la fecha'}, status=400)
    if not tramite_id:
        return JsonResponse({'error': 'Selecciona un trámite para consultar horarios.'}, status=400)

    try:
        tramite_id_int = int(tramite_id)
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Trámite no válido.'}, status=400)

    try:
        tramite = Tramite.objects.get(id=tramite_id_int, activo=True)
        duracion = tramite.duracion_minutos
    except Tramite.DoesNotExist:
        return JsonResponse({'error': 'Trámite no encontrado.'}, status=400)

    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
    ok_fecha, err_fecha = validar_fecha_agendado(fecha_obj)
    if not ok_fecha:
        return JsonResponse({'error': err_fecha}, status=400)

    dia_semana = fecha_obj.weekday()

    tipo_bloqueo, bloqueos = horarios_bloqueados_en_fecha(fecha_obj)
    if tipo_bloqueo == 'dia_completo':
        return JsonResponse({'horarios': [], 'dia_bloqueado': True, 'duracion_minutos': duracion})

    fin_jornada = fin_jornada_minutos(dia_semana)
    if fin_jornada is None:
        return JsonResponse({'horarios': [], 'dia_bloqueado': True, 'duracion_minutos': duracion})

    slots_base = generar_slots_dia(dia_semana, duracion)
    intervalos_ocupados = citas_ocupadas_en_fecha(fecha_obj)

    horarios = []
    for inicio in slots_base:
        disponible = slot_disponible(inicio, duracion, fin_jornada, intervalos_ocupados, bloqueos)
        horarios.append({
            'hora': format_minutes(inicio),
            'ocupado': not disponible,
            'duracion_minutos': duracion,
        })

    return JsonResponse({
        'horarios': horarios,
        'dia_bloqueado': False,
        'duracion_minutos': duracion,
        'intervalo_minutos': duracion,
        'fecha_min': rango_fechas_agendado()[0].isoformat(),
        'fecha_max': rango_fechas_agendado()[1].isoformat(),
    })


@require_POST
def api_crear_cita(request):
    """ API: Crea la cita y devuelve folio + URL del QR """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    tramite_id  = body.get('tramite_id')
    nombre      = body.get('nombre', '').strip()
    curp        = (body.get('curp', '') or '').strip().upper()
    cp          = body.get('cp', '').strip()
    direccion   = body.get('direccion', '').strip()
    fecha       = body.get('fecha')
    hora        = body.get('hora')

    if not all([tramite_id, nombre, curp, cp, direccion, fecha, hora]):
        return JsonResponse({'ok': False, 'error': 'Faltan datos requeridos.'})
    try:
        curp = validar_curp(curp)
    except ValidationError as exc:
        return JsonResponse({'ok': False, 'error': exc.messages[0]})
    if not re.match(r'^[0-9]{5}$', cp):
        return JsonResponse({'ok': False, 'error': 'Código postal inválido.'})

    # Validar que el horario no esté bloqueado por el oficial (defensa adicional)
    fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
    ok_fecha, err_fecha = validar_fecha_agendado(fecha_obj)
    if not ok_fecha:
        return JsonResponse({'ok': False, 'error': err_fecha})
    if HorarioBloqueado.objects.filter(fecha=fecha_obj, hora__isnull=True).exists():
        return JsonResponse({'ok': False, 'error': 'Ese día no está disponible para citas.'})
    if HorarioBloqueado.objects.filter(fecha=fecha_obj, hora=hora).exists():
        return JsonResponse({'ok': False, 'error': 'Ese horario ya no está disponible.'})

    try:
        tramite = Tramite.objects.get(id=tramite_id, activo=True)
    except Tramite.DoesNotExist:
        return JsonResponse({'ok': False, 'error': 'Trámite no encontrado.'})

    valido, error = validar_disponibilidad(fecha_obj, hora, tramite.duracion_minutos)
    if not valido:
        return JsonResponse({'ok': False, 'error': error})

    try:
        cita = Cita(
            tramite=tramite,
            nombre_ciudadano=nombre,
            curp_ciudadano=curp,
            codigo_postal=cp,
            direccion=direccion,
            fecha=fecha,
            hora=hora,
            estado='PENDIENTE',
        )
        cita.save()  # full_clean + genera QR automáticamente por el modelo
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)})

    qr_url = request.build_absolute_uri(cita.codigo_qr.url) if cita.codigo_qr else ''
    pdf_url = request.build_absolute_uri(f'/citas/comprobante/{cita.id}/pdf/')

    return JsonResponse({
        'ok': True,
        'folio': cita.id,
        'qr_url': qr_url,
        'pdf_url': pdf_url,
    })


def descargar_comprobante_pdf(request, cita_id):
    """Descarga el comprobante de cita en PDF (datos + QR)."""
    cita = get_object_or_404(Cita.objects.select_related('tramite'), pk=cita_id)
    if cita.estado == 'CANCELADA':
        return JsonResponse({'error': 'Esta cita fue cancelada.'}, status=404)
    try:
        pdf_buffer = generar_comprobante_pdf(cita)
    except Exception as e:
        return JsonResponse({'error': f'No se pudo generar el PDF: {e}'}, status=500)
    response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="comprobante_cita_folio_{cita.id}.pdf"'
    return response


@login_required
@user_passes_test(puede_ver_panel_citas)
def api_citas_estado(request):
    """ API JSON para actualización en tiempo real de citas """
    hoy = timezone.now().date()
    estado_filtro = request.GET.get('estado')
    qs = Cita.objects.select_related('tramite', 'tramite__seccion')
    if estado_filtro:
        estados = [e.strip() for e in estado_filtro.split(',')]
        qs = qs.filter(estado__in=estados)
    else:
        qs = qs.filter(fecha=hoy)
    citas = []
    for c in qs.order_by('fecha', 'hora')[:100]:
        citas.append({
            'id': c.id,
            'hora': c.hora.strftime('%H:%M'),
            'fecha': c.fecha.isoformat(),
            'nombre': c.nombre_ciudadano,
            'curp': c.curp_ciudadano,
            'tramite': c.tramite.nombre,
            'seccion': c.tramite.seccion.nombre if c.tramite.seccion else '',
            'estado': c.estado,
            'puede_cancelar': c.puede_cancelarse(),
            'costo': float(c.tramite.costo),
        })
    return JsonResponse({'citas': citas, 'timestamp': timezone.now().isoformat()})


@login_required
@user_passes_test(puede_ver_panel_citas)
def api_resumen_dashboard(request):
    """ Contadores en tiempo real para dashboards """
    hoy = timezone.now().date()
    return JsonResponse({
        'total_citas_hoy': Cita.objects.filter(fecha=hoy).count(),
        'citas_pendientes': Cita.objects.filter(fecha=hoy, estado='PENDIENTE').count(),
        'citas_en_caja': Cita.objects.filter(fecha=hoy, estado='ASISTIDA').count(),
        'citas_pagadas': Cita.objects.filter(fecha=hoy, estado='PAGADA').count(),
        'citas_finalizadas': Cita.objects.filter(fecha=hoy, estado='FINALIZADA').count(),
        'ingresos_hoy': float(
            pagos_para_ingresos().filter(fecha_pago__date=hoy)
            .aggregate(Sum('monto_cobrado'))['monto_cobrado__sum'] or 0
        ),
    })


# ==========================================
# 🧑‍💼 DASHBOARDS POR ROL
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def dashboard_capturista(request):
    hoy = timezone.now().date()
    citas = Cita.objects.filter(
        fecha=hoy,
        estado__in=['PENDIENTE', 'ASISTIDA'],
    ).select_related('tramite__seccion').order_by('hora')
    return render(request, 'citas/dashboard_capturista.html', {
        'citas': citas,
        'hoy': hoy,
        'citas_pendientes': Cita.objects.filter(fecha=hoy, estado='PENDIENTE').count(),
        'oficina': OFICINA_REGISTRO_CIVIL,
    })


@login_required
@user_passes_test(es_oficial_o_admin)
def dashboard_oficial(request):
    hoy = timezone.now().date()
    contexto = {
        'hoy': hoy,
        'total_citas_hoy': Cita.objects.filter(fecha=hoy).count(),
        'citas_pendientes': Cita.objects.filter(fecha=hoy, estado='PENDIENTE').count(),
        'citas_en_caja': Cita.objects.filter(fecha=hoy, estado='ASISTIDA').count(),
        'citas_pagadas': Cita.objects.filter(fecha=hoy, estado='PAGADA').count(),
        'citas_finalizadas': Cita.objects.filter(fecha=hoy, estado='FINALIZADA').count(),
        'ingresos_hoy': pagos_para_ingresos().filter(
            fecha_pago__date=hoy
        ).aggregate(Sum('monto_cobrado'))['monto_cobrado__sum'] or 0,
        'citas_hoy': Cita.objects.filter(fecha=hoy).select_related('tramite').order_by('hora'),
    }
    return render(request, 'citas/dashboard_oficial.html', contexto)


# ==========================================
# 🗓️ GESTIÓN DE HORARIOS (RF-09)
# ==========================================

@login_required
@user_passes_test(es_oficial_o_admin)
def gestionar_horarios(request):
    """ Permite al Oficial bloquear días completos o horarios específicos """
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        tipo = request.POST.get('tipo')
        motivo = request.POST.get('motivo', '').strip()

        if not fecha or not tipo:
            messages.error(request, "Debes seleccionar una fecha y el tipo de bloqueo.")
            return redirect('gestionar_horarios')

        if tipo == 'dia_completo':
            obj, creado = HorarioBloqueado.objects.get_or_create(
                fecha=fecha, hora=None,
                defaults={'motivo': motivo, 'creado_por': request.user}
            )
            if creado:
                messages.success(request, f"📅 Día {fecha} bloqueado completamente.")
                registrar_log(request, 'INFO', f"Día {fecha} bloqueado completamente. Motivo: {motivo or 'Sin motivo'}.")
            else:
                messages.warning(request, "Ese día ya estaba bloqueado.")

        elif tipo == 'horario_especifico':
            horas = request.POST.getlist('hora')  # getlist en lugar de get
            if not horas:
               messages.error(request, "Debes seleccionar al menos una hora.")
               return redirect('gestionar_horarios')
    
            creados = 0
            for hora in horas:
                obj, creado = HorarioBloqueado.objects.get_or_create(
                    fecha=fecha, hora=hora,
                    defaults={'motivo': motivo, 'creado_por': request.user}
                )
                if creado:
                    creados += 1
    
            if creados > 0:
                messages.success(request, f"⏰ {creados} horario(s) bloqueados para el {fecha}.")
                registrar_log(request, 'INFO', f"{creados} horario(s) bloqueados para {fecha}. Motivo: {motivo or 'Sin motivo'}.")
            else:
                messages.warning(request, "Esos horarios ya estaban bloqueados.")

        return redirect('gestionar_horarios')

    bloqueos = HorarioBloqueado.objects.filter(
        fecha__gte=timezone.now().date()
    ).order_by('fecha', 'hora')

    

    return render(request, 'citas/gestionar_horarios.html', {'bloqueos': bloqueos})

@login_required
@user_passes_test(es_oficial_o_admin)
def eliminar_bloqueos_dia(request, fecha):
    cantidad = HorarioBloqueado.objects.filter(fecha=fecha).count()
    HorarioBloqueado.objects.filter(fecha=fecha).delete()
    registrar_log(request, 'INFO', f"Eliminados {cantidad} bloqueo(s) del día {fecha}.")
    messages.success(request, f"Todos los bloqueos del {fecha} eliminados.")
    return redirect('gestionar_horarios')

@login_required
@user_passes_test(es_oficial_o_admin)
def eliminar_bloqueo(request, bloqueo_id):
    bloqueo = get_object_or_404(HorarioBloqueado, id=bloqueo_id)
    desc = str(bloqueo)
    bloqueo.delete()
    registrar_log(request, 'INFO', f"Bloqueo eliminado: {desc}")
    messages.success(request, "Bloqueo eliminado correctamente.")
    return redirect('gestionar_horarios')


# ==========================================
# 🔁 REDIRECCIÓN POR ROL
# ==========================================

@login_required
def redirigir_por_rol(request):
    if request.user.is_superuser or es_administrador(request.user):
        return redirect('/admin/citas/dashboard/')
    elif request.user.groups.filter(name='oficial').exists():
        return redirect('/citas/oficial/')
    elif request.user.groups.filter(name='Capturista').exists():
        return redirect('/citas/capturista/')
    else:
        return redirect('/admin/login/')
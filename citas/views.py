from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone
from .models import Cita, Tramite, BitacoraAuditoria
from .office_info import OFICINA_REGISTRO_CIVIL
from .comprobante_pdf import generar_comprobante_pdf
from .auditoria import registrar_log
from .servicios import Bitacora, Caja, Calendario, CitaNegocio, QR, TramiteNegocio
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
import json
from datetime import datetime


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
    resumen = CitaNegocio.resumen_dashboard(hoy)
    contexto = {
        'titulo': 'Panel de Control - Registro Civil',
        'hoy': hoy,
        'mostrar_admin_sistema': es_administrador(request.user) or request.user.is_superuser,
        **resumen,
    }
    return render(request, 'citas/dashboard_personalizado.html', contexto)


# ==========================================
# 📅 AGENDA (HU-3)
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def vista_agenda(request):
    hoy = timezone.now().date()
    return render(request, 'citas/agenda.html', {
        'citas': CitaNegocio.listar_pendientes_agenda(incluir_futuras=True),
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
    token = (request.POST.get('token') or '').strip()
    ok, payload = QR.validar_y_marcar_asistida(cita_id, token, request.user)
    if 'log' in payload:
        registrar_log(request, payload['log'][0], payload['log'][1])
    if ok:
        return JsonResponse({
            'status': payload['status'],
            'ciudadano': payload['ciudadano'],
            'tramite': payload['tramite'],
            'cita_id': payload['cita_id'],
            'nuevo_estado': payload['nuevo_estado'],
        })
    return JsonResponse({'status': payload['status'], 'message': payload['message']})


# ==========================================
# 💰 CAJA (HU-4 y HU-8)
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def vista_fila_caja(request):
    return render(request, 'citas/fila_caja.html', {'fila': CitaNegocio.listar_fila_caja()})

@login_required
@user_passes_test(es_capturista_o_superior)
@require_POST
def registrar_pago_ventanilla(request, cita_id):
    cita = get_object_or_404(Cita, id=cita_id)
    ok, error = Caja.registrar_pago(cita, request.user)
    if not ok:
        registrar_log(request, 'TRANSACCION', f"Cobro rechazado cita #{cita_id}: {error}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': error})
        messages.error(request, error)
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
    ok, msg = CitaNegocio.finalizar(cita)
    if ok:
        registrar_log(request, 'MODIFICACION_CITA', msg)
        messages.success(request, f"Trámite de {cita.nombre_ciudadano} finalizado.")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': True, 'cita_id': cita.id, 'nuevo_estado': 'FINALIZADA'})
    elif request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        registrar_log(request, 'MODIFICACION_CITA', f"Finalización rechazada cita #{cita_id}: {msg}")
        return JsonResponse({'ok': False, 'error': msg})
    messages.error(request, msg)
    return redirect('vista_citas_pagadas')

@login_required
@user_passes_test(puede_cancelar_citas)
@require_POST
def cancelar_cita(request, cita_id):
    """ Admin u oficial cancela una cita (no permitido si ya está finalizada). """
    cita = get_object_or_404(Cita, id=cita_id)
    ok, msg, extra = CitaNegocio.cancelar(cita, request.user.username)
    if ok:
        registrar_log(request, 'MODIFICACION_CITA', extra['log'])
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'ok': True,
                'cita_id': cita.id,
                'nuevo_estado': extra['nuevo_estado'],
                'message': msg,
                'ingreso_descontado': extra['ingreso_descontado'],
            })
        messages.success(request, msg)
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
    ok, msg = CitaNegocio.revertir_asistencia(cita)
    if not ok:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'ok': False, 'error': msg}, status=400)
        messages.error(request, msg)
        return redirect(request.META.get('HTTP_REFERER', 'vista_agenda'))
    registrar_log(request, 'CANCELACION_ERROR', msg)
    ok_msg = 'Asistencia revertida. La cita volvió a estado Pendiente.'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'ok': True, 'cita_id': cita.id, 'nuevo_estado': 'PENDIENTE', 'message': ok_msg})
    messages.success(request, ok_msg)
    return redirect(request.META.get('HTTP_REFERER', 'vista_agenda'))

@login_required
@user_passes_test(es_oficial_o_admin)
def vista_citas_pagadas(request):
    return render(request, 'citas/citas_pagadas.html', {'citas': CitaNegocio.listar_pagadas()})


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_historial_finalizadas(request, anio=None, mes=None):
    return render(
        request,
        'citas/historial_finalizadas.html',
        CitaNegocio.historial_finalizadas(anio, mes),
    )


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_historial_canceladas(request, anio=None, mes=None):
    return render(
        request,
        'citas/historial_canceladas.html',
        CitaNegocio.historial_canceladas(anio, mes),
    )


@login_required
@user_passes_test(puede_ver_panel_citas)
def vista_bitacora(request):
    """Bitácora de auditoría — solo lectura, con filtros."""
    registros, usuarios = Bitacora.consultar(
        q=request.GET.get('q', '').strip(),
        accion=request.GET.get('accion', '').strip(),
        usuario=request.GET.get('usuario', '').strip(),
        page=request.GET.get('page'),
    )

    return render(request, 'citas/bitacora.html', {
        'registros': registros,
        'usuarios': usuarios,
        'acciones': BitacoraAuditoria.TIPO_ACCION_CHOICES,
        'filtro_q': request.GET.get('q', '').strip(),
        'filtro_accion': request.GET.get('accion', '').strip(),
        'filtro_usuario': request.GET.get('usuario', '').strip(),
    })


# ==========================================
# ⚙️ CATÁLOGO (HU-5)
# ==========================================

@login_required
@user_passes_test(es_admin_o_super)
def agregar_elemento_catalogo(request):
    if request.method == 'POST':
        if 'btn_crear_seccion' in request.POST:
            ok, msg, seccion = TramiteNegocio.crear_seccion(request.POST.get('nombre_seccion'))
            if ok:
                registrar_log(request, 'INFO', f"Sección de catálogo creada: '{seccion.nombre}'.")
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect('agregar_elemento_catalogo')

        elif 'btn_crear_tramite' in request.POST:
            ok, msg, tramite = TramiteNegocio.crear_tramite(
                request.POST.get('seccion_asociada'),
                request.POST.get('nombre_tramite'),
                request.POST.get('costo_tramite', 0),
                request.POST.get('duracion_tramite', 15),
                request.POST.get('documentos_tramite', ''),
            )
            if ok:
                registrar_log(
                    request, 'MODIFICACION_COSTO',
                    f"Trámite creado: '{tramite.nombre}' en '{tramite.seccion.nombre}' (${tramite.costo}).",
                )
                messages.success(request, msg)
            else:
                messages.error(request, msg)
            return redirect('agregar_elemento_catalogo')

        elif 'btn_editar_tramite' in request.POST:
            ok, msg, costo_anterior = TramiteNegocio.actualizar_tramite(
                request.POST.get('tramite_id'),
                {
                    'nombre': request.POST.get('nombre_tramite'),
                    'costo': request.POST.get('costo_tramite'),
                    'duracion': request.POST.get('duracion_tramite'),
                    'documentos': request.POST.get('documentos_tramite', ''),
                    'seccion_id': request.POST.get('seccion_asociada'),
                },
            )
            if not ok:
                messages.error(request, msg)
                return redirect('agregar_elemento_catalogo')
            tramite = Tramite.objects.get(id=request.POST.get('tramite_id'))
            if costo_anterior != tramite.costo:
                registrar_log(
                    request, 'MODIFICACION_COSTO',
                    f"Trámite '{tramite.nombre}': costo ${costo_anterior} → ${tramite.costo}.",
                )
            else:
                registrar_log(request, 'INFO', f"Trámite actualizado: '{tramite.nombre}'.")
            messages.success(request, msg)
            return redirect('agregar_elemento_catalogo')

        elif 'btn_toggle_tramite' in request.POST:
            ok, msg, estado_txt = TramiteNegocio.alternar_activo(request.POST.get('tramite_id'))
            if not ok:
                messages.error(request, msg)
                return redirect('agregar_elemento_catalogo')
            tramite = Tramite.objects.get(id=request.POST.get('tramite_id'))
            registrar_log(request, 'INFO', f"Trámite '{tramite.nombre}' {estado_txt}.")
            messages.success(request, msg)
            return redirect('agregar_elemento_catalogo')

    secciones, tramites = TramiteNegocio.listar_catalogo_admin()
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
    return render(request, 'citas/reporte_caja.html', Caja.reporte_mensual(anio, mes))


@login_required
@user_passes_test(es_oficial_o_admin)
@require_POST
def cerrar_corte_diario(request):
    """ HU-8: Genera corte de caja diario inmutable desglosado por trámite. """
    fecha = Caja.parsear_fecha_corte(request.POST.get('fecha'))
    ok, mensaje, datos = Caja.cerrar_corte_diario(fecha, request.user)
    if not ok:
        messages.warning(request, mensaje)
        return redirect('reporte_caja')
    registrar_log(
        request, 'CIERRE_CORTE',
        f"Corte diario {fecha}: ${datos['total']} en {datos['cantidad']} pago(s).",
    )
    messages.success(request, mensaje)
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
    return render(request, 'citas/agendar.html', {
        'oficina': OFICINA_REGISTRO_CIVIL,
        'dias_cancelacion_portal': CitaNegocio.DIAS_MINIMOS_CANCELACION_CIUDADANO,
    })


def api_tramites(request):
    """ API: Devuelve todos los trámites activos agrupados por sección """
    response = JsonResponse({'secciones': TramiteNegocio.listar_activos_agrupados()})
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
        tramite = TramiteNegocio.obtener_activo(tramite_id_int)
        duracion = tramite.duracion_minutos
    except Tramite.DoesNotExist:
        return JsonResponse({'error': 'Trámite no encontrado.'}, status=400)

    resultado = Calendario.horarios_para_fecha(fecha, duracion)
    if 'error' in resultado:
        return JsonResponse({'error': resultado['error']}, status=400)
    return JsonResponse(resultado)


@require_POST
def api_validar_curp_portal(request):
    """ API portal: verifica CURP y si ya tiene cita activa (estilo INE). """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'message': 'Datos inválidos.'}, status=400)
    ok, mensaje, extra = CitaNegocio.validar_curp_disponible(body.get('curp'))
    payload = {'ok': ok, 'message': mensaje}
    if extra:
        payload.update(extra)
    return JsonResponse(payload, status=200 if ok else 409)


@require_POST
def api_consultar_cita_portal(request):
    """ API portal: consulta cita por folio y CURP. """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    ok, error, datos = CitaNegocio.consultar_portal(body.get('folio'), body.get('curp'))
    if not ok:
        return JsonResponse({'ok': False, 'error': error}, status=404)
    if datos.get('pdf_url'):
        datos['pdf_url'] = request.build_absolute_uri(datos['pdf_url'])
    return JsonResponse({'ok': True, 'cita': datos})


@require_POST
def api_cancelar_cita_portal(request):
    """ API portal: cancela cita por folio y CURP (mínimo 7 días de anticipación). """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)
    ok, mensaje, datos = CitaNegocio.cancelar_desde_portal(body.get('folio'), body.get('curp'))
    if not ok:
        return JsonResponse({'ok': False, 'error': mensaje}, status=400)
    return JsonResponse({'ok': True, 'message': mensaje, 'cita': datos})


@require_POST
def api_crear_cita(request):
    """ API: Crea la cita y devuelve folio + URL del QR """
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Datos inválidos.'}, status=400)

    ok, resultado = CitaNegocio.crear_desde_portal(body)
    if not ok:
        return JsonResponse({'ok': False, 'error': resultado})

    cita = resultado
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
    fecha = None
    fecha_str = request.GET.get('fecha')
    if fecha_str:
        try:
            fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    if request.GET.get('incluir_futuras') in ('1', 'true', 'yes'):
        citas = CitaNegocio.serializar_agenda_operaciones(fecha)
    else:
        citas = CitaNegocio.serializar_para_api(request.GET.get('estado'), fecha=fecha)
    return JsonResponse({'citas': citas, 'timestamp': timezone.now().isoformat()})


@login_required
@user_passes_test(puede_ver_panel_citas)
def api_resumen_dashboard(request):
    return JsonResponse(CitaNegocio.resumen_dashboard())


# ==========================================
# 🧑‍💼 DASHBOARDS POR ROL
# ==========================================

@login_required
@user_passes_test(es_capturista_o_superior)
def dashboard_capturista(request):
    hoy = timezone.now().date()
    return render(request, 'citas/dashboard_capturista.html', {
        'citas_hoy': CitaNegocio.listar_del_dia(hoy, estados=['PENDIENTE', 'ASISTIDA']),
        'citas_agenda': CitaNegocio.listar_agenda_operaciones(hoy),
        'hoy': hoy,
        'citas_pendientes': CitaNegocio.resumen_dashboard(hoy)['citas_pendientes'],
        'oficina': OFICINA_REGISTRO_CIVIL,
    })


@login_required
@user_passes_test(es_oficial_o_admin)
def dashboard_oficial(request):
    hoy = timezone.now().date()
    return render(request, 'citas/dashboard_oficial.html', {
        'hoy': hoy,
        **CitaNegocio.resumen_dashboard(hoy),
    })


# ==========================================
# 🗓️ GESTIÓN DE HORARIOS (RF-09)
# ==========================================

@login_required
@user_passes_test(es_oficial_o_admin)
def gestionar_horarios(request):
    if request.method == 'POST':
        ok, msg, _ = Calendario.crear_bloqueo(
            request.POST.get('fecha'),
            request.POST.get('tipo'),
            request.POST.get('motivo', ''),
            request.user,
            horas=request.POST.getlist('hora'),
        )
        if ok:
            messages.success(request, msg)
            registrar_log(request, 'INFO', f"{msg} Motivo: {request.POST.get('motivo', '').strip() or 'Sin motivo'}.")
        elif msg.startswith('Debes'):
            messages.error(request, msg)
        else:
            messages.warning(request, msg)
        return redirect('gestionar_horarios')

    return render(request, 'citas/gestionar_horarios.html', {
        'bloqueos': Calendario.listar_bloqueos_futuros(),
    })

@login_required
@user_passes_test(es_oficial_o_admin)
def eliminar_bloqueos_dia(request, fecha):
    cantidad = Calendario.eliminar_bloqueos_dia(fecha)
    registrar_log(request, 'INFO', f"Eliminados {cantidad} bloqueo(s) del día {fecha}.")
    messages.success(request, f"Todos los bloqueos del {fecha} eliminados.")
    return redirect('gestionar_horarios')

@login_required
@user_passes_test(es_oficial_o_admin)
def eliminar_bloqueo(request, bloqueo_id):
    desc = Calendario.eliminar_bloqueo(bloqueo_id)
    registrar_log(request, 'INFO', f"Bloqueo eliminado: {desc}")
    messages.success(request, "Bloqueo eliminado correctamente.")
    return redirect('gestionar_horarios')


# ==========================================
# 🔁 REDIRECCIÓN POR ROL
# ==========================================

@login_required
def redirigir_por_rol(request):
    from autenticacion.servicios import Login
    return redirect(Login.url_panel_para_usuario(request.user))
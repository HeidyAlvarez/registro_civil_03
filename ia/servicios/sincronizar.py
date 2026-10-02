"""Genera notificaciones, casos urgentes, anomalías y propuestas. No modifica citas por sí solo."""

import datetime
from collections import defaultdict

from django.core.cache import cache
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from citas.auditoria import registrar_log
from citas.models import BitacoraAuditoria, Cita
from citas.office_info import OFICINA_REGISTRO_CIVIL
from citas.utils import (
    fin_jornada_minutos,
    format_minutes,
    get_intervalo_cita,
    slot_disponible,
)
from ia.models import (
    AlertaUrgente,
    Anomalia,
    EventoInvestigacion,
    NotificacionInteligente,
    PropuestaOptimizacion,
    ReglaPrioridad,
)
from ia.servicios.analitica import ocupacion_fecha
from ia.servicios.texto import es_tramite_sensible, normalizar

UMBRAL_ACTIVIDAD = 40
UMBRAL_MODIFICACIONES = 6
UMBRAL_ACCESOS = 5
UMBRAL_REGISTROS = 8
HORA_HABITUAL_DESDE = 8
HORA_HABITUAL_HASTA = 17

REGLAS_INICIALES = (
    {
        'nombre': 'Registro de defunción pendiente',
        'palabras_clave': 'defun',
        'minutos_umbral': 30,
        'estados': 'PENDIENTE,ASISTIDA',
        'solo_hoy': True,
        'accion_sugerida': 'Revisar solicitud.',
    },
    {
        'nombre': 'Solicitud del día sin seguimiento',
        'palabras_clave': '',
        'minutos_umbral': 180,
        'estados': 'PENDIENTE',
        'solo_hoy': True,
        'accion_sugerida': 'Verificar si la solicitud requiere atención conforme al procedimiento.',
    },
)


def asegurar_reglas():
    for datos in REGLAS_INICIALES:
        ReglaPrioridad.objects.get_or_create(
            nombre=datos['nombre'],
            defaults=datos,
        )


def sincronizar_si_hace_falta():
    if cache.get('ia_sync_reciente'):
        return
    sincronizar()
    cache.set('ia_sync_reciente', True, 300)


def sincronizar():
    asegurar_reglas()
    sincronizar_notificaciones()
    sincronizar_urgentes()
    sincronizar_anomalias()
    manana = timezone.localdate() + datetime.timedelta(days=1)
    generar_propuesta(manana)


def _crear_notificacion(**datos):
    clave = datos.pop('clave')
    NotificacionInteligente.objects.get_or_create(clave=clave, defaults=datos)


def sincronizar_notificaciones():
    hoy = timezone.localdate()
    manana = hoy + datetime.timedelta(days=1)
    citas_manana = Cita.objects.filter(fecha=manana, estado='PENDIENTE').select_related('tramite')
    for cita in citas_manana:
        hora = cita.hora.strftime('%H:%M')
        _crear_notificacion(
            clave=f'rec-{cita.id}',
            destino=NotificacionInteligente.CIUDADANO,
            curp=cita.curp_ciudadano,
            categoria=NotificacionInteligente.RECORDATORIO,
            titulo='Recordatorio de cita',
            mensaje=f'Tu cita es mañana a las {hora}.',
            cita=cita,
        )
        docs = (cita.tramite.documentos_requeridos or '').strip()
        if docs:
            mensaje = f'Recuerda presentar identificación oficial y los documentos requeridos: {docs}'
        else:
            mensaje = 'Recuerda presentar identificación oficial y los documentos requeridos para tu trámite.'
        _crear_notificacion(
            clave=f'doc-{cita.id}',
            destino=NotificacionInteligente.CIUDADANO,
            curp=cita.curp_ciudadano,
            categoria=NotificacionInteligente.DOCUMENTACION,
            titulo='Documentación',
            mensaje=mensaje,
            cita=cita,
        )

    canceladas = Cita.objects.filter(
        estado='CANCELADA',
        fecha__gte=hoy,
        creado_el__date__gte=hoy - datetime.timedelta(days=2),
    ).select_related('tramite')
    for cita in canceladas[:30]:
        _crear_notificacion(
            clave=f'disp-{cita.id}',
            destino=NotificacionInteligente.CIUDADANO,
            curp=cita.curp_ciudadano,
            categoria=NotificacionInteligente.DISPONIBILIDAD,
            titulo='Disponibilidad',
            mensaje=(
                f'Se liberó el horario de tu cita de {cita.tramite.nombre}. '
                'Puedes volver a agendar si aún necesitas el trámite.'
            ),
            cita=cita,
        )

    promedio = _promedio_citas_dia()
    total_manana = Cita.objects.filter(fecha=manana).exclude(estado='CANCELADA').count()
    if promedio and total_manana >= max(promedio * 1.3, promedio + 2):
        _crear_notificacion(
            clave=f'demanda-{manana.isoformat()}',
            destino=NotificacionInteligente.FUNCIONARIO,
            categoria=NotificacionInteligente.DEMANDA,
            titulo='Incremento de demanda',
            mensaje=f'Se detectó incremento de demanda para mañana: {total_manana} citas, frente a un promedio de {promedio:.0f}.',
        )

    pendientes = Cita.objects.filter(fecha=hoy, estado__in=('PENDIENTE', 'ASISTIDA')).count()
    if pendientes:
        _crear_notificacion(
            clave=f'pend-{hoy.isoformat()}',
            destino=NotificacionInteligente.FUNCIONARIO,
            categoria=NotificacionInteligente.PENDIENTES,
            titulo='Solicitudes pendientes',
            mensaje=f'Existen {pendientes} solicitudes pendientes de revisión.',
        )


def _promedio_citas_dia():
    desde = timezone.localdate() - datetime.timedelta(days=60)
    filas = (
        Cita.objects.filter(fecha__gte=desde, fecha__lt=timezone.localdate())
        .exclude(estado='CANCELADA')
        .values('fecha')
        .annotate(total=Count('id'))
    )
    totales = [fila['total'] for fila in filas]
    if not totales:
        return 0
    return sum(totales) / len(totales)


def sincronizar_urgentes():
    ahora = timezone.now()
    hoy = timezone.localdate()
    reglas = ReglaPrioridad.objects.filter(activa=True)
    candidatos = Cita.objects.filter(
        estado__in=('PENDIENTE', 'ASISTIDA'),
        fecha__gte=hoy - datetime.timedelta(days=1),
        fecha__lte=hoy,
    ).select_related('tramite')
    for cita in candidatos:
        for regla in reglas:
            if not _cumple_regla(cita, regla, ahora, hoy):
                continue
            minutos = max(int((ahora - cita.creado_el).total_seconds() // 60), 0)
            docs = (cita.tramite.documentos_requeridos or '').strip()
            documentacion = 'completa' if docs else 'sin requisitos registrados en el catálogo'
            titulo = f'Solicitud de {cita.tramite.nombre.lower()} pendiente de revisión.'
            alerta, creada = AlertaUrgente.objects.get_or_create(
                clave=f'urg-{regla.id}-{cita.id}',
                defaults={
                    'cita': cita,
                    'regla': regla,
                    'titulo': titulo,
                    'detalle': 'La solicitud cumple una regla de atención del Registro Civil. La prioridad la confirma el personal.',
                    'tiempo_minutos': minutos,
                    'documentacion': documentacion,
                    'accion_sugerida': regla.accion_sugerida,
                },
            )
            if not creada and alerta.estado == AlertaUrgente.ABIERTA:
                alerta.tiempo_minutos = minutos
                alerta.documentacion = documentacion
                alerta.save(update_fields=['tiempo_minutos', 'documentacion'])


def _cumple_regla(cita, regla, ahora, hoy):
    if cita.estado not in regla.lista_estados():
        return False
    if regla.solo_hoy and cita.fecha != hoy:
        return False
    if regla.palabras_clave and regla.palabras_clave not in normalizar(cita.tramite.nombre):
        return False
    return (ahora - cita.creado_el).total_seconds() >= regla.minutos_umbral * 60


def sincronizar_anomalias():
    desde = timezone.now() - datetime.timedelta(days=14)
    registros = list(
        BitacoraAuditoria.objects.filter(fecha_hora__gte=desde).select_related('usuario')
    )
    _anomalia_actividad(registros)
    _anomalia_modificaciones(registros)
    _anomalia_accesos(registros)
    _anomalia_horario(registros)
    _anomalia_registros(registros)


def _crear_anomalia(clave, tipo, descripcion, registros, usuario=None, usuario_texto=''):
    if Anomalia.objects.filter(clave=clave).exists():
        return
    evidencia = {
        'registros': [r.id for r in registros[:30]],
        'umbral': {
            Anomalia.ACTIVIDAD: UMBRAL_ACTIVIDAD,
            Anomalia.MODIFICACIONES: UMBRAL_MODIFICACIONES,
            Anomalia.ACCESO: UMBRAL_ACCESOS,
            Anomalia.REGISTROS: UMBRAL_REGISTROS,
        }.get(tipo),
    }
    Anomalia.objects.create(
        clave=clave,
        usuario=usuario,
        usuario_texto=usuario_texto or (usuario.username if usuario else ''),
        area=OFICINA_REGISTRO_CIVIL['nombre_corto'],
        tipo=tipo,
        descripcion=descripcion,
        evidencia=evidencia,
    )


def _anomalia_actividad(registros):
    por_usuario_dia = defaultdict(list)
    for registro in registros:
        if not registro.usuario_id:
            continue
        dia = timezone.localtime(registro.fecha_hora).date()
        por_usuario_dia[(registro.usuario_id, dia)].append(registro)
    promedios = defaultdict(list)
    for (usuario_id, _dia), grupo in por_usuario_dia.items():
        promedios[usuario_id].append(len(grupo))
    for (usuario_id, dia), grupo in por_usuario_dia.items():
        if len(grupo) < UMBRAL_ACTIVIDAD:
            continue
        otros = [n for n in promedios[usuario_id] if n != len(grupo)]
        base = (sum(otros) / len(otros)) if otros else 10
        if otros and base > 15:
            continue
        usuario = grupo[0].usuario
        _crear_anomalia(
            f'act-{usuario_id}-{dia.isoformat()}',
            Anomalia.ACTIVIDAD,
            (
                f'Actividad inusual detectada. En la sesión del {dia.strftime("%d/%m/%Y")} '
                f'se registraron {len(grupo)} operaciones. El patrón habitual de referencia es de cerca de {base:.0f}.'
            ),
            grupo,
            usuario=usuario,
        )


def _anomalia_modificaciones(registros):
    mods = [r for r in registros if r.accion in ('MODIFICACION_CITA', 'MODIFICACION_COSTO')]
    mods.sort(key=lambda r: r.fecha_hora)
    for indice, registro in enumerate(mods):
        ventana = [registro]
        for otro in mods[indice + 1:]:
            if (otro.fecha_hora - registro.fecha_hora).total_seconds() > 3600:
                break
            if otro.usuario_id == registro.usuario_id:
                ventana.append(otro)
        if len(ventana) < UMBRAL_MODIFICACIONES:
            continue
        dia = timezone.localtime(registro.fecha_hora).strftime('%Y%m%d%H')
        _crear_anomalia(
            f'mod-{registro.usuario_id}-{dia}',
            Anomalia.MODIFICACIONES,
            (
                f'Se detectaron {len(ventana)} modificaciones en un intervalo corto. '
                'El comportamiento se señala para revisión; no implica por sí mismo una falta.'
            ),
            ventana,
            usuario=registro.usuario,
        )


def _anomalia_accesos(registros):
    fallos = [r for r in registros if r.accion == 'ACCESO_DENEGADO']
    fallos.sort(key=lambda r: r.fecha_hora)
    for indice, registro in enumerate(fallos):
        ventana = [registro]
        for otro in fallos[indice + 1:]:
            if (otro.fecha_hora - registro.fecha_hora).total_seconds() > 3600:
                break
            misma_persona = registro.usuario_id and otro.usuario_id == registro.usuario_id
            misma_ip = registro.ip_direccion and otro.ip_direccion == registro.ip_direccion
            if misma_persona or misma_ip:
                ventana.append(otro)
        if len(ventana) < UMBRAL_ACCESOS:
            continue
        marca = timezone.localtime(registro.fecha_hora).strftime('%Y%m%d%H')
        quien = registro.usuario_id or registro.ip_direccion or 'sin-ip'
        _crear_anomalia(
            f'acc-{quien}-{marca}',
            Anomalia.ACCESO,
            (
                f'Se detectaron {len(ventana)} intentos de acceso fallidos o accesos repetidos '
                'en un intervalo de una hora.'
            ),
            ventana,
            usuario=registro.usuario,
            usuario_texto=registro.nombre_usuario_log() if not registro.usuario_id else '',
        )


def _anomalia_horario(registros):
    fuera = []
    for registro in registros:
        hora = timezone.localtime(registro.fecha_hora).hour
        if hora < 7 or hora >= 21:
            fuera.append(registro)
    agrupados = defaultdict(list)
    for registro in fuera:
        dia = timezone.localtime(registro.fecha_hora).date()
        agrupados[(registro.usuario_id, registro.ip_direccion, dia)].append(registro)
    for (usuario_id, ip, dia), grupo in agrupados.items():
        usuario = grupo[0].usuario
        _crear_anomalia(
            f'hor-{usuario_id or ip}-{dia.isoformat()}',
            Anomalia.HORARIO,
            (
                f'Hay actividad el {dia.strftime("%d/%m/%Y")} fuera del horario habitual '
                f'({HORA_HABITUAL_DESDE:02d}:00–{HORA_HABITUAL_HASTA:02d}:00). '
                'Se genera la alerta para revisión, sin asumir una conducta indebida.'
            ),
            grupo,
            usuario=usuario,
        )


def _anomalia_registros(registros):
    por_dia = defaultdict(list)
    for registro in registros:
        if registro.accion not in ('MODIFICACION_CITA', 'MODIFICACION_COSTO'):
            continue
        dia = timezone.localtime(registro.fecha_hora).date()
        por_dia[(registro.usuario_id, dia, registro.accion)].append(registro)
    for (usuario_id, dia, accion), grupo in por_dia.items():
        umbral = 5 if accion == 'MODIFICACION_COSTO' else UMBRAL_REGISTROS
        if len(grupo) < umbral:
            continue
        _crear_anomalia(
            f'reg-{usuario_id}-{accion}-{dia.isoformat()}',
            Anomalia.REGISTROS,
            (
                f'Hay {len(grupo)} modificaciones consecutivas de tipo {accion} '
                f'el {dia.strftime("%d/%m/%Y")}. Un supervisor puede revisar los registros afectados.'
            ),
            grupo,
            usuario=grupo[0].usuario,
        )


def generar_propuesta(fecha):
    if PropuestaOptimizacion.objects.filter(fecha=fecha, estado=PropuestaOptimizacion.PROPUESTA).exists():
        return None
    filas, citas = ocupacion_fecha(fecha)
    if not citas:
        return None
    cargas = [fila['total'] for fila in filas]
    if not cargas or max(cargas) < 2 or min(cargas) >= max(cargas):
        return None
    movimientos = _movimientos(fecha, citas)
    if not movimientos:
        return None
    horas_altas = [fila['hora'] for fila in filas if fila['total'] == max(cargas)]
    resumen = (
        f'Se detectó concentración alrededor de {", ".join(horas_altas)}. '
        'La propuesta redistribuye citas pendientes no sensibles hacia horarios con capacidad. '
        'Las citas de matrimonio, defunción y divorcio no se incluyen.'
    )
    return PropuestaOptimizacion.objects.create(
        fecha=fecha,
        resumen=resumen,
        analisis={'horas': filas},
        movimientos=movimientos,
    )


def _movimientos(fecha, citas):
    fin = fin_jornada_minutos(fecha.weekday())
    if fin is None:
        return []
    ahora = timezone.now()
    ocupados = [get_intervalo_cita(cita) for cita in citas]
    por_hora = defaultdict(int)
    for cita in citas:
        por_hora[cita.hora.hour] += 1
    if not por_hora:
        return []
    tope = max(por_hora.values())
    horas_libres = [
        hora for hora in range(9, fin // 60)
        if por_hora.get(hora, 0) < tope and por_hora.get(hora, 0) <= max(tope // 2, 0)
    ]
    if not horas_libres:
        return []
    movibles = [
        cita for cita in citas
        if cita.estado == 'PENDIENTE'
        and por_hora.get(cita.hora.hour, 0) >= tope
        and not es_tramite_sensible(cita.tramite.nombre)
        and _es_futura(cita, ahora)
    ]
    movimientos = []
    for cita in movibles:
        duracion = cita.tramite.duracion_minutos or 15
        inicio_actual, fin_actual = get_intervalo_cita(cita)
        for hora in horas_libres:
            inicio = hora * 60
            if not slot_disponible(inicio, duracion, fin, ocupados, []):
                continue
            if inicio == inicio_actual:
                continue
            _retirar(ocupados, inicio_actual, fin_actual)
            ocupados.append((inicio, inicio + duracion))
            movimientos.append({
                'cita_id': cita.id,
                'ciudadano': cita.nombre_ciudadano,
                'tramite': cita.tramite.nombre,
                'hora_actual': cita.hora.strftime('%H:%M'),
                'hora_propuesta': format_minutes(inicio),
                'motivo': 'El horario de origen está saturado y el destino tiene capacidad.',
            })
            break
        if len(movimientos) >= 8:
            break
    return movimientos


def _retirar(ocupados, inicio, fin):
    for indice, (a, b) in enumerate(ocupados):
        if a == inicio and b == fin:
            ocupados.pop(indice)
            return


def _es_futura(cita, ahora):
    momento = datetime.datetime.combine(cita.fecha, cita.hora)
    if timezone.is_aware(ahora):
        momento = timezone.make_aware(momento, timezone.get_current_timezone())
    return momento > ahora


def aplicar_propuesta(propuesta, usuario, request):
    if propuesta.estado != PropuestaOptimizacion.PROPUESTA:
        return False, 'Esta propuesta ya fue revisada.'
    aplicados = []
    fallos = []
    with transaction.atomic():
        bloqueada = PropuestaOptimizacion.objects.select_for_update().get(pk=propuesta.pk)
        if bloqueada.estado != PropuestaOptimizacion.PROPUESTA:
            return False, 'Esta propuesta ya fue revisada.'
        for movimiento in bloqueada.movimientos:
            cita = Cita.objects.filter(pk=movimiento['cita_id']).select_related('tramite').first()
            if not cita or cita.estado != 'PENDIENTE':
                fallos.append(f"La cita #{movimiento['cita_id']} ya no está pendiente.")
                continue
            if cita.hora.strftime('%H:%M') != movimiento['hora_actual']:
                fallos.append(f"La cita #{cita.id} ya cambió de horario.")
                continue
            if es_tramite_sensible(cita.tramite.nombre):
                fallos.append(f"La cita #{cita.id} es sensible y no se modifica.")
                continue
            cita.hora = datetime.datetime.strptime(movimiento['hora_propuesta'], '%H:%M').time()
            try:
                cita.save()
            except Exception:
                fallos.append(f'La cita #{cita.id} no se pudo mover.')
                continue
            aplicados.append(cita.id)
            NotificacionInteligente.objects.get_or_create(
                clave=f"cam-{cita.id}-{movimiento['hora_propuesta']}",
                defaults={
                    'destino': NotificacionInteligente.CIUDADANO,
                    'curp': cita.curp_ciudadano,
                    'categoria': NotificacionInteligente.CAMBIO,
                    'titulo': 'Tu cita fue modificada',
                    'mensaje': (
                        f'Tu cita de {cita.tramite.nombre} fue modificada al '
                        f'{cita.fecha.strftime("%d/%m/%Y")} a las {movimiento["hora_propuesta"]}, '
                        'después de la autorización de un funcionario.'
                    ),
                    'cita': cita,
                },
            )
            registrar_log(
                request,
                'MODIFICACION_CITA',
                (
                    f"Optimización de citas autorizada: cita #{cita.id} "
                    f"de {movimiento['hora_actual']} a {movimiento['hora_propuesta']}."
                ),
            )
        if not aplicados:
            return False, ' '.join(fallos) or 'No hubo citas que se pudieran mover.'
        bloqueada.estado = PropuestaOptimizacion.APLICADA
        bloqueada.revisada_por = usuario
        bloqueada.revisada_el = timezone.now()
        bloqueada.nota = ' '.join(fallos)
        bloqueada.save(update_fields=['estado', 'revisada_por', 'revisada_el', 'nota'])
    return True, f'Se aplicaron {len(aplicados)} cambio(s) de horario.'


def rechazar_propuesta(propuesta, usuario, nota):
    if propuesta.estado != PropuestaOptimizacion.PROPUESTA:
        return False, 'Esta propuesta ya fue revisada.'
    propuesta.estado = PropuestaOptimizacion.RECHAZADA
    propuesta.revisada_por = usuario
    propuesta.revisada_el = timezone.now()
    propuesta.nota = nota
    propuesta.save(update_fields=['estado', 'revisada_por', 'revisada_el', 'nota'])
    return True, 'La propuesta quedó rechazada. Ninguna cita fue modificada.'


def registrar_evento(anomalia, usuario, accion, nota=''):
    EventoInvestigacion.objects.create(
        anomalia=anomalia,
        usuario=usuario,
        accion=accion,
        nota=nota,
    )

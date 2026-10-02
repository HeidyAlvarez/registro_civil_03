"""Demanda, sugerencia de horario, temporadas y reportes a partir del historial."""

import datetime
from collections import defaultdict

from django.utils import timezone

from citas.models import Cita, PagoCaja, Tramite
from citas.utils import (
    citas_ocupadas_en_fecha,
    fin_jornada_minutos,
    format_minutes,
    generar_slots_dia,
    horarios_bloqueados_en_fecha,
    slot_disponible,
    validar_fecha_agendado,
)
from ia.servicios.texto import es_tramite_sensible, normalizar

DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
MESES = ['', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
ARTICULO_DIA = {
    'Lunes': 'Los lunes',
    'Martes': 'Los martes',
    'Miércoles': 'Los miércoles',
    'Jueves': 'Los jueves',
    'Viernes': 'Los viernes',
    'Sábado': 'Los sábados',
    'Domingo': 'Los domingos',
}


def _hoy():
    return timezone.localdate()


def _qs_periodo(dias):
    desde = _hoy() - datetime.timedelta(days=dias)
    return Cita.objects.filter(fecha__gte=desde).select_related('tramite')


def panorama_demanda(dias=120):
    citas = list(_qs_periodo(dias))
    activas = [c for c in citas if c.estado != 'CANCELADA']
    canceladas = [c for c in citas if c.estado == 'CANCELADA']
    atendidas = [c for c in citas if c.estado in ('PAGADA', 'FINALIZADA', 'ASISTIDA')]

    por_dia_n = defaultdict(int)
    por_hora_n = defaultdict(int)
    por_tramite_n = defaultdict(int)
    calor = defaultdict(int)
    por_semana = defaultdict(int)

    for cita in activas:
        por_dia_n[cita.fecha.weekday()] += 1
        por_hora_n[cita.hora.hour] += 1
        por_tramite_n[cita.tramite.nombre] += 1
        calor[(cita.fecha.weekday(), cita.hora.hour)] += 1
        por_semana[cita.fecha.isocalendar()[:2]] += 1

    max_dia = max(por_dia_n.values(), default=0) or 1
    por_dia = []
    for indice, nombre in enumerate(DIAS):
        total = por_dia_n.get(indice, 0)
        por_dia.append({
            'nombre': nombre,
            'total': total,
            'pct': round(total * 100 / max_dia) if max_dia else 0,
        })

    horas = list(range(9, 17))
    max_hora = max((por_hora_n.get(h, 0) for h in horas), default=0) or 1
    por_hora = []
    for hora in horas:
        total = por_hora_n.get(hora, 0)
        por_hora.append({
            'hora': f'{hora:02d}:00',
            'total': total,
            'pct': round(total * 100 / max_hora) if max_hora else 0,
        })

    max_celda = max(calor.values(), default=0) or 1
    heatmap = []
    for dia in range(6):
        celdas = []
        for hora in horas:
            total = calor.get((dia, hora), 0)
            celdas.append({
                'total': total,
                'intensidad': round(total / max_celda, 2),
            })
        heatmap.append({'dia': DIAS[dia], 'celdas': celdas})

    por_tramite = sorted(
        ({'nombre': nombre, 'total': total} for nombre, total in por_tramite_n.items()),
        key=lambda item: item['total'],
        reverse=True,
    )[:8]

    tendencia = []
    for clave in sorted(por_semana)[-8:]:
        anio, semana = clave
        tendencia.append({'etiqueta': f'S{semana} {anio}', 'total': por_semana[clave]})
    max_tend = max((item['total'] for item in tendencia), default=0) or 1
    for item in tendencia:
        item['pct'] = round(item['total'] * 100 / max_tend)

    return {
        'desde': _hoy() - datetime.timedelta(days=dias),
        'hasta': _hoy(),
        'total_citas': len(activas),
        'cancelaciones': len(canceladas),
        'personas_atendidas': len(atendidas),
        'por_dia': por_dia,
        'por_hora': por_hora,
        'horas': [f'{h:02d}:00' for h in horas],
        'heatmap': heatmap,
        'por_tramite': por_tramite,
        'tendencia': tendencia,
        'espera_promedio': tiempo_promedio_atencion(),
        'hallazgos': _hallazgos(por_dia, por_hora, por_tramite, len(activas)),
    }


def _hallazgos(por_dia, por_hora, por_tramite, total):
    if total == 0:
        return ['Aún no hay suficiente historial. El análisis se completará conforme se registren citas.']
    hallazgos = []
    top_dia = max(por_dia, key=lambda item: item['total'])
    promedio = sum(item['total'] for item in por_dia) / len(por_dia)
    if top_dia['total'] > 0 and top_dia['total'] >= max(promedio * 1.15, 1):
        tramite = f" de {por_tramite[0]['nombre'].lower()}" if por_tramite else ''
        hallazgos.append(f"{ARTICULO_DIA[top_dia['nombre']]} existe una demanda elevada{tramite}.")
    frase_hora = _frase_horario(por_hora)
    if frase_hora:
        hallazgos.append(frase_hora)
    if not hallazgos:
        hallazgos.append('La demanda del periodo está repartida, sin un pico dominante.')
    return hallazgos


def _frase_horario(por_hora):
    top = max(por_hora, key=lambda item: item['total'])
    if top['total'] <= 0:
        return None
    hora = int(top['hora'][:2])
    siguientes = {item['hora']: item['total'] for item in por_hora}
    media = f'{hora + 1:02d}:00'
    if siguientes.get(media, 0) >= top['total'] * 0.5:
        return f'Entre las {top["hora"]} y las {hora + 2:02d}:00 se concentra una parte importante de las citas.'
    return f'A las {top["hora"]} se concentra una parte importante de las citas.'


def tiempo_promedio_atencion(tramite_id=None):
    pagos = PagoCaja.objects.select_related('cita', 'cita__tramite')
    if tramite_id:
        pagos = pagos.filter(cita__tramite_id=tramite_id)
    muestras = []
    por_hora = defaultdict(list)
    for pago in pagos:
        cita = pago.cita
        inicio = datetime.datetime.combine(cita.fecha, cita.hora)
        pago_dt = pago.fecha_pago
        if timezone.is_aware(pago_dt):
            inicio = timezone.make_aware(inicio, timezone.get_current_timezone())
        minutos = (pago_dt - inicio).total_seconds() / 60
        if minutos < 0 or minutos > 480:
            continue
        muestras.append(minutos)
        por_hora[cita.hora.hour].append(minutos)
    if not muestras:
        return {'global': None, 'por_hora': {}}
    return {
        'global': round(sum(muestras) / len(muestras)),
        'por_hora': {hora: round(sum(vals) / len(vals)) for hora, vals in por_hora.items()},
    }


def clasificar_nivel(valor, bajo, alto):
    if valor <= bajo:
        return 'baja'
    if valor >= alto:
        return 'alta'
    return 'media'


def _historico_por_hora(tramite_id, weekday):
    desde = _hoy() - datetime.timedelta(days=180)
    conteo = defaultdict(int)
    dias_vistos = set()
    citas = Cita.objects.filter(
        fecha__gte=desde,
        tramite_id=tramite_id,
    ).exclude(estado='CANCELADA')
    for cita in citas:
        if cita.fecha.weekday() != weekday:
            continue
        conteo[cita.hora.hour] += 1
        dias_vistos.add(cita.fecha)
    dias = max(len(dias_vistos), 1)
    return {hora: total / dias for hora, total in conteo.items()}, len(dias_vistos)


def sugerir_horario(tramite, fecha):
    ok, error = validar_fecha_agendado(fecha)
    if not ok:
        return {'error': error, 'opciones': [], 'tramite': tramite, 'fecha': fecha}

    dia = fecha.weekday()
    fin = fin_jornada_minutos(dia)
    if fin is None:
        return {
            'error': 'Ese día no hay atención en la oficialía.',
            'opciones': [],
            'tramite': tramite,
            'fecha': fecha,
        }

    tipo_bloqueo, bloqueos = horarios_bloqueados_en_fecha(fecha)
    if tipo_bloqueo == 'dia_completo':
        return {
            'error': 'Ese día está bloqueado para citas.',
            'opciones': [],
            'tramite': tramite,
            'fecha': fecha,
        }

    duracion = tramite.duracion_minutos or 15
    slots = generar_slots_dia(dia, duracion)
    ocupados = citas_ocupadas_en_fecha(fecha)
    promedios, dias_muestra = _historico_por_hora(tramite.id, dia)
    espera = tiempo_promedio_atencion(tramite.id)['por_hora']
    valores = list(promedios.values()) or [0]
    bajo = min(valores) if valores else 0
    alto = max(valores) if valores else 0
    if alto == bajo:
        alto = bajo + 1

    citas_dia = Cita.objects.filter(fecha=fecha, tramite=tramite).exclude(estado='CANCELADA')
    carga_hora = defaultdict(int)
    for cita in citas_dia:
        carga_hora[cita.hora.hour] += 1

    opciones = []
    for inicio in slots:
        disponible = slot_disponible(inicio, duracion, fin, ocupados, bloqueos)
        hora = inicio // 60
        score = promedios.get(hora, 0) + carga_hora.get(hora, 0)
        nivel = clasificar_nivel(score, bajo, alto if alto != bajo else bajo + 1)
        if carga_hora.get(hora, 0) >= 2:
            nivel = 'alta'
        elif not promedios and carga_hora.get(hora, 0) == 0:
            nivel = 'baja'
        elif not promedios and carga_hora.get(hora, 0) == 1:
            nivel = 'media'
        espera_hora = espera.get(hora)
        explicacion = _explicar_nivel(nivel, espera_hora, dias_muestra)
        opciones.append({
            'hora': format_minutes(inicio),
            'nivel': nivel,
            'etiqueta': f'Demanda estimada {nivel}',
            'disponible': disponible,
            'explicacion': explicacion,
        })

    orden = {'baja': 0, 'media': 1, 'alta': 2}
    opciones.sort(key=lambda item: (orden[item['nivel']], item['hora']))
    return {
        'error': None,
        'tramite': tramite,
        'fecha': fecha,
        'opciones': opciones,
        'dias_muestra': dias_muestra,
        'recomendado': next((item for item in opciones if item['disponible'] and item['nivel'] == 'baja'), None),
    }


def _explicar_nivel(nivel, espera_hora, dias_muestra):
    base = {
        'baja': 'Este horario presenta históricamente menor demanda',
        'media': 'Este horario presenta una demanda intermedia respecto al historial disponible',
        'alta': 'Este horario concentra históricamente más citas',
    }[nivel]
    if nivel == 'baja' and espera_hora is not None:
        base += f' y un tiempo promedio de atención de {espera_hora} minutos para este trámite'
    elif nivel == 'baja':
        base += ' y menor concentración de citas para este trámite'
    if dias_muestra == 0:
        base += '. Todavía hay poco historial de este día, así que la estimación usa las citas ya agendadas en la fecha'
    base += '.'
    return base


def etiquetas_temporada(mes):
    tags = [MESES[mes]]
    if mes in (7, 8):
        tags.append('vacaciones de verano')
    if mes in (12, 1):
        tags.append('el periodo vacacional de fin de año')
    if mes == 12:
        tags.append('fin de año')
    if mes in (9, 10, 11, 1, 2, 3, 4, 5, 6):
        tags.append('la temporada escolar')
    return tags


def analisis_temporadas():
    citas = Cita.objects.exclude(estado='CANCELADA').select_related('tramite')
    cubo = defaultdict(int)
    for cita in citas:
        cubo[(cita.fecha.year, cita.fecha.month, cita.tramite.nombre)] += 1

    hoy = _hoy()
    actual = defaultdict(int)
    for (anio, mes, nombre), total in cubo.items():
        if anio == hoy.year and mes == hoy.month:
            actual[nombre] += total

    frases = []
    filas = []
    nombres = sorted({nombre for (_, _, nombre) in cubo})
    temporada = etiquetas_temporada(hoy.month)[0]
    for nombre in nombres:
        mismo_mes = [
            total for (anio, mes, nom), total in cubo.items()
            if nom == nombre and mes == hoy.month and anio != hoy.year
        ]
        otros = [
            total for (anio, mes, nom), total in cubo.items()
            if nom == nombre and not (anio == hoy.year and mes == hoy.month)
        ]
        if mismo_mes:
            referencia = sum(mismo_mes) / len(mismo_mes)
            metodo = 'mismo mes de años anteriores'
        elif otros:
            referencia = sum(otros) / len(otros)
            metodo = 'promedio de los otros meses registrados'
        else:
            referencia = 0
            metodo = 'sin historial comparable'
        valor = actual[nombre]
        frase = _frase_cambio(nombre, valor, referencia, temporada)
        if frase:
            frases.append(frase)
        filas.append({
            'nombre': nombre,
            'actual': valor,
            'referencia': round(referencia, 1),
            'metodo': metodo,
        })

    por_mes_n = defaultdict(int)
    for (anio, mes, _), total in cubo.items():
        por_mes_n[(anio, mes)] += total
    serie = []
    for clave in sorted(por_mes_n)[-12:]:
        anio, mes = clave
        serie.append({'etiqueta': f'{MESES[mes][:3]} {anio}', 'total': por_mes_n[clave]})
    max_serie = max((item['total'] for item in serie), default=0) or 1
    for item in serie:
        item['pct'] = round(item['total'] * 100 / max_serie)

    if not frases:
        frases.append('No hay un cambio de temporada lo bastante marcado con el historial disponible.')

    return {
        'mes': MESES[hoy.month],
        'anio': hoy.year,
        'frases': frases,
        'filas': sorted(filas, key=lambda item: item['actual'], reverse=True),
        'serie': serie,
        'temporadas': etiquetas_temporada(hoy.month),
    }


def _frase_cambio(nombre, actual, referencia, temporada):
    if referencia < 2 and actual < 2:
        return None
    if referencia <= 0:
        return None
    ratio = actual / referencia
    visible = normalizar(nombre)
    if ratio >= 1.25:
        return (
            f'La demanda de {visible} presenta un incremento respecto al '
            f'comportamiento histórico de {temporada}.'
        )
    if ratio <= 0.75:
        return (
            f'La demanda de {visible} presenta una disminución respecto al '
            f'comportamiento histórico de {temporada}.'
        )
    return None


def ocupacion_fecha(fecha):
    citas = list(
        Cita.objects.filter(fecha=fecha).exclude(estado='CANCELADA').select_related('tramite')
    )
    fin = fin_jornada_minutos(fecha.weekday())
    horas = list(range(9, (fin or 17 * 60) // 60))
    por_hora = {hora: [] for hora in horas}
    for cita in citas:
        por_hora.setdefault(cita.hora.hour, []).append(cita)
    filas = []
    for hora in sorted(por_hora):
        grupo = por_hora[hora]
        filas.append({
            'hora': f'{hora:02d}:00',
            'total': len(grupo),
            'sensibles': sum(1 for c in grupo if es_tramite_sensible(c.tramite.nombre)),
        })
    return filas, citas


def construir_reporte(tipo):
    demanda = panorama_demanda()
    temporadas = analisis_temporadas()
    if tipo == 'demanda':
        return {
            'titulo': 'Reporte de demanda',
            'intro': 'Trámites con más solicitudes en el periodo analizado.',
            'hallazgos': demanda['hallazgos'],
            'tabla': {
                'titulo': 'Trámites más solicitados',
                'columnas': ['Trámite', 'Solicitudes'],
                'filas': [[f['nombre'], f['total']] for f in demanda['por_tramite']],
            },
        }
    if tipo == 'citas':
        return {
            'titulo': 'Reporte de citas',
            'intro': 'Horarios con mayor y menor utilización en el historial reciente.',
            'hallazgos': demanda['hallazgos'],
            'tabla': {
                'titulo': 'Utilización por hora',
                'columnas': ['Hora', 'Citas'],
                'filas': [[f['hora'], f['total']] for f in demanda['por_hora']],
            },
        }
    if tipo == 'atencion':
        espera = demanda['espera_promedio']['global']
        texto = (
            f'{espera} minutos entre la hora de la cita y el registro del pago.'
            if espera is not None
            else 'Aún no hay pagos suficientes para calcular un tiempo de atención observado. Se muestra la duración configurada en el catálogo.'
        )
        tramites = Tramite.objects.filter(activo=True).order_by('nombre')
        return {
            'titulo': 'Reporte de atención',
            'intro': texto,
            'hallazgos': [],
            'tabla': {
                'titulo': 'Duración configurada por trámite',
                'columnas': ['Trámite', 'Minutos'],
                'filas': [[t.nombre, t.duracion_minutos] for t in tramites],
            },
        }
    if tipo == 'temporadas':
        return {
            'titulo': 'Reporte de temporadas',
            'intro': f'Cambios de demanda en {temporadas["mes"]} de {temporadas["anio"]}.',
            'hallazgos': temporadas['frases'],
            'tabla': {
                'titulo': 'Mes actual frente a la referencia histórica',
                'columnas': ['Trámite', 'Mes actual', 'Referencia', 'Método'],
                'filas': [
                    [f['nombre'], f['actual'], f['referencia'], f['metodo']]
                    for f in temporadas['filas']
                ],
            },
        }
    return None

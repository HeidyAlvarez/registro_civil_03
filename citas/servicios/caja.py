"""Tabla CRC 26 — Caja (control de pagos)."""

import json
from datetime import datetime

from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Sum
from django.db.models.functions import ExtractWeekDay, TruncMonth
from django.utils import timezone

from citas.models import Cita, CorteCajaDiario, PagoCaja
from citas.servicios.constantes import MESES_ESPANOL
from citas.utils import pagos_para_ingresos


class Caja:
    """Registro de cobros, cancelación de pagos vía cita y corte diario."""

    @classmethod
    def registrar_pago(cls, cita, cajero):
        """
        Crea PagoCaja y pasa la cita a PAGADA.
        Retorna (ok, error_msg|None).
        """
        if cita.estado != 'ASISTIDA':
            return False, f'La cita está en estado {cita.estado}.'
        try:
            with transaction.atomic():
                PagoCaja.objects.create(
                    cita=cita,
                    monto_cobrado=cita.tramite.costo,
                    cajero=cajero,
                )
                cita.estado = 'PAGADA'
                cita.save()
        except IntegrityError:
            return False, 'Esta cita ya tiene un pago registrado.'
        return True, None

    @classmethod
    def cerrar_corte_diario(cls, fecha, usuario):
        """
        Genera corte inmutable y marca pagos con corte_cierre_listo=True.
        Retorna (ok, mensaje, datos|None).
        """
        if CorteCajaDiario.objects.filter(fecha=fecha).exists():
            return False, f'El corte del {fecha} ya fue cerrado.', None

        pagos = pagos_para_ingresos().filter(fecha_pago__date=fecha, corte_cierre_listo=False)
        if not pagos.exists():
            return False, f'No hay pagos pendientes de corte para el {fecha}.', None

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
            corte = CorteCajaDiario.objects.create(
                fecha=fecha,
                total_recaudado=total,
                desglose_tramites=desglose,
                cantidad_pagos=cantidad,
                cerrado_por=usuario,
            )
            pagos.update(corte_cierre_listo=True)

        return True, f'Corte del {fecha} cerrado correctamente (${total}).', {
            'corte': corte,
            'total': total,
            'cantidad': cantidad,
        }

    @classmethod
    def parsear_fecha_corte(cls, fecha_str):
        try:
            return datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else timezone.now().date()
        except ValueError:
            return timezone.now().date()

    @classmethod
    def ingresos_del_dia(cls, fecha=None):
        fecha = fecha or timezone.now().date()
        return float(
            pagos_para_ingresos().filter(fecha_pago__date=fecha)
            .aggregate(Sum('monto_cobrado'))['monto_cobrado__sum'] or 0
        )

    @classmethod
    def reporte_mensual(cls, anio=None, mes=None):
        ahora = timezone.now()
        anio_filtrar = int(anio) if anio else ahora.year
        mes_filtrar = int(mes) if mes else ahora.month
        es_mes_actual = (anio_filtrar == ahora.year and mes_filtrar == ahora.month)

        pagos_mes = pagos_para_ingresos().filter(
            fecha_pago__year=anio_filtrar,
            fecha_pago__month=mes_filtrar,
            cita__tramite__isnull=False,
            cita__tramite__seccion__isnull=False,
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
        datos_semana_reales = [
            dias_datos[1], dias_datos[2], dias_datos[3],
            dias_datos[4], dias_datos[5], dias_datos[6], dias_datos[0],
        ]

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

        meses_historial = []
        for item in meses_con_datos:
            dt = item['month']
            meses_historial.append({
                'anio': dt.year,
                'mes': dt.month,
                'etiqueta': f"{MESES_ESPANOL.get(dt.month, 'Mes')} {dt.year}",
            })

        hoy = ahora.date()
        pagos_hoy = pagos_para_ingresos().filter(fecha_pago__date=hoy)
        desglose_hoy = list(
            pagos_hoy.values('cita__tramite__nombre', 'cita__tramite__seccion__nombre')
            .annotate(cantidad=Count('id'), total=Sum('monto_cobrado'))
            .order_by('-total')
        )
        total_hoy = pagos_hoy.aggregate(t=Sum('monto_cobrado'))['t'] or 0

        return {
            'total_acumulado': total_acumulado,
            'total_tramites': total_tramites,
            'usuarios_activos': usuarios_activos,
            'tiempo_promedio': tiempo_promedio,
            'reporte_tramites': reporte_por_tramite,
            'mes_nombre': MESES_ESPANOL.get(mes_filtrar, 'Mes Desconocido'),
            'anio': anio_filtrar,
            'es_mes_actual': es_mes_actual,
            'meses_historial': meses_historial,
            'datos_semana_json': json.dumps(datos_semana_reales),
            'labels_grafica_json': json.dumps(labels_top),
            'datos_grafica_json': json.dumps(cantidades_top),
            'corte_hoy': CorteCajaDiario.objects.filter(fecha=hoy).first(),
            'desglose_hoy': desglose_hoy,
            'total_hoy': total_hoy,
            'fecha_hoy': hoy,
            'cortes_historial': CorteCajaDiario.objects.all().order_by('-fecha')[:12],
        }

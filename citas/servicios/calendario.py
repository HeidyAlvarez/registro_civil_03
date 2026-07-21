"""Tabla CRC 23 — Calendario (control de horarios)."""

import datetime

from django.utils import timezone

from citas.models import HorarioBloqueado
from citas.utils import (
    citas_ocupadas_en_fecha,
    fin_jornada_minutos,
    format_minutes,
    generar_slots_dia,
    horarios_bloqueados_en_fecha,
    rango_fechas_agendado,
    slot_disponible,
    validar_disponibilidad,
    validar_fecha_agendado,
)


class Calendario:
    """Disponibilidad de horarios según duración del trámite y bloqueos."""

    @classmethod
    def validar_fecha_agendamiento(cls, fecha):
        return validar_fecha_agendado(fecha)

    @classmethod
    def validar_horario(cls, fecha, hora_str, duracion_minutos):
        return validar_disponibilidad(fecha, hora_str, duracion_minutos)

    @classmethod
    def dia_bloqueado_completo(cls, fecha):
        return HorarioBloqueado.objects.filter(fecha=fecha, hora__isnull=True).exists()

    @classmethod
    def hora_bloqueada(cls, fecha, hora):
        return HorarioBloqueado.objects.filter(fecha=fecha, hora=hora).exists()

    @classmethod
    def horarios_para_fecha(cls, fecha_str, duracion_minutos):
        fecha_obj = datetime.datetime.strptime(fecha_str, '%Y-%m-%d').date()
        ok_fecha, err_fecha = cls.validar_fecha_agendamiento(fecha_obj)
        if not ok_fecha:
            return {'error': err_fecha}

        dia_semana = fecha_obj.weekday()
        tipo_bloqueo, bloqueos = horarios_bloqueados_en_fecha(fecha_obj)
        if tipo_bloqueo == 'dia_completo':
            return {
                'horarios': [],
                'dia_bloqueado': True,
                'duracion_minutos': duracion_minutos,
            }

        fin_jornada = fin_jornada_minutos(dia_semana)
        if fin_jornada is None:
            return {
                'horarios': [],
                'dia_bloqueado': True,
                'duracion_minutos': duracion_minutos,
            }

        slots_base = generar_slots_dia(dia_semana, duracion_minutos)
        intervalos_ocupados = citas_ocupadas_en_fecha(fecha_obj)
        horarios = []
        for inicio in slots_base:
            disponible = slot_disponible(
                inicio, duracion_minutos, fin_jornada, intervalos_ocupados, bloqueos,
            )
            horarios.append({
                'hora': format_minutes(inicio),
                'ocupado': not disponible,
                'duracion_minutos': duracion_minutos,
            })

        min_fecha, max_fecha = rango_fechas_agendado()
        return {
            'horarios': horarios,
            'dia_bloqueado': False,
            'duracion_minutos': duracion_minutos,
            'intervalo_minutos': duracion_minutos,
            'fecha_min': min_fecha.isoformat(),
            'fecha_max': max_fecha.isoformat(),
        }

    @classmethod
    def crear_bloqueo(cls, fecha, tipo, motivo, usuario, horas=None):
        if not fecha or not tipo:
            return False, 'Debes seleccionar una fecha y el tipo de bloqueo.', 0

        motivo = (motivo or '').strip()

        if tipo == 'dia_completo':
            _, creado = HorarioBloqueado.objects.get_or_create(
                fecha=fecha, hora=None,
                defaults={'motivo': motivo, 'creado_por': usuario},
            )
            if creado:
                return True, f"Día {fecha} bloqueado completamente.", 1
            return False, 'Ese día ya estaba bloqueado.', 0

        if tipo == 'horario_especifico':
            horas = horas or []
            if not horas:
                return False, 'Debes seleccionar al menos una hora.', 0
            creados = 0
            for hora in horas:
                _, creado = HorarioBloqueado.objects.get_or_create(
                    fecha=fecha, hora=hora,
                    defaults={'motivo': motivo, 'creado_por': usuario},
                )
                if creado:
                    creados += 1
            if creados > 0:
                return True, f"{creados} horario(s) bloqueados para el {fecha}.", creados
            return False, 'Esos horarios ya estaban bloqueados.', 0

        return False, 'Tipo de bloqueo no válido.', 0

    @classmethod
    def listar_bloqueos_futuros(cls):
        return HorarioBloqueado.objects.filter(
            fecha__gte=timezone.now().date(),
        ).order_by('fecha', 'hora')

    @classmethod
    def eliminar_bloqueos_dia(cls, fecha):
        cantidad = HorarioBloqueado.objects.filter(fecha=fecha).count()
        HorarioBloqueado.objects.filter(fecha=fecha).delete()
        return cantidad

    @classmethod
    def eliminar_bloqueo(cls, bloqueo_id):
        bloqueo = HorarioBloqueado.objects.get(id=bloqueo_id)
        desc = str(bloqueo)
        bloqueo.delete()
        return desc

import calendar
import datetime
import threading

_local = threading.local()

def fin_jornada_minutos(dia_semana):
    if dia_semana < 5:
        return 17 * 60
    if dia_semana == 5:
        return 13 * 60
    return None


def set_current_request(request):
    _local.request = request


def get_current_request():
    return getattr(_local, 'request', None)


def obtener_ip(request):
    if request is None:
        return None
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def time_to_minutes(t):
    return t.hour * 60 + t.minute


def minutes_to_time(total_minutes):
    return datetime.time(total_minutes // 60, total_minutes % 60)


def parse_hora_str(hora_str):
    h, m = map(int, hora_str.split(':'))
    return h * 60 + m


def format_minutes(total_minutes):
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def get_intervalo_cita(cita):
    inicio = time_to_minutes(cita.hora)
    fin = inicio + cita.tramite.duracion_minutos
    return inicio, fin


def intervalos_se_solapan(inicio_a, fin_a, inicio_b, fin_b):
    return inicio_a < fin_b and inicio_b < fin_a


def generar_slots_dia(dia_semana, intervalo_minutos):
    """Genera horarios de inicio espaciados según la duración del trámite."""
    fin = fin_jornada_minutos(dia_semana)
    if fin is None:
        return []
    intervalo = max(int(intervalo_minutos), 1)
    inicio = 9 * 60
    slots = []
    actual = inicio
    while actual + intervalo <= fin:
        slots.append(actual)
        actual += intervalo
    return slots


def citas_ocupadas_en_fecha(fecha):
    from .models import Cita
    citas = Cita.objects.filter(fecha=fecha).exclude(estado='CANCELADA').select_related('tramite')
    intervalos = []
    for cita in citas:
        intervalos.append(get_intervalo_cita(cita))
    return intervalos


def horarios_bloqueados_en_fecha(fecha_obj):
    from .models import HorarioBloqueado
    bloqueos = HorarioBloqueado.objects.filter(fecha=fecha_obj)
    if bloqueos.filter(hora__isnull=True).exists():
        return 'dia_completo', []
    bloqueados = []
    for bloqueo in bloqueos.filter(hora__isnull=False):
        inicio = time_to_minutes(bloqueo.hora)
        bloqueados.append((inicio, inicio + 30))
    return 'parcial', bloqueados


def slot_disponible(inicio_slot, duracion, fin_jornada, intervalos_ocupados, bloqueos):
    fin_slot = inicio_slot + duracion
    if fin_slot > fin_jornada:
        return False
    for inicio_b, fin_b in bloqueos:
        if intervalos_se_solapan(inicio_slot, fin_slot, inicio_b, fin_b):
            return False
    for inicio_o, fin_o in intervalos_ocupados:
        if intervalos_se_solapan(inicio_slot, fin_slot, inicio_o, fin_o):
            return False
    return True


def validar_disponibilidad(fecha, hora_str, duracion_minutos):
    from .models import HorarioBloqueado
    fecha_obj = fecha if isinstance(fecha, datetime.date) else datetime.datetime.strptime(str(fecha), '%Y-%m-%d').date()
    dia_semana = fecha_obj.weekday()
    fin_jornada = fin_jornada_minutos(dia_semana)
    if fin_jornada is None:
        return False, 'Ese día no hay atención.'
    slots = generar_slots_dia(dia_semana, duracion_minutos)
    if not slots:
        return False, 'No hay horarios disponibles para la duración de este trámite.'
    tipo_bloqueo, bloqueos = horarios_bloqueados_en_fecha(fecha_obj)
    if tipo_bloqueo == 'dia_completo':
        return False, 'Ese día no está disponible para citas.'
    inicio = parse_hora_str(hora_str)
    if inicio not in slots:
        return False, 'Horario no válido para la duración de este trámite.'
    intervalos = citas_ocupadas_en_fecha(fecha_obj)
    if not slot_disponible(inicio, duracion_minutos, fin_jornada, intervalos, bloqueos):
        return False, 'Horario no disponible para la duración de este trámite.'
    return True, None


def sumar_un_mes(fecha):
    """Suma un mes calendario conservando el día cuando es posible."""
    mes = fecha.month + 1
    anio = fecha.year
    if mes > 12:
        mes = 1
        anio += 1
    dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
    return datetime.date(anio, mes, dia)


def rango_fechas_agendado(hoy=None):
    """Anticipación mínima: mañana. Máxima: un mes calendario."""
    hoy = hoy or datetime.date.today()
    return hoy + datetime.timedelta(days=1), sumar_un_mes(hoy)


def validar_fecha_agendado(fecha):
    """Valida que la fecha esté dentro del rango permitido para agendar."""
    if isinstance(fecha, str):
        fecha = datetime.datetime.strptime(fecha, '%Y-%m-%d').date()
    min_fecha, max_fecha = rango_fechas_agendado()
    if fecha < min_fecha:
        return False, 'La cita debe ser a partir de mañana.'
    if fecha > max_fecha:
        return False, 'Solo puedes agendar con un máximo de un mes de anticipación.'
    return True, None


def pagos_para_ingresos():
    """ Pagos que cuentan en ingresos (excluye citas canceladas). """
    from .models import PagoCaja
    return PagoCaja.objects.exclude(cita__estado='CANCELADA')

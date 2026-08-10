"""Tabla CRC 22 — Cita (lógica principal)."""

import re
from datetime import datetime

from django.core.exceptions import ValidationError
from django.db.models import Count, ObjectDoesNotExist, Q, Sum
from django.db.models.functions import TruncMonth
from django.urls import reverse
from django.utils import timezone

from citas.models import Cita as CitaModel
from citas.models import Tramite as TramiteModel
from citas.servicios.calendario import Calendario
from citas.servicios.constantes import MESES_ESPANOL
from citas.utils import es_tramite_registro_nacimiento, validar_datos_recien_nacido
from citas.validators import validar_curp


class Cita:
    """Validación, creación y gestión del flujo de estados de citas."""

    ESTADOS_CITA_ACTIVA = ('PENDIENTE', 'ASISTIDA', 'PAGADA')
    DIAS_MINIMOS_CANCELACION_CIUDADANO = 7
    ESTADO_ETIQUETAS = {
        'PENDIENTE': 'Pendiente',
        'ASISTIDA': 'Asistida en ventanilla',
        'PAGADA': 'Pagada',
        'FINALIZADA': 'Finalizada',
        'CANCELADA': 'Cancelada',
    }

    @classmethod
    def tiene_cita_activa_curp(cls, curp):
        return CitaModel.objects.filter(
            curp_ciudadano=curp,
            estado__in=cls.ESTADOS_CITA_ACTIVA,
        ).exists()

    @classmethod
    def validar_curp_disponible(cls, curp_raw):
        try:
            curp = validar_curp((curp_raw or '').strip().upper())
        except ValidationError as exc:
            return False, exc.messages[0], None
        if cls.tiene_cita_activa_curp(curp):
            return False, 'Ya existe una cita programada para estos datos.', {'tiene_cita_activa': True}
        return True, 'CURP disponible para agendar.', None

    @classmethod
    def obtener_por_folio_curp(cls, folio, curp_raw):
        try:
            folio_int = int(folio)
        except (TypeError, ValueError):
            return None
        try:
            curp = validar_curp((curp_raw or '').strip().upper())
        except ValidationError:
            return None
        try:
            return CitaModel.objects.select_related('tramite__seccion').get(
                id=folio_int,
                curp_ciudadano=curp,
            )
        except CitaModel.DoesNotExist:
            return None

    @classmethod
    def dias_hasta_cita(cls, cita):
        return (cita.fecha - timezone.now().date()).days

    @classmethod
    def puede_cancelar_por_ciudadano(cls, cita):
        if cita.estado == 'CANCELADA':
            return False, 'Esta cita ya fue cancelada.'
        if cita.estado == 'FINALIZADA':
            return False, 'Esta cita ya fue atendida y finalizada; no puede cancelarse en línea.'
        if cita.estado != 'PENDIENTE':
            return False, 'Solo puedes cancelar citas que aún no han sido atendidas en ventanilla.'
        dias = cls.dias_hasta_cita(cita)
        if dias < cls.DIAS_MINIMOS_CANCELACION_CIUDADANO:
            return False, (
                f'No es posible cancelar en línea: faltan {max(dias, 0)} día(s) para tu cita. '
                f'La cancelación en el portal solo está disponible con al menos '
                f'{cls.DIAS_MINIMOS_CANCELACION_CIUDADANO} días de anticipación.'
            )
        return True, None

    @classmethod
    def serializar_portal(cls, cita):
        puede, motivo = cls.puede_cancelar_por_ciudadano(cita)
        dias = cls.dias_hasta_cita(cita)
        return {
            'folio': cita.id,
            'nombre': cita.nombre_ciudadano,
            'curp': cita.curp_ciudadano,
            'tramite': cita.tramite.nombre,
            'seccion': cita.tramite.seccion.nombre if cita.tramite.seccion else '',
            'fecha': cita.fecha.isoformat(),
            'hora': cita.hora.strftime('%H:%M'),
            'estado': cita.estado,
            'estado_etiqueta': cls.ESTADO_ETIQUETAS.get(cita.estado, cita.estado),
            'costo': float(cita.tramite.costo),
            'dias_restantes': dias,
            'puede_cancelar': puede,
            'motivo_no_cancelar': motivo,
            'pdf_url': reverse('descargar_comprobante_pdf', args=[cita.id]),
            'qr_url': reverse('imagen_qr_cita', args=[cita.id]),
        }

    @classmethod
    def consultar_portal(cls, folio, curp):
        if not folio or not curp:
            return False, 'Ingresa el folio de tu cita y tu CURP.', None
        cita = cls.obtener_por_folio_curp(folio, curp)
        if not cita:
            return False, 'No se encontró una cita con ese folio y CURP. Verifica los datos.', None
        return True, None, cls.serializar_portal(cita)

    @classmethod
    def cancelar_desde_portal(cls, folio, curp):
        if not folio or not curp:
            return False, 'Ingresa el folio de tu cita y tu CURP.', None
        cita = cls.obtener_por_folio_curp(folio, curp)
        if not cita:
            return False, 'No se encontró una cita con ese folio y CURP. Verifica los datos.', None
        puede, motivo = cls.puede_cancelar_por_ciudadano(cita)
        if not puede:
            return False, motivo, None
        cita.estado = 'CANCELADA'
        cita.save(update_fields=['estado'])
        return True, 'Tu cita fue cancelada correctamente.', cls.serializar_portal(cita)

    @classmethod
    def crear_desde_portal(cls, datos):
        """
        Crea una cita desde el portal ciudadano.
        datos: dict con tramite_id, nombre, curp, cp, direccion, fecha, hora, datos_recien_nacido.
        Retorna (ok, cita|mensaje_error).
        """
        tramite_id = datos.get('tramite_id')
        nombre = (datos.get('nombre') or '').strip()
        curp = (datos.get('curp') or '').strip().upper()
        cp = (datos.get('cp') or '').strip()
        direccion = (datos.get('direccion') or '').strip()
        fecha = datos.get('fecha')
        hora = datos.get('hora')

        if not all([tramite_id, nombre, curp, cp, direccion, fecha, hora]):
            return False, 'Faltan datos requeridos.'
        try:
            curp = validar_curp(curp)
        except ValidationError as exc:
            return False, exc.messages[0]
        if not re.match(r'^[0-9]{5}$', cp):
            return False, 'Código postal inválido.'

        if cls.tiene_cita_activa_curp(curp):
            return False, 'Ya existe una cita programada para estos datos.'

        fecha_obj = datetime.strptime(fecha, '%Y-%m-%d').date()
        ok_fecha, err_fecha = Calendario.validar_fecha_agendamiento(fecha_obj)
        if not ok_fecha:
            return False, err_fecha
        if Calendario.dia_bloqueado_completo(fecha_obj):
            return False, 'Ese día no está disponible para citas.'
        if Calendario.hora_bloqueada(fecha_obj, hora):
            return False, 'Ese horario ya no está disponible.'

        try:
            tramite = TramiteModel.objects.get(id=tramite_id, activo=True)
        except TramiteModel.DoesNotExist:
            return False, 'Trámite no encontrado.'

        valido, error = Calendario.validar_horario(fecha_obj, hora, tramite.duracion_minutos)
        if not valido:
            return False, error

        datos_adicionales = {}
        if es_tramite_registro_nacimiento(tramite.nombre):
            ok_rn, err_rn, datos_rn = validar_datos_recien_nacido(datos.get('datos_recien_nacido'))
            if not ok_rn:
                return False, err_rn
            datos_adicionales = datos_rn

        try:
            cita = CitaModel(
                tramite=tramite,
                nombre_ciudadano=nombre,
                curp_ciudadano=curp,
                codigo_postal=cp,
                direccion=direccion,
                fecha=fecha,
                hora=hora,
                estado='PENDIENTE',
                datos_adicionales=datos_adicionales,
            )
            cita.save()
        except Exception as exc:
            return False, str(exc)

        return True, cita

    @classmethod
    def listar_del_dia(cls, fecha=None, estados=None):
        fecha = fecha or timezone.now().date()
        qs = CitaModel.objects.filter(fecha=fecha).select_related('tramite', 'tramite__seccion')
        if estados:
            qs = qs.filter(estado__in=estados)
        return qs.order_by('hora')

    @classmethod
    def puede_cancelar_por_rol(cls, user):
        return (
            user.is_superuser
            or user.groups.filter(name__in=['oficial', 'Administrador']).exists()
        )

    @classmethod
    def cancelar(cls, cita, usuario_username):
        if cita.estado == 'FINALIZADA':
            return False, 'No se puede cancelar una cita que ya fue finalizada.', None
        if cita.estado == 'CANCELADA':
            return False, 'Esta cita ya está cancelada.', None
        if not cita.puede_cancelarse():
            return False, f'No se puede cancelar una cita en estado {cita.estado}.', None

        monto_descontado = None
        if cita.estado == 'PAGADA':
            try:
                monto_descontado = cita.pagocaja.monto_cobrado
            except ObjectDoesNotExist:
                pass
        cita.estado = 'CANCELADA'
        cita.save(update_fields=['estado'])

        desc_log = f"Cita #{cita.id} ({cita.nombre_ciudadano}) cancelada por {usuario_username}."
        if monto_descontado is not None:
            desc_log += f" Ingreso descontado: ${monto_descontado}."
        ok_msg = 'Cita cancelada correctamente.'
        if monto_descontado is not None:
            ok_msg += f' Se descontó ${monto_descontado} de los ingresos.'
        return True, ok_msg, {
            'nuevo_estado': 'CANCELADA',
            'ingreso_descontado': float(monto_descontado) if monto_descontado is not None else None,
            'log': desc_log,
        }

    @classmethod
    def finalizar(cls, cita):
        if cita.estado != 'PAGADA':
            return False, f'Solo se puede finalizar una cita pagada (actual: {cita.estado}).'
        cita.estado = 'FINALIZADA'
        cita.save(update_fields=['estado'])
        return True, (
            f"Cita #{cita.id} ({cita.nombre_ciudadano}) marcada como FINALIZADA."
        )

    @classmethod
    def revertir_asistencia(cls, cita):
        if cita.estado != 'ASISTIDA':
            return False, f'Solo se puede revertir una cita en estado Asistida (actual: {cita.estado}).'
        cita.estado = 'PENDIENTE'
        cita.usuario_atendio = None
        cita.save(update_fields=['estado', 'usuario_atendio'])
        return True, (
            f"Asistencia revertida: cita #{cita.id} ({cita.nombre_ciudadano}) regresó a PENDIENTE."
        )

    @classmethod
    def _anotar_monto_pagado(cls, citas):
        for cita in citas:
            try:
                cita.monto_pagado = cita.pagocaja.monto_cobrado
            except ObjectDoesNotExist:
                cita.monto_pagado = cita.tramite.costo
        return citas

    @classmethod
    def listar_agenda_operaciones(cls, hoy=None):
        """Hoy (pendiente/asistida) + futuras pendientes, solo visualización operativa."""
        hoy = hoy or timezone.now().date()
        return (
            CitaModel.objects.filter(
                Q(fecha=hoy, estado__in=['PENDIENTE', 'ASISTIDA'])
                | Q(fecha__gt=hoy, estado='PENDIENTE')
            )
            .select_related('tramite', 'tramite__seccion')
            .order_by('fecha', 'hora')
        )

    @classmethod
    def listar_pendientes_agenda(cls, incluir_futuras=True):
        hoy = timezone.now().date()
        qs = CitaModel.objects.filter(estado='PENDIENTE')
        if incluir_futuras:
            qs = qs.filter(fecha__gte=hoy)
        else:
            qs = qs.filter(fecha=hoy)
        return qs.select_related('tramite__seccion').order_by('fecha', 'hora')

    @classmethod
    def listar_fila_caja(cls):
        return CitaModel.objects.filter(
            estado='ASISTIDA',
        ).select_related('tramite__seccion').order_by('hora')

    @classmethod
    def listar_pagadas(cls):
        citas = CitaModel.objects.filter(
            estado='PAGADA',
        ).select_related('tramite__seccion', 'pagocaja').order_by('fecha', 'hora')
        return cls._anotar_monto_pagado(list(citas))

    @classmethod
    def _resumen_meses(cls, estado, incluir_ingresos=False):
        resumen_meses = (
            CitaModel.objects.filter(estado=estado)
            .annotate(mes=TruncMonth('fecha'))
            .values('mes')
            .annotate(
                cantidad=Count('id'),
                **({'ingresos': Sum('pagocaja__monto_cobrado')} if incluir_ingresos else {}),
            )
            .order_by('-mes')
        )
        meses = []
        for item in resumen_meses:
            dt = item['mes']
            if not dt:
                continue
            entrada = {
                'anio': dt.year,
                'mes': dt.month,
                'etiqueta': f"{MESES_ESPANOL.get(dt.month, 'Mes')} {dt.year}",
                'cantidad': item['cantidad'],
            }
            if incluir_ingresos:
                entrada['ingresos'] = item['ingresos'] or 0
            meses.append(entrada)
        return meses

    @classmethod
    def historial_finalizadas(cls, anio=None, mes=None):
        totales_globales = CitaModel.objects.filter(estado='FINALIZADA').aggregate(
            total_citas=Count('id'),
            total_ingresos=Sum('pagocaja__monto_cobrado'),
        )
        contexto = {
            'meses': cls._resumen_meses('FINALIZADA', incluir_ingresos=True),
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
            citas = list(
                CitaModel.objects.filter(estado='FINALIZADA', fecha__year=anio, fecha__month=mes)
                .select_related('tramite__seccion')
                .order_by('-fecha', '-hora')
            )
            cls._anotar_monto_pagado(citas)
            total_ingresos = sum(c.monto_pagado for c in citas)
            contexto.update({
                'mes_detalle': True,
                'citas_mes': citas,
                'mes_nombre': MESES_ESPANOL.get(mes, 'Mes'),
                'anio': anio,
                'mes': mes,
                'total_mes_citas': len(citas),
                'total_mes_ingresos': total_ingresos,
                'panel_anterior_url': reverse('vista_historial_finalizadas'),
            })
        return contexto

    @classmethod
    def historial_canceladas(cls, anio=None, mes=None):
        contexto = {
            'meses': cls._resumen_meses('CANCELADA'),
            'total_global_citas': CitaModel.objects.filter(estado='CANCELADA').count(),
            'mes_detalle': None,
            'citas_mes': [],
            'mes_nombre': '',
            'anio': None,
            'mes': None,
            'total_mes_citas': 0,
        }
        if anio is not None and mes is not None:
            citas = list(
                CitaModel.objects.filter(estado='CANCELADA', fecha__year=anio, fecha__month=mes)
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
                'panel_anterior_url': reverse('vista_historial_canceladas'),
            })
        return contexto

    @classmethod
    def resumen_dashboard(cls, fecha=None):
        fecha = fecha or timezone.now().date()
        from citas.servicios.caja import Caja
        return {
            'total_citas_hoy': CitaModel.objects.filter(fecha=fecha).count(),
            'citas_pendientes': CitaModel.objects.filter(fecha=fecha, estado='PENDIENTE').count(),
            'citas_en_caja': CitaModel.objects.filter(fecha=fecha, estado='ASISTIDA').count(),
            'citas_pagadas': CitaModel.objects.filter(fecha=fecha, estado='PAGADA').count(),
            'citas_finalizadas': CitaModel.objects.filter(fecha=fecha, estado='FINALIZADA').count(),
            'ingresos_hoy': Caja.ingresos_del_dia(fecha),
            'citas_hoy': CitaModel.objects.filter(fecha=fecha).select_related('tramite').order_by('hora'),
        }

    @classmethod
    def _serializar_cita_listado(cls, cita):
        return {
            'id': cita.id,
            'hora': cita.hora.strftime('%H:%M'),
            'fecha': cita.fecha.isoformat(),
            'nombre': cita.nombre_ciudadano,
            'curp': cita.curp_ciudadano,
            'tramite': cita.tramite.nombre,
            'seccion': cita.tramite.seccion.nombre if cita.tramite.seccion else '',
            'estado': cita.estado,
            'puede_cancelar': cita.puede_cancelarse(),
            'costo': float(cita.tramite.costo),
            'es_futura': cita.fecha > timezone.now().date(),
        }

    @classmethod
    def serializar_agenda_operaciones(cls, hoy=None, limite=200):
        citas = []
        for c in cls.listar_agenda_operaciones(hoy)[:limite]:
            citas.append(cls._serializar_cita_listado(c))
        return citas

    @classmethod
    def serializar_para_api(cls, estado_filtro=None, fecha=None, limite=100):
        fecha = fecha or timezone.now().date()
        qs = CitaModel.objects.select_related('tramite', 'tramite__seccion').filter(fecha=fecha)
        if estado_filtro:
            estados = [e.strip() for e in estado_filtro.split(',')]
            qs = qs.filter(estado__in=estados)
        citas = []
        for c in qs.order_by('fecha', 'hora')[:limite]:
            citas.append(cls._serializar_cita_listado(c))
        return citas

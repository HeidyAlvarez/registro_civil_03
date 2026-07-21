"""Tabla CRC 25 — Trámite (gestión del catálogo)."""

from django.core.exceptions import ValidationError

from citas.models import SeccionTramite, Tramite as TramiteModel


class Tramite:
    """Catálogo activo para el portal y reglas de desactivación."""

    Modelo = TramiteModel

    @classmethod
    def listar_activos_agrupados(cls):
        tramites_qs = (
            TramiteModel.objects.filter(activo=True)
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
            grupos[clave]['tramites'].append(cls._serializar(tramite))
        return [grupos[k] for k in orden]

    @classmethod
    def obtener_activo(cls, tramite_id):
        return TramiteModel.objects.get(id=tramite_id, activo=True)

    @staticmethod
    def _serializar(tramite):
        return {
            'id': tramite.id,
            'nombre': tramite.nombre,
            'costo': float(tramite.costo),
            'duracion_minutos': tramite.duracion_minutos,
            'documentos': tramite.documentos_requeridos or '',
        }

    @classmethod
    def puede_desactivarse(cls, tramite):
        return not tramite.tiene_citas_pendientes_futuras()

    @classmethod
    def crear_seccion(cls, nombre):
        nombre = (nombre or '').strip()
        if not nombre:
            return False, 'El nombre de la sección es obligatorio.', None
        seccion, _ = SeccionTramite.objects.get_or_create(nombre=nombre)
        return True, f"Sección '{nombre}' creada correctamente.", seccion

    @classmethod
    def crear_tramite(cls, seccion_id, nombre, costo, duracion, documentos=''):
        nombre = (nombre or '').strip()
        if not seccion_id or not nombre:
            return False, 'Sección y nombre del trámite son obligatorios.', None
        seccion = SeccionTramite.objects.get(id=seccion_id)
        tramite = TramiteModel.objects.create(
            seccion=seccion,
            nombre=nombre,
            costo=costo,
            duracion_minutos=int(duracion) if duracion else 15,
            documentos_requeridos=(documentos or '').strip() or None,
        )
        return True, f"Opción '{nombre}' vinculada con éxito.", tramite

    @classmethod
    def actualizar_tramite(cls, tramite_id, datos):
        tramite = TramiteModel.objects.get(id=tramite_id)
        costo_anterior = tramite.costo
        tramite.nombre = datos.get('nombre', tramite.nombre).strip()
        tramite.costo = datos.get('costo', tramite.costo)
        tramite.duracion_minutos = int(datos.get('duracion', tramite.duracion_minutos) or 15)
        tramite.documentos_requeridos = datos.get('documentos', '').strip() or None
        seccion_id = datos.get('seccion_id')
        if seccion_id:
            tramite.seccion = SeccionTramite.objects.get(id=seccion_id)
        try:
            tramite.save()
        except ValidationError as exc:
            return False, '; '.join(getattr(exc, 'messages', [str(exc)])), None
        return True, f"Trámite '{tramite.nombre}' actualizado.", costo_anterior

    @classmethod
    def alternar_activo(cls, tramite_id):
        tramite = TramiteModel.objects.get(id=tramite_id)
        if tramite.activo and not cls.puede_desactivarse(tramite):
            return False, (
                f"No se puede desactivar '{tramite.nombre}': tiene citas futuras Pendientes."
            ), None
        tramite.activo = not tramite.activo
        try:
            tramite.save()
        except ValidationError as exc:
            return False, '; '.join(exc.messages), None
        estado_txt = 'activado' if tramite.activo else 'desactivado'
        return True, f"Trámite '{tramite.nombre}' {estado_txt}.", estado_txt

    @classmethod
    def listar_catalogo_admin(cls):
        secciones = SeccionTramite.objects.all().order_by('nombre')
        tramites = (
            TramiteModel.objects.select_related('seccion')
            .order_by('seccion__nombre', 'nombre', '-activo')
        )
        return secciones, tramites

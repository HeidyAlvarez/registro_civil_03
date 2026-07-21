from django.contrib import admin, messages
from django.urls import path
from django.db.models.deletion import ProtectedError
from django.core.exceptions import ValidationError
from autenticacion.servicios import Login
from .models import SeccionTramite, Tramite, Cita, PagoCaja, BitacoraAuditoria, CorteCajaDiario
from .views import dashboard_personalizado
from .auditoria import registrar_log, registrar_log_seguridad, rol_usuario
from django.contrib.auth.models import Group
from django.contrib.admin import AdminSite
from django.shortcuts import redirect

# Grupos: ver autenticacion.admin.GrupoRegistroCivilAdmin


class AuditoriaAdminMixin:
    def _log(self, request, accion, descripcion):
        registrar_log(request, accion, f"[{rol_usuario(request.user)}] {descripcion}")


class SoloSuperusuarioAdminMixin:
    """Pantallas técnicas de Django Admin: solo superusuario."""

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_superuser:
            return False
        return super().has_delete_permission(request, obj)


# ── Registros de modelos ──────────────────────────────────────────────

@admin.register(SeccionTramite)
class SeccionTramiteAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'nombre']
    search_fields = ['nombre']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            self._log(request, 'INFO', f"Sección actualizada: '{obj.nombre}'.")
        else:
            self._log(request, 'INFO', f"Sección creada: '{obj.nombre}'.")

    def delete_model(self, request, obj):
        nombre = obj.nombre
        super().delete_model(request, obj)
        self._log(request, 'INFO', f"Sección eliminada: '{nombre}'.")


@admin.register(Tramite)
class TramiteAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = ['seccion', 'nombre', 'costo', 'duracion_minutos', 'activo']
    search_fields = ['nombre']
    fields = ['seccion', 'nombre', 'duracion_minutos', 'costo', 'documentos_requeridos', 'activo']

    def _intentar_eliminar_tramite(self, request, obj):
        try:
            nombre = obj.nombre
            obj.delete()
            self._log(request, 'INFO', f"Trámite eliminado: '{nombre}'.")
            return True
        except ValidationError as e:
            messages.error(request, e.messages[0] if e.messages else str(e))
        except ProtectedError:
            messages.error(
                request,
                f"No se puede eliminar '{obj.nombre}' porque tiene citas registradas en el historial. "
                "Desactívalo con el campo «Activo» en su lugar.",
            )
        return False

    def delete_model(self, request, obj):
        self._intentar_eliminar_tramite(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            self._intentar_eliminar_tramite(request, obj)

    def save_model(self, request, obj, form, change):
        if change:
            prev = Tramite.objects.filter(pk=obj.pk).first()
            if prev and prev.activo and not obj.activo and obj.tiene_citas_pendientes_futuras():
                messages.error(
                    request,
                    f"No se puede desactivar '{obj.nombre}': tiene citas futuras Pendientes.",
                )
                obj.activo = True
        super().save_model(request, obj, form, change)
        if not change:
            self._log(
                request, 'MODIFICACION_COSTO',
                f"Trámite creado en admin: '{obj.nombre}' (${obj.costo}).",
            )


@admin.register(Cita)
class CitaAdmin(AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'fecha', 'hora', 'nombre_ciudadano', 'tramite', 'estado']
    search_fields = ['curp_ciudadano', 'nombre_ciudadano']

    def has_add_permission(self, request):
        """Las citas nuevas se agendan solo por el portal ciudadano."""
        return False

    def save_model(self, request, obj, form, change):
        prev = None
        if change:
            prev = Cita.objects.filter(pk=obj.pk).first()
            if prev and prev.estado == 'FINALIZADA' and obj.estado != 'FINALIZADA':
                messages.error(request, 'Una cita finalizada no puede cambiar de estado.')
                return
            if prev and obj.estado == 'CANCELADA' and prev.estado == 'FINALIZADA':
                messages.error(request, 'No se puede cancelar una cita finalizada.')
                return
        super().save_model(request, obj, form, change)
        if change and prev:
            if prev.estado != obj.estado:
                self._log(
                    request, 'MODIFICACION_CITA',
                    f"Cita #{obj.id} ({obj.nombre_ciudadano}): {prev.estado} → {obj.estado} (admin).",
                )

    def delete_model(self, request, obj):
        desc = f"Cita #{obj.id} ({obj.nombre_ciudadano}) eliminada desde admin."
        super().delete_model(request, obj)
        self._log(request, 'MODIFICACION_CITA', desc)


@admin.register(PagoCaja)
class PagoCajaAdmin(SoloSuperusuarioAdminMixin, AuditoriaAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'cita', 'monto_cobrado', 'fecha_pago', 'cajero', 'corte_cierre_listo')
    search_fields = ('cita__nombre_ciudadano', 'id')
    actions = ['cerrar_corte_masivo']

    def has_change_permission(self, request, obj=None):
        if obj is not None and obj.corte_cierre_listo:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj is not None and obj.corte_cierre_listo:
            return False
        return super().has_delete_permission(request, obj)

    def cerrar_corte_masivo(self, request, queryset):
        total = queryset.count()
        queryset.update(corte_cierre_listo=True)
        self._log(request, 'CIERRE_CORTE', f"Cierre de corte aplicado a {total} pago(s).")
    cerrar_corte_masivo.short_description = "🔒 Cerrar corte para los registros seleccionados"


@admin.register(CorteCajaDiario)
class CorteCajaDiarioAdmin(SoloSuperusuarioAdminMixin, admin.ModelAdmin):
    list_display = ('fecha', 'total_recaudado', 'cantidad_pagos', 'cerrado_por', 'cerrado_el')
    readonly_fields = ('fecha', 'total_recaudado', 'desglose_tramites', 'cantidad_pagos', 'cerrado_por', 'cerrado_el')
    ordering = ('-fecha',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(BitacoraAuditoria)
class BitacoraAuditoriaAdmin(admin.ModelAdmin):
    list_display = ('fecha_hora', 'usuario', 'accion', 'descripcion', 'ip_direccion')
    search_fields = ('descripcion', 'usuario__username', 'ip_direccion')
    readonly_fields = ('usuario', 'accion', 'descripcion', 'fecha_hora', 'ip_direccion')

    def changelist_view(self, request, extra_context=None):
        from django.urls import reverse
        qs = request.GET.urlencode()
        url = reverse('vista_bitacora')
        if qs:
            url = f'{url}?{qs}'
        return redirect(url)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ── Inyectar URL del dashboard en admin.site ─────────────────────────

_original_get_urls = admin.AdminSite.get_urls

def _custom_get_urls(self):
    urls = _original_get_urls(self)
    custom_urls = [
        path('citas/dashboard/', self.admin_view(dashboard_personalizado), name='citas_dashboard'),
    ]
    return custom_urls + urls

admin.AdminSite.get_urls = _custom_get_urls


_original_index = admin.AdminSite.index

def _custom_index(self, request, extra_context=None):
    if request.user.is_authenticated and (
        request.user.is_superuser
        or request.user.groups.filter(name='Administrador').exists()
    ):
        return redirect('citas_dashboard')
    return _original_index(self, request, extra_context)

admin.AdminSite.index = _custom_index


# ── Personalización visual ────────────────────────────────────────────
admin.site.site_header = "Registro Civil"
admin.site.site_title = "Registro Civil"
admin.site.index_title = "Panel de Administración"

original_login = AdminSite.login

def custom_login(self, request, extra_context=None):
    if request.method == 'POST':
        from django.contrib.auth import authenticate, login
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect(Login.url_panel_para_usuario(user))
        elif username:
            registrar_log_seguridad(
                request,
                'ACCESO_DENEGADO',
                Login.mensaje_intento_fallido(username),
                username=username,
            )
    return original_login(self, request, extra_context)

AdminSite.login = custom_login
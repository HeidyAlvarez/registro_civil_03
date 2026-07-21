# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from .models import UsuarioRegistroCivil

ROL_A_GRUPO = {
    UsuarioRegistroCivil.ADMINISTRADOR: 'Administrador',
    UsuarioRegistroCivil.OFICIAL_PRINCIPAL: 'oficial',
    UsuarioRegistroCivil.CAPTURISTA: 'Capturista',
}

GRUPOS_SISTEMA = frozenset(ROL_A_GRUPO.values())


def sincronizar_rol_y_grupos(usuario):
    """ HU-6: Sincroniza el rol del modelo con los grupos de Django. """
    nombre_grupo = ROL_A_GRUPO.get(usuario.rol)
    if not nombre_grupo:
        return
    grupo, _ = Group.objects.get_or_create(name=nombre_grupo)
    usuario.groups.set([grupo])
    usuario.is_staff = usuario.rol in (
        UsuarioRegistroCivil.ADMINISTRADOR,
        UsuarioRegistroCivil.OFICIAL_PRINCIPAL,
    )
    usuario.save(update_fields=['is_staff'])


@admin.register(UsuarioRegistroCivil)
class UsuarioRegistroCivilAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Información de Roles (XP)', {'fields': ('rol',)}),
    )
    list_display = ['username', 'email', 'rol', 'is_staff']
    list_filter = ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sincronizar_rol_y_grupos(obj)


try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


@admin.register(Group)
class GrupoRegistroCivilAdmin(admin.ModelAdmin):
    """Grupos de permisos del sistema (Administrador, oficial, Capturista, etc.)."""
    search_fields = ('name',)
    filter_horizontal = ('permissions',)
    list_display = ('name', 'usuarios_count', 'permisos_count')
    ordering = ('name',)

    @admin.display(description='Usuarios')
    def usuarios_count(self, obj):
        return obj.user_set.count()

    @admin.display(description='Permisos')
    def permisos_count(self, obj):
        return obj.permissions.count()

    def has_delete_permission(self, request, obj=None):
        if obj and obj.name in GRUPOS_SISTEMA:
            return False
        return super().has_delete_permission(request, obj)

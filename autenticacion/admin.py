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

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sincronizar_rol_y_grupos(obj)


# Grupos gestionados automáticamente por rol — no mostrar sección duplicada
try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass

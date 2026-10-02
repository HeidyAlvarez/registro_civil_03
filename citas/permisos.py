"""Reglas de autorización compartidas por vistas HTML y API."""


def es_administrador(user):
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name='Administrador').exists()
    )


def es_oficial_o_admin(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name__in=['oficial', 'Administrador']).exists()
    )


def es_capturista_o_superior(user):
    return user.is_authenticated and (
        user.is_superuser
        or user.groups.filter(name__in=['Capturista', 'oficial', 'Administrador']).exists()
    )


def puede_ver_panel_citas(user):
    return user.is_authenticated and (
        user.is_staff or es_capturista_o_superior(user) or es_oficial_o_admin(user)
    )


def es_admin_o_super(user):
    return es_administrador(user)

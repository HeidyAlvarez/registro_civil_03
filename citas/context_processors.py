from django.urls import reverse


def _url_panel_inicio(user):
    if not user.is_authenticated:
        return reverse('admin:login')
    if user.is_superuser:
        return reverse('citas_dashboard')
    grupos = set(user.groups.values_list('name', flat=True))
    if 'oficial' in grupos:
        return reverse('dashboard_oficial')
    if 'Capturista' in grupos:
        return reverse('dashboard_capturista')
    if user.is_staff or 'Administrador' in grupos:
        return reverse('citas_dashboard')
    return reverse('citas_dashboard')


def panel_inicio(request):
    url = _url_panel_inicio(request.user)
    path = request.path.rstrip('/')
    home = url.rstrip('/')
    return {
        'panel_inicio_url': url,
        'panel_anterior_url': url,
        'en_panel_inicio': path == home,
    }

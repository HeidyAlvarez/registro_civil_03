from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def frontend_shell(request, path=''):
    """Entrega la SPA React; Django conserva APIs, sesión y administración."""
    return render(request, 'frontend/index.html')

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from citas import views as citas_views

urlpatterns = [
    # Dashboard ANTES que admin/ para que Django lo encuentre primero
    path('admin/citas/dashboard/', citas_views.dashboard_personalizado, name='citas_dashboard'),
    path('admin/', admin.site.urls),
    path('citas/', include('citas.urls')),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', citas_views.redirigir_por_rol, name='inicio'),
    path('redirigir/', citas_views.redirigir_por_rol, name='redirigir'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




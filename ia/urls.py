from django.urls import path

from . import views

urlpatterns = [
    path('', views.portal_ia, name='ia_ciudadano'),
    path('asistente/', views.asistente, name='ia_asistente'),
    path('dias-concurridos/', views.dias_concurridos, name='ia_dias'),
    path('interno/dias-concurridos/', views.dias_concurridos_interno, name='ia_dias_interno'),
    path('sugerencia/', views.sugerencia_horario, name='ia_sugerencia'),
    path('notificaciones/', views.notificaciones_ciudadano, name='ia_notificaciones'),
    path('notificaciones/leida/', views.marcar_notificacion, name='ia_notificacion_leida'),

    path('interno/', views.panel_interno, name='ia_interno'),
    path('interno/temporadas/', views.temporadas, name='ia_temporadas'),
    path('interno/optimizacion/', views.optimizacion, name='ia_optimizacion'),
    path('interno/optimizacion/<int:propuesta_id>/', views.optimizacion_detalle, name='ia_optimizacion_detalle'),
    path('interno/urgentes/', views.casos_urgentes, name='ia_urgentes'),
    path('interno/urgentes/<int:alerta_id>/revisar/', views.revisar_urgente, name='ia_urgente_revisar'),
    path('interno/anomalias/', views.anomalias, name='ia_anomalias'),
    path('interno/anomalias/<int:anomalia_id>/', views.anomalia_detalle, name='ia_anomalia_detalle'),
    path('interno/reportes/', views.reportes, name='ia_reportes'),
    path('interno/reportes/<slug:tipo>/', views.reporte_detalle, name='ia_reporte'),
    path('interno/sincronizar/', views.forzar_sincronizacion, name='ia_sincronizar'),
    path('interno/atencion/<int:solicitud_id>/', views.atender_solicitud, name='ia_atender_solicitud'),
]

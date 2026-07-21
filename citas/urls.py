from django.urls import path
from . import views

urlpatterns = [
    path('horarios/gestionar/', views.gestionar_horarios, name='gestionar_horarios'),
    path('horarios/eliminar/<int:bloqueo_id>/', views.eliminar_bloqueo, name='eliminar_bloqueo'),
    path('horarios/eliminar-dia/<str:fecha>/', views.eliminar_bloqueos_dia, name='eliminar_bloqueos_dia'),

    path('citas/pagadas/', views.vista_citas_pagadas, name='vista_citas_pagadas'),
    path('citas/finalizadas/', views.vista_historial_finalizadas, name='vista_historial_finalizadas'),
    path('citas/finalizadas/<int:anio>/<int:mes>/', views.vista_historial_finalizadas, name='vista_historial_finalizadas_mes'),
    path('citas/canceladas/', views.vista_historial_canceladas, name='vista_historial_canceladas'),
    path('citas/canceladas/<int:anio>/<int:mes>/', views.vista_historial_canceladas, name='vista_historial_canceladas_mes'),
    path('bitacora/', views.vista_bitacora, name='vista_bitacora'),
    path('citas/finalizar/<int:cita_id>/', views.finalizar_cita, name='finalizar_cita'),
    path('citas/cancelar/<int:cita_id>/', views.cancelar_cita, name='cancelar_cita'),
    path('citas/revertir-asistencia/<int:cita_id>/', views.revertir_asistencia_cita, name='revertir_asistencia'),
    
    # 📅 AGENDA
    path('agenda/', views.vista_agenda, name='vista_agenda'),

    # 📷 ESCÁNER QR
    path('escanear/<int:cita_id>/', views.vista_escanear_qr, name='escanear_qr'),
    path('validar/<int:cita_id>/', views.validar_cita, name='validar_cita'),
    path('validar/<int:cita_id>/<str:token>/', views.validar_cita, name='validar_cita_token'),
    path('validar-qr/<int:cita_id>/', views.procesar_validacion_qr, name='procesar_qr'),

    # 💰 CAJA
    path('caja/', views.vista_fila_caja, name='fila_caja'),
    path('caja/cobrar/<int:cita_id>/', views.registrar_pago_ventanilla, name='procesar_cobro'),

    # 📊 REPORTES
    path('caja/reporte/', views.vista_reporte_caja, name='reporte_caja'),
    path('caja/reporte/historial/<int:anio>/<int:mes>/', views.vista_reporte_caja, name='reporte_caja_historial'),
    path('caja/corte/cerrar/', views.cerrar_corte_diario, name='cerrar_corte_diario'),

    # ⚙️ CATÁLOGO
    path('catalogo/agregar/', views.agregar_elemento_catalogo, name='agregar_elemento_catalogo'),

    # 👤 REGISTRO
    path('registrar/', views.vista_registrar, name='registrar'),

    # 🌐 PORTAL CIUDADANO
    path('', views.portal_agendar, name='portal_ciudadano'),
    path('api/tramites/', views.api_tramites, name='api_tramites'),
    path('api/horarios/', views.api_horarios, name='api_horarios'),
    path('api/validar-curp/', views.api_validar_curp_portal, name='api_validar_curp_portal'),
    path('api/consultar-cita/', views.api_consultar_cita_portal, name='api_consultar_cita_portal'),
    path('api/cancelar-cita/', views.api_cancelar_cita_portal, name='api_cancelar_cita_portal'),
    path('api/citas/', views.api_citas_estado, name='api_citas_estado'),
    path('api/dashboard/', views.api_resumen_dashboard, name='api_resumen_dashboard'),
    path('agendar/', views.api_crear_cita, name='api_crear_cita'),
    path('comprobante/<int:cita_id>/pdf/', views.descargar_comprobante_pdf, name='descargar_comprobante_pdf'),

    # CAPTURISTA
    path('capturista/', views.dashboard_capturista, name='dashboard_capturista'),

    # OFICIAL
    path('oficial/', views.dashboard_oficial, name='dashboard_oficial'),
]
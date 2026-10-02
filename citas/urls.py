from django.urls import include, path
from . import views
from . import api_v1
from .frontend import frontend_shell

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

    # Módulo de IA (ciudadanos y control interno)
    path('ia/', include('ia.urls')),

    # 🌐 PORTAL CIUDADANO
    path('', frontend_shell, name='portal_ciudadano'),
    path('agendar-cita/', frontend_shell, name='frontend_agendar'),
    path('consultar/', frontend_shell, name='frontend_consultar'),
    path('cancelar/', frontend_shell, name='frontend_cancelar'),
    path('tramites/', frontend_shell, name='frontend_tramites'),
    path('ubicacion/', frontend_shell, name='frontend_ubicacion'),
    path('inteligencia/', frontend_shell, name='frontend_ia'),
    path('inteligencia/<path:path>/', frontend_shell, name='frontend_ia_path'),
    path('acceso/', frontend_shell, name='frontend_acceso'),
    path('panel/', frontend_shell, name='frontend_panel'),
    path('panel/<path:path>/', frontend_shell, name='frontend_panel_path'),
    path('portal-anterior/', views.portal_agendar, name='portal_anterior'),

    # API v1 para React
    path('api/v1/auth/me/', api_v1.session_me, name='api_v1_session'),
    path('api/v1/auth/login/', api_v1.session_login, name='api_v1_login'),
    path('api/v1/auth/logout/', api_v1.session_logout, name='api_v1_logout'),
    path('api/v1/navigation/', api_v1.navigation, name='api_v1_navigation'),
    path('api/v1/audit/', api_v1.audit_log, name='api_v1_audit'),
    path('api/v1/reports/financial/', api_v1.financial_report, name='api_v1_financial_report'),
    path('api/v1/schedule-blocks/', api_v1.schedule_blocks, name='api_v1_schedule_blocks'),
    path('api/v1/schedule-blocks/<int:block_id>/', api_v1.schedule_block_detail, name='api_v1_schedule_block_detail'),
    path('api/v1/catalog/', api_v1.catalog_management, name='api_v1_catalog'),
    path('api/tramites/', views.api_tramites, name='api_tramites'),
    path('api/horarios/', views.api_horarios, name='api_horarios'),
    path('api/validar-curp/', views.api_validar_curp_portal, name='api_validar_curp_portal'),
    path('api/consultar-cita/', views.api_consultar_cita_portal, name='api_consultar_cita_portal'),
    path('api/cancelar-cita/', views.api_cancelar_cita_portal, name='api_cancelar_cita_portal'),
    path('api/citas/', views.api_citas_estado, name='api_citas_estado'),
    path('api/dashboard/', views.api_resumen_dashboard, name='api_resumen_dashboard'),
    path('agendar/', views.api_crear_cita, name='api_crear_cita'),
    path('qr/<int:cita_id>/<str:token>/', views.imagen_qr_cita, name='imagen_qr_cita'),
    path('comprobante/<int:cita_id>/<str:token>/pdf/', views.descargar_comprobante_pdf, name='descargar_comprobante_pdf'),

    # CAPTURISTA
    path('capturista/', views.dashboard_capturista, name='dashboard_capturista'),

    # OFICIAL
    path('oficial/', views.dashboard_oficial, name='dashboard_oficial'),
]
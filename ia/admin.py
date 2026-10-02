from django.contrib import admin

from .models import (
    AlertaUrgente,
    Anomalia,
    EventoInvestigacion,
    NotificacionInteligente,
    PropuestaOptimizacion,
    ReglaPrioridad,
    SolicitudAtencion,
)


@admin.register(ReglaPrioridad)
class ReglaPrioridadAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'minutos_umbral', 'estados', 'solo_hoy', 'activa')


@admin.register(AlertaUrgente)
class AlertaUrgenteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'estado', 'tiempo_minutos', 'creada_el')
    list_filter = ('estado',)


@admin.register(Anomalia)
class AnomaliaAdmin(admin.ModelAdmin):
    list_display = ('folio', 'tipo', 'estado', 'area', 'detectada_el')
    list_filter = ('tipo', 'estado')


@admin.register(EventoInvestigacion)
class EventoInvestigacionAdmin(admin.ModelAdmin):
    list_display = ('anomalia', 'accion', 'usuario', 'fecha_hora')


@admin.register(PropuestaOptimizacion)
class PropuestaOptimizacionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'estado', 'creada_el', 'revisada_por')


@admin.register(NotificacionInteligente)
class NotificacionInteligenteAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'destino', 'categoria', 'leida', 'creado_el')
    list_filter = ('destino', 'categoria', 'leida')


@admin.register(SolicitudAtencion)
class SolicitudAtencionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'curp', 'estado', 'creado_el')
    list_filter = ('estado',)

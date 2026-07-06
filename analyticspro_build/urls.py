from django.urls import path
from analyticspro.views import dashboard, api_calls, api_calls_extended, api_agents, api_meta

app_name = 'analyticspro'

urlpatterns = [
    # ── Dashboard HTML ───────────────────────────────────────────
    path('analyticspro/', dashboard.index, name='dashboard'),

    # ── Meta (campanas, agentes, sync) ───────────────────────────
    path('analyticspro/api/campanas/', api_meta.campanas, name='api_campanas'),
    path('analyticspro/api/agentes/', api_meta.agentes, name='api_agentes'),
    path('analyticspro/api/sync/status/', api_meta.sync_status, name='api_sync_status'),

    # ── Call analytics ───────────────────────────────────────────
    path('analyticspro/api/kpis/', api_calls.kpis, name='api_kpis'),
    path('analyticspro/api/distribucion-llamadas/', api_calls.distribucion_llamadas, name='api_distribucion_llamadas'),
    path('analyticspro/api/evolucion-hora/', api_calls.evolucion_hora, name='api_evolucion_hora'),
    path('analyticspro/api/nivel-servicio/', api_calls.nivel_servicio, name='api_nivel_servicio'),
    path('analyticspro/api/nivel-servicio-detallado/', api_calls.nivel_servicio_detallado, name='api_nivel_servicio_detallado'),
    path('analyticspro/api/causas-no-atencion/', api_calls.causas_no_atencion, name='api_causas_no_atencion'),
    path('analyticspro/api/llamadas-atendidas/', api_calls.llamadas_atendidas, name='api_llamadas_atendidas'),
    path('analyticspro/api/llamadas-abandonadas/', api_calls.llamadas_abandonadas, name='api_llamadas_abandonadas'),
    path('analyticspro/api/llamadas-por-tipo/', api_calls.llamadas_por_tipo, name='api_llamadas_por_tipo'),
    path('analyticspro/api/llamadas-por-campana/', api_calls.llamadas_por_campana, name='api_llamadas_por_campana'),
    path('analyticspro/api/evolucion-diaria/', api_calls.evolucion_diaria, name='api_evolucion_diaria'),

    # ── Call analytics extended ──────────────────────────────────
    path('analyticspro/api/distribucion-por-campana-detalle/', api_calls_extended.distribucion_por_campana_detalle, name='api_distribucion_campana_detalle'),
    path('analyticspro/api/transferencias/', api_calls_extended.transferencias, name='api_transferencias'),
    path('analyticspro/api/distribucion-horaria-detallada/', api_calls_extended.distribucion_horaria_detallada, name='api_distribucion_horaria_detallada'),
    path('analyticspro/api/tabla-distribucion-horaria/', api_calls_extended.tabla_distribucion_horaria, name='api_tabla_distribucion_horaria'),
    path('analyticspro/api/salientes/dashboard/', api_calls_extended.salientes_dashboard, name='api_salientes_dashboard'),
    path('analyticspro/api/salientes/por-agente/', api_calls_extended.salientes_por_agente, name='api_salientes_por_agente'),
    path('analyticspro/api/salientes/detalle/', api_calls_extended.llamadas_salientes_detalle, name='api_salientes_detalle'),

    # ── Call analytics extended — nuevas ────────────────────────────────
    path('analyticspro/api/nivel-atencion-campanas/', api_calls_extended.nivel_atencion_campanas, name='api_nivel_atencion_campanas'),

    # ── Dialer (tipo_llamada=2, marcador predictivo) ─────────────────────
    path('analyticspro/api/dialer/dashboard/', api_calls_extended.dialer_dashboard, name='api_dialer_dashboard'),
    path('analyticspro/api/dialer/detalle/', api_calls_extended.dialer_detalle, name='api_dialer_detalle'),

    # ── Agent analytics ──────────────────────────────────────────
    path('analyticspro/api/agentes/rendimiento/', api_agents.rendimiento, name='api_agentes_rendimiento'),

    # ── Agent analytics — nuevas ─────────────────────────────────────────
    path('analyticspro/api/agentes/rendimiento-completo/', api_agents.rendimiento_completo, name='api_agentes_rendimiento_completo'),
    path('analyticspro/api/agentes/heatmap-completo/', api_agents.disponibilidad_heatmap_completo, name='api_agentes_heatmap_completo'),
    path('analyticspro/api/agentes/<int:agente_id>/sesiones/', api_agents.sesiones, name='api_agentes_sesiones'),
    path('analyticspro/api/agentes/<int:agente_id>/pausas/', api_agents.pausas, name='api_agentes_pausas'),
    path('analyticspro/api/agentes/<int:agente_id>/timeline/', api_agents.timeline, name='api_agentes_timeline'),
    path('analyticspro/api/agentes/disponibilidad/', api_agents.disponibilidad, name='api_agentes_disponibilidad'),
    path('analyticspro/api/agentes/disponibilidad-heatmap/', api_agents.disponibilidad_heatmap, name='api_agentes_heatmap'),
    path('analyticspro/api/agentes/<int:agente_id>/sesiones/', api_agents.sesiones, name='api_agente_sesiones'),
    path('analyticspro/api/agentes/<int:agente_id>/pausas/', api_agents.pausas, name='api_agente_pausas'),
    path('analyticspro/api/agentes/<int:agente_id>/timeline/', api_agents.timeline, name='api_agente_timeline'),

    # ── Exports ──────────────────────────────────────────────────
    path('analyticspro/api/export/llamadas-atendidas/', api_calls.export_llamadas_atendidas, name='api_export_llamadas_atendidas'),
    path('analyticspro/api/export/llamadas-abandonadas/', api_calls.export_llamadas_abandonadas, name='api_export_llamadas_abandonadas'),
    path('analyticspro/api/export/agentes-rendimiento/', api_agents.export_rendimiento, name='api_export_agentes_rendimiento'),
]

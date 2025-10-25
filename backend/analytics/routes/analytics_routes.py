"""
Rutas de la API para Analytics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date
import time

from ..database import get_db
from ..services.call_analytics import CallAnalyticsService
from ..services.agent_analytics import AgentAnalyticsService
from ..models.omnileads_models import Campana, AgenteProfile, User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# Simple cache for campanas and agentes (expires after 5 minutes)
_campanas_cache = {'data': None, 'timestamp': 0}
_agentes_cache = {'data': None, 'timestamp': 0}
CACHE_TTL = 300  # 5 minutes


async def parse_filters(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    campana_id: Optional[int] = Query(None, description="ID de campaña (único)"),
    campana_ids: Optional[str] = Query(None, description="IDs de campañas separados por coma"),
    tipo_campana: Optional[int] = Query(None, description="Tipo de campaña"),
    agente_id: Optional[int] = Query(None, description="ID de agente (único)"),
    agente_ids: Optional[str] = Query(None, description="IDs de agentes separados por coma"),
    tipo_llamada: Optional[str] = Query(None, description="Tipo de llamada: entrantes o salientes")
) -> dict:
    """Parse y retorna los filtros comunes"""
    filters = {}
    if fecha_inicio:
        filters['fecha_inicio'] = datetime.combine(fecha_inicio, datetime.min.time())
    if fecha_fin:
        filters['fecha_fin'] = datetime.combine(fecha_fin, datetime.max.time())
    
    # Soportar tanto campana_id único como campana_ids múltiples
    if campana_ids:
        filters['campana_ids'] = [int(id.strip()) for id in campana_ids.split(',') if id.strip()]
    elif campana_id:
        filters['campana_id'] = campana_id
    
    if tipo_campana:
        filters['tipo_campana'] = tipo_campana
    
    # Soportar tanto agente_id único como agente_ids múltiples
    if agente_ids:
        filters['agente_ids'] = [int(id.strip()) for id in agente_ids.split(',') if id.strip()]
    elif agente_id:
        filters['agente_id'] = agente_id
    
    # Tipo de llamada
    if tipo_llamada:
        filters['tipo_llamada'] = tipo_llamada
    
    return filters


async def parse_filters_no_agente(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    campana_id: Optional[int] = Query(None, description="ID de campaña"),
    tipo_campana: Optional[int] = Query(None, description="Tipo de campaña")
) -> dict:
    """Parse filtros sin agente_id (para evitar conflicto con path params)"""
    filters = {}
    if fecha_inicio:
        filters['fecha_inicio'] = datetime.combine(fecha_inicio, datetime.min.time())
    if fecha_fin:
        filters['fecha_fin'] = datetime.combine(fecha_fin, datetime.min.time())
    if campana_id:
        filters['campana_id'] = campana_id
    if tipo_campana:
        filters['tipo_campana'] = tipo_campana
    return filters


@router.get("/test")
async def test_connection(db: Session = Depends(get_db)):
    """Test de conexión a la base de datos"""
    try:
        # Intentar contar registros
        from ..models.omnileads_models import LlamadaLog
        count = db.query(LlamadaLog).count()
        return {
            "status": "success",
            "message": "Conexión exitosa a PostgreSQL OmniLeads",
            "total_llamadas": count
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@router.get("/kpis")
async def get_kpis(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene los KPIs principales"""
    service = CallAnalyticsService(db)
    return service.get_kpis(filters)


@router.get("/llamadas-por-tipo")
async def get_llamadas_por_tipo(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución separando ENTRANTES vs SALIENTES (crítico Power BI)"""
    service = CallAnalyticsService(db)
    return service.get_llamadas_por_tipo(filters)


@router.get("/distribucion-llamadas")
async def get_distribucion_llamadas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la distribución de llamadas por estado"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_llamadas(filters)


@router.get("/distribucion-por-tipo")
async def get_distribucion_por_tipo(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la distribución de llamadas separada por tipo (entrantes vs salientes)"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_por_tipo(filters)


@router.get("/evolucion-hora")
async def get_evolucion_hora(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la evolución de llamadas por hora"""
    service = CallAnalyticsService(db)
    return service.get_evolucion_por_hora(filters)


@router.get("/nivel-servicio")
async def get_nivel_servicio(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene el nivel de servicio detallado"""
    service = CallAnalyticsService(db)
    return service.get_nivel_servicio_detallado(filters)


@router.get("/causas-no-atencion")
async def get_causas_no_atencion(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene las causas de llamadas no atendidas"""
    service = CallAnalyticsService(db)
    return service.get_causas_no_atencion(filters)


@router.get("/llamadas-atendidas")
async def get_llamadas_atendidas(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Registros por página"),
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene lista detallada de llamadas ATENDIDAS (COMPLETEAGENT, COMPLETEOUTNUM)"""
    service = CallAnalyticsService(db)
    return service.get_llamadas_detalladas(filters, page, per_page)


@router.get("/llamadas-abandonadas")
async def get_llamadas_abandonadas(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Registros por página"),
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene lista detallada de llamadas ABANDONADAS (ABANDON, ABANDON-CTOUT, ABANDONWEL)"""
    service = CallAnalyticsService(db)
    return service.get_llamadas_abandonadas(filters, page, per_page)


@router.get("/llamadas-detalladas")
async def get_llamadas_detalladas(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Registros por página"),
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene lista detallada de llamadas atendidas (alias para compatibilidad)"""
    service = CallAnalyticsService(db)
    return service.get_llamadas_detalladas(filters, page, per_page)


@router.get("/nivel-atencion-campanas")
async def get_nivel_atencion_campanas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Nivel de atención por campaña con alertas (Power BI)"""
    service = CallAnalyticsService(db)
    return service.get_nivel_atencion_por_campana(filters)


@router.get("/distribucion-horaria-detallada")
async def get_dist_horaria_detallada(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución horaria: entrantes, salientes, abandonadas"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_horaria_detallada(filters)


@router.get("/distribucion-campanas")
async def get_distribucion_campanas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene distribución de llamadas por campaña"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_por_campana(filters)


@router.get("/evolucion-semanal")
async def get_evolucion_semanal(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene evolución semanal con contestadas, abandonadas y agentes activos"""
    service = CallAnalyticsService(db)
    return service.get_evolucion_semanal(filters)


@router.get("/agentes/rendimiento")
async def get_rendimiento_agentes(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene el rendimiento de agentes"""
    service = AgentAnalyticsService(db)
    return service.get_rendimiento_agentes(filters)



@router.get("/agentes/disponibilidad")
async def get_disponibilidad_agentes(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene reporte detallado de disponibilidad de agentes"""
    service = AgentAnalyticsService(db)
    return service.get_disponibilidad_agentes(filters)


@router.get("/agentes/ocupacion")
async def get_ocupacion_agentes(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la ocupación de agentes"""
    service = AgentAnalyticsService(db)
    return service.get_ocupacion_agentes(filters)


@router.get("/agentes/{agente_id}/timeline")
async def get_timeline_agente(
    agente_id: int,
    filters: dict = Depends(parse_filters_no_agente),
    db: Session = Depends(get_db)
):
    """Obtiene el timeline de actividad de un agente"""
    service = AgentAnalyticsService(db)
    return service.get_timeline_agente(agente_id, filters)


@router.get("/pausas/distribucion")
async def get_distribucion_pausas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la distribución de pausas"""
    service = AgentAnalyticsService(db)
    return service.get_distribucion_pausas(filters)


@router.get("/campanas")
async def get_campanas(db: Session = Depends(get_db)):
    """Obtiene lista de campañas (cached)"""
    current_time = time.time()
    
    # Check cache
    if (_campanas_cache['data'] is not None and 
        current_time - _campanas_cache['timestamp'] < CACHE_TTL):
        return _campanas_cache['data']
    
    # Query database (sin filtro oculto para evitar full table scan)
    campanas = db.query(Campana).order_by(Campana.nombre).all()
    
    result = [{
        'id': c.id,
        'nombre': c.nombre,
        'tipo': c.type,
        'estado': c.estado
    } for c in campanas]
    
    # Update cache
    _campanas_cache['data'] = result
    _campanas_cache['timestamp'] = current_time
    
    return result


@router.get("/agentes")
async def get_agentes(db: Session = Depends(get_db)):
    """Obtiene lista de agentes (cached)"""
    current_time = time.time()
    
    # Check cache
    if (_agentes_cache['data'] is not None and 
        current_time - _agentes_cache['timestamp'] < CACHE_TTL):
        return _agentes_cache['data']
    
    # Query database (sin filtro borrado para evitar full table scan)
    agentes = db.query(
        AgenteProfile.id,
        User.first_name,
        User.last_name,
        AgenteProfile.estado
    ).join(
        User, AgenteProfile.user_id == User.id
    ).order_by(User.first_name, User.last_name).all()
    
    result = [{
        'id': a.id,
        'nombre': f'{a.first_name} {a.last_name}',
        'estado': a.estado
    } for a in agentes]
    
    # Update cache
    _agentes_cache['data'] = result
    _agentes_cache['timestamp'] = current_time
    
    return result



# ==================== NUEVOS ENDPOINTS PREMIUM ====================

# Importar servicio extendido
from ..services.call_analytics_extended import CallAnalyticsExtended


@router.get("/distribucion-por-campana-detalle")
async def get_distribucion_por_campana_detalle(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución de llamadas por campaña (Pie Chart)"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_distribucion_por_campana(filters)


@router.get("/distribucion-por-dia-semana")
async def get_distribucion_por_dia_semana(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución de llamadas por día de la semana"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_distribucion_por_dia_semana(filters)


@router.get("/distribucion-por-mes")
async def get_distribucion_por_mes(
    anio: int = Query(None, description="Año para filtrar"),
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución de llamadas por mes"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_distribucion_por_mes(anio, filters)


@router.get("/distribucion-por-rango-horario")
async def get_distribucion_por_rango_horario(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución de llamadas por rangos horarios"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_distribucion_por_rango_horario(filters)


@router.get("/salientes/dashboard")
async def get_salientes_dashboard(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Dashboard completo de llamadas salientes"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_llamadas_salientes_dashboard(filters)


@router.get("/salientes/manuales-vs-dialer")
async def get_manuales_vs_dialer(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Comparativa llamadas manuales vs dialer"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_llamadas_manuales_vs_dialer(filters)


@router.get("/causas-desconexion-detalladas")
async def get_causas_desconexion_detalladas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Causas de desconexión detalladas (incluye transferencias)"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_causas_desconexion_detalladas(filters)


@router.get("/causas-no-conexion-completas")
async def get_causas_no_conexion_completas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Causas de no conexión completas"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_causas_no_conexion_completas(filters)


@router.get("/sin-conexion-por-agente")
async def get_sin_conexion_por_agente(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Llamadas sin conexión desglosadas por agente"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_sin_conexion_por_agente(filters)


@router.get("/sin-conexion-por-campana")
async def get_sin_conexion_por_campana(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Llamadas sin conexión desglosadas por campaña"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_sin_conexion_por_campana(filters)


@router.get("/agentes/total-sesiones")
async def get_total_sesiones(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Resumen de sesiones de todos los agentes"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_total_sesiones_agentes(filters)


@router.get("/agentes/disponibilidad-heatmap")
async def get_disponibilidad_heatmap(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Número de agentes por día/hora (heatmap)"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_agentes_por_dia_hora(filters)


@router.get("/agentes/disponibilidad-ampliada")
async def get_disponibilidad_ampliada(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Disponibilidad de agentes con métricas ampliadas"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_disponibilidad_agentes_ampliada(filters)


@router.get("/transferencias")
async def get_analisis_transferencias(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Análisis completo de transferencias"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_analisis_transferencias(filters)


@router.get("/nivel-servicio-detallado")
async def get_nivel_servicio_detallado(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Nivel de servicio con bloques configurables"""
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_nivel_servicio_detallado(filters)



@router.get("/tabla-distribucion-horaria")
async def get_tabla_distribucion_horaria(
    agrupar_por: str = 'hora',
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """
    Tabla de distribución horaria con métricas completas
    Parámetros:
        - agrupar_por: 'hora', 'mes', 'dia_semana', 'campana'
    """
    service_ext = CallAnalyticsExtended(db)
    return service_ext.get_distribucion_horaria_detallada(filters, agrupar_por)


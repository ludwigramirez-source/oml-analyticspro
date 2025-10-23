"""
Rutas de la API para Analytics
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, date

from ..database import get_db
from ..services.call_analytics import CallAnalyticsService
from ..services.agent_analytics import AgentAnalyticsService
from ..models.omnileads_models import Campana, AgenteProfile, User

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


def parse_filters(
    fecha_inicio: Optional[date] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    campana_id: Optional[int] = Query(None, description="ID de campaña"),
    tipo_campana: Optional[int] = Query(None, description="Tipo de campaña"),
    agente_id: Optional[int] = Query(None, description="ID de agente")
) -> dict:
    """Parse y retorna los filtros comunes"""
    filters = {}
    if fecha_inicio:
        filters['fecha_inicio'] = datetime.combine(fecha_inicio, datetime.min.time())
    if fecha_fin:
        filters['fecha_fin'] = datetime.combine(fecha_fin, datetime.min.time())
    if campana_id:
        filters['campana_id'] = campana_id
    if tipo_campana:
        filters['tipo_campana'] = tipo_campana
    if agente_id:
        filters['agente_id'] = agente_id
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


@router.get("/distribucion-llamadas")
async def get_distribucion_llamadas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene la distribución de llamadas por estado"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_llamadas(filters)


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


@router.get("/llamadas-detalladas")
async def get_llamadas_detalladas(
    page: int = Query(1, ge=1, description="Número de página"),
    per_page: int = Query(50, ge=1, le=200, description="Registros por página"),
    solo_atendidas: bool = Query(False, description="Solo llamadas atendidas"),
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene lista detallada de llamadas con paginación"""
    filters['solo_atendidas'] = solo_atendidas
    service = CallAnalyticsService(db)
    return service.get_llamadas_detalladas(filters, page, per_page)


@router.get("/distribucion-campanas")
async def get_distribucion_campanas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene distribución de llamadas por campaña"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_por_campana(filters)


@router.get("/agentes/rendimiento")
async def get_rendimiento_agentes(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Obtiene el rendimiento de agentes"""
    service = AgentAnalyticsService(db)
    return service.get_rendimiento_agentes(filters)


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
    filters: dict = Depends(parse_filters),
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
    """Obtiene lista de campañas"""
    campanas = db.query(Campana).filter(
        Campana.oculto == False
    ).order_by(Campana.nombre).all()
    
    return [{
        'id': c.id,
        'nombre': c.nombre,
        'tipo': c.type,
        'estado': c.estado
    } for c in campanas]


@router.get("/agentes")
async def get_agentes(db: Session = Depends(get_db)):
    """Obtiene lista de agentes"""
    agentes = db.query(
        AgenteProfile.id,
        User.first_name,
        User.last_name,
        AgenteProfile.estado
    ).join(
        User, AgenteProfile.user_id == User.id
    ).filter(
        AgenteProfile.borrado == False
    ).order_by(User.first_name, User.last_name).all()
    
    return [{
        'id': a.id,
        'nombre': f'{a.first_name} {a.last_name}',
        'estado': a.estado
    } for a in agentes]

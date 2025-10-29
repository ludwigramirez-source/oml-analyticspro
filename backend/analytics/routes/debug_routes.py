"""
Endpoints temporales para debugging
"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.omnileads_models import LlamadaLog

router = APIRouter(prefix="/api/debug", tags=["Debug"])


@router.get("/db-values")
async def check_db_values(db: Session = Depends(get_db)):
    """Endpoint temporal para verificar valores reales en la BD"""

    results = {}

    # 1. Valores de tipo_llamada
    tipo_llamada_query = db.query(
        LlamadaLog.tipo_llamada,
        func.count(LlamadaLog.id).label('total')
    ).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).group_by(LlamadaLog.tipo_llamada).all()

    results['tipo_llamada'] = [
        {'valor': r.tipo_llamada, 'total': r.total}
        for r in tipo_llamada_query
    ]

    # 2. Valores de tipo_campana
    tipo_campana_query = db.query(
        LlamadaLog.tipo_campana,
        func.count(LlamadaLog.id).label('total')
    ).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).group_by(LlamadaLog.tipo_campana).all()

    results['tipo_campana'] = [
        {'valor': r.tipo_campana, 'total': r.total}
        for r in tipo_campana_query
    ]

    # 3. Eventos más comunes
    eventos_query = db.query(
        LlamadaLog.event,
        func.count(LlamadaLog.id).label('total')
    ).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).group_by(LlamadaLog.event).order_by(func.count(LlamadaLog.id).desc()).limit(20).all()

    results['eventos'] = [
        {'evento': r.event, 'total': r.total}
        for r in eventos_query
    ]

    # 4. Combinaciones tipo_llamada + tipo_campana
    combo_query = db.query(
        LlamadaLog.tipo_llamada,
        LlamadaLog.tipo_campana,
        func.count(LlamadaLog.id).label('total')
    ).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).group_by(LlamadaLog.tipo_llamada, LlamadaLog.tipo_campana).order_by(func.count(LlamadaLog.id).desc()).all()

    results['combinaciones'] = [
        {
            'tipo_llamada': r.tipo_llamada,
            'tipo_campana': r.tipo_campana,
            'total': r.total
        }
        for r in combo_query
    ]

    # 5. Total
    total = db.query(func.count(LlamadaLog.id)).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).scalar()

    results['total_octubre'] = total

    # 6. Ejemplos
    ejemplos = db.query(LlamadaLog).filter(
        LlamadaLog.time >= '2024-10-01',
        LlamadaLog.time < '2024-11-01'
    ).limit(10).all()

    results['ejemplos'] = [
        {
            'callid': e.callid,
            'tipo_llamada': e.tipo_llamada,
            'tipo_campana': e.tipo_campana,
            'event': e.event,
            'duracion': e.duracion_llamada
        }
        for e in ejemplos
    ]

    return results

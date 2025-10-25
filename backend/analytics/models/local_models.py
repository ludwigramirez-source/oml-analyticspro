"""
Modelos MongoDB para caché local de datos de OmniLeads
Optimiza consultas al tener datos locales indexados
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class CampanaLocal(BaseModel):
    """Campañas en caché local"""
    id: int
    nombre: str
    tipo: int
    estado: int
    sincronizado_at: datetime = Field(default_factory=datetime.utcnow)


class AgenteLocal(BaseModel):
    """Agentes en caché local"""
    id: int
    username: str
    first_name: str
    last_name: str
    user_id: int
    sincronizado_at: datetime = Field(default_factory=datetime.utcnow)


class ActividadAgenteLocal(BaseModel):
    """Actividades de agentes en caché local"""
    id: int
    agente_id: int
    time: datetime
    event: str
    pausa_id: Optional[str] = None
    sincronizado_at: datetime = Field(default_factory=datetime.utcnow)


class LlamadaLocal(BaseModel):
    """Llamadas en caché local (solo las que tienen agente)"""
    id: int
    callid: str
    time: datetime
    agente_id: Optional[int] = None
    campana_id: Optional[int] = None
    event: str
    duracion_llamada: Optional[int] = None
    bridge_wait_time: Optional[int] = None
    tipo_llamada: Optional[int] = None
    sincronizado_at: datetime = Field(default_factory=datetime.utcnow)


class PausaLocal(BaseModel):
    """Tipos de pausa en caché local"""
    id: int
    nombre: str
    tipo: str  # 'R' = Recreativa, 'P' = Productiva
    sincronizado_at: datetime = Field(default_factory=datetime.utcnow)

"""
Modelos para la configuración de la aplicación
Almacena configuraciones de conexión a bases de datos
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class DatabaseConfig(BaseModel):
    """Configuración de conexión a PostgreSQL OmniLeads"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str  # Se encriptará antes de guardar
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
    connection_test_success: bool = False
    connection_test_message: Optional[str] = None


class DatabaseConfigCreate(BaseModel):
    """Schema para crear una nueva configuración"""
    db_host: str
    db_port: int = 5432
    db_name: str
    db_user: str
    db_password: str


class DatabaseConfigUpdate(BaseModel):
    """Schema para actualizar configuración existente"""
    db_host: Optional[str] = None
    db_port: Optional[int] = None
    db_name: Optional[str] = None
    db_user: Optional[str] = None
    db_password: Optional[str] = None


class DatabaseConfigResponse(BaseModel):
    """Schema para respuesta (oculta password)"""
    id: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    connection_test_success: bool
    connection_test_message: Optional[str] = None


class ConnectionTestResult(BaseModel):
    """Resultado de prueba de conexión"""
    success: bool
    message: str
    details: Optional[dict] = None

"""
Endpoints para gestión de configuraciones
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from motor.motor_asyncio import AsyncIOMotorDatabase

from analytics.models.config_models import (
    ConnectionTestResult,
    DatabaseConfigCreate,
    DatabaseConfigResponse,
    DatabaseConfigUpdate,
)
from analytics.services.config_service import ConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["Configuration"])


# Dependency para obtener MongoDB
async def get_mongo_db():
    """Obtiene la instancia de MongoDB desde el app state"""
    from server import db
    return db


@router.post("/test-connection", response_model=ConnectionTestResult)
async def test_database_connection(
    config: DatabaseConfigCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Prueba la conexión a la base de datos PostgreSQL
    sin guardar la configuración
    """
    try:
        service = ConfigService(db)
        result = await service.test_connection(config)
        return result
    except Exception as e:
        logger.error(f"Error testing connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=DatabaseConfigResponse)
async def create_database_config(
    config: DatabaseConfigCreate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Crea una nueva configuración de base de datos.
    Prueba la conexión antes de guardar.
    Desactiva automáticamente otras configuraciones.
    """
    try:
        service = ConfigService(db)
        created_config = await service.create_config(config)

        # Devolver sin password
        return DatabaseConfigResponse(
            id=created_config.id,
            db_host=created_config.db_host,
            db_port=created_config.db_port,
            db_name=created_config.db_name,
            db_user=created_config.db_user,
            created_at=created_config.created_at,
            updated_at=created_config.updated_at,
            is_active=created_config.is_active,
            connection_test_success=created_config.connection_test_success,
            connection_test_message=created_config.connection_test_message
        )
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/active", response_model=DatabaseConfigResponse)
async def get_active_config(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Obtiene la configuración activa actual
    """
    try:
        service = ConfigService(db)
        config = await service.get_active_config()

        if not config:
            raise HTTPException(status_code=404, detail="No hay configuración activa")

        return DatabaseConfigResponse(
            id=config.id,
            db_host=config.db_host,
            db_port=config.db_port,
            db_name=config.db_name,
            db_user=config.db_user,
            created_at=config.created_at,
            updated_at=config.updated_at,
            is_active=config.is_active,
            connection_test_success=config.connection_test_success,
            connection_test_message=config.connection_test_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting active config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[DatabaseConfigResponse])
async def get_all_configs(
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Obtiene todas las configuraciones guardadas (sin passwords)
    """
    try:
        service = ConfigService(db)
        configs = await service.get_all_configs()
        return configs
    except Exception as e:
        logger.error(f"Error getting configs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{config_id}", response_model=DatabaseConfigResponse)
async def update_config(
    config_id: str,
    update_data: DatabaseConfigUpdate,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Actualiza una configuración existente
    """
    try:
        service = ConfigService(db)
        updated = await service.update_config(config_id, update_data)

        if not updated:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")

        return DatabaseConfigResponse(
            id=updated.id,
            db_host=updated.db_host,
            db_port=updated.db_port,
            db_name=updated.db_name,
            db_user=updated.db_user,
            created_at=updated.created_at,
            updated_at=updated.updated_at,
            is_active=updated.is_active,
            connection_test_success=updated.connection_test_success,
            connection_test_message=updated.connection_test_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Elimina una configuración
    """
    try:
        service = ConfigService(db)
        deleted = await service.delete_config(config_id)

        if not deleted:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")

        return {"message": "Configuración eliminada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{config_id}/activate")
async def activate_config(
    config_id: str,
    db: AsyncIOMotorDatabase = Depends(get_mongo_db)
):
    """
    Activa una configuración específica
    """
    try:
        service = ConfigService(db)
        activated = await service.activate_config(config_id)

        if not activated:
            raise HTTPException(status_code=404, detail="Configuración no encontrada")

        return {"message": "Configuración activada exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error activating config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

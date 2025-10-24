"""
Servicio para gestionar configuraciones de base de datos
"""
import logging
from typing import Optional, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
import base64

from analytics.models.config_models import (
    DatabaseConfig,
    DatabaseConfigCreate,
    DatabaseConfigUpdate,
    ConnectionTestResult
)

logger = logging.getLogger(__name__)


class ConfigService:
    """Servicio para gestionar configuraciones"""
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self.db = mongo_db
        self.collection = self.db.database_configs
    
    def _encrypt_password(self, password: str) -> str:
        """Encripta la contraseña usando base64 (simple encoding)"""
        # Nota: Para producción, usar una librería de encriptación real como cryptography
        return base64.b64encode(password.encode()).decode()
    
    def _decrypt_password(self, encrypted: str) -> str:
        """Desencripta la contraseña"""
        return base64.b64decode(encrypted.encode()).decode()
    
    async def test_connection(self, config: DatabaseConfigCreate) -> ConnectionTestResult:
        """Prueba la conexión a la base de datos PostgreSQL"""
        try:
            # Construir URL de conexión
            db_url = f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"
            
            # Intentar crear engine y conectar
            engine = create_engine(db_url, pool_pre_ping=True)
            
            with engine.connect() as connection:
                # Ejecutar query simple para verificar conexión
                result = connection.execute(text("SELECT version()"))
                version = result.fetchone()[0]
                
                logger.info(f"✅ Conexión exitosa a PostgreSQL: {version}")
                
                return ConnectionTestResult(
                    success=True,
                    message="Conexión exitosa",
                    details={"version": version[:100]}  # Limitar longitud
                )
        
        except OperationalError as e:
            error_msg = str(e.orig) if hasattr(e, 'orig') else str(e)
            logger.error(f"❌ Error de conexión: {error_msg}")
            return ConnectionTestResult(
                success=False,
                message=f"Error de conexión: {error_msg}",
                details=None
            )
        
        except Exception as e:
            logger.error(f"❌ Error inesperado: {str(e)}")
            return ConnectionTestResult(
                success=False,
                message=f"Error inesperado: {str(e)}",
                details=None
            )
    
    async def create_config(self, config_data: DatabaseConfigCreate) -> DatabaseConfig:
        """Crea una nueva configuración"""
        
        # Primero probar la conexión
        test_result = await self.test_connection(config_data)
        
        # Crear configuración
        config = DatabaseConfig(
            **config_data.model_dump(),
            connection_test_success=test_result.success,
            connection_test_message=test_result.message
        )
        
        # Encriptar password antes de guardar
        config_dict = config.model_dump()
        config_dict['db_password'] = self._encrypt_password(config_dict['db_password'])
        
        # Serializar datetime a ISO string
        config_dict['created_at'] = config_dict['created_at'].isoformat()
        config_dict['updated_at'] = config_dict['updated_at'].isoformat()
        
        # Desactivar todas las configuraciones previas
        await self.collection.update_many(
            {'is_active': True},
            {'$set': {'is_active': False}}
        )
        
        # Guardar en MongoDB
        await self.collection.insert_one(config_dict)
        
        # Si la conexión fue exitosa, actualizar la conexión global
        if test_result.success:
            try:
                from analytics.database import update_database_connection
                connection_string = self.get_connection_string(config)
                update_database_connection(connection_string)
                logger.info("✅ Conexión global actualizada")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo actualizar conexión global: {e}")
        
        logger.info(f"✅ Configuración guardada: {config.db_host}:{config.db_port}/{config.db_name}")
        
        return config
    
    async def get_active_config(self) -> Optional[DatabaseConfig]:
        """Obtiene la configuración activa"""
        doc = await self.collection.find_one({'is_active': True})
        
        if not doc:
            return None
        
        # Convertir ISO strings a datetime
        if isinstance(doc.get('created_at'), str):
            doc['created_at'] = datetime.fromisoformat(doc['created_at'])
        if isinstance(doc.get('updated_at'), str):
            doc['updated_at'] = datetime.fromisoformat(doc['updated_at'])
        
        # Desencriptar password
        if 'db_password' in doc:
            doc['db_password'] = self._decrypt_password(doc['db_password'])
        
        return DatabaseConfig(**doc)
    
    async def get_all_configs(self) -> list:
        """Obtiene todas las configuraciones (sin passwords)"""
        configs = await self.collection.find({}, {"_id": 0, "db_password": 0}).to_list(100)
        
        # Convertir ISO strings a datetime
        for config in configs:
            if isinstance(config.get('created_at'), str):
                config['created_at'] = datetime.fromisoformat(config['created_at'])
            if isinstance(config.get('updated_at'), str):
                config['updated_at'] = datetime.fromisoformat(config['updated_at'])
        
        return configs
    
    async def update_config(self, config_id: str, update_data: DatabaseConfigUpdate) -> Optional[DatabaseConfig]:
        """Actualiza una configuración existente"""
        
        # Obtener configuración actual
        current = await self.collection.find_one({'id': config_id})
        if not current:
            return None
        
        # Preparar datos de actualización
        update_dict = update_data.model_dump(exclude_unset=True)
        
        # Encriptar password si se proporciona
        if 'db_password' in update_dict and update_dict['db_password']:
            update_dict['db_password'] = self._encrypt_password(update_dict['db_password'])
        
        update_dict['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        # Actualizar en MongoDB
        await self.collection.update_one(
            {'id': config_id},
            {'$set': update_dict}
        )
        
        # Obtener configuración actualizada
        updated = await self.get_active_config()
        
        logger.info(f"✅ Configuración actualizada: {config_id}")
        
        return updated
    
    async def delete_config(self, config_id: str) -> bool:
        """Elimina una configuración"""
        result = await self.collection.delete_one({'id': config_id})
        
        if result.deleted_count > 0:
            logger.info(f"✅ Configuración eliminada: {config_id}")
            return True
        
        return False
    
    async def activate_config(self, config_id: str) -> bool:
        """Activa una configuración específica y actualiza la conexión"""
        # Desactivar todas
        await self.collection.update_many(
            {'is_active': True},
            {'$set': {'is_active': False}}
        )
        
        # Activar la seleccionada
        result = await self.collection.update_one(
            {'id': config_id},
            {'$set': {'is_active': True, 'updated_at': datetime.now(timezone.utc).isoformat()}}
        )
        
        if result.modified_count > 0:
            logger.info(f"✅ Configuración activada: {config_id}")
            
            # Actualizar la conexión global
            try:
                config = await self.get_active_config()
                if config:
                    from analytics.database import update_database_connection
                    connection_string = self.get_connection_string(config)
                    update_database_connection(connection_string)
                    logger.info(f"✅ Conexión global actualizada a: {config.db_host}:{config.db_port}/{config.db_name}")
            except Exception as e:
                logger.error(f"❌ Error actualizando conexión global: {e}")
            
            return True
        
        return False
    
    def get_connection_string(self, config: DatabaseConfig) -> str:
        """Genera la cadena de conexión PostgreSQL"""
        return f"postgresql://{config.db_user}:{config.db_password}@{config.db_host}:{config.db_port}/{config.db_name}"

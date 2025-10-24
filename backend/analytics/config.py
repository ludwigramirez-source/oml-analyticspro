"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import os
import asyncio
from dotenv import load_dotenv
from pathlib import Path
import logging

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)


class OmniLeadsConfig:
    """Configuración de conexión a PostgreSQL OmniLeads"""
    
    # Configuración de PostgreSQL OmniLeads (READ-ONLY) - Fallback desde .env
    OMNILEADS_DB_HOST = os.getenv('OMNILEADS_DB_HOST', 'localhost')
    OMNILEADS_DB_PORT = os.getenv('OMNILEADS_DB_PORT', '5432')
    OMNILEADS_DB_NAME = os.getenv('OMNILEADS_DB_NAME', 'omnileads')
    OMNILEADS_DB_USER = os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly')
    OMNILEADS_DB_PASSWORD = os.getenv('OMNILEADS_DB_PASSWORD', '')
    
    @classmethod
    def get_active_config_from_mongo(cls):
        """Obtiene la configuración activa desde MongoDB"""
        try:
            # Import here to avoid circular imports
            from motor.motor_asyncio import AsyncIOMotorClient
            import base64
            
            # Get MongoDB connection from server
            mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
            client = AsyncIOMotorClient(mongo_url)
            db = client[os.environ.get('DB_NAME', 'test_database')]
            
            # Try to get active config synchronously
            import asyncio
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If we're in an async context, we can't run async code
                return None
            
            async def get_config():
                doc = await db.database_configs.find_one({'is_active': True})
                client.close()
                return doc
            
            doc = loop.run_until_complete(get_config())
            
            if doc:
                # Decrypt password
                password = base64.b64decode(doc['db_password'].encode()).decode()
                logger.info(f"✅ Using active MongoDB config: {doc['db_host']}:{doc['db_port']}/{doc['db_name']}")
                return {
                    'host': doc['db_host'],
                    'port': doc['db_port'],
                    'name': doc['db_name'],
                    'user': doc['db_user'],
                    'password': password
                }
        except Exception as e:
            logger.warning(f"⚠️ Could not get active config from MongoDB: {e}")
        
        return None
    
    @classmethod
    def get_database_url(cls) -> str:
        """Retorna la URL de conexión a PostgreSQL"""
        # Try to get active config from MongoDB first
        active_config = cls.get_active_config_from_mongo()
        
        if active_config:
            return (
                f"postgresql://{active_config['user']}:{active_config['password']}"
                f"@{active_config['host']}:{active_config['port']}/{active_config['name']}"
            )
        
        # Fallback to environment variables
        logger.info("📋 Using fallback config from environment variables")
        return (
            f"postgresql://{cls.OMNILEADS_DB_USER}:{cls.OMNILEADS_DB_PASSWORD}"
            f"@{cls.OMNILEADS_DB_HOST}:{cls.OMNILEADS_DB_PORT}/{cls.OMNILEADS_DB_NAME}"
        )
    
    @classmethod
    def get_connection_params(cls) -> dict:
        """Retorna los parámetros de conexión como diccionario"""
        # Try to get active config from MongoDB first
        active_config = cls.get_active_config_from_mongo()
        
        if active_config:
            return {
                'host': active_config['host'],
                'port': active_config['port'],
                'database': active_config['name'],
                'user': active_config['user'],
                'password': active_config['password'],
                'options': '-c default_transaction_read_only=on'  # READ-ONLY
            }
        
        # Fallback to environment variables
        return {
            'host': cls.OMNILEADS_DB_HOST,
            'port': cls.OMNILEADS_DB_PORT,
            'database': cls.OMNILEADS_DB_NAME,
            'user': cls.OMNILEADS_DB_USER,
            'password': cls.OMNILEADS_DB_PASSWORD,
            'options': '-c default_transaction_read_only=on'  # READ-ONLY
        }


# Instancia de configuración
config = OmniLeadsConfig()

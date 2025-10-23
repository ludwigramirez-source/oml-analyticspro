"""
Gestión de conexión a base de datos PostgreSQL OmniLeads
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import config
import logging

logger = logging.getLogger(__name__)

# URL de conexión a PostgreSQL (inicialmente desde env)
DATABASE_URL = config.get_database_url()

# Crear engine con configuración READ-ONLY
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,  # Cambiar a True para debug SQL
    connect_args={
        "options": "-c default_transaction_read_only=on"
    }
)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para modelos
Base = declarative_base()


def update_database_connection(db_url: str):
    """
    Actualiza la conexión a la base de datos con una nueva URL
    Se llama cuando se guarda una nueva configuración desde el frontend
    """
    global engine, SessionLocal
    
    try:
        # Cerrar engine anterior
        engine.dispose()
        
        # Crear nuevo engine
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            connect_args={
                "options": "-c default_transaction_read_only=on"
            }
        )
        
        # Crear nueva sesión
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        logger.info("✅ Conexión a base de datos actualizada exitosamente")
        return True
    
    except Exception as e:
        logger.error(f"❌ Error actualizando conexión: {e}")
        return False


def get_db():
    """Dependency para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""
Gestión de conexión a base de datos PostgreSQL OmniLeads
"""
import logging

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import config

logger = logging.getLogger(__name__)

# Base para modelos
Base = declarative_base()

# Variables globales para engine y session
engine = None
SessionLocal = None

def _initialize_engine():
    """Inicializa el engine de base de datos de forma lazy"""
    global engine, SessionLocal

    if engine is not None:
        return engine

    try:
        # URL de conexión a PostgreSQL (inicialmente desde env)
        DATABASE_URL = config.get_database_url()

        # Crear engine con configuración READ-ONLY y timeout
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,  # Cambiar a True para debug SQL
            connect_args={
                "options": "-c default_transaction_read_only=on -c statement_timeout=30000"  # 30 segundos timeout
            }
        )

        # Crear sesión
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        logger.info("Database engine initialized successfully")
        return engine

    except Exception as e:
        logger.error(f"Error initializing database engine: {e}")
        raise


def update_database_connection(db_url: str):
    """
    Actualiza la conexión a la base de datos con una nueva URL
    Se llama cuando se guarda una nueva configuración desde el frontend
    """
    global engine, SessionLocal

    try:
        # Cerrar engine anterior si existe
        if engine:
            engine.dispose()

        # Crear nuevo engine con timeout
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False,
            connect_args={
                "options": "-c default_transaction_read_only=on -c statement_timeout=30000"  # 30 segundos timeout
            }
        )

        # Crear nueva sesión
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        logger.info("Database connection updated successfully")
        return True

    except Exception as e:
        logger.error(f"Error updating database connection: {e}")
        return False


def get_db():
    """Dependency para obtener sesión de base de datos"""
    global engine, SessionLocal

    # Inicializar engine si no está inicializado
    if engine is None:
        _initialize_engine()

    if SessionLocal is None:
        raise Exception("Database connection not configured")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

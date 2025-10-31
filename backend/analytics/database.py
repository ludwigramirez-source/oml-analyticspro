"""
Gestión de conexión a base de datos PostgreSQL OmniLeads
Conexión configurada mediante variables de entorno (.env)
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
        # URL de conexión a PostgreSQL desde variables de entorno
        database_url = config.get_database_url()

        logger.info(f"Conectando a PostgreSQL: {config.OMNILEADS_DB_HOST}:{config.OMNILEADS_DB_PORT}/{config.OMNILEADS_DB_NAME}")

        # Crear engine con configuración READ-ONLY, timeout y pool optimizado
        engine = create_engine(
            database_url,
            # OPTIMIZACIÓN: Pool de conexiones configurado para mejor concurrencia
            pool_size=20,          # Conexiones permanentes (default: 5)
            max_overflow=40,       # Conexiones adicionales (default: 10)
            pool_timeout=30,       # Timeout para obtener conexión del pool
            pool_pre_ping=True,    # Verificar conexión antes de usar
            pool_recycle=3600,     # Reciclar conexiones cada hora
            echo=False,            # Cambiar a True para debug SQL
            connect_args={
                "options": "-c default_transaction_read_only=on -c statement_timeout=30000",  # 30 segundos timeout
                "connect_timeout": 10  # Timeout de conexión inicial
            }
        )

        # Crear sesión
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

        logger.info("✅ Engine de base de datos inicializado correctamente")
        return engine

    except Exception as e:
        logger.error(f"❌ Error inicializando engine: {e}")
        logger.error("Verifica las variables de entorno: OMNILEADS_DB_HOST, OMNILEADS_DB_PORT, OMNILEADS_DB_NAME, OMNILEADS_DB_USER, OMNILEADS_DB_PASSWORD")
        raise


def get_db():
    """Dependency para obtener sesión de base de datos"""
    global engine, SessionLocal

    # Inicializar engine si no está inicializado
    if engine is None:
        _initialize_engine()

    if SessionLocal is None:
        raise Exception("Database connection not configured. Check .env file.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

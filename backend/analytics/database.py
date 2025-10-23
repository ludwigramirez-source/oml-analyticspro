"""
Gestión de conexión a base de datos PostgreSQL OmniLeads
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import config

# URL de conexión a PostgreSQL
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


def get_db():
    """Dependency para obtener sesión de base de datos"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

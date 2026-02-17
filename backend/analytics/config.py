"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import logging
import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)


class OmniLeadsConfig:
    """Configuración de conexión a PostgreSQL OmniLeads"""

    # Configuración de PostgreSQL OmniLeads (READ-ONLY)
    OMNILEADS_DB_HOST = os.getenv('OMNILEADS_DB_HOST', 'localhost')
    OMNILEADS_DB_PORT = os.getenv('OMNILEADS_DB_PORT', '5432')
    OMNILEADS_DB_NAME = os.getenv('OMNILEADS_DB_NAME', 'omnileads')
    OMNILEADS_DB_USER = os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly')
    OMNILEADS_DB_PASSWORD = os.getenv('OMNILEADS_DB_PASSWORD', '')

    # Timezone Configuration (default GMT-6 for Central America)
    TIMEZONE_OFFSET = int(os.getenv('TIMEZONE_OFFSET', '-6'))
    # Nombre IANA del timezone local (para PostgreSQL AT TIME ZONE)
    # Se puede sobreescribir con TIMEZONE_NAME en .env
    TIMEZONE_NAME = os.getenv(
        'TIMEZONE_NAME', 'America/Managua'
    )

    @classmethod
    def get_database_url(cls) -> str:
        """Retorna la URL de conexión a PostgreSQL"""
        return (
            f"postgresql://{cls.OMNILEADS_DB_USER}:{cls.OMNILEADS_DB_PASSWORD}"
            f"@{cls.OMNILEADS_DB_HOST}:{cls.OMNILEADS_DB_PORT}/{cls.OMNILEADS_DB_NAME}"
        )

    @classmethod
    def get_connection_params(cls) -> dict:
        """Retorna los parámetros de conexión como diccionario"""
        return {
            'host': cls.OMNILEADS_DB_HOST,
            'port': cls.OMNILEADS_DB_PORT,
            'database': cls.OMNILEADS_DB_NAME,
            'user': cls.OMNILEADS_DB_USER,
            'password': cls.OMNILEADS_DB_PASSWORD,
            'options': '-c default_transaction_read_only=on'  # READ-ONLY
        }

    @classmethod
    def get_timezone(cls):
        """Retorna el timezone configurado basado en TIMEZONE_OFFSET"""
        return timezone(timedelta(hours=cls.TIMEZONE_OFFSET))


# Instancia de configuración
config = OmniLeadsConfig()

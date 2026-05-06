"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import logging
import os
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

    # Timezone de la BD de OmniLeads (como está configurado en sus envars)
    # Se usa para extraer la hora "tal cual" del timestamp,
    # ya que el reloj del servidor tiene la hora local correcta
    # pero OmniLeads graba el offset de este timezone.
    TIMEZONE_DB = os.getenv('TIMEZONE_DB', 'America/Bogota')

    # ── BD Local (replica sincronizada) ──────────────────────────
    USE_LOCAL_DB = os.getenv('USE_LOCAL_DB', 'false').lower() == 'true'
    LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST', 'postgres-local')
    LOCAL_DB_PORT = os.getenv('LOCAL_DB_PORT', '5432')
    LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME', 'omnileads_local')
    LOCAL_DB_USER = os.getenv('LOCAL_DB_USER', 'analytics')
    LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD', 'analytics_password')

    @classmethod
    def get_database_url(cls) -> str:
        """Retorna la URL de conexión a PostgreSQL (source remota)"""
        return (
            f"postgresql://{cls.OMNILEADS_DB_USER}:{cls.OMNILEADS_DB_PASSWORD}"
            f"@{cls.OMNILEADS_DB_HOST}:{cls.OMNILEADS_DB_PORT}/{cls.OMNILEADS_DB_NAME}"
        )

    @classmethod
    def get_local_database_url(cls) -> str:
        """Retorna la URL de conexión a la BD local"""
        return (
            f"postgresql://{cls.LOCAL_DB_USER}:{cls.LOCAL_DB_PASSWORD}"
            f"@{cls.LOCAL_DB_HOST}:{cls.LOCAL_DB_PORT}/{cls.LOCAL_DB_NAME}"
        )

    @classmethod
    def get_active_database_url(cls) -> str:
        """Retorna la URL de la BD activa (local o remota)"""
        if cls.USE_LOCAL_DB:
            return cls.get_local_database_url()
        return cls.get_database_url()

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



# Instancia de configuración
config = OmniLeadsConfig()

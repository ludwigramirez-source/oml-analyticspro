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



# Instancia de configuración
config = OmniLeadsConfig()

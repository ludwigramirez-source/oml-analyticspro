"""
Configuracion para el servicio de sincronizacion.
Lee variables de entorno para conexion a BD source (OmniLeads) y BD local.
"""
import os
import logging
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

logger = logging.getLogger(__name__)


class SyncConfig:
    """Configuracion de sincronizacion"""

    # ── BD Source (OmniLeads remota, READ-ONLY) ──────────────────
    SOURCE_DB_HOST = os.getenv('OMNILEADS_DB_HOST', 'localhost')
    SOURCE_DB_PORT = os.getenv('OMNILEADS_DB_PORT', '5432')
    SOURCE_DB_NAME = os.getenv('OMNILEADS_DB_NAME', 'omnileads')
    SOURCE_DB_USER = os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly')
    SOURCE_DB_PASSWORD = os.getenv('OMNILEADS_DB_PASSWORD', '')

    # ── BD Local (replica) ───────────────────────────────────────
    LOCAL_DB_HOST = os.getenv('LOCAL_DB_HOST', 'postgres-local')
    LOCAL_DB_PORT = os.getenv('LOCAL_DB_PORT', '5433')
    LOCAL_DB_NAME = os.getenv('LOCAL_DB_NAME', 'omnileads_local')
    LOCAL_DB_USER = os.getenv('LOCAL_DB_USER', 'analytics')
    LOCAL_DB_PASSWORD = os.getenv('LOCAL_DB_PASSWORD', 'analytics_password')

    # ── Intervalos de sync (segundos) ────────────────────────────
    SYNC_INTERVAL_EVENT_LOGS = int(
        os.getenv('SYNC_INTERVAL_EVENT_LOGS', '300')  # 5 min
    )
    SYNC_INTERVAL_REFERENCE = int(
        os.getenv('SYNC_INTERVAL_REFERENCE', '3600')  # 1 hora
    )

    # ── Tamanos de batch ─────────────────────────────────────────
    SYNC_BATCH_SIZE = int(os.getenv('SYNC_BATCH_SIZE', '10000'))
    SYNC_INITIAL_BATCH_SIZE = int(
        os.getenv('SYNC_INITIAL_BATCH_SIZE', '50000')
    )

    @classmethod
    def get_source_dsn(cls) -> dict:
        """Parametros de conexion psycopg2 a la BD source"""
        return {
            'host': cls.SOURCE_DB_HOST,
            'port': cls.SOURCE_DB_PORT,
            'dbname': cls.SOURCE_DB_NAME,
            'user': cls.SOURCE_DB_USER,
            'password': cls.SOURCE_DB_PASSWORD,
            'options': '-c default_transaction_read_only=on',
            'connect_timeout': 15,
        }

    @classmethod
    def get_local_dsn(cls) -> dict:
        """Parametros de conexion psycopg2 a la BD local"""
        return {
            'host': cls.LOCAL_DB_HOST,
            'port': cls.LOCAL_DB_PORT,
            'dbname': cls.LOCAL_DB_NAME,
            'user': cls.LOCAL_DB_USER,
            'password': cls.LOCAL_DB_PASSWORD,
            'connect_timeout': 10,
        }

    @classmethod
    def get_local_database_url(cls) -> str:
        """URL SQLAlchemy para la BD local"""
        return (
            f"postgresql://{cls.LOCAL_DB_USER}:{cls.LOCAL_DB_PASSWORD}"
            f"@{cls.LOCAL_DB_HOST}:{cls.LOCAL_DB_PORT}/{cls.LOCAL_DB_NAME}"
        )


sync_config = SyncConfig()

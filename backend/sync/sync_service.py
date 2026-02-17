"""
Servicio daemon de sincronizacion.
Ejecuta sync inicial y luego programa syncs periodicos con APScheduler.
"""
import logging
import signal
import sys

import psycopg2
from apscheduler.schedulers.blocking import BlockingScheduler

from .config import sync_config
from .health import start_health_server
from .schema import initialize_schema
from .sync_engine import SyncEngine

# ── Configuracion de logging ─────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger('sync-service')

# Reducir ruido de APScheduler
logging.getLogger('apscheduler').setLevel(logging.WARNING)


def wait_for_local_db(max_retries=30, delay=2):
    """Espera a que la BD local este lista."""
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(**sync_config.get_local_dsn())
            conn.close()
            logger.info("BD local disponible")
            return True
        except psycopg2.OperationalError:
            logger.info(
                f"Esperando BD local... "
                f"(intento {attempt + 1}/{max_retries})"
            )
            import time
            time.sleep(delay)
    logger.error("BD local no disponible despues de reintentos")
    return False


def main():
    """Punto de entrada del servicio de sync."""

    logger.info("=" * 60)
    logger.info("OmniLeads Analytics - Sync Service")
    logger.info("=" * 60)
    logger.info(
        f"Source: {sync_config.SOURCE_DB_HOST}:"
        f"{sync_config.SOURCE_DB_PORT}/"
        f"{sync_config.SOURCE_DB_NAME}"
    )
    logger.info(
        f"Local:  {sync_config.LOCAL_DB_HOST}:"
        f"{sync_config.LOCAL_DB_PORT}/"
        f"{sync_config.LOCAL_DB_NAME}"
    )
    logger.info(
        f"Intervalos: event_logs={sync_config.SYNC_INTERVAL_EVENT_LOGS}s, "
        f"reference={sync_config.SYNC_INTERVAL_REFERENCE}s"
    )
    logger.info("=" * 60)

    # ── Esperar BD local ─────────────────────────────────────────
    if not wait_for_local_db():
        sys.exit(1)

    # ── Inicializar schema ───────────────────────────────────────
    logger.info("Inicializando schema...")
    local_conn = psycopg2.connect(**sync_config.get_local_dsn())
    try:
        initialize_schema(local_conn)
    finally:
        local_conn.close()

    # ── Health check server ────────────────────────────────────────
    start_health_server()

    # ── Sync inicial (blocking) ──────────────────────────────────
    engine = SyncEngine()
    logger.info("Ejecutando sync inicial...")
    try:
        engine.sync_all()
    except Exception as e:
        logger.error(f"Error en sync inicial: {e}")
        # No salir — programar reintentos

    # ── Configurar APScheduler ───────────────────────────────────
    scheduler = BlockingScheduler()

    # Job: Sync de event logs (llamadas + actividad agentes)
    scheduler.add_job(
        engine.sync_event_logs,
        'interval',
        seconds=sync_config.SYNC_INTERVAL_EVENT_LOGS,
        id='sync_event_logs',
        name='Sync event logs (llamadas + actividad)',
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60,
    )

    # Job: Sync de tablas de referencia
    scheduler.add_job(
        engine.sync_reference_data,
        'interval',
        seconds=sync_config.SYNC_INTERVAL_REFERENCE,
        id='sync_reference_data',
        name='Sync reference data',
        max_instances=1,
        coalesce=True,
        misfire_grace_time=120,
    )

    # ── Manejo de senales ────────────────────────────────────────
    def shutdown(signum, frame):
        logger.info(
            f"Recibida senal {signum}. Cerrando..."
        )
        scheduler.shutdown(wait=False)
        engine.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # ── Arrancar scheduler ───────────────────────────────────────
    logger.info(
        "Scheduler iniciado. "
        f"Event logs cada {sync_config.SYNC_INTERVAL_EVENT_LOGS}s, "
        f"reference cada {sync_config.SYNC_INTERVAL_REFERENCE}s"
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Sync service detenido")
        engine.close()


if __name__ == '__main__':
    main()

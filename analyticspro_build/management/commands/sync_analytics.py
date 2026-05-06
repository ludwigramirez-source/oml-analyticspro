"""
Management command para sincronizar datos de OmniLeads a omnileads_local.
Uso:
  python manage.py sync_analytics --event-logs    (sync incremental, cada 5 min via cron)
  python manage.py sync_analytics --reference     (sync tablas de referencia, cada 1h)
  python manage.py sync_analytics --initial       (carga inicial completa)
  python manage.py sync_analytics --once          (una vuelta completa)
"""
import logging
import os
import time
from functools import wraps

import psycopg2
from psycopg2.extras import execute_values

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger('analyticspro.sync')

# ── Tablas de alto volumen (sync incremental por MAX id) ─────────

INCREMENTAL_TABLES = {
    'reportes_app_llamadalog': [
        'id', 'time', 'callid', 'campana_id', 'tipo_campana',
        'tipo_llamada', 'agente_id', 'event', 'numero_marcado',
        'contacto_id', 'bridge_wait_time', 'duracion_llamada',
        'archivo_grabacion', 'agente_extra_id', 'campana_extra_id',
        'numero_extra',
    ],
    'reportes_app_actividadagentelog': [
        'id', 'time', 'agente_id', 'event', 'pausa_id',
    ],
}

# ── Tablas de referencia (full refresh) ─────────────────────────
# Solo columnas efectivamente usadas por las queries analíticas.

REFERENCE_TABLES = {
    'ominicontacto_app_campana': [
        'id', 'nombre', 'type', 'estado', 'es_template',
    ],
    'ominicontacto_app_agenteprofile': [
        'id', 'sip_extension', 'is_inactive', 'borrado', 'user_id',
    ],
    'ominicontacto_app_user': [
        'id', 'username', 'first_name', 'last_name',
    ],
    'ominicontacto_app_pausa': [
        'id', 'nombre', 'tipo',
    ],
}

# ── DDLs de tablas espejo ────────────────────────────────────────

SCHEMA_DDLS = {
    'reportes_app_llamadalog': """
        CREATE TABLE IF NOT EXISTS public.reportes_app_llamadalog (
            id BIGINT PRIMARY KEY,
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            callid VARCHAR(200) NOT NULL,
            campana_id INTEGER,
            tipo_campana INTEGER,
            tipo_llamada INTEGER NOT NULL DEFAULT 3,
            agente_id INTEGER,
            event VARCHAR(32) NOT NULL,
            numero_marcado VARCHAR(128),
            contacto_id INTEGER,
            bridge_wait_time INTEGER,
            duracion_llamada INTEGER,
            archivo_grabacion VARCHAR(100),
            agente_extra_id INTEGER,
            campana_extra_id INTEGER,
            numero_extra VARCHAR(20)
        );
        CREATE INDEX IF NOT EXISTS idx_llamadalog_time ON public.reportes_app_llamadalog ("time");
        CREATE INDEX IF NOT EXISTS idx_llamadalog_campana ON public.reportes_app_llamadalog (campana_id);
        CREATE INDEX IF NOT EXISTS idx_llamadalog_agente ON public.reportes_app_llamadalog (agente_id);
        CREATE INDEX IF NOT EXISTS idx_llamadalog_event ON public.reportes_app_llamadalog (event);
        CREATE INDEX IF NOT EXISTS idx_llamadalog_callid ON public.reportes_app_llamadalog (callid);
        CREATE INDEX IF NOT EXISTS idx_llamadalog_tipo ON public.reportes_app_llamadalog (tipo_llamada);
        CREATE INDEX IF NOT EXISTS idx_llamadalog_time_campana ON public.reportes_app_llamadalog ("time", campana_id);
    """,
    'reportes_app_actividadagentelog': """
        CREATE TABLE IF NOT EXISTS public.reportes_app_actividadagentelog (
            id BIGINT PRIMARY KEY,
            time TIMESTAMP WITH TIME ZONE NOT NULL,
            agente_id INTEGER NOT NULL,
            event VARCHAR(50) NOT NULL,
            pausa_id VARCHAR(50)
        );
        CREATE INDEX IF NOT EXISTS idx_actividad_time ON public.reportes_app_actividadagentelog ("time");
        CREATE INDEX IF NOT EXISTS idx_actividad_agente ON public.reportes_app_actividadagentelog (agente_id);
        CREATE INDEX IF NOT EXISTS idx_actividad_event ON public.reportes_app_actividadagentelog (event);
    """,
    'ominicontacto_app_campana': """
        CREATE TABLE IF NOT EXISTS public.ominicontacto_app_campana (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(128),
            type INTEGER,
            estado INTEGER,
            es_template BOOLEAN
        );
    """,
    'ominicontacto_app_agenteprofile': """
        CREATE TABLE IF NOT EXISTS public.ominicontacto_app_agenteprofile (
            id INTEGER PRIMARY KEY,
            sip_extension VARCHAR(40),
            is_inactive BOOLEAN,
            borrado BOOLEAN,
            user_id INTEGER
        );
    """,
    'ominicontacto_app_user': """
        CREATE TABLE IF NOT EXISTS public.ominicontacto_app_user (
            id INTEGER PRIMARY KEY,
            username VARCHAR(150),
            first_name VARCHAR(150),
            last_name VARCHAR(150)
        );
    """,
    'ominicontacto_app_pausa': """
        CREATE TABLE IF NOT EXISTS public.ominicontacto_app_pausa (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR(128),
            tipo VARCHAR(4)
        );
    """,
    'sync_metadata': """
        CREATE TABLE IF NOT EXISTS public.sync_metadata (
            table_name VARCHAR(100) PRIMARY KEY,
            last_synced_id BIGINT NOT NULL DEFAULT 0,
            last_sync_time TIMESTAMP WITH TIME ZONE,
            sync_status VARCHAR(20) NOT NULL DEFAULT 'pending',
            rows_synced BIGINT NOT NULL DEFAULT 0,
            rows_total BIGINT NOT NULL DEFAULT 0,
            error_message TEXT,
            sync_duration_s REAL
        );
    """,
}


def _get_source_dsn():
    """DSN para la BD fuente (OmniLeads productivo, read-only)."""
    return {
        'host': os.getenv('PGHOST', 'localhost'),
        'port': int(os.getenv('PGPORT', '5432')),
        'dbname': os.getenv('PGDATABASE', 'omnileads'),
        'user': os.getenv('PGUSER', 'omnileads'),
        'password': os.getenv('PGPASSWORD', ''),
        'options': '-c default_transaction_read_only=on',
        'connect_timeout': 15,
    }


def _get_local_dsn():
    """DSN para la BD local (omnileads_local)."""
    db = settings.DATABASES.get('analytics', {})
    return {
        'host': db.get('HOST', 'localhost'),
        'port': int(db.get('PORT', 5432)),
        'dbname': db.get('NAME', 'omnileads_local'),
        'user': db.get('USER', 'analytics'),
        'password': db.get('PASSWORD', ''),
        'connect_timeout': 15,
    }


def _get_watermark(local_conn, table_name):
    """Lee el last_synced_id para la tabla."""
    with local_conn.cursor() as cur:
        cur.execute(
            "SELECT last_synced_id FROM sync_metadata WHERE table_name = %s",
            [table_name]
        )
        row = cur.fetchone()
        return row[0] if row else 0


def _set_status(local_conn, table_name, status, error=None):
    with local_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_metadata (table_name, sync_status, error_message)
            VALUES (%s, %s, %s)
            ON CONFLICT (table_name) DO UPDATE
            SET sync_status = EXCLUDED.sync_status,
                error_message = EXCLUDED.error_message
        """, [table_name, status, error])
    local_conn.commit()


def _update_watermark(local_conn, table_name, last_id, rows_synced, rows_total, status, duration_s):
    with local_conn.cursor() as cur:
        cur.execute("""
            INSERT INTO sync_metadata
                (table_name, last_synced_id, last_sync_time, sync_status,
                 rows_synced, rows_total, sync_duration_s, error_message)
            VALUES (%s, %s, NOW(), %s, %s, %s, %s, NULL)
            ON CONFLICT (table_name) DO UPDATE SET
                last_synced_id = EXCLUDED.last_synced_id,
                last_sync_time = EXCLUDED.last_sync_time,
                sync_status    = EXCLUDED.sync_status,
                rows_synced    = EXCLUDED.rows_synced,
                rows_total     = EXCLUDED.rows_total,
                sync_duration_s = EXCLUDED.sync_duration_s,
                error_message  = NULL
        """, [table_name, last_id, status, rows_synced, rows_total, duration_s])
    local_conn.commit()


def initialize_schema(local_conn):
    """Crea todas las tablas en omnileads_local (idempotente)."""
    with local_conn.cursor() as cur:
        for name, ddl in SCHEMA_DDLS.items():
            logger.info(f'  Ensuring table: {name}')
            cur.execute(ddl)
    local_conn.commit()
    logger.info('Schema initialized.')


def sync_incremental(source_conn, local_conn, table_name, columns, batch_size=10000):
    """Sync incremental: lee desde last_synced_id+1 en bloques."""
    watermark = _get_watermark(local_conn, table_name)
    _set_status(local_conn, table_name, 'syncing')
    start = time.time()
    total_inserted = 0
    cols_sql = ', '.join(columns)
    placeholders = ', '.join(['%s'] * len(columns))
    conflict_updates = ', '.join(
        f'{c} = EXCLUDED.{c}' for c in columns if c != 'id'
    )

    current_id = watermark
    while True:
        # Plain cursor (not named) — pagination is done by SQL LIMIT/OFFSET
        with source_conn.cursor() as src_cur:
            src_cur.execute(
                f"SELECT {cols_sql} FROM public.{table_name} "
                f"WHERE id > %s ORDER BY id LIMIT %s",
                [current_id, batch_size]
            )
            rows = src_cur.fetchall()

        if not rows:
            break

        with local_conn.cursor() as loc_cur:
            execute_values(
                loc_cur,
                f"INSERT INTO public.{table_name} ({cols_sql}) VALUES %s "
                f"ON CONFLICT (id) DO UPDATE SET {conflict_updates}",
                rows
            )
        local_conn.commit()

        total_inserted += len(rows)
        current_id = rows[-1][0]  # last id in batch
        logger.debug(f'[{table_name}] batch {total_inserted} rows, up to id={current_id}')

        if len(rows) < batch_size:
            break  # last page

    # Update watermark
    with local_conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM public.{table_name}")
        rows_total = cur.fetchone()[0]

    _update_watermark(
        local_conn, table_name,
        last_id=current_id,
        rows_synced=total_inserted,
        rows_total=rows_total,
        status='completed',
        duration_s=round(time.time() - start, 2),
    )
    logger.info(
        f'[{table_name}] incremental done: +{total_inserted} rows in '
        f'{time.time()-start:.1f}s. Total: {rows_total}'
    )
    return total_inserted


def sync_reference(source_conn, local_conn, table_name, columns):
    """Full refresh de tabla de referencia (truncate + insert)."""
    _set_status(local_conn, table_name, 'syncing')
    start = time.time()
    cols_sql = ', '.join(columns)

    with source_conn.cursor() as src_cur:
        src_cur.execute(f"SELECT {cols_sql} FROM public.{table_name}")
        rows = src_cur.fetchall()

    placeholders = ', '.join(['%s'] * len(columns))
    conflict_updates = ', '.join(
        f'{c} = EXCLUDED.{c}' for c in columns if c != 'id'
    )

    with local_conn.cursor() as loc_cur:
        execute_values(
            loc_cur,
            f"INSERT INTO public.{table_name} ({cols_sql}) VALUES %s "
            f"ON CONFLICT (id) DO UPDATE SET {conflict_updates}",
            rows
        )
    local_conn.commit()

    _update_watermark(
        local_conn, table_name,
        last_id=0,
        rows_synced=len(rows),
        rows_total=len(rows),
        status='completed',
        duration_s=round(time.time() - start, 2),
    )
    logger.info(f'[{table_name}] reference sync done: {len(rows)} rows in {time.time()-start:.1f}s')
    return len(rows)


class Command(BaseCommand):
    help = 'Sincroniza datos OmniLeads → omnileads_local'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group()
        group.add_argument('--event-logs', action='store_true',
                           help='Sync tablas de eventos (incremental)')
        group.add_argument('--reference', action='store_true',
                           help='Sync tablas de referencia (full refresh)')
        group.add_argument('--initial', action='store_true',
                           help='Carga inicial completa + schema')
        group.add_argument('--once', action='store_true',
                           help='Una vuelta completa (eventos + referencia)')
        group.add_argument('--init-schema', action='store_true',
                           help='Solo inicializar schema (tablas e indices)')

    def handle(self, *args, **options):
        source_conn = None
        local_conn = None
        try:
            source_conn = psycopg2.connect(**_get_source_dsn())
            source_conn.set_session(autocommit=True)  # read-only safe
            local_conn = psycopg2.connect(**_get_local_dsn())

            if options['init_schema'] or options['initial']:
                self.stdout.write('Initializing schema...')
                initialize_schema(local_conn)

            if options['event_logs'] or options['once'] or options['initial']:
                self.stdout.write('Syncing event logs (incremental)...')
                for tbl, cols in INCREMENTAL_TABLES.items():
                    try:
                        n = sync_incremental(source_conn, local_conn, tbl, cols)
                        self.stdout.write(f'  {tbl}: +{n} rows')
                    except Exception as e:
                        _set_status(local_conn, tbl, 'error', str(e))
                        self.stderr.write(f'  ERROR {tbl}: {e}')

            if options['reference'] or options['once'] or options['initial']:
                self.stdout.write('Syncing reference tables (full refresh)...')
                for tbl, cols in REFERENCE_TABLES.items():
                    try:
                        n = sync_reference(source_conn, local_conn, tbl, cols)
                        self.stdout.write(f'  {tbl}: {n} rows')
                    except Exception as e:
                        _set_status(local_conn, tbl, 'error', str(e))
                        self.stderr.write(f'  ERROR {tbl}: {e}')

            self.stdout.write(self.style.SUCCESS('Sync complete.'))

        finally:
            for conn in [source_conn, local_conn]:
                if conn and not conn.closed:
                    try:
                        conn.close()
                    except Exception:
                        pass

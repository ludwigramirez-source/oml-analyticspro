"""
Funciones para gestionar watermarks de sincronizacion.
Los watermarks rastrean el ultimo ID procesado por tabla.
"""
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def get_watermark(conn, table_name: str) -> int:
    """Obtiene el ultimo ID sincronizado para una tabla."""
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT last_synced_id FROM public.sync_metadata "
            "WHERE table_name = %s",
            (table_name,)
        )
        row = cur.fetchone()
        return row[0] if row else 0
    finally:
        cur.close()


def update_watermark(
    conn, table_name: str, last_id: int, rows_synced: int,
    rows_total: int = 0, status: str = 'completed',
    error_message: str = None, duration_s: float = None
):
    """
    Actualiza el watermark y metadata de sincronizacion.
    Usa UPSERT para crear o actualizar el registro.
    """
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO public.sync_metadata
                (table_name, last_synced_id, last_sync_time,
                 sync_status, rows_synced, rows_total,
                 error_message, sync_duration_s)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (table_name) DO UPDATE SET
                last_synced_id = EXCLUDED.last_synced_id,
                last_sync_time = EXCLUDED.last_sync_time,
                sync_status = EXCLUDED.sync_status,
                rows_synced = EXCLUDED.rows_synced,
                rows_total = EXCLUDED.rows_total,
                error_message = EXCLUDED.error_message,
                sync_duration_s = EXCLUDED.sync_duration_s
        """, (
            table_name,
            last_id,
            datetime.now(timezone.utc),
            status,
            rows_synced,
            rows_total,
            error_message,
            duration_s,
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error actualizando watermark para {table_name}: {e}")
        raise
    finally:
        cur.close()


def set_status(conn, table_name: str, status: str,
               error_message: str = None):
    """Actualiza solo el estado de sync (sin cambiar watermark)."""
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO public.sync_metadata
                (table_name, sync_status, error_message,
                 last_sync_time)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (table_name) DO UPDATE SET
                sync_status = EXCLUDED.sync_status,
                error_message = EXCLUDED.error_message,
                last_sync_time = EXCLUDED.last_sync_time
        """, (
            table_name, status, error_message,
            datetime.now(timezone.utc),
        ))
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Error actualizando estado para {table_name}: {e}")
    finally:
        cur.close()


def get_all_status(conn) -> list:
    """Obtiene el estado de sync de todas las tablas."""
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT table_name, last_synced_id, last_sync_time,
                   sync_status, rows_synced, rows_total,
                   error_message, sync_duration_s
            FROM public.sync_metadata
            ORDER BY table_name
        """)
        rows = cur.fetchall()
        return [
            {
                'table_name': r[0],
                'last_synced_id': r[1],
                'last_sync_time': r[2].isoformat() if r[2] else None,
                'sync_status': r[3],
                'rows_synced': r[4],
                'rows_total': r[5],
                'error_message': r[6],
                'sync_duration_s': r[7],
            }
            for r in rows
        ]
    except Exception:
        return []
    finally:
        cur.close()

"""
Motor de sincronizacion de datos OmniLeads → BD Local.
Usa psycopg2 directo para maximo rendimiento.
"""
import logging
import time
from functools import wraps

import psycopg2
from psycopg2.extras import execute_values

from .config import sync_config
from .watermark import get_watermark, set_status, update_watermark

logger = logging.getLogger(__name__)

# ── Definicion de tablas ─────────────────────────────────────────

# Tablas de alto volumen (sync incremental por id)
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
    # Gestiones: alto volumen (234K+ y creciendo), sync incremental
    'ominicontacto_app_customformgestion': [
        'id', 'telefono', 'nombre', 'nis', 'incidencia_id',
        'fecha', 'agent_id', 'call_id', 'campana_id', 'rec_file',
    ],
}

# Tablas de referencia (full refresh — solo tablas pequenas/estaticas)
REFERENCE_TABLES = {
    'ominicontacto_app_campana': [
        'id', 'estado', 'nombre', 'fecha_inicio', 'fecha_fin',
        'oculto', 'campaign_id_wombat', 'type', 'tipo_interaccion',
        'es_template', 'nombre_template', 'es_manual', 'objetivo',
        'tiempo_desconexion', 'bd_contacto_id', 'reported_by_id',
        'sitio_externo_id', 'mostrar_nombre', 'id_externo',
        'sistema_externo_id', 'campo_desactivacion',
        'campos_bd_no_editables', 'campos_bd_ocultos', 'outcid',
        'outr_id', 'videocall_habilitada', 'speech',
        'campo_direccion', 'mostrar_did',
        'mostrar_nombre_ruta_entrante', 'control_de_duplicados',
        'prioridad', 'campos_bd_obligatorios',
    ],
    'ominicontacto_app_agenteprofile': [
        'id', 'sip_extension', 'sip_password', 'estado',
        'is_inactive', 'borrado', 'grupo_id', 'reported_by_id',
        'user_id',
    ],
    'ominicontacto_app_user': [
        'id', 'password', 'last_login', 'is_superuser', 'username',
        'first_name', 'last_name', 'email', 'is_staff', 'is_active',
        'date_joined',
    ],
    'ominicontacto_app_pausa': [
        'id', 'nombre', 'tipo', 'eliminada',
    ],
    'ominicontacto_app_customformincidencias': [
        'id', 'codigo', 'descripcion', 'created_at', 'updated_at',
        'is_active',
    ],
}


def retry_on_db_error(max_retries=3, base_delay=5):
    """Decorator con retry y backoff exponencial para errores de BD."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except (psycopg2.OperationalError,
                        psycopg2.InterfaceError) as e:
                    last_exception = e
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Error de conexion en {func.__name__} "
                        f"(intento {attempt + 1}/{max_retries}): {e}. "
                        f"Reintentando en {delay}s..."
                    )
                    time.sleep(delay)
            logger.error(
                f"Fallo definitivo en {func.__name__} "
                f"despues de {max_retries} intentos: {last_exception}"
            )
            raise last_exception
        return wrapper
    return decorator


class SyncEngine:
    """Motor de sincronizacion con psycopg2 directo."""

    def __init__(self):
        self._source_conn = None
        self._local_conn = None

    def _get_source_conn(self):
        """Obtiene conexion a BD source (recreando si es necesario)."""
        if self._source_conn is None or self._source_conn.closed:
            self._source_conn = psycopg2.connect(
                **sync_config.get_source_dsn()
            )
            self._source_conn.set_session(autocommit=False)
        return self._source_conn

    def _get_local_conn(self):
        """Obtiene conexion a BD local (recreando si es necesario)."""
        if self._local_conn is None or self._local_conn.closed:
            self._local_conn = psycopg2.connect(
                **sync_config.get_local_dsn()
            )
            self._local_conn.set_session(autocommit=False)
        return self._local_conn

    def close(self):
        """Cierra todas las conexiones."""
        for conn in (self._source_conn, self._local_conn):
            if conn and not conn.closed:
                try:
                    conn.close()
                except Exception:
                    pass
        self._source_conn = None
        self._local_conn = None

    # ── Sync incremental (tablas de alto volumen) ────────────────

    @retry_on_db_error(max_retries=3, base_delay=5)
    def sync_incremental(self, table_name: str, columns: list):
        """
        Sincroniza una tabla de alto volumen de forma incremental.
        - Lee el watermark (ultimo id procesado)
        - SELECT nuevos registros desde source
        - INSERT con ON CONFLICT DO NOTHING en local
        - Actualiza watermark
        """
        local_conn = self._get_local_conn()
        source_conn = self._get_source_conn()

        watermark = get_watermark(local_conn, table_name)
        set_status(local_conn, table_name, 'syncing')

        start_time = time.time()
        total_inserted = 0
        is_initial = watermark == 0
        batch_size = (
            sync_config.SYNC_INITIAL_BATCH_SIZE
            if is_initial
            else sync_config.SYNC_BATCH_SIZE
        )

        if is_initial:
            logger.info(
                f"[{table_name}] Carga inicial "
                f"(batch_size={batch_size})..."
            )
        else:
            logger.info(
                f"[{table_name}] Sync incremental "
                f"desde id={watermark}..."
            )

        try:
            # Para carga inicial, usar server-side cursor
            if is_initial:
                total_inserted = self._initial_load(
                    source_conn, local_conn,
                    table_name, columns, batch_size
                )
            else:
                total_inserted = self._incremental_sync(
                    source_conn, local_conn,
                    table_name, columns, watermark, batch_size
                )

            duration = time.time() - start_time

            # Obtener conteo total en local
            cur_local = local_conn.cursor()
            cur_local.execute(
                f"SELECT COUNT(*) FROM public.{table_name}"
            )
            rows_total = cur_local.fetchone()[0]
            cur_local.close()

            # Obtener watermark actualizado
            new_watermark = get_watermark(local_conn, table_name)

            update_watermark(
                local_conn, table_name,
                last_id=new_watermark,
                rows_synced=total_inserted,
                rows_total=rows_total,
                status='completed',
                duration_s=round(duration, 2),
            )

            rate = (
                f" ({total_inserted / duration:.0f} rows/s)"
                if duration > 0 and total_inserted > 0 else ""
            )
            logger.info(
                f"[{table_name}] Sync completado: "
                f"+{total_inserted} filas en {duration:.1f}s{rate}. "
                f"Total local: {rows_total}"
            )
            return total_inserted

        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{table_name}] Error en sync: {e}"
            )
            set_status(
                local_conn, table_name, 'error',
                error_message=str(e)[:500]
            )
            raise

    def _initial_load(
        self, source_conn, local_conn,
        table_name, columns, batch_size
    ):
        """Carga inicial usando server-side cursor."""
        cols_str = ', '.join(f'"{c}"' for c in columns)
        placeholders = ', '.join(['%s'] * len(columns))
        conflict_col = 'id'

        insert_sql = (
            f"INSERT INTO public.{table_name} ({cols_str}) "
            f"VALUES %s "
            f"ON CONFLICT ({conflict_col}) DO NOTHING"
        )

        # Server-side cursor para no cargar todo en memoria
        cursor_name = f"sync_{table_name}_initial"
        source_cur = source_conn.cursor(name=cursor_name)
        source_cur.itersize = batch_size

        source_cur.execute(
            f"SELECT {cols_str} FROM public.{table_name} "
            f"ORDER BY id"
        )

        total = 0
        max_id = 0
        local_cur = local_conn.cursor()

        try:
            while True:
                rows = source_cur.fetchmany(batch_size)
                if not rows:
                    break

                execute_values(
                    local_cur, insert_sql, rows,
                    page_size=batch_size
                )
                local_conn.commit()

                batch_max_id = max(r[0] for r in rows)  # id = col 0
                max_id = max(max_id, batch_max_id)
                total += len(rows)

                # Actualizar watermark parcial
                update_watermark(
                    local_conn, table_name,
                    last_id=max_id,
                    rows_synced=total,
                    status='syncing',
                )

                logger.info(
                    f"  [{table_name}] Carga inicial: "
                    f"{total} filas procesadas "
                    f"(ultimo id={max_id})"
                )

        finally:
            source_cur.close()
            local_cur.close()

        return total

    def _incremental_sync(
        self, source_conn, local_conn,
        table_name, columns, watermark, batch_size
    ):
        """Sync incremental desde watermark."""
        cols_str = ', '.join(f'"{c}"' for c in columns)
        conflict_col = 'id'

        insert_sql = (
            f"INSERT INTO public.{table_name} ({cols_str}) "
            f"VALUES %s "
            f"ON CONFLICT ({conflict_col}) DO NOTHING"
        )

        source_cur = source_conn.cursor()
        local_cur = local_conn.cursor()

        total = 0
        current_watermark = watermark

        try:
            while True:
                source_cur.execute(
                    f"SELECT {cols_str} FROM public.{table_name} "
                    f"WHERE id > %s ORDER BY id LIMIT %s",
                    (current_watermark, batch_size)
                )
                rows = source_cur.fetchall()

                if not rows:
                    break

                execute_values(
                    local_cur, insert_sql, rows,
                    page_size=batch_size
                )
                local_conn.commit()

                batch_max_id = max(r[0] for r in rows)
                current_watermark = batch_max_id
                total += len(rows)

                # Actualizar watermark despues de cada batch
                update_watermark(
                    local_conn, table_name,
                    last_id=current_watermark,
                    rows_synced=total,
                    status='syncing',
                )

                logger.info(
                    f"  [{table_name}] +{len(rows)} filas "
                    f"(watermark={current_watermark})"
                )

                # Si el batch no esta lleno, terminamos
                if len(rows) < batch_size:
                    break

        finally:
            source_cur.close()
            local_cur.close()

        return total

    # ── Full refresh (tablas de referencia) ───────────────────────

    @retry_on_db_error(max_retries=3, base_delay=5)
    def sync_reference_table(self, table_name: str, columns: list):
        """
        Sincroniza una tabla de referencia con full refresh.
        TRUNCATE + INSERT atomico dentro de una transaccion.
        """
        local_conn = self._get_local_conn()
        source_conn = self._get_source_conn()

        set_status(local_conn, table_name, 'syncing')
        start_time = time.time()

        cols_str = ', '.join(f'"{c}"' for c in columns)

        try:
            # Leer todos los datos de source
            source_cur = source_conn.cursor()
            source_cur.execute(
                f"SELECT {cols_str} FROM public.{table_name}"
            )
            rows = source_cur.fetchall()
            source_cur.close()

            # TRUNCATE + INSERT atomico
            local_cur = local_conn.cursor()
            local_cur.execute(
                f"TRUNCATE TABLE public.{table_name}"
            )

            if rows:
                insert_sql = (
                    f"INSERT INTO public.{table_name} ({cols_str}) "
                    f"VALUES %s"
                )
                execute_values(local_cur, insert_sql, rows)

            local_conn.commit()
            local_cur.close()

            duration = time.time() - start_time
            max_id = max((r[0] for r in rows), default=0)

            update_watermark(
                local_conn, table_name,
                last_id=max_id,
                rows_synced=len(rows),
                rows_total=len(rows),
                status='completed',
                duration_s=round(duration, 2),
            )

            logger.info(
                f"[{table_name}] Full refresh: "
                f"{len(rows)} filas en {duration:.1f}s"
            )
            return len(rows)

        except Exception as e:
            local_conn.rollback()
            logger.error(
                f"[{table_name}] Error en full refresh: {e}"
            )
            set_status(
                local_conn, table_name, 'error',
                error_message=str(e)[:500]
            )
            raise

    # ── Sync completo (todas las tablas) ─────────────────────────

    def sync_event_logs(self):
        """Sincroniza las tablas de alto volumen."""
        for table, columns in INCREMENTAL_TABLES.items():
            try:
                self.sync_incremental(table, columns)
            except Exception as e:
                logger.error(
                    f"Error sincronizando {table}: {e}"
                )

    def sync_reference_data(self):
        """Sincroniza las tablas de referencia."""
        for table, columns in REFERENCE_TABLES.items():
            try:
                self.sync_reference_table(table, columns)
            except Exception as e:
                logger.error(
                    f"Error sincronizando {table}: {e}"
                )

    def sync_all(self):
        """Ejecuta sync completo de todas las tablas."""
        logger.info("=" * 60)
        logger.info("Iniciando sync completo...")
        logger.info("=" * 60)

        start = time.time()

        # Primero las tablas de referencia (rapido)
        self.sync_reference_data()

        # Luego las tablas de alto volumen
        self.sync_event_logs()

        duration = time.time() - start
        logger.info(
            f"Sync completo finalizado en {duration:.1f}s"
        )

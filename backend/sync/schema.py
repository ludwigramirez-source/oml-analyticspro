"""
DDL para crear las tablas en la BD local.
Schema identico al de OmniLeads (omnileads_models.py).
"""
import logging

logger = logging.getLogger(__name__)

# ── Tablas de alto volumen (sync incremental) ────────────────────

LLAMADA_LOG_DDL = """
CREATE TABLE IF NOT EXISTS public.reportes_app_llamadalog (
    id              INTEGER PRIMARY KEY,
    "time"          TIMESTAMP WITH TIME ZONE NOT NULL,
    callid          VARCHAR(32),
    campana_id      INTEGER,
    tipo_campana    INTEGER,
    tipo_llamada    INTEGER,
    agente_id       INTEGER,
    event           VARCHAR(32),
    numero_marcado  VARCHAR(128),
    contacto_id     INTEGER,
    bridge_wait_time INTEGER,
    duracion_llamada INTEGER,
    archivo_grabacion VARCHAR(100),
    agente_extra_id  INTEGER,
    campana_extra_id INTEGER,
    numero_extra    VARCHAR(128)
);
"""

ACTIVIDAD_AGENTE_LOG_DDL = """
CREATE TABLE IF NOT EXISTS public.reportes_app_actividadagentelog (
    id        INTEGER PRIMARY KEY,
    "time"    TIMESTAMP WITH TIME ZONE NOT NULL,
    agente_id INTEGER,
    event     VARCHAR(32),
    pausa_id  VARCHAR(128)
);
"""

# ── Tablas de referencia (full refresh) ──────────────────────────

CAMPANA_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_campana (
    id                      INTEGER PRIMARY KEY,
    estado                  INTEGER NOT NULL,
    nombre                  VARCHAR(128) NOT NULL,
    fecha_inicio            DATE,
    fecha_fin               DATE,
    oculto                  BOOLEAN NOT NULL DEFAULT false,
    campaign_id_wombat      INTEGER,
    type                    INTEGER NOT NULL DEFAULT 0,
    tipo_interaccion        INTEGER NOT NULL DEFAULT 0,
    es_template             BOOLEAN NOT NULL DEFAULT false,
    nombre_template         VARCHAR(128),
    es_manual               BOOLEAN NOT NULL DEFAULT false,
    objetivo                INTEGER NOT NULL DEFAULT 0,
    tiempo_desconexion      INTEGER NOT NULL DEFAULT 0,
    bd_contacto_id          INTEGER,
    reported_by_id          INTEGER NOT NULL DEFAULT 0,
    sitio_externo_id        INTEGER,
    mostrar_nombre          BOOLEAN NOT NULL DEFAULT false,
    id_externo              VARCHAR(128),
    sistema_externo_id      INTEGER,
    campo_desactivacion     VARCHAR(128),
    campos_bd_no_editables  VARCHAR(2052) NOT NULL DEFAULT '',
    campos_bd_ocultos       VARCHAR(2052) NOT NULL DEFAULT '',
    outcid                  VARCHAR(128),
    outr_id                 INTEGER,
    videocall_habilitada    BOOLEAN NOT NULL DEFAULT false,
    speech                  TEXT,
    campo_direccion         VARCHAR(128),
    mostrar_did             BOOLEAN NOT NULL DEFAULT false,
    mostrar_nombre_ruta_entrante BOOLEAN NOT NULL DEFAULT false,
    control_de_duplicados   INTEGER NOT NULL DEFAULT 0,
    prioridad               INTEGER NOT NULL DEFAULT 0,
    campos_bd_obligatorios  VARCHAR(2052) NOT NULL DEFAULT ''
);
"""

AGENTE_PROFILE_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_agenteprofile (
    id              INTEGER PRIMARY KEY,
    sip_extension   INTEGER NOT NULL,
    sip_password    VARCHAR(128),
    estado          INTEGER NOT NULL DEFAULT 0,
    is_inactive     BOOLEAN NOT NULL DEFAULT false,
    borrado         BOOLEAN NOT NULL DEFAULT false,
    grupo_id        INTEGER NOT NULL DEFAULT 0,
    reported_by_id  INTEGER NOT NULL DEFAULT 0,
    user_id         INTEGER NOT NULL
);
"""

USER_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_user (
    id            INTEGER PRIMARY KEY,
    password      VARCHAR(128) NOT NULL DEFAULT '',
    last_login    TIMESTAMP WITH TIME ZONE,
    is_superuser  BOOLEAN NOT NULL DEFAULT false,
    username      VARCHAR(150) NOT NULL,
    first_name    VARCHAR(150) NOT NULL DEFAULT '',
    last_name     VARCHAR(150) NOT NULL DEFAULT '',
    email         VARCHAR(254) NOT NULL DEFAULT '',
    is_staff      BOOLEAN NOT NULL DEFAULT false,
    is_active     BOOLEAN NOT NULL DEFAULT true,
    date_joined   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
"""

PAUSA_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_pausa (
    id        INTEGER PRIMARY KEY,
    nombre    VARCHAR(20) NOT NULL,
    tipo      VARCHAR(1) NOT NULL,
    eliminada BOOLEAN NOT NULL DEFAULT false
);
"""

CUSTOM_FORM_GESTION_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_customformgestion (
    id             INTEGER PRIMARY KEY,
    telefono       VARCHAR(128) NOT NULL DEFAULT '',
    nombre         VARCHAR(255) NOT NULL DEFAULT '',
    nis            VARCHAR(128) NOT NULL DEFAULT '',
    incidencia_id  INTEGER NOT NULL DEFAULT 0,
    fecha          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    agent_id       INTEGER NOT NULL DEFAULT 0,
    call_id        VARCHAR(200) NOT NULL DEFAULT '',
    campana_id     INTEGER NOT NULL DEFAULT 0,
    rec_file       VARCHAR(255)
);
"""

CUSTOM_FORM_INCIDENCIAS_DDL = """
CREATE TABLE IF NOT EXISTS public.ominicontacto_app_customformincidencias (
    id          INTEGER PRIMARY KEY,
    codigo      INTEGER NOT NULL DEFAULT 0,
    descripcion VARCHAR(255) NOT NULL DEFAULT '',
    created_at  DATE NOT NULL DEFAULT CURRENT_DATE,
    updated_at  DATE NOT NULL DEFAULT CURRENT_DATE,
    is_active   BOOLEAN NOT NULL DEFAULT true
);
"""

# ── Tabla de metadata de sincronizacion ──────────────────────────

SYNC_METADATA_DDL = """
CREATE TABLE IF NOT EXISTS public.sync_metadata (
    table_name      VARCHAR(100) PRIMARY KEY,
    last_synced_id  BIGINT NOT NULL DEFAULT 0,
    last_sync_time  TIMESTAMP WITH TIME ZONE,
    sync_status     VARCHAR(20) NOT NULL DEFAULT 'pending',
    rows_synced     BIGINT NOT NULL DEFAULT 0,
    rows_total      BIGINT NOT NULL DEFAULT 0,
    error_message   TEXT,
    sync_duration_s REAL
);
"""

# ── Indices de rendimiento ───────────────────────────────────────

PERFORMANCE_INDEXES = [
    # llamadalog
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_time ON public.reportes_app_llamadalog (\"time\")",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_campana_id ON public.reportes_app_llamadalog (campana_id)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_agente_id ON public.reportes_app_llamadalog (agente_id)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_event ON public.reportes_app_llamadalog (event)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_callid ON public.reportes_app_llamadalog (callid)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_tipo_llamada ON public.reportes_app_llamadalog (tipo_llamada)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_time_campana ON public.reportes_app_llamadalog (\"time\", campana_id)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_time_agente ON public.reportes_app_llamadalog (\"time\", agente_id)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_callid_time ON public.reportes_app_llamadalog (callid, \"time\" DESC)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_event_tipo ON public.reportes_app_llamadalog (event, tipo_llamada)",
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_time_event_campana ON public.reportes_app_llamadalog (\"time\", event, campana_id)",
    # covering index for KPIs
    "CREATE INDEX IF NOT EXISTS idx_llamadalog_kpi_cover ON public.reportes_app_llamadalog (\"time\", tipo_llamada, event) INCLUDE (callid, duracion_llamada, bridge_wait_time, campana_id, agente_id)",
    # actividadagentelog
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_time ON public.reportes_app_actividadagentelog (\"time\")",
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_agente_id ON public.reportes_app_actividadagentelog (agente_id)",
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_event ON public.reportes_app_actividadagentelog (event)",
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_agente_time ON public.reportes_app_actividadagentelog (agente_id, \"time\" DESC)",
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_agente_event ON public.reportes_app_actividadagentelog (agente_id, event)",
    "CREATE INDEX IF NOT EXISTS idx_actividadagente_cover ON public.reportes_app_actividadagentelog (agente_id, \"time\", event) INCLUDE (pausa_id)",
]


def initialize_schema(conn):
    """
    Crea todas las tablas e indices en la BD local.
    Seguro de ejecutar multiples veces (IF NOT EXISTS).
    """
    logger.info("Inicializando schema de BD local...")

    tables = [
        ('reportes_app_llamadalog', LLAMADA_LOG_DDL),
        ('reportes_app_actividadagentelog', ACTIVIDAD_AGENTE_LOG_DDL),
        ('ominicontacto_app_campana', CAMPANA_DDL),
        ('ominicontacto_app_agenteprofile', AGENTE_PROFILE_DDL),
        ('ominicontacto_app_user', USER_DDL),
        ('ominicontacto_app_pausa', PAUSA_DDL),
        ('ominicontacto_app_customformgestion', CUSTOM_FORM_GESTION_DDL),
        ('ominicontacto_app_customformincidencias',
         CUSTOM_FORM_INCIDENCIAS_DDL),
        ('sync_metadata', SYNC_METADATA_DDL),
    ]

    cur = conn.cursor()
    try:
        for name, ddl in tables:
            logger.info(f"  Creando tabla: {name}")
            cur.execute(ddl)

        logger.info("Creando indices de rendimiento...")
        for idx_sql in PERFORMANCE_INDEXES:
            cur.execute(idx_sql)

        conn.commit()
        logger.info("Schema inicializado correctamente")
    except Exception as e:
        conn.rollback()
        logger.error(f"Error inicializando schema: {e}")
        raise
    finally:
        cur.close()

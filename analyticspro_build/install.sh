#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  AnalyticsPro VOML — Instalador
#  Uso: bash analyticspro_build/install.sh
#  Ejecutar en el servidor OmniLeads (SSH como root)
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Rutas estándar OmniLeads ──────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OML_HOME=/opt/omnileads/ominicontacto
VENV_PY=/opt/omnileads/virtualenv/bin/python
SETTINGS_DIR=$OML_HOME/ominicontacto/settings
DEST_DIR=$OML_HOME/analyticspro
FIFO=/opt/omnileads/run/.uwsgi-fifo
ENVARS=/etc/profile.d/omnileads_envars.sh
SYNC_LOG=/var/log/analyticspro_sync.log
TOTAL_STEPS=7

# ── Colores ───────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# ── Helpers ───────────────────────────────────────────────────────────────────
banner()  { echo -e "${CYAN}${BOLD}$*${NC}"; }
info()    { echo -e "  ${CYAN}→${NC} $*"; }
ok()      { echo -e "    ${GREEN}✓${NC} $*"; }
warn()    { echo -e "    ${YELLOW}⚠${NC}  $*"; }
fail()    { echo -e "    ${RED}✗ ERROR:${NC} $*" >&2; exit 1; }
step()    { echo ""; echo -e "  ${BOLD}[$1/${TOTAL_STEPS}]${NC} ${BOLD}$2${NC}"; }

psql_run() {
    # psql_run <dbname> <sql>
    PGPASSWORD="$OML_PGPASSWORD" psql \
        -h "$OML_PGHOST" -p "$OML_PGPORT" \
        -U "$OML_PGUSER" -d "$1" \
        -v ON_ERROR_STOP=1 \
        -c "$2" 2>&1
}

psql_check() {
    # psql_check <dbname> <sql> — returns exit code 0 if rows found
    PGPASSWORD="$OML_PGPASSWORD" psql \
        -h "$OML_PGHOST" -p "$OML_PGPORT" \
        -U "$OML_PGUSER" -d "$1" \
        -tAc "$2" 2>/dev/null | grep -q 1
}

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║   AnalyticsPro — Instalador  VOML   ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

# ── Verificar entorno OmniLeads ───────────────────────────────────────────────
if [ ! -f "$ENVARS" ]; then
    fail "No se encontró $ENVARS\n  Este script debe correr en un servidor OmniLeads instalado."
fi

source "$ENVARS" 2>/dev/null || true

if [ ! -f "$VENV_PY" ]; then
    fail "No se encontró el virtualenv en $VENV_PY"
fi

if [ ! -d "$OML_HOME" ]; then
    fail "No se encontró OmniLeads en $OML_HOME"
fi

# ── Leer variables de entorno PostgreSQL ──────────────────────────────────────
OML_PGHOST="${PGHOST:-localhost}"
OML_PGPORT="${PGPORT:-5432}"
OML_PGUSER="${PGUSER:-omnileads}"
OML_PGDATABASE="${PGDATABASE:-omnileads}"
OML_PGPASSWORD="${PGPASSWORD:-}"

# Auto-detectar zona horaria del servidor
SERVER_TZ="$(timedatectl 2>/dev/null | awk '/Time zone/ {print $3}' || cat /etc/timezone 2>/dev/null || echo 'America/Bogota')"

# ── Mostrar entorno detectado ─────────────────────────────────────────────────
banner "Entorno detectado:"
info "OmniLeads:  $OML_HOME"
info "Python:     $VENV_PY"
info "PostgreSQL: $OML_PGHOST:$OML_PGPORT  BD=$OML_PGDATABASE  Usuario=$OML_PGUSER"
info "TZ servidor: $SERVER_TZ"
echo ""

# ── Preguntas interactivas ────────────────────────────────────────────────────
banner "Configuración requerida:"
echo ""

# 1. Contraseña para analytics_user
while true; do
    read -s -p "  Contraseña para analytics_user (nueva, mín. 8 chars): " ANALYTICS_DB_PASSWORD
    echo ""
    if [ ${#ANALYTICS_DB_PASSWORD} -ge 8 ]; then
        read -s -p "  Confirmar contraseña: " ANALYTICS_DB_PASSWORD2
        echo ""
        if [ "$ANALYTICS_DB_PASSWORD" = "$ANALYTICS_DB_PASSWORD2" ]; then
            break
        else
            echo -e "  ${RED}Las contraseñas no coinciden. Intente de nuevo.${NC}"
        fi
    else
        echo -e "  ${RED}Contraseña muy corta (mínimo 8 caracteres).${NC}"
    fi
done

# 2. Zona horaria — mostrar opciones comunes para evitar errores de tipeo
echo ""
echo -e "  ${BOLD}Zona horaria de la BD:${NC}"
echo "  Opciones comunes: America/Bogota, America/Lima, America/Managua,"
echo "                    America/Mexico_City, America/Caracas, America/Santiago"
echo "  (Detectada en el servidor: $SERVER_TZ)"
while true; do
    read -p "  Ingresa la zona horaria [$SERVER_TZ]: " TZ_INPUT
    ANALYTICS_TZ="${TZ_INPUT:-$SERVER_TZ}"
    # Validar que no sea una sola letra ni esté vacía de forma extraña
    if [ ${#ANALYTICS_TZ} -gt 3 ] && [[ "$ANALYTICS_TZ" == *"/"* ]]; then
        break
    else
        echo -e "  ${RED}Zona horaria inválida. Debe tener el formato Región/Ciudad (ej: America/Bogota).${NC}"
    fi
done

# 3. Llamadas salientes
echo ""
read -p "  ¿Mostrar llamadas salientes en KPIs? Escribe 'si' o 'no' [no]: " INBOUND_INPUT
case "${INBOUND_INPUT,,}" in
    si|yes|y) INBOUND_ONLY="False" ;;
    *)        INBOUND_ONLY="True"  ;;
esac

# ── Resumen + confirmación ────────────────────────────────────────────────────
echo ""
banner "Resumen de instalación:"
info "Módulo destino:       $DEST_DIR"
info "BD analytics:         omnileads_local @ $OML_PGHOST:$OML_PGPORT"
info "Usuario analytics:    analytics_user / ****"
info "Zona horaria BD:      $ANALYTICS_TZ"
info "Salientes visibles:   $([ "$INBOUND_ONLY" = 'False' ] && echo 'Sí' || echo 'No')"
echo ""
read -p "  ¿Continuar con la instalación? [s/N]: " CONFIRM
case "${CONFIRM,,}" in
    s|si|yes|y) ;;
    *) echo "  Cancelado."; exit 0 ;;
esac

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 1 — Copiar módulo
# ═══════════════════════════════════════════════════════════════════════════════
step 1 "Copiando módulo analyticspro"

# Si el destino ya existe y es el mismo directorio que el fuente, skip
if [ "$(realpath "$SCRIPT_DIR" 2>/dev/null)" = "$(realpath "$DEST_DIR" 2>/dev/null)" ]; then
    ok "El fuente ya está en el destino ($DEST_DIR) — omitiendo copia"
else
    mkdir -p "$DEST_DIR"
    # Copiar todo excepto install.sh y scripts _*.py de desarrollo
    rsync -a --exclude='install.sh' --exclude='_*.py' \
          "$SCRIPT_DIR/" "$DEST_DIR/" 2>/dev/null || \
    {
        # Fallback si rsync no está disponible
        cp -r "$SCRIPT_DIR/." "$DEST_DIR/"
        rm -f "$DEST_DIR/install.sh" "$DEST_DIR"/_*.py 2>/dev/null || true
    }
    ok "Módulo copiado → $DEST_DIR"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 2 — Crear BD secundaria y usuario
# ═══════════════════════════════════════════════════════════════════════════════
step 2 "Creando BD omnileads_local y usuario analytics_user"

# Crear usuario (idempotente)
if psql_check postgres "SELECT 1 FROM pg_roles WHERE rolname='analytics_user'"; then
    # Ya existe — actualizar contraseña
    psql_run postgres "ALTER ROLE analytics_user WITH PASSWORD '$ANALYTICS_DB_PASSWORD'" > /dev/null
    ok "analytics_user ya existía — contraseña actualizada"
else
    psql_run postgres "CREATE ROLE analytics_user WITH LOGIN PASSWORD '$ANALYTICS_DB_PASSWORD'" > /dev/null
    ok "analytics_user creado"
fi

# Crear base de datos (idempotente)
if psql_check postgres "SELECT 1 FROM pg_database WHERE datname='omnileads_local'"; then
    ok "omnileads_local ya existía — omitiendo creación"
else
    psql_run postgres "CREATE DATABASE omnileads_local OWNER analytics_user ENCODING 'UTF8'" > /dev/null
    ok "Base de datos omnileads_local creada"
fi

# Otorgar permisos
psql_run postgres "GRANT ALL PRIVILEGES ON DATABASE omnileads_local TO analytics_user" > /dev/null

# Otorgar SELECT en tablas fuente
SOURCE_TABLES=(
    "reportes_app_llamadalog"
    "reportes_app_actividadagentelog"
    "ominicontacto_app_campana"
    "ominicontacto_app_agenteprofile"
    "ominicontacto_app_user"
    "ominicontacto_app_pausa"
)
for TABLE in "${SOURCE_TABLES[@]}"; do
    psql_run "$OML_PGDATABASE" "GRANT SELECT ON $TABLE TO analytics_user" > /dev/null \
        && true || warn "GRANT SELECT en $TABLE falló (puede no existir)"
done
ok "Permisos SELECT otorgados en tablas fuente"

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 3 — Registrar app en OmniLeads
# ═══════════════════════════════════════════════════════════════════════════════
step 3 "Registrando analyticspro en OmniLeads"

ADDONS_FILE="$SETTINGS_DIR/addons.py"
LOCAL_FILE="$SETTINGS_DIR/oml_settings_local.py"
TS="$(date +%Y%m%d_%H%M%S)"

if [ ! -f "$ADDONS_FILE" ]; then
    fail "No se encontró $ADDONS_FILE — verifica la instalación de OmniLeads"
fi

# Patch addons.py
if grep -q "analyticspro" "$ADDONS_FILE" 2>/dev/null; then
    ok "addons.py ya tenía analyticspro — omitido"
else
    cp "$ADDONS_FILE" "${ADDONS_FILE}.bak.${TS}"
    cat >> "$ADDONS_FILE" << 'ADDONS_EOF'

# ── AnalyticsPro (módulo de analytics integrado) ──────────────────
ADDONS_APPS.append('analyticspro.apps.AnalyticsproConfig')
ADDON_URLPATTERNS.append((r'^', 'analyticspro.urls'))
ADDONS_EOF
    ok "addons.py actualizado (backup: addons.py.bak.$TS)"
fi

# Patch oml_settings_local.py
if [ ! -f "$LOCAL_FILE" ]; then
    fail "No se encontró $LOCAL_FILE — verifica la instalación de OmniLeads"
fi

if grep -q "analyticspro\|omnileads_local" "$LOCAL_FILE" 2>/dev/null; then
    ok "oml_settings_local.py ya tenía configuración analytics — omitido"
else
    cp "$LOCAL_FILE" "${LOCAL_FILE}.bak.${TS}"
    cat >> "$LOCAL_FILE" << SETTINGS_EOF

# ══ AnalyticsPro ══════════════════════════════════════════════════════════════
DATABASES['analytics'] = {
    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    'HOST': '${OML_PGHOST}',
    'PORT': '${OML_PGPORT}',
    'NAME': 'omnileads_local',
    'USER': 'analytics_user',
    'PASSWORD': '${ANALYTICS_DB_PASSWORD}',
    'CONN_MAX_AGE': 300,
    'OPTIONS': {'options': '-c statement_timeout=30000'},
}
DATABASE_ROUTERS = ['analyticspro.db.AnalyticsRouter']
ANALYTICSPRO_TIMEZONE_DB = '${ANALYTICS_TZ}'
ANALYTICSPRO_INBOUND_ONLY = ${INBOUND_ONLY}
ANALYTICSPRO_SYNC_BATCH_SIZE = 10000
SETTINGS_EOF
    ok "oml_settings_local.py actualizado (backup: oml_settings_local.py.bak.$TS)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 4 — Collectstatic
# ═══════════════════════════════════════════════════════════════════════════════
step 4 "Recolectando archivos estáticos"

cd "$OML_HOME"
"$VENV_PY" manage.py collectstatic --noinput -v 0 2>&1 | tail -3 || fail "collectstatic falló"
ok "Collectstatic completado"

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 5 — Carga inicial de datos
# ═══════════════════════════════════════════════════════════════════════════════
step 5 "Carga inicial de datos (puede tardar varios minutos según el volumen)"
echo "      Esto sincroniza el historial completo de OmniLeads → omnileads_local"

SYNC_OUTPUT=$("$VENV_PY" manage.py sync_analytics --initial 2>&1) || fail "sync_analytics --initial falló:\n$SYNC_OUTPUT"

# Contar total de filas insertadas
TOTAL_ROWS=$(echo "$SYNC_OUTPUT" | grep -oP '\+\d+' | tr -d '+' | awk '{s+=$1} END {print s}' 2>/dev/null || echo "?")
echo "$SYNC_OUTPUT" | grep -E "(Sync|syncing|table|ERROR|error)" | head -15 | sed 's/^/      /'
ok "Sync inicial completo — $TOTAL_ROWS filas cargadas"

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 6 — Configurar cron
# ═══════════════════════════════════════════════════════════════════════════════
step 6 "Configurando sincronización periódica (cron)"

CRON_EVENTS="*/5 * * * * source ${ENVARS} && cd ${OML_HOME} && ${VENV_PY} manage.py sync_analytics --event-logs >> ${SYNC_LOG} 2>&1"
CRON_REF="0 * * * * source ${ENVARS} && cd ${OML_HOME} && ${VENV_PY} manage.py sync_analytics --reference >> ${SYNC_LOG} 2>&1"

# Eliminar entradas anteriores de analyticspro + agregar las nuevas (idempotente)
(
    crontab -l 2>/dev/null | grep -v "analyticspro\|sync_analytics" || true
    echo "# ── AnalyticsPro sync ──────────────────────────────────────────────"
    echo "$CRON_EVENTS"
    echo "$CRON_REF"
) | crontab -

ok "Cron configurado: eventos cada 5 min, referencia cada hora"
info "Log: $SYNC_LOG"

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 7 — Recargar servidor de aplicaciones
# ═══════════════════════════════════════════════════════════════════════════════
step 7 "Recargando servidor de aplicaciones"

RELOADED=false

# Opción A: systemd omnileads (nombre estándar en instalaciones recientes)
if systemctl is-active --quiet omnileads 2>/dev/null; then
    systemctl restart omnileads
    ok "Servicio omnileads reiniciado"
    RELOADED=true
fi

# Opción B: uWSGI FIFO
if [ "$RELOADED" = false ] && [ -p "$FIFO" ]; then
    echo r > "$FIFO"
    sleep 2
    ok "uWSGI recargado vía FIFO ($FIFO)"
    RELOADED=true
fi

# Opción C: systemd omnileads-uwsgi
if [ "$RELOADED" = false ] && systemctl is-active --quiet omnileads-uwsgi 2>/dev/null; then
    systemctl restart omnileads-uwsgi
    ok "Servicio omnileads-uwsgi reiniciado"
    RELOADED=true
fi

# Opción D: systemd omnileads-gunicorn
if [ "$RELOADED" = false ] && systemctl is-active --quiet omnileads-gunicorn 2>/dev/null; then
    systemctl restart omnileads-gunicorn
    ok "Servicio omnileads-gunicorn reiniciado"
    RELOADED=true
fi

if [ "$RELOADED" = false ]; then
    warn "No se detectó el servicio automáticamente."
    warn "Recarga manualmente:  echo r > $FIFO"
    warn "O bien:               systemctl restart <nombre-del-servicio>"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  VERIFICACIÓN RÁPIDA
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
banner "Verificación:"

# Django check
if "$VENV_PY" manage.py check analyticspro -v 0 > /dev/null 2>&1; then
    ok "Django check analyticspro: OK"
else
    warn "Django check reportó advertencias — revisar manualmente"
fi

# Tablas en omnileads_local
TABLE_COUNT=$(PGPASSWORD="$ANALYTICS_DB_PASSWORD" psql \
    -h "$OML_PGHOST" -p "$OML_PGPORT" \
    -U analytics_user -d omnileads_local \
    -tAc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo "0")
ok "Tablas en omnileads_local: $TABLE_COUNT"

# Cron
CRON_COUNT=$(crontab -l 2>/dev/null | grep -c "sync_analytics" || echo "0")
ok "Entradas cron analyticspro: $CRON_COUNT"

# ═══════════════════════════════════════════════════════════════════════════════
#  FINALIZADO
# ═══════════════════════════════════════════════════════════════════════════════
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || hostname)
echo ""
echo -e "  ${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}${BOLD}║     ✅  Instalación completa         ║${NC}"
echo -e "  ${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "  🌐  ${BOLD}https://${SERVER_IP}/analyticspro/${NC}"
echo ""
echo "  Inicia sesión con un usuario Supervisor o Administrador de OmniLeads."
echo ""
echo -e "  ${CYAN}Comandos útiles:${NC}"
echo "  → Ver log de sync:  tail -f $SYNC_LOG"
echo "  → Sync manual:      $VENV_PY manage.py sync_analytics --once"
echo "  → Verificar cron:   crontab -l | grep analyticspro"
echo ""

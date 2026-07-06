#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
#  AnalyticsPro VOML — Actualizador
#  Uso: bash analyticspro_build/update.sh
#  Ejecutar en un servidor OmniLeads (SSH como root) donde analyticspro
#  YA está instalado. Trae el código más reciente de la rama VOML,
#  lo copia al módulo desplegado, corre collectstatic y recarga el
#  servidor de aplicaciones. No toca la BD ni pide contraseñas.
# ═══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
OML_HOME=/opt/omnileads/ominicontacto
VENV_PY=/opt/omnileads/virtualenv/bin/python
DEST_DIR=$OML_HOME/analyticspro
FIFO=/opt/omnileads/run/.uwsgi-fifo
TOTAL_STEPS=4

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

banner()  { echo -e "${CYAN}${BOLD}$*${NC}"; }
info()    { echo -e "  ${CYAN}→${NC} $*"; }
ok()      { echo -e "    ${GREEN}✓${NC} $*"; }
warn()    { echo -e "    ${YELLOW}⚠${NC}  $*"; }
fail()    { echo -e "    ${RED}✗ ERROR:${NC} $*" >&2; exit 1; }
step()    { echo ""; echo -e "  ${BOLD}[$1/${TOTAL_STEPS}]${NC} ${BOLD}$2${NC}"; }

echo ""
echo -e "${CYAN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║   AnalyticsPro — Actualizador VOML   ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

if [ ! -d "$DEST_DIR" ]; then
    fail "No se encontró $DEST_DIR — este servidor no tiene analyticspro instalado.\n  Usa install.sh en lugar de update.sh."
fi

if [ ! -f "$VENV_PY" ]; then
    fail "No se encontró el virtualenv en $VENV_PY"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 1 — Actualizar el repo local (git pull)
# ═══════════════════════════════════════════════════════════════════════════════
step 1 "Actualizando repo ($REPO_DIR)"

cd "$REPO_DIR"
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo '?')"
if [ "$CURRENT_BRANCH" != "VOML" ]; then
    warn "El repo está en la rama '$CURRENT_BRANCH', no en VOML. Continuando de todas formas."
fi

BEFORE="$(git rev-parse HEAD 2>/dev/null || echo '?')"
git pull origin "$CURRENT_BRANCH" 2>&1 | sed 's/^/      /'
AFTER="$(git rev-parse HEAD 2>/dev/null || echo '?')"

if [ "$BEFORE" = "$AFTER" ]; then
    ok "Ya estaba al día ($AFTER)"
else
    ok "Actualizado: $BEFORE → $AFTER"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 2 — Copiar módulo actualizado
# ═══════════════════════════════════════════════════════════════════════════════
step 2 "Copiando módulo a $DEST_DIR"

rsync -a --exclude='install.sh' --exclude='update.sh' --exclude='_*.py' \
      "$SCRIPT_DIR/" "$DEST_DIR/" 2>/dev/null || \
{
    cp -r "$SCRIPT_DIR/." "$DEST_DIR/"
    rm -f "$DEST_DIR/install.sh" "$DEST_DIR/update.sh" "$DEST_DIR"/_*.py 2>/dev/null || true
}
chown -R root:root "$DEST_DIR"
ok "Módulo copiado"

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 3 — Collectstatic + Django check
# ═══════════════════════════════════════════════════════════════════════════════
step 3 "Collectstatic y verificación Django"

cd "$OML_HOME"
"$VENV_PY" manage.py collectstatic --noinput -v 0 2>&1 | tail -3 || fail "collectstatic falló"
ok "Collectstatic completado"

if "$VENV_PY" manage.py check analyticspro -v 0 > /dev/null 2>&1; then
    ok "Django check analyticspro: OK"
else
    fail "Django check reportó errores — revisar antes de continuar"
fi

# ═══════════════════════════════════════════════════════════════════════════════
#  PASO 4 — Recargar servidor de aplicaciones
# ═══════════════════════════════════════════════════════════════════════════════
step 4 "Recargando servidor de aplicaciones"

RELOADED=false

if systemctl is-active --quiet omnileads 2>/dev/null; then
    systemctl restart omnileads
    ok "Servicio omnileads reiniciado"
    RELOADED=true
fi

if [ "$RELOADED" = false ] && [ -p "$FIFO" ]; then
    echo r > "$FIFO"
    sleep 2
    ok "uWSGI recargado vía FIFO ($FIFO)"
    RELOADED=true
fi

if [ "$RELOADED" = false ] && systemctl is-active --quiet omnileads-uwsgi 2>/dev/null; then
    systemctl restart omnileads-uwsgi
    ok "Servicio omnileads-uwsgi reiniciado"
    RELOADED=true
fi

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

echo ""
echo -e "  ${GREEN}${BOLD}╔══════════════════════════════════════╗${NC}"
echo -e "  ${GREEN}${BOLD}║     ✅  Actualización completa       ║${NC}"
echo -e "  ${GREEN}${BOLD}╚══════════════════════════════════════╝${NC}"
echo ""

#!/bin/bash
#
# Script de migración de timezone GMT-5 → GMT-6
# OmniLeads Analytics Pro
# Fecha: 2026-01-17
#

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Banner
echo "================================================================================"
echo "  OMNILEADS ANALYTICS - MIGRACIÓN DE TIMEZONE GMT-5 → GMT-6"
echo "================================================================================"
echo ""

# Parsear argumentos
ENVIRONMENT="development"
SKIP_BACKUP=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        -h|--help)
            echo "Uso: $0 [opciones]"
            echo ""
            echo "Opciones:"
            echo "  -e, --environment <env>   Ambiente: development o production (default: development)"
            echo "  --skip-backup             No crear backups antes de aplicar cambios"
            echo "  --force                   No pedir confirmación"
            echo "  -h, --help                Mostrar esta ayuda"
            echo ""
            echo "Ejemplos:"
            echo "  $0 --environment development"
            echo "  $0 --environment production --force"
            exit 0
            ;;
        *)
            echo -e "${RED}Error: Argumento desconocido: $1${NC}"
            exit 1
            ;;
    esac
done

# Validar ambiente
if [[ "$ENVIRONMENT" != "development" && "$ENVIRONMENT" != "production" ]]; then
    echo -e "${RED}Error: Ambiente debe ser 'development' o 'production'${NC}"
    exit 1
fi

# Determinar archivo de docker-compose
if [ "$ENVIRONMENT" == "production" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    ENV_NAME="PRODUCCIÓN"
else
    COMPOSE_FILE="docker-compose.dev.yml"
    ENV_NAME="DESARROLLO"
fi

echo -e "${BLUE}Ambiente seleccionado: ${ENV_NAME}${NC}"
echo -e "${BLUE}Archivo Docker Compose: ${COMPOSE_FILE}${NC}"
echo ""

# Verificar que el archivo compose existe
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: No se encontró el archivo $COMPOSE_FILE${NC}"
    exit 1
fi

# Verificar que .env existe
if [ ! -f ".env" ]; then
    echo -e "${RED}Error: No se encontró el archivo .env${NC}"
    exit 1
fi

# Confirmación si no es force
if [ "$FORCE" = false ]; then
    echo -e "${YELLOW}⚠️  Este script va a:${NC}"
    echo "  1. Crear backups de archivos (a menos que uses --skip-backup)"
    echo "  2. Verificar configuración de TIMEZONE_OFFSET en .env"
    echo "  3. Verificar que docker-compose.yml tiene la variable"
    echo "  4. Reiniciar los contenedores Docker"
    echo ""
    read -p "¿Deseas continuar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Cancelado por el usuario${NC}"
        exit 0
    fi
fi

echo ""
echo "================================================================================"
echo "PASO 1: VERIFICACIÓN DE CAMBIOS"
echo "================================================================================"
echo ""

# Verificar .env tiene TIMEZONE_OFFSET
if grep -q "TIMEZONE_OFFSET=" .env; then
    CURRENT_OFFSET=$(grep "TIMEZONE_OFFSET=" .env | cut -d'=' -f2)
    echo -e "${GREEN}✓${NC} .env tiene TIMEZONE_OFFSET configurado: ${CURRENT_OFFSET}"
else
    echo -e "${RED}✗${NC} .env no tiene TIMEZONE_OFFSET configurado"
    echo ""
    echo -e "${YELLOW}Por favor agrega esta línea al archivo .env:${NC}"
    echo "TIMEZONE_OFFSET=-6"
    echo ""
    exit 1
fi

# Verificar docker-compose tiene la variable
if grep -q "TIMEZONE_OFFSET=" "$COMPOSE_FILE"; then
    echo -e "${GREEN}✓${NC} $COMPOSE_FILE tiene TIMEZONE_OFFSET en environment"
else
    echo -e "${RED}✗${NC} $COMPOSE_FILE no tiene TIMEZONE_OFFSET configurado"
    echo ""
    echo -e "${YELLOW}Por favor agrega esta línea a la sección backend.environment en $COMPOSE_FILE:${NC}"
    echo "      - TIMEZONE_OFFSET=\${TIMEZONE_OFFSET:--6}"
    echo ""
    exit 1
fi

# Verificar backend/analytics/config.py
if grep -q "TIMEZONE_OFFSET = int(os.getenv" "backend/analytics/config.py"; then
    echo -e "${GREEN}✓${NC} backend/analytics/config.py tiene TIMEZONE_OFFSET"
else
    echo -e "${RED}✗${NC} backend/analytics/config.py no está actualizado"
    echo ""
    echo -e "${YELLOW}Por favor revisa el archivo TIMEZONE_MIGRATION.md para aplicar los cambios${NC}"
    exit 1
fi

# Verificar backend/analytics/services/call_analytics.py
if grep -q "from ..config import config" "backend/analytics/services/call_analytics.py"; then
    echo -e "${GREEN}✓${NC} call_analytics.py importa config"
else
    echo -e "${YELLOW}⚠${NC}  call_analytics.py puede necesitar actualizaciones"
fi

# Verificar backend/analytics/services/agent_analytics.py
if grep -q "from ..config import config" "backend/analytics/services/agent_analytics.py"; then
    echo -e "${GREEN}✓${NC} agent_analytics.py importa config"
else
    echo -e "${YELLOW}⚠${NC}  agent_analytics.py puede necesitar actualizaciones"
fi

echo ""
echo "================================================================================"
echo "PASO 2: BACKUP DE CONFIGURACIÓN"
echo "================================================================================"
echo ""

if [ "$SKIP_BACKUP" = false ]; then
    BACKUP_DIR="backups/timezone_migration_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"

    echo "Creando backups en: $BACKUP_DIR"

    cp .env "$BACKUP_DIR/.env.backup"
    echo -e "${GREEN}✓${NC} .env"

    cp "$COMPOSE_FILE" "$BACKUP_DIR/$COMPOSE_FILE.backup"
    echo -e "${GREEN}✓${NC} $COMPOSE_FILE"

    echo ""
    echo -e "${GREEN}Backups creados exitosamente${NC}"
else
    echo -e "${YELLOW}Omitiendo creación de backups (--skip-backup)${NC}"
fi

echo ""
echo "================================================================================"
echo "PASO 3: REINICIAR CONTENEDORES DOCKER"
echo "================================================================================"
echo ""

echo "Deteniendo contenedores..."
docker-compose -f "$COMPOSE_FILE" down

echo ""
echo "Levantando contenedores con nueva configuración..."
docker-compose -f "$COMPOSE_FILE" up -d

echo ""
echo "Esperando que los contenedores inicien (10 segundos)..."
sleep 10

echo ""
echo "================================================================================"
echo "PASO 4: VERIFICACIÓN POST-MIGRACIÓN"
echo "================================================================================"
echo ""

# Obtener nombre del contenedor backend
BACKEND_CONTAINER=$(docker-compose -f "$COMPOSE_FILE" ps -q backend 2>/dev/null)

if [ -z "$BACKEND_CONTAINER" ]; then
    echo -e "${RED}✗${NC} No se pudo encontrar el contenedor backend"
    echo ""
    echo "Ejecuta: docker-compose -f $COMPOSE_FILE ps"
    exit 1
fi

BACKEND_NAME=$(docker ps --filter "id=$BACKEND_CONTAINER" --format "{{.Names}}")

echo "Contenedor backend: $BACKEND_NAME"
echo ""

# Verificar variable de entorno
echo "Verificando TIMEZONE_OFFSET en el contenedor..."
CONTAINER_TZ=$(docker exec "$BACKEND_NAME" env | grep TIMEZONE_OFFSET | cut -d'=' -f2)

if [ "$CONTAINER_TZ" == "-6" ]; then
    echo -e "${GREEN}✓${NC} TIMEZONE_OFFSET configurado correctamente: $CONTAINER_TZ"
else
    echo -e "${RED}✗${NC} TIMEZONE_OFFSET no está configurado o tiene valor incorrecto: $CONTAINER_TZ"
    exit 1
fi

# Verificar que el módulo de config carga correctamente
echo ""
echo "Verificando módulo de configuración..."
VERIFY_OUTPUT=$(docker exec "$BACKEND_NAME" python -c "
from analytics.config import config
print(f'Timezone: {config.get_timezone()}')
print(f'Offset: {config.TIMEZONE_OFFSET}')
" 2>&1)

if [[ $VERIFY_OUTPUT == *"UTC-06:00"* ]]; then
    echo -e "${GREEN}✓${NC} Módulo de configuración funciona correctamente"
    echo "$VERIFY_OUTPUT"
else
    echo -e "${RED}✗${NC} Problema con el módulo de configuración"
    echo "$VERIFY_OUTPUT"
    exit 1
fi

# Verificar API (si está disponible)
echo ""
echo "Verificando API..."
BACKEND_PORT=$(grep "BACKEND_PORT" .env | cut -d'=' -f2)
BACKEND_PORT=${BACKEND_PORT:-8000}

sleep 2  # Esperar que la API esté lista

API_RESPONSE=$(curl -s "http://localhost:$BACKEND_PORT/api/health" 2>&1)

if [[ $API_RESPONSE == *"healthy"* ]]; then
    echo -e "${GREEN}✓${NC} API está respondiendo correctamente"
else
    echo -e "${YELLOW}⚠${NC}  No se pudo verificar la API (puede estar iniciando aún)"
fi

echo ""
echo "================================================================================"
echo "✅ MIGRACIÓN COMPLETADA EXITOSAMENTE"
echo "================================================================================"
echo ""
echo -e "${GREEN}La zona horaria ha sido configurada a GMT-6${NC}"
echo ""
echo "Próximos pasos:"
echo "  1. Verifica que los reportes muestren las horas correctas"
echo "  2. Compara timestamps con la base de datos (deberían ser 1 hora menos)"
echo "  3. Revisa los logs para asegurar que no hay errores"
echo ""
echo "Comandos útiles:"
echo "  # Ver logs del backend"
echo "  docker logs $BACKEND_NAME --tail 50 -f"
echo ""
echo "  # Probar endpoint de llamadas"
echo "  curl -s \"http://localhost:$BACKEND_PORT/api/analytics/llamadas-atendidas?page=1&per_page=1\""
echo ""
echo "  # Rollback (si algo sale mal)"
if [ "$SKIP_BACKUP" = false ]; then
    echo "  cp $BACKUP_DIR/.env .env"
    echo "  cp $BACKUP_DIR/$COMPOSE_FILE.backup $COMPOSE_FILE"
    echo "  docker-compose -f $COMPOSE_FILE down && docker-compose -f $COMPOSE_FILE up -d"
fi
echo ""
echo "================================================================================"

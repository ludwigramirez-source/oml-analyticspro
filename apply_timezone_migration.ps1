# Script de migración de timezone GMT-5 → GMT-6
# OmniLeads Analytics Pro
# Fecha: 2026-01-17

param(
    [string]$Environment = "development",
    [switch]$SkipBackup = $false,
    [switch]$Force = $false,
    [switch]$Help = $false
)

# Colores
function Write-Success { Write-Host $args -ForegroundColor Green }
function Write-Error { Write-Host $args -ForegroundColor Red }
function Write-Warning { Write-Host $args -ForegroundColor Yellow }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

# Banner
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  OMNILEADS ANALYTICS - MIGRACIÓN DE TIMEZONE GMT-5 → GMT-6" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Help
if ($Help) {
    Write-Host "Uso: .\apply_timezone_migration.ps1 [opciones]"
    Write-Host ""
    Write-Host "Opciones:"
    Write-Host "  -Environment <env>   Ambiente: development o production (default: development)"
    Write-Host "  -SkipBackup          No crear backups antes de aplicar cambios"
    Write-Host "  -Force               No pedir confirmación"
    Write-Host "  -Help                Mostrar esta ayuda"
    Write-Host ""
    Write-Host "Ejemplos:"
    Write-Host "  .\apply_timezone_migration.ps1 -Environment development"
    Write-Host "  .\apply_timezone_migration.ps1 -Environment production -Force"
    exit 0
}

# Validar ambiente
if ($Environment -ne "development" -and $Environment -ne "production") {
    Write-Error "Error: Ambiente debe ser 'development' o 'production'"
    exit 1
}

# Determinar archivo de docker-compose
if ($Environment -eq "production") {
    $ComposeFile = "docker-compose.prod.yml"
    $EnvName = "PRODUCCIÓN"
} else {
    $ComposeFile = "docker-compose.dev.yml"
    $EnvName = "DESARROLLO"
}

Write-Info "Ambiente seleccionado: $EnvName"
Write-Info "Archivo Docker Compose: $ComposeFile"
Write-Host ""

# Verificar que el archivo compose existe
if (-not (Test-Path $ComposeFile)) {
    Write-Error "Error: No se encontró el archivo $ComposeFile"
    exit 1
}

# Verificar que .env existe
if (-not (Test-Path ".env")) {
    Write-Error "Error: No se encontró el archivo .env"
    exit 1
}

# Confirmación si no es force
if (-not $Force) {
    Write-Warning "⚠️  Este script va a:"
    Write-Host "  1. Crear backups de archivos (a menos que uses -SkipBackup)"
    Write-Host "  2. Verificar configuración de TIMEZONE_OFFSET en .env"
    Write-Host "  3. Verificar que docker-compose.yml tiene la variable"
    Write-Host "  4. Reiniciar los contenedores Docker"
    Write-Host ""
    $response = Read-Host "¿Deseas continuar? (y/N)"
    if ($response -notmatch "^[Yy]$") {
        Write-Warning "Cancelado por el usuario"
        exit 0
    }
}

Write-Host ""
Write-Host "================================================================================"
Write-Host "PASO 1: VERIFICACIÓN DE CAMBIOS"
Write-Host "================================================================================"
Write-Host ""

# Verificar .env tiene TIMEZONE_OFFSET
$envContent = Get-Content ".env" -Raw
if ($envContent -match "TIMEZONE_OFFSET=") {
    $currentOffset = ($envContent -split "`n" | Where-Object { $_ -match "TIMEZONE_OFFSET=" } | Select-Object -First 1).Split("=")[1].Trim()
    Write-Success "✓ .env tiene TIMEZONE_OFFSET configurado: $currentOffset"
} else {
    Write-Error "✗ .env no tiene TIMEZONE_OFFSET configurado"
    Write-Host ""
    Write-Warning "Por favor agrega esta línea al archivo .env:"
    Write-Host "TIMEZONE_OFFSET=-6"
    Write-Host ""
    exit 1
}

# Verificar docker-compose tiene la variable
$composeContent = Get-Content $ComposeFile -Raw
if ($composeContent -match "TIMEZONE_OFFSET=") {
    Write-Success "✓ $ComposeFile tiene TIMEZONE_OFFSET en environment"
} else {
    Write-Error "✗ $ComposeFile no tiene TIMEZONE_OFFSET configurado"
    Write-Host ""
    Write-Warning "Por favor agrega esta línea a la sección backend.environment en ${ComposeFile}:"
    Write-Host "      - TIMEZONE_OFFSET=`${TIMEZONE_OFFSET:--6}"
    Write-Host ""
    exit 1
}

# Verificar backend/analytics/config.py
$configContent = Get-Content "backend\analytics\config.py" -Raw -ErrorAction SilentlyContinue
if ($configContent -match "TIMEZONE_OFFSET = int\(os.getenv") {
    Write-Success "✓ backend/analytics/config.py tiene TIMEZONE_OFFSET"
} else {
    Write-Error "✗ backend/analytics/config.py no está actualizado"
    Write-Host ""
    Write-Warning "Por favor revisa el archivo TIMEZONE_MIGRATION.md para aplicar los cambios"
    exit 1
}

# Verificar backend/analytics/services/call_analytics.py
$callAnalyticsContent = Get-Content "backend\analytics\services\call_analytics.py" -Raw -ErrorAction SilentlyContinue
if ($callAnalyticsContent -match "from \.\.config import config") {
    Write-Success "✓ call_analytics.py importa config"
} else {
    Write-Warning "⚠ call_analytics.py puede necesitar actualizaciones"
}

# Verificar backend/analytics/services/agent_analytics.py
$agentAnalyticsContent = Get-Content "backend\analytics\services\agent_analytics.py" -Raw -ErrorAction SilentlyContinue
if ($agentAnalyticsContent -match "from \.\.config import config") {
    Write-Success "✓ agent_analytics.py importa config"
} else {
    Write-Warning "⚠ agent_analytics.py puede necesitar actualizaciones"
}

Write-Host ""
Write-Host "================================================================================"
Write-Host "PASO 2: BACKUP DE CONFIGURACIÓN"
Write-Host "================================================================================"
Write-Host ""

if (-not $SkipBackup) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backupDir = "backups\timezone_migration_$timestamp"
    New-Item -ItemType Directory -Path $backupDir -Force | Out-Null

    Write-Host "Creando backups en: $backupDir"

    Copy-Item ".env" "$backupDir\.env.backup"
    Write-Success "✓ .env"

    Copy-Item $ComposeFile "$backupDir\$ComposeFile.backup"
    Write-Success "✓ $ComposeFile"

    Write-Host ""
    Write-Success "Backups creados exitosamente"
} else {
    Write-Warning "Omitiendo creación de backups (-SkipBackup)"
}

Write-Host ""
Write-Host "================================================================================"
Write-Host "PASO 3: REINICIAR CONTENEDORES DOCKER"
Write-Host "================================================================================"
Write-Host ""

Write-Host "Deteniendo contenedores..."
docker-compose -f $ComposeFile down

Write-Host ""
Write-Host "Levantando contenedores con nueva configuración..."
docker-compose -f $ComposeFile up -d

Write-Host ""
Write-Host "Esperando que los contenedores inicien (10 segundos)..."
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "================================================================================"
Write-Host "PASO 4: VERIFICACIÓN POST-MIGRACIÓN"
Write-Host "================================================================================"
Write-Host ""

# Obtener contenedores
$backendContainer = docker-compose -f $ComposeFile ps -q backend 2>$null

if (-not $backendContainer) {
    Write-Error "✗ No se pudo encontrar el contenedor backend"
    Write-Host ""
    Write-Host "Ejecuta: docker-compose -f $ComposeFile ps"
    exit 1
}

$backendName = (docker ps --filter "id=$backendContainer" --format "{{.Names}}").Trim()

Write-Host "Contenedor backend: $backendName"
Write-Host ""

# Verificar variable de entorno
Write-Host "Verificando TIMEZONE_OFFSET en el contenedor..."
$containerTz = (docker exec $backendName env | Select-String "TIMEZONE_OFFSET").ToString().Split("=")[1].Trim()

if ($containerTz -eq "-6") {
    Write-Success "✓ TIMEZONE_OFFSET configurado correctamente: $containerTz"
} else {
    Write-Error "✗ TIMEZONE_OFFSET no está configurado o tiene valor incorrecto: $containerTz"
    exit 1
}

# Verificar que el módulo de config carga correctamente
Write-Host ""
Write-Host "Verificando módulo de configuración..."
$verifyScript = @"
from analytics.config import config
print(f'Timezone: {config.get_timezone()}')
print(f'Offset: {config.TIMEZONE_OFFSET}')
"@

$verifyOutput = docker exec $backendName python -c $verifyScript 2>&1

if ($verifyOutput -match "UTC-06:00") {
    Write-Success "✓ Módulo de configuración funciona correctamente"
    Write-Host $verifyOutput
} else {
    Write-Error "✗ Problema con el módulo de configuración"
    Write-Host $verifyOutput
    exit 1
}

# Verificar API (si está disponible)
Write-Host ""
Write-Host "Verificando API..."
$backendPort = ($envContent -split "`n" | Where-Object { $_ -match "BACKEND_PORT=" } | Select-Object -First 1).Split("=")[1].Trim()
if (-not $backendPort) { $backendPort = "8000" }

Start-Sleep -Seconds 2  # Esperar que la API esté lista

try {
    $apiResponse = Invoke-RestMethod -Uri "http://localhost:$backendPort/api/health" -TimeoutSec 5 -ErrorAction Stop
    if ($apiResponse.status -eq "healthy") {
        Write-Success "✓ API está respondiendo correctamente"
    }
} catch {
    Write-Warning "⚠ No se pudo verificar la API (puede estar iniciando aún)"
}

Write-Host ""
Write-Host "================================================================================"
Write-Host "✅ MIGRACIÓN COMPLETADA EXITOSAMENTE" -ForegroundColor Green
Write-Host "================================================================================"
Write-Host ""
Write-Success "La zona horaria ha sido configurada a GMT-6"
Write-Host ""
Write-Host "Próximos pasos:"
Write-Host "  1. Verifica que los reportes muestren las horas correctas"
Write-Host "  2. Compara timestamps con la base de datos (deberían ser 1 hora menos)"
Write-Host "  3. Revisa los logs para asegurar que no hay errores"
Write-Host ""
Write-Host "Comandos útiles:"
Write-Host "  # Ver logs del backend"
Write-Host "  docker logs $backendName --tail 50 -f"
Write-Host ""
Write-Host "  # Probar endpoint de llamadas"
Write-Host "  curl -s `"http://localhost:$backendPort/api/analytics/llamadas-atendidas?page=1&per_page=1`""
Write-Host ""
if (-not $SkipBackup) {
    Write-Host "  # Rollback (si algo sale mal)"
    Write-Host "  Copy-Item $backupDir\.env.backup .env -Force"
    Write-Host "  Copy-Item $backupDir\$ComposeFile.backup $ComposeFile -Force"
    Write-Host "  docker-compose -f $ComposeFile down; docker-compose -f $ComposeFile up -d"
}
Write-Host ""
Write-Host "================================================================================"

# Script simple para reiniciar contenedores Docker
# OmniLeads Analytics Pro

param(
    [string]$Environment = "development"
)

function Write-Info { Write-Host $args -ForegroundColor Cyan }
function Write-Success { Write-Host $args -ForegroundColor Green }

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  REINICIAR CONTENEDORES DOCKER - OMNILEADS ANALYTICS" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Determinar archivo de docker-compose
if ($Environment -eq "production") {
    $ComposeFile = "docker-compose.prod.yml"
    $EnvName = "PRODUCCIÓN"
} else {
    $ComposeFile = "docker-compose.dev.yml"
    $EnvName = "DESARROLLO"
}

Write-Info "Ambiente: $EnvName"
Write-Info "Archivo: $ComposeFile"
Write-Host ""

# Verificar que existe
if (-not (Test-Path $ComposeFile)) {
    Write-Host "Error: No se encontró $ComposeFile" -ForegroundColor Red
    exit 1
}

Write-Host "1. Deteniendo contenedores..." -ForegroundColor Yellow
docker-compose -f $ComposeFile down

Write-Host ""
Write-Host "2. Levantando contenedores..." -ForegroundColor Yellow
docker-compose -f $ComposeFile up -d

Write-Host ""
Write-Host "3. Esperando inicio (10 segundos)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host ""
Write-Host "4. Estado de contenedores:" -ForegroundColor Yellow
docker-compose -f $ComposeFile ps

Write-Host ""
Write-Success "✓ Contenedores reiniciados"
Write-Host ""
Write-Host "Ver logs: docker-compose -f $ComposeFile logs -f"
Write-Host ""

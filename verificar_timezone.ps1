# Script de verificación rápida de timezone
# OmniLeads Analytics Pro

param(
    [string]$Environment = "development"
)

function Write-Success { Write-Host "✓" -ForegroundColor Green -NoNewline; Write-Host " $args" }
function Write-Error { Write-Host "✗" -ForegroundColor Red -NoNewline; Write-Host " $args" }
function Write-Info { Write-Host $args -ForegroundColor Cyan }

Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "  VERIFICACIÓN DE CONFIGURACIÓN DE TIMEZONE" -ForegroundColor Cyan
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

# Determinar archivo compose
$ComposeFile = if ($Environment -eq "production") { "docker-compose.prod.yml" } else { "docker-compose.dev.yml" }

Write-Info "Ambiente: $Environment"
Write-Info "Archivo Docker Compose: $ComposeFile"
Write-Host ""

Write-Host "VERIFICACIÓN DE ARCHIVOS:" -ForegroundColor Yellow
Write-Host "=========================" -ForegroundColor Yellow
Write-Host ""

# 1. Verificar .env
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "TIMEZONE_OFFSET=-6") {
        Write-Success ".env tiene TIMEZONE_OFFSET=-6"
    } elseif ($envContent -match "TIMEZONE_OFFSET=") {
        $offset = ($envContent -split "`n" | Where-Object { $_ -match "TIMEZONE_OFFSET=" } | Select-Object -First 1).Split("=")[1].Trim()
        Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
        Write-Host ".env tiene TIMEZONE_OFFSET=$offset (esperado: -6)"
    } else {
        Write-Error ".env NO tiene TIMEZONE_OFFSET configurado"
    }
} else {
    Write-Error ".env no existe"
}

# 2. Verificar docker-compose
if (Test-Path $ComposeFile) {
    $composeContent = Get-Content $ComposeFile -Raw
    if ($composeContent -match "TIMEZONE_OFFSET=") {
        Write-Success "$ComposeFile tiene TIMEZONE_OFFSET en environment"
    } else {
        Write-Error "$ComposeFile NO tiene TIMEZONE_OFFSET configurado"
    }
} else {
    Write-Error "$ComposeFile no existe"
}

# 3. Verificar config.py
if (Test-Path "backend\analytics\config.py") {
    $configContent = Get-Content "backend\analytics\config.py" -Raw
    if ($configContent -match "TIMEZONE_OFFSET = int\(os.getenv" -and $configContent -match "def get_timezone") {
        Write-Success "backend/analytics/config.py está actualizado"
    } else {
        Write-Error "backend/analytics/config.py NO está actualizado"
    }
} else {
    Write-Error "backend/analytics/config.py no existe"
}

# 4. Verificar call_analytics.py
if (Test-Path "backend\analytics\services\call_analytics.py") {
    $callContent = Get-Content "backend\analytics\services\call_analytics.py" -Raw
    if ($callContent -match "from \.\.config import config" -and $callContent -match "local_tz = config\.get_timezone\(\)") {
        Write-Success "backend/analytics/services/call_analytics.py está actualizado"
    } else {
        Write-Error "backend/analytics/services/call_analytics.py NO está actualizado"
    }
} else {
    Write-Error "backend/analytics/services/call_analytics.py no existe"
}

# 5. Verificar agent_analytics.py
if (Test-Path "backend\analytics\services\agent_analytics.py") {
    $agentContent = Get-Content "backend\analytics\services\agent_analytics.py" -Raw
    if ($agentContent -match "from \.\.config import config") {
        Write-Success "backend/analytics/services/agent_analytics.py está actualizado"
    } else {
        Write-Error "backend/analytics/services/agent_analytics.py NO está actualizado"
    }
} else {
    Write-Error "backend/analytics/services/agent_analytics.py no existe"
}

Write-Host ""
Write-Host "VERIFICACIÓN DE CONTENEDORES:" -ForegroundColor Yellow
Write-Host "=============================" -ForegroundColor Yellow
Write-Host ""

# Verificar si Docker está corriendo
try {
    $dockerRunning = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker está corriendo"

        # Obtener contenedor backend
        $backendContainer = docker-compose -f $ComposeFile ps -q backend 2>$null

        if ($backendContainer) {
            $backendName = (docker ps --filter "id=$backendContainer" --format "{{.Names}}").Trim()
            Write-Success "Contenedor backend encontrado: $backendName"

            # Verificar variable de entorno en contenedor
            $containerTz = (docker exec $backendName env | Select-String "TIMEZONE_OFFSET").ToString().Split("=")[1].Trim()
            if ($containerTz -eq "-6") {
                Write-Success "TIMEZONE_OFFSET en contenedor: $containerTz"
            } else {
                Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
                Write-Host "TIMEZONE_OFFSET en contenedor: $containerTz (esperado: -6)"
            }

            # Verificar módulo de Python
            try {
                $pythonCheck = docker exec $backendName python -c "from analytics.config import config; print(config.TIMEZONE_OFFSET)" 2>&1
                if ($pythonCheck.Trim() -eq "-6") {
                    Write-Success "Módulo Python config.TIMEZONE_OFFSET: $($pythonCheck.Trim())"
                } else {
                    Write-Host "⚠ " -ForegroundColor Yellow -NoNewline
                    Write-Host "Módulo Python config.TIMEZONE_OFFSET: $($pythonCheck.Trim()) (esperado: -6)"
                }
            } catch {
                Write-Error "No se pudo verificar el módulo Python"
            }

        } else {
            Write-Error "Contenedor backend no está corriendo"
            Write-Host "   Ejecuta: docker-compose -f $ComposeFile up -d"
        }

    } else {
        Write-Error "Docker no está corriendo"
    }
} catch {
    Write-Error "Error al conectar con Docker"
}

Write-Host ""
Write-Host "================================================================================"
Write-Host ""

# Resumen
$allOk = $true
if ((Get-Content ".env" -Raw) -notmatch "TIMEZONE_OFFSET=-6") { $allOk = $false }
if ((Get-Content $ComposeFile -Raw) -notmatch "TIMEZONE_OFFSET=") { $allOk = $false }
if ((Get-Content "backend\analytics\config.py" -Raw) -notmatch "def get_timezone") { $allOk = $false }

if ($allOk) {
    Write-Host "RESULTADO: " -NoNewline
    Write-Host "CONFIGURACIÓN CORRECTA ✓" -ForegroundColor Green
    Write-Host ""
    Write-Host "Los reportes deberían mostrar timestamps en GMT-6"
} else {
    Write-Host "RESULTADO: " -NoNewline
    Write-Host "SE REQUIEREN CAMBIOS ✗" -ForegroundColor Red
    Write-Host ""
    Write-Host "Revisa TIMEZONE_MIGRATION.md para aplicar los cambios faltantes"
}

Write-Host ""
Write-Host "Para más detalles, lee: TIMEZONE_MIGRATION.md"
Write-Host "================================================================================"
Write-Host ""

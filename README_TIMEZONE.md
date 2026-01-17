# 🕐 Migración de Timezone GMT-5 → GMT-6

## 📁 Archivos Creados

Se han generado los siguientes archivos para facilitar la migración:

| Archivo | Descripción | Tamaño |
|---------|-------------|--------|
| `TIMEZONE_MIGRATION.md` | 📖 **Documentación completa** con todos los cambios detallados | 21 KB |
| `apply_timezone_migration.ps1` | 🔧 Script PowerShell automatizado con verificaciones | 11 KB |
| `apply_timezone_migration.sh` | 🔧 Script Bash automatizado (Linux/Mac) | 10 KB |
| `restart_docker.ps1` | 🔄 Script simple para reiniciar contenedores | 2 KB |
| `verificar_timezone.ps1` | ✅ Script de verificación rápida | 7 KB |
| `ARCHIVOS_MIGRACION_TIMEZONE.txt` | 📋 Resumen de archivos y pasos | 5 KB |

---

## 🚀 Inicio Rápido

### Para Desarrollo (Ya aplicado ✓)
```powershell
# Los cambios ya están aplicados en desarrollo
# Solo verifica que funciona:
.\verificar_timezone.ps1
```

### Para Producción (Pendiente)

#### Opción 1: Migración Automática (Recomendada)
```powershell
# 1. Lee primero la documentación
Get-Content TIMEZONE_MIGRATION.md

# 2. Aplica los cambios de código manualmente (archivos .py)

# 3. Ejecuta el script automatizado
.\apply_timezone_migration.ps1 -Environment production
```

#### Opción 2: Migración Manual
```powershell
# 1. Lee y sigue TIMEZONE_MIGRATION.md paso a paso

# 2. Reinicia los contenedores
.\restart_docker.ps1 -Environment production

# 3. Verifica que funciona
.\verificar_timezone.ps1 -Environment production
```

---

## 📖 Documentación Detallada

### 1. TIMEZONE_MIGRATION.md
**LEE ESTE ARCHIVO PRIMERO**

Contiene:
- ✅ Explicación completa de todos los cambios
- ✅ Código ANTES y DESPUÉS de cada modificación
- ✅ Ubicación exacta de cada línea a modificar
- ✅ Instrucciones de verificación
- ✅ Procedimiento de rollback

### 2. Scripts de PowerShell

#### `apply_timezone_migration.ps1`
Script completo que:
- Verifica que todos los archivos están actualizados
- Crea backups automáticos
- Reinicia contenedores Docker
- Verifica que la configuración funciona

```powershell
# Desarrollo (con confirmación)
.\apply_timezone_migration.ps1 -Environment development

# Producción (sin confirmación)
.\apply_timezone_migration.ps1 -Environment production -Force

# Sin crear backups
.\apply_timezone_migration.ps1 -Environment production -SkipBackup

# Ver ayuda
.\apply_timezone_migration.ps1 -Help
```

#### `restart_docker.ps1`
Script simple para solo reiniciar contenedores:
```powershell
.\restart_docker.ps1 -Environment development
.\restart_docker.ps1 -Environment production
```

#### `verificar_timezone.ps1`
Verifica configuración sin hacer cambios:
```powershell
.\verificar_timezone.ps1 -Environment development
.\verificar_timezone.ps1 -Environment production
```

---

## 🔍 ¿Qué Cambió?

### Cambio Principal
**GMT-5** (Colombia, Perú) → **GMT-6** (Nicaragua, Costa Rica, El Salvador)

Todos los timestamps en reportes mostrarán **1 hora menos**.

### Archivos Modificados
1. `.env` - Variable `TIMEZONE_OFFSET=-6`
2. `backend/analytics/config.py` - Configuración centralizada
3. `backend/analytics/services/call_analytics.py` - Conversión de timestamps
4. `backend/analytics/services/agent_analytics.py` - Conversión de timestamps
5. `docker-compose.dev.yml` - Variable de entorno
6. `docker-compose.prod.yml` - Variable de entorno (pendiente)

### ¿Qué NO cambió?
- ✅ Los datos en la base de datos NO cambian
- ✅ Los filtros por fecha siguen funcionando igual
- ✅ La conversión es en tiempo real al consultar

---

## ✅ Verificación

### Verificar en Desarrollo
```powershell
# 1. Verificar archivos y contenedores
.\verificar_timezone.ps1

# 2. Probar API
curl "http://localhost:8000/api/analytics/llamadas-atendidas?page=1&per_page=1"

# 3. Comparar con base de datos
# Las horas en la API deberían ser 1 hora menos que en la BD
```

### Verificar Variable en Contenedor
```powershell
# Ver variable de entorno
docker exec oml-backend-dev env | findstr TIMEZONE

# Debería mostrar: TIMEZONE_OFFSET=-6
```

### Verificar en Base de Datos
```sql
-- Conectar a PostgreSQL
psql -h 192.168.15.104 -U analitycs_user -d omnileads

-- Comparar timestamps
SELECT
    id,
    time AS time_original,
    time AT TIME ZONE 'America/Managua' as time_gmt6
FROM reportes_app_llamadalog
ORDER BY time DESC
LIMIT 5;

-- time_gmt6 debería mostrar 1 hora menos que time_original
```

---

## 🔄 Rollback (En caso de problemas)

Si algo sale mal, los scripts crean backups automáticos:

```powershell
# Los backups se guardan en:
cd backups\timezone_migration_YYYYMMDD_HHMMSS

# Restaurar manualmente
Copy-Item backups\<timestamp>\.env.backup .env -Force
Copy-Item backups\<timestamp>\docker-compose.prod.yml.backup docker-compose.prod.yml -Force

# Reiniciar contenedores
.\restart_docker.ps1 -Environment production
```

---

## 📞 Soporte

### Problemas Comunes

**1. Los contenedores no inician**
```powershell
# Ver logs
docker-compose -f docker-compose.prod.yml logs -f backend

# Ver estado
docker-compose -f docker-compose.prod.yml ps
```

**2. La variable no está cargada**
```powershell
# Verificar .env
Get-Content .env | Select-String TIMEZONE

# Verificar docker-compose
Get-Content docker-compose.prod.yml | Select-String TIMEZONE

# Reiniciar contenedores
.\restart_docker.ps1 -Environment production
```

**3. La API no responde**
```powershell
# Esperar más tiempo (puede estar iniciando)
Start-Sleep -Seconds 30

# Ver logs
docker logs oml-backend-prod --tail 50 -f
```

### Contacto
Si los problemas persisten:
1. Revisa `TIMEZONE_MIGRATION.md` sección "Soporte"
2. Verifica los logs del backend
3. Ejecuta rollback si es necesario
4. Contacta al equipo de desarrollo

---

## 📊 Resumen Ejecutivo

| Aspecto | Detalle |
|---------|---------|
| **Cambio** | GMT-5 → GMT-6 (1 hora de diferencia) |
| **Impacto** | Todos los reportes muestran timestamps 1 hora menos |
| **Datos en BD** | NO cambian (solo la visualización) |
| **Reversible** | Sí, con rollback o cambiando `TIMEZONE_OFFSET` |
| **Configurable** | Sí, vía variable de entorno |
| **Tiempo estimado** | 15-30 minutos (migración manual completa) |
| **Riesgo** | Bajo (no afecta datos, solo visualización) |

---

**Última actualización**: 2026-01-17
**Estado**: Aplicado en desarrollo ✓ | Pendiente en producción
**Documentación completa**: TIMEZONE_MIGRATION.md

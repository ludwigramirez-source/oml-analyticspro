# Migración de Zona Horaria GMT-5 → GMT-6

**Fecha**: 2026-01-17
**Objetivo**: Configurar todos los reportes y timestamps para usar GMT-6 (América Central) en lugar de GMT-5

---

## Resumen de Cambios

Se ha implementado un sistema configurable de zona horaria que permite cambiar el offset GMT mediante una variable de entorno `TIMEZONE_OFFSET`. Esto afecta a todos los reportes de llamadas, agentes, sesiones y pausas.

**Cambio Principal**: GMT-5 → GMT-6 (1 hora de diferencia)

---

## Archivos Modificados

### 1. `.env` (Archivo de configuración principal)

**Ubicación**: `/oml-analyticspro/.env`

**Cambio a aplicar**: Agregar variable de timezone después de `LOG_LEVEL`

```env
# ============================================================================
# BACKEND CONFIGURATION
# ============================================================================
BACKEND_PORT=8000
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
LOG_LEVEL=DEBUG

# Timezone Configuration (GMT offset in hours, e.g., -6 for Central America)
TIMEZONE_OFFSET=-6
```

---

### 2. `backend/analytics/config.py` (Configuración del backend)

**Ubicación**: `/backend/analytics/config.py`

**Cambios**:

#### a) Agregar imports (línea 7)
```python
from datetime import timedelta, timezone
```

Resultado:
```python
"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import logging
import os
from datetime import timedelta, timezone  # ← AGREGAR
from pathlib import Path

from dotenv import load_dotenv
```

#### b) Agregar variable de configuración (después de línea 26)
```python
# Timezone Configuration (default GMT-6 for Central America)
TIMEZONE_OFFSET = int(os.getenv('TIMEZONE_OFFSET', '-6'))
```

Resultado:
```python
class OmniLeadsConfig:
    """Configuración de conexión a PostgreSQL OmniLeads"""

    # Configuración de PostgreSQL OmniLeads (READ-ONLY)
    OMNILEADS_DB_HOST = os.getenv('OMNILEADS_DB_HOST', 'localhost')
    OMNILEADS_DB_PORT = os.getenv('OMNILEADS_DB_PORT', '5432')
    OMNILEADS_DB_NAME = os.getenv('OMNILEADS_DB_NAME', 'omnileads')
    OMNILEADS_DB_USER = os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly')
    OMNILEADS_DB_PASSWORD = os.getenv('OMNILEADS_DB_PASSWORD', '')

    # Timezone Configuration (default GMT-6 for Central America)
    TIMEZONE_OFFSET = int(os.getenv('TIMEZONE_OFFSET', '-6'))  # ← AGREGAR
```

#### c) Agregar método helper (antes del final de la clase)
```python
@classmethod
def get_timezone(cls):
    """Retorna el timezone configurado basado en TIMEZONE_OFFSET"""
    return timezone(timedelta(hours=cls.TIMEZONE_OFFSET))
```

Resultado:
```python
    @classmethod
    def get_connection_params(cls) -> dict:
        """Retorna los parámetros de conexión como diccionario"""
        return {
            'host': cls.OMNILEADS_DB_HOST,
            'port': cls.OMNILEADS_DB_PORT,
            'database': cls.OMNILEADS_DB_NAME,
            'user': cls.OMNILEADS_DB_USER,
            'password': cls.OMNILEADS_DB_PASSWORD,
            'options': '-c default_transaction_read_only=on'  # READ-ONLY
        }

    @classmethod
    def get_timezone(cls):  # ← AGREGAR
        """Retorna el timezone configurado basado en TIMEZONE_OFFSET"""
        return timezone(timedelta(hours=cls.TIMEZONE_OFFSET))


# Instancia de configuración
config = OmniLeadsConfig()
```

---

### 3. `backend/analytics/services/call_analytics.py`

**Ubicación**: `/backend/analytics/services/call_analytics.py`

**Cambios a realizar**: Reemplazar hardcoded GMT-5 por timezone configurable

#### a) En función `get_llamadas_abandonadas()` (línea ~595-596)

**ANTES**:
```python
        Convierte timezone a GMT-5 (America/Bogota)
        """
        from datetime import timedelta
        from datetime import timezone as dt_timezone

        filters = filters or {}
```

**DESPUÉS**:
```python
        Convierte timezone según configuración (TIMEZONE_OFFSET)
        """
        from ..config import config

        filters = filters or {}
```

#### b) En función `get_llamadas_abandonadas()` (línea ~652-659)

**ANTES**:
```python
        # Timezone GMT-5 (America/Bogota)
        gmt_minus_5 = dt_timezone(timedelta(hours=-5))

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a GMT-5
            time_gmt5 = llamada.time.astimezone(gmt_minus_5)
```

**DESPUÉS**:
```python
        # Timezone configurado
        local_tz = config.get_timezone()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a timezone local
            time_local = llamada.time.astimezone(local_tz)
```

#### c) Reemplazar todas las referencias a `time_gmt5` por `time_local` en la misma función

**ANTES**:
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_gmt5.strftime('%Y-%m-%d'),
                'hora': time_gmt5.strftime('%H:%M:%S'),
```

**DESPUÉS**:
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_local.strftime('%Y-%m-%d'),
                'hora': time_local.strftime('%H:%M:%S'),
```

#### d) Repetir pasos a), b) y c) en función `get_llamadas_detalladas()` (línea ~690)

Mismos cambios exactos que en `get_llamadas_abandonadas()`.

---

### 4. `backend/analytics/services/agent_analytics.py`

**Ubicación**: `/backend/analytics/services/agent_analytics.py`

**Cambios**:

#### a) Agregar import al inicio (después de línea 9)

**ANTES**:
```python
from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from ..models.omnileads_models import (
```

**DESPUÉS**:
```python
from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from ..config import config  # ← AGREGAR
from ..models.omnileads_models import (
```

#### b) En función `get_timeline_agente()` (línea ~304-320)

**ANTES**:
```python
        # Construir timeline sin queries adicionales
        timeline = []
        for act in actividades:
            # Lookup O(1) desde diccionario pre-cargado
            pausa_nombre = pausas_dict.get(act.pausa_id) if act.pausa_id else None

            # Mapear evento a descripción
            evento_map = {
                'ADDMEMBER': 'Ingreso al sistema',
                'REMOVEMEMBER': 'Salida del sistema',
                'PAUSEALL': f'En pausa: {pausa_nombre or "Sin especificar"}',
                'UNPAUSEALL': 'Fin de pausa'
            }

            timeline.append({
                'tiempo': act.time.strftime('%H:%M:%S'),
                'evento': evento_map.get(act.event, act.event),
                'tipo': act.event
            })
```

**DESPUÉS**:
```python
        # Construir timeline sin queries adicionales
        local_tz = config.get_timezone()  # ← AGREGAR
        timeline = []
        for act in actividades:
            # Lookup O(1) desde diccionario pre-cargado
            pausa_nombre = pausas_dict.get(act.pausa_id) if act.pausa_id else None

            # Mapear evento a descripción
            evento_map = {
                'ADDMEMBER': 'Ingreso al sistema',
                'REMOVEMEMBER': 'Salida del sistema',
                'PAUSEALL': f'En pausa: {pausa_nombre or "Sin especificar"}',
                'UNPAUSEALL': 'Fin de pausa'
            }

            # Convertir tiempo a timezone local
            time_local = act.time.astimezone(local_tz)  # ← AGREGAR

            timeline.append({
                'tiempo': time_local.strftime('%H:%M:%S'),  # ← CAMBIAR
                'evento': evento_map.get(act.event, act.event),
                'tipo': act.event
            })
```

#### c) En función `get_disponibilidad_agentes()` (línea ~567-580)

**ANTES**:
```python
            agentes_dict[agente_id].update({
                'llamadas_contestadas': metricas['llamadas_atendidas'],
                'num_sesiones': num_sesiones,
                'tiempo_total_sesion': int(tiempo_total_sesion),
                'tiempo_promedio_sesion': tiempo_promedio_sesion,
                'tiempo_al_habla': tiempo_al_habla,
                'num_pausas': num_pausas,
                'tiempo_pausa_recreativa': int(tiempo_pausas_recreativas),
                'tiempo_pausa_productiva': int(tiempo_pausas_productivas),
                'tiempo_total_pausa': int(tiempo_total_pausas),
                'tiempo_promedio_pausa': tiempo_promedio_pausa,
                'ocupacion': ocupacion,
                'primer_login': primer_login.strftime('%H:%M:%S') if primer_login else '-',
                'ultimo_logout': ultimo_logout.strftime('%H:%M:%S') if ultimo_logout else '-'
            })
```

**DESPUÉS**:
```python
            # Convertir timestamps a timezone local
            local_tz = config.get_timezone()  # ← AGREGAR
            primer_login_local = primer_login.astimezone(local_tz) if primer_login else None  # ← AGREGAR
            ultimo_logout_local = ultimo_logout.astimezone(local_tz) if ultimo_logout else None  # ← AGREGAR

            agentes_dict[agente_id].update({
                'llamadas_contestadas': metricas['llamadas_atendidas'],
                'num_sesiones': num_sesiones,
                'tiempo_total_sesion': int(tiempo_total_sesion),
                'tiempo_promedio_sesion': tiempo_promedio_sesion,
                'tiempo_al_habla': tiempo_al_habla,
                'num_pausas': num_pausas,
                'tiempo_pausa_recreativa': int(tiempo_pausas_recreativas),
                'tiempo_pausa_productiva': int(tiempo_pausas_productivas),
                'tiempo_total_pausa': int(tiempo_total_pausas),
                'tiempo_promedio_pausa': tiempo_promedio_pausa,
                'ocupacion': ocupacion,
                'primer_login': primer_login_local.strftime('%H:%M:%S') if primer_login_local else '-',  # ← CAMBIAR
                'ultimo_logout': ultimo_logout_local.strftime('%H:%M:%S') if ultimo_logout_local else '-'  # ← CAMBIAR
            })
```

#### d) En función `get_detalle_sesiones_agente()` (línea ~617-650)

**ANTES**:
```python
        sesiones = []
        tiempo_login = None
        sesiones_totales = 0
        sesiones_filtradas = 0

        for actividad in actividades:
```

**DESPUÉS**:
```python
        sesiones = []
        tiempo_login = None
        sesiones_totales = 0
        sesiones_filtradas = 0
        local_tz = config.get_timezone()  # ← AGREGAR

        for actividad in actividades:
```

**Y más adelante en la misma función**:

**ANTES**:
```python
                if incluir_sesion:
                    sesiones_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    sesiones.append({
                        'fecha_inicio': tiempo_login.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': actividad.time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

**DESPUÉS**:
```python
                if incluir_sesion:
                    sesiones_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    # Convertir timestamps a timezone local
                    tiempo_login_local = tiempo_login.astimezone(local_tz)  # ← AGREGAR
                    tiempo_logout_local = actividad.time.astimezone(local_tz)  # ← AGREGAR

                    sesiones.append({
                        'fecha_inicio': tiempo_login_local.strftime('%Y-%m-%d %H:%M:%S'),  # ← CAMBIAR
                        'fecha_fin': tiempo_logout_local.strftime('%Y-%m-%d %H:%M:%S'),  # ← CAMBIAR
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

#### e) En función `get_detalle_pausas_agente()` (línea ~700-740)

**ANTES**:
```python
        pausas = []
        tiempo_pausa_inicio = None
        pausa_id_actual = None
        pausas_totales = 0
        pausas_filtradas = 0

        for actividad in actividades:
```

**DESPUÉS**:
```python
        pausas = []
        tiempo_pausa_inicio = None
        pausa_id_actual = None
        pausas_totales = 0
        pausas_filtradas = 0
        local_tz = config.get_timezone()  # ← AGREGAR

        for actividad in actividades:
```

**Y más adelante**:

**ANTES**:
```python
                if incluir_pausa:
                    pausas_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    pausa_info = pausas_dict.get(pausa_id_actual, {'tipo': 'P', 'nombre': 'Otra'})

                    pausas.append({
                        'tipo': pausa_info['tipo'],
                        'nombre': pausa_info['nombre'],
                        'fecha_inicio': tiempo_pausa_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': actividad.time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

**DESPUÉS**:
```python
                if incluir_pausa:
                    pausas_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    pausa_info = pausas_dict.get(pausa_id_actual, {'tipo': 'P', 'nombre': 'Otra'})

                    # Convertir timestamps a timezone local
                    tiempo_pausa_inicio_local = tiempo_pausa_inicio.astimezone(local_tz)  # ← AGREGAR
                    tiempo_pausa_fin_local = actividad.time.astimezone(local_tz)  # ← AGREGAR

                    pausas.append({
                        'tipo': pausa_info['tipo'],
                        'nombre': pausa_info['nombre'],
                        'fecha_inicio': tiempo_pausa_inicio_local.strftime('%Y-%m-%d %H:%M:%S'),  # ← CAMBIAR
                        'fecha_fin': tiempo_pausa_fin_local.strftime('%Y-%m-%d %H:%M:%S'),  # ← CAMBIAR
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

---

### 5. `docker-compose.dev.yml` y `docker-compose.prod.yml`

**Ubicación**: `/docker-compose.dev.yml` y `/docker-compose.prod.yml`

**Cambio**: Agregar variable de entorno al servicio backend

#### En `docker-compose.dev.yml` (línea ~23):

**ANTES**:
```yaml
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - DB_NAME=${DB_NAME:-omnileads_analytics}
      - OMNILEADS_DB_HOST=${OMNILEADS_DB_HOST:-postgres-omnileads}
      - OMNILEADS_DB_PORT=${OMNILEADS_DB_PORT:-5432}
      - OMNILEADS_DB_USER=${OMNILEADS_DB_USER:-postgres}
      - OMNILEADS_DB_PASSWORD=${OMNILEADS_DB_PASSWORD:-postgres}
      - OMNILEADS_DB_NAME=${OMNILEADS_DB_NAME:-omnileads}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-key-change-in-production}
      - LOG_LEVEL=${LOG_LEVEL:-DEBUG}
```

**DESPUÉS**:
```yaml
    environment:
      - PYTHONUNBUFFERED=1
      - PYTHONDONTWRITEBYTECODE=1
      - DB_NAME=${DB_NAME:-omnileads_analytics}
      - OMNILEADS_DB_HOST=${OMNILEADS_DB_HOST:-postgres-omnileads}
      - OMNILEADS_DB_PORT=${OMNILEADS_DB_PORT:-5432}
      - OMNILEADS_DB_USER=${OMNILEADS_DB_USER:-postgres}
      - OMNILEADS_DB_PASSWORD=${OMNILEADS_DB_PASSWORD:-postgres}
      - OMNILEADS_DB_NAME=${OMNILEADS_DB_NAME:-omnileads}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-key-change-in-production}
      - LOG_LEVEL=${LOG_LEVEL:-DEBUG}
      - TIMEZONE_OFFSET=${TIMEZONE_OFFSET:--6}  # ← AGREGAR
```

#### Repetir el mismo cambio en `docker-compose.prod.yml`

---

## Pasos para Aplicar en Producción

### Opción 1: Manual (Recomendado para Producción)

1. **Backup de archivos actuales**:
   ```bash
   cd /ruta/al/proyecto
   cp .env .env.backup.$(date +%Y%m%d)
   cp backend/analytics/config.py backend/analytics/config.py.backup
   cp backend/analytics/services/call_analytics.py backend/analytics/services/call_analytics.py.backup
   cp backend/analytics/services/agent_analytics.py backend/analytics/services/agent_analytics.py.backup
   cp docker-compose.prod.yml docker-compose.prod.yml.backup
   ```

2. **Aplicar cambios manualmente** siguiendo este documento

3. **Reiniciar servicios**:
   ```bash
   # Detener servicios
   docker-compose -f docker-compose.prod.yml down

   # Levantar servicios con nuevas configuraciones
   docker-compose -f docker-compose.prod.yml up -d

   # Verificar que la variable esté cargada
   docker exec <nombre-backend-container> env | grep TIMEZONE_OFFSET
   # Debería mostrar: TIMEZONE_OFFSET=-6
   ```

4. **Verificar funcionamiento**:
   ```bash
   # Probar endpoint de llamadas
   curl -s "http://localhost:8000/api/analytics/llamadas-atendidas?page=1&per_page=1"

   # Las horas deberían estar en GMT-6 (1 hora menos que antes)
   ```

### Opción 2: Usando el script automático

Ver archivo `apply_timezone_migration.sh` en la raíz del proyecto.

```bash
chmod +x apply_timezone_migration.sh
./apply_timezone_migration.sh --environment production
```

---

## Verificación Post-Migración

### 1. Verificar variable de entorno
```bash
docker exec <backend-container> env | grep TIMEZONE_OFFSET
```
**Esperado**: `TIMEZONE_OFFSET=-6`

### 2. Probar conversión de timestamps
```bash
docker exec <backend-container> python -c "
from analytics.config import config
print('Timezone:', config.get_timezone())
print('Offset:', config.TIMEZONE_OFFSET)
"
```
**Esperado**:
```
Timezone: UTC-06:00
Offset: -6
```

### 3. Verificar API
```bash
curl -s "http://localhost:8000/api/analytics/llamadas-atendidas?page=1&per_page=1" | jq '.data[0].hora'
```
Compare la hora devuelta con el timestamp en la base de datos. Debería ser 1 hora menos.

### 4. Verificar en la base de datos
```sql
-- Conectarse a PostgreSQL
psql -h <host> -U <user> -d omnileads

-- Ver último registro con timestamp
SELECT
    id,
    time AT TIME ZONE 'America/Managua' as time_gmt6,  -- GMT-6
    event
FROM reportes_app_llamadalog
WHERE event IN ('COMPLETEAGENT', 'COMPLETEOUTNUM')
ORDER BY time DESC
LIMIT 1;
```

---

## Rollback (En caso de problemas)

Si algo sale mal, restaurar archivos desde backup:

```bash
cd /ruta/al/proyecto

# Restaurar archivos
cp .env.backup.YYYYMMDD .env
cp backend/analytics/config.py.backup backend/analytics/config.py
cp backend/analytics/services/call_analytics.py.backup backend/analytics/services/call_analytics.py
cp backend/analytics/services/agent_analytics.py.backup backend/analytics/services/agent_analytics.py
cp docker-compose.prod.yml.backup docker-compose.prod.yml

# Reiniciar servicios
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

---

## Notas Adicionales

- **No afecta datos en BD**: Esta migración solo cambia cómo se muestran los timestamps en la API/Frontend. Los datos en la base de datos permanecen sin cambios.
- **Cambio transparente**: La conversión de timezone se hace en tiempo real al momento de consultar los datos.
- **Configurable**: Si en el futuro necesitas cambiar a otro timezone (ej: GMT-7), solo cambia `TIMEZONE_OFFSET=-7` en `.env` y reinicia los contenedores.
- **Compatibilidad**: Los filtros por fecha siguen funcionando correctamente porque las comparaciones se hacen antes de la conversión.

---

## Soporte

Si tienes problemas con la migración:
1. Revisa los logs del backend: `docker logs <backend-container> --tail 100`
2. Verifica que todas las variables de entorno estén cargadas correctamente
3. Asegúrate de haber reiniciado los contenedores después de los cambios
4. En caso de dudas, usa el rollback y contacta al equipo de desarrollo

---

**Última actualización**: 2026-01-17
**Aplicado en**: Ambiente de Desarrollo ✓
**Pendiente**: Ambiente de Producción

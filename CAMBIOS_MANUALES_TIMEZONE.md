# Cambios Manuales para Migración de Timezone GMT-5 → GMT-6

**Fecha**: 2026-01-17
**Ambiente**: Producción
**Objetivo**: Cambiar zona horaria de GMT-5 a GMT-6

---

## 📋 LISTA DE ARCHIVOS A MODIFICAR

1. `.env`
2. `backend/analytics/config.py`
3. `backend/analytics/services/call_analytics.py`
4. `backend/analytics/services/agent_analytics.py`
5. `docker-compose.dev.yml`
6. `docker-compose.prod.yml`

---

## ARCHIVO 1: `.env`

**Ubicación**: `/oml-analyticspro/.env`

### AGREGAR después de la línea 13 (después de `LOG_LEVEL=DEBUG`)

**ANTES** (líneas 8-13):
```env
# ============================================================================
# BACKEND CONFIGURATION
# ============================================================================
BACKEND_PORT=8000
PYTHONUNBUFFERED=1
PYTHONDONTWRITEBYTECODE=1
LOG_LEVEL=DEBUG
```

**DESPUÉS** (líneas 8-16):
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

## ARCHIVO 2: `backend/analytics/config.py`

**Ubicación**: `/backend/analytics/config.py`

### CAMBIO 1: Línea 7 - Agregar imports

**ANTES** (líneas 1-9):
```python
"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
```

**DESPUÉS** (líneas 1-10):
```python
"""
Configuración para el módulo de Analytics OmniLeads
Conexión READ-ONLY a PostgreSQL
"""
import logging
import os
from datetime import timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
```

### CAMBIO 2: Línea 26 - Agregar variable de timezone

**ANTES** (líneas 20-26):
```python
class OmniLeadsConfig:
    """Configuración de conexión a PostgreSQL OmniLeads"""

    # Configuración de PostgreSQL OmniLeads (READ-ONLY)
    OMNILEADS_DB_HOST = os.getenv('OMNILEADS_DB_HOST', 'localhost')
    OMNILEADS_DB_PORT = os.getenv('OMNILEADS_DB_PORT', '5432')
    OMNILEADS_DB_NAME = os.getenv('OMNILEADS_DB_NAME', 'omnileads')
    OMNILEADS_DB_USER = os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly')
    OMNILEADS_DB_PASSWORD = os.getenv('OMNILEADS_DB_PASSWORD', '')
```

**DESPUÉS** (líneas 20-29):
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
    TIMEZONE_OFFSET = int(os.getenv('TIMEZONE_OFFSET', '-6'))
```

### CAMBIO 3: Línea 46 - Agregar método get_timezone

**ANTES** (líneas 38-50):
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


# Instancia de configuración
config = OmniLeadsConfig()
```

**DESPUÉS** (líneas 38-55):
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
    def get_timezone(cls):
        """Retorna el timezone configurado basado en TIMEZONE_OFFSET"""
        return timezone(timedelta(hours=cls.TIMEZONE_OFFSET))


# Instancia de configuración
config = OmniLeadsConfig()
```

---

## ARCHIVO 3: `backend/analytics/services/call_analytics.py`

**Ubicación**: `/backend/analytics/services/call_analytics.py`

### CAMBIO 1: Línea 593-596 - Función get_llamadas_abandonadas

**ANTES** (líneas 590-598):
```python
        Incluye: ABANDONADAS (entrantes) + NO ATENDIDAS (salientes)
        - ABANDON, ABANDONWEL, EXITWITHTIMEOUT (abandonadas entrantes)
        - NOANSWER, CANCEL, BUSY, etc. (no atendidas salientes)
        Convierte timezone a GMT-5 (America/Bogota)
        """
        from datetime import timedelta
        from datetime import timezone as dt_timezone

        filters = filters or {}
```

**DESPUÉS** (líneas 590-597):
```python
        Incluye: ABANDONADAS (entrantes) + NO ATENDIDAS (salientes)
        - ABANDON, ABANDONWEL, EXITWITHTIMEOUT (abandonadas entrantes)
        - NOANSWER, CANCEL, BUSY, etc. (no atendidas salientes)
        Convierte timezone según configuración (TIMEZONE_OFFSET)
        """
        from ..config import config

        filters = filters or {}
```

### CAMBIO 2: Línea 651-659 - Función get_llamadas_abandonadas (conversión timezone)

**ANTES** (líneas 647-659):
```python
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone GMT-5 (America/Bogota)
        gmt_minus_5 = dt_timezone(timedelta(hours=-5))

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a GMT-5
            time_gmt5 = llamada.time.astimezone(gmt_minus_5)
```

**DESPUÉS** (líneas 647-657):
```python
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone configurado
        local_tz = config.get_timezone()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a timezone local
            time_local = llamada.time.astimezone(local_tz)
```

### CAMBIO 3: Línea 670-673 - Función get_llamadas_abandonadas (usar time_local)

**ANTES** (líneas 669-673):
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_gmt5.strftime('%Y-%m-%d'),
                'hora': time_gmt5.strftime('%H:%M:%S'),
```

**DESPUÉS** (líneas 669-673):
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_local.strftime('%Y-%m-%d'),
                'hora': time_local.strftime('%H:%M:%S'),
```

### CAMBIO 4: Línea 693-697 - Función get_llamadas_detalladas

**ANTES** (líneas 691-699):
```python
        """
        Obtiene lista detallada de llamadas ATENDIDAS con paginación
        Solo eventos finales: COMPLETEAGENT, COMPLETEOUTNUM
        Convierte timezone a GMT-5 (America/Bogota)
        """
        from datetime import timedelta
        from datetime import timezone as dt_timezone

        filters = filters or {}
```

**DESPUÉS** (líneas 691-698):
```python
        """
        Obtiene lista detallada de llamadas ATENDIDAS con paginación
        Solo eventos finales: COMPLETEAGENT, COMPLETEOUTNUM
        Convierte timezone según configuración (TIMEZONE_OFFSET)
        """
        from ..config import config

        filters = filters or {}
```

### CAMBIO 5: Línea 749-757 - Función get_llamadas_detalladas (conversión timezone)

**ANTES** (líneas 745-757):
```python
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone GMT-5 (America/Bogota)
        gmt_minus_5 = dt_timezone(timedelta(hours=-5))

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a GMT-5
            time_gmt5 = llamada.time.astimezone(gmt_minus_5)
```

**DESPUÉS** (líneas 745-755):
```python
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone configurado
        local_tz = config.get_timezone()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a timezone local
            time_local = llamada.time.astimezone(local_tz)
```

### CAMBIO 6: Línea 765-766 - Función get_llamadas_detalladas (usar time_local)

**ANTES** (líneas 762-766):
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_gmt5.strftime('%Y-%m-%d'),
                'hora': time_gmt5.strftime('%H:%M:%S'),
```

**DESPUÉS** (líneas 762-766):
```python
            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_local.strftime('%Y-%m-%d'),
                'hora': time_local.strftime('%H:%M:%S'),
```

---

## ARCHIVO 4: `backend/analytics/services/agent_analytics.py`

**Ubicación**: `/backend/analytics/services/agent_analytics.py`

### CAMBIO 1: Línea 11 - Agregar import de config

**ANTES** (líneas 8-17):
```python
from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from ..models.omnileads_models import (
    ActividadAgenteLog,
    AgenteProfile,
    LlamadaLog,
    Pausa,
    User,
)
```

**DESPUÉS** (líneas 8-18):
```python
from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from ..config import config
from ..models.omnileads_models import (
    ActividadAgenteLog,
    AgenteProfile,
    LlamadaLog,
    Pausa,
    User,
)
```

### CAMBIO 2: Línea 304-320 - Función get_timeline_agente

**ANTES** (líneas 303-320):
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

**DESPUÉS** (líneas 303-323):
```python
        # Construir timeline sin queries adicionales
        local_tz = config.get_timezone()
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
            time_local = act.time.astimezone(local_tz)

            timeline.append({
                'tiempo': time_local.strftime('%H:%M:%S'),
                'evento': evento_map.get(act.event, act.event),
                'tipo': act.event
            })
```

### CAMBIO 3: Línea 567-580 - Función get_disponibilidad_agentes

**ANTES** (líneas 567-580):
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

**DESPUÉS** (líneas 567-585):
```python
            # Convertir timestamps a timezone local
            local_tz = config.get_timezone()
            primer_login_local = primer_login.astimezone(local_tz) if primer_login else None
            ultimo_logout_local = ultimo_logout.astimezone(local_tz) if ultimo_logout else None

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
                'primer_login': primer_login_local.strftime('%H:%M:%S') if primer_login_local else '-',
                'ultimo_logout': ultimo_logout_local.strftime('%H:%M:%S') if ultimo_logout_local else '-'
            })
```

### CAMBIO 4: Línea 617-620 - Función get_detalle_sesiones_agente

**ANTES** (líneas 617-622):
```python
        sesiones = []
        tiempo_login = None
        sesiones_totales = 0
        sesiones_filtradas = 0

        for actividad in actividades:
```

**DESPUÉS** (líneas 617-623):
```python
        sesiones = []
        tiempo_login = None
        sesiones_totales = 0
        sesiones_filtradas = 0
        local_tz = config.get_timezone()

        for actividad in actividades:
```

### CAMBIO 5: Línea 646-651 - Función get_detalle_sesiones_agente (conversión timestamps)

**ANTES** (líneas 641-651):
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

**DESPUÉS** (líneas 641-655):
```python
                if incluir_sesion:
                    sesiones_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    # Convertir timestamps a timezone local
                    tiempo_login_local = tiempo_login.astimezone(local_tz)
                    tiempo_logout_local = actividad.time.astimezone(local_tz)

                    sesiones.append({
                        'fecha_inicio': tiempo_login_local.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': tiempo_logout_local.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

### CAMBIO 6: Línea 700-705 - Función get_detalle_pausas_agente

**ANTES** (líneas 700-706):
```python
        pausas = []
        tiempo_pausa_inicio = None
        pausa_id_actual = None
        pausas_totales = 0
        pausas_filtradas = 0

        for actividad in actividades:
```

**DESPUÉS** (líneas 700-707):
```python
        pausas = []
        tiempo_pausa_inicio = None
        pausa_id_actual = None
        pausas_totales = 0
        pausas_filtradas = 0
        local_tz = config.get_timezone()

        for actividad in actividades:
```

### CAMBIO 7: Línea 733-744 - Función get_detalle_pausas_agente (conversión timestamps)

**ANTES** (líneas 726-744):
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

**DESPUÉS** (líneas 726-748):
```python
                if incluir_pausa:
                    pausas_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    pausa_info = pausas_dict.get(pausa_id_actual, {'tipo': 'P', 'nombre': 'Otra'})

                    # Convertir timestamps a timezone local
                    tiempo_pausa_inicio_local = tiempo_pausa_inicio.astimezone(local_tz)
                    tiempo_pausa_fin_local = actividad.time.astimezone(local_tz)

                    pausas.append({
                        'tipo': pausa_info['tipo'],
                        'nombre': pausa_info['nombre'],
                        'fecha_inicio': tiempo_pausa_inicio_local.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': tiempo_pausa_fin_local.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })
```

---

## ARCHIVO 5: `docker-compose.dev.yml`

**Ubicación**: `/docker-compose.dev.yml`

### CAMBIO: Línea 23 - Agregar variable TIMEZONE_OFFSET

**ANTES** (líneas 12-23):
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
    volumes:
```

**DESPUÉS** (líneas 12-24):
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
      - TIMEZONE_OFFSET=${TIMEZONE_OFFSET:--6}
    volumes:
```

---

## ARCHIVO 6: `docker-compose.prod.yml`

**Ubicación**: `/docker-compose.prod.yml`

### CAMBIO: Agregar variable TIMEZONE_OFFSET

**Busca la sección `backend.environment` y agrega la línea**:
```yaml
      - TIMEZONE_OFFSET=${TIMEZONE_OFFSET:--6}
```

**NOTA**: Debe estar en la misma sección donde están las otras variables como `OMNILEADS_DB_HOST`, `LOG_LEVEL`, etc.

---

## ✅ PASOS FINALES

Después de hacer todos los cambios:

### 1. Reiniciar contenedores Docker

**Para desarrollo**:
```powershell
docker-compose -f docker-compose.dev.yml down
docker-compose -f docker-compose.dev.yml up -d
```

**Para producción**:
```powershell
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### 2. Verificar que funcionó

```powershell
# Ver variable de entorno
docker exec <nombre-container-backend> env | grep TIMEZONE
# Debe mostrar: TIMEZONE_OFFSET=-6

# Verificar módulo Python
docker exec <nombre-container-backend> python -c "from analytics.config import config; print(config.TIMEZONE_OFFSET)"
# Debe mostrar: -6

# Probar API
curl "http://localhost:8000/api/analytics/llamadas-atendidas?page=1&per_page=1"
# Las horas deben estar en GMT-6 (1 hora menos que antes)
```

---

## 🔄 ROLLBACK

Si algo sale mal, revierte los cambios:

1. Restaura los archivos desde backup (si los creaste)
2. O cambia manualmente:
   - `.env`: Cambia `TIMEZONE_OFFSET=-6` a `TIMEZONE_OFFSET=-5`
   - Reinicia contenedores

---

## 📊 RESUMEN

| Archivo | Cambios |
|---------|---------|
| `.env` | 1 línea agregada |
| `config.py` | 3 cambios (import, variable, método) |
| `call_analytics.py` | 6 cambios (2 funciones modificadas) |
| `agent_analytics.py` | 7 cambios (4 funciones modificadas) |
| `docker-compose.dev.yml` | 1 línea agregada |
| `docker-compose.prod.yml` | 1 línea agregada |
| **TOTAL** | 19 cambios en 6 archivos |

**Tiempo estimado**: 20-30 minutos

---

**Última actualización**: 2026-01-17
**Aplicado en desarrollo**: ✓
**Pendiente en producción**: Sí

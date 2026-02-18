# Resumen de Cambios — 17 de Febrero 2026

**Proyecto**: OmniLeads Analytics Pro
**Rama**: `V2DNDS`
**Commits del día**: 12
**Archivos modificados**: 36
**Líneas**: +5,052 / -1,135

---

## 1. Corrección de Métricas y Clasificación de Eventos

**Commits**: `07dd456`, `02421b6`

### Problema
Los conteos de llamadas eran inconsistentes entre endpoints. Algunos contaban filas duplicadas (múltiples eventos por llamada), otros usaban clasificaciones de eventos diferentes.

### Solución
- **Unificación de subquery global** `_build_last_event_subquery()`: todos los endpoints ahora usan `MAX(id) GROUP BY callid` para obtener el último evento de cada llamada
- **Clasificación unificada**: EXITWITHTIMEOUT movido a ABANDONADAS, COMPLETE-CT no estándar eliminado
- **Endpoints corregidos**: `get_kpis()`, `get_distribucion_llamadas()`, `get_llamadas_por_tipo()`, `get_llamadas_detalladas()`, `get_llamadas_abandonadas()`
- **Frontend**: `buildQueryString()` envía `campana_ids` y `agente_ids` para filtros multi-selección

### Archivos
- `backend/analytics/services/call_analytics.py`
- `backend/analytics/services/call_analytics_extended.py`
- `backend/analytics/services/agent_analytics.py`
- `frontend/src/services/analyticsApi.js`

---

## 2. Corrección de Timezone

**Commits**: `07dd456`, `4353e87`, `941e12f`, `c2f4c16`

### Problema
La hora mostrada en los reportes no correspondía a la hora local de Nicaragua. El servidor OmniLeads tiene reloj en hora Nicaragua pero PostgreSQL graba con offset de Colombia (UTC-5). Se intentaron varias estrategias: offset fijo de -6 horas (incorrecto, causaba doble resta), `func.timezone('America/Managua')` y finalmente se determinó que la hora numérica en la BD ya es correcta.

### Solución final
- `_local_time()` usa `AT TIME ZONE 'America/Bogota'` (extrae la hora tal cual está en la BD sin conversión)
- Se eliminaron todos los `.astimezone()` en detalle de llamadas, sesiones, pausas, transferencias y gestiones
- Filtros usan naive datetime (sin tzinfo) para evitar `TypeError: naive vs aware`
- Variable `TIMEZONE_DB = 'America/Bogota'` como única configuración de timezone

### Archivos
- `backend/analytics/config.py`
- `backend/analytics/services/call_analytics.py`
- `backend/analytics/services/call_analytics_extended.py`
- `backend/analytics/services/agent_analytics.py`
- `backend/analytics/services/gestion_analytics.py`

---

## 3. Server-Side Sorting + Nuevos Reportes

**Commit**: `41749b0`

### Funcionalidades
- **Ordenamiento server-side** para tablas de Atendidas, Abandonadas y Salientes (`sort_by`/`sort_dir` params, ordenamiento across all pages)
- **Filtros `agente_ids`/`campana_ids`** en tabs Agentes y Agentes Avanzado
- **Nueva tabla detalle de Salientes** con paginación server-side y exportación Excel (`/salientes/detalle`)
- **Reporte Gestiones** con paginación y ExportButtonAsync
- **Card Transferencias por Campaña**

### Archivos nuevos
- `frontend/src/components/analytics/TablaLlamadasOptimizada.js`
- `frontend/src/components/analytics/TablaAbandonadasOptimizada.js`
- `frontend/src/components/analytics/reportes/Gestiones.js`

### Archivos modificados
- `backend/analytics/routes/analytics_routes.py`
- `backend/analytics/services/call_analytics.py`
- `frontend/src/components/analytics/reportes/LlamadasSalientes.js`
- `frontend/src/components/analytics/reportes/Transferencias.js`
- `frontend/src/utils/excelExport.js`

---

## 4. BD Local Sincronizada (Sync Service)

**Commit**: `6c952d8`

### Problema
El backend consultaba directamente la BD remota de OmniLeads (192.168.15.104), generando dependencia de red, latencia y carga sobre la BD de producción.

### Solución
Nuevo sistema de sincronización con BD local PostgreSQL:

- **Motor de sync incremental** (`sync_engine.py`): `WHERE id > watermark` para tablas de alto volumen (llamadalog, actividadagentelog), full refresh para tablas de referencia
- **Daemon con APScheduler** (`sync_service.py`): event logs cada 5 min, referencia cada 1 hora
- **Schema y watermarks** (`schema.py`, `watermark.py`): 8 tablas + sync_metadata + índices de rendimiento
- **Health check** HTTP en puerto 8001
- **Toggle seguro**: `USE_LOCAL_DB=true/false` para cambiar instantáneamente entre BD local y remota
- **Frontend**: `SyncStatusBadge` con estado de sincronización en tiempo real

### Rendimiento
- Carga inicial: ~1.68M filas en ~6 minutos
- Sync incremental: ~300 filas en 0.3 segundos
- KPIs verificados: idénticos entre BD local y remota

### Archivos nuevos (paquete `backend/sync/`)
- `__init__.py`, `__main__.py`, `config.py`, `health.py`
- `schema.py`, `sync_engine.py`, `sync_service.py`, `watermark.py`
- `compose/dev/sync/sync.dev.dockerfile`

### Archivos modificados
- `backend/analytics/config.py` — Variables `LOCAL_DB_*`, `USE_LOCAL_DB`
- `backend/analytics/database.py` — Soporte dual BD (local/remota)
- `docker-compose.dev.yml` — Servicios `postgres-local` + `sync-service`
- `frontend/src/components/analytics/SyncStatusBadge.js` — NUEVO
- `frontend/src/components/analytics/DashboardMejorado.js`
- `frontend/src/services/analyticsApi.js`

---

## 5. Producción + Guía de Despliegue

**Commit**: `614debf`

### Entregables
- **`docker-compose.prod.yml`** actualizado con `postgres-local` y `sync-service`, tuning de PostgreSQL (shared_buffers, effective_cache_size, work_mem)
- **`compose/prod/sync/sync.prod.dockerfile`**: build multi-stage con usuario non-root
- **`.env.example`**: variables LOCAL_DB y SYNC documentadas
- **`DEPLOY_UBUNTU.md`**: guía paso a paso para despliegue en Ubuntu 22.04 (14 secciones: requisitos, Docker, env, build, firewall, SSL, monitoreo, rollback)

---

## 6. Auditoría de Gestiones

**Commit**: `6aeb016`

### Problema
Las gestiones (234K+ filas) estaban clasificadas como tabla de referencia (full refresh cada 1 hora). Además, no existía forma de auditar qué llamadas atendidas no tenían gestión registrada.

### Solución

**Sync**: `customformgestion` movida de `REFERENCE_TABLES` a `INCREMENTAL_TABLES` (sync cada 5 min) + 6 índices de rendimiento.

**Nuevos endpoints**:
- `GET /gestiones/auditoria` — KPIs: total atendidas, total gestiones, sin gestión, cobertura porcentual
- `GET /gestiones/sin-gestion` — Lista paginada de llamadas atendidas sin registro de gestión (LEFT ANTI JOIN por callid)

**Frontend**:
- 4 tarjetas de auditoría (Llamadas Contestadas, Total Gestiones, Sin Gestión, Cobertura %)
- Tabla paginada "Llamadas Atendidas sin Gestión" con exportación Excel

### Archivos
- `backend/sync/sync_engine.py` — Mover customformgestion a INCREMENTAL
- `backend/sync/schema.py` — 6 índices para gestiones
- `backend/analytics/services/gestion_analytics.py` — Métodos de auditoría
- `backend/analytics/routes/analytics_routes.py` — 2 endpoints nuevos
- `frontend/src/components/analytics/reportes/Gestiones.js`
- `frontend/src/services/analyticsApi.js`

---

## 7. Corrección de Hora/Duración + Formato Unificado

**Commit**: `f3412ac`

### Problema 1: Hora incorrecta en Detalle de Gestiones
La hora venía de `customformgestion.fecha` (momento en que el agente guardó la gestión, hasta ~1h después de la llamada) en vez de `LlamadaLog.time` (hora real de la llamada).

### Solución
Dos subqueries separadas en `get_gestiones_detalle()`:
- **`hora_sq`**: `MAX(time)` de **cualquier evento** del callid — matchea incluso llamadas en curso
- **`duracion_sq`**: `MAX(duracion_llamada)` solo de **eventos atendidos** — duración solo para llamadas terminadas

### Problema 2: Formato de duración/espera inconsistente
Cada tabla usaba un formato diferente: `Xm Xs`, `m:ss`, `Xs`.

### Solución
Formato **`mm:ss`** unificado con padding (ej: `01:29`, `00:45`) en todas las tablas:
- `Gestiones.js` — `formatDuration()` + nueva columna Duración
- `TablaLlamadasOptimizada.js` — espera de `Xs` a `mm:ss`
- `TablaAbandonadasOptimizada.js` — nueva función + espera a `mm:ss`
- `TablaLlamadas.js` — espera a `mm:ss`
- `LlamadasSalientes.js` — espera a `mm:ss`

### Problema 3: Header redundante
Se mostraba "Última actualización: dd/mm/yyyy HH:mm:ss" junto al SyncStatusBadge.

### Solución
- Eliminada línea "Última actualización" del header
- SyncStatusBadge mejorado: hora Nicaragua (UTC-6), tarjeta destacada de gestiones en panel desplegable

---

## 8. Corrección KPI Ocupación

**Commit**: `6722cad`

### Problema
El KPI "Ocupación" del dashboard mostraba **14.73%**, un valor irreal para un call center con alto flujo. La fórmula dividía el tiempo total de llamadas entre `agentes_activos × 24 horas`, asumiendo que todos los agentes estuvieron conectados las 24h y sin descontar pausas recreativas.

### Solución
Nuevo cálculo basado en datos reales de `ActividadAgenteLog`:

```
ocupacion = tiempo_hablando / (tiempo_sesion_real - pausas_recreativas) × 100
```

- **`tiempo_hablando`**: SUM(duracion_llamada) de eventos atendidos
- **`tiempo_sesion_real`**: Duración de pares ADDMEMBER→REMOVEMEMBER por agente
- **`pausas_recreativas`**: Duración de pares PAUSEALL→UNPAUSEALL donde Pausa.tipo='R'

**Resultado**: ~87%, consistente con el reporte de disponibilidad de agentes.

También corregido `get_ocupacion_agentes()` que asumía jornada fija de 480 minutos; ahora usa tiempos reales de sesión por agente.

### Archivos
- `backend/analytics/services/call_analytics.py` — KPI global con query a ActividadAgenteLog
- `backend/analytics/services/agent_analytics.py` — Ocupación por agente con sesión real

---

## 9. Auditoría de Código — DRY + Bug Fixes

**Commit**: `14dd9d3`

### Mejora 1: Constantes centralizadas (Backend)
**Problema**: EVENTOS_ATENDIDAS, EVENTOS_ABANDONADAS, TIPO_SALIENTE, etc. estaban definidos en 4 archivos de servicios (~50 líneas duplicadas por archivo).

**Solución**: Nuevo archivo `backend/analytics/constants.py` como fuente única de verdad:
- `EVENTOS_ATENDIDAS`, `EVENTOS_ABANDONADAS`, `EVENTOS_NO_ATENDIDAS`
- `EVENTOS_INTERMEDIOS`, `EVENTOS_EXCLUIDOS`, `EVENTOS_FINALES`
- `TIPO_SALIENTE`, `TIPO_ENTRANTE`, `SLA_THRESHOLD_60`, `SLA_THRESHOLD_20`
- `EVENTOS_SALIENTES`, `EVENTOS_TRANSFERENCIAS` (diccionarios especializados)

Los 4 servicios ahora importan desde `constants.py`.

### Mejora 2: Formatters centralizados (Frontend)
**Problema**: `formatDuration()` / `formatDuracion()` duplicada en 6 componentes.

**Solución**: Nuevo archivo `frontend/src/utils/formatters.js` con ambos nombres exportados. Los 6 componentes ahora importan desde aquí.

### Bug Fix 1: NoneType en strftime de Gestiones
**Problema**: Si una gestión no tiene `hora_llamada` ni `fecha`, `ts.strftime()` genera `AttributeError`.
**Fix**: `if ts else '-'` como guard en fecha y hora.

### Bug Fix 2: TMO null safety
**Problema**: `if metrics.tmo_promedio` trata 0 segundos como falsy (0 es `False` en Python).
**Fix**: `if metrics.tmo_promedio is not None` — explícito contra None.

### Bug Fix 3: Validación de paginación
**Problema**: `page=0` o `page=-1` genera offset negativo → query SQL inválida.
**Fix**: `page = max(1, page)` y `per_page = max(1, min(per_page, 200))` en 5 endpoints paginados.

### Documento de Auditoría
Creado `AUDITORIA_RECOMENDACIONES.md` con hallazgos de QA, mejoras de código, y plan de acción priorizado (P1/P2/P3).

### Archivos nuevos
- `backend/analytics/constants.py`
- `frontend/src/utils/formatters.js`
- `AUDITORIA_RECOMENDACIONES.md`

### Archivos modificados
- `backend/analytics/services/call_analytics.py`
- `backend/analytics/services/call_analytics_extended.py`
- `backend/analytics/services/agent_analytics.py`
- `backend/analytics/services/gestion_analytics.py`
- `frontend/src/components/analytics/TablaLlamadasOptimizada.js`
- `frontend/src/components/analytics/TablaAbandonadasOptimizada.js`
- `frontend/src/components/analytics/TablaLlamadas.js`
- `frontend/src/components/analytics/reportes/Gestiones.js`
- `frontend/src/components/analytics/reportes/LlamadasSalientes.js`
- `frontend/src/components/analytics/reportes/Transferencias.js`

---

## Resumen de Arquitectura Final

```
BD Remota OmniLeads (192.168.15.104)
    |  sync incremental cada 5 min (psycopg2)
    v
[sync-service] --> [postgres-local] <-- Backend (SQLAlchemy ORM)
                                          |
                                      API REST (FastAPI)
                                          |
                                      Frontend (React)
```

**36 archivos modificados** | **+5,052 líneas** | **-1,135 líneas** | **12 commits**

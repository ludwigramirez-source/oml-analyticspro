# Resumen de Cambios — 10 de Marzo 2026

**Proyecto**: OmniLeads Analytics Pro
**Rama**: `V2DNDS`
**Commits del día**: 4
**Archivos modificados**: 9
**Líneas**: +379 / -347

---

## 1. Modo Solo-Entrantes — Eliminación de Salientes y Transferencias

**Commit**: `2aeb42c`

### Problema
Las llamadas salientes (tipo_llamada=1) y transferencias estaban distorsionando los KPIs y métricas del dashboard, impidiendo un análisis correcto para este cliente que solo opera con llamadas entrantes.

### Solución
- **Toggle centralizado**: `INBOUND_ONLY_MODE = True` en `constants.py` con lista derivada `TIPOS_LLAMADA_ACTIVOS`
- **Backend**: `_apply_filters()` fuerza `tipo_llamada == TIPO_ENTRANTE` cuando el modo está activo; `_build_last_event_subquery()` y `get_kpis()` usan `TIPOS_LLAMADA_ACTIVOS`
- **Frontend**: Eliminados tabs Salientes y Transferencias, removido filtro "Tipo de Llamada", removidas funciones y estados asociados a distribución por tipo
- **Reversible**: Basta con cambiar `INBOUND_ONLY_MODE = False` para restaurar salientes

### Archivos
- `backend/analytics/constants.py` — nuevo toggle y lista derivada
- `backend/analytics/services/call_analytics.py` — filtros entrantes-only
- `backend/analytics/services/gestion_analytics.py` — usa `TIPOS_LLAMADA_ACTIVOS`
- `frontend/src/components/analytics/DashboardMejorado.js` — tabs y estados removidos
- `frontend/src/components/analytics/FilterSection.js` — dropdown tipo_llamada removido
- `frontend/src/components/analytics/reportes/Gestiones.js` — columna tipo_llamada removida
- `frontend/src/components/analytics/TablaAbandonadas.js` — texto actualizado

### Impacto en Métricas
| Métrica | Antes (con salientes) | Después (solo entrantes) |
|---|---|---|
| SLA 60s | 81.39% | 88.47% |
| Tasa Abandono | 29.67% | 23.4% |

### Correcciones adicionales incluidas
- **Dockerfile producción**: Agregado `pip install --upgrade pip` antes de `requirements.txt`
- **requirements.txt**: Removido `jq>=1.6.0` (no importado, fallaba compilación en imagen slim)

---

## 2. Restauración Card EntradasSalidas y Renombrar KPI

**Commit**: `3c05736`

### Problema
Al implementar modo solo-entrantes se removió la tarjeta verde de "Llamadas Entrantes" que es visualmente importante para el cliente. También el KPI decía "Llamadas Perdidas" en vez de "Llamadas Abandonadas".

### Solución
- Restaurado import, estado y render de `<EntradasSalidas>` (muestra entrantes con dato real y salientes en 0)
- KPI cambiado de `kpis.llamadas_perdidas` → `kpis.llamadas_abandonadas` con label "Llamadas Abandonadas"

### Archivos
- `frontend/src/components/analytics/DashboardMejorado.js`

---

## 3. Gestiones Deduplicadas — 1 Gestión por Call ID

**Commit**: `f7a1800`

### Problema
El modelo de gestiones contaba múltiples gestiones por llamada y gestiones huérfanas:
- **Duplicados**: Doble clic, reenvío de formulario, cambio de clasificación → 2+ gestiones por call_id
- **Huérfanas**: Gestiones de llamadas ABANDON, CONNECT (en curso), BTOUT-TRY, de otro día, o salientes
- Ejemplo día 10/03: 8,152 gestiones brutas en BD, pero solo 7,666 válidas

### Solución — Reescritura completa de `gestion_analytics.py`

**Regla**: 1 llamada = 1 gestión.

Dos subqueries reutilizables aplicados en todos los métodos:

```python
_build_llamadas_atendidas_sq(filters)
# → callids de ENTRANTES ATENDIDAS en el rango (GROUP BY callid)

_build_gestion_unica_sq(filters)
# → MAX(id) por call_id (última gestión registrada)
```

Cada método cruza ambas subqueries: solo gestiones cuyo `call_id` coincide con una llamada entrante atendida del mismo rango.

**Casos manejados**:
| Caso | Tratamiento |
|---|---|
| Mismo agente, misma incidencia (doble clic) | MAX(id) — toma última |
| Mismo agente, incidencia distinta (reclasificación) | MAX(id) — toma última |
| Agente distinto (transferencia) | MAX(id) — toma última |
| Evento ABANDON | Excluida (no es atendida) |
| Evento CONNECT (en curso) | Excluida (no es atendida) |
| Evento BTOUT-TRY | Excluida (no es atendida) |
| Llamada de otro día | Excluida (fuera del rango) |
| Llamada saliente (tipo=1) | Excluida (INBOUND_ONLY_MODE) |

**Optimizaciones de performance**:
- Conteo separado del query principal (sin JOINs de lookup)
- JOIN directo por PK para hora/duración (elimina subqueries sin filtro de fecha)
- Paginación estabilizada con `ORDER BY fecha DESC, id DESC`

### Archivos
- `backend/analytics/services/gestion_analytics.py` — reescritura completa (298 insertions, 214 deletions)

### Verificación
Validado con datos reales en 8 días (5 de marzo + 3 de febrero):

| Día | Brutas | Duplicados | Huérfanas | Válidas | Cobertura |
|---|---|---|---|---|---|
| 10 mar | 8,152+ | 18+ | 130+ | 7,666 | 94.2% |
| 9 mar | 8,152 | 18 | 130 | 8,022 | 94.2% |
| 8 mar | 4,016 | 3 | 105 | 3,926 | 92.5% |
| 7 mar | 5,951 | 16 | 99 | 5,844 | 94.0% |
| 12 feb | — | — | — | 8,291 | 93.8% |
| 19 feb | — | — | — | 8,808 | 91.8% |
| 25 feb | — | — | — | 8,448 | 91.8% |

- Cero duplicados en paginación completa (verificado recorriendo todas las páginas)
- Suma de incidencias = total KPIs (consistencia interna)
- Sin gestión = atendidas - gestiones (cuadra en todos los endpoints)

---

## 4. Atribución de Gestiones al Agente de la Llamada

**Commit**: `683c810`

### Problema
En transferencias, el agente que registra la gestión (`CustomFormGestion.agent_id`) puede diferir del que cerró la llamada (`LlamadaLog.agente_id`). Esto causaba que un agente tuviera más gestiones que llamadas atendidas.

Ejemplo: Agente 55 (JUAN GUTIÉRREZ) tenía 38 gestiones pero solo 37 llamadas — la gestión extra correspondía a una llamada cerrada por Agente 137.

### Solución
Tres métodos modificados para usar `LlamadaLog.agente_id` (agente de la llamada) en vez de `CustomFormGestion.agent_id` (agente que registró):

- `get_gestiones_kpis()` — conteo de agentes activos
- `get_gestiones_por_agente()` — agrupación por agente
- `get_gestiones_detalle()` — nombre del agente en detalle

### Archivos
- `backend/analytics/services/gestion_analytics.py`

### Verificación
Validado en 8 días (5 de marzo + 3 de febrero) con ~622 verificaciones por agente:

| Día | Agentes | Exceden (gestiones > llamadas) |
|---|---|---|
| 10 mar | 85 | **0** |
| 9 mar | 85 | **0** |
| 8 mar | 53 | **0** |
| 7 mar | 67 | **0** |
| 6 mar | 83 | **0** |
| 12 feb | 83 | **0** |
| 19 feb | 85 | **0** |
| 25 feb | 83 | **0** |

**Regla cumplida**: `gestiones_por_agente <= llamadas_por_agente` en todos los casos.

---

## Resumen de Commits

| # | Hash | Tipo | Descripción |
|---|---|---|---|
| 1 | `2aeb42c` | feat | Modo solo-entrantes — eliminar salientes y transferencias |
| 2 | `3c05736` | fix | Restaurar card EntradasSalidas y renombrar KPI |
| 3 | `f7a1800` | fix | Gestiones deduplicadas — 1 gestión por call_id |
| 4 | `683c810` | fix | Atribuir gestiones al agente de la llamada |

**Total**: 9 archivos modificados, +379 / -347 líneas

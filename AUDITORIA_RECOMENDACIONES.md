# Auditoría y Recomendaciones — OmniLeads Analytics Pro

**Fecha**: 17 de febrero de 2026
**Rama**: V2DNDS
**Contexto**: Aplicación Docker local, conexión read-only a BD, no expuesta a internet

---

## 1. Resumen Ejecutivo

Se realizó una auditoría integral con 3 agentes especializados (QA, Seguridad, Code Review) analizando todo el codebase del proyecto.

### Correcciones aplicadas hoy (11 commits)

| Commit | Descripción |
|--------|-------------|
| `07dd456` | Correcciones de métricas, reporte Gestiones y timezone |
| `4353e87` | Timezone: AT TIME ZONE en vez de interval |
| `941e12f` | Hora tal cual de BD sin conversión |
| `c2f4c16` | Comparación naive vs aware en sesiones/pausas |
| `02421b6` | Conteo unificado con MAX(id) por callid |
| `41749b0` | Server-side sorting, filtros agentes/campañas, salientes |
| `6c952d8` | BD local sincronizada con sync-service |
| `614debf` | Producción con BD local + guía despliegue |
| `6aeb016` | Auditoría gestiones + sync incremental |
| `f3412ac` | Hora/duración gestiones + formato mm:ss unificado |
| `6722cad` | Ocupación KPI con datos reales de sesión |

### Estado de hallazgos

| Categoría | Total | Corregidos hoy | Corregidos en auditoría | Pendientes |
|-----------|-------|----------------|------------------------|------------|
| QA - Bugs | 12 | 7 | 3 | 2 |
| Code Quality | 10 | 0 | 2 | 8 |
| Seguridad* | 16 | 0 | 0 | 16 |

*\*Seguridad no se aborda por ahora — el proyecto corre en Docker local sin exposición.*

---

## 2. Bugs Corregidos Hoy (referencia)

Ya no requieren acción:

- ✅ **Timezone/hora incorrecta** en todos los reportes — 4 commits
- ✅ **Ocupación KPI 14.73%** → 82.13% usando datos reales de sesión
- ✅ **Formato duración inconsistente** (Xm Xs, Xs, m:ss) → mm:ss unificado
- ✅ **Eventos ATENDIDAS inconsistentes** entre 4 archivos → sincronizados
- ✅ **KeyError agente_id** en get_ocupacion_agentes()
- ✅ **Jornada fija 480 min** en chart ocupación → datos reales
- ✅ **Conteo duplicado** de llamadas por múltiples eventos → MAX(id) por callid

---

## 3. Bugs Corregidos en esta Auditoría

| Bug | Archivo | Fix aplicado |
|-----|---------|--------------|
| NoneType en strftime si gestión sin fecha ni llamada | `gestion_analytics.py:333-334` | Fallback: `if ts else '-'` |
| TMO promedio: 0 segundos tratado como None | `call_analytics.py:239-240` | `is not None` en vez de truthiness |
| Paginación sin validación (page=0 o negativo) | 4 archivos con paginación | `page = max(1, page)` + cap per_page a 200 |

---

## 4. Bugs Pendientes (no críticos)

| # | Bug | Archivo | Severidad | Nota |
|---|-----|---------|-----------|------|
| 1 | Cambios/tendencias hardcodeados ('+12%', '+8%') | `call_analytics.py` get_kpis() | Baja | Son datos ficticios de UI, no afectan métricas reales. Requiere lógica de comparación con período anterior |
| 2 | Ocupación capada con `min(100)` sin log de advertencia | `call_analytics.py` | Baja | Si supera 100%, es síntoma de error en clasificación de pausas. Considerar agregar log.warning |

---

## 5. Mejoras de Código Aplicadas en esta Auditoría

### 5.1 Constantes centralizadas (DRY)

**Problema**: EVENTOS_ATENDIDAS, EVENTOS_ABANDONADAS, etc. definidos idénticamente en 4 archivos.

**Solución**: Creado `backend/analytics/constants.py` como fuente única de verdad. Los 4 servicios ahora importan desde ahí:
- `call_analytics.py`
- `call_analytics_extended.py`
- `agent_analytics.py`
- `gestion_analytics.py`

### 5.2 formatDuration centralizado (DRY)

**Problema**: Función formatDuration/formatDuracion duplicada en 6 componentes React con variaciones menores.

**Solución**: Creado `frontend/src/utils/formatters.js` con `formatDuration` y alias `formatDuracion`. Los 6 componentes ahora importan desde ahí:
- `TablaLlamadasOptimizada.js`
- `TablaAbandonadasOptimizada.js`
- `TablaLlamadas.js`
- `Gestiones.js`
- `LlamadasSalientes.js`
- `Transferencias.js`

---

## 6. Mejoras de Código Recomendadas (futuro)

### P1 — Importantes

| # | Mejora | Archivo(s) | Esfuerzo | Beneficio |
|---|--------|-----------|----------|-----------|
| 1 | **Dividir DashboardMejorado.js** (~700 líneas) en componentes: DashboardHeader, FilterPanel, KPISection, ChartsSection, TablesSection | `DashboardMejorado.js` | 3 días | Mantenibilidad, testabilidad |
| 2 | **Extraer get_kpis()** (~300 líneas) en submétodos: _calc_ocupacion(), _calc_sla(), _get_agent_sessions() | `call_analytics.py` | 1 día | Legibilidad, testabilidad |
| 3 | **Crear BaseAnalyticsService** con _apply_filters() compartido | `call_analytics.py`, `call_analytics_extended.py`, `gestion_analytics.py` | 1 día | Elimina duplicación de filtros |
| 4 | **APIs en paralelo** en dashboard: usar Promise.allSettled() en vez de llamadas secuenciales | `DashboardMejorado.js` | 4 horas | Carga 5-10x más rápida |
| 5 | **React.memo** en tablas pesadas para evitar re-renders innecesarios | `TablaLlamadas.js`, `TablaAbandonadas.js` | 2 horas | Performance UI |
| 6 | **Calcular cambios reales** vs período anterior en get_kpis() en vez de '+12%' hardcodeado | `call_analytics.py` | 2 días | Datos reales en dashboard |

### P2 — Mejoras

| # | Mejora | Archivo(s) | Esfuerzo | Beneficio |
|---|--------|-----------|----------|-----------|
| 7 | **Debouncing en filtros** — evitar llamadas API en cada cambio | `DashboardMejorado.js` | 2 horas | Reduce carga en backend |
| 8 | **Context API para filtros** — eliminar prop drilling | `DashboardMejorado.js` → componentes hijos | 4 horas | Código más limpio |
| 9 | **Lazy loading por tab** — solo cargar datos del tab activo | `DashboardMejorado.js` | 4 horas | Menos queries innecesarias |
| 10 | **Mensajes de error descriptivos** en frontend | `DashboardMejorado.js` | 2 horas | Mejor UX |
| 11 | **Validación de respuestas API** con schema | `analyticsApi.js` | 4 horas | Detectar errores temprano |
| 12 | **API_URL relativo** en producción (no localhost:81) | `analyticsApi.js` | 30 min | Portabilidad |

### P3 — Nice-to-have

| # | Mejora | Esfuerzo |
|---|--------|----------|
| 13 | Tests unitarios pytest para servicios backend | 5 días |
| 14 | Tests React con @testing-library | 3 días |
| 15 | Ordenamiento persistente en URL (query params) | 2 horas |
| 16 | Export PDF con gráficos | 2 días |
| 17 | Auto-refresh cada N minutos | 2 horas |
| 18 | Accesibilidad (aria-labels, roles) | 1 día |

---

## 7. Notas sobre Seguridad

> **No se realizan cambios de seguridad en esta auditoría.** El proyecto corre en Docker local sin exposición a internet y solo muestra métricas de lectura.

**Si en el futuro se expone a producción**, se recomienda:
- Restringir CORS (`allow_origins` específicos en vez de `["*"]`)
- Implementar autenticación JWT en endpoints
- Remover/proteger endpoints de debug (`/api/debug/`)
- Remover `.env` del repositorio git si contiene credenciales
- Activar security headers en Nginx (HSTS, X-Frame-Options, CSP)
- Cambiar JWT secret de desarrollo

---

## 8. Plan de Acción Resumido

```
Semana 1: Refactorización de código
├── Día 1-2: Dividir DashboardMejorado.js en componentes
├── Día 3: Extraer submétodos de get_kpis() + BaseAnalyticsService
├── Día 4: Promise.allSettled + React.memo + debouncing
└── Día 5: Calcular cambios reales vs período anterior

Semana 2: Testing + Polish
├── Día 1-3: Tests unitarios backend (pytest)
├── Día 4: Tests frontend (React Testing Library)
└── Día 5: Mejoras UX (mensajes error, lazy loading)

Futuro (solo si se expone):
└── Implementar medidas de seguridad listadas arriba
```

**Esfuerzo estimado total**: ~10 días-persona para mejoras de código, ~5 días para testing.

---

*Generado por agentes de auditoría automatizados — verificado contra 11 commits del 17/02/2026.*

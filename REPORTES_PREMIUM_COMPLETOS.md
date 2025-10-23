# 📊 REPORTES PREMIUM OMNILEADS - ANÁLISIS COMPLETO

## Basado en documentación oficial y código fuente premium_reports_app v1.3.6

---

## 📋 LISTA COMPLETA DE REPORTES

### ✅ YA IMPLEMENTADOS (nuestro sistema actual)

1. **Distribución General** - ✅ Parcial
   - Tenemos: KPIs, gráfico de distribución
   - Falta: Métricas específicas por campaña

2. **Llamadas Atendidas** - ✅ Implementado
   - Tabla detallada con callid, agente, duración, quién colgó

3. **Llamadas Abandonadas** - ✅ Implementado
   - Tabla con tipo de abandono clasificado

4. **Distribución Horaria** - ✅ Implementado
   - Gráfico multilinea con entrantes/salientes/abandonadas

5. **Nivel de Servicio** - ✅ Implementado
   - Gráfico de barras con rangos de tiempo

6. **Rendimiento de Agentes** - ✅ Implementado
   - Tabla con métricas por agente

7. **Campañas con Alertas** - ✅ Implementado
   - Tabla con niveles de atención y alertas

---

## ❌ REPORTES QUE FALTAN POR IMPLEMENTAR

### CATEGORÍA 1: DISTRIBUCIÓN AVANZADA

#### 📊 **Distribución por Campaña** (Gráfico Circular)
- **Archivo**: `templates/distribucion/distribucion_por_campana.html`
- **Descripción**: Gráfico circular mostrando % de llamadas por campaña
- **Métricas**:
  - Total llamadas por campaña
  - Porcentaje del total
  - Comparativa visual
- **Visualización**: Pie Chart con % por campaña

#### 📅 **Distribución por Día de Semana**
- **Descripción**: Llamadas agrupadas por día (Lunes-Domingo)
- **Métricas**:
  - Total llamadas por día
  - Promedio por día
  - Identificar días pico
- **Visualización**: Gráfico de barras

#### 📆 **Distribución por Mes**
- **Archivo**: `templates/distribucion/distribucion_por_mes.html`
- **Descripción**: Evolución mensual de llamadas
- **Métricas**:
  - Total llamadas por mes
  - Tendencia mensual
  - Comparativa año anterior
- **Visualización**: Line chart mensual

#### 🕐 **Distribución por Rango Horario**
- **Archivo**: `templates/distribucion/saliente_por_rango_horario.html`
- **Descripción**: Llamadas agrupadas por franjas horarias configurables
- **Métricas**:
  - Total por franja (ej: 8-12, 12-16, 16-20)
  - % de ocupación por franja
  - Horas pico
- **Visualización**: Heatmap o barras por rango

---

### CATEGORÍA 2: LLAMADAS SALIENTES (FALTA COMPLETAMENTE)

#### 📱 **Llamadas Salientes - Distribución General**
- **Archivo**: `templates/distribucion/saliente_por_dia.html`, `saliente_por_hora.html`
- **Descripción**: Métricas específicas de llamadas salientes
- **Métricas**:
  - Total marcadas (DIAL)
  - Total contactadas (ANSWER)
  - No contestadas (NOANSWER)
  - Ocupadas (BUSY)
  - Canceladas (CANCEL)
  - Tasa de contactación
- **Visualización**: Dashboard específico para outbound

#### 📞 **Llamadas Manuales**
- **Archivo**: `templates/distribucion/saliente_manuales.html`
- **Descripción**: Separar llamadas manuales vs dialer
- **Métricas**:
  - Llamadas manuales por agente
  - Efectividad de manuales
  - Tiempo promedio de marcado

---

### CATEGORÍA 3: CAUSAS DE DESCONEXIÓN/NO CONEXIÓN (MEJORAR)

#### 🔴 **Causas de Desconexión** (Mejorar actual)
- **Archivo**: `templates/llamadas_atendidas/causas_desconexion.html`
- **Descripción**: Análisis detallado de por qué terminan las llamadas
- **Eventos**:
  - COMPLETEAGENT (agente cuelga)
  - COMPLETEOUTNUM (cliente cuelga)
  - COMPLETE-CTOUT (transfer consultivo)
  - COMPLETE-BTOUT (transfer ciego)
- **Métricas**:
  - N° de llamadas por causa
  - % por causa
  - Tendencia temporal
- **Visualización**: Pie chart + tabla detallada

#### ⚠️ **Causas de No Conexión** (Mejorar actual)
- **Archivo**: `templates/no_atendidas/causas_no_conexion.html`
- **Descripción**: Por qué las llamadas no se conectaron
- **Eventos**:
  - ABANDON (abandono en cola)
  - ABANDONWEL (abandono en bienvenida)
  - EXITWITHTIMEOUT (timeout)
  - CONGESTION (congestión)
  - NONDIALPLAN (sin ruta)
  - CHANUNAVAIL (canal no disponible)
- **Métricas**:
  - N° por causa
  - % del total
  - Análisis temporal
- **Visualización**: Pie chart con todos los motivos

#### 📊 **Llamadas Sin Conexión por Agente y Campaña**
- **Archivo**: `templates/no_atendidas/llamadas_sin_conexion.html`
- **Descripción**: Desglose de llamadas sin conexión
- **Tablas**:
  1. Por Agente: ID, Nombre, N° llamadas, %
  2. Por Campaña: ID, Nombre, N° llamadas, %
- **Útil para**: Identificar problemas específicos de agente o campaña

---

### CATEGORÍA 4: REPORTES DE AGENTES (AMPLIAR)

#### 👥 **Total de Sesiones**
- **Archivo**: `templates/reporte_agente/total_sesiones.html`
- **Descripción**: Resumen de sesiones de todos los agentes
- **Métricas Globales**:
  - N° de agentes disponibles
  - Tiempo promedio de sesión
  - Tiempo mínimo de sesión
  - Tiempo máximo de sesión
  - Tiempo total acumulado
- **Visualización**: Cards con métricas + histograma de distribución

#### 📅 **Número de Agentes por Día/Hora**
- **Archivo**: `templates/reporte_agente/numero_agentes.html`
- **Descripción**: Heatmap de disponibilidad de agentes
- **Estructura**:
  - Eje X: Horas (0-23)
  - Eje Y: Días de la semana
  - Valor: N° de agentes logueados
- **Visualización**: Heatmap + gráfico de barras
- **Útil para**: Planificación de personal, identificar gaps de cobertura

#### ⏱️ **Disponibilidad de Agentes** (Ampliar actual)
- **Archivo**: `templates/reporte_agente/disponibilidad_agentes.html`
- **Descripción**: Métricas detalladas de uso del tiempo
- **Columnas adicionales necesarias**:
  - Time on Hold (tiempo en espera)
  - Session N° (número de logins/logouts)
  - Number of Pausas
  - Time Total de Waiting
  - Time Total de Pausa
  - Promedio de Pausa
  - % de ocupación = (Tiempo en llamada / Tiempo total sesión) × 100

---

### CATEGORÍA 5: NIVEL DE SERVICIO (AMPLIAR)

#### 🎯 **Nivel de Servicio Detallado**
- **Archivo**: `templates/llamadas_atendidas/nivel_servicio.html`
- **Descripción**: Distribución de tiempos de espera en bloques
- **Bloques sugeridos** (configurables):
  - 0-10 segundos
  - 11-20 segundos
  - 21-30 segundos
  - 31-60 segundos
  - 61-120 segundos
  - >120 segundos
- **Columnas**:
  - Rango
  - N° llamadas
  - Delta (incremento)
  - % del total
  - % acumulado
- **Visualización**: Barras + línea acumulativa

---

### CATEGORÍA 6: TRANSFERENCIAS (NUEVO - CRÍTICO)

#### 🔄 **Análisis de Transferencias**
- **Descripción**: Métricas de llamadas transferidas
- **Eventos**:
  - CT-TRY (intento transfer consultivo)
  - CT-ANSWER (transfer consultivo atendido)
  - CT-BUSY (transfer consultivo ocupado)
  - CT-DISCARD (transfer consultivo descartado)
  - BTOUT-TRY (intento transfer ciego)
  - BTOUT-ANSWER (transfer ciego atendido)
  - COMPLETE-CT (completado consultivo)
  - COMPLETE-BTOUT (completado ciego)
- **Métricas**:
  - Total intentos de transfer
  - % exitosos
  - % fallidos
  - Tiempo promedio de transfer
  - Transfer por agente
  - Transfer por campaña
- **Visualización**: Funnel chart + tabla detallada

---

## 🎨 MEJORAS DE VISUALIZACIÓN NECESARIAS

### 1. **Dashboard Principal Mejorado**
Basado en el archivo: `templates/premium_reports.html`

**Estructura sugerida:**
```
┌─────────────────────────────────────────────┐
│  FILTROS AVANZADOS (sidebar colapsable)    │
├─────────────────────────────────────────────┤
│  OVERVIEW - 12 KPIs principales             │
├─────────────────────────────────────────────┤
│  GRÁFICOS PRINCIPALES (Grid 2x2)            │
│  - Distribución por campaña (pie)           │
│  - Evolución temporal (line)                │
│  - Horas pico (bar)                         │
│  - Agentes disponibles (heatmap)            │
├─────────────────────────────────────────────┤
│  PESTAÑAS DE REPORTES DETALLADOS            │
│  1. Distribución                            │
│  2. Llamadas Atendidas                      │
│  3. Llamadas Abandonadas                    │
│  4. No Atendidas                            │
│  5. Agentes                                 │
│  6. Transferencias (NUEVO)                  │
│  7. Campañas                                │
└─────────────────────────────────────────────┘
```

### 2. **Sistema de Filtros Avanzado**
Basado en documentación, implementar:

**Filtros de Objetos:**
- ☑️ Tipo de campaña (All, Entrantes, Salientes Manual, Dialer, Preview)
- ☑️ Campañas específicas (multi-select)
- ☑️ Grupos de agentes
- ☑️ Agentes específicos
- ☑️ Inclusión de llamadas manuales (checkbox)
- ☑️ Número telefónico (búsqueda)
- ☑️ CallID (búsqueda)
- ☑️ Tipo de conexión (Fallidas, Exitosas, Todas)

**Filtros Temporales:**
- ☑️ Fecha inicio / fin
- ☑️ Días de la semana (checkbox: L M M J V S D)
- ☑️ Rangos horarios (multi-select: 00-04, 04-08, etc.)
- ☑️ Ajuste de zona horaria (+/- horas)

**Parámetros de Servicio:**
- ☑️ Service Level (segundos)
- ☑️ Tiempo máximo de sesión estimado

---

## 📊 TABLAS Y GRÁFICOS POR IMPLEMENTAR

### Gráficos Faltantes:
1. ✅ Pie Chart - Distribución por campaña
2. ✅ Box Plot - Duraciones de sesiones (Min, Q1, Q2, Q3, Max)
3. ✅ Heatmap - Número de agentes por día/hora
4. ✅ Funnel Chart - Proceso de transferencias
5. ✅ Line Chart - Tendencia mensual
6. ✅ Stacked Bar - Llamadas salientes (marcadas, contactadas, fallidas)

### Tablas Faltantes:
1. ✅ Detalle de transferencias
2. ✅ Llamadas sin conexión por agente
3. ✅ Llamadas sin conexión por campaña
4. ✅ Duraciones de sesiones
5. ✅ Llamadas manuales vs dialer

---

## 🔢 MÉTRICAS Y FÓRMULAS DOCUMENTADAS

### Fórmulas Oficiales:

1. **Tiempo Promedio de Espera**
   ```
   = SUM(bridge_wait_time) / COUNT(llamadas)
   ```

2. **Tiempo Promedio al Habla**
   ```
   = SUM(duracion_llamada) / COUNT(llamadas_atendidas)
   ```

3. **% de Ocupación del Agente**
   ```
   = (Tiempo en llamada / Tiempo total de sesión) × 100
   ```

4. **Promedio de Sesión**
   ```
   = Tiempo total de sesión / Número de sesiones
   ```

5. **Promedio de Pausa**
   ```
   = Tiempo total de pausa / Número de pausas
   ```

6. **% Llamadas Atendidas**
   ```
   = (Llamadas atendidas / Total llamadas procesadas) × 100
   ```

7. **% Llamadas No Atendidas**
   ```
   = (Llamadas no atendidas / Total llamadas procesadas) × 100
   ```

8. **Tasa de Contactación (Outbound)**
   ```
   = (ANSWER / DIAL) × 100
   ```

---

## 🎯 PLAN DE IMPLEMENTACIÓN PRIORIZADO

### FASE 1: REPORTES CRÍTICOS (Alta Prioridad) - 2-3 días

1. **Distribución por Campaña** (Pie Chart)
   - Endpoint: `/api/analytics/distribucion-campanas-detalle`
   - Componente: `CampanasPieChart.js`

2. **Causas de Desconexión Completo**
   - Mejorar endpoint existente con más eventos
   - Pie chart + tabla detallada

3. **Causas de No Conexión Completo**
   - Incluir TODOS los eventos (CONGESTION, NONDIALPLAN, etc.)
   - Visualización mejorada

4. **Llamadas Sin Conexión por Agente/Campaña**
   - Endpoint: `/api/analytics/sin-conexion-por-agente`
   - Endpoint: `/api/analytics/sin-conexion-por-campana`
   - Tablas comparativas

### FASE 2: REPORTES DE AGENTES (Alta Prioridad) - 2 días

5. **Total de Sesiones**
   - Endpoint: `/api/analytics/agentes/total-sesiones`
   - Cards con métricas globales + histograma

6. **Número de Agentes por Día/Hora**
   - Endpoint: `/api/analytics/agentes/disponibilidad-heatmap`
   - Heatmap component con ApexCharts

7. **Disponibilidad Mejorada**
   - Ampliar endpoint actual con: pausas, waiting, ocupación

### FASE 3: DISTRIBUCIÓN TEMPORAL (Media Prioridad) - 2 días

8. **Distribución por Día de Semana**
   - Endpoint: `/api/analytics/distribucion-por-dia-semana`
   - Bar chart Lun-Dom

9. **Distribución por Mes**
   - Endpoint: `/api/analytics/distribucion-por-mes`
   - Line chart con tendencia

10. **Distribución por Rango Horario**
    - Endpoint: `/api/analytics/distribucion-rangos-horarios`
    - Configurable (8-12, 12-16, 16-20, 20-24)

### FASE 4: LLAMADAS SALIENTES (Media Prioridad) - 2 días

11. **Dashboard de Llamadas Salientes**
    - Endpoint: `/api/analytics/salientes/resumen`
    - KPIs específicos outbound

12. **Llamadas Manuales vs Dialer**
    - Endpoint: `/api/analytics/salientes/manuales-vs-dialer`
    - Comparativa

### FASE 5: TRANSFERENCIAS (Baja Prioridad) - 1-2 días

13. **Análisis de Transferencias**
    - Endpoint: `/api/analytics/transferencias`
    - Funnel chart + métricas

### FASE 6: FILTROS AVANZADOS (Baja Prioridad) - 1 día

14. **Sistema de Filtros Completo**
    - Componente: `FiltrosAvanzados.js`
    - Todos los filtros del PDF

### FASE 7: NIVEL DE SERVICIO DETALLADO (Baja Prioridad) - 1 día

15. **Nivel de Servicio con Bloques Configurables**
    - Ampliar endpoint actual
    - Línea acumulativa

---

## 📄 EXPORTACIÓN

**TODAS las tablas deben permitir**:
- ✅ Exportar a CSV
- ✅ Exportar a Excel (opcional)
- ✅ Copiar al portapapeles
- ✅ Imprimir

---

## 🎬 RESUMEN EJECUTIVO

**Total de Reportes en Premium:**
- ✅ Implementados: 7
- ❌ Faltantes: 15
- **Total**: 22 reportes

**Trabajo Estimado**: 10-12 días de desarrollo

**Prioridad Inmediata** (Fase 1-2):
1. Distribución por campaña (pie chart)
2. Causas detalladas (desconexión y no conexión)
3. Sin conexión por agente/campaña
4. Total de sesiones
5. Heatmap de disponibilidad

¿Quieres que implemente la Fase 1 ahora mismo?

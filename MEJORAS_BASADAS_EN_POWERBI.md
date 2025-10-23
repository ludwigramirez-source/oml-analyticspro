# 📊 Mejoras al Módulo de Analytics Basadas en Power BI

## Análisis del Reporte Power BI de Capresoca

Basado en el análisis del reporte Power BI existente, he identificado las siguientes mejoras y ajustes necesarios para nuestro módulo de analytics.

---

## 🎯 MÉTRICAS CLAVE IDENTIFICADAS EN POWER BI

### 1. **Nivel de Atención** - 90.79%
**Fórmula:** `(Llamadas Entrantes Atendidas / Total Llamadas Entrantes) × 100`

**Cálculo por Campaña:**
```
- PQRS: (23/24) × 100 = 95.83%
- ATENCION_AL_USUARIO: (144/146) × 100 = 95.07%
- REFERENCIA: (15/16) × 100 = 93.75%
- ASEGURAMIENTO: (35/58) × 100 = 70.73% ⚠️ (BAJO)
```

**Implementación Actual:** ✅ Ya implementado en `get_kpis()` como Service Level
**Acción:** Agregar cálculo por campaña y alertas para campañas con nivel bajo (<80%)

---

### 2. **Nivel de Servicio < 60 seg** - 84.94%
**Fórmula:** `(Llamadas atendidas en <60 segundos / Total llamadas atendidas) × 100`

**Implementación Actual:** ⚠️ Parcialmente implementado (actualmente usa 20 segundos)
**Acción:** Cambiar threshold de 20s a 60s y renombrar

---

### 3. **Nivel de Conversación (Duración Promedio)** - 219.63 segundos
**Fórmula:** `AVG(duracion_llamada) para llamadas atendidas`

**Implementación Actual:** ✅ Ya implementado como TMO
**Acción:** Renombrar para claridad

---

### 4. **Clasificación de Llamadas**

Power BI clasifica las llamadas en:

#### **Llamadas Entrantes:**
- **Atendidas**: 217 llamadas
- **Abandonadas**: 27 llamadas
- **Total**: 244 llamadas

#### **Llamadas Salientes:**
- **Atendidas**: 21 llamadas
- **No Atendidas**: 9 llamadas
- **Total**: 30 llamadas

**Implementación Actual:** ❌ NO distingue entre entrantes y salientes
**Acción:** **CRÍTICO** - Agregar campo `tipo_llamada` para diferenciar ENTRANTE vs SALIENTE

---

## 🔧 MEJORAS NECESARIAS

### **PRIORIDAD ALTA** 🔴

#### 1. Agregar Diferenciación Entrante/Saliente
```python
# En call_analytics.py
def get_distribucion_llamadas_por_tipo(self, filters: Dict = None) -> Dict:
    """Distribución separando llamadas entrantes y salientes"""
    query = self.db.query(LlamadaLog)
    query = self._apply_filters(query, filters)
    
    # tipo_llamada: 1=Entrante, 2=Saliente, 3=Transferencia
    entrantes = query.filter(LlamadaLog.tipo_llamada == 1).count()
    salientes = query.filter(LlamadaLog.tipo_llamada == 2).count()
    
    # Separar atendidas y no atendidas por tipo
    entrantes_atendidas = query.filter(
        LlamadaLog.tipo_llamada == 1,
        LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
    ).count()
    
    entrantes_abandonadas = query.filter(
        LlamadaLog.tipo_llamada == 1,
        LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
    ).count()
    
    salientes_atendidas = query.filter(
        LlamadaLog.tipo_llamada == 2,
        LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
    ).count()
    
    salientes_no_atendidas = query.filter(
        LlamadaLog.tipo_llamada == 2,
        LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
    ).count()
    
    return {
        'entrantes': {
            'total': entrantes,
            'atendidas': entrantes_atendidas,
            'abandonadas': entrantes_abandonadas,
            'nivel_atencion': round(entrantes_atendidas / entrantes * 100, 2) if entrantes > 0 else 0
        },
        'salientes': {
            'total': salientes,
            'atendidas': salientes_atendidas,
            'no_atendidas': salientes_no_atendidas,
            'nivel_atencion': round(salientes_atendidas / salientes * 100, 2) if salientes > 0 else 0
        }
    }
```

#### 2. Cambiar Service Level de 20s a 60s
```python
# En call_analytics.py - Método get_kpis()
# Cambiar línea 73:
sla_threshold = 60  # Era 20, ahora 60 segundos según Power BI
```

#### 3. Agregar Nivel de Atención por Campaña con Alertas
```python
def get_nivel_atencion_por_campana(self, filters: Dict = None) -> List[Dict]:
    """
    Obtiene el nivel de atención por campaña con alertas
    """
    filters = filters or {}
    query = self.db.query(
        Campana.nombre,
        func.count(LlamadaLog.id).label('total'),
        func.sum(
            case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
        ).label('atendidas')
    ).join(
        LlamadaLog, Campana.id == LlamadaLog.campana_id
    )
    
    query = self._apply_filters(query, filters)
    
    resultados = query.group_by(Campana.nombre).all()
    
    campanias = []
    for r in resultados:
        nivel = round(r.atendidas / r.total * 100, 2) if r.total > 0 else 0
        
        # Determinar estado según nivel
        if nivel >= 90:
            estado = 'excelente'
            color = 'green'
        elif nivel >= 80:
            estado = 'bueno'
            color = 'yellow'
        else:
            estado = 'critico'  # Como ASEGURAMIENTO con 70.73%
            color = 'red'
        
        campanias.append({
            'campana': r.nombre,
            'total_llamadas': r.total,
            'atendidas': r.atendidas,
            'nivel_atencion': nivel,
            'estado': estado,
            'color': color
        })
    
    return campanias
```

---

### **PRIORIDAD MEDIA** 🟡

#### 4. Detalle de Llamadas por Agente (como en Power BI)
```python
def get_detalle_llamadas_por_agente(self, filters: Dict = None) -> List[Dict]:
    """
    Detalle de llamadas por agente con entrantes, salientes y duración promedio
    Similar al reporte "Detalle LLamadas por Agentes" de Power BI
    """
    query = self.db.query(
        User.email.label('agente_email'),
        User.first_name,
        User.last_name,
        func.count(
            case((LlamadaLog.tipo_llamada == 1, 1), else_=None)
        ).label('entrantes'),
        func.count(
            case((LlamadaLog.tipo_llamada == 2, 1), else_=None)
        ).label('salientes'),
        func.avg(LlamadaLog.duracion_llamada).label('prom_duracion')
    ).join(
        AgenteProfile, User.id == AgenteProfile.user_id
    ).join(
        LlamadaLog, AgenteProfile.id == LlamadaLog.agente_id
    )
    
    query = self._apply_filters(query, filters)
    
    resultados = query.group_by(
        User.email, User.first_name, User.last_name
    ).all()
    
    return [{
        'agente': f'{r.first_name} {r.last_name}',
        'email': r.agente_email,
        'entrantes': r.entrantes or 0,
        'salientes': r.salientes or 0,
        'promedio_duracion': int(r.prom_duracion) if r.prom_duracion else 0
    } for r in resultados]
```

#### 5. Distribución Horaria Mejorada
```python
def get_distribucion_horaria_detallada(self, filters: Dict = None) -> Dict:
    """
    Distribución horaria separando entrantes, salientes y abandonadas
    Como en el gráfico "Distribución Horaria" de Power BI
    """
    query = self.db.query(LlamadaLog)
    query = self._apply_filters(query, filters)
    
    # Agrupar por hora del día
    resultados = query.with_entities(
        extract('hour', LlamadaLog.time).label('hora'),
        LlamadaLog.tipo_llamada,
        LlamadaLog.event,
        func.count(LlamadaLog.id).label('total')
    ).group_by('hora', LlamadaLog.tipo_llamada, LlamadaLog.event).all()
    
    # Inicializar arrays
    horas = list(range(24))
    entrantes = [0] * 24
    salientes = [0] * 24
    abandonadas = [0] * 24
    
    for r in resultados:
        hora_idx = int(r.hora)
        if r.tipo_llamada == 1:  # Entrante
            entrantes[hora_idx] += r.total
            if r.event in self.EVENTOS_NO_ATENDIDAS:
                abandonadas[hora_idx] += r.total
        elif r.tipo_llamada == 2:  # Saliente
            salientes[hora_idx] += r.total
    
    return {
        'labels': [f'{h:02d}:00' for h in horas],
        'datasets': [
            {
                'label': 'Llamadas Entrantes',
                'data': entrantes,
                'borderColor': 'rgba(23, 162, 184, 1)',  # Teal como Power BI
                'backgroundColor': 'rgba(23, 162, 184, 0.1)'
            },
            {
                'label': 'Abandonadas',
                'data': abandonadas,
                'borderColor': 'rgba(220, 53, 69, 1)',  # Rojo
                'backgroundColor': 'rgba(220, 53, 69, 0.1)'
            },
            {
                'label': 'Salientes',
                'data': salientes,
                'borderColor': 'rgba(0, 123, 255, 1)',  # Azul
                'backgroundColor': 'rgba(0, 123, 255, 0.1)'
            }
        ]
    }
```

---

### **PRIORIDAD BAJA** 🟢

#### 6. Total Llamadas por Mes (Gráfico de Barras)
```python
def get_total_llamadas_por_mes(self, anio: int = None) -> Dict:
    """
    Total de llamadas por mes separando entrantes y salientes
    Como el gráfico "Total Llamadas x Mes" de Power BI
    """
    query = self.db.query(
        extract('month', LlamadaLog.time).label('mes'),
        LlamadaLog.tipo_llamada,
        func.count(LlamadaLog.id).label('total')
    )
    
    if anio:
        query = query.filter(extract('year', LlamadaLog.time) == anio)
    
    resultados = query.group_by('mes', LlamadaLog.tipo_llamada).all()
    
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    entrantes = [0] * 12
    salientes = [0] * 12
    
    for r in resultados:
        mes_idx = int(r.mes) - 1
        if r.tipo_llamada == 1:
            entrantes[mes_idx] = r.total
        elif r.tipo_llamada == 2:
            salientes[mes_idx] = r.total
    
    return {
        'labels': meses,
        'datasets': [
            {
                'label': 'Entrantes',
                'data': entrantes,
                'backgroundColor': 'rgba(23, 162, 184, 0.8)'
            },
            {
                'label': 'Salientes',
                'data': salientes,
                'backgroundColor': 'rgba(0, 123, 255, 0.8)'
            }
        ]
    }
```

---

## 📋 NUEVOS ENDPOINTS A CREAR

```python
# En analytics_routes.py

@router.get("/llamadas-por-tipo")
async def get_llamadas_por_tipo(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución separando entrantes y salientes"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_llamadas_por_tipo(filters)


@router.get("/nivel-atencion-campanas")
async def get_nivel_atencion_campanas(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Nivel de atención por campaña con alertas"""
    service = CallAnalyticsService(db)
    return service.get_nivel_atencion_por_campana(filters)


@router.get("/agentes/detalle-llamadas")
async def get_detalle_agentes(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Detalle de llamadas por agente (entrantes/salientes)"""
    service = CallAnalyticsService(db)
    return service.get_detalle_llamadas_por_agente(filters)


@router.get("/distribucion-horaria-detallada")
async def get_dist_horaria_detallada(
    filters: dict = Depends(parse_filters),
    db: Session = Depends(get_db)
):
    """Distribución horaria con entrantes, salientes y abandonadas"""
    service = CallAnalyticsService(db)
    return service.get_distribucion_horaria_detallada(filters)


@router.get("/llamadas-por-mes")
async def get_llamadas_mes(
    anio: int = Query(None, description="Año"),
    db: Session = Depends(get_db)
):
    """Total llamadas por mes (entrantes/salientes)"""
    service = CallAnalyticsService(db)
    return service.get_total_llamadas_por_mes(anio)
```

---

## 🎨 MEJORAS AL DASHBOARD FRONTEND

### 1. Agregar Sección "Llamadas Entrantes vs Salientes"
```jsx
{/* Nuevo componente en Dashboard */}
<div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
  {/* Llamadas Entrantes */}
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h3 className="text-xl font-bold text-gray-800 mb-4">
      📞 Llamadas Entrantes
    </h3>
    <div className="text-4xl font-bold text-teal-600 mb-2">
      {datosEntrantes.total}
    </div>
    <div className="grid grid-cols-2 gap-4 mt-4">
      <div>
        <p className="text-sm text-gray-600">Atendidas</p>
        <p className="text-2xl font-semibold text-green-600">
          {datosEntrantes.atendidas}
        </p>
      </div>
      <div>
        <p className="text-sm text-gray-600">Abandonadas</p>
        <p className="text-2xl font-semibold text-red-600">
          {datosEntrantes.abandonadas}
        </p>
      </div>
    </div>
    <div className="mt-4 p-3 bg-teal-50 rounded">
      <p className="text-sm font-medium text-teal-800">
        Nivel de Atención: {datosEntrantes.nivel_atencion}%
      </p>
    </div>
  </div>

  {/* Llamadas Salientes */}
  <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
    <h3 className="text-xl font-bold text-gray-800 mb-4">
      📱 Llamadas Salientes
    </h3>
    <div className="text-4xl font-bold text-blue-600 mb-2">
      {datosSalientes.total}
    </div>
    <div className="grid grid-cols-2 gap-4 mt-4">
      <div>
        <p className="text-sm text-gray-600">Atendidas</p>
        <p className="text-2xl font-semibold text-green-600">
          {datosSalientes.atendidas}
        </p>
      </div>
      <div>
        <p className="text-sm text-gray-600">No Atendidas</p>
        <p className="text-2xl font-semibold text-orange-600">
          {datosSalientes.no_atendidas}
        </p>
      </div>
    </div>
    <div className="mt-4 p-3 bg-blue-50 rounded">
      <p className="text-sm font-medium text-blue-800">
        Nivel de Atención: {datosSalientes.nivel_atencion}%
      </p>
    </div>
  </div>
</div>
```

### 2. Tabla con Alertas por Campaña
```jsx
{/* Tabla con formato condicional como Power BI */}
<table className="min-w-full divide-y divide-gray-200">
  <thead className="bg-gray-50">
    <tr>
      <th>Campaña</th>
      <th>Cantidad Agentes</th>
      <th>Llamadas Entrantes</th>
      <th>Atendidas</th>
      <th>Abandonadas</th>
      <th>Nivel de Atención</th>
      <th>Prom. Duración</th>
    </tr>
  </thead>
  <tbody>
    {campanias.map((c, idx) => (
      <tr key={idx}>
        <td>{c.campana}</td>
        <td>{c.cantidad_agentes}</td>
        <td>{c.llamadas_entrantes}</td>
        <td className="text-green-600">{c.atendidas}</td>
        <td className="text-red-600">{c.abandonadas}</td>
        <td>
          <span className={`px-3 py-1 rounded font-semibold ${
            c.nivel_atencion >= 90 ? 'bg-green-100 text-green-800' :
            c.nivel_atencion >= 80 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
          }`}>
            {c.nivel_atencion}%
          </span>
        </td>
        <td>{c.prom_duracion}s</td>
      </tr>
    ))}
  </tbody>
</table>
```

---

## 📊 RESUMEN DE CAMBIOS

| Métrica/Feature | Estado Actual | Requiere Cambio | Prioridad |
|----------------|---------------|-----------------|-----------|
| Nivel de Atención | ✅ Implementado | ✅ Agregar por campaña | 🔴 Alta |
| Service Level < 60s | ⚠️ Usa 20s | ✅ Cambiar a 60s | 🔴 Alta |
| Entrantes vs Salientes | ❌ No distingue | ✅ Agregar separación completa | 🔴 Alta |
| Duración Promedio | ✅ Implementado | ✅ Renombrar | 🟢 Baja |
| Distribución Horaria | ✅ Implementado | ✅ Agregar abandonadas | 🟡 Media |
| Detalle por Agente | ✅ Implementado | ✅ Agregar entrantes/salientes | 🟡 Media |
| Total x Mes | ❌ No existe | ✅ Crear nuevo | 🟢 Baja |
| Alertas por Campaña | ❌ No existe | ✅ Crear nuevo | 🔴 Alta |

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Paso 1: Cambios en Backend (2-3 horas)
1. ✅ Modificar `get_kpis()` - Cambiar SLA de 20s a 60s
2. ✅ Crear `get_distribucion_llamadas_por_tipo()` - Entrantes vs Salientes
3. ✅ Crear `get_nivel_atencion_por_campana()` - Con alertas
4. ✅ Crear `get_detalle_llamadas_por_agente()` - Con entrantes/salientes
5. ✅ Modificar `get_evolucion_por_hora()` - Agregar abandonadas
6. ✅ Crear endpoints en `analytics_routes.py`

### Paso 2: Cambios en Frontend (2-3 horas)
1. ✅ Agregar sección Entrantes vs Salientes
2. ✅ Actualizar tabla de campañas con formato condicional
3. ✅ Actualizar gráfico de distribución horaria
4. ✅ Agregar gráfico de llamadas por mes

### Paso 3: Testing (1 hora)
1. ✅ Probar todos los nuevos endpoints
2. ✅ Verificar que los datos coincidan con Power BI
3. ✅ Validar alertas de campañas

---

## 📝 NOTAS IMPORTANTES

1. **Tipo de Llamada en BD:**
   - Verificar valores en `tipo_llamada`: 1=Entrante, 2=Saliente, 3=Transferencia
   - Si usa otros códigos, ajustar en el código

2. **Umbral de Alertas:**
   - Power BI marca en rojo campañas con <80% de nivel de atención
   - Configurar esto como variable ajustable

3. **Emails de Agentes:**
   - Power BI muestra emails (agente01@capresoca.com)
   - Nuestro sistema muestra nombres completos
   - Mantener ambos disponibles

4. **Horario de Operación:**
   - Power BI muestra de 7 AM a 5 PM
   - Nuestro sistema muestra 24 horas
   - Agregar filtro configurable

---

¿Quieres que implemente estas mejoras ahora?

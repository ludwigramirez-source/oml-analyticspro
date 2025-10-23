# 📊 OmniLeads Analytics - Módulo de Reportes

Sistema completo de análisis y reportes para OmniLeads Call Center construido con **FastAPI + React + PostgreSQL**.

## 🎯 Características Implementadas

### ✅ KPIs Principales
- Llamadas Totales
- Llamadas Atendidas
- Llamadas Perdidas
- TMO (Tiempo Medio de Operación) Promedio
- Tiempo de Espera Promedio
- Service Level (% atendidas en <20s)
- Agentes Activos
- Ocupación de Agentes

### ✅ Reportes y Visualizaciones
1. **Distribución de Llamadas**
   - Gráfico de dona con llamadas atendidas/abandonadas/no atendidas
   - Evolución de llamadas por hora

2. **Llamadas Atendidas**
   - Nivel de servicio por rangos de tiempo
   - Tabla detallada de todas las llamadas atendidas

3. **Llamadas No Atendidas**
   - Gráfico circular de causas de no atención
   - Análisis de motivos (abandono, timeout, busy, etc.)

4. **Agentes**
   - Gráfico de ocupación por agente (tiempo en llamada/disponible/pausa)
   - Tabla de rendimiento con métricas individuales
   - Estados en tiempo real

5. **Campañas**
   - Tabla comparativa de todas las campañas
   - Tasa de atención por campaña

### ✅ Sistema de Filtros
- Filtro por rango de fechas
- Filtro por campaña
- Filtro por agente
- Filtro por tipo de campaña

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────┐
│                  FRONTEND                       │
│            React + Chart.js                     │
│         (Puerto 3000)                           │
└──────────────┬──────────────────────────────────┘
               │ HTTP/REST API
               │
┌──────────────▼──────────────────────────────────┐
│                  BACKEND                        │
│            FastAPI + SQLAlchemy                 │
│         (Puerto 8001)                           │
└──────────────┬──────────────────────────────────┘
               │ READ-ONLY Connection
               │
┌──────────────▼──────────────────────────────────┐
│           PostgreSQL 11+                        │
│        Base de Datos OmniLeads                  │
│         (Puerto 5432)                           │
└─────────────────────────────────────────────────┘
```

---

## 📁 Estructura del Proyecto

```
/app/
├── backend/
│   ├── analytics/                    # Módulo de Analytics
│   │   ├── config.py                # Configuración de PostgreSQL
│   │   ├── database.py              # Gestión de conexión
│   │   ├── models/
│   │   │   └── omnileads_models.py  # Modelos SQLAlchemy (READ-ONLY)
│   │   ├── services/
│   │   │   ├── call_analytics.py    # Servicio de análisis de llamadas
│   │   │   └── agent_analytics.py   # Servicio de análisis de agentes
│   │   └── routes/
│   │       └── analytics_routes.py  # Endpoints REST API
│   ├── server.py                    # Servidor FastAPI principal
│   └── .env                         # Variables de entorno
│
└── frontend/
    ├── src/
    │   ├── components/
    │   │   └── analytics/
    │   │       ├── AnalyticsDashboard.js  # Dashboard principal
    │   │       ├── KPICard.js             # Componente de KPI
    │   │       ├── FilterSection.js       # Filtros
    │   │       ├── ChartCard.js           # Gráficos
    │   │       ├── TablaLlamadas.js       # Tabla de llamadas
    │   │       └── TablaAgentes.js        # Tabla de agentes
    │   ├── services/
    │   │   └── analyticsApi.js            # Cliente API
    │   └── App.js
    └── package.json
```

---

## ⚙️ Configuración

### 1. Credenciales de PostgreSQL

Edita el archivo `/app/backend/.env` y configura las credenciales de tu base de datos OmniLeads:

```bash
# ============================================
# CONFIGURACIÓN POSTGRESQL OMNILEADS
# ============================================
OMNILEADS_DB_HOST=tu-servidor-postgresql
OMNILEADS_DB_PORT=5432
OMNILEADS_DB_NAME=omnileads
OMNILEADS_DB_USER=omnileads_readonly
OMNILEADS_DB_PASSWORD=tu-contraseña-segura
```

### 2. Crear Usuario READ-ONLY en PostgreSQL

Para garantizar que el módulo de analytics **NO pueda modificar datos**, crea un usuario con permisos de solo lectura:

```sql
-- Conectarse a PostgreSQL como superusuario
psql -U postgres

-- Crear usuario readonly
CREATE USER omnileads_readonly WITH PASSWORD 'tu-contraseña-segura';

-- Otorgar permisos de conexión
GRANT CONNECT ON DATABASE omnileads TO omnileads_readonly;

-- Conectarse a la base de datos
\c omnileads

-- Otorgar permisos de SELECT en todas las tablas
GRANT SELECT ON ALL TABLES IN SCHEMA public TO omnileads_readonly;

-- Otorgar permisos automáticos en tablas futuras
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO omnileads_readonly;

-- Verificar que la conexión sea READ-ONLY
ALTER USER omnileads_readonly SET default_transaction_read_only = on;
```

### 3. Reiniciar Servicios

```bash
# Reiniciar backend para cargar nueva configuración
sudo supervisorctl restart backend

# Verificar que esté corriendo
sudo supervisorctl status
```

---

## 🚀 Uso

### Acceder al Dashboard

1. Abre tu navegador en: `http://localhost:3000` (desarrollo) o tu URL de producción
2. El dashboard cargará automáticamente con los datos actuales
3. Usa los filtros para personalizar las vistas
4. Navega entre las pestañas para ver diferentes reportes

### Endpoints de la API

Todos los endpoints están bajo `/api/analytics`:

#### KPIs y Métricas Generales
- `GET /api/analytics/test` - Test de conexión
- `GET /api/analytics/kpis` - KPIs principales
- `GET /api/analytics/distribucion-llamadas` - Distribución de llamadas
- `GET /api/analytics/evolucion-hora` - Evolución por hora

#### Llamadas
- `GET /api/analytics/nivel-servicio` - Nivel de servicio detallado
- `GET /api/analytics/causas-no-atencion` - Causas de no atención
- `GET /api/analytics/llamadas-detalladas?page=1&per_page=50` - Lista paginada
- `GET /api/analytics/distribucion-campanas` - Por campaña

#### Agentes
- `GET /api/analytics/agentes/rendimiento` - Rendimiento de agentes
- `GET /api/analytics/agentes/ocupacion` - Ocupación de agentes
- `GET /api/analytics/pausas/distribucion` - Distribución de pausas

#### Listas Auxiliares
- `GET /api/analytics/campanas` - Lista de campañas
- `GET /api/analytics/agentes` - Lista de agentes

#### Parámetros de Filtro (Query Parameters)
Todos los endpoints aceptan:
- `fecha_inicio` - Fecha inicio (YYYY-MM-DD)
- `fecha_fin` - Fecha fin (YYYY-MM-DD)
- `campana_id` - ID de campaña
- `tipo_campana` - Tipo de campaña
- `agente_id` - ID de agente

Ejemplo:
```bash
curl "http://localhost:8001/api/analytics/kpis?fecha_inicio=2024-01-01&fecha_fin=2024-01-31&campana_id=5"
```

---

## 📊 Tablas de Base de Datos Utilizadas

### Principales
- `reportes_app_llamadalog` - Logs de todas las llamadas
- `reportes_app_actividadagentelog` - Actividad de agentes
- `ominicontacto_app_campana` - Información de campañas
- `ominicontacto_app_agenteprofile` - Perfiles de agentes
- `ominicontacto_app_pausa` - Tipos de pausas
- `auth_user` - Usuarios (para nombres de agentes)

---

## 🔧 Troubleshooting

### Error: "Cannot connect to PostgreSQL"

1. Verifica que PostgreSQL esté corriendo:
   ```bash
   sudo -u postgres pg_ctlcluster 15 main status
   ```

2. Verifica las credenciales en `.env`

3. Revisa los logs:
   ```bash
   tail -50 /var/log/supervisor/backend.err.log
   ```

### Error: "No data shown in dashboard"

1. Verifica que la BD tenga datos:
   ```bash
   sudo -u postgres psql omnileads -c "SELECT COUNT(*) FROM reportes_app_llamadalog;"
   ```

2. Verifica permisos del usuario:
   ```bash
   sudo -u postgres psql omnileads -c "\du omnileads_readonly"
   ```

### Frontend no carga

1. Verifica que el backend esté corriendo:
   ```bash
   curl http://localhost:8001/api/analytics/test
   ```

2. Revisa logs del frontend:
   ```bash
   tail -50 /var/log/supervisor/frontend.err.log
   ```

---

## 📈 Métricas Calculadas

### Service Level
Porcentaje de llamadas atendidas en menos de 20 segundos respecto al total de llamadas atendidas.

```
Service Level = (Llamadas atendidas en <20s / Total llamadas atendidas) × 100
```

### TMO (Tiempo Medio de Operación)
Promedio de duración de todas las llamadas atendidas.

```
TMO = Σ(duracion_llamada) / Total llamadas atendidas
```

### Ocupación
Porcentaje de tiempo que los agentes están en llamadas respecto al tiempo disponible.

```
Ocupación = (Tiempo total en llamadas / Tiempo disponible) × 100
```

### Tasa de Atención
Porcentaje de llamadas atendidas respecto al total de llamadas.

```
Tasa Atención = (Llamadas atendidas / Total llamadas) × 100
```

---

## 🔒 Seguridad

- ✅ **Conexión READ-ONLY**: El usuario de BD tiene permisos solo de lectura
- ✅ **Sin modificación de datos**: Imposible alterar datos de OmniLeads
- ✅ **Separación de aplicaciones**: Módulo independiente del sistema principal
- ✅ **Variables de entorno**: Credenciales almacenadas de forma segura

---

## 📦 Dependencias

### Backend (Python)
- fastapi==0.110.1
- sqlalchemy==2.0.36
- psycopg2-binary==2.9.11
- pandas==2.2.0
- python-dotenv>=1.0.1

### Frontend (JavaScript)
- react
- react-router-dom
- chart.js
- react-chartjs-2
- date-fns

---

## 🎨 Diseño

El diseño del dashboard está inspirado en Google Analytics:
- Colores: Azul primario (#1a73e8), verde, amarillo, rojo
- Tipografía: System fonts (legible, moderna)
- Estilo: Limpio, profesional, sin gradientes
- Espaciado: Generoso, fácil de leer

---

## 🚦 Estado del Proyecto

### ✅ Completado
- [x] Configuración de PostgreSQL
- [x] Modelos SQLAlchemy (read-only)
- [x] Servicios de análisis de llamadas
- [x] Servicios de análisis de agentes
- [x] API REST completa
- [x] Dashboard React completo
- [x] Sistema de filtros
- [x] Visualizaciones con Chart.js
- [x] Tablas interactivas
- [x] KPIs en tiempo real
- [x] Conexión segura READ-ONLY

### 🔄 Posibles Mejoras Futuras
- [ ] Exportación a Excel/PDF
- [ ] Gráficos adicionales (TMO por hora, etc.)
- [ ] Timeline de actividad de agentes
- [ ] Comparación entre períodos
- [ ] Alertas configurables
- [ ] Reportes programados por email
- [ ] Dashboard personalizable
- [ ] Guardado de filtros favoritos

---

## 📝 Notas Importantes

1. **Backup para Pruebas**: El sistema actualmente usa el backup restaurado localmente para pruebas. Para conectar a la BD real de producción, actualiza las credenciales en `.env`.

2. **Rendimiento**: Las consultas están optimizadas pero con grandes volúmenes de datos (>100k llamadas) considera agregar índices en PostgreSQL.

3. **Actualización de Datos**: El dashboard muestra datos en tiempo real. Usa el botón "Actualizar" para refrescar.

4. **Compatibilidad**: Compatible con OmniLeads 1.x y PostgreSQL 11+.

---

## 🆘 Soporte

Para problemas o dudas:
1. Revisa la sección de Troubleshooting
2. Verifica los logs del sistema
3. Consulta la documentación de OmniLeads

---

**Versión**: 1.0  
**Última actualización**: Octubre 2024  
**Desarrollado para**: Sistema de Call Center OmniLeads

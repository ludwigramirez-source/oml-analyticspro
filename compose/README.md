# Docker Compose Configuration for OmniLeads Analytics

Configuración profesional de Docker Compose para desarrollo y producción del proyecto OmniLeads Analytics.

## Estructura

```
compose/
├── backend.dev.dockerfile       # Dockerfile de desarrollo para backend
├── backend.prod.dockerfile      # Dockerfile de producción para backend
├── frontend.dev.dockerfile      # Dockerfile de desarrollo para frontend
├── frontend.prod.dockerfile     # Dockerfile de producción para frontend
├── docker-compose.dev.yml       # Configuración Docker Compose para desarrollo
├── docker-compose.prod.yml      # Configuración Docker Compose para producción
├── nginx.conf                   # Configuración base de Nginx
├── default.conf                 # Configuración de Nginx para desarrollo
├── prod/
│   ├── nginx-prod.conf         # Configuración de Nginx para producción
│   ├── ssl/                    # Certificados SSL (solo producción)
│   ├── mongo-backup/           # Backups de MongoDB
│   └── postgres-backup/        # Backups de PostgreSQL
├── .env.example                # Archivo de ejemplo de variables de entorno
├── .dockerignore               # Archivos ignorados en construcción de imágenes
└── README.md                   # Este archivo
```

## Configuración Rápida

### 1. Preparación Inicial

```bash
# Navegar a la carpeta del proyecto
cd oml-analyticspro

# Copiar archivo de configuración
cp compose/.env.example compose/.env

# Editar variables de entorno según tus necesidades
nano compose/.env
```

### 2. Desarrollo

```bash
# Construir imágenes y iniciar servicios
docker-compose -f compose/docker-compose.dev.yml up -d

# Ver logs en tiempo real
docker-compose -f compose/docker-compose.dev.yml logs -f

# Detener servicios
docker-compose -f compose/docker-compose.dev.yml down

# Limpiar volúmenes (cuidado: elimina datos)
docker-compose -f compose/docker-compose.dev.yml down -v
```

### 3. Producción

```bash
# Construir imágenes optimizadas
docker-compose -f compose/docker-compose.prod.yml build --no-cache

# Iniciar servicios con configuración de producción
docker-compose -f compose/docker-compose.prod.yml up -d

# Ver estado
docker-compose -f compose/docker-compose.prod.yml ps

# Ver logs
docker-compose -f compose/docker-compose.prod.yml logs -f backend
```

## Servicios Disponibles

### Desarrollo

| Servicio | Puerto | URL | Descripción |
|----------|--------|-----|-------------|
| Backend | 8000 | http://localhost:8000 | API FastAPI |
| Frontend | 3000 | http://localhost:3000 | Aplicación React |
| MongoDB | 27017 | localhost:27017 | Base de datos NoSQL |
| PostgreSQL | 5432 | localhost:5432 | Base de datos OmniLeads |
| pgAdmin | 5050 | http://localhost:5050 | Interfaz PostgreSQL |
| Mongo Express | 8081 | http://localhost:8081 | Interfaz MongoDB |

### Producción

| Servicio | Descripción |
|----------|-------------|
| Backend | API FastAPI (2 réplicas) |
| Frontend | Aplicación React (compilada) |
| Nginx | Reverse Proxy + Balanceo de carga |
| MongoDB | Base de datos NoSQL |
| PostgreSQL | Base de datos OmniLeads |

## Variables de Entorno

### Requeridas

- `MONGO_URL` - URL de conexión a MongoDB
- `DB_NAME` - Nombre de la base de datos MongoDB
- `OMNILEADS_DB_HOST` - Host de PostgreSQL
- `OMNILEADS_DB_USER` - Usuario de PostgreSQL
- `OMNILEADS_DB_PASSWORD` - Contraseña de PostgreSQL
- `OMNILEADS_DB_NAME` - Nombre de la base de datos
- `JWT_SECRET_KEY` - Clave secreta JWT

### Opcionales

- `LOG_LEVEL` - Nivel de logging (DEBUG, INFO, WARNING, ERROR)
- `REACT_APP_API_URL` - URL del API (por defecto: http://localhost:8000/api)
- `AWS_ACCESS_KEY_ID` - Credenciales de AWS
- `AWS_SECRET_ACCESS_KEY` - Credenciales de AWS

## Comandos Útiles

### Desarrollo

```bash
# Iniciar servicios
docker-compose -f compose/docker-compose.dev.yml up -d

# Reconstruir imágenes
docker-compose -f compose/docker-compose.dev.yml up -d --build

# Ejecutar comando en el contenedor
docker-compose -f compose/docker-compose.dev.yml exec backend bash

# Ver logs de un servicio específico
docker-compose -f compose/docker-compose.dev.yml logs -f backend

# Detener un servicio específico
docker-compose -f compose/docker-compose.dev.yml stop backend
```

### Producción

```bash
# Construcción multi-etapa
docker-compose -f compose/docker-compose.prod.yml build --no-cache

# Escalar servicios
docker-compose -f compose/docker-compose.prod.yml up -d --scale backend=3

# Ver recursos utilizados
docker stats

# Backup de bases de datos
docker-compose -f compose/docker-compose.prod.yml exec mongo mongodump --out /backup
```

## Características de Seguridad

### Backend
- ✅ Usuario no-root
- ✅ Health checks
- ✅ Variables de entorno sensibles
- ✅ Control de recursos (CPU, memoria)

### Frontend
- ✅ Build multi-etapa optimizado
- ✅ Nginx con headers de seguridad
- ✅ Compresión Gzip
- ✅ Caché de activos estáticos

### Databases
- ✅ Autenticación habilitada
- ✅ Volúmenes persistentes
- ✅ Health checks
- ✅ Backups

### Nginx
- ✅ SSL/TLS en producción
- ✅ HSTS
- ✅ CSP (Content Security Policy)
- ✅ Rate limiting
- ✅ Balanceo de carga

## Troubleshooting

### Los servicios no inician

```bash
# Verificar logs
docker-compose -f compose/docker-compose.dev.yml logs

# Verificar volúmenes
docker volume ls

# Limpiar y reintentar
docker-compose -f compose/docker-compose.dev.yml down -v
docker-compose -f compose/docker-compose.dev.yml up -d
```

### Puerto ya en uso

```bash
# Encontrar proceso usando puerto 8000
lsof -i :8000

# O cambiar puerto en .env
BACKEND_PORT=8001
```

### Base de datos no conecta

```bash
# Verificar estado de los contenedores
docker-compose -f compose/docker-compose.dev.yml ps

# Ejecutar health check
docker-compose -f compose/docker-compose.dev.yml exec mongo mongosh
docker-compose -f compose/docker-compose.dev.yml exec postgres-omnileads psql -U postgres
```

## Performance Tips

### Desarrollo

- Usar volúmenes montados para código (hot reload)
- Limitar logs verbosos en desarrollo
- Usar `--build` solo cuando cambien dependencias

### Producción

- Usar builds multi-etapa
- Limitar recursos por servicio
- Usar réplicas para redundancia
- Implementar CI/CD para deployments
- Monitorear con Prometheus/Grafana (opcional)

## Escalado

Para escalar en producción:

```bash
# Aumentar réplicas del backend
docker-compose -f compose/docker-compose.prod.yml up -d --scale backend=3
```

## Backups

### MongoDB

```bash
docker-compose -f compose/docker-compose.prod.yml exec mongo \
  mongodump --uri="mongodb://user:pass@mongo:27017" --out /backup
```

### PostgreSQL

```bash
docker-compose -f compose/docker-compose.prod.yml exec postgres-omnileads \
  pg_dump -U postgres omnileads > /backup/omnileads.sql
```

## Monitoreo

Ver estadísticas en tiempo real:

```bash
docker stats
```

## Referencias

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose](https://docs.docker.com/compose/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [React](https://react.dev/)

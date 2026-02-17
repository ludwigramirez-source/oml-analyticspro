# Guia de Despliegue - OmniLeads Analytics Pro
## Ubuntu 22.04 LTS - Produccion

---

## Tabla de Contenido

1. [Requisitos del Servidor](#1-requisitos-del-servidor)
2. [Preparacion del Servidor](#2-preparacion-del-servidor)
3. [Instalar Docker y Docker Compose](#3-instalar-docker-y-docker-compose)
4. [Clonar el Repositorio](#4-clonar-el-repositorio)
5. [Configurar Variables de Entorno](#5-configurar-variables-de-entorno)
6. [Construir y Levantar los Servicios](#6-construir-y-levantar-los-servicios)
7. [Verificar el Despliegue](#7-verificar-el-despliegue)
8. [Configurar Firewall](#8-configurar-firewall)
9. [Configurar SSL con Certbot (Opcional)](#9-configurar-ssl-con-certbot-opcional)
10. [Mantenimiento y Operaciones](#10-mantenimiento-y-operaciones)
11. [Monitoreo](#11-monitoreo)
12. [Troubleshooting](#12-troubleshooting)
13. [Rollback](#13-rollback)
14. [Actualizaciones](#14-actualizaciones)

---

## 1. Requisitos del Servidor

### Hardware Minimo
| Recurso | Minimo | Recomendado |
|---------|--------|-------------|
| CPU     | 2 cores | 4 cores |
| RAM     | 4 GB   | 8 GB |
| Disco   | 40 GB SSD | 80 GB SSD |

### Requisitos de Red
- El servidor debe tener acceso a la BD de OmniLeads (ej: `192.168.15.104:5432`)
- Puerto 80 (HTTP) abierto para acceso web
- Puerto 443 (HTTPS) si se configura SSL
- Puerto 22 (SSH) para administracion

### Software
- Ubuntu 22.04 LTS (server o desktop)
- Docker Engine 24+
- Docker Compose v2+
- Git

---

## 2. Preparacion del Servidor

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Instalar paquetes basicos
sudo apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    git \
    htop \
    nano

# Configurar timezone (debe coincidir con la BD de OmniLeads)
sudo timedatectl set-timezone America/Bogota

# Verificar timezone
timedatectl
```

---

## 3. Instalar Docker y Docker Compose

```bash
# Agregar clave GPG oficial de Docker
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Agregar repositorio de Docker
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Instalar Docker Engine + Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Agregar usuario actual al grupo docker (evita usar sudo)
sudo usermod -aG docker $USER

# IMPORTANTE: Cerrar sesion y volver a entrar para que tome efecto
# O ejecutar:
newgrp docker

# Verificar instalacion
docker --version
docker compose version
```

### Configurar Docker para produccion

```bash
# Crear directorio de configuracion
sudo mkdir -p /etc/docker

# Configurar log rotation y storage driver
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "storage-driver": "overlay2"
}
EOF

# Reiniciar Docker
sudo systemctl restart docker

# Habilitar Docker al arranque
sudo systemctl enable docker
```

---

## 4. Clonar el Repositorio

```bash
# Crear directorio para la aplicacion
sudo mkdir -p /opt/oml-analytics
sudo chown $USER:$USER /opt/oml-analytics

# Clonar repositorio (rama V2DNDS)
cd /opt/oml-analytics
git clone -b V2DNDS https://github.com/TU-USUARIO/oml-analyticspro.git .

# Verificar que estas en la rama correcta
git branch --show-current
# Debe mostrar: V2DNDS
```

---

## 5. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# Editar configuracion
nano .env
```

### Variables CRITICAS que debes cambiar:

```env
# ============================================================================
# CONEXION A BD OMNILEADS (REMOTA) - OBLIGATORIO
# ============================================================================
OMNILEADS_DB_HOST=192.168.15.104        # IP de tu servidor OmniLeads
OMNILEADS_DB_PORT=5432                   # Puerto PostgreSQL de OmniLeads
OMNILEADS_DB_USER=analitycs_user         # Usuario de solo lectura
OMNILEADS_DB_PASSWORD=TuPasswordReal     # Password del usuario
OMNILEADS_DB_NAME=omnileads             # Nombre de la BD

# ============================================================================
# SEGURIDAD - OBLIGATORIO CAMBIAR
# ============================================================================
JWT_SECRET_KEY=genera-una-clave-aleatoria-de-32-caracteres-aqui
LOCAL_DB_PASSWORD=una-password-segura-para-bd-local

# ============================================================================
# TIMEZONE - DEBE COINCIDIR CON OMNILEADS
# ============================================================================
TIMEZONE_DB=America/Bogota

# ============================================================================
# BACKEND
# ============================================================================
LOG_LEVEL=INFO                           # Usar INFO en produccion (no DEBUG)

# ============================================================================
# FRONTEND - CAMBIAR IP/DOMINIO
# ============================================================================
REACT_APP_API_URL=http://TU-IP-O-DOMINIO/api
REACT_APP_BACKEND_URL=http://TU-IP-O-DOMINIO

# ============================================================================
# LOCAL DB (generalmente no necesita cambios)
# ============================================================================
USE_LOCAL_DB=true
LOCAL_DB_NAME=omnileads_local
LOCAL_DB_USER=analytics

# ============================================================================
# SYNC (generalmente no necesita cambios)
# ============================================================================
SYNC_INTERVAL_EVENT_LOGS=300             # Sync cada 5 minutos
SYNC_INTERVAL_REFERENCE=3600            # Referencia cada 1 hora
SYNC_BATCH_SIZE=10000
SYNC_INITIAL_BATCH_SIZE=50000
```

### Generar JWT_SECRET_KEY segura:

```bash
# Generar clave aleatoria
openssl rand -hex 32
# Copiar el resultado y pegarlo en JWT_SECRET_KEY del .env
```

### Verificar conectividad a BD OmniLeads:

```bash
# Probar que el servidor puede llegar a la BD de OmniLeads
# Instalar cliente PostgreSQL temporalmente
sudo apt install -y postgresql-client

# Probar conexion
psql -h 192.168.15.104 -U analitycs_user -d omnileads -c "SELECT 1;"
# Debe pedir password y retornar "1"

# Si falla, verificar:
# 1. Que la IP es correcta
# 2. Que el firewall permite la conexion en el puerto 5432
# 3. Que pg_hba.conf del servidor OmniLeads permite la conexion desde esta IP
```

---

## 6. Construir y Levantar los Servicios

### Primera vez (build completo):

```bash
cd /opt/oml-analytics

# Construir todas las imagenes (puede tomar 5-10 minutos)
docker compose -f docker-compose.prod.yml build --no-cache

# Levantar servicios
docker compose -f docker-compose.prod.yml up -d

# Ver logs en tiempo real (Ctrl+C para salir)
docker compose -f docker-compose.prod.yml logs -f
```

### Orden de arranque:

Los servicios arrancan en este orden:
1. **postgres-local** - BD local (espera healthcheck)
2. **sync-service** - Crea schema, hace carga inicial, luego sync periodico
3. **backend** (x2 replicas) - API FastAPI con Gunicorn
4. **frontend** - Nginx + React build

### Esperar la carga inicial:

La primera vez, el sync-service necesita traer todos los datos historicos. Esto puede tomar entre 5-30 minutos dependiendo del volumen de datos.

```bash
# Monitorear progreso del sync
docker compose -f docker-compose.prod.yml logs -f sync-service

# Veras mensajes como:
# [SYNC] Carga inicial llamadalog: 890524 filas en 231.6s
# [SYNC] Carga inicial actividadagentelog: 557101 filas en 80.7s
# [SYNC] Sync completo finalizado en 354.7s

# Verificar que todos los servicios estan corriendo
docker compose -f docker-compose.prod.yml ps
```

### Resultado esperado de `docker compose ps`:

```
NAME                    STATUS              PORTS
oml-frontend-prod       Up (healthy)        0.0.0.0:80->80/tcp
oml-analytics-backend-1 Up (healthy)        8000/tcp
oml-analytics-backend-2 Up (healthy)        8000/tcp
oml-postgres-local-prod Up (healthy)        5432/tcp
oml-sync-service-prod   Up (healthy)
```

---

## 7. Verificar el Despliegue

### 7.1 Verificar servicios

```bash
# Estado de todos los contenedores
docker compose -f docker-compose.prod.yml ps

# Health check del backend
curl -s http://localhost/api/ | python3 -m json.tool

# Health check del sync-service
docker compose -f docker-compose.prod.yml exec sync-service curl -s http://localhost:8001/health

# Estado de sincronizacion
curl -s http://localhost/api/analytics/sync/status | python3 -m json.tool
```

### 7.2 Verificar desde navegador

Abre en el navegador: `http://TU-IP-DEL-SERVIDOR`

Deberias ver:
- El dashboard de OmniLeads Analytics Pro
- En la barra superior, el badge "Sincronizado" con fecha/hora y cantidad de registros
- Los KPIs con datos reales

### 7.3 Verificar KPIs

```bash
# Probar endpoint de KPIs
curl -s "http://localhost/api/analytics/kpis?fecha_inicio=$(date +%Y-%m-%d)&fecha_fin=$(date +%Y-%m-%d)" | python3 -m json.tool
```

---

## 8. Configurar Firewall

```bash
# Instalar UFW si no esta instalado
sudo apt install -y ufw

# Permitir SSH (para no perder acceso)
sudo ufw allow 22/tcp

# Permitir HTTP
sudo ufw allow 80/tcp

# Permitir HTTPS (si vas a usar SSL)
sudo ufw allow 443/tcp

# Habilitar firewall
sudo ufw enable

# Verificar reglas
sudo ufw status verbose
```

> **IMPORTANTE**: Si el servidor esta en la misma red que OmniLeads, no necesitas abrir el puerto 5432. Docker se conecta internamente.

---

## 9. Configurar SSL con Certbot (Opcional)

Si tienes un dominio apuntando al servidor, puedes configurar HTTPS gratuito:

### Opcion A: Certbot standalone (mas simple)

```bash
# Instalar Certbot
sudo apt install -y certbot

# Detener frontend temporalmente (Certbot necesita el puerto 80)
docker compose -f docker-compose.prod.yml stop frontend

# Obtener certificado
sudo certbot certonly --standalone -d tu-dominio.com

# Reiniciar frontend
docker compose -f docker-compose.prod.yml start frontend
```

Luego configura los certificados en el archivo `compose/prod/nginx-prod.conf`:

```nginx
server {
    listen 443 ssl;
    server_name tu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/tu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tu-dominio.com/privkey.pem;

    # ... resto de la configuracion ...
}

server {
    listen 80;
    server_name tu-dominio.com;
    return 301 https://$server_name$request_uri;
}
```

Y monta los certificados en el contenedor frontend via docker-compose.prod.yml:

```yaml
frontend:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
  ports:
    - "80:80"
    - "443:443"
```

### Renovacion automatica

```bash
# Certbot renueva automaticamente, pero verificar:
sudo certbot renew --dry-run

# Agregar cron para recargar Nginx despues de renovar
echo "0 3 * * * certbot renew --post-hook 'docker compose -f /opt/oml-analytics/docker-compose.prod.yml restart frontend'" | sudo crontab -
```

---

## 10. Mantenimiento y Operaciones

### Comandos frecuentes

```bash
cd /opt/oml-analytics

# Ver estado de servicios
docker compose -f docker-compose.prod.yml ps

# Ver logs de un servicio especifico
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f sync-service
docker compose -f docker-compose.prod.yml logs -f postgres-local

# Reiniciar un servicio
docker compose -f docker-compose.prod.yml restart backend
docker compose -f docker-compose.prod.yml restart sync-service

# Detener todo
docker compose -f docker-compose.prod.yml down

# Detener y eliminar volumenes (PELIGROSO - borra datos de BD local)
# docker compose -f docker-compose.prod.yml down -v

# Ver uso de recursos
docker stats
```

### Verificar estado de sincronizacion

```bash
# Desde el API
curl -s http://localhost/api/analytics/sync/status | python3 -m json.tool

# Desde el contenedor sync-service
docker compose -f docker-compose.prod.yml exec sync-service \
    curl -s http://localhost:8001/status | python3 -m json.tool

# Conectar a la BD local directamente
docker compose -f docker-compose.prod.yml exec postgres-local \
    psql -U analytics -d omnileads_local -c "SELECT * FROM sync_metadata ORDER BY table_name;"
```

### Backup de la BD local

```bash
# Crear backup (no es critico ya que los datos se pueden re-sincronizar)
docker compose -f docker-compose.prod.yml exec postgres-local \
    pg_dump -U analytics omnileads_local > backup_$(date +%Y%m%d_%H%M%S).sql

# Nota: Si pierdes la BD local, simplemente reinicia el sync-service
# y hara una carga inicial completa automaticamente
```

### Limpieza de Docker

```bash
# Limpiar imagenes antiguas
docker image prune -f

# Limpiar todo lo no usado (cuidado en produccion)
# docker system prune -f
```

---

## 11. Monitoreo

### Script de monitoreo basico

Crea un script para verificar el estado:

```bash
sudo tee /opt/oml-analytics/check_health.sh <<'SCRIPT'
#!/bin/bash
echo "=== OmniLeads Analytics Pro - Health Check ==="
echo "Fecha: $(date)"
echo ""

# Verificar contenedores
echo "--- Contenedores ---"
docker compose -f /opt/oml-analytics/docker-compose.prod.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Verificar API
echo "--- API Health ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/api/)
if [ "$HTTP_CODE" = "200" ]; then
    echo "API: OK ($HTTP_CODE)"
else
    echo "API: ERROR ($HTTP_CODE)"
fi
echo ""

# Verificar Sync
echo "--- Sync Status ---"
curl -s http://localhost/api/analytics/sync/status 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "Sync status no disponible"
echo ""

# Uso de disco
echo "--- Uso de Disco ---"
docker system df
SCRIPT

chmod +x /opt/oml-analytics/check_health.sh
```

### Cron de monitoreo (opcional)

```bash
# Verificar health cada 5 minutos y guardar log
echo "*/5 * * * * /opt/oml-analytics/check_health.sh >> /var/log/oml-analytics-health.log 2>&1" | crontab -
```

---

## 12. Troubleshooting

### El frontend no carga

```bash
# Verificar que el contenedor esta corriendo
docker compose -f docker-compose.prod.yml ps frontend

# Ver logs
docker compose -f docker-compose.prod.yml logs frontend

# Verificar que Nginx esta respondiendo
curl -I http://localhost/

# Rebuild si es necesario
docker compose -f docker-compose.prod.yml build --no-cache frontend
docker compose -f docker-compose.prod.yml up -d frontend
```

### Error de conexion a BD OmniLeads

```bash
# Verificar conectividad desde el contenedor sync-service
docker compose -f docker-compose.prod.yml exec sync-service \
    python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='$OMNILEADS_DB_HOST',
    port=$OMNILEADS_DB_PORT,
    user='$OMNILEADS_DB_USER',
    password='$OMNILEADS_DB_PASSWORD',
    dbname='$OMNILEADS_DB_NAME'
)
print('Conexion exitosa')
conn.close()
"

# Si falla, verificar:
# 1. Variables en .env
# 2. Firewall del servidor OmniLeads
# 3. pg_hba.conf del servidor OmniLeads
```

### Sync service no sincroniza

```bash
# Ver logs detallados
docker compose -f docker-compose.prod.yml logs --tail=100 sync-service

# Verificar estado en sync_metadata
docker compose -f docker-compose.prod.yml exec postgres-local \
    psql -U analytics -d omnileads_local -c \
    "SELECT table_name, sync_status, rows_synced, last_sync_time, error_message FROM sync_metadata;"

# Reiniciar sync-service
docker compose -f docker-compose.prod.yml restart sync-service

# Forzar re-sincronizacion completa (resetear watermarks)
docker compose -f docker-compose.prod.yml exec postgres-local \
    psql -U analytics -d omnileads_local -c \
    "UPDATE sync_metadata SET last_synced_id = 0, sync_status = 'pending';"
docker compose -f docker-compose.prod.yml restart sync-service
```

### Backend responde lento

```bash
# Ver recursos de los contenedores
docker stats

# Si postgres-local consume mucha CPU, puede estar en carga inicial
# Esperar a que el sync-service termine

# Verificar conexiones activas a la BD local
docker compose -f docker-compose.prod.yml exec postgres-local \
    psql -U analytics -d omnileads_local -c \
    "SELECT count(*) FROM pg_stat_activity WHERE state = 'active';"
```

### Reinicio completo (si todo falla)

```bash
cd /opt/oml-analytics

# Detener todo
docker compose -f docker-compose.prod.yml down

# Rebuild
docker compose -f docker-compose.prod.yml build --no-cache

# Levantar
docker compose -f docker-compose.prod.yml up -d

# Monitorear
docker compose -f docker-compose.prod.yml logs -f
```

### Reinicio completo CON perdida de datos locales

```bash
# SOLO si la BD local esta corrupta
cd /opt/oml-analytics
docker compose -f docker-compose.prod.yml down -v
docker compose -f docker-compose.prod.yml up -d
# El sync-service hara una carga inicial completa (puede tomar 10-30 min)
```

---

## 13. Rollback

### Volver al modo directo (sin BD local)

Si hay problemas con la sincronizacion, puedes desactivar la BD local:

```bash
# Editar .env
nano /opt/oml-analytics/.env
# Cambiar: USE_LOCAL_DB=false

# Reiniciar solo el backend
docker compose -f docker-compose.prod.yml restart backend

# El backend ahora consulta directo a la BD de OmniLeads
# El sync-service sigue corriendo pero no afecta nada
```

### Volver a activar BD local

```bash
# Editar .env
nano /opt/oml-analytics/.env
# Cambiar: USE_LOCAL_DB=true

# Reiniciar backend
docker compose -f docker-compose.prod.yml restart backend
```

---

## 14. Actualizaciones

### Actualizar a una nueva version

```bash
cd /opt/oml-analytics

# Hacer backup antes de actualizar
docker compose -f docker-compose.prod.yml exec postgres-local \
    pg_dump -U analytics omnileads_local > backup_pre_update_$(date +%Y%m%d).sql

# Traer cambios del repositorio
git fetch origin
git pull origin V2DNDS

# Rebuild imagenes
docker compose -f docker-compose.prod.yml build --no-cache

# Reiniciar servicios (con zero-downtime para backend)
docker compose -f docker-compose.prod.yml up -d

# Verificar
docker compose -f docker-compose.prod.yml ps
curl -s http://localhost/api/ | python3 -m json.tool
```

---

## Resumen de Arquitectura en Produccion

```
Internet/LAN
    |
    v
[Ubuntu 22.04 Server]
    |
    +-- [frontend] Nginx:80 --> React build estatic
    |       |
    |       +-- /api/* --> proxy_pass al backend
    |
    +-- [backend x2] Gunicorn:8000 (FastAPI)
    |       |
    |       +-- Lee de: postgres-local (USE_LOCAL_DB=true)
    |       |   o
    |       +-- Lee de: OmniLeads remoto (USE_LOCAL_DB=false)
    |
    +-- [postgres-local] PostgreSQL 16 (replica local)
    |       ^
    |       |
    +-- [sync-service] Sincroniza cada 5 min
            |
            +-- Lee de: OmniLeads BD remota (192.168.x.x:5432)
```

### Puertos expuestos
| Puerto | Servicio | Descripcion |
|--------|----------|-------------|
| 80     | Nginx/Frontend | Web UI + API proxy |
| 443    | Nginx/Frontend | HTTPS (si se configura SSL) |

### Puertos internos (solo red Docker)
| Puerto | Servicio | Descripcion |
|--------|----------|-------------|
| 8000   | Backend (x2) | API FastAPI |
| 5432   | postgres-local | BD local |
| 8001   | sync-service | Health check |

---

## Soporte

- **Logs del backend**: `docker compose -f docker-compose.prod.yml logs -f backend`
- **Logs del sync**: `docker compose -f docker-compose.prod.yml logs -f sync-service`
- **Estado de sync**: `curl http://localhost/api/analytics/sync/status`
- **Branch**: `V2DNDS`

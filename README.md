# 📊 OmniLeads Analytics Pro

Advanced analytics and reporting platform for OmniLeads contact center system. Real-time KPIs, comprehensive call analytics, agent performance metrics, and customizable reporting with Power BI integration.

## 🎯 Project Overview

**OmniLeads Analytics Pro** is a modern analytics platform built on top of OmniLeads to provide:

- **Real-time KPIs:** Call metrics, wait times, service levels
- **Agent Analytics:** Performance, availability, session details
- **Call Analytics:** Distribution, types, outcomes, transfers
- **Premium Reports:** Advanced filtering, grouping, and data export
- **Power BI Integration:** Direct connection for dashboard creation
- **Multi-database Support:** Dynamic database configuration management

### Tech Stack

**Backend:**
- FastAPI 0.110.1
- SQLAlchemy 2.0.36 (PostgreSQL ORM)
- Uvicorn 0.25.0 (development)
- Gunicorn (production)
- Pydantic 2.6.4

**Frontend:**
- React 19.0.0
- React Router Dom 7.5.1
- Axios 1.8.4
- TailwindCSS 3.4.17
- ApexCharts 5.3.5
- Zod 3.24.4

**Infrastructure:**
- Docker & Docker Compose
- PostgreSQL (OmniLeads data source)
- Nginx (reverse proxy, production)
- pgAdmin (database management, development only)

---

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose installed
- Git
- ~1GB free disk space

### Setup Inicial (5 minutes)

```bash
# 1. Clone the repository
git clone <repository-url>
cd oml-analyticspro

# 2. Configure environment variables
cp .env.example .env

# 3. Edit .env with your OmniLeads database credentials
nano .env
# Required values:
# - OMNILEADS_DB_HOST (database server host)
# - OMNILEADS_DB_PORT (usually 5432)
# - OMNILEADS_DB_NAME (usually "omnileads")
# - OMNILEADS_DB_USER (read-only user)
# - OMNILEADS_DB_PASSWORD (database password)

# 4. Start all services (development)
docker-compose -f docker-compose.dev.yml up -d

# 5. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
# pgAdmin: http://localhost:5050 (admin@example.com / admin)
```

### Local Development (without Docker)

#### Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm start

# Build for production
npm run build
```

---

## 📁 Project Structure

```
oml-analyticspro/
├── backend/                              # FastAPI backend
│   ├── analytics/
│   │   ├── models/                       # SQLAlchemy models
│   │   ├── routes/                       # API endpoints
│   │   ├── services/                     # Business logic
│   │   └── database.py                   # DB configuration
│   ├── server.py                         # FastAPI app entry
│   └── requirements.txt                  # Python dependencies
├── frontend/                             # React application
│   ├── src/
│   │   ├── components/                   # Reusable components
│   │   ├── pages/                        # Page components
│   │   ├── services/                     # API services
│   │   ├── hooks/                        # Custom hooks
│   │   ├── context/                      # Context API
│   │   ├── styles/                       # Global styles
│   │   └── utils/                        # Utility functions
│   ├── public/
│   └── package.json                      # Node dependencies
├── compose/                              # Docker configuration
│   ├── dev/
│   │   ├── backend/backend.dev.dockerfile
│   │   └── frontend/frontend.dev.dockerfile
│   ├── prod/
│   │   ├── backend/backend.prod.dockerfile
│   │   └── frontend/frontend.prod.dockerfile
│   └── nginx/                            # Nginx config (prod)
├── tests/                                # Project tests
├── .env.example                          # Environment template
├── docker-compose.dev.yml                # Development services
├── docker-compose.prod.yml               # Production services
├── Claude.md                             # Development guide
└── README.md                             # This file
```

---

## 🐳 Docker Commands

### Development

Services: Backend, Frontend, PostgreSQL (OmniLeads), pgAdmin

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# Rebuild images
docker-compose -f docker-compose.dev.yml up -d --build

# View logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Access backend shell
docker-compose -f docker-compose.dev.yml exec backend bash

# Stop services
docker-compose -f docker-compose.dev.yml down

# Stop and remove volumes (clean databases)
docker-compose -f docker-compose.dev.yml down -v
```

### Production

Services: Backend (replicas), Frontend, PostgreSQL, Nginx

```bash
# Build optimized images
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View status
docker-compose -f docker-compose.prod.yml ps

# Scale backend replicas
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

---

## 📚 API Documentation

### Available Endpoints

#### KPIs & Metrics
```
GET /api/analytics/kpis
GET /api/analytics/llamadas-por-tipo
GET /api/analytics/distribucion-llamadas
GET /api/analytics/evolucion-hora
GET /api/analytics/distribucion-por-tipo
```

#### Agent Analytics
```
GET /api/analytics/agentes/rendimiento
GET /api/analytics/agentes/disponibilidad
GET /api/analytics/agentes/sesiones/{agente_id}
GET /api/analytics/agentes/detalle-sesiones/{agente_id}
```

#### Transfer Analytics
```
GET /api/analytics/transferencias/analisis
GET /api/analytics/transferencias/detalle
```

### Query Parameters

Common filtering parameters for all analytics endpoints:

```bash
fecha_inicio=YYYY-MM-DD              # Start date (optional)
fecha_fin=YYYY-MM-DD                 # End date (optional)
campana_id=123                       # Campaign ID (optional)
campana_ids=1,2,3                    # Multiple campaign IDs (optional)
agente_id=456                        # Agent ID (optional)
agente_ids=4,5,6                     # Multiple agent IDs (optional)
tipo_llamada=entrantes|salientes    # Call type (optional)
```

### Example Requests

```bash
# Get all KPIs for October 2025
curl "http://localhost:8000/api/analytics/kpis?fecha_inicio=2025-10-01&fecha_fin=2025-10-31"

# Get agent performance for specific agent
curl "http://localhost:8000/api/analytics/agentes/rendimiento?agente_id=123"

# Get calls by type with campaign filter
curl "http://localhost:8000/api/analytics/llamadas-por-tipo?campana_ids=1,2,3"
```

Interactive API documentation available at: `http://localhost:8000/docs`

---

## ⚙️ Configuration

### Environment Variables

**Development** (`.env`):
```bash
# Backend
BACKEND_PORT=8000
LOG_LEVEL=DEBUG
JWT_SECRET_KEY=dev-secret-key-change-in-production

# Frontend
FRONTEND_PORT=3000
REACT_APP_API_URL=http://localhost:8000/api

# PostgreSQL (OmniLeads Database)
OMNILEADS_DB_HOST=postgres-omnileads
OMNILEADS_DB_PORT=5432
OMNILEADS_DB_USER=dbuser
OMNILEADS_DB_PASSWORD=YourStrongPassword
OMNILEADS_DB_NAME=omnileads

# pgAdmin (Development only)
PGADMIN_PORT=5050
PGADMIN_EMAIL=admin@example.com
PGADMIN_PASSWORD=admin
```

**Production** (`.env`):
```bash
# Use secure credentials from secrets manager
BACKEND_PORT=8000
LOG_LEVEL=INFO
JWT_SECRET_KEY=<secure-key-from-secrets-manager>

# Frontend
REACT_APP_API_URL=https://api.example.com

# PostgreSQL - Use managed service or secure setup
OMNILEADS_DB_HOST=db.example.com
OMNILEADS_DB_PORT=5432
OMNILEADS_DB_USER=<prod-user>
OMNILEADS_DB_PASSWORD=<secure-password>
OMNILEADS_DB_NAME=omnileads
```

### Code Quality Standards

This project follows PEP 8 standards:

```bash
# Check code quality
python -m flake8 backend/ --max-line-length=88

# Check import organization
python -m isort backend/ --check-only --profile black

# Format code with black
python -m black backend/ --line-length=88

# Run tests
pytest backend/tests/
```

---

## 🐛 Troubleshooting

### Docker Issues

#### PostgreSQL cannot connect
```bash
# Verify credentials in .env
cat .env | grep OMNILEADS_DB

# Test connection with psql
psql -h localhost -U ${OMNILEADS_DB_USER} -d ${OMNILEADS_DB_NAME}

# Check container is running
docker-compose -f docker-compose.dev.yml ps

# View PostgreSQL logs
docker-compose -f docker-compose.dev.yml logs postgres-omnileads
```

#### Backend connection refused
```bash
# Check backend is running
docker-compose -f docker-compose.dev.yml ps backend

# Test API endpoint
curl http://localhost:8000/api/

# View backend logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Check environment variables
docker-compose -f docker-compose.dev.yml config | grep -A 10 "backend:"
```

#### Frontend blank page
```bash
# Check frontend is running
docker-compose -f docker-compose.dev.yml ps frontend

# Check frontend build
docker-compose -f docker-compose.dev.yml logs frontend

# Rebuild frontend
docker-compose -f docker-compose.dev.yml up -d --build frontend

# Test frontend directly
curl http://localhost:3000
```

### Database Connection Issues

#### Cannot connect to OmniLeads database
```bash
# 1. Verify credentials
cat .env | grep OMNILEADS_DB

# 2. Test connection with psql
psql -h $OMNILEADS_DB_HOST -U $OMNILEADS_DB_USER -d $OMNILEADS_DB_NAME

# 3. Check firewall/network access
telnet $OMNILEADS_DB_HOST 5432

# 4. Verify PostgreSQL is running (on database server)
sudo systemctl status postgresql
sudo netstat -tlnp | grep 5432
```

#### Read-only user lacks permissions
```bash
# On OmniLeads database server:
sudo -u postgres psql omnileads

-- Grant schema access
GRANT USAGE ON SCHEMA public TO omnileads_readonly;

-- Grant table access
GRANT SELECT ON ALL TABLES IN SCHEMA public TO omnileads_readonly;

-- Grant future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO omnileads_readonly;
```

### API Issues

#### 404 Not Found on analytics endpoints
```bash
# Check backend is running
curl http://localhost:8000/api/

# Check API documentation
# Open: http://localhost:8000/docs

# View backend logs
docker-compose -f docker-compose.dev.yml logs -f backend

# Check if analytics routes are loaded
docker-compose -f docker-compose.dev.yml logs backend | grep "Analytics"
```

#### No data returned from queries
```bash
# 1. Verify date range has data
psql -h $OMNILEADS_DB_HOST -U $OMNILEADS_DB_USER -d $OMNILEADS_DB_NAME

-- Check for data in date range
SELECT COUNT(*) FROM reportes_app_llamadalog
WHERE time >= '2025-10-01' AND time < '2025-11-01';

-- Verify table exists
\dt reportes_app_llamadalog

-- 2. Try without date filter
curl "http://localhost:8000/api/analytics/kpis"

-- 3. Check data types
SELECT DISTINCT tipo_llamada FROM reportes_app_llamadalog LIMIT 5;
```

#### Query timeout on large datasets
```bash
# Add date filter to reduce dataset
curl "http://localhost:8000/api/analytics/kpis?fecha_inicio=2025-10-01&fecha_fin=2025-10-31"

# Reduce number of records
curl "http://localhost:8000/api/analytics/llamadas-por-tipo?campana_id=1"

# Add database indexes (on OmniLeads database):
CREATE INDEX idx_llamadalog_time ON reportes_app_llamadalog(time);
CREATE INDEX idx_llamadalog_type ON reportes_app_llamadalog(tipo_llamada);
CREATE INDEX idx_llamadalog_agente ON reportes_app_llamadalog(agente_id);
CREATE INDEX idx_llamadalog_campana ON reportes_app_llamadalog(campana_id);
```

### Frontend Issues

#### CORS error on API calls
```bash
# Check backend is responding to requests
curl http://localhost:8000/api/

# Verify backend has CORS enabled
# Check: backend/server.py should have CORSMiddleware configured

# Test API directly
curl -H "Origin: http://localhost:3000" http://localhost:8000/api/
```

#### Console errors in browser
```bash
# Check frontend logs
docker-compose -f docker-compose.dev.yml logs -f frontend

# Check API endpoint in React
grep -r "REACT_APP_API_URL" frontend/src/

# Verify .env is loaded
echo $REACT_APP_API_URL
```

### Performance Issues

#### Slow response times (>5 seconds)
```bash
# Check backend resource usage
docker stats backend

# Analyze database query performance
EXPLAIN ANALYZE SELECT COUNT(*) FROM reportes_app_llamadalog;

# Add database indexes
CREATE INDEX idx_llamadalog_time ON reportes_app_llamadalog(time);
CREATE INDEX idx_llamadalog_type ON reportes_app_llamadalog(tipo_llamada);
CREATE INDEX idx_llamadalog_agente ON reportes_app_llamadalog(agente_id);
CREATE INDEX idx_llamadalog_campana ON reportes_app_llamadalog(campana_id);
```

#### Memory leak (memory grows over time)
```bash
# Monitor memory usage
docker stats backend

# Restart backend service
docker-compose -f docker-compose.dev.yml restart backend

# Check for unclosed database connections
grep -r "close()" backend/analytics/
```

---

## 📈 Monitoring & Logging

### View Logs

```bash
# All services
docker-compose -f docker-compose.dev.yml logs -f

# Specific service
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f postgres-omnileads

# Last 50 lines
docker-compose -f docker-compose.dev.yml logs --tail=50 backend

# Search logs
docker-compose -f docker-compose.dev.yml logs backend | grep "error"
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/

# Frontend health
curl http://localhost:3000

# Database connection
psql -h localhost -U ${OMNILEADS_DB_USER} -d ${OMNILEADS_DB_NAME} -c "SELECT 1;"

# All services status
docker-compose -f docker-compose.dev.yml ps
```

---

## 🚢 Production Deployment

### Pre-deployment Checklist

```bash
# 1. Run all tests
pytest backend/tests/

# 2. Check code quality
python -m flake8 backend/ --max-line-length=88
python -m isort backend/ --check-only --profile black

# 3. Build images
docker-compose -f docker-compose.prod.yml build

# 4. Test images locally
docker-compose -f docker-compose.prod.yml up -d

# 5. Verify endpoints
curl http://localhost:8000/api/
curl http://localhost/
```

### Deploy

```bash
# 1. Set production environment
export ENVIRONMENT=production
nano .env

# 2. Pull latest code
git pull origin main

# 3. Build and start services
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify services
docker-compose -f docker-compose.prod.yml ps
docker-compose -f docker-compose.prod.yml logs -f

# 5. Monitor
watch -n 5 'docker stats'
```

---

## 📞 Development Guidelines

For detailed development guidelines including:
- Code conventions
- Testing practices
- Security best practices
- Performance optimization
- Git workflow
- Deployment procedures

See: **[Claude.md](./Claude.md)**

### Quick Commands

```bash
# Git
git checkout -b feature/name           # Create feature branch
git add .                              # Stage changes
git commit -m "feat: description"      # Commit with proper format
git push origin feature/name           # Push to remote

# Docker
docker-compose up -d                   # Start services
docker-compose down                    # Stop services
docker-compose logs -f                 # View logs
docker ps                              # List containers

# Python
python -m venv venv                    # Create virtual environment
source venv/bin/activate               # Activate (Linux/Mac)
pip install -r requirements.txt        # Install dependencies
pytest                                 # Run tests
flake8 .                               # Check code style

# Node
npm install                            # Install dependencies
npm start                              # Start dev server
npm run build                          # Build for production
npm test                               # Run tests
```

---

## 📄 License

This project is part of the OmniLeads ecosystem.

---

## 🔄 Version History

### v1.0.0 (October 2025)
- Initial release
- Core analytics endpoints
- Database configuration management
- Docker compose setup
- Code quality improvements (91.3% PEP 8 compliance)

---

## 🎯 Next Steps

1. Configure OmniLeads database credentials in `.env`
2. Start services: `docker-compose -f docker-compose.dev.yml up -d`
3. Access frontend: `http://localhost:3000`
4. Review API docs: `http://localhost:8000/docs`
5. Create custom dashboards with your data

For more information, see [Claude.md](./Claude.md) for development guidelines.

---

**Last Updated:** October 28, 2025

Happy analyzing! 📊

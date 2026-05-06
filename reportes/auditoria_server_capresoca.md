# Auditoría Servidor capresoca.iptegra.co
**Fecha:** 2026-05-06  
**Propósito:** Fase 0 bloqueante — datos concretos para la migración VOML  
**Ejecutada por:** Claude (claude.ai)  

---

## 1. Versiones

| Componente | Versión |
|---|---|
| OS | CentOS 7 · kernel 3.10.0-1160.119.1.el7.x86_64 |
| Python | 3.6.8 |
| Django | 2.2.7 |
| PostgreSQL | 11.11 |
| psycopg2 (venv) | 2.7.5 ✅ ya instalado |
| openpyxl (venv) | 3.1.2 ✅ ya instalado |
| pandas (venv) | 1.1.5 ✅ ya instalado |
| celery (venv) | **NO instalado** |
| OmniLeads branch | release-1.30.0 |
| OmniLeads commit | 709a9c312ce3186236ba43c93248c898227e093e |
| OmniLeads fecha build | Tue Jul 15 14:58:31 -05 2025 |

---

## 2. Path del codebase OmniLeads

```
/opt/omnileads/ominicontacto/          ← Django project root (manage.py aquí)
/opt/omnileads/virtualenv/             ← Python venv
/opt/omnileads/static/                 ← STATIC_ROOT (collectstatic apunta aquí)
/opt/omnileads/media_root/             ← MEDIA_ROOT
/opt/omnileads/run/oml_uwsgi.socket   ← socket uWSGI
/opt/omnileads/log/oml_uwsgi.log      ← log uWSGI
/var/lib/pgsql/11/data/               ← PostgreSQL data dir
```

**⚠️ No es un repositorio git** — el server recibió el código como tarball/deploy directo. La versión se traquea por las envars `OML_BRANCH`, `OML_COMMIT` en `/etc/profile.d/omnileads_envars.sh`.

---

## 3. Settings relevantes

| Variable | Valor |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `ominicontacto.settings.production` |
| `AUTH_USER_MODEL` | `ominicontacto_app.User` |
| `TIME_ZONE` | `America/Bogota` |
| `USE_TZ` | `True` |
| `STATIC_ROOT` | `/opt/omnileads/static` |
| `MEDIA_ROOT` | `/opt/omnileads/media_root` |
| `DATABASES['default']` | host=localhost port=5432 db=omnileads user=omnileads |
| `DATABASES['replica']` | host=localhost port=5432 db=omnileads user=omnileads (misma BD) |

**Archivos de settings:**
```
ominicontacto/settings/
├── defaults.py          ← INSTALLED_APPS, TEMPLATES, MIDDLEWARE base
├── production.py        ← importa oml_settings_local
├── oml_settings_local.py ← lee envars, define DATABASES, SECRET_KEY
└── addons.py            ← configuración add-ons
```

**INSTALLED_APPS relevantes:**
```
django.contrib.admin, auth, contenttypes, sessions, messages, staticfiles
channels, configuracion_telefonia_app, crispy_forms, compressor, defender,
formtools, ominicontacto_app, reciclado_app, reportes_app, supervision_app,
notification_app, simple_history, widget_tweaks, rest_framework,
rest_framework.authtoken, api_app, constance, django_js_reverse,
import_export, django_extensions, constance.backends.database,
django_sass, django_sendfile, easyaudit, sslserver, form_app
```

---

## 4. Celery

**Celery NO está instalado** en el venv. Sin `CELERY_BROKER_URL` ni `CELERY_BEAT_SCHEDULE`.

**Redis SÍ está corriendo** (`redis-cli ping` → `PONG`, servicio `redis.service` activo).

**Decisión para VOML → Plan B:** management command + cron del sistema.  
*(Redis disponible: si en el futuro se quiere Celery, solo se instala `celery[redis]` y se activa. Por ahora cron es más seguro para no tocar la pila de OmniLeads.)*

```cron
# Ejemplo futuro /etc/cron.d/analyticspro
*/5 * * * * omnileads /opt/omnileads/virtualenv/bin/python /opt/omnileads/ominicontacto/manage.py sync_analytics --event-logs >> /opt/omnileads/log/analytics_sync.log 2>&1
0 * * * * omnileads /opt/omnileads/virtualenv/bin/python /opt/omnileads/ominicontacto/manage.py sync_analytics --reference >> /opt/omnileads/log/analytics_sync.log 2>&1
```

---

## 5. Patrón de menú — **registry via AppConfig**

El sidebar de OmniLeads está en:
```
ominicontacto_app/templates/gestor/sidebar_gestion.html
```

El template itera `ADMIN_MENU_ITEMS`, que es poblado por el context processor:
```python
# ominicontacto_app/context_processors.py  → addon_menu_items()
for app in apps.get_app_configs():
    if hasattr(app, 'supervision_menu_items'):
        app_items = app.supervision_menu_items(request, permissions)
        if app_items:
            menu_items += app_items
```

**Cada app instalada puede agregar ítems al menú** implementando `supervision_menu_items(self, request, permissions)` en su `AppConfig`. Los ítems se ordenan por clave `order`.

**Formato de un ítem:**
```python
{
    'order': 500,          # int, posición relativa
    'label': _('Analytics Pro'),
    'icon': 'icon-graph',
    'id': 'menuAnalytics',
    'url': reverse('analyticspro:dashboard'),   # si tiene URL directa
    # o 'children': [...]  si es un grupo con submenú
}
```

**Condición de acceso:** El context processor solo llama `supervision_menu_items` si `request.user.get_tiene_permiso_administracion()` → True. Este método retorna True para Administradores y Supervisores normales, no para Agentes ni clientes.

Las permissions pasadas al método son un set de codenames de `PermisoOML` asociados al rol del usuario. Para nuestro módulo, podemos ignorar este check y simplemente retornar el ítem siempre (cualquier usuario con acceso al sidebar lo ve), o crear un permiso propio `analytics_pro_view`.

---

## 6. Nombres reales de grupos

```
id=1  Administrador
id=2  Gerente
id=3  Supervisor
id=4  Referente
id=5  Agente
id=6  Cliente Webphone
id=8  Coordinador
```

**GRUPOS_PERMITIDOS** para `analyticspro`:
```python
GRUPOS_PERMITIDOS = ['Administrador', 'Gerente', 'Supervisor', 'Coordinador']
```

La propiedad `get_tiene_permiso_administracion()` ya cubre Administrador + Supervisor (suficiente para el sidebar). Las vistas individuales se decoran adicionalmente si se quiere excluir Gerente/Coordinador.

---

## 7. Servicios systemd y comando de arranque

| Servicio | Descripción |
|---|---|
| `omnileads.service` | uWSGI — app principal Django |
| `omnileads-daphne.service` | Daphne — WebSockets (Django Channels) |
| `nginx.service` | Reverse proxy (SSL Let's Encrypt) |
| `asterisk.service` + `asterisk-reloader.service` | PBX |
| `redis.service` | Redis (cache + WebSockets) |
| `container-oml-websockets-server.service` | Docker container WebSocket server |

**Comandos de restart tras deploy:**
```bash
systemctl restart omnileads.service        # recarga uWSGI (también relee settings)
systemctl restart omnileads-daphne.service # solo si tocamos ASGI
# nginx: solo si tocamos su config
systemctl reload nginx
```

**venv:** `/opt/omnileads/virtualenv/`  
**uWSGI ini:** `/opt/omnileads/run/oml_uwsgi.ini` (30 workers, harakiri=600s)

---

## 8. Estáticos y reverse-proxy

- **STATIC_ROOT:** `/opt/omnileads/static/` → nginx sirve `/static/ → /opt/omnileads/static/`
- **collectstatic:** `python manage.py collectstatic --noinput` copia a `/opt/omnileads/static/`
- **Nuestros estáticos:** irán a `/opt/omnileads/static/analyticspro/` (auto via `collectstatic`)
- **URL pattern:** `location /static/ { alias /opt/omnileads/static/; }` en nginx
- **SSL:** Let's Encrypt via Certbot, `https://capresoca.iptegra.co`
- **Bootstrap:** 4.0.0 **vendorizado** en `/opt/omnileads/static/bootstrap-4.0.0/`
- **jQuery:** 2.2.4 vendorizado
- **Font Awesome** vendorizado
- **django-compressor** activo (templates usan `{% compress js %}`)

**Para `analyticspro`:** usar `{% load static %}` normalmente. Los assets propios van en `analyticspro/static/analyticspro/`. No depender de CDN (el server puede no tener salida a internet en runtime).

---

## 9. Localización de `omnileads_local`

**La BD secundaria NO existe aún.** Se debe crear:

```bash
# Como postgres o root con PGPASSWORD
PGPASSWORD=c4pr3s0c4.c4ll psql -h localhost -U omnileads postgres -c "
  CREATE DATABASE omnileads_local OWNER omnileads;
  CREATE USER analytics WITH PASSWORD 'analytics_password';
  GRANT CONNECT ON DATABASE omnileads_local TO analytics;
"
# Luego conectar a omnileads_local y dar permisos de SELECT + write en sync_metadata
```

**Localización física:** mismo servidor, misma instancia Postgres (localhost:5432, data en `/var/lib/pgsql/11/data/`).  
**Espacio disponible:** 166 GB libres — sin problema.

**Alias Django:**
```python
DATABASES['analytics'] = {
    'ENGINE': 'django.db.backends.postgresql',
    'HOST': 'localhost',
    'PORT': '5432',
    'NAME': 'omnileads_local',
    'USER': 'analytics',
    'PASSWORD': os.getenv('ANALYTICSPRO_DB_PASSWORD', 'analytics_password'),
    'OPTIONS': {'options': '-c statement_timeout=30000'},
}
```

---

## 10. Versión de Bootstrap y librerías frontend

| Librería | Versión | Fuente |
|---|---|---|
| Bootstrap | **4.0.0** | Vendorizado (`/static/bootstrap-4.0.0/`) |
| jQuery | 2.2.4 | Vendorizado (`/static/jquery-2.2.4.min.js`) |
| Font Awesome | 5.x | Vendorizado (`/static/ominicontacto/CSS/ext/fa-*.css`) |
| Moment.js | disponible | Vendorizado |
| Bootstrap DateTimePicker | disponible | Vendorizado |
| DateRangePicker | disponible | Vendorizado |

**Para `analyticspro`:**
- Heredamos Bootstrap 4, jQuery 2.2.4 y Font Awesome via `{% extends "base.html" %}`
- ApexCharts se agrega como asset propio en `static/analyticspro/vendor/apexcharts.min.js`
- No CDN — copiar el minified a la carpeta vendor antes de `collectstatic`

---

## Resumen de riesgos y resoluciones

| Riesgo del plan | Estado |
|---|---|
| Django antiguo que limite ORM/Celery | ✅ Django 2.2.7 soporta todo lo necesario |
| OmniLeads sin Celery | ✅ Sin Celery → **Plan B: management command + cron** |
| Patrón de menú no estándar | ✅ Registry `supervision_menu_items()` en AppConfig — limpio |
| Conflicto psycopg2 | ✅ psycopg2 2.7.5 ya en venv, compatible |
| `omnileads_local` fuera del server | ✅ Misma instancia postgres — crear BD es el único paso |
| Bootstrap mismatch | ✅ Bootstrap 4.0.0 — igual al que usamos |
| Postgres < 12 | ⚠️ Postgres 11.11 — window functions OK (disponibles desde PG 8.4), CTEs OK. Sin `GENERATED ALWAYS` columns ni algunos PG13+ features. **Sin impacto** para nuestras queries. |

---

## Próximos pasos

1. **Fase 1:** Crear rama `VOML` desde `V2DNDS-FIXNOC` y borrar módulo gestiones (17 items).
2. **Crear BD:** `omnileads_local` en localhost:5432 + usuario `analytics`.
3. **Fase 2:** Scaffold `analyticspro/` dentro de `/opt/omnileads/ominicontacto/`.
4. **Fase 3:** Management command `sync_analytics` + cron.
5. **Deploy:** `systemctl restart omnileads.service` tras instalar.

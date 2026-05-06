#!/usr/bin/env python
"""
Patch settings files to register analyticspro in OmniLeads.
Run on server as: /opt/omnileads/virtualenv/bin/python /tmp/_patch_settings.py
"""
import os
import shutil
from datetime import datetime

BASE = '/opt/omnileads/ominicontacto/ominicontacto/settings/'
ADDONS = BASE + 'addons.py'
LOCAL = BASE + 'oml_settings_local.py'

BACKUP_TS = datetime.now().strftime('%Y%m%d_%H%M%S')

# ── 1. Patch addons.py ────────────────────────────────────────────

addons_append = """
# ── AnalyticsPro (built-in analytics module) ──────────────────────
ADDONS_APPS.append('analyticspro.apps.AnalyticsproConfig')
ADDON_URLPATTERNS.append((r'^', 'analyticspro.urls'))
"""

with open(ADDONS) as f:
    content = f.read()

if 'analyticspro' in content:
    print('[addons.py] already patched — skipping')
else:
    shutil.copy(ADDONS, ADDONS + '.bak.' + BACKUP_TS)
    with open(ADDONS, 'a') as f:
        f.write(addons_append)
    print('[addons.py] patched — analyticspro registered in ADDONS_APPS + ADDON_URLPATTERNS')

# ── 2. Patch oml_settings_local.py ───────────────────────────────

local_append = """

# ══ AnalyticsPro settings ══════════════════════════════════════════
# Secondary analytics database (omnileads_local)
DATABASES['analytics'] = {
    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    'HOST': 'localhost',
    'PORT': os.getenv('PGPORT', '5432'),
    'NAME': 'omnileads_local',
    'USER': 'analytics_user',
    'PASSWORD': 'analytics_pass_2024',
    'CONN_MAX_AGE': 300,
    'OPTIONS': {'options': '-c statement_timeout=30000'},
}
DATABASE_ROUTERS = ['analyticspro.db.AnalyticsRouter']
ANALYTICSPRO_TIMEZONE_DB = 'America/Bogota'
ANALYTICSPRO_INBOUND_ONLY = True
ANALYTICSPRO_SYNC_BATCH_SIZE = 10000
"""

with open(LOCAL) as f:
    local_content = f.read()

if 'analyticspro' in local_content.lower():
    print('[oml_settings_local.py] already patched — skipping')
else:
    shutil.copy(LOCAL, LOCAL + '.bak.' + BACKUP_TS)
    with open(LOCAL, 'a') as f:
        f.write(local_append)
    print('[oml_settings_local.py] patched — analytics DB + routers added')

# ── 3. Verify ────────────────────────────────────────────────────

print('\n--- Verification ---')
with open(ADDONS) as f:
    c = f.read()
print('addons.py has analyticspro:', 'analyticspro' in c)
with open(LOCAL) as f:
    c = f.read()
print('oml_settings_local.py has analytics DB:', "DATABASES['analytics']" in c)
print('Done.')

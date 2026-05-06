#!/usr/bin/env python
"""Server audit helper — read key lines from settings and urls."""
import os

base = '/opt/omnileads/ominicontacto/ominicontacto/settings/'
urls_path = '/opt/omnileads/ominicontacto/ominicontacto/urls.py'

KEYWORDS = ['INSTALLED_APPS', 'oml_settings_local', 'ADDON_URLPATTERNS', 'ADDON_APPS',
            'analyticspro', 'DATABASE_ROUTERS', 'addons']

for fname in ['defaults.py', 'production.py', 'addons.py']:
    fpath = base + fname
    print(f"\n=== {fname} KEY LINES ===")
    try:
        with open(fpath) as f:
            lines = f.readlines()
        for i, line in enumerate(lines, 1):
            for kw in KEYWORDS:
                if kw in line:
                    print(f"{i}: {line}", end='')
                    break
        print(f"  (total {len(lines)} lines)")
    except Exception as e:
        print(f"  ERROR: {e}")

print("\n=== oml_settings_local.py FULL ===")
with open(base + 'oml_settings_local.py') as f:
    print(f.read())

print("\n=== addons.py FULL ===")
try:
    with open(base + 'addons.py') as f:
        print(f.read())
except Exception as e:
    print(f"ERROR: {e}")

print("\n=== urls.py ALL ===")
with open(urls_path) as f:
    for i, line in enumerate(f, 1):
        print(f"{i}: {line}", end='')

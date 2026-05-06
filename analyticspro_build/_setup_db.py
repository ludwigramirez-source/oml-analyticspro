#!/usr/bin/env python
"""
Create analytics_user and omnileads_local database on the server.
Run as: /opt/omnileads/virtualenv/bin/python /tmp/_setup_db.py
"""
import os
import subprocess

# Read the production postgres credentials from environment
PGHOST = os.getenv('PGHOST', 'localhost')
PGPORT = os.getenv('PGPORT', '5432')
PGUSER = os.getenv('PGUSER', 'omnileads')
PGDATABASE = os.getenv('PGDATABASE', 'omnileads')

print(f"PGHOST={PGHOST} PGPORT={PGPORT} PGUSER={PGUSER} PGDATABASE={PGDATABASE}")

import psycopg2

def psql(sql, dbname='postgres', autocommit=True):
    conn = psycopg2.connect(host=PGHOST, port=PGPORT, user=PGUSER,
                            dbname=dbname)
    conn.autocommit = autocommit
    cur = conn.cursor()
    try:
        cur.execute(sql)
        try:
            rows = cur.fetchall()
            return rows
        except Exception:
            return []
    except psycopg2.errors.DuplicateObject as e:
        print(f"  SKIP (already exists): {e}")
        return []
    except Exception as e:
        print(f"  ERROR: {e}")
        return []
    finally:
        cur.close()
        conn.close()

# 1. Create analytics_user
print('\n[1] Creating analytics_user...')
rows = psql("SELECT 1 FROM pg_roles WHERE rolname='analytics_user'")
if rows:
    print('  analytics_user already exists')
else:
    psql("CREATE ROLE analytics_user WITH LOGIN PASSWORD 'analytics_pass_2024'")
    print('  analytics_user created')

# 2. Create omnileads_local database
print('\n[2] Creating omnileads_local database...')
rows = psql("SELECT 1 FROM pg_database WHERE datname='omnileads_local'")
if rows:
    print('  omnileads_local already exists')
else:
    psql("CREATE DATABASE omnileads_local OWNER analytics_user ENCODING 'UTF8'")
    print('  omnileads_local created')

# 3. Grant permissions on omnileads_local
print('\n[3] Granting permissions on omnileads_local...')
psql("GRANT ALL PRIVILEGES ON DATABASE omnileads_local TO analytics_user", dbname='postgres')
psql("GRANT CONNECT ON DATABASE omnileads_local TO analytics_user", dbname='postgres')
print('  grants applied')

# 4. Grant analytics_user SELECT on source tables (in main omnileads DB)
print('\n[4] Granting SELECT on source tables in main DB...')
grant_sqls = [
    "GRANT SELECT ON reportes_app_llamadalog TO analytics_user",
    "GRANT SELECT ON reportes_app_actividadagentelog TO analytics_user",
    "GRANT SELECT ON ominicontacto_app_campana TO analytics_user",
    "GRANT SELECT ON ominicontacto_app_agenteprofile TO analytics_user",
    "GRANT SELECT ON ominicontacto_app_user TO analytics_user",
    "GRANT SELECT ON ominicontacto_app_pausa TO analytics_user",
]
for sql in grant_sqls:
    r = psql(sql, dbname=PGDATABASE)
    print(f'  {sql[:60]}...')

# 5. Test connection to omnileads_local as analytics_user
print('\n[5] Testing connection to omnileads_local as analytics_user...')
try:
    conn2 = psycopg2.connect(host=PGHOST, port=PGPORT, user='analytics_user',
                              password='analytics_pass_2024', dbname='omnileads_local')
    cur2 = conn2.cursor()
    cur2.execute("SELECT version()")
    print(f'  OK: {cur2.fetchone()[0][:50]}')
    cur2.close()
    conn2.close()
except Exception as e:
    print(f'  FAILED: {e}')

print('\nDB setup complete.')

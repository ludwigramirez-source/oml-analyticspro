"""
Script para verificar valores reales en la base de datos
"""
import os
from collections import Counter

import psycopg2
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Conectar a la base de datos
conn = psycopg2.connect(
    host=os.getenv('OMNILEADS_DB_HOST', 'capresoca.iptegra.co'),
    port=int(os.getenv('OMNILEADS_DB_PORT', '5432')),
    database=os.getenv('OMNILEADS_DB_NAME', 'omnileads'),
    user=os.getenv('OMNILEADS_DB_USER', 'omnileads_readonly'),
    password=os.getenv('OMNILEADS_DB_PASSWORD')
)

cur = conn.cursor()

print("=" * 80)
print("VERIFICACIÓN DE VALORES EN reportes_app_llamadalog")
print("=" * 80)

# 1. Ver qué valores tiene tipo_llamada
print("\n1. VALORES DE tipo_llamada:")
cur.execute("""
    SELECT tipo_llamada, COUNT(*) as total
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
    GROUP BY tipo_llamada
    ORDER BY tipo_llamada
""")
for row in cur.fetchall():
    print(f"   tipo_llamada = {row[0]}: {row[1]:,} registros")

# 2. Ver qué valores tiene tipo_campana
print("\n2. VALORES DE tipo_campana:")
cur.execute("""
    SELECT tipo_campana, COUNT(*) as total
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
    GROUP BY tipo_campana
    ORDER BY tipo_campana
""")
for row in cur.fetchall():
    print(f"   tipo_campana = {row[0]}: {row[1]:,} registros")

# 3. Ver qué eventos hay
print("\n3. EVENTOS MÁS COMUNES:")
cur.execute("""
    SELECT event, COUNT(*) as total
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
    GROUP BY event
    ORDER BY total DESC
    LIMIT 20
""")
for row in cur.fetchall():
    print(f"   {row[0]:20} : {row[1]:,} registros")

# 4. Combinación tipo_llamada + tipo_campana
print("\n4. COMBINACIONES tipo_llamada + tipo_campana:")
cur.execute("""
    SELECT tipo_llamada, tipo_campana, COUNT(*) as total
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
    GROUP BY tipo_llamada, tipo_campana
    ORDER BY total DESC
""")
for row in cur.fetchall():
    print(f"   tipo_llamada={row[0]}, tipo_campana={row[1]}: {row[2]:,} registros")

# 5. Total de registros en octubre
print("\n5. TOTAL DE REGISTROS EN OCTUBRE 2024:")
cur.execute("""
    SELECT COUNT(*) as total
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
""")
total = cur.fetchone()[0]
print(f"   {total:,} registros totales")

# 6. Ver algunos registros ejemplo
print("\n6. EJEMPLOS DE REGISTROS:")
cur.execute("""
    SELECT callid, tipo_llamada, tipo_campana, event, duracion_llamada
    FROM reportes_app_llamadalog
    WHERE time >= '2024-10-01' AND time < '2024-11-01'
    LIMIT 10
""")
print("   callid | tipo_llamada | tipo_campana | event | duracion")
print("   " + "-" * 70)
for row in cur.fetchall():
    print(f"   {row[0]:<10} | {row[1]:<12} | {row[2]:<12} | {row[3]:<15} | {row[4]}")

cur.close()
conn.close()

print("\n" + "=" * 80)
print("VERIFICACIÓN COMPLETADA")
print("=" * 80)

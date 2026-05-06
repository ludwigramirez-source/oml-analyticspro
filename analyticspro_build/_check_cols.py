import psycopg2, os

conn = psycopg2.connect(
    host=os.getenv('PGHOST', 'localhost'),
    port=int(os.getenv('PGPORT', '5432')),
    dbname=os.getenv('PGDATABASE', 'omnileads'),
    user=os.getenv('PGUSER', 'omnileads'),
    password=os.getenv('PGPASSWORD', ''),
)
conn.autocommit = True
cur = conn.cursor()

# Check column types
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'reportes_app_actividadagentelog'
    ORDER BY ordinal_position
""")
print("=== actividadagentelog columns ===")
for row in cur.fetchall():
    print(row)

# Sample pausa_id values
cur.execute("SELECT id, agente_id, event, pausa_id FROM reportes_app_actividadagentelog WHERE pausa_id IS NOT NULL LIMIT 3")
print("\n=== rows with pausa_id ===")
for row in cur.fetchall():
    print(repr(row), [type(v) for v in row])

# Check all distinct pausa_id-ish values near the failing row
cur.execute("SELECT id, time, agente_id, event, pausa_id FROM reportes_app_actividadagentelog WHERE id BETWEEN 1 AND 5 ORDER BY id")
print("\n=== first 5 rows ===")
for row in cur.fetchall():
    print(repr(row))

cur.close()
conn.close()

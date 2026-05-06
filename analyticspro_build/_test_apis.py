"""
Quick smoke test for AnalyticsPro services.
Run via: manage.py shell < /tmp/_test_apis.py
"""
import json
from datetime import date, timedelta

today = date.today()
before = today - timedelta(days=300)  # cover Jul 2025 – Jan 2026 data window

filters = {
    'fecha_inicio': before.strftime('%Y-%m-%d'),
    'fecha_fin': today.strftime('%Y-%m-%d'),
}

print("=== Testing with filters:", filters, "===\n")

# ─── CallAnalyticsService ─────────────────────────────────────────────────────
from analyticspro.services.call_analytics import CallAnalyticsService
svc = CallAnalyticsService()

print("-- get_kpis --")
kpis = svc.get_kpis(filters)
assert kpis.get('total_llamadas', 0) > 0, "KPIs returned 0 total_llamadas"
print(json.dumps(kpis, default=str, indent=2)[:400])

print("\n-- get_distribucion_llamadas --")
dist = svc.get_distribucion_llamadas(filters)
assert len(dist) > 0, "distribucion_llamadas empty"
print(json.dumps(dist, default=str, indent=2)[:300])

print("\n-- get_causas_no_atencion --")
causas = svc.get_causas_no_atencion(filters)
assert len(causas) > 0, "causas_no_atencion empty"
print(json.dumps(causas, default=str, indent=2)[:300])

print("\n-- get_llamadas_atendidas (page 1, per_page=3) --")
atend = svc.get_llamadas_atendidas(filters, page=1, per_page=3)
assert atend.get('total', 0) > 0, "llamadas_atendidas total=0"
assert len(atend.get('data', [])) == 3, f"expected 3 rows, got {len(atend.get('data', []))}"
print("total:", atend['total'], "data rows:", len(atend['data']))

print("\n-- get_llamadas_abandonadas (page 1, per_page=3) --")
aban = svc.get_llamadas_abandonadas(filters, page=1, per_page=3)
assert aban.get('total', 0) > 0, "llamadas_abandonadas total=0"
print("total:", aban['total'], "data rows:", len(aban.get('data', [])))

print("\n-- get_evolucion_hora --")
evh = svc.get_evolucion_hora(filters)
assert len(evh) > 0, "evolucion_hora empty"
print("hours:", len(evh), "sample:", json.dumps(evh[0], default=str))

print("\n-- get_nivel_servicio --")
ns = svc.get_nivel_servicio(filters)
print("nivel_servicio:", json.dumps(ns, default=str)[:200])

# ─── AgentAnalyticsService ───────────────────────────────────────────────────
from analyticspro.services.agent_analytics import AgentAnalyticsService
asvc = AgentAnalyticsService()

print("\n-- get_rendimiento --")
rend = asvc.get_rendimiento(filters)
assert len(rend) > 0, "rendimiento empty"
print("agents:", len(rend))
print("first:", json.dumps(rend[0], default=str)[:200])

print("\n-- get_pausas_dict --")
from analyticspro.services.base import AnalyticsBaseService
bsvc = AnalyticsBaseService()
pausas = bsvc.get_pausas_dict()
print("pausas:", pausas)

# ─── CallAnalyticsExtendedService ────────────────────────────────────────────
from analyticspro.services.call_analytics_extended import CallAnalyticsExtendedService
esvc = CallAnalyticsExtendedService()

print("\n-- get_distribucion_por_campana_detalle --")
camp = esvc.get_distribucion_por_campana_detalle(filters)
assert len(camp) > 0, "distribucion_campana_detalle empty"
print("campaigns:", len(camp))
print("first:", json.dumps(camp[0], default=str)[:200])

print("\n-- get_distribucion_horaria_detallada --")
hor = esvc.get_distribucion_horaria_detallada(filters)
print("hourly rows:", len(hor))

print("\n-- get_transferencias --")
transf = esvc.get_transferencias(filters)
print("transferencias:", json.dumps(transf, default=str)[:300])

# ─── Meta queries ─────────────────────────────────────────────────────────────
print("\n-- campanas (meta) --")
with bsvc.cursor() as cur:
    cur.execute("SELECT id, nombre, type, estado FROM ominicontacto_app_campana WHERE es_template = false ORDER BY nombre")
    rows = bsvc.fetchall_dict(cur)
assert len(rows) > 0, "no campanas found"
print("campanas:", len(rows))
for r in rows[:3]:
    print(" ", r)

print("\n=== ALL TESTS PASSED ===")

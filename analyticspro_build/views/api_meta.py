"""Endpoints JSON para metadatos: campañas, agentes, sync status."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import connections

from analyticspro.views.mixins import require_analytics_access
from analyticspro.services.base import AnalyticsBaseService


def _json(data, status=200):
    return JsonResponse(data, safe=False, status=status)


@login_required
@require_analytics_access
def campanas(request):
    svc = AnalyticsBaseService()
    with svc.cursor() as cur:
        cur.execute("""
            SELECT id, nombre, type, estado
            FROM ominicontacto_app_campana
            WHERE es_template = false
            ORDER BY nombre
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return _json(rows)


@login_required
@require_analytics_access
def agentes(request):
    svc = AnalyticsBaseService()
    with svc.cursor() as cur:
        cur.execute("""
            SELECT ap.id, u.first_name, u.last_name,
                   u.first_name || ' ' || u.last_name AS nombre_completo,
                   ap.sip_extension
            FROM ominicontacto_app_agenteprofile ap
            JOIN ominicontacto_app_user u ON u.id = ap.user_id
            WHERE ap.borrado = false AND ap.is_inactive = false
            ORDER BY u.first_name, u.last_name
        """)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, row)) for row in cur.fetchall()]
    return _json(rows)


@login_required
@require_analytics_access
def sync_status(request):
    try:
        svc = AnalyticsBaseService()
        with svc.cursor() as cur:
            cur.execute("""
                SELECT table_name, last_synced_id, last_sync_time,
                       sync_status, rows_synced, rows_total,
                       error_message, sync_duration_s
                FROM sync_metadata
                ORDER BY table_name
            """)
            cols = [d[0] for d in cur.description]
            tables = [dict(zip(cols, row)) for row in cur.fetchall()]

        # Normalize datetime fields
        for t in tables:
            if t.get('last_sync_time'):
                t['last_sync_time'] = str(t['last_sync_time'])

        total_rows = sum(t.get('rows_total', 0) or 0 for t in tables)
        last_sync = max(
            (t['last_sync_time'] for t in tables if t.get('last_sync_time')),
            default=None
        )
        has_error = any(t.get('sync_status') == 'error' for t in tables)

        return _json({
            'tables': tables,
            'total_rows': total_rows,
            'last_sync_time': last_sync,
            'error': 'Hay tablas con errores de sync' if has_error else None,
        })
    except Exception as e:
        return _json({
            'tables': [],
            'total_rows': 0,
            'last_sync_time': None,
            'error': str(e),
        })

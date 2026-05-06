"""Endpoints JSON para analytics de agentes."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse

from analyticspro.views.mixins import require_analytics_access, parse_filters
from analyticspro.services.agent_analytics import AgentAnalyticsService


def _svc():
    return AgentAnalyticsService()


def _json(data, status=200):
    return JsonResponse(data, safe=False, status=status)


@login_required
@require_analytics_access
def rendimiento(request):
    filters = parse_filters(request)
    return _json(_svc().get_rendimiento(filters))


@login_required
@require_analytics_access
def disponibilidad(request):
    filters = parse_filters(request)
    return _json(_svc().get_disponibilidad(filters))


@login_required
@require_analytics_access
def disponibilidad_heatmap(request):
    filters = parse_filters(request)
    return _json(_svc().get_disponibilidad_heatmap(filters))


@login_required
@require_analytics_access
def sesiones(request, agente_id):
    filters = parse_filters(request)
    return _json(_svc().get_sesiones_agente(agente_id, filters))


@login_required
@require_analytics_access
def pausas(request, agente_id):
    filters = parse_filters(request)
    return _json(_svc().get_pausas_agente(agente_id, filters))


@login_required
@require_analytics_access
def timeline(request, agente_id):
    filters = parse_filters(request)
    return _json(_svc().get_timeline_agente(agente_id, filters))


@login_required
@require_analytics_access
def export_rendimiento(request):
    filters = parse_filters(request)
    data = _svc().export_rendimiento_excel(filters)
    response = HttpResponse(
        data,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="rendimiento_agentes.xlsx"'
    return response

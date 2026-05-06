"""Endpoints JSON para analytics extendido de llamadas."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from analyticspro.views.mixins import require_analytics_access, parse_filters
from analyticspro.services.call_analytics_extended import CallAnalyticsExtendedService


def _svc():
    return CallAnalyticsExtendedService()


def _json(data, status=200):
    return JsonResponse(data, safe=False, status=status)


@login_required
@require_analytics_access
def distribucion_por_campana_detalle(request):
    filters = parse_filters(request)
    return _json(_svc().get_distribucion_por_campana_detalle(filters))


@login_required
@require_analytics_access
def transferencias(request):
    filters = parse_filters(request)
    return _json(_svc().get_transferencias(filters))


@login_required
@require_analytics_access
def distribucion_horaria_detallada(request):
    filters = parse_filters(request)
    agrupar_por = request.GET.get('agrupar_por', 'hora')
    return _json(_svc().get_distribucion_horaria_detallada(filters, agrupar_por))


@login_required
@require_analytics_access
def tabla_distribucion_horaria(request):
    filters = parse_filters(request)
    agrupar_por = request.GET.get('agrupar_por', 'hora')
    if agrupar_por not in ('hora', 'dia', 'semana', 'mes', 'campana'):
        agrupar_por = 'hora'
    return _json(_svc().get_distribucion_horaria_detallada(filters, agrupar_por))


@login_required
@require_analytics_access
def nivel_atencion_campanas(request):
    filters = parse_filters(request)
    umbral = int(request.GET.get('umbral', 80))
    return _json(_svc().get_nivel_atencion_campanas(filters, umbral))


@login_required
@require_analytics_access
def salientes_dashboard(request):
    filters = parse_filters(request)
    return _json(_svc().get_salientes_dashboard(filters))


@login_required
@require_analytics_access
def salientes_por_agente(request):
    filters = parse_filters(request)
    return _json(_svc().get_salientes_por_agente(filters))

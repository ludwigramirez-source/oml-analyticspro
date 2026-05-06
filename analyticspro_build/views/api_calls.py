"""
Endpoints JSON para analytics de llamadas.
Todos los endpoints requieren autenticación + grupo permitido.
"""
import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse

from analyticspro.views.mixins import require_analytics_access, parse_filters
from analyticspro.services.call_analytics import CallAnalyticsService


def _svc():
    return CallAnalyticsService()


def _json(data, status=200):
    return JsonResponse(data, safe=False, status=status)


@login_required
@require_analytics_access
def kpis(request):
    filters = parse_filters(request)
    return _json(_svc().get_kpis(filters))


@login_required
@require_analytics_access
def distribucion_llamadas(request):
    filters = parse_filters(request)
    return _json(_svc().get_distribucion_llamadas(filters))


@login_required
@require_analytics_access
def evolucion_hora(request):
    filters = parse_filters(request)
    return _json(_svc().get_evolucion_hora(filters))


@login_required
@require_analytics_access
def evolucion_diaria(request):
    filters = parse_filters(request)
    return _json(_svc().get_evolucion_diaria(filters))


@login_required
@require_analytics_access
def nivel_servicio(request):
    filters = parse_filters(request)
    return _json(_svc().get_nivel_servicio(filters))


@login_required
@require_analytics_access
def nivel_servicio_detallado(request):
    filters = parse_filters(request)
    return _json(_svc().get_nivel_servicio_detallado(filters))


@login_required
@require_analytics_access
def causas_no_atencion(request):
    filters = parse_filters(request)
    return _json(_svc().get_causas_no_atencion(filters))


@login_required
@require_analytics_access
def llamadas_atendidas(request):
    filters = parse_filters(request)
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 50)), 200)
    sort_by = request.GET.get('sort_by', 'time')
    sort_dir = request.GET.get('sort_dir', 'desc')
    return _json(_svc().get_llamadas_atendidas(filters, page, per_page, sort_by, sort_dir))


@login_required
@require_analytics_access
def llamadas_abandonadas(request):
    filters = parse_filters(request)
    page = int(request.GET.get('page', 1))
    per_page = min(int(request.GET.get('per_page', 50)), 200)
    sort_by = request.GET.get('sort_by', 'time')
    sort_dir = request.GET.get('sort_dir', 'desc')
    return _json(_svc().get_llamadas_abandonadas(filters, page, per_page, sort_by, sort_dir))


@login_required
@require_analytics_access
def llamadas_por_tipo(request):
    filters = parse_filters(request)
    return _json(_svc().get_llamadas_por_tipo(filters))


@login_required
@require_analytics_access
def llamadas_por_campana(request):
    filters = parse_filters(request)
    return _json(_svc().get_llamadas_por_campana(filters))


@login_required
@require_analytics_access
def export_llamadas_atendidas(request):
    filters = parse_filters(request)
    data = _svc().export_llamadas_atendidas_excel(filters)
    response = HttpResponse(
        data,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="llamadas_atendidas.xlsx"'
    return response


@login_required
@require_analytics_access
def export_llamadas_abandonadas(request):
    filters = parse_filters(request)
    data = _svc().export_llamadas_abandonadas_excel(filters)
    response = HttpResponse(
        data,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="llamadas_abandonadas.xlsx"'
    return response

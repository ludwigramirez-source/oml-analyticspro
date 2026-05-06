"""
Decoradores y mixins de acceso para Analytics Pro.
Grupos permitidos: Administrador, Gerente, Supervisor, Coordinador.
"""
import json
from functools import wraps

from django.http import JsonResponse, HttpResponseForbidden


GRUPOS_PERMITIDOS = frozenset([
    'Administrador', 'Gerente', 'Supervisor', 'Coordinador',
])


def _has_analytics_access(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=GRUPOS_PERMITIDOS).exists()


def require_analytics_access(view_func):
    """Decorator que exige pertenencia a GRUPOS_PERMITIDOS."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not _has_analytics_access(request.user):
            if request.headers.get('Accept', '').startswith('application/json'):
                return JsonResponse({'error': 'Acceso denegado'}, status=403)
            return HttpResponseForbidden('Acceso denegado — Analytics Pro')
        return view_func(request, *args, **kwargs)
    return wrapper


def parse_filters(request):
    """
    Extrae filtros estándar de los query params de una request.
    Retorna dict compatible con los servicios de analytics.
    Compatible con Python 3.6+ (strptime instead of fromisoformat).
    """
    from datetime import datetime

    filters = {}

    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    if fecha_inicio:
        try:
            # Accept YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(fecha_inicio.split('+')[0][:19], fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = None
            if dt:
                filters['fecha_inicio'] = dt
        except Exception:
            pass

    if fecha_fin:
        try:
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(fecha_fin.split('+')[0][:19], fmt)
                    break
                except ValueError:
                    continue
            else:
                dt = None
            if dt:
                # Include the full last day if only date was given
                if 'T' not in fecha_fin and dt.hour == 0 and dt.minute == 0:
                    dt = dt.replace(hour=23, minute=59, second=59,
                                    microsecond=999999)
                filters['fecha_fin'] = dt
        except Exception:
            pass

    campana_ids = request.GET.get('campana_ids')
    campana_id = request.GET.get('campana_id')
    if campana_ids:
        try:
            filters['campana_ids'] = [int(x) for x in campana_ids.split(',') if x.strip()]
        except ValueError:
            pass
    elif campana_id:
        try:
            filters['campana_id'] = int(campana_id)
        except ValueError:
            pass

    agente_ids = request.GET.get('agente_ids')
    agente_id = request.GET.get('agente_id')
    if agente_ids:
        try:
            filters['agente_ids'] = [int(x) for x in agente_ids.split(',') if x.strip()]
        except ValueError:
            pass
    elif agente_id:
        try:
            filters['agente_id'] = int(agente_id)
        except ValueError:
            pass

    tipo_llamada = request.GET.get('tipo_llamada')
    if tipo_llamada:
        filters['tipo_llamada'] = tipo_llamada

    tipo_campana = request.GET.get('tipo_campana')
    if tipo_campana:
        try:
            filters['tipo_campana'] = int(tipo_campana)
        except ValueError:
            pass

    return filters

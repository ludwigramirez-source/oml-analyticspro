"""Vista principal del dashboard de Analytics Pro."""
from datetime import date, timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from analyticspro.views.mixins import require_analytics_access


@login_required
@require_analytics_access
def index(request):
    """Renderiza el dashboard principal de Analytics Pro."""
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)

    # Use URL params when provided (allows deep-linking with specific date ranges)
    fecha_inicio = request.GET.get('fecha_inicio', thirty_days_ago.strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', today.strftime('%Y-%m-%d'))

    # Validate format (YYYY-MM-DD); fall back to defaults on bad input
    try:
        from datetime import datetime
        datetime.strptime(fecha_inicio[:10], '%Y-%m-%d')
        fecha_inicio = fecha_inicio[:10]
    except (ValueError, TypeError):
        fecha_inicio = thirty_days_ago.strftime('%Y-%m-%d')
    try:
        from datetime import datetime
        datetime.strptime(fecha_fin[:10], '%Y-%m-%d')
        fecha_fin = fecha_fin[:10]
    except (ValueError, TypeError):
        fecha_fin = today.strftime('%Y-%m-%d')

    context = {
        'page_title': 'Analytics Pro',
        'fecha_default_inicio': fecha_inicio,
        'fecha_default_fin': fecha_fin,
    }
    return render(request, 'analyticspro/dashboard.html', context)

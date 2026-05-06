from django.apps import AppConfig
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class AnalyticsproConfig(AppConfig):
    name = 'analyticspro'
    verbose_name = _('Analytics Pro')

    def supervision_menu_items(self, request, permissions):
        """Agrega el item Analytics Pro al menu lateral de OmniLeads."""
        return [{
            'order': 550,
            'label': _('Analytics Pro'),
            'icon': 'icon-graph',
            'url': reverse('analyticspro:dashboard'),
        }]

    def ready(self):
        pass

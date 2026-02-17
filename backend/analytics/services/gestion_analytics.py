"""
Servicio de análisis de gestiones de incidencias
Tablas: ominicontacto_app_customformgestion + ominicontacto_app_customformincidencias
"""
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import config
from ..models.omnileads_models import (
    AgenteProfile,
    Campana,
    CustomFormGestion,
    CustomFormIncidencias,
    User,
)


class GestionAnalyticsService:
    """Servicio para análisis de gestiones (customformgestion)"""

    def __init__(self, db: Session):
        self.db = db

    def _apply_filters(self, query, filters: Dict):
        """Aplica filtros comunes a las consultas de gestiones"""
        if filters.get('fecha_inicio'):
            query = query.filter(
                CustomFormGestion.fecha >= filters['fecha_inicio']
            )
        if filters.get('fecha_fin'):
            query = query.filter(
                CustomFormGestion.fecha <= filters['fecha_fin']
            )
        if filters.get('campana_ids'):
            query = query.filter(
                CustomFormGestion.campana_id.in_(
                    filters['campana_ids']
                )
            )
        elif filters.get('campana_id'):
            query = query.filter(
                CustomFormGestion.campana_id == filters['campana_id']
            )
        if filters.get('agente_ids'):
            query = query.filter(
                CustomFormGestion.agent_id.in_(
                    filters['agente_ids']
                )
            )
        elif filters.get('agente_id'):
            query = query.filter(
                CustomFormGestion.agent_id == filters['agente_id']
            )
        return query

    def get_gestiones_kpis(self, filters: Dict = None) -> Dict:
        """KPIs principales de gestiones"""
        filters = filters or {}

        query = self.db.query(CustomFormGestion)
        query = self._apply_filters(query, filters)

        total = query.count()

        agentes_activos = query.with_entities(
            func.count(func.distinct(CustomFormGestion.agent_id))
        ).scalar() or 0

        campanas_activas = query.with_entities(
            func.count(func.distinct(CustomFormGestion.campana_id))
        ).scalar() or 0

        promedio_por_agente = (
            round(total / agentes_activos, 2)
            if agentes_activos > 0 else 0
        )

        # Top incidencia
        top_incidencia = self.db.query(
            CustomFormIncidencias.descripcion,
            func.count(CustomFormGestion.id).label('total'),
        ).join(
            CustomFormGestion,
            CustomFormGestion.incidencia_id
            == CustomFormIncidencias.id,
        )
        top_incidencia = self._apply_filters(top_incidencia, filters)
        top_incidencia = (
            top_incidencia.group_by(CustomFormIncidencias.descripcion)
            .order_by(func.count(CustomFormGestion.id).desc())
            .first()
        )

        return {
            'total_gestiones': total,
            'agentes_activos': agentes_activos,
            'campanas_activas': campanas_activas,
            'promedio_por_agente': promedio_por_agente,
            'top_incidencia': (
                top_incidencia.descripcion if top_incidencia else ''
            ),
            'top_incidencia_total': (
                top_incidencia.total if top_incidencia else 0
            ),
        }

    def get_gestiones_por_agente(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por agente"""
        filters = filters or {}

        query = self.db.query(
            CustomFormGestion.agent_id,
            User.first_name,
            User.last_name,
            func.count(CustomFormGestion.id).label(
                'total_gestiones'
            ),
        ).outerjoin(
            AgenteProfile,
            CustomFormGestion.agent_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )

        query = self._apply_filters(query, filters)

        resultados = (
            query.group_by(
                CustomFormGestion.agent_id,
                User.first_name,
                User.last_name,
            )
            .order_by(func.count(CustomFormGestion.id).desc())
            .all()
        )

        return [
            {
                'agente_id': r.agent_id,
                'agente': (
                    f'{r.first_name or ""} '
                    f'{r.last_name or ""}'.strip()
                    or f'Agente {r.agent_id}'
                ),
                'total_gestiones': r.total_gestiones,
            }
            for r in resultados
        ]

    def get_gestiones_por_campana(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por campaña"""
        filters = filters or {}

        query = self.db.query(
            CustomFormGestion.campana_id,
            Campana.nombre.label('campana_nombre'),
            func.count(CustomFormGestion.id).label(
                'total_gestiones'
            ),
        ).outerjoin(
            Campana, CustomFormGestion.campana_id == Campana.id
        )

        query = self._apply_filters(query, filters)

        resultados = (
            query.group_by(
                CustomFormGestion.campana_id, Campana.nombre
            )
            .order_by(func.count(CustomFormGestion.id).desc())
            .all()
        )

        return [
            {
                'campana_id': r.campana_id,
                'campana': (
                    r.campana_nombre
                    or f'Campana {r.campana_id}'
                ),
                'total_gestiones': r.total_gestiones,
            }
            for r in resultados
        ]

    def get_gestiones_por_incidencia(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por tipo de incidencia"""
        filters = filters or {}

        query = self.db.query(
            CustomFormIncidencias.id,
            CustomFormIncidencias.codigo,
            CustomFormIncidencias.descripcion,
            func.count(CustomFormGestion.id).label(
                'total_gestiones'
            ),
        ).join(
            CustomFormGestion,
            CustomFormGestion.incidencia_id
            == CustomFormIncidencias.id,
        )

        query = self._apply_filters(query, filters)

        resultados = (
            query.group_by(
                CustomFormIncidencias.id,
                CustomFormIncidencias.codigo,
                CustomFormIncidencias.descripcion,
            )
            .order_by(func.count(CustomFormGestion.id).desc())
            .all()
        )

        return [
            {
                'incidencia_id': r.id,
                'codigo': r.codigo,
                'descripcion': r.descripcion,
                'total_gestiones': r.total_gestiones,
            }
            for r in resultados
        ]

    def get_gestiones_detalle(
        self,
        filters: Dict = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict:
        """Detalle paginado de gestiones"""
        from ..config import config

        filters = filters or {}

        query = self.db.query(
            CustomFormGestion,
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
            Campana.nombre.label('campana_nombre'),
            CustomFormIncidencias.descripcion.label(
                'incidencia_nombre'
            ),
        ).outerjoin(
            AgenteProfile,
            CustomFormGestion.agent_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        ).outerjoin(
            Campana, CustomFormGestion.campana_id == Campana.id
        ).outerjoin(
            CustomFormIncidencias,
            CustomFormGestion.incidencia_id
            == CustomFormIncidencias.id,
        )

        query = self._apply_filters(query, filters)

        total = query.count()

        offset = (page - 1) * per_page
        resultados = (
            query.order_by(CustomFormGestion.fecha.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        local_tz = config.get_timezone()

        gestiones = []
        for r in resultados:
            g = r.CustomFormGestion

            fecha_local = g.fecha.astimezone(local_tz)

            gestiones.append({
                'id': g.id,
                'nombre': g.nombre,
                'telefono': g.telefono,
                'nis': g.nis,
                'incidencia': r.incidencia_nombre or '',
                'fecha': fecha_local.strftime('%Y-%m-%d'),
                'hora': fecha_local.strftime('%H:%M:%S'),
                'agente': (
                    f'{r.agente_nombre or ""} '
                    f'{r.agente_apellido or ""}'.strip()
                    or f'Agente {g.agent_id}'
                ),
                'campana': (
                    r.campana_nombre
                    or f'Campana {g.campana_id}'
                ),
                'call_id': g.call_id or '',
                'rec_file': g.rec_file or '',
            })

        return {
            'data': gestiones,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
        }

    def get_gestiones_por_dia(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por día (timezone local)"""
        filters = filters or {}

        # Convertir fecha a timezone local para agrupar
        local_fecha = func.timezone(
            config.TIMEZONE_NAME, CustomFormGestion.fecha
        )

        query = self.db.query(
            func.date(local_fecha).label('dia'),
            func.count(CustomFormGestion.id).label('total'),
        )

        query = self._apply_filters(query, filters)

        resultados = (
            query.group_by(func.date(local_fecha))
            .order_by(func.date(local_fecha))
            .all()
        )

        return [
            {
                'dia': (
                    r.dia.strftime('%Y-%m-%d') if r.dia else ''
                ),
                'total': r.total,
            }
            for r in resultados
        ]

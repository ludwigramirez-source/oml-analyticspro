"""
Servicio de análisis de gestiones de incidencias
Tablas: ominicontacto_app_customformgestion + ominicontacto_app_customformincidencias
"""
from typing import Dict, List

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from ..config import config
from ..constants import (
    EVENTOS_ATENDIDAS,
    TIPO_ENTRANTE,
    TIPO_SALIENTE,
    TIPOS_LLAMADA_ACTIVOS,
)
from ..models.omnileads_models import (
    AgenteProfile,
    Campana,
    CustomFormGestion,
    CustomFormIncidencias,
    LlamadaLog,
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
        """Detalle paginado de gestiones con duración de llamada"""
        filters = filters or {}
        page = max(1, page)
        per_page = max(1, min(per_page, 200))

        # Subquery 1: hora real de la llamada (cualquier evento)
        # Matchea incluso llamadas en curso (ENTERQUEUE, CONNECT)
        hora_sq = self.db.query(
            LlamadaLog.callid.label('callid'),
            func.max(LlamadaLog.time).label(
                'hora_llamada'
            ),
        ).filter(
            LlamadaLog.callid.isnot(None),
            LlamadaLog.callid != '',
        ).group_by(
            LlamadaLog.callid
        ).subquery()

        # Subquery 2: duración (solo eventos atendidos)
        duracion_sq = self.db.query(
            LlamadaLog.callid.label('callid'),
            func.max(
                LlamadaLog.duracion_llamada
            ).label('duracion'),
        ).filter(
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
            LlamadaLog.callid.isnot(None),
            LlamadaLog.callid != '',
        ).group_by(
            LlamadaLog.callid
        ).subquery()

        query = self.db.query(
            CustomFormGestion,
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
            Campana.nombre.label('campana_nombre'),
            CustomFormIncidencias.descripcion.label(
                'incidencia_nombre'
            ),
            duracion_sq.c.duracion.label(
                'duracion_llamada'
            ),
            hora_sq.c.hora_llamada.label(
                'hora_llamada'
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
        ).outerjoin(
            hora_sq,
            CustomFormGestion.call_id
            == hora_sq.c.callid,
        ).outerjoin(
            duracion_sq,
            CustomFormGestion.call_id
            == duracion_sq.c.callid,
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

        gestiones = []
        for r in resultados:
            g = r.CustomFormGestion

            # Hora de la llamada (LlamadaLog.time) o
            # fallback a fecha de gestión
            ts = r.hora_llamada or g.fecha

            gestiones.append({
                'id': g.id,
                'nombre': g.nombre,
                'telefono': g.telefono,
                'nis': g.nis,
                'incidencia': r.incidencia_nombre or '',
                'fecha': ts.strftime('%Y-%m-%d') if ts else '-',
                'hora': ts.strftime('%H:%M:%S') if ts else '-',
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
                'duracion_llamada': (
                    r.duracion_llamada or 0
                ),
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
            config.TIMEZONE_DB, CustomFormGestion.fecha
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

    # ── Auditoría: Llamadas atendidas sin gestión ──────────────

    def _apply_llamada_filters(self, query, filters: Dict):
        """Aplica filtros a queries sobre LlamadaLog"""
        if filters.get('fecha_inicio'):
            query = query.filter(
                LlamadaLog.time >= filters['fecha_inicio']
            )
        if filters.get('fecha_fin'):
            query = query.filter(
                LlamadaLog.time <= filters['fecha_fin']
            )
        if filters.get('campana_ids'):
            query = query.filter(
                LlamadaLog.campana_id.in_(
                    filters['campana_ids']
                )
            )
        elif filters.get('campana_id'):
            query = query.filter(
                LlamadaLog.campana_id == filters['campana_id']
            )
        if filters.get('agente_ids'):
            query = query.filter(
                LlamadaLog.agente_id.in_(
                    filters['agente_ids']
                )
            )
        elif filters.get('agente_id'):
            query = query.filter(
                LlamadaLog.agente_id == filters['agente_id']
            )
        return query

    def get_auditoria_gestiones(
        self, filters: Dict = None
    ) -> Dict:
        """
        KPIs de auditoría: total atendidas vs total gestiones
        vs llamadas sin gestión.
        """
        filters = filters or {}

        # 1) Subquery: último evento por callid (MAX(id))
        last_event_sq = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id'),
        ).filter(
            LlamadaLog.tipo_llamada.in_(
                TIPOS_LLAMADA_ACTIVOS
            ),
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
        )
        last_event_sq = self._apply_llamada_filters(
            last_event_sq, filters
        )
        last_event_sq = last_event_sq.group_by(
            LlamadaLog.callid
        ).subquery()

        # 2) Total llamadas atendidas (callids únicos)
        total_atendidas = self.db.query(
            func.count(last_event_sq.c.callid)
        ).scalar() or 0

        # 3) Total gestiones en el rango
        q_gestiones = self.db.query(
            func.count(CustomFormGestion.id)
        )
        q_gestiones = self._apply_filters(q_gestiones, filters)
        total_gestiones = q_gestiones.scalar() or 0

        # 4) Callids que tienen gestión
        gestion_callids_sq = self.db.query(
            CustomFormGestion.call_id
        ).filter(
            CustomFormGestion.call_id.isnot(None),
            CustomFormGestion.call_id != '',
        )
        gestion_callids_sq = self._apply_filters(
            gestion_callids_sq, filters
        )
        gestion_callids_sq = gestion_callids_sq.subquery()

        # 5) Llamadas atendidas sin gestión
        sin_gestion = self.db.query(
            func.count(last_event_sq.c.callid)
        ).filter(
            ~last_event_sq.c.callid.in_(
                self.db.query(gestion_callids_sq.c.call_id)
            )
        ).scalar() or 0

        # Porcentaje de cobertura
        cobertura = (
            round(
                (total_gestiones / total_atendidas) * 100, 1
            )
            if total_atendidas > 0 else 0
        )

        return {
            'total_atendidas': total_atendidas,
            'total_gestiones': total_gestiones,
            'sin_gestion': sin_gestion,
            'cobertura_pct': cobertura,
        }

    def get_llamadas_sin_gestion(
        self,
        filters: Dict = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict:
        """
        Lista paginada de llamadas atendidas que NO tienen
        registro en customformgestion.
        """
        filters = filters or {}
        page = max(1, page)
        per_page = max(1, min(per_page, 200))

        # Subquery: último evento atendido por callid
        last_event_sq = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id'),
        ).filter(
            LlamadaLog.tipo_llamada.in_(
                TIPOS_LLAMADA_ACTIVOS
            ),
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
        )
        last_event_sq = self._apply_llamada_filters(
            last_event_sq, filters
        )
        last_event_sq = last_event_sq.group_by(
            LlamadaLog.callid
        ).subquery()

        # Subquery: callids que SÍ tienen gestión
        gestion_callids_sq = self.db.query(
            CustomFormGestion.call_id
        ).filter(
            CustomFormGestion.call_id.isnot(None),
            CustomFormGestion.call_id != '',
        )
        gestion_callids_sq = self._apply_filters(
            gestion_callids_sq, filters
        )
        gestion_callids_sq = gestion_callids_sq.subquery()

        # Query principal: llamadas sin gestión
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
        ).join(
            last_event_sq,
            and_(
                LlamadaLog.callid == last_event_sq.c.callid,
                LlamadaLog.id == last_event_sq.c.ultimo_id,
            ),
        ).filter(
            ~LlamadaLog.callid.in_(
                self.db.query(gestion_callids_sq.c.call_id)
            )
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile,
            LlamadaLog.agente_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )

        total = query.count()

        offset = (page - 1) * per_page
        resultados = (
            query.order_by(LlamadaLog.time.desc())
            .offset(offset)
            .limit(per_page)
            .all()
        )

        llamadas = []
        for r in resultados:
            ll = r.LlamadaLog
            local_time = ll.time
            llamadas.append({
                'callid': ll.callid or '',
                'fecha': local_time.strftime('%Y-%m-%d'),
                'hora': local_time.strftime('%H:%M:%S'),
                'numero': ll.numero_marcado or '',
                'evento': ll.event or '',
                'duracion': ll.duracion_llamada or 0,
                'espera': ll.bridge_wait_time or 0,
                'agente': (
                    f'{r.agente_nombre or ""} '
                    f'{r.agente_apellido or ""}'.strip()
                    or f'Agente {ll.agente_id}'
                ),
                'campana': (
                    r.campana_nombre
                    or f'Campana {ll.campana_id}'
                ),
                'tipo_llamada': (
                    'Entrante'
                    if ll.tipo_llamada == TIPO_ENTRANTE
                    else 'Saliente'
                ),
            })

        return {
            'data': llamadas,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (
                (total + per_page - 1) // per_page
            ),
        }

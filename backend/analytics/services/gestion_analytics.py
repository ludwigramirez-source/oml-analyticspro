"""
Servicio de análisis de gestiones de incidencias
Tablas: ominicontacto_app_customformgestion + ominicontacto_app_customformincidencias

REGLA: 1 llamada = 1 gestión.
- Si hay múltiples gestiones para el mismo call_id, se toma la
  de MAX(id) (última registrada).
- Solo se cuentan gestiones cuyo call_id corresponde a una llamada
  ENTRANTE ATENDIDA dentro del rango de fechas consultado.
- Se excluyen: gestiones huérfanas, de llamadas salientes,
  de llamadas abandonadas/en curso/transferidas sin cierre,
  y gestiones de llamadas de otros días.
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

    # ── Filtros compartidos ──────────────────────────────────

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

    # ── Subqueries reutilizables ─────────────────────────────

    def _build_llamadas_atendidas_sq(self, filters: Dict):
        """
        Subquery: callids de llamadas ENTRANTES ATENDIDAS
        (último evento = ATENDIDA) en el rango de fechas.
        Retorna (callid, ultimo_id).
        """
        sq = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id'),
        ).filter(
            LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS),
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
        )
        sq = self._apply_llamada_filters(sq, filters)
        return sq.group_by(LlamadaLog.callid).subquery()

    def _build_gestion_unica_sq(self, filters: Dict):
        """
        Subquery: 1 gestión por call_id (MAX id = última registrada).
        Solo gestiones con call_id no vacío.
        Retorna (call_id, ultimo_gestion_id).
        """
        sq = self.db.query(
            CustomFormGestion.call_id,
            func.max(CustomFormGestion.id).label(
                'ultimo_gestion_id'
            ),
        ).filter(
            CustomFormGestion.call_id.isnot(None),
            CustomFormGestion.call_id != '',
        )
        sq = self._apply_filters(sq, filters)
        return sq.group_by(
            CustomFormGestion.call_id
        ).subquery()

    # ── KPIs de gestiones ────────────────────────────────────

    def get_gestiones_kpis(self, filters: Dict = None) -> Dict:
        """
        KPIs principales de gestiones.
        Usa gestiones deduplicadas (1 por call_id) cruzadas con
        llamadas entrantes atendidas.
        """
        filters = filters or {}

        # Llamadas entrantes atendidas
        atendidas_sq = self._build_llamadas_atendidas_sq(filters)

        # Gestiones únicas por call_id
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # Gestiones válidas = cruce de ambas
        # (call_id existe como callid atendido)
        gestiones_validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        # Contar gestiones válidas
        total = self.db.query(
            func.count(gestiones_validas_sq.c.ultimo_gestion_id)
        ).scalar() or 0

        # Agentes y campañas activos (sobre gestiones válidas)
        stats = self.db.query(
            func.count(
                func.distinct(CustomFormGestion.agent_id)
            ).label('agentes'),
            func.count(
                func.distinct(CustomFormGestion.campana_id)
            ).label('campanas'),
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(
                    gestiones_validas_sq.c.ultimo_gestion_id
                )
            )
        ).first()

        agentes_activos = stats.agentes if stats else 0
        campanas_activas = stats.campanas if stats else 0

        promedio_por_agente = (
            round(total / agentes_activos, 2)
            if agentes_activos > 0 else 0
        )

        # Top incidencia (sobre gestiones válidas)
        top_incidencia = self.db.query(
            CustomFormIncidencias.descripcion,
            func.count(CustomFormGestion.id).label('total'),
        ).join(
            CustomFormGestion,
            CustomFormGestion.incidencia_id
            == CustomFormIncidencias.id,
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(
                    gestiones_validas_sq.c.ultimo_gestion_id
                )
            )
        ).group_by(
            CustomFormIncidencias.descripcion
        ).order_by(
            func.count(CustomFormGestion.id).desc()
        ).first()

        return {
            'total_gestiones': total,
            'agentes_activos': agentes_activos,
            'campanas_activas': campanas_activas,
            'promedio_por_agente': promedio_por_agente,
            'top_incidencia': (
                top_incidencia.descripcion
                if top_incidencia else ''
            ),
            'top_incidencia_total': (
                top_incidencia.total if top_incidencia else 0
            ),
        }

    # ── Agrupaciones ─────────────────────────────────────────

    def get_gestiones_por_agente(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por agente (deduplicadas)"""
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # IDs de gestiones válidas
        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        query = self.db.query(
            CustomFormGestion.agent_id,
            User.first_name,
            User.last_name,
            func.count(CustomFormGestion.id).label(
                'total_gestiones'
            ),
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(validas_sq.c.ultimo_gestion_id)
            )
        ).outerjoin(
            AgenteProfile,
            CustomFormGestion.agent_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        ).group_by(
            CustomFormGestion.agent_id,
            User.first_name,
            User.last_name,
        ).order_by(
            func.count(CustomFormGestion.id).desc()
        ).all()

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
            for r in query
        ]

    def get_gestiones_por_campana(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por campaña (deduplicadas)"""
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        query = self.db.query(
            CustomFormGestion.campana_id,
            Campana.nombre.label('campana_nombre'),
            func.count(CustomFormGestion.id).label(
                'total_gestiones'
            ),
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(validas_sq.c.ultimo_gestion_id)
            )
        ).outerjoin(
            Campana, CustomFormGestion.campana_id == Campana.id
        ).group_by(
            CustomFormGestion.campana_id, Campana.nombre
        ).order_by(
            func.count(CustomFormGestion.id).desc()
        ).all()

        return [
            {
                'campana_id': r.campana_id,
                'campana': (
                    r.campana_nombre
                    or f'Campana {r.campana_id}'
                ),
                'total_gestiones': r.total_gestiones,
            }
            for r in query
        ]

    def get_gestiones_por_incidencia(
        self, filters: Dict = None
    ) -> List[Dict]:
        """Gestiones agrupadas por tipo de incidencia (deduplicadas)"""
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

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
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(validas_sq.c.ultimo_gestion_id)
            )
        ).group_by(
            CustomFormIncidencias.id,
            CustomFormIncidencias.codigo,
            CustomFormIncidencias.descripcion,
        ).order_by(
            func.count(CustomFormGestion.id).desc()
        ).all()

        return [
            {
                'incidencia_id': r.id,
                'codigo': r.codigo,
                'descripcion': r.descripcion,
                'total_gestiones': r.total_gestiones,
            }
            for r in query
        ]

    # ── Detalle paginado ─────────────────────────────────────

    def get_gestiones_detalle(
        self,
        filters: Dict = None,
        page: int = 1,
        per_page: int = 50,
    ) -> Dict:
        """
        Detalle paginado de gestiones con duración de llamada.
        1 gestión por call_id (MAX id), cruzada con llamadas
        entrantes atendidas del mismo rango de fechas.
        """
        filters = filters or {}
        page = max(1, page)
        per_page = max(1, min(per_page, 200))

        # Subquery: llamadas entrantes atendidas
        atendidas_sq = self._build_llamadas_atendidas_sq(filters)

        # Subquery: 1 gestión por call_id (última)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # Subquery: IDs de gestiones válidas
        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
            gestion_unica_sq.c.call_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        # Subquery: hora real de la llamada (cualquier evento)
        hora_sq = self.db.query(
            LlamadaLog.callid.label('callid'),
            func.max(LlamadaLog.time).label('hora_llamada'),
        ).filter(
            LlamadaLog.callid.isnot(None),
            LlamadaLog.callid != '',
        ).group_by(
            LlamadaLog.callid
        ).subquery()

        # Subquery: duración (solo eventos atendidos)
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

        # Query principal: solo gestiones válidas
        query = self.db.query(
            CustomFormGestion,
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
            Campana.nombre.label('campana_nombre'),
            CustomFormIncidencias.descripcion.label(
                'incidencia_nombre'
            ),
            duracion_sq.c.duracion.label('duracion_llamada'),
            hora_sq.c.hora_llamada.label('hora_llamada'),
        ).join(
            validas_sq,
            CustomFormGestion.id
            == validas_sq.c.ultimo_gestion_id,
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
            CustomFormGestion.call_id == hora_sq.c.callid,
        ).outerjoin(
            duracion_sq,
            CustomFormGestion.call_id == duracion_sq.c.callid,
        )

        total = query.count()

        offset = (page - 1) * per_page
        resultados = (
            query.order_by(
                CustomFormGestion.fecha.desc(),
                CustomFormGestion.id.desc(),
            )
            .offset(offset)
            .limit(per_page)
            .all()
        )

        gestiones = []
        for r in resultados:
            g = r.CustomFormGestion
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
                'duracion_llamada': r.duracion_llamada or 0,
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
        """Gestiones válidas agrupadas por día (timezone local)"""
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        local_fecha = func.timezone(
            config.TIMEZONE_DB, CustomFormGestion.fecha
        )

        resultados = self.db.query(
            func.date(local_fecha).label('dia'),
            func.count(CustomFormGestion.id).label('total'),
        ).filter(
            CustomFormGestion.id.in_(
                self.db.query(validas_sq.c.ultimo_gestion_id)
            )
        ).group_by(
            func.date(local_fecha)
        ).order_by(
            func.date(local_fecha)
        ).all()

        return [
            {
                'dia': (
                    r.dia.strftime('%Y-%m-%d') if r.dia else ''
                ),
                'total': r.total,
            }
            for r in resultados
        ]

    # ── Auditoría: Llamadas atendidas sin gestión ────────────

    def get_auditoria_gestiones(
        self, filters: Dict = None
    ) -> Dict:
        """
        KPIs de auditoría: total atendidas vs total gestiones
        deduplicadas vs llamadas sin gestión.
        """
        filters = filters or {}

        # Llamadas entrantes atendidas (callids únicos)
        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        total_atendidas = self.db.query(
            func.count(atendidas_sq.c.callid)
        ).scalar() or 0

        # Gestiones únicas por call_id
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # Gestiones válidas = cruce con llamadas atendidas
        total_gestiones = self.db.query(
            func.count(gestion_unica_sq.c.ultimo_gestion_id)
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).scalar() or 0

        # Llamadas sin gestión
        sin_gestion = self.db.query(
            func.count(atendidas_sq.c.callid)
        ).filter(
            ~atendidas_sq.c.callid.in_(
                self.db.query(gestion_unica_sq.c.call_id)
            )
        ).scalar() or 0

        # Porcentaje de cobertura
        cobertura = (
            round((total_gestiones / total_atendidas) * 100, 1)
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
        registro en customformgestion (deduplicado por call_id).
        """
        filters = filters or {}
        page = max(1, page)
        per_page = max(1, min(per_page, 200))

        # Llamadas entrantes atendidas
        atendidas_sq = self._build_llamadas_atendidas_sq(filters)

        # Gestiones únicas por call_id
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # Query: llamadas sin gestión
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
        ).join(
            atendidas_sq,
            and_(
                LlamadaLog.callid == atendidas_sq.c.callid,
                LlamadaLog.id == atendidas_sq.c.ultimo_id,
            ),
        ).filter(
            ~LlamadaLog.callid.in_(
                self.db.query(gestion_unica_sq.c.call_id)
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
            query.order_by(
                LlamadaLog.time.desc(),
                LlamadaLog.id.desc(),
            )
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

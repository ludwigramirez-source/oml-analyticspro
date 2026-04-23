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

UNIFICACIÓN DE FECHAS (flag USE_FECHA_LOGICA_LLAMADA):
- Off (default): llamadas filtradas por LlamadaLog.time,
  gestiones por CustomFormGestion.fecha. El agente que cierra
  el formulario después de medianoche atribuye la gestión al día
  siguiente aunque la llamada fue antes → diferencia con conteo
  de llamadas.
- On: ambos filtros usan la fecha lógica = día del primer evento
  del callid (MIN(LlamadaLog.time) AT TIME ZONE TIMEZONE_DB). Toda
  gestión cuenta en el mismo día que su llamada. Corrige ~0.7% de
  gestiones +1 día detectadas en diagnóstico de 30 días.
"""
from datetime import timedelta
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

    def _apply_llamada_filters_no_fecha(self, query, filters: Dict):
        """Aplica filtros de LlamadaLog excepto fechas (para fecha_logica_sq)."""
        if filters.get('campana_ids'):
            query = query.filter(
                LlamadaLog.campana_id.in_(filters['campana_ids'])
            )
        elif filters.get('campana_id'):
            query = query.filter(
                LlamadaLog.campana_id == filters['campana_id']
            )
        if filters.get('agente_ids'):
            query = query.filter(
                LlamadaLog.agente_id.in_(filters['agente_ids'])
            )
        elif filters.get('agente_id'):
            query = query.filter(
                LlamadaLog.agente_id == filters['agente_id']
            )
        return query

    def _apply_gestion_filters_no_fecha(self, query, filters: Dict):
        """Aplica filtros de CustomFormGestion excepto fechas."""
        if filters.get('campana_ids'):
            query = query.filter(
                CustomFormGestion.campana_id.in_(filters['campana_ids'])
            )
        elif filters.get('campana_id'):
            query = query.filter(
                CustomFormGestion.campana_id == filters['campana_id']
            )
        if filters.get('agente_ids'):
            query = query.filter(
                CustomFormGestion.agent_id.in_(filters['agente_ids'])
            )
        elif filters.get('agente_id'):
            query = query.filter(
                CustomFormGestion.agent_id == filters['agente_id']
            )
        return query

    def _build_fecha_logica_sq(self, filters: Dict):
        """
        Subquery: mapea callid → fecha_logica (día del primer evento
        en TIMEZONE_DB). Retorna (callid, fecha_logica).

        Ventana expandida ±1 día contra LlamadaLog.time para capturar
        llamadas split-day; luego el HAVING restringe a fecha_logica
        dentro del rango solicitado.
        """
        fecha_ini = filters.get('fecha_inicio')
        fecha_fin = filters.get('fecha_fin')

        first_event = func.min(LlamadaLog.time)
        fecha_logica_expr = func.date(
            func.timezone(config.TIMEZONE_DB, first_event)
        )

        q = self.db.query(
            LlamadaLog.callid,
            fecha_logica_expr.label('fecha_logica'),
        ).filter(
            LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS),
        )

        if fecha_ini is not None:
            q = q.filter(
                LlamadaLog.time >= fecha_ini - timedelta(days=1)
            )
        if fecha_fin is not None:
            q = q.filter(
                LlamadaLog.time <= fecha_fin + timedelta(days=1)
            )

        q = self._apply_llamada_filters_no_fecha(q, filters)
        q = q.group_by(LlamadaLog.callid)

        if fecha_ini is not None:
            q = q.having(fecha_logica_expr >= fecha_ini.date())
        if fecha_fin is not None:
            q = q.having(fecha_logica_expr <= fecha_fin.date())

        return q.subquery()

    def _build_llamadas_atendidas_sq(self, filters: Dict):
        """
        Subquery: callids de llamadas ENTRANTES ATENDIDAS
        (último evento = ATENDIDA) en el rango de fechas.
        Retorna (callid, ultimo_id).

        USE_FECHA_LOGICA_LLAMADA=True → filtra por fecha lógica del
        callid (día del primer evento), no por LlamadaLog.time directo.
        """
        if not config.USE_FECHA_LOGICA_LLAMADA:
            sq = self.db.query(
                LlamadaLog.callid,
                func.max(LlamadaLog.id).label('ultimo_id'),
            ).filter(
                LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS),
                LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
            )
            sq = self._apply_llamada_filters(sq, filters)
            return sq.group_by(LlamadaLog.callid).subquery()

        fecha_logica_sq = self._build_fecha_logica_sq(filters)
        sq = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id'),
        ).join(
            fecha_logica_sq,
            LlamadaLog.callid == fecha_logica_sq.c.callid,
        ).filter(
            LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS),
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
        )
        sq = self._apply_llamada_filters_no_fecha(sq, filters)
        return sq.group_by(LlamadaLog.callid).subquery()

    def _build_gestion_unica_sq(self, filters: Dict):
        """
        Subquery: 1 gestión por call_id (MAX id = última registrada).
        Solo gestiones con call_id no vacío.
        Retorna (call_id, ultimo_gestion_id).

        USE_FECHA_LOGICA_LLAMADA=True → NO filtra por
        CustomFormGestion.fecha; en su lugar, restringe a call_ids
        cuya fecha_logica cae en el rango solicitado (vía JOIN a
        fecha_logica_sq). Así una gestión guardada después de
        medianoche queda en el día de la llamada, no de su registro.
        """
        if not config.USE_FECHA_LOGICA_LLAMADA:
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

        fecha_logica_sq = self._build_fecha_logica_sq(filters)
        sq = self.db.query(
            CustomFormGestion.call_id,
            func.max(CustomFormGestion.id).label(
                'ultimo_gestion_id'
            ),
            # fecha_logica es constante por callid, MAX() sirve
            # solo para permitir el GROUP BY sobre call_id.
            func.max(fecha_logica_sq.c.fecha_logica).label(
                'fecha_logica'
            ),
        ).join(
            fecha_logica_sq,
            CustomFormGestion.call_id == fecha_logica_sq.c.callid,
        ).filter(
            CustomFormGestion.call_id.isnot(None),
            CustomFormGestion.call_id != '',
        )
        sq = self._apply_gestion_filters_no_fecha(sq, filters)
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
        # Incluye llamada_id para resolver agente de la llamada
        gestiones_validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
            atendidas_sq.c.ultimo_id.label('llamada_id'),
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        # Contar gestiones válidas
        total = self.db.query(
            func.count(gestiones_validas_sq.c.ultimo_gestion_id)
        ).scalar() or 0

        # Agentes (de la llamada, no de la gestión) y campañas
        stats = self.db.query(
            func.count(
                func.distinct(LlamadaLog.agente_id)
            ).label('agentes'),
            func.count(
                func.distinct(CustomFormGestion.campana_id)
            ).label('campanas'),
        ).join(
            gestiones_validas_sq,
            CustomFormGestion.id
            == gestiones_validas_sq.c.ultimo_gestion_id,
        ).outerjoin(
            LlamadaLog,
            LlamadaLog.id
            == gestiones_validas_sq.c.llamada_id,
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
        """
        Gestiones agrupadas por agente de la LLAMADA
        (no de la gestión), para consistencia con llamadas
        atendidas por agente.
        """
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        # IDs de gestiones válidas + llamada_id
        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
            atendidas_sq.c.ultimo_id.label('llamada_id'),
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        # Agrupar por agente de la llamada (LlamadaLog.agente_id)
        query = self.db.query(
            LlamadaLog.agente_id,
            User.first_name,
            User.last_name,
            func.count(validas_sq.c.ultimo_gestion_id).label(
                'total_gestiones'
            ),
        ).join(
            validas_sq,
            LlamadaLog.id == validas_sq.c.llamada_id,
        ).outerjoin(
            AgenteProfile,
            LlamadaLog.agente_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        ).group_by(
            LlamadaLog.agente_id,
            User.first_name,
            User.last_name,
        ).order_by(
            func.count(validas_sq.c.ultimo_gestion_id).desc()
        ).all()

        return [
            {
                'agente_id': r.agente_id,
                'agente': (
                    f'{r.first_name or ""} '
                    f'{r.last_name or ""}'.strip()
                    or f'Agente {r.agente_id}'
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

        # Subquery: IDs de gestiones válidas + id del registro
        # de llamada atendida (para obtener hora y duración
        # con JOIN directo por PK, sin escanear toda la tabla)
        validas_sq = self.db.query(
            gestion_unica_sq.c.ultimo_gestion_id,
            gestion_unica_sq.c.call_id,
            atendidas_sq.c.ultimo_id.label('llamada_id'),
        ).join(
            atendidas_sq,
            gestion_unica_sq.c.call_id == atendidas_sq.c.callid,
        ).subquery()

        # Conteo rápido: solo cuenta gestiones válidas
        # (sin JOINs de lookup = rápido)
        total = self.db.query(
            func.count(validas_sq.c.ultimo_gestion_id)
        ).scalar() or 0

        # Query principal: solo gestiones válidas
        # Hora y duración vienen del registro de llamada atendida
        # (JOIN por PK = instantáneo, sin GROUP BY sobre toda
        # la tabla llamadalog)
        query = self.db.query(
            CustomFormGestion,
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido'),
            Campana.nombre.label('campana_nombre'),
            CustomFormIncidencias.descripcion.label(
                'incidencia_nombre'
            ),
            LlamadaLog.agente_id.label('ll_agente_id'),
            LlamadaLog.duracion_llamada.label(
                'duracion_llamada'
            ),
            LlamadaLog.time.label('hora_llamada'),
        ).join(
            validas_sq,
            CustomFormGestion.id
            == validas_sq.c.ultimo_gestion_id,
        ).outerjoin(
            LlamadaLog,
            LlamadaLog.id == validas_sq.c.llamada_id,
        ).outerjoin(
            AgenteProfile,
            LlamadaLog.agente_id == AgenteProfile.id,
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        ).outerjoin(
            Campana, CustomFormGestion.campana_id == Campana.id
        ).outerjoin(
            CustomFormIncidencias,
            CustomFormGestion.incidencia_id
            == CustomFormIncidencias.id,
        )

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
                    or f'Agente {r.ll_agente_id}'
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
        """Gestiones válidas agrupadas por día (timezone local).

        En modo USE_FECHA_LOGICA_LLAMADA=True agrupa por día de la
        llamada (fecha_logica); en modo off agrupa por
        CustomFormGestion.fecha como siempre.
        """
        filters = filters or {}

        atendidas_sq = self._build_llamadas_atendidas_sq(filters)
        gestion_unica_sq = self._build_gestion_unica_sq(filters)

        if config.USE_FECHA_LOGICA_LLAMADA:
            # gestion_unica_sq ya expone fecha_logica por call_id
            resultados = self.db.query(
                gestion_unica_sq.c.fecha_logica.label('dia'),
                func.count(
                    gestion_unica_sq.c.ultimo_gestion_id
                ).label('total'),
            ).join(
                atendidas_sq,
                gestion_unica_sq.c.call_id
                == atendidas_sq.c.callid,
            ).group_by(
                gestion_unica_sq.c.fecha_logica
            ).order_by(
                gestion_unica_sq.c.fecha_logica
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

        # Conteo rápido: solo cuenta llamadas sin gestión
        # (sin JOINs de lookup)
        total = self.db.query(
            func.count(atendidas_sq.c.callid)
        ).filter(
            ~atendidas_sq.c.callid.in_(
                self.db.query(gestion_unica_sq.c.call_id)
            )
        ).scalar() or 0

        # Query: llamadas sin gestión (con datos de lookup)
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

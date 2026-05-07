"""
Extensión del servicio de análisis de llamadas
Métodos adicionales para reportes premium
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import and_, case, distinct, extract, func, or_
from sqlalchemy.orm import Session

from ..config import config
from ..constants import (
    EVENTOS_ABANDONADAS,
    EVENTOS_ATENDIDAS,
    EVENTOS_FINALES,
    EVENTOS_NO_ATENDIDAS,
    EVENTOS_SALIENTES,
    EVENTOS_TRANSFERENCIAS,
    TIPO_ENTRANTE,
    TIPO_SALIENTE,
    TIPOS_LLAMADA_ACTIVOS,
)
from ..models.omnileads_models import (
    ActividadAgenteLog,
    AgenteProfile,
    Campana,
    LlamadaLog,
    Pausa,
    User,
)


class CallAnalyticsExtended:
    """Servicio extendido para reportes premium"""

    # Constantes importadas desde analytics.constants
    EVENTOS_ATENDIDAS = EVENTOS_ATENDIDAS
    EVENTOS_ABANDONADAS = EVENTOS_ABANDONADAS
    EVENTOS_NO_ATENDIDAS = EVENTOS_NO_ATENDIDAS
    EVENTOS_FINALES = EVENTOS_FINALES
    EVENTOS_SALIENTES = EVENTOS_SALIENTES
    EVENTOS_TRANSFERENCIAS = EVENTOS_TRANSFERENCIAS

    def __init__(self, db: Session):
        self.db = db
        self._tz_db = config.TIMEZONE_DB  # 'America/Bogota'

    def _local_time(self, column):
        """
        Extrae timestamp naive con la hora tal cual está en la BD.
        AT TIME ZONE con el TZ de la BD devuelve la hora numérica
        sin convertir zona.
        """
        return func.timezone(self._tz_db, column)

    def _build_last_event_subquery(self, filters: Dict = None):
        """
        Construye subquery para obtener solo el último evento de cada llamada.
        Usa MAX(id) como desempate cuando hay múltiples eventos con mismo timestamp.
        """
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('max_id')
        ).filter(
            LlamadaLog.event.in_(self.EVENTOS_FINALES),
            LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS),
        )

        if filters:
            # Filtros de fecha
            if filters.get('fecha_inicio'):
                subquery = subquery.filter(LlamadaLog.time >= filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                subquery = subquery.filter(LlamadaLog.time <= filters['fecha_fin'])

            # Filtros de campaña (individual o múltiple)
            if filters.get('campana_ids'):
                subquery = subquery.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
            elif filters.get('campana_id'):
                subquery = subquery.filter(LlamadaLog.campana_id == filters['campana_id'])

            # Filtros de agente (individual o múltiple)
            if filters.get('agente_ids'):
                subquery = subquery.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))
            elif filters.get('agente_id'):
                subquery = subquery.filter(LlamadaLog.agente_id == filters['agente_id'])

            # Filtro de tipo de llamada (TIPO_ENTRANTE=3, TIPO_SALIENTE=1)
            if filters.get('tipo_llamada'):
                if filters['tipo_llamada'] == 'entrantes':
                    subquery = subquery.filter(LlamadaLog.tipo_llamada == 3)
                elif filters['tipo_llamada'] == 'salientes':
                    subquery = subquery.filter(LlamadaLog.tipo_llamada == 1)

            # Filtro de tipo de campaña
            if filters.get('tipo_campana'):
                subquery = subquery.filter(LlamadaLog.tipo_campana == filters['tipo_campana'])

        return subquery.group_by(LlamadaLog.callid).subquery()

    def _apply_filters(self, query, filters: Dict):
        """Aplica filtros comunes a las consultas"""
        if not filters:
            return query

        # Filtros de fecha
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])

        # Filtros de campaña (individual o múltiple)
        if filters.get('campana_ids'):
            query = query.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        elif filters.get('campana_id'):
            query = query.filter(LlamadaLog.campana_id == filters['campana_id'])

        # Filtros de agente (individual o múltiple)
        if filters.get('agente_ids'):
            query = query.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))
        elif filters.get('agente_id'):
            query = query.filter(LlamadaLog.agente_id == filters['agente_id'])

        # Filtro de tipo de llamada (TIPO_ENTRANTE=3, TIPO_SALIENTE=1)
        if filters.get('tipo_llamada'):
            if filters['tipo_llamada'] == 'entrantes':
                query = query.filter(LlamadaLog.tipo_llamada == 3)
            elif filters['tipo_llamada'] == 'salientes':
                query = query.filter(LlamadaLog.tipo_llamada == 1)

        # Filtro de tipo de campaña
        if filters.get('tipo_campana'):
            query = query.filter(LlamadaLog.tipo_campana == filters['tipo_campana'])

        return query

    # ==================== DISTRIBUCIÓN AVANZADA ====================

    def get_distribucion_por_campana(self, filters: Dict = None) -> List[Dict]:
        """
        Distribución de llamadas por campaña (Pie Chart)
        Retorna nombre, total y porcentaje por campaña
        """
        filters = filters or {}

        # Obtener solo el último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        query = self.db.query(
            Campana.nombre,
            func.count(distinct(LlamadaLog.callid)).label('total')
        ).join(
            LlamadaLog, Campana.id == LlamadaLog.campana_id
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        resultados = query.group_by(Campana.nombre).all()

        # Calcular total general
        total_general = sum(r.total for r in resultados)

        return [{
            'campana': r.nombre,
            'total': r.total,
            'porcentaje': round(r.total / total_general * 100, 2) if total_general > 0 else 0
        } for r in resultados]

    def get_distribucion_por_dia_semana(self, filters: Dict = None) -> List[Dict]:
        """
        Distribución de llamadas por día de la semana
        0=Domingo, 6=Sábado
        """
        filters = filters or {}

        # Obtener solo el último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        local_time = self._local_time(LlamadaLog.time)
        query = self.db.query(
            extract('dow', local_time).label('dia_semana'),
            func.count(distinct(LlamadaLog.callid)).label('total')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        resultados = query.group_by('dia_semana').all()

        dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

        # Crear array con todos los días inicializados en 0
        distribucion = {i: 0 for i in range(7)}
        for r in resultados:
            distribucion[int(r.dia_semana)] = r.total

        # Calcular promedio
        total_llamadas = sum(distribucion.values())
        promedio = total_llamadas / 7 if total_llamadas > 0 else 0

        return [{
            'dia': dias[i],
            'total': distribucion[i],
            'promedio': round(promedio, 2),
            'es_pico': distribucion[i] > promedio
        } for i in range(7)]

    def get_distribucion_por_mes(self, anio: int = None, filters: Dict = None) -> List[Dict]:
        """
        Distribución de llamadas por mes
        """
        filters = filters or {}

        # Obtener solo el último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        local_time = self._local_time(LlamadaLog.time)
        query = self.db.query(
            extract('month', local_time).label('mes'),
            func.count(distinct(LlamadaLog.callid)).label('total')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        if anio:
            query = query.filter(extract('year', local_time) == anio)

        resultados = query.group_by('mes').all()

        meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

        # Crear array con todos los meses inicializados en 0
        distribucion = {i: 0 for i in range(1, 13)}
        for r in resultados:
            distribucion[int(r.mes)] = r.total

        return [{
            'mes': meses[i-1],
            'mes_numero': i,
            'total': distribucion[i]
        } for i in range(1, 13)]

    def get_distribucion_por_rango_horario(self, filters: Dict = None) -> List[Dict]:
        """
        Distribución por rangos horarios configurables
        Rangos: 0-6, 6-12, 12-18, 18-24
        """
        filters = filters or {}

        # Obtener solo el último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        local_time = self._local_time(LlamadaLog.time)
        query = self.db.query(
            extract('hour', local_time).label('hora'),
            func.count(distinct(LlamadaLog.callid)).label('total')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        resultados = query.group_by('hora').all()

        # Definir rangos horarios
        rangos = {
            '00:00 - 06:00': (0, 6),
            '06:00 - 12:00': (6, 12),
            '12:00 - 18:00': (12, 18),
            '18:00 - 24:00': (18, 24)
        }

        distribucion_rangos = {rango: 0 for rango in rangos}

        for r in resultados:
            hora = int(r.hora)
            for nombre_rango, (inicio, fin) in rangos.items():
                if inicio <= hora < fin:
                    distribucion_rangos[nombre_rango] += r.total

        total = sum(distribucion_rangos.values())

        return [{
            'rango': nombre,
            'total': total_llamadas,
            'porcentaje': round(total_llamadas / total * 100, 2) if total > 0 else 0
        } for nombre, total_llamadas in distribucion_rangos.items()]

    # ==================== LLAMADAS SALIENTES ====================

    def get_llamadas_salientes_dashboard(self, filters: Dict = None) -> Dict:
        """
        Dashboard completo de llamadas salientes
        Categorías basadas en el evento final de cada llamada única
        """
        filters = filters or {}

        # Subquery para obtener el último evento de cada llamada (por callid)
        # Usa MAX(id) como desempate para eventos con mismo timestamp
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.tipo_llamada == 1  # Salientes = 1
        )

        # Aplicar todos los filtros (fecha, campaña, agente)
        subquery = self._apply_filters(subquery, filters)

        subquery = subquery.group_by(LlamadaLog.callid).subquery()

        # Query principal: unir para obtener el evento final de cada llamada
        # Excluir NONDIALPLAN y CONGESTION (no son llamadas reales)
        query = self.db.query(LlamadaLog).join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.id == subquery.c.ultimo_id
            )
        ).filter(
            ~LlamadaLog.event.in_(['NONDIALPLAN', 'CONGESTION'])
        )

        # Contar llamadas únicas por categoría basada en evento final
        total_llamadas = query.count()

        # Exitosas: las que terminaron con COMPLETE (fueron contestadas y terminaron)
        contestadas = query.filter(
            LlamadaLog.event.in_(['COMPLETEAGENT', 'COMPLETEOUTNUM'])
        ).count()

        # No contestadas/Canceladas: terminaron con CANCEL o NOANSWER
        no_contestadas = query.filter(
            LlamadaLog.event.in_(['NOANSWER', 'CANCEL'])
        ).count()

        # Ocupadas
        ocupadas = query.filter(LlamadaLog.event == 'BUSY').count()

        # Fallos técnicos
        fallos = query.filter(
            LlamadaLog.event == 'CHANUNAVAIL'
        ).count()

        # Transferencias y otros (nombres correctos de OmniLeads)
        otros = query.filter(
            LlamadaLog.event.in_([
                'BTOUT-TRY', 'CAMPT-COMPLETE', 'CAMPT-TRY',
                'CTOUT-TRY', 'ANSWER', 'DIAL'
            ])
        ).count()

        # Calcular tasa de contactación
        tasa_contactacion = round(
            contestadas / total_llamadas * 100, 2
        ) if total_llamadas > 0 else 0

        # Preparar eventos para el gráfico
        eventos = {
            'CONTESTADAS': {
                'descripcion': 'Llamadas Contestadas',
                'total': contestadas
            },
            'NO_CONTESTADAS': {
                'descripcion': 'No Contestadas',
                'total': no_contestadas
            },
            'OCUPADO': {
                'descripcion': 'Línea Ocupada',
                'total': ocupadas
            },
            'FALLOS': {
                'descripcion': 'Fallos Técnicos',
                'total': fallos
            },
            'OTROS': {
                'descripcion': 'Transferencias/Otros',
                'total': otros
            }
        }

        return {
            'eventos': eventos,
            'metricas': {
                'total_marcadas': total_llamadas,
                'total_contestadas': contestadas,
                'total_no_contestadas': no_contestadas,
                'total_ocupadas': ocupadas,
                'total_fallos': fallos,
                'tasa_contactacion': tasa_contactacion
            }
        }

    def get_llamadas_salientes_detalle(
        self, filters: Dict = None, page: int = 1,
        per_page: int = 50, sort_by: str = None,
        sort_dir: str = 'desc'
    ) -> Dict:
        """
        Detalle paginado de llamadas salientes con último evento por callid.
        Mismo patrón que get_llamadas_detalladas de CallAnalyticsService.
        Excluye NONDIALPLAN y CONGESTION (EVENTOS_EXCLUIDOS).
        """
        page = max(1, page)
        per_page = max(1, min(per_page, 200))
        filters = filters or {}

        # Subquery: último evento de cada llamada saliente
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.tipo_llamada == 1  # Solo salientes
        )

        # Aplicar filtros de fecha y campaña/agente
        subquery = self._apply_filters(subquery, filters)
        subquery = subquery.group_by(LlamadaLog.callid).subquery()

        # Query principal: JOIN con subquery para obtener evento final
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido')
        ).join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.id == subquery.c.ultimo_id
            )
        ).filter(
            # Excluir NONDIALPLAN, CONGESTION (no son llamadas reales)
            ~LlamadaLog.event.in_(['NONDIALPLAN', 'CONGESTION'])
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )

        # Total de registros
        total = query.count()

        # Ordenamiento server-side
        sort_map = {
            'fecha': LlamadaLog.time,
            'hora': LlamadaLog.time,
            'duracion': LlamadaLog.duracion_llamada,
            'espera': LlamadaLog.bridge_wait_time,
            'callid': LlamadaLog.callid,
            'numero': LlamadaLog.numero_marcado,
            'resultado': LlamadaLog.event,
            'campana': Campana.nombre,
            'agente': User.first_name,
        }
        sort_column = sort_map.get(sort_by, LlamadaLog.time)
        if sort_dir == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        # Paginación
        offset = (page - 1) * per_page
        resultados = query.offset(offset).limit(per_page).all()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Determinar resultado de la llamada
            evento = llamada.event
            if evento in ('COMPLETEAGENT', 'COMPLETEOUTNUM'):
                resultado = 'Contestada'
            elif evento in ('NOANSWER', 'CANCEL'):
                resultado = 'No contestada'
            elif evento == 'BUSY':
                resultado = 'Ocupado'
            elif evento == 'CHANUNAVAIL':
                resultado = 'Canal no disponible'
            elif evento == 'DIAL':
                resultado = 'Solo marcación'
            elif evento == 'ANSWER':
                resultado = 'Contestada (sin cierre)'
            else:
                resultado = evento

            # Quién colgó (solo para contestadas)
            quien_colgo = ''
            if evento == 'COMPLETEAGENT':
                quien_colgo = 'Agente'
            elif evento == 'COMPLETEOUTNUM':
                quien_colgo = 'Cliente'

            nombre_agente = (
                f'{r.agente_nombre or ""} {r.agente_apellido or ""}'.strip()
                or f'Agente {llamada.agente_id}'
            )

            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': llamada.time.strftime('%Y-%m-%d'),
                'hora': llamada.time.strftime('%H:%M:%S'),
                'campana': r.campana_nombre or f'Campaña {llamada.campana_id}',
                'agente': nombre_agente,
                'numero': llamada.numero_marcado or '-',
                'duracion': llamada.duracion_llamada or 0,
                'espera': llamada.bridge_wait_time or 0,
                'evento': evento,
                'resultado': resultado,
                'quien_colgo': quien_colgo,
            })

        return {
            'data': llamadas,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

    def get_llamadas_manuales_vs_dialer(self, filters: Dict = None) -> Dict:
        """
        Comparativa de llamadas manuales vs dialer
        Basado en tipo_campana: 1 = Manual, 3 = Dialer (según ejemplos)
        """
        filters = filters or {}

        query = self.db.query(LlamadaLog)
        query = query.filter(LlamadaLog.tipo_llamada == 1)  # Salientes = 1
        query = self._apply_filters(query, filters)

        # Contar por tipo_campana
        # tipo_campana: 1 = Manual, 3 = Dialer (basado en ejemplos reales)
        manuales = query.filter(LlamadaLog.tipo_campana == 1).count()
        dialer = query.filter(LlamadaLog.tipo_campana == 3).count()

        total = manuales + dialer

        return {
            'manuales': {
                'total': manuales,
                'porcentaje': round(manuales / total * 100, 2) if total > 0 else 0
            },
            'dialer': {
                'total': dialer,
                'porcentaje': round(dialer / total * 100, 2) if total > 0 else 0
            }
        }

    # ==================== CAUSAS DETALLADAS ====================

    def get_causas_desconexion_detalladas(self, filters: Dict = None) -> List[Dict]:
        """
        Análisis detallado de causas de desconexión
        Incluye eventos de transferencias
        """
        filters = filters or {}

        eventos_desconexion = [
            'COMPLETEAGENT',
            'COMPLETEOUTNUM',
            'COMPLETE-CTOUT',
            'COMPLETE-BTOUT'
        ]

        query = self.db.query(
            LlamadaLog.event,
            func.count(LlamadaLog.id).label('total')
        ).filter(
            LlamadaLog.event.in_(eventos_desconexion)
        )

        query = self._apply_filters(query, filters)

        resultados = query.group_by(LlamadaLog.event).all()

        total = sum(r.total for r in resultados)

        descripciones = {
            'COMPLETEAGENT': 'Agente colgó',
            'COMPLETEOUTNUM': 'Cliente colgó',
            'COMPLETE-CTOUT': 'Transfer consultivo',
            'COMPLETE-BTOUT': 'Transfer ciego'
        }

        return [{
            'evento': r.event,
            'descripcion': descripciones.get(r.event, r.event),
            'total': r.total,
            'porcentaje': round(r.total / total * 100, 2) if total > 0 else 0
        } for r in resultados]

    def get_causas_no_conexion_completas(self, filters: Dict = None) -> List[Dict]:
        """
        Análisis completo de causas de no conexión
        Incluye todos los eventos: ABANDON, EXITWITHTIMEOUT, CONGESTION, etc.
        """
        filters = filters or {}

        # NONDIALPLAN y CONGESTION excluidos: no son llamadas reales
        eventos_no_conexion = [
            'ABANDON',
            'ABANDONWEL',
            'ABANDON-CTOUT',
            'EXITWITHTIMEOUT',
            'CHANUNAVAIL',
            'NOANSWER',
            'CANCEL'
        ]

        query = self.db.query(
            LlamadaLog.event,
            func.count(LlamadaLog.id).label('total')
        ).filter(
            LlamadaLog.event.in_(eventos_no_conexion)
        )

        query = self._apply_filters(query, filters)

        resultados = query.group_by(LlamadaLog.event).all()

        total = sum(r.total for r in resultados)

        descripciones = {
            'ABANDON': 'Abandono en cola',
            'ABANDONWEL': 'Abandono en bienvenida',
            'ABANDON-CTOUT': 'Abandono en transfer',
            'EXITWITHTIMEOUT': 'Timeout',
            'CHANUNAVAIL': 'Canal no disponible',
            'NOANSWER': 'No contestada',
            'CANCEL': 'Cancelada'
        }

        return [{
            'evento': r.event,
            'descripcion': descripciones.get(r.event, r.event),
            'total': r.total,
            'porcentaje': round(r.total / total * 100, 2) if total > 0 else 0
        } for r in resultados]

    def get_sin_conexion_por_agente(self, filters: Dict = None) -> List[Dict]:
        """
        Llamadas sin conexión desglosadas por agente
        """
        filters = filters or {}

        eventos_sin_conexion = [
            'ABANDON', 'ABANDONWEL', 'EXITWITHTIMEOUT',
            'NOANSWER', 'CANCEL', 'CHANUNAVAIL'
        ]

        query = self.db.query(
            User.first_name,
            User.last_name,
            User.email,
            func.count(LlamadaLog.id).label('total')
        ).join(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).join(
            User, AgenteProfile.user_id == User.id
        ).filter(
            LlamadaLog.event.in_(eventos_sin_conexion)
        )

        query = self._apply_filters(query, filters)

        resultados = query.group_by(
            User.first_name, User.last_name, User.email
        ).all()

        total_general = sum(r.total for r in resultados)

        return [{
            'agente': f'{r.first_name} {r.last_name}',
            'email': r.email,
            'total': r.total,
            'porcentaje': round(r.total / total_general * 100, 2) if total_general > 0 else 0
        } for r in resultados]

    def get_sin_conexion_por_campana(self, filters: Dict = None) -> List[Dict]:
        """
        Llamadas sin conexión desglosadas por campaña
        """
        filters = filters or {}

        eventos_sin_conexion = [
            'ABANDON', 'ABANDONWEL', 'EXITWITHTIMEOUT',
            'NOANSWER', 'CANCEL', 'CHANUNAVAIL'
        ]

        query = self.db.query(
            Campana.nombre,
            func.count(LlamadaLog.id).label('total')
        ).join(
            LlamadaLog, Campana.id == LlamadaLog.campana_id
        ).filter(
            LlamadaLog.event.in_(eventos_sin_conexion)
        )

        query = self._apply_filters(query, filters)

        resultados = query.group_by(Campana.nombre).all()

        total_general = sum(r.total for r in resultados)

        return [{
            'campana': r.nombre,
            'total': r.total,
            'porcentaje': round(r.total / total_general * 100, 2) if total_general > 0 else 0
        } for r in resultados]

    # ==================== AGENTES AVANZADOS ====================

    def get_total_sesiones_agentes(self, filters: Dict = None) -> Dict:
        """
        Resumen de sesiones de todos los agentes
        Métricas globales: N° agentes, número total de actividades
        """
        filters = filters or {}

        query = self.db.query(
            ActividadAgenteLog.agente_id,
            func.count(ActividadAgenteLog.id).label('num_actividades')
        )

        # Aplicar filtros de fecha si existen
        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        resultados = query.group_by(ActividadAgenteLog.agente_id).all()

        if not resultados:
            return {
                'total_agentes': 0,
                'actividades_promedio': 0,
                'actividades_minimas': 0,
                'actividades_maximas': 0,
                'actividades_total': 0
            }

        actividades = [r.num_actividades for r in resultados if r.num_actividades]

        return {
            'total_agentes': len(resultados),
            'actividades_promedio': round(sum(actividades) / len(actividades) if actividades else 0, 2),
            'actividades_minimas': min(actividades) if actividades else 0,
            'actividades_maximas': max(actividades) if actividades else 0,
            'actividades_total': sum(actividades) if actividades else 0
        }

    def get_agentes_por_dia_hora(self, filters: Dict = None) -> List[Dict]:
        """
        Número de agentes disponibles por día y hora (para heatmap)
        Retorna matriz día x hora con cantidad de agentes
        """
        filters = filters or {}

        local_time_act = self._local_time(ActividadAgenteLog.time)
        query = self.db.query(
            extract('dow', local_time_act).label('dia'),
            extract('hour', local_time_act).label('hora'),
            func.count(distinct(ActividadAgenteLog.agente_id)).label('num_agentes')
        )

        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        # Filtrar por agente si se especifica
        if filters.get('agente_ids'):
            query = query.filter(
                ActividadAgenteLog.agente_id.in_(filters['agente_ids'])
            )
        elif filters.get('agente_id'):
            query = query.filter(
                ActividadAgenteLog.agente_id == filters['agente_id']
            )

        resultados = query.group_by('dia', 'hora').all()

        # Crear matriz 7 días x 24 horas
        matriz = [[0 for _ in range(24)] for _ in range(7)]

        for r in resultados:
            dia = int(r.dia)
            hora = int(r.hora)
            matriz[dia][hora] = r.num_agentes

        dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado']

        return {
            'dias': dias,
            'horas': list(range(24)),
            'matriz': matriz
        }

    def get_disponibilidad_agentes_ampliada(self, filters: Dict = None) -> List[Dict]:
        """
        Disponibilidad de agentes con métricas ampliadas
        Basado en actividades y llamadas registradas
        """
        filters = filters or {}

        # Query de llamadas por agente
        query = self.db.query(
            AgenteProfile.id,
            User.first_name,
            User.last_name,
            func.count(LlamadaLog.id).label('num_llamadas'),
            func.sum(LlamadaLog.duracion_llamada).label('tiempo_llamadas')
        ).join(
            LlamadaLog, AgenteProfile.id == LlamadaLog.agente_id
        ).join(
            User, AgenteProfile.user_id == User.id
        )

        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])

        resultados = query.group_by(
            AgenteProfile.id, User.first_name, User.last_name
        ).all()

        # Preparar métricas
        agentes_metricas = []

        for r in resultados:
            # Contar actividades
            actividades_query = self.db.query(
                func.count(ActividadAgenteLog.id).label('num_actividades')
            ).filter(
                ActividadAgenteLog.agente_id == r.id
            )

            if filters.get('fecha_inicio'):
                actividades_query = actividades_query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                actividades_query = actividades_query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

            num_actividades = actividades_query.scalar() or 0
            tiempo_promedio = round(r.tiempo_llamadas / r.num_llamadas, 2) if r.num_llamadas > 0 else 0

            agentes_metricas.append({
                'agente': f'{r.first_name} {r.last_name}',
                'num_sesiones': num_actividades,
                'tiempo_sesion': r.tiempo_llamadas,
                'tiempo_llamadas': r.tiempo_llamadas,
                'ocupacion': 100,  # 100% si está procesando llamadas
                'promedio_sesion': tiempo_promedio
            })

        return agentes_metricas

    # ==================== TRANSFERENCIAS ====================

    def get_analisis_transferencias(self, filters: Dict = None) -> Dict:
        """
        Análisis completo de transferencias.
        OPTIMIZADO: Consolidación de 10+ queries en 2 queries con agregaciones condicionales.
        Cuenta LLAMADAS ÚNICAS (por callid), no eventos individuales.
        Excluye llamadas que SOLO tienen ENTERQUEUE-TRANSFER.
        """
        filters = filters or {}
        from sqlalchemy import case

        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)

        # ========================================================================
        # OPTIMIZACIÓN 1: Consolidar conteo de eventos en single query
        # ========================================================================
        # ANTES: Loop con .count() por cada evento (10+ queries)
        # AHORA: 1 query con agregaciones condicionales
        eventos_counts = {}
        for evento in self.EVENTOS_TRANSFERENCIAS.keys():
            eventos_counts[evento] = func.sum(case((LlamadaLog.event == evento, 1), else_=0))

        eventos_result = query.with_entities(*eventos_counts.values()).first()

        metricas_eventos = {}
        for i, (evento, descripcion) in enumerate(self.EVENTOS_TRANSFERENCIAS.items()):
            metricas_eventos[evento] = {
                'descripcion': descripcion,
                'total': eventos_result[i] if eventos_result else 0
            }

        # ========================================================================
        # OPTIMIZACIÓN 2: Consolidar conteos de callids únicos en single query
        # ========================================================================
        # ANTES: 10 llamadas a count_unique_calls_with_event() (10 queries)
        # AHORA: 1 query con múltiples count(distinct(case(...)))

        base_query = self.db.query(LlamadaLog)
        base_query = self._apply_filters(base_query, filters)

        unique_counts = base_query.with_entities(
            # Transfer Ciego (BTOUT)
            func.count(func.distinct(case((LlamadaLog.event == 'BTOUT-TRY', LlamadaLog.callid)))).label('bt_intentos'),
            func.count(func.distinct(case((LlamadaLog.event == 'COMPLETE-BTOUT', LlamadaLog.callid)))).label('bt_completados'),
            func.count(func.distinct(case((LlamadaLog.event == 'BTOUT-ANSWER', LlamadaLog.callid)))).label('bt_atendidos'),
            func.count(func.distinct(case((LlamadaLog.event == 'BTOUT-CONGESTION', LlamadaLog.callid)))).label('bt_fallidos'),
            func.count(func.distinct(case((LlamadaLog.event == 'BTOUT-NONDIALPLAN', LlamadaLog.callid)))).label('bt_sin_ruta'),
            # Transfer Consultivo (CTOUT)
            func.count(func.distinct(case((LlamadaLog.event == 'CTOUT-TRY', LlamadaLog.callid)))).label('ct_intentos'),
            func.count(func.distinct(case((LlamadaLog.event == 'COMPLETE-CTOUT', LlamadaLog.callid)))).label('ct_completados'),
            func.count(func.distinct(case((LlamadaLog.event == 'CTOUT-ANSWER', LlamadaLog.callid)))).label('ct_atendidos'),
            func.count(func.distinct(case((LlamadaLog.event == 'CTOUT-DISCARD', LlamadaLog.callid)))).label('ct_descartados'),
            func.count(func.distinct(case((LlamadaLog.event == 'CTOUT-NONDIALPLAN', LlamadaLog.callid)))).label('ct_sin_ruta'),
            # Transfer Campaña (CAMPT)
            func.count(func.distinct(case((LlamadaLog.event == 'CAMPT-TRY', LlamadaLog.callid)))).label('campt_intentos'),
            func.count(func.distinct(case((LlamadaLog.event.in_(['CAMPT-COMPLETE', 'COMPLETE-CAMPT']), LlamadaLog.callid)))).label('campt_completados'),
        ).first()

        # Extraer resultados
        bt_intentos = unique_counts.bt_intentos or 0
        bt_completados = unique_counts.bt_completados or 0
        bt_atendidos = unique_counts.bt_atendidos or 0
        bt_fallidos = unique_counts.bt_fallidos or 0
        bt_sin_ruta = unique_counts.bt_sin_ruta or 0

        ct_intentos = unique_counts.ct_intentos or 0
        ct_completados = unique_counts.ct_completados or 0
        ct_atendidos = unique_counts.ct_atendidos or 0
        ct_descartados = unique_counts.ct_descartados or 0
        ct_sin_ruta = unique_counts.ct_sin_ruta or 0

        campt_intentos = unique_counts.campt_intentos or 0
        campt_completados = unique_counts.campt_completados or 0

        # Total de transferencias exitosas y intentos
        total_exitosas = bt_completados + ct_completados + campt_completados
        total_intentos = bt_intentos + ct_intentos + campt_intentos

        # Ingresos a cola por transferencia - CONTAR LLAMADAS ÚNICAS, no eventos
        # Obtener todos los callids que tienen ENTERQUEUE-TRANSFER
        callids_con_enterqueue = self.db.query(LlamadaLog.callid.distinct()).filter(
            LlamadaLog.event == 'ENTERQUEUE-TRANSFER'
        )
        callids_con_enterqueue = self._apply_filters(callids_con_enterqueue, filters)
        total_ingresos_cola = callids_con_enterqueue.count()

        # Calcular llamadas que SOLO tienen ENTERQUEUE-TRANSFER (para restar del total)
        # Estas son las que excluimos del detalle
        eventos_transferencia = list(self.EVENTOS_TRANSFERENCIAS.keys())

        # Obtener todos los callids con eventos de transferencia
        query_todos = self.db.query(
            LlamadaLog.callid,
            LlamadaLog.event
        ).filter(
            LlamadaLog.event.in_(eventos_transferencia)
        )
        query_todos = self._apply_filters(query_todos, filters)

        # Agrupar por callid y contar eventos
        llamadas_por_callid = {}
        for record in query_todos.all():
            if record.callid not in llamadas_por_callid:
                llamadas_por_callid[record.callid] = []
            llamadas_por_callid[record.callid].append(record.event)

        # Contar cuántas llamadas SOLO tienen ENTERQUEUE-TRANSFER
        llamadas_solo_enterqueue = sum(
            1 for eventos in llamadas_por_callid.values()
            if len(eventos) == 1 and eventos[0] == 'ENTERQUEUE-TRANSFER'
        )

        return {
            'eventos': metricas_eventos,  # Detalle de eventos individuales
            'resumen': {
                'transfer_ciego': {
                    'intentos': bt_intentos,
                    'atendidos': bt_atendidos,
                    'completados': bt_completados,
                    'fallidos': bt_fallidos,
                    'sin_ruta': bt_sin_ruta,
                    'tasa_exito': round(bt_completados / bt_intentos * 100, 2) if bt_intentos > 0 else 0
                },
                'transfer_consultivo': {
                    'intentos': ct_intentos,
                    'atendidos': ct_atendidos,
                    'completados': ct_completados,
                    'descartados': ct_descartados,
                    'sin_ruta': ct_sin_ruta,
                    'tasa_exito': round(ct_completados / ct_intentos * 100, 2) if ct_intentos > 0 else 0
                },
                'transfer_campana': {
                    'intentos': campt_intentos,
                    'completados': campt_completados,
                    'tasa_exito': round(campt_completados / campt_intentos * 100, 2) if campt_intentos > 0 else 0
                },
                'totales': {
                    'total_intentos': total_intentos,
                    'total_exitosas': total_exitosas,
                    'ingresos_cola': total_ingresos_cola,  # Llamadas únicas con ENTERQUEUE-TRANSFER
                    'solo_ingresos_cola': llamadas_solo_enterqueue,  # Llamadas que SOLO tienen este evento
                    'tasa_exito_global': round(total_exitosas / total_intentos * 100, 2) if total_intentos > 0 else 0
                }
            }
        }

    # ==================== NIVEL DE SERVICIO ====================

    def get_nivel_servicio_detallado(self, filters: Dict = None) -> List[Dict]:
        """
        Nivel de servicio con bloques configurables
        Bloques: 0-10s, 11-20s, 21-30s, 31-60s, 61-120s, >120s
        """
        filters = filters or {}

        # Obtener todas las llamadas atendidas con tiempo de espera
        query = self.db.query(LlamadaLog).filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        )

        query = self._apply_filters(query, filters)

        llamadas = query.all()

        # Definir bloques
        bloques = [
            (0, 10, '0-10 seg'),
            (11, 20, '11-20 seg'),
            (21, 30, '21-30 seg'),
            (31, 60, '31-60 seg'),
            (61, 120, '61-120 seg'),
            (121, float('inf'), '>120 seg')
        ]

        distribucion = {bloque[2]: 0 for bloque in bloques}

        for llamada in llamadas:
            tiempo_espera = llamada.bridge_wait_time or 0
            for minimo, maximo, etiqueta in bloques:
                if minimo <= tiempo_espera <= maximo:
                    distribucion[etiqueta] += 1
                    break

        total = len(llamadas)
        acumulado = 0

        resultado = []
        for minimo, maximo, etiqueta in bloques:
            cantidad = distribucion[etiqueta]
            acumulado += cantidad
            resultado.append({
                'rango': etiqueta,
                'cantidad': cantidad,
                'porcentaje': round(cantidad / total * 100, 2) if total > 0 else 0,
                'acumulado': acumulado,
                'porcentaje_acumulado': round(acumulado / total * 100, 2) if total > 0 else 0
            })

        return resultado

    # ==================== DISTRIBUCIÓN HORARIA DETALLADA ====================

    def get_distribucion_horaria_detallada(self, filters: Dict = None, agrupar_por: str = 'hora') -> List[Dict]:
        """
        Distribución horaria detallada SOLO para llamadas ENTRANTES con múltiples métricas

        Args:
            filters: Filtros estándar (fecha_inicio, fecha_fin, campana_ids, agente_ids)
            agrupar_por: 'hora', 'semana', 'mes', 'campana'

        Returns:
            Lista de diccionarios con métricas detalladas por grupo
        """
        filters = filters or {}

        # Usar listas unificadas de la clase
        eventos_atendidas = self.EVENTOS_ATENDIDAS
        eventos_abandonadas = self.EVENTOS_ABANDONADAS
        eventos_no_atendidas = self.EVENTOS_NO_ATENDIDAS

        # Usar el método centralizado que ya aplica TODOS los filtros correctamente
        last_events_subq = self._build_last_event_subquery(filters)

        # Query principal uniendo con última ocurrencia
        base_query = self.db.query(LlamadaLog).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        # Determinar campo de agrupación (timezone local)
        local_time = self._local_time(LlamadaLog.time)
        if agrupar_por == 'hora':
            group_field = extract('hour', local_time)
            group_label = 'hora'
        elif agrupar_por == 'dia':
            # Día completo (fecha en timezone local)
            group_field = func.date(local_time)
            group_label = 'dia'
        elif agrupar_por == 'semana':
            # Semana del mes (1-5)
            group_field = func.ceil(extract('day', local_time) / 7.0)
            group_label = 'semana'
        elif agrupar_por == 'mes':
            group_field = extract('month', local_time)
            group_label = 'mes'
        elif agrupar_por == 'campana':
            # Para campaña necesitamos join
            base_query = base_query.join(Campana, LlamadaLog.campana_id == Campana.id)
            group_field = Campana.nombre
            group_label = 'campana'
        else:
            group_field = extract('hour', local_time)
            group_label = 'hora'

        # Consulta agregada usando el join con last_events_subq que ya tiene todos los filtros
        query = self.db.query(
            group_field.label('grupo'),
            func.count(distinct(LlamadaLog.callid)).label('total_llamadas'),
            func.sum(case((LlamadaLog.event.in_(eventos_atendidas), 1), else_=0)).label('atendidas'),
            func.sum(case((LlamadaLog.event.in_(eventos_abandonadas), 1), else_=0)).label('abandonadas'),
            func.sum(case((LlamadaLog.event.in_(eventos_no_atendidas), 1), else_=0)).label('no_atendidas'),
            func.avg(case((LlamadaLog.event.in_(eventos_atendidas), LlamadaLog.bridge_wait_time), else_=None)).label('tiempo_espera_promedio'),
            func.avg(case((LlamadaLog.event.in_(eventos_abandonadas), LlamadaLog.bridge_wait_time), else_=None)).label('tiempo_abandono_promedio'),
            func.avg(case((LlamadaLog.event.in_(eventos_atendidas), LlamadaLog.duracion_llamada), else_=None)).label('duracion_promedio')
        ).select_from(LlamadaLog).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.max_id
            )
        )

        # Aplicar join adicional si es por campaña
        if agrupar_por == 'campana':
            query = query.join(Campana, LlamadaLog.campana_id == Campana.id)

        query = query.group_by(group_field)

        resultados = query.all()

        # Formatear resultados
        datos = []
        for r in resultados:
            grupo_valor = r.grupo

            # Formatear etiqueta según el tipo de agrupación
            if agrupar_por == 'hora':
                hora_inicio = int(grupo_valor)
                hora_fin = (hora_inicio + 1) % 24
                label = f"{hora_inicio:02d}:00 - {hora_fin:02d}:00"
            elif agrupar_por == 'dia':
                # Formatear fecha como DD/MM/YYYY
                if hasattr(grupo_valor, 'strftime'):
                    label = grupo_valor.strftime('%d/%m/%Y')
                else:
                    label = str(grupo_valor)
            elif agrupar_por == 'semana':
                label = f"Semana {int(grupo_valor)}"
            elif agrupar_por == 'mes':
                meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                         'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
                label = meses[int(grupo_valor) - 1] if 1 <= int(grupo_valor) <= 12 else str(grupo_valor)
            else:  # campaña
                label = str(grupo_valor)

            total = r.total_llamadas or 0
            atendidas = r.atendidas or 0
            abandonadas = r.abandonadas or 0
            no_atendidas = r.no_atendidas or 0

            datos.append({
                'grupo': label,
                'total_llamadas': total,
                'atendidas': atendidas,
                'abandonadas': abandonadas,
                'no_atendidas': no_atendidas,
                'porcentaje_atendidas': round((atendidas / total * 100), 2) if total > 0 else 0,
                'porcentaje_abandonadas': round((abandonadas / total * 100), 2) if total > 0 else 0,
                'porcentaje_no_atendidas': round((no_atendidas / total * 100), 2) if total > 0 else 0,
                'tiempo_espera_promedio': round(r.tiempo_espera_promedio or 0, 2),
                'tiempo_abandono_promedio': round(r.tiempo_abandono_promedio or 0, 2),
                'duracion_promedio': round(r.duracion_promedio or 0, 2)
            })

        # Ordenar según tipo de agrupación
        if agrupar_por == 'hora':
            # Crear lista completa de 24 horas (0-23)
            datos_dict = {d['grupo']: d for d in datos}
            datos_completos = []
            for hora in range(24):
                hora_inicio = hora
                hora_fin = (hora + 1) % 24
                label = f"{hora_inicio:02d}:00 - {hora_fin:02d}:00"

                if label in datos_dict:
                    datos_completos.append(datos_dict[label])
                else:
                    # Agregar hora sin datos
                    datos_completos.append({
                        'grupo': label,
                        'total_llamadas': 0,
                        'atendidas': 0,
                        'abandonadas': 0,
                        'no_atendidas': 0,
                        'porcentaje_atendidas': 0,
                        'porcentaje_abandonadas': 0,
                        'porcentaje_no_atendidas': 0,
                        'tiempo_espera_promedio': 0,
                        'tiempo_abandono_promedio': 0,
                        'duracion_promedio': 0
                    })
            return datos_completos
        elif agrupar_por == 'dia':
            # Ordenar por fecha (formato DD/MM/YYYY)
            def fecha_sort_key(x):
                try:
                    # Convertir DD/MM/YYYY a objeto datetime para ordenar
                    parts = x['grupo'].split('/')
                    if len(parts) == 3:
                        return int(parts[2]) * 10000 + int(parts[1]) * 100 + int(parts[0])
                    return 0
                except (ValueError, IndexError, KeyError, AttributeError):
                    return 0
            datos.sort(key=fecha_sort_key)
        elif agrupar_por == 'semana':
            datos.sort(key=lambda x: int(x['grupo'].split()[1]))
        elif agrupar_por == 'mes':
            meses_orden = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                           'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            datos.sort(key=lambda x: meses_orden.index(x['grupo']) if x['grupo'] in meses_orden else 99)
        else:  # campaña - ordenar por total descendente
            datos.sort(key=lambda x: x['total_llamadas'], reverse=True)

        return datos

    def get_detalle_transferencias(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el detalle de todas las llamadas con eventos de transferencia
        AGRUPADAS POR CALLID - Una fila por llamada con sus múltiples eventos
        """
        filters = filters or {}

        # Lista de eventos de transferencia
        eventos_transferencia = list(self.EVENTOS_TRANSFERENCIAS.keys())

        # Query base
        query = self.db.query(
            LlamadaLog.callid,
            LlamadaLog.time,
            LlamadaLog.event,
            LlamadaLog.campana_id,
            LlamadaLog.agente_id,
            LlamadaLog.numero_marcado,
            LlamadaLog.duracion_llamada,
            LlamadaLog.bridge_wait_time,
            LlamadaLog.contacto_id,
            Campana.nombre.label('campana_nombre'),
            User.first_name,
            User.last_name
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        ).filter(
            LlamadaLog.event.in_(eventos_transferencia)
        )

        # Aplicar filtros
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])
        if filters.get('campana_ids'):
            query = query.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        if filters.get('agente_ids'):
            query = query.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))

        query = query.order_by(LlamadaLog.time.asc())  # Ordenar por tiempo ascendente para agrupar

        llamadas = query.all()

        # Agrupar por callid (hora tal cual de la BD)
        llamadas_agrupadas = {}
        for llamada in llamadas:
            callid = llamada.callid

            if callid not in llamadas_agrupadas:
                agente_nombre = f'{llamada.first_name} {llamada.last_name}' if llamada.first_name else 'Sin Agente'

                llamadas_agrupadas[callid] = {
                    'callid': callid,
                    'fecha': llamada.time.strftime('%Y-%m-%d'),
                    'hora_inicio': llamada.time.strftime('%H:%M:%S'),
                    'campana': llamada.campana_nombre or 'Sin Campaña',
                    'agente': agente_nombre,
                    'numero': llamada.numero_marcado or 'N/A',
                    'duracion': int(llamada.duracion_llamada or 0),
                    'espera': int(llamada.bridge_wait_time or 0),
                    'contacto_id': llamada.contacto_id,
                    'eventos': []
                }

            # Agregar evento a la lista de eventos de esta llamada
            llamadas_agrupadas[callid]['eventos'].append({
                'evento': llamada.event,
                'evento_descripcion': self.EVENTOS_TRANSFERENCIAS.get(llamada.event, llamada.event),
                'hora': llamada.time.strftime('%H:%M:%S'),
                'duracion': int(llamada.duracion_llamada or 0)
            })

        # Convertir a lista y filtrar llamadas que SOLO tienen ENTERQUEUE-TRANSFER
        # Estas son llamadas transferidas a cola, no a agentes, y no deben contarse
        resultado = []
        for llamada in llamadas_agrupadas.values():
            # Si la llamada solo tiene 1 evento y es ENTERQUEUE-TRANSFER, la excluimos
            if len(llamada['eventos']) == 1 and llamada['eventos'][0]['evento'] == 'ENTERQUEUE-TRANSFER':
                continue
            resultado.append(llamada)

        # Ordenar por fecha descendente
        resultado.sort(key=lambda x: x['fecha'] + x['hora_inicio'], reverse=True)

        return resultado

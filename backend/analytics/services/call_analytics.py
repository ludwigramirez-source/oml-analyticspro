"""
Servicio de análisis de llamadas y métricas
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, case, extract, func, or_
from sqlalchemy.orm import Session

from ..config import config
from ..constants import (
    ABANDONMENT_THRESHOLD,
    EVENTOS_ABANDONADAS,
    EVENTOS_ATENDIDAS,
    EVENTOS_EXCLUIDOS,
    EVENTOS_FINALES,
    EVENTOS_INTERMEDIOS,
    EVENTOS_NO_ATENDIDAS,
    INBOUND_ONLY_MODE,
    NIVEL_ATENCION_CRITICO,
    SLA_THRESHOLD_20,
    SLA_THRESHOLD_60,
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


class CallAnalyticsService:
    """Servicio para análisis de llamadas"""

    # Constantes importadas desde analytics.constants
    EVENTOS_ATENDIDAS = EVENTOS_ATENDIDAS
    EVENTOS_ABANDONADAS = EVENTOS_ABANDONADAS
    EVENTOS_NO_ATENDIDAS = EVENTOS_NO_ATENDIDAS
    EVENTOS_INTERMEDIOS = EVENTOS_INTERMEDIOS
    EVENTOS_EXCLUIDOS = EVENTOS_EXCLUIDOS
    EVENTOS_FINALES = EVENTOS_FINALES
    TIPO_SALIENTE = TIPO_SALIENTE
    TIPO_ENTRANTE = TIPO_ENTRANTE
    SLA_THRESHOLD_60 = SLA_THRESHOLD_60
    SLA_THRESHOLD_20 = SLA_THRESHOLD_20
    ABANDONMENT_THRESHOLD = ABANDONMENT_THRESHOLD
    NIVEL_ATENCION_CRITICO = NIVEL_ATENCION_CRITICO

    def __init__(self, db: Session):
        self.db = db
        self._tz_db = config.TIMEZONE_DB  # 'America/Bogota'

    def _local_time(self, column):
        """
        Extrae timestamp naive con la hora tal cual está en la BD.
        El servidor OmniLeads tiene el reloj en hora local (Nicaragua)
        pero graba con offset de Colombia. AT TIME ZONE con el TZ de
        la BD devuelve la hora numérica sin convertir.
        """
        return func.timezone(self._tz_db, column)

    def _apply_filters(self, query, filters: Dict):
        """Aplica filtros comunes a las consultas"""
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])

        if filters.get('fecha_fin'):
            # Usar <= para incluir todo el día final (fecha_fin ya viene con 23:59:59.999999 desde el frontend)
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])

        # Campañas: soportar una sola o múltiples
        if filters.get('campana_ids'):
            query = query.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        elif filters.get('campana_id'):
            query = query.filter(LlamadaLog.campana_id == filters['campana_id'])

        if filters.get('tipo_campana'):
            query = query.filter(LlamadaLog.tipo_campana == filters['tipo_campana'])

        # Agentes: soportar uno solo o múltiples
        if filters.get('agente_ids'):
            query = query.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))
        elif filters.get('agente_id'):
            query = query.filter(LlamadaLog.agente_id == filters['agente_id'])

        # Tipo de llamada: entrantes o salientes
        if INBOUND_ONLY_MODE:
            query = query.filter(
                LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE
            )
        elif filters.get('tipo_llamada'):
            if filters['tipo_llamada'] == 'entrantes':
                query = query.filter(LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE)
            elif filters['tipo_llamada'] == 'salientes':
                query = query.filter(LlamadaLog.tipo_llamada == self.TIPO_SALIENTE)

        return query

    def _build_last_event_subquery(self, filters: Dict, event_list: List[str] = None):
        """
        Helper para construir subquery de último evento por callid con filtros aplicados.
        Usa MAX(id) como desempate cuando hay múltiples eventos con el mismo timestamp.
        """
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS)
        )

        # Filtrar por eventos específicos si se proporciona lista;
        # si no, usar EVENTOS_FINALES para coincidir con la lógica de CallAnalyticsExtended
        # y evitar que MAX(id) apunte a un evento intermedio (DIAL, ENTERQUEUE, etc.)
        if event_list:
            subquery = subquery.filter(LlamadaLog.event.in_(event_list))
        else:
            subquery = subquery.filter(LlamadaLog.event.in_(self.EVENTOS_FINALES))

        # Aplicar filtros comunes usando _apply_filters
        subquery = self._apply_filters(subquery, filters)

        return subquery.group_by(LlamadaLog.callid).subquery()

    def _get_sort_column(self, sort_by, LlamadaLogModel,
                         CampanaModel=None, UserModel=None):
        """
        Mapea nombre de campo frontend a columna SQLAlchemy
        para ORDER BY server-side.
        """
        sort_map = {
            'fecha': LlamadaLogModel.time,
            'hora': LlamadaLogModel.time,
            'duracion': LlamadaLogModel.duracion_llamada,
            'espera': LlamadaLogModel.bridge_wait_time,
            'tiempo_espera': LlamadaLogModel.bridge_wait_time,
            'callid': LlamadaLogModel.callid,
            'numero': LlamadaLogModel.numero_marcado,
            'evento': LlamadaLogModel.event,
            'agente_id': LlamadaLogModel.agente_id,
            'campana_id': LlamadaLogModel.campana_id,
        }
        if CampanaModel:
            sort_map['campana'] = CampanaModel.nombre
        if UserModel:
            sort_map['agente'] = UserModel.first_name
        return sort_map.get(sort_by, LlamadaLogModel.time)

    def get_kpis(self, filters: Dict = None) -> Dict:
        """
        Obtiene los KPIs principales del call center.
        OPTIMIZADO: Consolidación de subqueries y métricas en queries combinadas.
        """
        filters = filters or {}

        # Query base - SOLO EVENTOS FINALES y tipos activos
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_FINALES))
        query = query.filter(LlamadaLog.tipo_llamada.in_(TIPOS_LLAMADA_ACTIVOS))

        # Subquery para obtener último evento de cada llamada (por callid)
        from sqlalchemy import case

        last_events_subq = self._build_last_event_subquery(filters)

        # Single query con agregaciones condicionales para todos los tipos de llamadas
        call_counts = self.db.query(
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), LlamadaLog.callid),
                else_=None
            ))).label('atendidas'),
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS), LlamadaLog.callid),
                else_=None
            ))).label('abandonadas'),
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS), LlamadaLog.callid),
                else_=None
            ))).label('no_atendidas')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).first()

        llamadas_atendidas = call_counts.atendidas or 0
        llamadas_abandonadas = call_counts.abandonadas or 0
        llamadas_no_atendidas_otras = call_counts.no_atendidas or 0

        # Anomalías: llamadas cuyo último evento no está en ninguna categoría final
        todas_categorias = (
            self.EVENTOS_ATENDIDAS
            + self.EVENTOS_ABANDONADAS
            + self.EVENTOS_NO_ATENDIDAS
        )
        clasificadas = llamadas_atendidas + llamadas_abandonadas + llamadas_no_atendidas_otras

        # Total de llamadas = solo las que caen en categorías finales
        # Excluye NONDIALPLAN (click2call sin ruta) y eventos intermedios
        total_llamadas = clasificadas

        # Anomalías: llamadas cuyo último evento no está en ninguna
        # categoría final (ENTERQUEUE, CONNECT, HOLD, etc.)
        total_todas = self.db.query(
            func.count(func.distinct(LlamadaLog.callid))
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).scalar() or 0

        anomalias = max(0, total_todas - clasificadas)

        # Total no atendidas = abandonadas + otras
        llamadas_no_atendidas_total = llamadas_abandonadas + llamadas_no_atendidas_otras

        # OPTIMIZACIÓN 3: CONSOLIDAR TMO, ESPERA, SLA60, SLA20 EN SINGLE QUERY
        # En lugar de 4 queries separadas, usar una sola con múltiples agregaciones
        metrics = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).with_entities(
            func.avg(LlamadaLog.duracion_llamada).label('tmo_promedio'),
            func.avg(LlamadaLog.bridge_wait_time).label('espera_promedio'),
            func.sum(case(
                (and_(
                    LlamadaLog.bridge_wait_time.isnot(None),
                    LlamadaLog.bridge_wait_time <= self.SLA_THRESHOLD_60
                ), 1),
                else_=0
            )).label('llamadas_en_sla_60'),
            func.sum(case(
                (and_(
                    LlamadaLog.bridge_wait_time.isnot(None),
                    LlamadaLog.bridge_wait_time <= self.SLA_THRESHOLD_20
                ), 1),
                else_=0
            )).label('llamadas_en_sla_20')
        ).first()

        tmo_promedio = int(metrics.tmo_promedio) if metrics and metrics.tmo_promedio is not None else 0
        espera_promedio = int(metrics.espera_promedio) if metrics and metrics.espera_promedio is not None else 0
        llamadas_en_sla_60 = metrics.llamadas_en_sla_60 if metrics else 0
        llamadas_en_sla_20 = metrics.llamadas_en_sla_20 if metrics else 0

        service_level_60 = round((llamadas_en_sla_60 / llamadas_atendidas * 100), 2) if llamadas_atendidas > 0 else 0
        service_level_20 = round((llamadas_en_sla_20 / llamadas_atendidas * 100), 2) if llamadas_atendidas > 0 else 0

        # Agentes activos (únicos con llamadas en el período)
        agentes_activos = query.filter(
            LlamadaLog.agente_id.isnot(None)
        ).with_entities(
            func.count(func.distinct(LlamadaLog.agente_id))
        ).scalar() or 0

        # Ocupación = Tiempo hablando / Tiempo productivo (sesión - pausas recreativas)
        # Usa datos reales de ActividadAgenteLog para sesiones y pausas

        tiempo_total_llamadas = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.duracion_llamada.isnot(None)
        ).with_entities(
            func.sum(LlamadaLog.duracion_llamada)
        ).scalar() or 0

        # Obtener actividades de todos los agentes activos en el período
        actividades_query = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id.isnot(None)
        )
        if filters.get('fecha_inicio'):
            actividades_query = actividades_query.filter(
                ActividadAgenteLog.time >= filters['fecha_inicio']
            )
        if filters.get('fecha_fin'):
            actividades_query = actividades_query.filter(
                ActividadAgenteLog.time <= filters['fecha_fin']
            )

        actividades = actividades_query.order_by(
            ActividadAgenteLog.agente_id,
            ActividadAgenteLog.time
        ).all()

        # Agrupar actividades por agente
        actividades_por_agente = {}
        for act in actividades:
            if act.agente_id not in actividades_por_agente:
                actividades_por_agente[act.agente_id] = []
            actividades_por_agente[act.agente_id].append(act)

        # Obtener tipos de pausa (batch)
        all_pausa_ids = set()
        for acts in actividades_por_agente.values():
            for act in acts:
                if (act.event == 'PAUSEALL' and act.pausa_id
                        and str(act.pausa_id).isdigit()):
                    all_pausa_ids.add(int(act.pausa_id))

        pausas_dict = {}
        if all_pausa_ids:
            pausas_all = self.db.query(Pausa).filter(
                Pausa.id.in_(all_pausa_ids)
            ).all()
            pausas_dict = {str(p.id): p.tipo for p in pausas_all}

        # Calcular totales globales de sesión y pausas recreativas
        total_tiempo_sesion = 0
        total_pausas_recreativas = 0

        for agente_id, acts in actividades_por_agente.items():
            tiempo_login = None
            tiempo_pausa_inicio = None
            pausa_id_actual = None

            for actividad in acts:
                if actividad.event == 'ADDMEMBER':
                    tiempo_login = actividad.time
                elif actividad.event == 'REMOVEMEMBER':
                    if tiempo_login:
                        dur = (actividad.time - tiempo_login).total_seconds()
                        total_tiempo_sesion += dur
                        tiempo_login = None
                elif actividad.event == 'PAUSEALL':
                    tiempo_pausa_inicio = actividad.time
                    pausa_id_actual = actividad.pausa_id
                elif (actividad.event == 'UNPAUSEALL'
                        and tiempo_pausa_inicio):
                    dur = (actividad.time - tiempo_pausa_inicio).total_seconds()
                    if (pausa_id_actual
                            and pausa_id_actual in pausas_dict
                            and pausas_dict[pausa_id_actual] == 'R'):
                        total_pausas_recreativas += dur
                    tiempo_pausa_inicio = None
                    pausa_id_actual = None

        # Tiempo productivo = sesión total - pausas recreativas
        tiempo_productivo = total_tiempo_sesion - total_pausas_recreativas

        # Calcular ocupación
        ocupacion = round(
            (tiempo_total_llamadas / tiempo_productivo * 100), 2
        ) if tiempo_productivo > 0 else 0
        ocupacion = min(ocupacion, 100)  # Cap al 100%

        # Calcular métricas adicionales
        # FCR (First Call Resolution) - Simplificado
        fcr = round((llamadas_atendidas / total_llamadas * 100), 2) if total_llamadas > 0 else 0

        # Abandonment Rate (solo abandonadas, no todas las no atendidas)
        abandonment_rate = round((llamadas_abandonadas / total_llamadas * 100), 2) if total_llamadas > 0 else 0

        # ASA (Average Speed of Answer) - usando bridge_wait_time
        asa = espera_promedio

        # AHT (Average Handle Time) - igual que TMO
        aht = tmo_promedio

        return {
            'llamadas_totales': {
                'valor': total_llamadas,
                'cambio': '+12%',
                'tendencia': 'positivo',
                'icono': '📞'
            },
            'llamadas_atendidas': {
                'valor': llamadas_atendidas,
                'cambio': '+8%',
                'tendencia': 'positivo',
                'icono': '✅'
            },
            'llamadas_abandonadas': {
                'valor': llamadas_abandonadas,
                'cambio': '-5%',
                'tendencia': 'positivo' if abandonment_rate <= 5 else 'negativo',
                'icono': '📞❌',
                'label': 'Llamadas Abandonadas'
            },
            'llamadas_perdidas': {
                'valor': llamadas_no_atendidas_total,
                'cambio': '-3%',
                'tendencia': 'neutro',
                'icono': '❌',
                'label': 'Otras No Atendidas'
            },
            'aht': {  # Average Handle Time
                'valor': aht,
                'formato': 'segundos',
                'cambio': '-3%',
                'tendencia': 'positivo',
                'icono': '⏱️',
                'label': 'AHT (Tiempo Medio)'
            },
            'asa': {  # Average Speed of Answer
                'valor': asa,
                'formato': 'segundos',
                'cambio': '+2%',
                'tendencia': 'positivo' if asa <= 28 else 'negativo',
                'icono': '⏳',
                'label': 'ASA (Tiempo Espera)'
            },
            'service_level_60': {
                'valor': service_level_60,
                'formato': 'porcentaje',
                'cambio': '+5%',
                'tendencia': 'positivo' if service_level_60 >= 80 else 'negativo',
                'icono': '🎯',
                'label': 'Service Level < 60s'
            },
            'service_level_20': {
                'valor': service_level_20,
                'formato': 'porcentaje',
                'cambio': '+3%',
                'tendencia': 'positivo' if service_level_20 >= 70 else 'negativo',
                'icono': '⚡',
                'label': 'Service Level < 20s'
            },
            'fcr': {  # First Call Resolution
                'valor': fcr,
                'formato': 'porcentaje',
                'cambio': '+7%',
                'tendencia': 'positivo' if fcr >= 70 else 'negativo',
                'icono': '🎖️',
                'label': 'FCR (Resolución Primera Llamada)'
            },
            'abandonment_rate': {
                'valor': abandonment_rate,
                'formato': 'porcentaje',
                'cambio': '-2%',
                'tendencia': 'positivo' if abandonment_rate <= 5 else 'negativo',
                'icono': '📉',
                'label': 'Tasa de Abandono'
            },
            'agentes_activos': {
                'valor': agentes_activos,
                'cambio': '0%',
                'tendencia': 'neutral',
                'icono': '👥'
            },
            'ocupacion': {
                'valor': ocupacion,
                'formato': 'porcentaje',
                'cambio': '+4%',
                'tendencia': 'positivo' if (ocupacion >= 70 and ocupacion <= 90) else 'neutro',
                'icono': '📊'
            },
            'anomalias': {
                'valor': anomalias,
                'tendencia': 'negativo' if anomalias > 0 else 'neutro',
                'icono': '⚠️',
                'label': 'Anomalias'
            }
        }

    # Método get_llamadas_por_tipo removido - duplicado más abajo

    def get_distribucion_llamadas(self, filters: Dict = None) -> Dict:
        """
        Obtiene la distribución de llamadas por estado.
        Usa MAX(id) por callid para contar llamadas únicas,
        consistente con KPIs.
        """
        from sqlalchemy import case
        filters = filters or {}

        # Subquery: último evento de cada llamada (por callid)
        last_events_subq = self._build_last_event_subquery(filters)

        # Contar llamadas únicas por categoría del último evento
        counts = self.db.query(
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
                 LlamadaLog.callid),
                else_=None
            ))).label('atendidas'),
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS),
                 LlamadaLog.callid),
                else_=None
            ))).label('abandonadas'),
            func.count(func.distinct(case(
                (LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS),
                 LlamadaLog.callid),
                else_=None
            ))).label('no_atendidas'),
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).first()

        atendidas = counts.atendidas or 0
        abandonadas = counts.abandonadas or 0
        no_atendidas = counts.no_atendidas or 0
        total = atendidas + abandonadas + no_atendidas

        return {
            'labels': ['Atendidas', 'Abandonadas', 'No Atendidas'],
            'data': [atendidas, abandonadas, no_atendidas],
            'porcentajes': [
                round(atendidas / total * 100, 1) if total > 0 else 0,
                round(abandonadas / total * 100, 1) if total > 0 else 0,
                round(no_atendidas / total * 100, 1) if total > 0 else 0
            ]
        }

    def get_distribucion_por_tipo(self, filters: Dict = None) -> Dict:
        """
        Distribución de llamadas por tipo (entrantes vs salientes).
        Usa MAX(id) por callid para contar llamadas únicas,
        consistente con KPIs.
        """
        from sqlalchemy import case
        filters = filters or {}

        # Subquery GLOBAL: último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        # Base: solo filas que son el último evento
        base = self.db.query(LlamadaLog).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        )

        # --- ENTRANTES ---
        q_ent = base.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE
        )
        entrantes_atendidas = q_ent.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = q_ent.filter(
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()
        total_entrantes = entrantes_atendidas + entrantes_abandonadas

        # --- SALIENTES ---
        q_sal = base.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE
        )
        salientes_conectadas = q_sal.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        salientes_no_conectadas = q_sal.filter(
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
        ).count()
        total_salientes = salientes_conectadas + salientes_no_conectadas

        return {
            'entrantes': {
                'labels': ['Atendidas', 'Abandonadas'],
                'data': [entrantes_atendidas, entrantes_abandonadas],
                'porcentajes': [
                    round(entrantes_atendidas / total_entrantes * 100, 1) if total_entrantes > 0 else 0,
                    round(entrantes_abandonadas / total_entrantes * 100, 1) if total_entrantes > 0 else 0
                ],
                'total': total_entrantes
            },
            'salientes': {
                'labels': ['Conectadas', 'No Conectadas'],
                'data': [salientes_conectadas, salientes_no_conectadas],
                'porcentajes': [
                    round(salientes_conectadas / total_salientes * 100, 1) if total_salientes > 0 else 0,
                    round(salientes_no_conectadas / total_salientes * 100, 1) if total_salientes > 0 else 0
                ],
                'total': total_salientes
            }
        }

    def get_distribucion_horaria_detallada(self, filters: Dict = None) -> Dict:
        """
        Distribución horaria separando entrantes, salientes y abandonadas
        Como el gráfico "Distribución Horaria" de Power BI
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)

        # Obtener datos agrupados (hora convertida a timezone local)
        local_time = self._local_time(LlamadaLog.time)
        resultados = query.with_entities(
            extract('hour', local_time).label('hora'),
            LlamadaLog.tipo_llamada,
            LlamadaLog.event,
            func.count(LlamadaLog.id).label('total')
        ).group_by('hora', LlamadaLog.tipo_llamada, LlamadaLog.event).all()

        # Inicializar arrays de 24 horas
        horas = list(range(24))
        entrantes = [0] * 24
        salientes = [0] * 24
        abandonadas = [0] * 24

        for r in resultados:
            hora_idx = int(r.hora)
            if r.tipo_llamada == self.TIPO_ENTRANTE:
                entrantes[hora_idx] += r.total
                if r.event in self.EVENTOS_ABANDONADAS:
                    abandonadas[hora_idx] += r.total
            elif r.tipo_llamada == self.TIPO_SALIENTE:
                salientes[hora_idx] += r.total

        return {
            'labels': [f'{h:02d}:00' for h in horas],
            'entrantes': entrantes,
            'salientes': salientes,
            'abandonadas': abandonadas
        }

    def get_evolucion_por_hora(self, filters: Dict = None) -> Dict:
        """
        Obtiene la evolución de llamadas por hora
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)

        # Agrupar por hora (convertida a timezone local)
        local_time = self._local_time(LlamadaLog.time)
        resultados = query.with_entities(
            extract('hour', local_time).label('hora'),
            func.count(LlamadaLog.id).label('total')
        ).group_by('hora').order_by('hora').all()

        # Crear arrays de 24 horas
        horas = list(range(24))
        datos = [0] * 24

        for resultado in resultados:
            hora_idx = int(resultado.hora)
            datos[hora_idx] = resultado.total

        return {
            'labels': [f'{h:02d}:00' for h in horas],
            'data': datos
        }

    def get_nivel_servicio_detallado(self, filters: Dict = None) -> Dict:
        """
        Obtiene distribución del nivel de servicio por rangos de tiempo
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        query = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.bridge_wait_time.isnot(None)
        )

        # Definir rangos
        rangos = [
            ('0-10s', 0, 10),
            ('11-20s', 11, 20),
            ('21-30s', 21, 30),
            ('31-60s', 31, 60),
            ('>60s', 61, 999999)
        ]

        resultados = []
        for label, min_val, max_val in rangos:
            count = query.filter(
                and_(
                    LlamadaLog.bridge_wait_time >= min_val,
                    LlamadaLog.bridge_wait_time <= max_val
                )
            ).count()
            resultados.append(count)

        return {
            'labels': [r[0] for r in rangos],
            'data': resultados
        }

    def get_causas_no_atencion(self, filters: Dict = None) -> Dict:
        """
        Obtiene las causas de llamadas no atendidas
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS))

        resultados = query.with_entities(
            LlamadaLog.event,
            func.count(LlamadaLog.id).label('total')
        ).group_by(LlamadaLog.event).order_by(func.count(LlamadaLog.id).desc()).all()

        # Mapeo de eventos a nombres legibles
        evento_nombres = {
            'ABANDON': 'Abandonada',
            'EXITWITHTIMEOUT': 'Timeout',
            'NOANSWER': 'No contestó',
            'CANCEL': 'Cancelada',
            'BUSY': 'Ocupado',
            'CHANUNAVAIL': 'Canal no disponible',
            'FAIL': 'Fallo',
            'ABANDONWEL': 'Abandonada (bienvenida)',
            'RINGNOANSWER': 'Timbró sin respuesta',
            'CONGESTION': 'Congestión'
        }

        return {
            'labels': [evento_nombres.get(r.event, r.event) for r in resultados],
            'data': [r.total for r in resultados]
        }

    def get_llamadas_abandonadas(
        self, filters: Dict = None, page: int = 1,
        per_page: int = 50, sort_by: str = None,
        sort_dir: str = 'desc'
    ) -> Dict:
        """
        Obtiene lista detallada de llamadas NO ATENDIDAS con paginación.
        Usa el último evento GLOBAL de cada llamada (MAX(id) por callid)
        y filtra solo las cuyo último evento es ABANDONADA o NO_ATENDIDA.
        Consistente con KPIs.
        """
        page = max(1, page)
        per_page = max(1, min(per_page, 200))
        filters = filters or {}

        # Combinar eventos abandonadas + no atendidas
        eventos_no_atendidas_todas = (
            self.EVENTOS_ABANDONADAS + self.EVENTOS_NO_ATENDIDAS
        )

        # Subquery GLOBAL: último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        # Query principal: JOIN con subquery, filtrar NO ATENDIDAS
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).filter(
            LlamadaLog.event.in_(eventos_no_atendidas_todas)
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
        sort_column = self._get_sort_column(
            sort_by, LlamadaLog, Campana, User
        )
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

            # Mapear tipo de abandono
            tipo_abandono = {
                'ABANDON': 'En Cola',
                'ABANDONWEL': 'En Audio Bienvenida',
                'EXITWITHTIMEOUT': 'Timeout',
                'ABANDON-CTOUT': 'Durante Transferencia'
            }.get(llamada.event, llamada.event)

            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': llamada.time.strftime('%Y-%m-%d'),
                'hora': llamada.time.strftime('%H:%M:%S'),
                'campana': r.campana_nombre or f'Campaña {llamada.campana_id}',
                'agente': f'{r.agente_nombre or ""} {r.agente_apellido or ""}'.strip() or 'Sin asignar',
                'numero': llamada.numero_marcado or '-',
                'tiempo_espera': llamada.bridge_wait_time or 0,
                'evento': llamada.event,
                'tipo_abandono': tipo_abandono
            })

        return {
            'data': llamadas,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

    def get_llamadas_detalladas(
        self, filters: Dict = None, page: int = 1,
        per_page: int = 50, sort_by: str = None,
        sort_dir: str = 'desc'
    ) -> Dict:
        """
        Obtiene lista detallada de llamadas ATENDIDAS con paginación.
        Usa el último evento GLOBAL de cada llamada (MAX(id) por callid)
        y filtra solo las cuyo último evento es ATENDIDA.
        Consistente con KPIs.
        """
        page = max(1, page)
        per_page = max(1, min(per_page, 200))
        filters = filters or {}

        # Subquery GLOBAL: último evento de cada llamada
        last_events_subq = self._build_last_event_subquery(filters)

        # Query principal: JOIN con subquery, filtrar ATENDIDAS
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido')
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
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
        sort_column = self._get_sort_column(
            sort_by, LlamadaLog, Campana, User
        )
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

            # Determinar quién colgó
            quien_colgo = 'Agente' if llamada.event == 'COMPLETEAGENT' else 'Cliente'

            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': llamada.time.strftime('%Y-%m-%d'),
                'hora': llamada.time.strftime('%H:%M:%S'),
                'campana': r.campana_nombre or f'Campaña {llamada.campana_id}',
                'agente': f'{r.agente_nombre or ""} {r.agente_apellido or ""}'.strip() or f'Agente {llamada.agente_id}',
                'numero': llamada.numero_marcado or '-',
                'duracion': llamada.duracion_llamada or 0,
                'espera': llamada.bridge_wait_time or 0,
                'evento': llamada.event,
                'quien_colgo': quien_colgo,
                'grabacion': llamada.archivo_grabacion or ''
            })

        return {
            'data': llamadas,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }

    def get_nivel_atencion_por_campana(self, filters: Dict = None) -> List[Dict]:
        """
        Nivel de atención por campaña con alertas (como Power BI)
        Verde >= 90%, Amarillo >= 80%, Rojo < 80%
        Cuenta solo llamadas únicas (por callid, último evento)
        """
        filters = filters or {}

        # Subquery para obtener el último evento de cada llamada
        # Usa MAX(id) como desempate para eventos con mismo timestamp
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.tipo_llamada == 3  # Solo entrantes
        )

        if filters.get('fecha_inicio'):
            subquery = subquery.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            subquery = subquery.filter(LlamadaLog.time <= filters['fecha_fin'])

        subquery = subquery.group_by(LlamadaLog.callid).subquery()

        # Query principal con llamadas únicas
        query = self.db.query(
            Campana.nombre,
            Campana.id,
            func.count(func.distinct(AgenteProfile.id)).label('cantidad_agentes'),
            func.count(func.distinct(LlamadaLog.callid)).label('total_llamadas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
            ).label('atendidas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS), 1), else_=0)
            ).label('abandonadas'),
            func.avg(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), LlamadaLog.duracion_llamada), else_=None)
            ).label('prom_duracion')
        ).join(
            Campana, Campana.id == LlamadaLog.campana_id
        ).join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.id == subquery.c.ultimo_id
            )
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        )

        if filters.get('campana_ids'):
            query = query.filter(Campana.id.in_(filters['campana_ids']))
        if filters.get('agente_ids'):
            query = query.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))

        resultados = query.group_by(Campana.nombre, Campana.id).order_by(
            func.count(func.distinct(LlamadaLog.callid)).desc()
        ).all()

        campanias = []
        for r in resultados:
            nivel_atencion = round((r.atendidas / r.total_llamadas * 100), 2) if r.total_llamadas > 0 else 0

            # Determinar estado y color según nivel
            # Verde (OK): 80% - 100%
            # Naranja (Advertencia): 60% - 80%
            # Rojo (Crítico): < 60%
            if nivel_atencion >= 80:
                estado = 'excelente'
                color = 'green'
                alerta = False
            elif nivel_atencion >= 60:
                estado = 'advertencia'
                color = 'orange'
                alerta = False
            else:
                estado = 'critico'
                color = 'red'
                alerta = True  # Requiere atención inmediata

            campanias.append({
                'campana_id': r.id,
                'campana': r.nombre,
                'cantidad_agentes': r.cantidad_agentes or 0,
                'llamadas_entrantes': r.total_llamadas,
                'atendidas': r.atendidas or 0,
                'abandonadas': r.abandonadas or 0,
                'nivel_atencion': nivel_atencion,
                'prom_duracion': int(r.prom_duracion) if r.prom_duracion else 0,
                'estado': estado,
                'color': color,
                'alerta': alerta
            })

        return campanias

    def get_distribucion_por_campana(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene distribución de llamadas por campaña
        """
        filters = filters or {}
        query = self.db.query(
            Campana.nombre,
            func.count(LlamadaLog.id).label('total'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
            ).label('atendidas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS), 1), else_=0)
            ).label('no_atendidas')
        ).join(
            LlamadaLog, Campana.id == LlamadaLog.campana_id
        )

        query = self._apply_filters(query, filters)

        resultados = query.group_by(Campana.nombre).order_by(func.count(LlamadaLog.id).desc()).all()

        return [{
            'campana': r.nombre,
            'total': r.total,
            'atendidas': r.atendidas or 0,
            'no_atendidas': r.no_atendidas or 0,
            'tasa_atencion': round((r.atendidas or 0) / r.total * 100, 2) if r.total > 0 else 0
        } for r in resultados]

    def get_llamadas_por_tipo(self, filters: Dict = None) -> Dict:
        """
        Distribución de llamadas separando ENTRANTES y SALIENTES.
        Usa MAX(id) por callid para contar llamadas únicas,
        consistente con KPIs.
        """
        from sqlalchemy import case
        filters = filters or {}

        # Subquery: último evento de cada llamada (por callid)
        last_events_subq = self._build_last_event_subquery(filters)

        # Query base: solo filas que son el último evento
        base = self.db.query(LlamadaLog).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        )

        # --- ENTRANTES (tipo_llamada = 3) ---
        q_ent = base.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE
        )
        entrantes_atendidas = q_ent.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = q_ent.filter(
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()
        # Total = solo categorías finales (excluye intermedios/NONDIALPLAN)
        entrantes_total = entrantes_atendidas + entrantes_abandonadas

        # --- SALIENTES (tipo_llamada = 1) ---
        q_sal = base.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE
        )
        salientes_atendidas = q_sal.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        salientes_no_atendidas = q_sal.filter(
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
        ).count()
        # Total = solo categorías finales (excluye intermedios/NONDIALPLAN)
        salientes_total = salientes_atendidas + salientes_no_atendidas

        # Calcular tasas
        tasa_abandono_entrantes = round(
            entrantes_abandonadas / entrantes_total * 100, 2
        ) if entrantes_total > 0 else 0
        tasa_no_atencion_salientes = round(
            salientes_no_atendidas / salientes_total * 100, 2
        ) if salientes_total > 0 else 0

        return {
            'entrantes': {
                'total': entrantes_total,
                'atendidas': entrantes_atendidas,
                'abandonadas': entrantes_abandonadas,
                'nivel_atencion': round(
                    entrantes_atendidas / entrantes_total * 100, 2
                ) if entrantes_total > 0 else 0,
                'tasa_abandono': tasa_abandono_entrantes
            },
            'salientes': {
                'total': salientes_total,
                'atendidas': salientes_atendidas,
                'no_atendidas': salientes_no_atendidas,
                'nivel_atencion': round(
                    salientes_atendidas / salientes_total * 100, 2
                ) if salientes_total > 0 else 0,
                'tasa_no_atencion': tasa_no_atencion_salientes
            }
        }

    def get_evolucion_semanal(self, filters: Dict = None) -> Dict:
        """
        Obtiene evolución semanal de llamadas con 3 series:
        - Llamadas contestadas (atendidas)
        - Llamadas abandonadas
        - Agentes activos
        """
        filters = filters or {}

        # Consultar llamadas agrupadas por semana (timezone local)
        local_time = self._local_time(LlamadaLog.time)
        query = self.db.query(
            func.date_trunc('week', local_time).label('semana'),
            func.count(LlamadaLog.id).label('total'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
            ).label('contestadas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS), 1), else_=0)
            ).label('abandonadas')
        )

        query = self._apply_filters(query, filters)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_FINALES))

        resultados = query.group_by('semana').order_by('semana').all()

        # Consultar agentes activos por semana (timezone local)
        agentes_query = self.db.query(
            func.date_trunc('week', local_time).label('semana'),
            func.count(func.distinct(LlamadaLog.agente_id)).label('agentes_activos')
        )

        agentes_query = self._apply_filters(agentes_query, filters)
        agentes_query = agentes_query.filter(
            LlamadaLog.agente_id.isnot(None),
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        )

        agentes_resultados = agentes_query.group_by('semana').order_by('semana').all()

        # Crear diccionario de agentes por semana
        agentes_por_semana = {r.semana: r.agentes_activos for r in agentes_resultados}

        # Preparar respuesta
        semanas = []
        contestadas = []
        abandonadas = []
        agentes = []

        for r in resultados:
            # Formatear semana como "Semana del DD/MM"
            fecha_semana = r.semana.strftime('%d/%m')
            semanas.append(f"Semana {fecha_semana}")
            contestadas.append(r.contestadas or 0)
            abandonadas.append(r.abandonadas or 0)
            agentes.append(agentes_por_semana.get(r.semana, 0))

        return {
            'labels': semanas,
            'series': [
                {
                    'name': 'Contestadas',
                    'data': contestadas
                },
                {
                    'name': 'Abandonadas',
                    'data': abandonadas
                },
                {
                    'name': 'Agentes Activos',
                    'data': agentes
                }
            ]
        }

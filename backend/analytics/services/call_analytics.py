"""
Servicio de análisis de llamadas y métricas
"""
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import and_, case, extract, func, or_
from sqlalchemy.orm import Session

from ..config import config
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

    # Eventos que indican llamadas ATENDIDAS (conectadas con agente)
    # Lista maestra unificada - usada por todos los endpoints
    EVENTOS_ATENDIDAS = [
        'COMPLETEAGENT',      # Agente cuelga
        'COMPLETEOUTNUM',     # Cliente cuelga
        'COMPLETE-BTOUT',     # Transfer ciego completado
        'COMPLETE-CTOUT',     # Transfer consultivo completado
    ]

    # Eventos de llamadas ABANDONADAS (cliente abandona o timeout)
    # EXITWITHTIMEOUT incluido: el cliente esperó hasta que el sistema lo expulsó
    EVENTOS_ABANDONADAS = [
        'ABANDON',            # Abandono en cola
        'ABANDONWEL',         # Abandono durante audio de bienvenida
        'ABANDON-CTOUT',      # Abandono durante transfer consultivo
        'EXITWITHTIMEOUT',    # Timeout en cola (abandono forzado)
    ]

    # Otros eventos de llamadas NO atendidas (errores/problemas)
    EVENTOS_NO_ATENDIDAS = [
        'NOANSWER',           # No contesta (saliente)
        'CANCEL',             # Cancelada (saliente)
        'CHANUNAVAIL',        # Canal no disponible
        'NONDIALPLAN',        # Sin ruta de marcado
        'BUSY',               # Ocupado
        'DIAL',               # Llamada que solo quedó en DIAL
    ]

    # Eventos intermedios que NO deberían ser "último evento" (anomalías)
    EVENTOS_INTERMEDIOS = [
        'ENTERQUEUE',         # Solo entrada en cola
        'CONNECT',            # Solo conexión sin evento final
        'BTOUT-TRY',          # Intento de transfer
        'BTOUT-ANSWER',       # Respuesta de transfer
        'ANSWER',             # Respuesta genérica
        'HOLD',               # En espera
        'UNHOLD',             # Fin de espera
        'RINGNOANSWER',       # Timbrando sin respuesta (intermedio)
    ]

    # EVENTOS FINALES: Solo estos cuentan como "llamadas" en los totales
    EVENTOS_FINALES = (
        EVENTOS_ATENDIDAS
        + EVENTOS_ABANDONADAS
        + EVENTOS_NO_ATENDIDAS
    )

    # Tipos de llamada (basado en estructura real de OmniLeads)
    TIPO_SALIENTE = 1      # Llamadas manuales salientes
    TIPO_ENTRANTE = 3      # Llamadas entrantes (inbound)

    # Umbrales estándar de la industria
    SLA_THRESHOLD_60 = 60  # Nivel de servicio < 60 segundos
    SLA_THRESHOLD_20 = 20  # Nivel de servicio < 20 segundos
    ABANDONMENT_THRESHOLD = 0.05  # 5% tasa de abandono aceptable
    NIVEL_ATENCION_CRITICO = 80  # Nivel de atención crítico < 80%

    def __init__(self, db: Session):
        self.db = db
        self._tz_name = config.TIMEZONE_NAME  # 'America/Managua'

    def _local_time(self, column):
        """
        Convierte una columna timestamptz a hora local usando
        PostgreSQL AT TIME ZONE.
        Ej: time AT TIME ZONE 'America/Managua'
        Esto convierte correctamente desde el timezone de la BD
        (America/Bogota UTC-5) al timezone del cliente (UTC-6).
        """
        return func.timezone(self._tz_name, column)

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
        if filters.get('tipo_llamada'):
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
            LlamadaLog.tipo_llamada.in_([self.TIPO_ENTRANTE, self.TIPO_SALIENTE])
        )

        # Filtrar por eventos específicos si se proporciona lista
        if event_list:
            subquery = subquery.filter(LlamadaLog.event.in_(event_list))

        # Aplicar filtros comunes usando _apply_filters
        subquery = self._apply_filters(subquery, filters)

        return subquery.group_by(LlamadaLog.callid).subquery()

    def get_kpis(self, filters: Dict = None) -> Dict:
        """
        Obtiene los KPIs principales del call center.
        OPTIMIZADO: Consolidación de subqueries y métricas en queries combinadas.
        """
        filters = filters or {}

        # Query base - SOLO EVENTOS FINALES y SOLO tipo_llamada 1 y 3
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_FINALES))
        query = query.filter(LlamadaLog.tipo_llamada.in_([self.TIPO_ENTRANTE, self.TIPO_SALIENTE]))

        # OPTIMIZACIÓN 1: Contar con scalar en lugar de .count()
        total_llamadas = query.with_entities(func.count(LlamadaLog.id)).scalar() or 0

        # OPTIMIZACIÓN 2: CONSOLIDAR 3 SUBQUERIES EN 1 - Mayor impacto!
        # Single subquery para obtener último evento de cada llamada
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

        # Total de llamadas únicas basadas en último evento
        total_unicas = self.db.query(
            func.count(func.distinct(LlamadaLog.callid))
        ).join(
            last_events_subq,
            and_(
                LlamadaLog.callid == last_events_subq.c.callid,
                LlamadaLog.id == last_events_subq.c.ultimo_id
            )
        ).scalar() or 0

        anomalias = max(0, total_unicas - clasificadas)

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

        tmo_promedio = int(metrics.tmo_promedio) if metrics and metrics.tmo_promedio else 0
        espera_promedio = int(metrics.espera_promedio) if metrics and metrics.espera_promedio else 0
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

        # Ocupación - Cálculo simplificado basado en tiempo de llamadas
        # Ocupación = Tiempo total en llamadas / Tiempo disponible de agentes
        # Tiempo disponible estimado = Agentes activos × Duración del período en segundos

        tiempo_total_llamadas = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.duracion_llamada.isnot(None)
        ).with_entities(
            func.sum(LlamadaLog.duracion_llamada)
        ).scalar() or 0

        # Calcular duración del período en segundos
        if filters.get('fecha_inicio') and filters.get('fecha_fin'):
            # Si hay filtros de fecha, usar esos
            fecha_inicio = filters['fecha_inicio']
            fecha_fin = filters['fecha_fin']

            # Convertir a datetime si son date
            if not isinstance(fecha_inicio, datetime):
                fecha_inicio = datetime.combine(fecha_inicio, datetime.min.time())
            if not isinstance(fecha_fin, datetime):
                fecha_fin = datetime.combine(fecha_fin, datetime.max.time())

            duracion_periodo_segundos = (fecha_fin - fecha_inicio).total_seconds()
        else:
            # Sin filtros, asumir 1 día laboral (8 horas)
            duracion_periodo_segundos = 8 * 3600

        # Tiempo disponible = agentes activos × duración del período
        tiempo_disponible = agentes_activos * duracion_periodo_segundos

        # Calcular ocupación
        ocupacion = round((tiempo_total_llamadas / tiempo_disponible * 100), 2) if tiempo_disponible > 0 else 0
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
        Obtiene la distribución de llamadas por estado
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)

        atendidas = query.filter(LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)).count()
        abandonadas = query.filter(LlamadaLog.event == 'ABANDON').count()
        no_atendidas = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS),
            LlamadaLog.event != 'ABANDON'
        ).count()

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
        Obtiene la distribución de llamadas separada por tipo (entrantes vs salientes)
        Para mostrar dos gráficos de pie separados
        """
        filters = filters or {}

        # Consulta para llamadas entrantes
        query_entrantes = self.db.query(LlamadaLog)
        query_entrantes = self._apply_filters(query_entrantes, filters)
        query_entrantes = query_entrantes.filter(LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE)

        entrantes_atendidas = query_entrantes.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = query_entrantes.filter(
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()

        total_entrantes = entrantes_atendidas + entrantes_abandonadas

        # Consulta para llamadas salientes
        query_salientes = self.db.query(LlamadaLog)
        query_salientes = self._apply_filters(query_salientes, filters)
        query_salientes = query_salientes.filter(LlamadaLog.tipo_llamada == self.TIPO_SALIENTE)

        salientes_conectadas = query_salientes.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        salientes_no_conectadas = query_salientes.filter(
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
                if r.event in self.EVENTOS_NO_ATENDIDAS:
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

    def get_llamadas_abandonadas(self, filters: Dict = None, page: int = 1, per_page: int = 50) -> Dict:
        """
        Obtiene lista detallada de llamadas NO ATENDIDAS con paginación
        Incluye: ABANDONADAS (entrantes) + NO ATENDIDAS (salientes)
        - ABANDON, ABANDONWEL, EXITWITHTIMEOUT (abandonadas entrantes)
        - NOANSWER, CANCEL, BUSY, etc. (no atendidas salientes)
        Convierte timezone según configuración (TIMEZONE_OFFSET)
        """
        from ..config import config

        filters = filters or {}

        # Combinar eventos abandonadas + no atendidas
        eventos_no_atendidas_todas = self.EVENTOS_ABANDONADAS + self.EVENTOS_NO_ATENDIDAS

        # Subquery para obtener el último evento de cada llamada no atendida
        # Usa MAX(id) como desempate para eventos con mismo timestamp
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.event.in_(eventos_no_atendidas_todas),
            LlamadaLog.tipo_llamada.in_([self.TIPO_ENTRANTE, self.TIPO_SALIENTE])
        )

        if filters.get('fecha_inicio'):
            subquery = subquery.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            subquery = subquery.filter(LlamadaLog.time <= filters['fecha_fin'])
        if filters.get('campana_ids'):
            subquery = subquery.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        if filters.get('agente_ids'):
            subquery = subquery.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))

        subquery = subquery.group_by(LlamadaLog.callid).subquery()

        # Query principal con JOIN a subquery para obtener solo últimos eventos
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
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )

        # Total de registros
        total = query.count()

        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone configurado
        local_tz = config.get_timezone()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a timezone local
            time_local = llamada.time.astimezone(local_tz)

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
                'fecha': time_local.strftime('%Y-%m-%d'),
                'hora': time_local.strftime('%H:%M:%S'),
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

    def get_llamadas_detalladas(self, filters: Dict = None, page: int = 1, per_page: int = 50) -> Dict:
        """
        Obtiene lista detallada de llamadas ATENDIDAS con paginación
        Solo eventos finales: COMPLETEAGENT, COMPLETEOUTNUM
        Convierte timezone según configuración (TIMEZONE_OFFSET)
        """
        from ..config import config

        filters = filters or {}

        # Subquery para obtener el último evento de cada llamada atendida
        # Usa MAX(id) como desempate para eventos con mismo timestamp
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.id).label('ultimo_id')
        ).filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.tipo_llamada.in_([self.TIPO_ENTRANTE, self.TIPO_SALIENTE])
        )

        if filters.get('fecha_inicio'):
            subquery = subquery.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            subquery = subquery.filter(LlamadaLog.time <= filters['fecha_fin'])
        if filters.get('campana_ids'):
            subquery = subquery.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        if filters.get('agente_ids'):
            subquery = subquery.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))

        subquery = subquery.group_by(LlamadaLog.callid).subquery()

        # Query principal con JOIN a subquery para obtener solo últimos eventos
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
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )

        # Total de registros
        total = query.count()

        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()

        # Timezone configurado
        local_tz = config.get_timezone()

        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog

            # Convertir tiempo a timezone local
            time_local = llamada.time.astimezone(local_tz)

            # Determinar quién colgó
            quien_colgo = 'Agente' if llamada.event == 'COMPLETEAGENT' else 'Cliente'

            llamadas.append({
                'id': llamada.id,
                'callid': llamada.callid,
                'fecha': time_local.strftime('%Y-%m-%d'),
                'hora': time_local.strftime('%H:%M:%S'),
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
        Distribución de llamadas separando ENTRANTES y SALIENTES
        Mejora de Power BI - Solo cuenta eventos finales
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_FINALES))  # SOLO EVENTOS FINALES

        # Llamadas ENTRANTES (tipo_llamada = 3)
        entrantes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE).count()
        entrantes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()

        # Llamadas SALIENTES (tipo_llamada = 1)
        salientes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_SALIENTE).count()
        salientes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        # Para salientes: no atendidas = CANCEL, NOANSWER, BUSY, etc.
        salientes_no_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE,
            LlamadaLog.event.in_(['CANCEL', 'NOANSWER', 'BUSY', 'CHANUNAVAIL', 'NONDIALPLAN'])
        ).count()

        # Calcular tasas
        tasa_abandono_entrantes = round(entrantes_abandonadas / entrantes_total * 100, 2) if entrantes_total > 0 else 0
        tasa_no_atencion_salientes = round(salientes_no_atendidas / salientes_total * 100, 2) if salientes_total > 0 else 0

        return {
            'entrantes': {
                'total': entrantes_total,
                'atendidas': entrantes_atendidas,
                'abandonadas': entrantes_abandonadas,
                'nivel_atencion': round(entrantes_atendidas / entrantes_total * 100, 2) if entrantes_total > 0 else 0,
                'tasa_abandono': tasa_abandono_entrantes
            },
            'salientes': {
                'total': salientes_total,
                'atendidas': salientes_atendidas,
                'no_atendidas': salientes_no_atendidas,
                'nivel_atencion': round(salientes_atendidas / salientes_total * 100, 2) if salientes_total > 0 else 0,
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

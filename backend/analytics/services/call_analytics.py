"""
Servicio de análisis de llamadas y métricas
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, extract
from ..models.omnileads_models import LlamadaLog, Campana, AgenteProfile, User


class CallAnalyticsService:
    """Servicio para análisis de llamadas"""
    
    # Eventos de llamadas ATENDIDAS (cuando hay respuesta/conexión real)
    EVENTOS_ATENDIDAS = [
        'COMPLETEAGENT',      # Agente cuelga la llamada
        'COMPLETEOUTNUM',     # Cliente/llamante cuelga la llamada
    ]
    
    # Eventos de llamadas ABANDONADAS (cliente abandona)
    EVENTOS_ABANDONADAS = [
        'ABANDON',            # Abandono en cola
        'ABANDON-CTOUT',      # Abandono durante transfer consultivo
        'ABANDONWEL'          # Abandono durante audio de bienvenida
    ]
    
    # Otros eventos de llamadas NO atendidas
    EVENTOS_NO_ATENDIDAS = [
        'EXITWITHTIMEOUT',    # Timeout en cola
        'NOANSWER',           # No contesta (saliente)
        'CANCEL',             # Cancelada (saliente)
        'CHANUNAVAIL',        # Canal no disponible
        'NONDIALPLAN'         # Sin ruta de marcado
    ]
    
    # Tipos de llamada
    TIPO_ENTRANTE = 1
    TIPO_SALIENTE = 2
    TIPO_TRANSFERENCIA = 3
    
    # Umbrales estándar de la industria
    SLA_THRESHOLD_60 = 60  # Nivel de servicio < 60 segundos
    SLA_THRESHOLD_20 = 20  # Nivel de servicio < 20 segundos
    ABANDONMENT_THRESHOLD = 0.05  # 5% tasa de abandono aceptable
    NIVEL_ATENCION_CRITICO = 80  # Nivel de atención crítico < 80%
    
    def __init__(self, db: Session):
        self.db = db
    
    def _apply_filters(self, query, filters: Dict):
        """Aplica filtros comunes a las consultas"""
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        
        if filters.get('fecha_fin'):
            # Agregar 1 día para incluir todo el día final
            fecha_fin = filters['fecha_fin'] + timedelta(days=1)
            query = query.filter(LlamadaLog.time < fecha_fin)
        
        if filters.get('campana_id'):
            query = query.filter(LlamadaLog.campana_id == filters['campana_id'])
        
        if filters.get('tipo_campana'):
            query = query.filter(LlamadaLog.tipo_campana == filters['tipo_campana'])
        
        if filters.get('agente_id'):
            query = query.filter(LlamadaLog.agente_id == filters['agente_id'])
        
        return query
    
    def get_kpis(self, filters: Dict = None) -> Dict:
        """
        Obtiene los KPIs principales del call center
        """
        filters = filters or {}
        
        # Query base
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        
        # Total de llamadas
        total_llamadas = query.count()
        
        # Llamadas atendidas (COMPLETEAGENT, COMPLETEOUTNUM)
        llamadas_atendidas = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        
        # Llamadas abandonadas (ABANDON, ABANDON-CTOUT, ABANDONWEL)
        llamadas_abandonadas = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()
        
        # Otras llamadas no atendidas (NOANSWER, TIMEOUT, etc)
        llamadas_no_atendidas_otras = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
        ).count()
        
        # Total no atendidas = abandonadas + otras
        llamadas_no_atendidas_total = llamadas_abandonadas + llamadas_no_atendidas_otras
        
        # TMO (Tiempo Medio de Operación) - solo llamadas atendidas
        tmo_result = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.duracion_llamada.isnot(None)
        ).with_entities(
            func.avg(LlamadaLog.duracion_llamada).label('tmo_promedio')
        ).first()
        
        tmo_promedio = int(tmo_result.tmo_promedio) if tmo_result.tmo_promedio else 0
        
        # Tiempo de espera promedio
        espera_result = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.bridge_wait_time.isnot(None)
        ).with_entities(
            func.avg(LlamadaLog.bridge_wait_time).label('espera_promedio')
        ).first()
        
        espera_promedio = int(espera_result.espera_promedio) if espera_result.espera_promedio else 0
        
        # Service Level < 60 segundos (estándar industria)
        llamadas_en_sla_60 = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.bridge_wait_time <= self.SLA_THRESHOLD_60
        ).count()
        
        service_level_60 = round((llamadas_en_sla_60 / llamadas_atendidas * 100), 2) if llamadas_atendidas > 0 else 0
        
        # Service Level < 20 segundos (alto rendimiento)
        llamadas_en_sla_20 = query.filter(
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS),
            LlamadaLog.bridge_wait_time <= self.SLA_THRESHOLD_20
        ).count()
        
        service_level_20 = round((llamadas_en_sla_20 / llamadas_atendidas * 100), 2) if llamadas_atendidas > 0 else 0
        
        # Agentes activos (únicos con llamadas en el período)
        agentes_activos = query.filter(
            LlamadaLog.agente_id.isnot(None)
        ).with_entities(
            func.count(func.distinct(LlamadaLog.agente_id))
        ).scalar() or 0
        
        # Ocupación (porcentaje de tiempo en llamadas vs tiempo disponible)
        # Simplificado: tiempo total en llamadas / (agentes * tiempo período)
        tiempo_total_llamadas = query.filter(
            LlamadaLog.duracion_llamada.isnot(None)
        ).with_entities(
            func.sum(LlamadaLog.duracion_llamada)
        ).scalar() or 0
        
        # Calcular ocupación (asumiendo 8 horas = 28800 segundos por agente)
        tiempo_disponible = agentes_activos * 28800 if agentes_activos > 0 else 1
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
            }
        }
    
    def get_llamadas_por_tipo(self, filters: Dict = None) -> Dict:
        """
        Obtiene distribución separando ENTRANTES vs SALIENTES
        Crítico para replicar Power BI
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        
        # LLAMADAS ENTRANTES
        entrantes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE).count()
        entrantes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
        ).count()
        
        # LLAMADAS SALIENTES
        salientes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_SALIENTE).count()
        salientes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        salientes_no_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE,
            LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS)
        ).count()
        
        return {
            'entrantes': {
                'total': entrantes_total,
                'atendidas': entrantes_atendidas,
                'abandonadas': entrantes_abandonadas,
                'nivel_atencion': round((entrantes_atendidas / entrantes_total * 100), 2) if entrantes_total > 0 else 0,
                'tasa_abandono': round((entrantes_abandonadas / entrantes_total * 100), 2) if entrantes_total > 0 else 0
            },
            'salientes': {
                'total': salientes_total,
                'atendidas': salientes_atendidas,
                'no_atendidas': salientes_no_atendidas,
                'nivel_atencion': round((salientes_atendidas / salientes_total * 100), 2) if salientes_total > 0 else 0,
                'tasa_no_atencion': round((salientes_no_atendidas / salientes_total * 100), 2) if salientes_total > 0 else 0
            }
        }
    
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
    
    def get_distribucion_horaria_detallada(self, filters: Dict = None) -> Dict:
        """
        Distribución horaria separando entrantes, salientes y abandonadas
        Como el gráfico "Distribución Horaria" de Power BI
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        
        # Obtener datos agrupados
        resultados = query.with_entities(
            extract('hour', LlamadaLog.time).label('hora'),
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
        
        # Agrupar por hora
        resultados = query.with_entities(
            extract('hour', LlamadaLog.time).label('hora'),
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
        Obtiene lista detallada de llamadas ABANDONADAS con paginación
        Eventos: ABANDON, ABANDON-CTOUT, ABANDONWEL
        """
        filters = filters or {}
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido')
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )
        
        query = self._apply_filters(query, filters)
        
        # Filtrar solo llamadas abandonadas
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS))
        
        # Total de registros
        total = query.count()
        
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()
        
        llamadas = []
        for r in resultados:
            llamada = r.LlamadaLog
            
            # Mapear tipo de abandono
            tipo_abandono = {
                'ABANDON': 'En Cola',
                'ABANDON-CTOUT': 'Durante Transferencia',
                'ABANDONWEL': 'En Audio Bienvenida'
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
    
    def get_llamadas_detalladas(self, filters: Dict = None, page: int = 1, per_page: int = 50) -> Dict:
        """
        Obtiene lista detallada de llamadas ATENDIDAS con paginación
        Solo eventos: COMPLETEAGENT, COMPLETEOUTNUM
        """
        filters = filters or {}
        query = self.db.query(
            LlamadaLog,
            Campana.nombre.label('campana_nombre'),
            User.first_name.label('agente_nombre'),
            User.last_name.label('agente_apellido')
        ).outerjoin(
            Campana, LlamadaLog.campana_id == Campana.id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        ).outerjoin(
            User, AgenteProfile.user_id == User.id
        )
        
        query = self._apply_filters(query, filters)
        
        # Filtrar SOLO llamadas atendidas (COMPLETEAGENT, COMPLETEOUTNUM)
        query = query.filter(LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS))
        
        # Total de registros
        total = query.count()
        
        # Paginación
        offset = (page - 1) * per_page
        resultados = query.order_by(LlamadaLog.time.desc()).offset(offset).limit(per_page).all()
        
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
        """
        filters = filters or {}
        query = self.db.query(
            Campana.nombre,
            Campana.id,
            func.count(func.distinct(AgenteProfile.id)).label('cantidad_agentes'),
            func.count(LlamadaLog.id).label('total_llamadas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
            ).label('atendidas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_NO_ATENDIDAS), 1), else_=0)
            ).label('abandonadas'),
            func.avg(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), LlamadaLog.duracion_llamada), else_=None)
            ).label('prom_duracion')
        ).join(
            LlamadaLog, Campana.id == LlamadaLog.campana_id
        ).outerjoin(
            AgenteProfile, LlamadaLog.agente_id == AgenteProfile.id
        )
        
        query = self._apply_filters(query, filters)
        
        resultados = query.group_by(Campana.nombre, Campana.id).order_by(
            func.count(LlamadaLog.id).desc()
        ).all()
        
        campanias = []
        for r in resultados:
            nivel_atencion = round((r.atendidas / r.total_llamadas * 100), 2) if r.total_llamadas > 0 else 0
            
            # Determinar estado y color según nivel
            if nivel_atencion >= 90:
                estado = 'excelente'
                color = 'green'
                alerta = False
            elif nivel_atencion >= 80:
                estado = 'bueno'
                color = 'yellow'
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
        Mejora de Power BI
        """
        filters = filters or {}
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        
        # Llamadas ENTRANTES (tipo_llamada = 1)
        entrantes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE).count()
        entrantes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        entrantes_abandonadas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_ENTRANTE,
            LlamadaLog.event.in_(self.EVENTOS_ABANDONADAS)
        ).count()
        
        # Llamadas SALIENTES (tipo_llamada = 2)
        salientes_total = query.filter(LlamadaLog.tipo_llamada == self.TIPO_SALIENTE).count()
        salientes_atendidas = query.filter(
            LlamadaLog.tipo_llamada == self.TIPO_SALIENTE,
            LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS)
        ).count()
        salientes_no_atendidas = salientes_total - salientes_atendidas
        
        return {
            'entrantes': {
                'total': entrantes_total,
                'atendidas': entrantes_atendidas,
                'abandonadas': entrantes_abandonadas,
                'nivel_atencion': round(entrantes_atendidas / entrantes_total * 100, 2) if entrantes_total > 0 else 0
            },
            'salientes': {
                'total': salientes_total,
                'atendidas': salientes_atendidas,
                'no_atendidas': salientes_no_atendidas,
                'nivel_atencion': round(salientes_atendidas / salientes_total * 100, 2) if salientes_total > 0 else 0
            }
        }


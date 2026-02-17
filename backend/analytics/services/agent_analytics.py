"""
Servicio de análisis de agentes
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import and_, case, extract, func
from sqlalchemy.orm import Session

from ..config import config
from ..models.omnileads_models import (
    ActividadAgenteLog,
    AgenteProfile,
    LlamadaLog,
    Pausa,
    User,
)

logger = logging.getLogger(__name__)


class AgentAnalyticsService:
    """Servicio para análisis de agentes"""

    # Sincronizado con CallAnalyticsService
    EVENTOS_ATENDIDAS = [
        'COMPLETEAGENT',      # Agente cuelga
        'COMPLETEOUTNUM',     # Cliente cuelga
        'COMPLETE-BTOUT',     # Transfer ciego completado
        'COMPLETE-CTOUT',     # Transfer consultivo completado
    ]

    def __init__(self, db: Session):
        self.db = db

    def get_rendimiento_agentes(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el rendimiento de cada agente.
        OPTIMIZADO: Eliminación de N+1 queries mediante batch fetching.
        """
        filters = filters or {}

        # Eventos a excluir
        EVENTOS_EXCLUIDOS = ['NONDIALPLAN', 'CONGESTION']

        # Query para obtener métricas de llamadas por agente
        query = self.db.query(
            AgenteProfile.id,
            User.first_name,
            User.last_name,
            func.count(func.distinct(LlamadaLog.callid)).label('total_llamadas'),
            func.sum(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), 1), else_=0)
            ).label('atendidas'),
            func.avg(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), LlamadaLog.duracion_llamada), else_=None)
            ).label('tmo'),
            func.avg(
                case((LlamadaLog.event.in_(self.EVENTOS_ATENDIDAS), LlamadaLog.bridge_wait_time), else_=None)
            ).label('espera_promedio')
        ).join(
            User, AgenteProfile.user_id == User.id
        ).outerjoin(
            LlamadaLog, AgenteProfile.id == LlamadaLog.agente_id
        )

        # Excluir eventos no válidos
        query = query.filter(~LlamadaLog.event.in_(EVENTOS_EXCLUIDOS))

        # Aplicar filtros de fecha
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])

        # Filtrar por campaña
        if filters.get('campana_ids'):
            query = query.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        elif filters.get('campana_id'):
            query = query.filter(LlamadaLog.campana_id == filters['campana_id'])

        # Filtrar por agente
        if filters.get('agente_ids'):
            query = query.filter(AgenteProfile.id.in_(filters['agente_ids']))
        elif filters.get('agente_id'):
            query = query.filter(AgenteProfile.id == filters['agente_id'])

        # Filtrar solo agentes activos
        query = query.filter(~AgenteProfile.borrado)

        resultados = query.group_by(
            AgenteProfile.id, User.first_name, User.last_name
        ).having(
            func.count(func.distinct(LlamadaLog.callid)) > 0
        ).all()

        # OPTIMIZACIÓN: Obtener IDs de agentes para batch fetching
        agente_ids = [r.id for r in resultados]

        if not agente_ids:
            return []

        # BATCH QUERY 1: Tiempos de pausa para TODOS los agentes
        pausas_query = self.db.query(
            ActividadAgenteLog.agente_id,
            func.count(ActividadAgenteLog.id).label('num_pausas')
        ).filter(
            ActividadAgenteLog.agente_id.in_(agente_ids),
            ActividadAgenteLog.event == 'PAUSEALL'
        )

        if filters.get('fecha_inicio'):
            pausas_query = pausas_query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            pausas_query = pausas_query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        pausas_resultados = pausas_query.group_by(ActividadAgenteLog.agente_id).all()

        # Crear diccionario para lookup O(1)
        pausas_dict = {p.agente_id: p.num_pausas * 300 for p in pausas_resultados}

        # BATCH QUERY 2: Estados de TODOS los agentes (última actividad)
        # Usar subquery con MAX para obtener última actividad por agente
        ultima_actividad_subq = self.db.query(
            ActividadAgenteLog.agente_id,
            func.max(ActividadAgenteLog.time).label('ultimo_tiempo')
        ).filter(
            ActividadAgenteLog.agente_id.in_(agente_ids)
        ).group_by(ActividadAgenteLog.agente_id).subquery()

        # Join para obtener el evento de la última actividad
        ultimas_actividades = self.db.query(
            ActividadAgenteLog.agente_id,
            ActividadAgenteLog.event,
            ActividadAgenteLog.time
        ).join(
            ultima_actividad_subq,
            and_(
                ActividadAgenteLog.agente_id == ultima_actividad_subq.c.agente_id,
                ActividadAgenteLog.time == ultima_actividad_subq.c.ultimo_tiempo
            )
        ).all()

        # Procesar estados en diccionario
        estados_dict = {}
        ahora = datetime.now(tz=ultimas_actividades[0].time.tzinfo) if ultimas_actividades else datetime.now()
        for activity in ultimas_actividades:
            if (ahora - activity.time).total_seconds() > 3600:
                estado = 'offline'
            elif activity.event == 'ADDMEMBER':
                estado = 'disponible'
            elif activity.event == 'PAUSEALL':
                estado = 'pausa'
            elif activity.event == 'REMOVEMEMBER':
                estado = 'offline'
            else:
                estado = 'disponible'
            estados_dict[activity.agente_id] = estado

        # Construir lista de agentes usando datos pre-cargados (NO MÁS QUERIES!)
        agentes = []
        for r in resultados:
            total = r.total_llamadas or 0
            atendidas = r.atendidas or 0
            no_atendidas = total - atendidas

            # Lookup O(1) desde diccionarios pre-cargados
            tiempo_pausa = pausas_dict.get(r.id, 0)
            estado = estados_dict.get(r.id, 'offline')

            agentes.append({
                'id': r.id,
                'nombre': f'{r.first_name} {r.last_name}',
                'total_llamadas': total,
                'atendidas': atendidas,
                'no_atendidas': no_atendidas,
                'tmo': int(r.tmo) if r.tmo else 0,
                'espera_promedio': int(r.espera_promedio) if r.espera_promedio else 0,
                'tiempo_pausa': tiempo_pausa,
                'tasa_atencion': round(atendidas / total * 100, 2) if total > 0 else 0,
                'estado': estado
            })

        # Ordenar por total de llamadas
        agentes.sort(key=lambda x: x['total_llamadas'], reverse=True)

        return agentes

    def _get_tiempo_pausa_agente(self, agente_id: int, filters: Dict) -> int:
        """Calcula el tiempo total en pausa de un agente"""
        query = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id,
            ActividadAgenteLog.event == 'PAUSEALL'
        )

        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            # Usar <= para incluir todo el día final (fecha_fin ya viene con 23:59:59.999999 desde el frontend)
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        pausas = query.all()

        # Simplificado: contar eventos de pausa * 300 segundos promedio
        return len(pausas) * 300

    def _get_estado_agente(self, agente_id: int) -> str:
        """Obtiene el estado actual del agente"""
        # Buscar la última actividad
        ultima_actividad = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id
        ).order_by(ActividadAgenteLog.time.desc()).first()

        if not ultima_actividad:
            return 'offline'

        # Verificar si fue hace menos de 1 hora
        ahora = datetime.now(tz=ultima_actividad.time.tzinfo)
        if (ahora - ultima_actividad.time).total_seconds() > 3600:
            return 'offline'

        # Determinar estado basado en evento
        if ultima_actividad.event == 'ADDMEMBER':
            return 'disponible'
        elif ultima_actividad.event == 'PAUSEALL':
            return 'pausa'
        elif ultima_actividad.event == 'REMOVEMEMBER':
            return 'offline'

        return 'disponible'

    def get_ocupacion_agentes(self, filters: Dict = None) -> Dict:
        """
        Obtiene la ocupación de agentes (tiempo en llamadas vs disponible)
        """
        filters = filters or {}

        # Obtener todos los agentes activos
        agentes = self.get_rendimiento_agentes(filters)

        if not agentes:
            return {
                'labels': [],
                'datasets': [
                    {'label': 'En Llamada', 'data': []},
                    {'label': 'Disponible', 'data': []},
                    {'label': 'Pausa', 'data': []}
                ]
            }

        # Tomar top 10 agentes por llamadas
        top_agentes = agentes[:10]

        labels = [a['nombre'] for a in top_agentes]
        tiempo_llamada = []
        tiempo_disponible = []
        tiempo_pausa = []

        for agente in top_agentes:
            # Tiempo en llamadas (TMO * llamadas atendidas)
            t_llamada = (agente['tmo'] * agente['atendidas']) / 60  # En minutos
            t_pausa = agente['tiempo_pausa'] / 60  # En minutos

            # Asumiendo 8 horas de trabajo = 480 minutos
            t_total = 480
            t_disponible = max(0, t_total - t_llamada - t_pausa)

            tiempo_llamada.append(round(t_llamada, 2))
            tiempo_pausa.append(round(t_pausa, 2))
            tiempo_disponible.append(round(t_disponible, 2))

        return {
            'labels': labels,
            'datasets': [
                {
                    'label': 'En Llamada',
                    'data': tiempo_llamada,
                    'backgroundColor': 'rgba(26, 115, 232, 0.8)'
                },
                {
                    'label': 'Pausa',
                    'data': tiempo_pausa,
                    'backgroundColor': 'rgba(234, 134, 0, 0.8)'
                },
                {
                    'label': 'Disponible',
                    'data': tiempo_disponible,
                    'backgroundColor': 'rgba(52, 168, 83, 0.8)'
                }
            ]
        }

    def get_timeline_agente(self, agente_id: int, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el timeline de actividad de un agente.
        OPTIMIZADO: Eliminación de N+1 query mediante batch fetching de pausas.
        """
        filters = filters or {}

        # Obtener actividades del agente
        query = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id
        )

        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            # Usar <= para incluir todo el día final (fecha_fin ya viene con 23:59:59.999999 desde el frontend)
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        actividades = query.order_by(ActividadAgenteLog.time).all()

        # OPTIMIZACIÓN: Batch fetch de todas las pausas necesarias
        pausas_ids = set()
        for act in actividades:
            if act.pausa_id and str(act.pausa_id).isdigit():
                pausas_ids.add(int(act.pausa_id))

        # Una sola query para todas las pausas
        pausas_dict = {}
        if pausas_ids:
            pausas = self.db.query(Pausa).filter(Pausa.id.in_(pausas_ids)).all()
            pausas_dict = {str(p.id): p.nombre for p in pausas}

        # Construir timeline sin queries adicionales
        timeline = []
        for act in actividades:
            # Lookup O(1) desde diccionario pre-cargado
            pausa_nombre = pausas_dict.get(act.pausa_id) if act.pausa_id else None

            # Mapear evento a descripción
            evento_map = {
                'ADDMEMBER': 'Ingreso al sistema',
                'REMOVEMEMBER': 'Salida del sistema',
                'PAUSEALL': f'En pausa: {pausa_nombre or "Sin especificar"}',
                'UNPAUSEALL': 'Fin de pausa'
            }

            timeline.append({
                'tiempo': act.time.strftime('%H:%M:%S'),
                'evento': evento_map.get(act.event, act.event),
                'tipo': act.event
            })

        return timeline

    def get_distribucion_pausas(self, filters: Dict = None) -> Dict:
        """
        Obtiene la distribución de pausas por tipo
        """
        filters = filters or {}

        query = self.db.query(
            Pausa.nombre,
            Pausa.tipo,
            func.count(ActividadAgenteLog.id).label('total')
        ).join(
            ActividadAgenteLog,
            and_(
                Pausa.id == ActividadAgenteLog.pausa_id,
                ActividadAgenteLog.event == 'PAUSEALL'
            )
        )

        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            # Usar <= para incluir todo el día final (fecha_fin ya viene con 23:59:59.999999 desde el frontend)
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        query = query.filter(~Pausa.eliminada)

        resultados = query.group_by(Pausa.nombre, Pausa.tipo).order_by(
            func.count(ActividadAgenteLog.id).desc()
        ).all()

        return {
            'labels': [r.nombre for r in resultados],
            'data': [r.total for r in resultados],
            'tipos': [r.tipo for r in resultados]
        }

    def get_disponibilidad_agentes(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene reporte de disponibilidad de agentes con métricas de llamadas y actividad.
        OPTIMIZADO: Eliminación COMPLETA de N+1 queries mediante batch fetching masivo.
        """
        from sqlalchemy import and_, func

        filters = filters or {}

        # Constantes para eventos de llamadas atendidas
        EVENTOS_ATENDIDAS = ['COMPLETEAGENT', 'COMPLETEOUTNUM', 'COMPLETE-BTOUT', 'COMPLETE-CTOUT']

        # Eventos a excluir del conteo
        EVENTOS_EXCLUIDOS = ['NONDIALPLAN', 'CONGESTION']

        # Obtener agentes con llamadas en el período
        subquery_agentes = self.db.query(
            LlamadaLog.agente_id,
            func.count(func.distinct(LlamadaLog.callid)).label('total_llamadas')
        ).filter(
            LlamadaLog.agente_id.isnot(None),
            ~LlamadaLog.event.in_(EVENTOS_EXCLUIDOS)
        )

        if filters.get('fecha_inicio'):
            subquery_agentes = subquery_agentes.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            subquery_agentes = subquery_agentes.filter(LlamadaLog.time <= filters['fecha_fin'])

        # Filtrar por campaña si se especifica
        if filters.get('campana_ids'):
            subquery_agentes = subquery_agentes.filter(
                LlamadaLog.campana_id.in_(filters['campana_ids'])
            )
        elif filters.get('campana_id'):
            subquery_agentes = subquery_agentes.filter(
                LlamadaLog.campana_id == filters['campana_id']
            )

        # Filtrar por agente si se especifica
        if filters.get('agente_ids'):
            subquery_agentes = subquery_agentes.filter(
                LlamadaLog.agente_id.in_(filters['agente_ids'])
            )
        elif filters.get('agente_id'):
            subquery_agentes = subquery_agentes.filter(
                LlamadaLog.agente_id == filters['agente_id']
            )

        # Obtener agentes con llamadas, ordenados por cantidad
        agentes_con_llamadas = subquery_agentes.group_by(
            LlamadaLog.agente_id
        ).order_by(
            func.count(func.distinct(LlamadaLog.callid)).desc()
        ).all()

        if not agentes_con_llamadas:
            return []

        agentes_ids = [ag.agente_id for ag in agentes_con_llamadas]

        # Obtener información básica de agentes
        agentes_info = self.db.query(
            AgenteProfile.id,
            User.first_name,
            User.last_name
        ).join(
            User, AgenteProfile.user_id == User.id
        ).filter(
            AgenteProfile.id.in_(agentes_ids)
        ).all()

        agentes_dict = {
            ag.id: {
                'agente_id': ag.id,
                'nombre': f'{ag.first_name} {ag.last_name}',
                'llamadas_contestadas': 0,
                'num_sesiones': 0,
                'tiempo_total_sesion': 0,
                'tiempo_promedio_sesion': 0,
                'tiempo_al_habla': 0,
                'num_pausas': 0,
                'tiempo_pausa_recreativa': 0,
                'tiempo_pausa_productiva': 0,
                'tiempo_total_pausa': 0,
                'tiempo_promedio_pausa': 0,
                'ocupacion': 0,
                'primer_login': '-',
                'ultimo_logout': '-'
            }
            for ag in agentes_info
        }

        # ========================================================================
        # OPTIMIZACIÓN 1: BATCH QUERY - Métricas de llamadas para TODOS los agentes
        # ========================================================================
        metricas_batch_query = self.db.query(
            LlamadaLog.agente_id,
            func.count(func.distinct(LlamadaLog.callid)).label('llamadas_atendidas'),
            func.sum(LlamadaLog.duracion_llamada).label('tiempo_al_habla')
        ).filter(
            LlamadaLog.agente_id.in_(agentes_ids),
            LlamadaLog.event.in_(EVENTOS_ATENDIDAS),
            LlamadaLog.duracion_llamada.isnot(None)
        )

        if filters.get('fecha_inicio'):
            metricas_batch_query = metricas_batch_query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            metricas_batch_query = metricas_batch_query.filter(LlamadaLog.time <= filters['fecha_fin'])

        # Aplicar filtro de campaña también a métricas
        if filters.get('campana_ids'):
            metricas_batch_query = metricas_batch_query.filter(
                LlamadaLog.campana_id.in_(filters['campana_ids'])
            )
        elif filters.get('campana_id'):
            metricas_batch_query = metricas_batch_query.filter(
                LlamadaLog.campana_id == filters['campana_id']
            )

        metricas_batch = metricas_batch_query.group_by(LlamadaLog.agente_id).all()

        # Crear diccionario para lookup O(1)
        metricas_dict = {
            m.agente_id: {
                'llamadas_atendidas': m.llamadas_atendidas or 0,
                'tiempo_al_habla': int(m.tiempo_al_habla or 0)
            }
            for m in metricas_batch
        }

        # ========================================================================
        # OPTIMIZACIÓN 2: BATCH QUERY - Actividades de TODOS los agentes
        # ========================================================================
        actividades_batch_query = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id.in_(agentes_ids)
        )

        if filters.get('fecha_inicio'):
            actividades_batch_query = actividades_batch_query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            actividades_batch_query = actividades_batch_query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])

        actividades_batch = actividades_batch_query.order_by(ActividadAgenteLog.time).all()

        # Agrupar actividades por agente_id
        actividades_por_agente = {}
        for act in actividades_batch:
            if act.agente_id not in actividades_por_agente:
                actividades_por_agente[act.agente_id] = []
            actividades_por_agente[act.agente_id].append(act)

        # ========================================================================
        # OPTIMIZACIÓN 3: BATCH QUERY - Tipos de pausas de TODAS las actividades
        # ========================================================================
        all_pausa_ids = set()
        for acts in actividades_por_agente.values():
            for act in acts:
                if act.event == 'PAUSEALL' and act.pausa_id and str(act.pausa_id).isdigit():
                    all_pausa_ids.add(int(act.pausa_id))

        # Una sola query para TODOS los tipos de pausas
        pausas_dict = {}
        if all_pausa_ids:
            pausas_all = self.db.query(Pausa).filter(Pausa.id.in_(all_pausa_ids)).all()
            pausas_dict = {str(p.id): p.tipo for p in pausas_all}

        # ========================================================================
        # PROCESAMIENTO: Ahora el loop NO ejecuta queries, solo procesa datos
        # ========================================================================
        for agente_id in agentes_ids:
            if agente_id not in agentes_dict:
                continue

            # Lookup O(1) de métricas pre-cargadas
            metricas = metricas_dict.get(agente_id, {'llamadas_atendidas': 0, 'tiempo_al_habla': 0})

            # Lookup O(1) de actividades pre-cargadas
            actividades = actividades_por_agente.get(agente_id, [])

            # Calcular sesiones y pausas (sin queries adicionales)
            num_sesiones = 0
            tiempo_total_sesion = 0
            num_pausas = 0
            tiempo_pausas_recreativas = 0
            tiempo_pausas_productivas = 0
            primer_login = None
            ultimo_logout = None

            tiempo_login = None
            tiempo_pausa_inicio = None
            pausa_id_actual = None

            for actividad in actividades:
                if actividad.event == 'ADDMEMBER':
                    tiempo_login = actividad.time
                    num_sesiones += 1
                    if primer_login is None:
                        primer_login = actividad.time
                elif actividad.event == 'REMOVEMEMBER':
                    ultimo_logout = actividad.time
                    if tiempo_login:
                        duracion_sesion = (actividad.time - tiempo_login).total_seconds()
                        tiempo_total_sesion += duracion_sesion
                        tiempo_login = None
                elif actividad.event == 'PAUSEALL':
                    tiempo_pausa_inicio = actividad.time
                    pausa_id_actual = actividad.pausa_id
                    num_pausas += 1
                elif actividad.event == 'UNPAUSEALL' and tiempo_pausa_inicio:
                    duracion_pausa = (actividad.time - tiempo_pausa_inicio).total_seconds()

                    # Lookup O(1) del tipo de pausa desde diccionario pre-cargado
                    if pausa_id_actual and pausa_id_actual in pausas_dict:
                        if pausas_dict[pausa_id_actual] == 'R':
                            tiempo_pausas_recreativas += duracion_pausa
                        else:
                            tiempo_pausas_productivas += duracion_pausa
                    else:
                        # Si no se encuentra el tipo, asumirlo como productiva
                        tiempo_pausas_productivas += duracion_pausa

                    tiempo_pausa_inicio = None
                    pausa_id_actual = None

            # Calcular totales y promedios
            tiempo_total_pausas = tiempo_pausas_recreativas + tiempo_pausas_productivas
            tiempo_promedio_sesion = int(tiempo_total_sesion / num_sesiones) if num_sesiones > 0 else 0
            tiempo_promedio_pausa = int(tiempo_total_pausas / num_pausas) if num_pausas > 0 else 0

            tiempo_al_habla = metricas['tiempo_al_habla']
            tiempo_disponible = tiempo_total_sesion - tiempo_pausas_recreativas
            ocupacion = round((tiempo_al_habla / tiempo_disponible * 100), 1) if tiempo_disponible > 0 else 0
            ocupacion = min(ocupacion, 100)  # No puede ser mayor a 100%

            # Convertir timestamps a timezone local
            agentes_dict[agente_id].update({
                'llamadas_contestadas': metricas['llamadas_atendidas'],
                'num_sesiones': num_sesiones,
                'tiempo_total_sesion': int(tiempo_total_sesion),
                'tiempo_promedio_sesion': tiempo_promedio_sesion,
                'tiempo_al_habla': tiempo_al_habla,
                'num_pausas': num_pausas,
                'tiempo_pausa_recreativa': int(tiempo_pausas_recreativas),
                'tiempo_pausa_productiva': int(tiempo_pausas_productivas),
                'tiempo_total_pausa': int(tiempo_total_pausas),
                'tiempo_promedio_pausa': tiempo_promedio_pausa,
                'ocupacion': ocupacion,
                'primer_login': primer_login.strftime('%H:%M:%S') if primer_login else '-',
                'ultimo_logout': ultimo_logout.strftime('%H:%M:%S') if ultimo_logout else '-'
            })

        # Retornar solo agentes con llamadas
        resultado = [datos for datos in agentes_dict.values() if datos['llamadas_contestadas'] > 0]
        resultado.sort(key=lambda x: x['llamadas_contestadas'], reverse=True)

        return resultado

    def get_detalle_sesiones_agente(self, agente_id: int, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el detalle de todas las sesiones de un agente específico.
        """
        filters = filters or {}

        logger.info(f"get_detalle_sesiones_agente - agente_id={agente_id}, filters={filters}")

        # Obtener TODAS las actividades del agente (sin filtro de fecha en SQL)
        actividades = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id
        ).order_by(ActividadAgenteLog.time).all()

        logger.info(f"Total actividades encontradas: {len(actividades)}")

        sesiones = []
        tiempo_login = None
        sesiones_totales = 0
        sesiones_filtradas = 0

        for actividad in actividades:
            if actividad.event == 'ADDMEMBER':
                tiempo_login = actividad.time
            elif actividad.event == 'REMOVEMEMBER' and tiempo_login:
                sesiones_totales += 1
                duracion_segundos = (actividad.time - tiempo_login).total_seconds()

                # Aplicar filtros de fecha DESPUÉS de emparejar
                # Comparar como naive (strip tz) para evitar error
                incluir_sesion = True
                if filters.get('fecha_inicio') and filters.get('fecha_fin'):
                    t_logout = actividad.time.replace(tzinfo=None)
                    t_login = tiempo_login.replace(tzinfo=None)
                    if t_logout < filters['fecha_inicio'] or t_login > filters['fecha_fin']:
                        incluir_sesion = False

                if incluir_sesion:
                    sesiones_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    sesiones.append({
                        'fecha_inicio': tiempo_login.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': actividad.time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })

                tiempo_login = None

        logger.info(f"Sesiones totales encontradas: {sesiones_totales}, después de filtros: {sesiones_filtradas}")
        return sesiones

    def get_detalle_pausas_agente(self, agente_id: int, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el detalle de todas las pausas de un agente específico.
        """
        filters = filters or {}

        logger.info(f"get_detalle_pausas_agente - agente_id={agente_id}, filters={filters}")

        # Obtener TODAS las actividades del agente (sin filtro de fecha en SQL)
        actividades = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id
        ).order_by(ActividadAgenteLog.time).all()

        logger.info(f"Total actividades encontradas: {len(actividades)}")

        # Obtener tipos de pausas
        pausas_ids = [
            int(act.pausa_id) for act in actividades
            if act.event == 'PAUSEALL' and act.pausa_id and act.pausa_id.isdigit()
        ]
        pausas_dict = {}
        if pausas_ids:
            pausas_agente = self.db.query(Pausa).filter(Pausa.id.in_(pausas_ids)).all()
            pausas_dict = {str(p.id): {'tipo': p.tipo, 'nombre': p.nombre} for p in pausas_agente}

        # Agregar pausa ACW (After Call Work) para ID 0
        pausas_dict['0'] = {'tipo': 'P', 'nombre': 'ACW (After Call Work)'}

        pausas = []
        tiempo_pausa_inicio = None
        pausa_id_actual = None
        pausas_totales = 0
        pausas_filtradas = 0

        for actividad in actividades:
            if actividad.event == 'PAUSEALL':
                tiempo_pausa_inicio = actividad.time
                pausa_id_actual = actividad.pausa_id
            elif actividad.event == 'UNPAUSEALL' and tiempo_pausa_inicio:
                pausas_totales += 1
                duracion_segundos = (actividad.time - tiempo_pausa_inicio).total_seconds()

                # Aplicar filtros de fecha DESPUÉS de emparejar
                # Comparar como naive (strip tz) para evitar error
                incluir_pausa = True
                if filters.get('fecha_inicio') and filters.get('fecha_fin'):
                    t_fin = actividad.time.replace(tzinfo=None)
                    t_ini = tiempo_pausa_inicio.replace(tzinfo=None)
                    if t_fin < filters['fecha_inicio'] or t_ini > filters['fecha_fin']:
                        incluir_pausa = False

                if incluir_pausa:
                    pausas_filtradas += 1
                    horas = int(duracion_segundos // 3600)
                    minutos = int((duracion_segundos % 3600) // 60)
                    segundos = int(duracion_segundos % 60)

                    pausa_info = pausas_dict.get(pausa_id_actual, {'tipo': 'P', 'nombre': 'Otra'})

                    pausas.append({
                        'tipo': pausa_info['tipo'],
                        'nombre': pausa_info['nombre'],
                        'fecha_inicio': tiempo_pausa_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                        'fecha_fin': actividad.time.strftime('%Y-%m-%d %H:%M:%S'),
                        'duracion': f'{horas:02d}:{minutos:02d}:{segundos:02d}',
                        'duracion_segundos': int(duracion_segundos)
                    })

                tiempo_pausa_inicio = None
                pausa_id_actual = None

        logger.info(f"Pausas totales encontradas: {pausas_totales}, después de filtros: {pausas_filtradas}")
        return pausas


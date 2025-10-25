"""
Servicio de análisis de agentes
"""
from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, extract
from ..models.omnileads_models import (
    ActividadAgenteLog, LlamadaLog, AgenteProfile, User, Pausa
)


class AgentAnalyticsService:
    """Servicio para análisis de agentes"""
    
    EVENTOS_ATENDIDAS = ['CONNECT', 'COMPLETEAGENT']
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_rendimiento_agentes(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene el rendimiento de cada agente
        """
        filters = filters or {}
        
        # Query para obtener métricas de llamadas por agente
        query = self.db.query(
            AgenteProfile.id,
            User.first_name,
            User.last_name,
            func.count(LlamadaLog.id).label('total_llamadas'),
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
        
        # Aplicar filtros de fecha
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            fecha_fin = filters['fecha_fin'] + timedelta(days=1)
            query = query.filter(LlamadaLog.time < fecha_fin)
        
        # Filtrar solo agentes activos
        query = query.filter(AgenteProfile.borrado == False)
        
        resultados = query.group_by(
            AgenteProfile.id, User.first_name, User.last_name
        ).having(
            func.count(LlamadaLog.id) > 0
        ).all()
        
        agentes = []
        for r in resultados:
            total = r.total_llamadas or 0
            atendidas = r.atendidas or 0
            no_atendidas = total - atendidas
            
            # Calcular tiempo en pausa
            tiempo_pausa = self._get_tiempo_pausa_agente(r.id, filters)
            
            # Estado del agente (simplificado)
            estado = self._get_estado_agente(r.id)
            
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
            fecha_fin = filters['fecha_fin'] + timedelta(days=1)
            query = query.filter(ActividadAgenteLog.time < fecha_fin)
        
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
        ahora = datetime.now()
        if (ahora - ultima_actividad.time.replace(tzinfo=None)).seconds > 3600:
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
        Obtiene el timeline de actividad de un agente
        """
        filters = filters or {}
        
        # Obtener actividades del agente
        query = self.db.query(ActividadAgenteLog).filter(
            ActividadAgenteLog.agente_id == agente_id
        )
        
        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            fecha_fin = filters['fecha_fin'] + timedelta(days=1)
            query = query.filter(ActividadAgenteLog.time < fecha_fin)
        
        actividades = query.order_by(ActividadAgenteLog.time).all()
        
        timeline = []
        for act in actividades:
            # Obtener nombre de pausa si aplica
            pausa_nombre = None
            if act.pausa_id:
                pausa = self.db.query(Pausa).filter(Pausa.id == act.pausa_id).first()
                pausa_nombre = pausa.nombre if pausa else None
            
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
            fecha_fin = filters['fecha_fin'] + timedelta(days=1)
            query = query.filter(ActividadAgenteLog.time < fecha_fin)
        
        query = query.filter(Pausa.eliminada == False)
        
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
        Obtiene reporte detallado de disponibilidad de agentes (OPTIMIZADO)
        Incluye: sesiones, tiempo al habla, pausas, ocupación, TMO, tasa de atención
        """
        from datetime import timezone as dt_timezone
        from sqlalchemy import distinct
        
        filters = filters or {}
        
        # Constantes para eventos de llamadas atendidas
        EVENTOS_ATENDIDAS = ['COMPLETEAGENT', 'COMPLETEOUTNUM', 'COMPLETE-BTOUT', 'COMPLETE-CTOUT', 'COMPLETE-CT']
        
        # PASO 1: Obtener solo agentes que tuvieron actividad en el período
        actividad_query = self.db.query(distinct(ActividadAgenteLog.agente_id))
        
        if filters.get('fecha_inicio'):
            actividad_query = actividad_query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            actividad_query = actividad_query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])
        
        agentes_activos_ids = [r[0] for r in actividad_query.all()]
        
        if not agentes_activos_ids:
            return []
        
        # PASO 2: Obtener información básica de agentes
        agentes_info = self.db.query(
            AgenteProfile.id,
            User.username,
            User.first_name,
            User.last_name
        ).join(
            User, AgenteProfile.user_id == User.id
        ).filter(
            AgenteProfile.id.in_(agentes_activos_ids)
        ).all()
        
        agentes_dict = {
            ag.id: {
                'agente_id': ag.id,
                'username': ag.username,
                'nombre': f'{ag.first_name} {ag.last_name}'
            }
            for ag in agentes_info
        }
        
        # PASO 3: Calcular métricas de actividad por agente
        for agente_id in agentes_activos_ids:
            # Obtener todas las actividades del agente en el período
            actividad_query = self.db.query(ActividadAgenteLog).filter(
                ActividadAgenteLog.agente_id == agente_id
            )
            
            if filters.get('fecha_inicio'):
                actividad_query = actividad_query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                actividad_query = actividad_query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])
            
            actividades = actividad_query.order_by(ActividadAgenteLog.time).all()
            
            # Variables para calcular métricas
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
                    
                    # Verificar tipo de pausa
                    if pausa_id_actual and pausa_id_actual.isdigit():
                        pausa = self.db.query(Pausa).filter(Pausa.id == int(pausa_id_actual)).first()
                        if pausa:
                            if pausa.tipo == 'R':
                                tiempo_pausas_recreativas += duracion_pausa
                            else:
                                tiempo_pausas_productivas += duracion_pausa
                    
                    tiempo_pausa_inicio = None
                    pausa_id_actual = None
            
            # Cerrar sesión abierta si hay una al final del período
            if tiempo_login is not None and filters.get('fecha_fin'):
                fecha_fin = filters['fecha_fin']
                # Asegurar que ambas fechas sean aware o naive
                if tiempo_login.tzinfo is None and hasattr(fecha_fin, 'tzinfo') and fecha_fin.tzinfo is not None:
                    from datetime import timezone
                    tiempo_login = tiempo_login.replace(tzinfo=timezone.utc)
                elif tiempo_login.tzinfo is not None and (not hasattr(fecha_fin, 'tzinfo') or fecha_fin.tzinfo is None):
                    tiempo_login = tiempo_login.replace(tzinfo=None)
                    
                duracion_sesion = (fecha_fin - tiempo_login).total_seconds()
                tiempo_total_sesion += duracion_sesion
            
            # Guardar métricas de actividad
            agentes_dict[agente_id].update({
                'num_sesiones': num_sesiones,
                'tiempo_total_sesion': int(tiempo_total_sesion),
                'num_pausas': num_pausas,
                'tiempo_pausa_recreativa': int(tiempo_pausas_recreativas),
                'tiempo_pausa_productiva': int(tiempo_pausas_productivas),
                'primer_login': primer_login.strftime('%H:%M:%S') if primer_login else '-',
                'ultimo_logout': ultimo_logout.strftime('%H:%M:%S') if ultimo_logout else '-'
            })
        
        # PASO 4: Calcular métricas de llamadas usando agregaciones SQL
        for agente_id in agentes_activos_ids:
            # Subquery para obtener últimas llamadas únicas
            subquery_llamadas = self.db.query(
                LlamadaLog.callid,
                func.max(LlamadaLog.time).label('ultimo_tiempo')
            ).filter(
                LlamadaLog.agente_id == agente_id
            )
            
            if filters.get('fecha_inicio'):
                subquery_llamadas = subquery_llamadas.filter(LlamadaLog.time >= filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                subquery_llamadas = subquery_llamadas.filter(LlamadaLog.time <= filters['fecha_fin'])
            
            subquery_llamadas = subquery_llamadas.group_by(LlamadaLog.callid).subquery()
            
            # Query de llamadas únicas del agente
            llamadas_unicas = self.db.query(LlamadaLog).join(
                subquery_llamadas,
                and_(
                    LlamadaLog.callid == subquery_llamadas.c.callid,
                    LlamadaLog.time == subquery_llamadas.c.ultimo_tiempo
                )
            )
            
            total_llamadas = llamadas_unicas.count()
            
            # Llamadas atendidas
            llamadas_atendidas_query = llamadas_unicas.filter(
                LlamadaLog.event.in_(EVENTOS_ATENDIDAS)
            )
            
            llamadas_atendidas = llamadas_atendidas_query.count()
            
            # Métricas agregadas de llamadas atendidas
            metricas = llamadas_atendidas_query.filter(
                LlamadaLog.duracion_llamada.isnot(None),
                LlamadaLog.bridge_wait_time.isnot(None)
            ).with_entities(
                func.sum(LlamadaLog.duracion_llamada).label('tiempo_al_habla'),
                func.avg(LlamadaLog.duracion_llamada).label('tmo'),
                func.sum(LlamadaLog.bridge_wait_time).label('tiempo_total_espera')
            ).first()
            
            tiempo_al_habla = int(metricas.tiempo_al_habla or 0)
            tmo = int(metricas.tmo or 0)
            tiempo_total_espera = int(metricas.tiempo_total_espera or 0)
            
            # Calcular métricas derivadas
            tiempo_promedio_sesion = agentes_dict[agente_id]['tiempo_total_sesion'] / agentes_dict[agente_id]['num_sesiones'] if agentes_dict[agente_id]['num_sesiones'] > 0 else 0
            
            tiempo_total_pausas = agentes_dict[agente_id]['tiempo_pausa_recreativa'] + agentes_dict[agente_id]['tiempo_pausa_productiva']
            tiempo_promedio_pausa = tiempo_total_pausas / agentes_dict[agente_id]['num_pausas'] if agentes_dict[agente_id]['num_pausas'] > 0 else 0
            
            # Ocupación: tiempo al habla / (tiempo de sesión - pausas recreativas) * 100
            tiempo_disponible = agentes_dict[agente_id]['tiempo_total_sesion'] - agentes_dict[agente_id]['tiempo_pausa_recreativa']
            ocupacion = (tiempo_al_habla / tiempo_disponible * 100) if tiempo_disponible > 0 else 0
            ocupacion = min(ocupacion, 100)
            
            # Tasa de atención
            tasa_atencion = (llamadas_atendidas / total_llamadas * 100) if total_llamadas > 0 else 0
            
            # Actualizar con métricas de llamadas
            agentes_dict[agente_id].update({
                'tiempo_promedio_sesion': int(tiempo_promedio_sesion),
                'tiempo_al_habla': tiempo_al_habla,
                'tiempo_total_espera': tiempo_total_espera,
                'tiempo_promedio_pausa': int(tiempo_promedio_pausa),
                'ocupacion': round(ocupacion, 2),
                'tmo': tmo,
                'llamadas_contestadas': llamadas_atendidas,
                'total_llamadas': total_llamadas,
                'tasa_atencion': round(tasa_atencion, 2)
            })
        
        # Convertir a lista y ordenar por nombre
        resultado = list(agentes_dict.values())
        resultado.sort(key=lambda x: x['nombre'])
        
        return resultado


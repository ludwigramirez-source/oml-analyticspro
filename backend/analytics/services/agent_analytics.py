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

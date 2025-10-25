"""
Servicio de analytics de agentes usando caché local MongoDB
Ultra rápido al consultar datos locales indexados
"""
from datetime import datetime, timezone
from typing import Dict, List
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger(__name__)


class AgentAnalyticsLocalService:
    """Servicio de analytics usando datos locales de MongoDB"""
    
    def __init__(self, mongo_db: AsyncIOMotorDatabase):
        self.mongo = mongo_db
        
        # Constantes para eventos
        self.EVENTOS_ATENDIDAS = [
            'COMPLETEAGENT', 'COMPLETEOUTNUM', 'COMPLETE-BTOUT', 
            'COMPLETE-CTOUT', 'COMPLETE-CT'
        ]
    
    async def get_disponibilidad_agentes(self, filters: Dict = None) -> List[Dict]:
        """
        Obtiene disponibilidad de agentes desde MongoDB local
        ULTRA RÁPIDO - sin consultas a PostgreSQL
        """
        filters = filters or {}
        fecha_inicio = filters.get('fecha_inicio')
        fecha_fin = filters.get('fecha_fin')
        
        logger.info(f"📊 Generando reporte desde MongoDB local: {fecha_inicio} - {fecha_fin}")
        
        # Obtener agentes
        agentes = []
        async for ag in self.mongo.agentes_local.find():
            agentes.append(ag)
        
        if not agentes:
            return []
        
        # Obtener pausas para clasificarlas
        pausas_dict = {}
        async for pausa in self.mongo.pausas_local.find():
            pausas_dict[str(pausa['id'])] = pausa['tipo']
        
        resultado = []
        
        for agente in agentes:
            agente_id = agente['id']
            
            # Filtro de query para actividades
            actividad_filter = {'agente_id': agente_id}
            if fecha_inicio:
                actividad_filter['time'] = {'$gte': fecha_inicio}
            if fecha_fin:
                if 'time' in actividad_filter:
                    actividad_filter['time']['$lte'] = fecha_fin
                else:
                    actividad_filter['time'] = {'$lte': fecha_fin}
            
            # Obtener actividades del agente
            actividades = []
            async for act in self.mongo.actividades_agente_local.find(
                actividad_filter
            ).sort('time', 1):
                actividades.append(act)
            
            # Procesar métricas de actividad
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
                if actividad['event'] == 'ADDMEMBER':
                    tiempo_login = actividad['time']
                    num_sesiones += 1
                    if primer_login is None:
                        primer_login = actividad['time']
                elif actividad['event'] == 'REMOVEMEMBER':
                    ultimo_logout = actividad['time']
                    if tiempo_login:
                        duracion = (actividad['time'] - tiempo_login).total_seconds()
                        tiempo_total_sesion += duracion
                        tiempo_login = None
                elif actividad['event'] == 'PAUSEALL':
                    tiempo_pausa_inicio = actividad['time']
                    pausa_id_actual = actividad.get('pausa_id')
                    num_pausas += 1
                elif actividad['event'] == 'UNPAUSEALL' and tiempo_pausa_inicio:
                    duracion_pausa = (actividad['time'] - tiempo_pausa_inicio).total_seconds()
                    
                    # Clasificar pausa
                    if pausa_id_actual and pausa_id_actual in pausas_dict:
                        if pausas_dict[pausa_id_actual] == 'R':
                            tiempo_pausas_recreativas += duracion_pausa
                        else:
                            tiempo_pausas_productivas += duracion_pausa
                    
                    tiempo_pausa_inicio = None
                    pausa_id_actual = None
            
            # Cerrar sesión abierta
            if tiempo_login and fecha_fin:
                duracion = (fecha_fin - tiempo_login).total_seconds()
                tiempo_total_sesion += duracion
            
            # Filtro para llamadas
            llamada_filter = {'agente_id': agente_id}
            if fecha_inicio:
                llamada_filter['time'] = {'$gte': fecha_inicio}
            if fecha_fin:
                if 'time' in llamada_filter:
                    llamada_filter['time']['$lte'] = fecha_fin
                else:
                    llamada_filter['time'] = {'$lte': fecha_fin}
            
            # Obtener llamadas únicas (por callid)
            pipeline = [
                {'$match': llamada_filter},
                {'$sort': {'time': -1}},
                {'$group': {
                    '_id': '$callid',
                    'evento': {'$first': '$event'},
                    'duracion': {'$first': '$duracion_llamada'},
                    'espera': {'$first': '$bridge_wait_time'}
                }}
            ]
            
            llamadas_unicas = []
            async for ll in self.mongo.llamadas_local.aggregate(pipeline):
                llamadas_unicas.append(ll)
            
            total_llamadas = len(llamadas_unicas)
            
            # Llamadas atendidas
            llamadas_atendidas = [
                ll for ll in llamadas_unicas 
                if ll['evento'] in self.EVENTOS_ATENDIDAS
            ]
            
            num_llamadas_atendidas = len(llamadas_atendidas)
            
            # Métricas de llamadas
            tiempo_al_habla = sum([
                ll['duracion'] for ll in llamadas_atendidas 
                if ll['duracion']
            ])
            
            tiempo_total_espera = sum([
                ll['espera'] for ll in llamadas_atendidas 
                if ll['espera']
            ])
            
            tmo = int(tiempo_al_habla / num_llamadas_atendidas) if num_llamadas_atendidas > 0 else 0
            
            # Calcular métricas derivadas
            tiempo_promedio_sesion = int(tiempo_total_sesion / num_sesiones) if num_sesiones > 0 else 0
            tiempo_total_pausas = tiempo_pausas_recreativas + tiempo_pausas_productivas
            tiempo_promedio_pausa = int(tiempo_total_pausas / num_pausas) if num_pausas > 0 else 0
            
            # Ocupación
            tiempo_disponible = tiempo_total_sesion - tiempo_pausas_recreativas
            ocupacion = (tiempo_al_habla / tiempo_disponible * 100) if tiempo_disponible > 0 else 0
            ocupacion = min(ocupacion, 100)
            
            # Tasa de atención
            tasa_atencion = (num_llamadas_atendidas / total_llamadas * 100) if total_llamadas > 0 else 0
            
            # Solo agregar si tiene actividad
            if num_sesiones > 0 or total_llamadas > 0:
                resultado.append({
                    'agente_id': agente_id,
                    'nombre': f"{agente['first_name']} {agente['last_name']}",
                    'username': agente['username'],
                    'num_sesiones': num_sesiones,
                    'primer_login': primer_login.strftime('%H:%M:%S') if primer_login else '-',
                    'ultimo_logout': ultimo_logout.strftime('%H:%M:%S') if ultimo_logout else '-',
                    'tiempo_total_sesion': int(tiempo_total_sesion),
                    'tiempo_promedio_sesion': tiempo_promedio_sesion,
                    'tiempo_al_habla': int(tiempo_al_habla),
                    'num_pausas': num_pausas,
                    'tiempo_pausa_recreativa': int(tiempo_pausas_recreativas),
                    'tiempo_pausa_productiva': int(tiempo_pausas_productivas),
                    'tiempo_promedio_pausa': tiempo_promedio_pausa,
                    'tiempo_total_espera': int(tiempo_total_espera),
                    'ocupacion': round(ocupacion, 2),
                    'tmo': tmo,
                    'llamadas_contestadas': num_llamadas_atendidas,
                    'total_llamadas': total_llamadas,
                    'tasa_atencion': round(tasa_atencion, 2)
                })
        
        # Ordenar por nombre
        resultado.sort(key=lambda x: x['nombre'])
        
        logger.info(f"✅ Reporte generado: {len(resultado)} agentes")
        return resultado

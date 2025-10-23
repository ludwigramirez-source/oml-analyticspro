"""
Extensión del servicio de análisis de llamadas
Métodos adicionales para reportes premium
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case, extract, distinct
from ..models.omnileads_models import LlamadaLog, Campana, AgenteProfile, User, ActividadAgenteLog, Pausa


class CallAnalyticsExtended:
    """Servicio extendido para reportes premium"""
    
    # Eventos de llamadas salientes
    EVENTOS_SALIENTES = {
        'DIAL': 'Marcación iniciada',
        'ANSWER': 'Llamada contestada',
        'NOANSWER': 'No contestada',
        'BUSY': 'Ocupado',
        'CANCEL': 'Cancelada',
        'CONGESTION': 'Congestión',
        'CHANUNAVAIL': 'Canal no disponible'
    }
    
    # Eventos de transferencias
    EVENTOS_TRANSFERENCIAS = {
        'CT-TRY': 'Intento transfer consultivo',
        'CT-ANSWER': 'Transfer consultivo atendido',
        'CT-BUSY': 'Transfer consultivo ocupado',
        'CT-DISCARD': 'Transfer consultivo descartado',
        'BTOUT-TRY': 'Intento transfer ciego',
        'BTOUT-ANSWER': 'Transfer ciego atendido',
        'COMPLETE-CTOUT': 'Completado transfer consultivo',
        'COMPLETE-BTOUT': 'Completado transfer ciego'
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _apply_filters(self, query, filters: Dict):
        """Aplica filtros comunes a las consultas"""
        if not filters:
            return query
        
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])
        
        if filters.get('campana_id'):
            query = query.filter(LlamadaLog.campana_id == filters['campana_id'])
        
        if filters.get('agente_id'):
            query = query.filter(LlamadaLog.agente_id == filters['agente_id'])
        
        return query
    
    # ==================== DISTRIBUCIÓN AVANZADA ====================
    
    def get_distribucion_por_campana(self, filters: Dict = None) -> List[Dict]:
        """
        Distribución de llamadas por campaña (Pie Chart)
        Retorna nombre, total y porcentaje por campaña
        """
        filters = filters or {}
        
        query = self.db.query(
            Campana.nombre,
            func.count(LlamadaLog.id).label('total')
        ).join(
            LlamadaLog, Campana.id == LlamadaLog.campana_id
        )
        
        query = self._apply_filters(query, filters)
        
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
        0=Lunes, 6=Domingo
        """
        filters = filters or {}
        
        query = self.db.query(
            extract('dow', LlamadaLog.time).label('dia_semana'),
            func.count(LlamadaLog.id).label('total')
        )
        
        query = self._apply_filters(query, filters)
        
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
        
        query = self.db.query(
            extract('month', LlamadaLog.time).label('mes'),
            func.count(LlamadaLog.id).label('total')
        )
        
        if anio:
            query = query.filter(extract('year', LlamadaLog.time) == anio)
        
        query = self._apply_filters(query, filters)
        
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
        
        query = self.db.query(
            extract('hour', LlamadaLog.time).label('hora'),
            func.count(LlamadaLog.id).label('total')
        )
        
        query = self._apply_filters(query, filters)
        
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
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.time).label('ultimo_tiempo')
        ).filter(
            LlamadaLog.tipo_llamada == 1  # Salientes = 1
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
        
        # Query principal: unir para obtener el evento final de cada llamada
        query = self.db.query(LlamadaLog).join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.time == subquery.c.ultimo_tiempo
            )
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
            LlamadaLog.event.in_(['CONGESTION', 'NONDIALPLAN', 'CHANUNAVAIL'])
        ).count()
        
        # Transferencias y otros
        otros = query.filter(
            LlamadaLog.event.in_(['BT-TRY', 'BT-BUSY', 'CAMPT-COMPLETE', 'CAMPT-TRY'])
        ).count()
        
        # Calcular tasa de contactación
        tasa_contactacion = round(contestadas / total_llamadas * 100, 2) if total_llamadas > 0 else 0
        
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
        
        eventos_no_conexion = [
            'ABANDON',
            'ABANDONWEL',
            'ABANDON-CTOUT',
            'EXITWITHTIMEOUT',
            'CONGESTION',
            'NONDIALPLAN',
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
            'CONGESTION': 'Congestión',
            'NONDIALPLAN': 'Sin ruta',
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
        
        query = self.db.query(
            extract('dow', ActividadAgenteLog.time).label('dia'),
            extract('hour', ActividadAgenteLog.time).label('hora'),
            func.count(distinct(ActividadAgenteLog.agente_id)).label('num_agentes')
        )
        
        if filters.get('fecha_inicio'):
            query = query.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(ActividadAgenteLog.time <= filters['fecha_fin'])
        
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
        Análisis completo de transferencias (funnel)
        Eventos: CT-TRY, CT-ANSWER, BTOUT-TRY, BTOUT-ANSWER, etc.
        """
        filters = filters or {}
        
        query = self.db.query(LlamadaLog)
        query = self._apply_filters(query, filters)
        
        # Contar por tipo de evento de transferencia
        metricas = {}
        for evento, descripcion in self.EVENTOS_TRANSFERENCIAS.items():
            count = query.filter(LlamadaLog.event == evento).count()
            metricas[evento] = {
                'descripcion': descripcion,
                'total': count
            }
        
        # Calcular métricas de funnel
        ct_intentos = metricas.get('CT-TRY', {}).get('total', 0)
        ct_exitosos = metricas.get('CT-ANSWER', {}).get('total', 0)
        bt_intentos = metricas.get('BTOUT-TRY', {}).get('total', 0)
        bt_exitosos = metricas.get('BTOUT-ANSWER', {}).get('total', 0)
        
        return {
            'eventos': metricas,
            'resumen': {
                'transfer_consultivo': {
                    'intentos': ct_intentos,
                    'exitosos': ct_exitosos,
                    'tasa_exito': round(ct_exitosos / ct_intentos * 100, 2) if ct_intentos > 0 else 0
                },
                'transfer_ciego': {
                    'intentos': bt_intentos,
                    'exitosos': bt_exitosos,
                    'tasa_exito': round(bt_exitosos / bt_intentos * 100, 2) if bt_intentos > 0 else 0
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
            LlamadaLog.event.in_(['COMPLETEAGENT', 'COMPLETEOUTNUM'])
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
        
        # Definir eventos
        eventos_atendidas = ['COMPLETEAGENT', 'COMPLETEOUTNUM']
        eventos_abandonadas = ['ABANDON', 'ABANDONWEL', 'EXITWITHTIMEOUT']
        eventos_transferencias = ['COMPLETE-CTOUT', 'COMPLETE-BTOUT', 'CT-ANSWER', 'BTOUT-ANSWER']
        
        # Base query con subquery para obtener última ocurrencia de cada llamada
        subquery = self.db.query(
            LlamadaLog.callid,
            func.max(LlamadaLog.time).label('ultimo_tiempo')
        ).filter(
            LlamadaLog.tipo_llamada == 3  # Solo entrantes
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
        
        # Query principal uniendo con última ocurrencia
        base_query = self.db.query(LlamadaLog).join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.time == subquery.c.ultimo_tiempo
            )
        )
        
        # Determinar campo de agrupación
        if agrupar_por == 'hora':
            group_field = extract('hour', LlamadaLog.time)
            group_label = 'hora'
        elif agrupar_por == 'semana':
            # Semana del mes (1-5)
            group_field = func.ceil(extract('day', LlamadaLog.time) / 7.0)
            group_label = 'semana'
        elif agrupar_por == 'mes':
            group_field = extract('month', LlamadaLog.time)
            group_label = 'mes'
        elif agrupar_por == 'campana':
            # Para campaña necesitamos join
            base_query = base_query.join(Campana, LlamadaLog.campana_id == Campana.id)
            group_field = Campana.nombre
            group_label = 'campana'
        else:
            group_field = extract('hour', LlamadaLog.time)
            group_label = 'hora'
        
        # Consulta agregada
        query = self.db.query(
            group_field.label('grupo'),
            func.count(LlamadaLog.id).label('total_llamadas'),
            func.sum(case((LlamadaLog.event.in_(eventos_atendidas), 1), else_=0)).label('atendidas'),
            func.sum(case((LlamadaLog.event.in_(eventos_abandonadas), 1), else_=0)).label('abandonadas'),
            func.sum(case((LlamadaLog.event.in_(eventos_transferencias), 1), else_=0)).label('transferidas'),
            func.avg(case((LlamadaLog.event.in_(eventos_atendidas), LlamadaLog.bridge_wait_time), else_=None)).label('tiempo_espera_promedio'),
            func.avg(case((LlamadaLog.event.in_(eventos_abandonadas), LlamadaLog.duracion_llamada), else_=None)).label('tiempo_abandono_promedio'),
            func.avg(case((LlamadaLog.event.in_(eventos_atendidas), LlamadaLog.duracion_llamada), else_=None)).label('duracion_promedio')
        ).select_from(LlamadaLog)
        
        # Aplicar join si es por campaña
        if agrupar_por == 'campana':
            query = query.join(Campana, LlamadaLog.campana_id == Campana.id)
        
        # Aplicar filtros adicionales
        query = query.join(
            subquery,
            and_(
                LlamadaLog.callid == subquery.c.callid,
                LlamadaLog.time == subquery.c.ultimo_tiempo
            )
        ).filter(LlamadaLog.tipo_llamada == 3)
        
        if filters.get('fecha_inicio'):
            query = query.filter(LlamadaLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query = query.filter(LlamadaLog.time <= filters['fecha_fin'])
        if filters.get('campana_ids'):
            query = query.filter(LlamadaLog.campana_id.in_(filters['campana_ids']))
        if filters.get('agente_ids'):
            query = query.filter(LlamadaLog.agente_id.in_(filters['agente_ids']))
        
        query = query.group_by(group_field)
        
        resultados = query.all()
        
        # Formatear resultados
        datos = []
        for r in resultados:
            grupo_valor = r.grupo
            
            # Formatear etiqueta según el tipo de agrupación
            if agrupar_por == 'hora':
                label = f"{int(grupo_valor):02d}:00 - {int(grupo_valor):02d}:59"
            elif agrupar_por == 'mes':
                meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
                label = meses[int(grupo_valor) - 1] if 1 <= int(grupo_valor) <= 12 else str(grupo_valor)
            elif agrupar_por == 'dia_semana':
                dias = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']
                label = dias[int(grupo_valor)] if 0 <= int(grupo_valor) <= 6 else str(grupo_valor)
            else:  # campaña
                label = str(grupo_valor)
            
            total = r.total_llamadas or 0
            atendidas = r.atendidas or 0
            abandonadas = r.abandonadas or 0
            transferidas = r.transferidas or 0
            
            datos.append({
                'grupo': label,
                'total_llamadas': total,
                'atendidas': atendidas,
                'abandonadas': abandonadas,
                'transferidas': transferidas,
                'porcentaje_atendidas': round((atendidas / total * 100), 2) if total > 0 else 0,
                'porcentaje_abandonadas': round((abandonadas / total * 100), 2) if total > 0 else 0,
                'tiempo_espera_promedio': round(r.tiempo_espera_promedio or 0, 2),
                'tiempo_abandono_promedio': round(r.tiempo_abandono_promedio or 0, 2),
                'duracion_promedio': round(r.duracion_promedio or 0, 2)
            })
        
        # Ordenar según tipo de agrupación
        if agrupar_por == 'hora':
            datos.sort(key=lambda x: int(x['grupo'].split(':')[0]))
        elif agrupar_por == 'mes':
            meses_orden = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            datos.sort(key=lambda x: meses_orden.index(x['grupo']) if x['grupo'] in meses_orden else 99)
        elif agrupar_por == 'dia_semana':
            dias_orden = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
            datos.sort(key=lambda x: dias_orden.index(x['grupo']) if x['grupo'] in dias_orden else 99)
        else:  # campaña - ordenar por total descendente
            datos.sort(key=lambda x: x['total_llamadas'], reverse=True)
        
        return datos


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
        Métricas: DIAL, ANSWER, NOANSWER, BUSY, CANCEL, tasa de contactación
        """
        filters = filters or {}
        
        query = self.db.query(LlamadaLog)
        query = query.filter(LlamadaLog.tipo_llamada == 2)  # Salientes
        query = self._apply_filters(query, filters)
        
        # Contar por evento
        eventos = {}
        for evento, descripcion in self.EVENTOS_SALIENTES.items():
            count = query.filter(LlamadaLog.event == evento).count()
            eventos[evento] = {
                'descripcion': descripcion,
                'total': count
            }
        
        # Calcular métricas
        total_marcadas = eventos.get('DIAL', {}).get('total', 0)
        total_contestadas = eventos.get('ANSWER', {}).get('total', 0)
        
        tasa_contactacion = round(total_contestadas / total_marcadas * 100, 2) if total_marcadas > 0 else 0
        
        return {
            'eventos': eventos,
            'metricas': {
                'total_marcadas': total_marcadas,
                'total_contestadas': total_contestadas,
                'total_no_contestadas': eventos.get('NOANSWER', {}).get('total', 0),
                'total_ocupadas': eventos.get('BUSY', {}).get('total', 0),
                'total_canceladas': eventos.get('CANCEL', {}).get('total', 0),
                'tasa_contactacion': tasa_contactacion
            }
        }
    
    def get_llamadas_manuales_vs_dialer(self, filters: Dict = None) -> Dict:
        """
        Comparativa de llamadas manuales vs dialer
        """
        filters = filters or {}
        
        query = self.db.query(LlamadaLog)
        query = query.filter(LlamadaLog.tipo_llamada == 2)  # Salientes
        query = self._apply_filters(query, filters)
        
        # Obtener todas las llamadas con información de campaña
        llamadas = query.join(Campana, LlamadaLog.campana_id == Campana.id).all()
        
        # Clasificar (esto depende de cómo OmniLeads distingue manual vs dialer)
        # Por ahora, asumiré que hay un campo en Campana que indica el tipo
        manuales = 0
        dialer = 0
        
        for llamada in llamadas:
            # Aquí necesitaríamos la lógica real para distinguir
            # Por ahora, voy a usar un placeholder
            manuales += 1  # Placeholder
        
        return {
            'manuales': {
                'total': manuales,
                'porcentaje': round(manuales / len(llamadas) * 100, 2) if len(llamadas) > 0 else 0
            },
            'dialer': {
                'total': dialer,
                'porcentaje': round(dialer / len(llamadas) * 100, 2) if len(llamadas) > 0 else 0
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
        Métricas globales: N° agentes, tiempo promedio, min, max, total
        """
        filters = filters or {}
        
        query = self.db.query(
            ActividadAgenteLog.agente_id,
            func.sum(ActividadAgenteLog.tiempo_sesion).label('tiempo_total')
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
                'tiempo_promedio': 0,
                'tiempo_minimo': 0,
                'tiempo_maximo': 0,
                'tiempo_total': 0
            }
        
        tiempos = [r.tiempo_total for r in resultados if r.tiempo_total]
        
        return {
            'total_agentes': len(resultados),
            'tiempo_promedio': round(sum(tiempos) / len(tiempos) if tiempos else 0, 2),
            'tiempo_minimo': min(tiempos) if tiempos else 0,
            'tiempo_maximo': max(tiempos) if tiempos else 0,
            'tiempo_total': sum(tiempos) if tiempos else 0
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
        Incluye: tiempo en pausas, número de pausas, ocupación
        """
        filters = filters or {}
        
        # Query principal de actividad
        query_actividad = self.db.query(
            AgenteProfile.id,
            User.first_name,
            User.last_name,
            func.sum(ActividadAgenteLog.tiempo_sesion).label('tiempo_sesion'),
            func.count(ActividadAgenteLog.id).label('num_sesiones')
        ).join(
            ActividadAgenteLog, AgenteProfile.id == ActividadAgenteLog.agente_id
        ).join(
            User, AgenteProfile.user_id == User.id
        )
        
        if filters.get('fecha_inicio'):
            query_actividad = query_actividad.filter(ActividadAgenteLog.time >= filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            query_actividad = query_actividad.filter(ActividadAgenteLog.time <= filters['fecha_fin'])
        
        resultados = query_actividad.group_by(
            AgenteProfile.id, User.first_name, User.last_name
        ).all()
        
        # Por cada agente, obtener métricas adicionales
        agentes_metricas = []
        
        for r in resultados:
            # Tiempo en llamadas
            llamadas_query = self.db.query(
                func.sum(LlamadaLog.duracion_llamada).label('tiempo_llamadas')
            ).filter(
                LlamadaLog.agente_id == r.id
            )
            
            if filters.get('fecha_inicio'):
                llamadas_query = llamadas_query.filter(LlamadaLog.time >= filters['fecha_inicio'])
            if filters.get('fecha_fin'):
                llamadas_query = llamadas_query.filter(LlamadaLog.time <= filters['fecha_fin'])
            
            tiempo_llamadas = llamadas_query.scalar() or 0
            
            # Calcular ocupación
            ocupacion = round(tiempo_llamadas / r.tiempo_sesion * 100, 2) if r.tiempo_sesion > 0 else 0
            
            agentes_metricas.append({
                'agente': f'{r.first_name} {r.last_name}',
                'tiempo_sesion': r.tiempo_sesion,
                'num_sesiones': r.num_sesiones,
                'tiempo_llamadas': tiempo_llamadas,
                'ocupacion': ocupacion,
                'promedio_sesion': round(r.tiempo_sesion / r.num_sesiones, 2) if r.num_sesiones > 0 else 0
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

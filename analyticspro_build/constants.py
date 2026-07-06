"""
Constantes centralizadas para OmniLeads Analytics Pro.
Fuente única de verdad para clasificación de eventos y tipos de llamada.
"""

# ============================================================================
# MODO: SOLO ENTRANTES
# Cuando True, TODAS las queries excluyen salientes (tipo_llamada=1).
# Poner False para restaurar análisis entrantes+salientes.
# ============================================================================
INBOUND_ONLY_MODE = True

# ============================================================================
# EVENTOS DE LLAMADAS - Clasificación OmniLeads
# ============================================================================

# Eventos que indican llamadas ATENDIDAS (conectadas con agente)
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
# NOTA: NONDIALPLAN y CONGESTION excluidos - no son llamadas reales.
EVENTOS_NO_ATENDIDAS = [
    'NOANSWER',           # No contesta (saliente)
    'CANCEL',             # Cancelada (saliente)
    'CHANUNAVAIL',        # Canal no disponible
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
    'CAMPT-TRY',          # Intento de transfer de campaña
    'CAMPT-COMPLETE',     # Transfer de campaña completado
    'CTOUT-TRY',          # Intento de transfer consultivo
]

# Eventos EXCLUIDOS de todo conteo - no son llamadas reales
EVENTOS_EXCLUIDOS = [
    'NONDIALPLAN',        # Click2call sin ruta válida
    'CONGESTION',         # Congestión de red (nunca conectó)
]

# EVENTOS FINALES: Solo estos cuentan como "llamadas" en los totales
EVENTOS_FINALES = (
    EVENTOS_ATENDIDAS
    + EVENTOS_ABANDONADAS
    + EVENTOS_NO_ATENDIDAS
)

# ============================================================================
# TIPOS DE LLAMADA
# ============================================================================

TIPO_SALIENTE = 1      # Llamadas manuales salientes
TIPO_DIALER = 2        # Llamadas automáticas del marcador predictivo (dialer)
TIPO_ENTRANTE = 3      # Llamadas entrantes (inbound)

# Tipos activos según modo (usado en queries de filtrado)
TIPOS_LLAMADA_ACTIVOS = (
    [TIPO_ENTRANTE] if INBOUND_ONLY_MODE
    else [TIPO_ENTRANTE, TIPO_SALIENTE]
)

# ============================================================================
# UMBRALES ESTÁNDAR DE LA INDUSTRIA
# ============================================================================

SLA_THRESHOLD_60 = 60  # Nivel de servicio < 60 segundos
SLA_THRESHOLD_20 = 20  # Nivel de servicio < 20 segundos
ABANDONMENT_THRESHOLD = 0.05  # 5% tasa de abandono aceptable
NIVEL_ATENCION_CRITICO = 80  # Nivel de atención crítico < 80%

# ============================================================================
# EVENTOS ESPECIALES (solo usados por call_analytics_extended)
# ============================================================================

# Eventos de llamadas salientes
EVENTOS_SALIENTES = {
    'DIAL': 'Marcación iniciada',
    'ANSWER': 'Llamada contestada',
    'NOANSWER': 'No contestada',
    'BUSY': 'Ocupado',
    'CANCEL': 'Cancelada',
    'CONGESTION': 'Congestión',
    'CHANUNAVAIL': 'Canal no disponible',
}

# Eventos de transferencias (nombres reales de OmniLeads)
EVENTOS_TRANSFERENCIAS = {
    # Transfer Ciego (Blind Transfer Out)
    'BTOUT-TRY': 'Intento de transfer ciego',
    'BTOUT-ANSWER': 'Transfer ciego atendido',
    'BTOUT-NONDIALPLAN': 'Transfer ciego - sin ruta',
    'BTOUT-CONGESTION': 'Transfer ciego - congestión',
    'COMPLETE-BTOUT': 'Llamada completada vía transfer ciego',
    # Transfer Consultivo (Consultive Transfer Out)
    'CTOUT-TRY': 'Intento de transfer consultivo',
    'CTOUT-ANSWER': 'Transfer consultivo atendido',
    'CTOUT-NONDIALPLAN': 'Transfer consultivo - sin ruta',
    'CTOUT-DISCARD': 'Transfer consultivo descartado',
    'COMPLETE-CTOUT': 'Llamada completada vía transfer consultivo',
    # Transfer de Campaña
    'CAMPT-TRY': 'Intento de transfer a campaña',
    'CAMPT-COMPLETE': 'Transfer a campaña completado',
    'COMPLETE-CAMPT': 'Llamada completada vía transfer campaña',
    # Cola
    'ENTERQUEUE-TRANSFER': 'Llamada ingresó a cola por transferencia',
}

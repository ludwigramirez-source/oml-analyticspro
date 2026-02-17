/**
 * Servicio API para Analytics OmniLeads
 */

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:81';

class AnalyticsAPI {
  /**
   * Construye query string con filtros
   */
  buildQueryString(filters = {}) {
    const params = new URLSearchParams();

    if (filters.fecha_inicio) {
      params.append('fecha_inicio', filters.fecha_inicio);
    }
    if (filters.fecha_fin) {
      params.append('fecha_fin', filters.fecha_fin);
    }
    // Soportar campana_ids (múltiples) y campana_id (único)
    // campana_ids puede ser array [1,2,3] o string "1,2,3"
    if (filters.campana_ids && filters.campana_ids.length > 0) {
      const ids = Array.isArray(filters.campana_ids)
        ? filters.campana_ids.join(',')
        : filters.campana_ids;
      if (ids) params.append('campana_ids', ids);
    } else if (filters.campana_id) {
      params.append('campana_id', filters.campana_id);
    }
    if (filters.tipo_campana) {
      params.append('tipo_campana', filters.tipo_campana);
    }
    // Soportar agente_ids (múltiples) y agente_id (único)
    // agente_ids puede ser array [1,2,3] o string "1,2,3"
    if (filters.agente_ids && filters.agente_ids.length > 0) {
      const ids = Array.isArray(filters.agente_ids)
        ? filters.agente_ids.join(',')
        : filters.agente_ids;
      if (ids) params.append('agente_ids', ids);
    } else if (filters.agente_id) {
      params.append('agente_id', filters.agente_id);
    }
    // Tipo de llamada (entrantes/salientes)
    if (filters.tipo_llamada) {
      params.append('tipo_llamada', filters.tipo_llamada);
    }

    return params.toString();
  }

  /**
   * Fetch genérico con manejo de errores
   */
  async fetchData(endpoint, filters = {}) {
    try {
      const queryString = this.buildQueryString(filters);
      // Si el endpoint ya tiene parámetros (?), usar & para agregar más
      const separator = endpoint.includes('?') ? '&' : '?';
      const url = `${API_URL}/api/analytics/${endpoint}${queryString ? separator + queryString : ''}`;
      
      const response = await fetch(url);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching ${endpoint}:`, error);
      throw error;
    }
  }

  // ==================== ENDPOINTS ====================

  /**
   * Test de conexión
   */
  async testConnection() {
    return this.fetchData('test');
  }

  /**
   * Obtiene KPIs principales
   */
  async getKPIs(filters = {}) {
    return this.fetchData('kpis', filters);
  }

  /**
   * Obtiene llamadas separadas por tipo (ENTRANTES vs SALIENTES)
   */
  async getLlamadasPorTipo(filters = {}) {
    return this.fetchData('llamadas-por-tipo', filters);
  }

  /**
   * Obtiene distribución de llamadas
   */
  async getDistribucionLlamadas(filters = {}) {
    return this.fetchData('distribucion-llamadas', filters);
  }
  
  /**
   * Obtiene nivel de atención por campaña con alertas
   */
  async getNivelAtencionCampanas(filters = {}) {
    return this.fetchData('nivel-atencion-campanas', filters);
  }
  
  /**
   * Obtiene distribución horaria detallada
   */
  async getDistribucionHorariaDetallada(filters = {}) {
    return this.fetchData('distribucion-horaria-detallada', filters);
  }

  /**
   * Obtiene distribución por tipo (entrantes vs salientes)
   */
  async getDistribucionPorTipo(filters = {}) {
    return this.fetchData('distribucion-por-tipo', filters);
  }

  /**
   * Obtiene evolución por hora
   */
  async getEvolucionHora(filters = {}) {
    return this.fetchData('evolucion-hora', filters);
  }

  /**
   * Obtiene nivel de servicio
   */
  async getNivelServicio(filters = {}) {
    return this.fetchData('nivel-servicio', filters);
  }

  /**
   * Obtiene causas de no atención
   */
  async getCausasNoAtencion(filters = {}) {
    return this.fetchData('causas-no-atencion', filters);
  }

  /**
   * Obtiene llamadas ATENDIDAS detalladas
   */
  async getLlamadasAtendidas(page = 1, perPage = 50, filters = {}, sortBy = null, sortDir = 'desc') {
    let endpoint = `llamadas-atendidas?page=${page}&per_page=${perPage}`;
    if (sortBy) endpoint += `&sort_by=${sortBy}&sort_dir=${sortDir}`;
    return this.fetchData(endpoint, filters);
  }

  /**
   * Obtiene llamadas ABANDONADAS detalladas
   */
  async getLlamadasAbandonadas(page = 1, perPage = 50, filters = {}, sortBy = null, sortDir = 'desc') {
    let endpoint = `llamadas-abandonadas?page=${page}&per_page=${perPage}`;
    if (sortBy) endpoint += `&sort_by=${sortBy}&sort_dir=${sortDir}`;
    return this.fetchData(endpoint, filters);
  }

  /**
   * Obtiene llamadas detalladas (alias para atendidas)
   */
  async getLlamadasDetalladas(page = 1, perPage = 50, filters = {}) {
    return this.getLlamadasAtendidas(page, perPage, filters);
  }

  /**
   * Obtiene distribución por campañas
   */
  async getDistribucionCampanas(filters = {}) {
    return this.fetchData('distribucion-campanas', filters);
  }

  /**
   * Obtiene rendimiento de agentes (disponibilidad detallada)
   */
  async getRendimientoAgentes(filters = {}) {
    return this.fetchData('agentes/disponibilidad', filters);
  }

  /**
   * Obtiene ocupación de agentes
   */
  async getOcupacionAgentes(filters = {}) {
    return this.fetchData('agentes/ocupacion', filters);
  }

  /**
   * Obtiene distribución de pausas
   */
  async getDistribucionPausas(filters = {}) {
    return this.fetchData('pausas/distribucion', filters);
  }

  /**
   * Obtiene detalle de sesiones de un agente
   */
  async getDetalleSesionesAgente(agenteId, filters = {}) {
    return this.fetchData(`agentes/${agenteId}/sesiones`, filters);
  }

  /**
   * Obtiene detalle de pausas de un agente
   */
  async getDetallePausasAgente(agenteId, filters = {}) {
    return this.fetchData(`agentes/${agenteId}/pausas`, filters);
  }

  /**
   * Obtiene lista de campañas
   */
  async getCampanas() {
    return this.fetchData('campanas');
  }

  /**
   * Obtiene lista de agentes
   */
  async getAgentes() {
    return this.fetchData('agentes');
  }

  
  /**
   * Obtiene disponibilidad detallada de agentes
   */
  async getDisponibilidadAgentes(filters = {}) {
    return this.fetchData('agentes/disponibilidad', filters);
  }

  
  // ==================== NUEVOS ENDPOINTS PREMIUM ====================
  
  /**
   * Distribución por campaña detallada
   */
  async getDistribucionPorCampanaDetalle(filters = {}) {
    return this.fetchData('distribucion-por-campana-detalle', filters);
  }
  
  /**
   * Distribución por día de la semana
   */
  async getDistribucionPorDiaSemana(filters = {}) {
    return this.fetchData('distribucion-por-dia-semana', filters);
  }
  
  /**
   * Distribución por mes
   */
  async getDistribucionPorMes(anio = null, filters = {}) {
    const endpoint = anio ? `distribucion-por-mes?anio=${anio}` : 'distribucion-por-mes';
    return this.fetchData(endpoint, filters);
  }
  
  /**
   * Distribución por rango horario
   */
  async getDistribucionPorRangoHorario(filters = {}) {
    return this.fetchData('distribucion-por-rango-horario', filters);
  }
  
  /**
   * Evolución semanal (contestadas, abandonadas, agentes activos)
   */
  async getEvolucionSemanal(filters = {}) {
    return this.fetchData('evolucion-semanal', filters);
  }
  
  /**
   * Dashboard de llamadas salientes
   */
  async getSalientesDashboard(filters = {}) {
    return this.fetchData('salientes/dashboard', filters);
  }
  
  /**
   * Detalle paginado de llamadas salientes
   */
  async getSalientesDetalle(page = 1, perPage = 50, filters = {}, sortBy = null, sortDir = 'desc') {
    let endpoint = `salientes/detalle?page=${page}&per_page=${perPage}`;
    if (sortBy) endpoint += `&sort_by=${sortBy}&sort_dir=${sortDir}`;
    return this.fetchData(endpoint, filters);
  }

  /**
   * Llamadas manuales vs dialer
   */
  async getManualesVsDiater(filters = {}) {
    return this.fetchData('salientes/manuales-vs-dialer', filters);
  }
  
  /**
   * Causas de desconexión detalladas
   */
  async getCausasDesconexionDetalladas(filters = {}) {
    return this.fetchData('causas-desconexion-detalladas', filters);
  }
  
  /**
   * Causas de no conexión completas
   */
  async getCausasNoConexionCompletas(filters = {}) {
    return this.fetchData('causas-no-conexion-completas', filters);
  }
  
  /**
   * Llamadas sin conexión por agente
   */
  async getSinConexionPorAgente(filters = {}) {
    return this.fetchData('sin-conexion-por-agente', filters);
  }
  
  /**
   * Llamadas sin conexión por campaña
   */
  async getSinConexionPorCampana(filters = {}) {
    return this.fetchData('sin-conexion-por-campana', filters);
  }
  
  /**
   * Total de sesiones de agentes
   */
  async getTotalSesionesAgentes(filters = {}) {
    return this.fetchData('agentes/total-sesiones', filters);
  }
  
  /**
   * Disponibilidad de agentes (heatmap)
   */
  async getDisponibilidadHeatmap(filters = {}) {
    return this.fetchData('agentes/disponibilidad-heatmap', filters);
  }
  
  /**
   * Disponibilidad de agentes ampliada
   */
  async getDisponibilidadAmpliada(filters = {}) {
    return this.fetchData('agentes/disponibilidad-ampliada', filters);
  }
  
  /**
   * Análisis de transferencias
   */
  async getAnalisisTransferencias(filters = {}) {
    return this.fetchData('transferencias', filters);
  }

  /**
   * Detalle de llamadas con transferencias
   */
  async getDetalleTransferencias(filters = {}) {
    return this.fetchData('transferencias/detalle', filters);
  }
  
  /**
   * Nivel de servicio detallado
   */
  async getNivelServicioDetallado(filters = {}) {
    return this.fetchData('nivel-servicio-detallado', filters);
  }

  /**
   * Tabla de distribución horaria con métricas detalladas
   */
  async getTablaDistribucionHoraria(filters = {}, agruparPor = 'hora') {
    const queryString = this.buildQueryString(filters);
    const baseUrl = `tabla-distribucion-horaria?agrupar_por=${agruparPor}`;
    const url = queryString ? `${baseUrl}&${queryString}` : baseUrl;
    
    try {
      const fullUrl = `${API_URL}/api/analytics/${url}`;
      const response = await fetch(fullUrl);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      return await response.json();
    } catch (error) {
      console.error(`Error fetching tabla-distribucion-horaria:`, error);
      throw error;
    }
  }
  // ==================== GESTIONES ====================

  async getGestionesKpis(filters = {}) {
    return this.fetchData('gestiones/kpis', filters);
  }

  async getGestionesPorAgente(filters = {}) {
    return this.fetchData('gestiones/por-agente', filters);
  }

  async getGestionesPorCampana(filters = {}) {
    return this.fetchData('gestiones/por-campana', filters);
  }

  async getGestionesDetalle(filters = {}, page = 1, perPage = 50) {
    return this.fetchData(
      `gestiones/detalle?page=${page}&per_page=${perPage}`,
      filters
    );
  }

  async getGestionesPorDia(filters = {}) {
    return this.fetchData('gestiones/por-dia', filters);
  }

  async getGestionesPorIncidencia(filters = {}) {
    return this.fetchData('gestiones/por-incidencia', filters);
  }
}

export default new AnalyticsAPI();


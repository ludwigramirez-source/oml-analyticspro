/**
 * Servicio API para Configuración de Base de Datos
 */

const API_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

class ConfigAPI {
  /**
   * Prueba la conexión a la base de datos sin guardarla
   */
  async testConnection(config) {
    try {
      const response = await fetch(`${API_URL}/api/config/test-connection`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al probar conexión');
      }

      return await response.json();
    } catch (error) {
      console.error('Error testing connection:', error);
      throw error;
    }
  }

  /**
   * Crea y guarda una nueva configuración de base de datos
   */
  async createConfig(config) {
    try {
      const response = await fetch(`${API_URL}/api/config/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al guardar configuración');
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating config:', error);
      throw error;
    }
  }

  /**
   * Obtiene la configuración activa
   */
  async getActiveConfig() {
    try {
      const response = await fetch(`${API_URL}/api/config/active`);

      if (response.status === 404) {
        return null; // No hay configuración activa
      }

      if (!response.ok) {
        throw new Error('Error al obtener configuración activa');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting active config:', error);
      return null;
    }
  }

  /**
   * Obtiene todas las configuraciones
   */
  async getAllConfigs() {
    try {
      const response = await fetch(`${API_URL}/api/config/`);

      if (!response.ok) {
        throw new Error('Error al obtener configuraciones');
      }

      return await response.json();
    } catch (error) {
      console.error('Error getting configs:', error);
      return [];
    }
  }

  /**
   * Actualiza una configuración existente
   */
  async updateConfig(configId, updateData) {
    try {
      const response = await fetch(`${API_URL}/api/config/${configId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updateData)
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al actualizar configuración');
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating config:', error);
      throw error;
    }
  }

  /**
   * Elimina una configuración
   */
  async deleteConfig(configId) {
    try {
      const response = await fetch(`${API_URL}/api/config/${configId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al eliminar configuración');
      }

      return await response.json();
    } catch (error) {
      console.error('Error deleting config:', error);
      throw error;
    }
  }

  /**
   * Activa una configuración específica
   */
  async activateConfig(configId) {
    try {
      const response = await fetch(`${API_URL}/api/config/${configId}/activate`, {
        method: 'POST'
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error al activar configuración');
      }

      return await response.json();
    } catch (error) {
      console.error('Error activating config:', error);
      throw error;
    }
  }
}

export default new ConfigAPI();

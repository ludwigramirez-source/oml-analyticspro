import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import ApexChart from '../ApexChart';

const CausasDetalladas = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [causasDesconexion, setCausasDesconexion] = useState([]);
  const [causasNoConexion, setCausasNoConexion] = useState([]);
  const [sinConexionAgente, setSinConexionAgente] = useState([]);
  const [sinConexionCampana, setSinConexionCampana] = useState([]);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [desconexion, noConexion, porAgente, porCampana] = await Promise.all([
        analyticsApi.getCausasDesconexionDetalladas(filters).catch(() => []),
        analyticsApi.getCausasNoConexionCompletas(filters).catch(() => []),
        analyticsApi.getSinConexionPorAgente(filters).catch(() => []),
        analyticsApi.getSinConexionPorCampana(filters).catch(() => [])
      ]);

      setCausasDesconexion(preparePieData(desconexion));
      setCausasNoConexion(preparePieData(noConexion));
      setSinConexionAgente(porAgente);
      setSinConexionCampana(porCampana);
    } catch (error) {
      console.error('Error loading causas detalladas:', error);
    } finally {
      setLoading(false);
    }
  };

  const preparePieData = (data) => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data.map(item => ({
      label: item.descripcion || item.evento,
      value: item.total || 0
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">🔍 Análisis de Causas</h2>
      
      {/* Gráficos de Causas */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <ApexChart
          type="pie"
          data={causasDesconexion}
          title="Causas de Desconexión"
        />
        
        <ApexChart
          type="pie"
          data={causasNoConexion}
          title="Causas de No Conexión"
        />
      </div>

      {/* Tablas de Detalle */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sin Conexión por Agente */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">
            Sin Conexión por Agente
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">%</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sinConexionAgente.slice(0, 10).map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.agente}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.total}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.porcentaje}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sin Conexión por Campaña */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">
            Sin Conexión por Campaña
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaña</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">%</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sinConexionCampana.slice(0, 10).map((item, idx) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.campana}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.total}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{item.porcentaje}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CausasDetalladas;
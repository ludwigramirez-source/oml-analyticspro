import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';

const Transferencias = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [analisis, setAnalisis] = useState(null);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await analyticsApi.getAnalisisTransferencias(filters);
      setAnalisis(data);
    } catch (error) {
      console.error('Error loading transferencias:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!analisis) {
    return (
      <div className="text-center py-12 text-gray-500">
        No hay datos de transferencias disponibles
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">🔄 Análisis de Transferencias</h2>
      
      {/* Resumen de Transferencias */}
      {analisis.resumen && (
        <div className="mb-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Transfer Consultivo */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">
                📞 Transfer Consultivo
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <KPICard
                  title="Intentos"
                  value={analisis.resumen.transfer_consultivo.intentos}
                  icon="🔵"
                />
                <KPICard
                  title="Exitosos"
                  value={analisis.resumen.transfer_consultivo.exitosos}
                  icon="✅"
                />
              </div>
              <div className="mt-4">
                <div className="flex justify-between mb-2">
                  <span className="text-gray-700">Tasa de Éxito</span>
                  <span className="font-bold text-green-600">
                    {analisis.resumen.transfer_consultivo.tasa_exito}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-green-600 h-3 rounded-full"
                    style={{ width: `${analisis.resumen.transfer_consultivo.tasa_exito}%` }}
                  ></div>
                </div>
              </div>
            </div>

            {/* Transfer Ciego */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-bold text-gray-800 mb-4">
                ⚡ Transfer Ciego
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <KPICard
                  title="Intentos"
                  value={analisis.resumen.transfer_ciego.intentos}
                  icon="🔵"
                />
                <KPICard
                  title="Exitosos"
                  value={analisis.resumen.transfer_ciego.exitosos}
                  icon="✅"
                />
              </div>
              <div className="mt-4">
                <div className="flex justify-between mb-2">
                  <span className="text-gray-700">Tasa de Éxito</span>
                  <span className="font-bold text-green-600">
                    {analisis.resumen.transfer_ciego.tasa_exito}%
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="bg-green-600 h-3 rounded-full"
                    style={{ width: `${analisis.resumen.transfer_ciego.tasa_exito}%` }}
                  ></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detalle de Eventos */}
      {analisis.eventos && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">
            Detalle de Eventos de Transferencia
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evento</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descripción</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(analisis.eventos)
                  .filter(([evento, data]) => data.total > 0)
                  .map(([evento, data]) => (
                    <tr key={evento}>
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{evento}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{data.descripcion}</td>
                      <td className="px-4 py-3 text-sm text-gray-900">{data.total}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default Transferencias;
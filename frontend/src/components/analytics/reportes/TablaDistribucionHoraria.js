import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import * as XLSX from 'xlsx';

const TablaDistribucionHoraria = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState([]);
  const [agrupacion, setAgrupacion] = useState('hora');

  useEffect(() => {
    loadData();
  }, [filters, agrupacion]);

  const loadData = async () => {
    setLoading(true);
    try {
      const result = await analyticsApi.getTablaDistribucionHoraria(filters, agrupacion);
      setData(result || []);
    } catch (error) {
      console.error('Error loading distribución horaria:', error);
      setData([]);
    } finally {
      setLoading(false);
    }
  };

  const formatTiempo = (segundos) => {
    if (!segundos || segundos <= 0) return '0s';
    const mins = Math.floor(segundos / 60);
    const secs = Math.floor(segundos % 60);
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
  };

  const handleExportExcel = () => {
    const excelData = data.map(row => ({
      'Grupo': row.grupo,
      'Recibidas': row.total_llamadas,
      'Atendidas': row.atendidas,
      'Abandonadas': row.abandonadas,
      'Transferidas': row.transferidas,
      '% Atendidas': `${row.porcentaje_atendidas}%`,
      '% Abandonadas': `${row.porcentaje_abandonadas}%`,
      'T. Espera Prom.': formatTiempo(row.tiempo_espera_promedio),
      'T. Abandono Prom.': formatTiempo(row.tiempo_abandono_promedio),
      'Duración Prom.': formatTiempo(row.duracion_promedio)
    }));

    const ws = XLSX.utils.json_to_sheet(excelData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Distribución');
    XLSX.writeFile(wb, `distribucion_${agrupacion}_${new Date().toISOString().split('T')[0]}.xlsx`);
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
      <div className="mb-6 flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-800">📊 Distribución Horaria Detallada</h2>
        <button
          onClick={handleExportExcel}
          className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
        >
          <span>📥</span>
          Descargar Excel
        </button>
      </div>

      {/* Botones de Agrupación */}
      <div className="mb-6 flex gap-3 flex-wrap">
        <button
          onClick={() => setAgrupacion('hora')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            agrupacion === 'hora'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          🕐 Por Hora
        </button>
        <button
          onClick={() => setAgrupacion('dia_semana')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            agrupacion === 'dia_semana'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          📅 Por Día Semana
        </button>
        <button
          onClick={() => setAgrupacion('mes')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            agrupacion === 'mes'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          📆 Por Mes
        </button>
        <button
          onClick={() => setAgrupacion('campana')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            agrupacion === 'campana'
              ? 'bg-blue-600 text-white'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          }`}
        >
          📞 Por Campaña
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto bg-white rounded-lg shadow">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {agrupacion === 'hora' ? 'Hora' : 
                 agrupacion === 'dia_semana' ? 'Día' :
                 agrupacion === 'mes' ? 'Mes' : 'Campaña'}
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Recibidas
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Atendidas
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Abandonadas
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Transfer.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                % Atend.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                % Aband.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                T. Espera
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                T. Aband.
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duración
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.map((row, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {row.grupo}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                  {row.total_llamadas}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-green-600">
                  {row.atendidas}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-red-600">
                  {row.abandonadas}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-blue-600">
                  {row.transferidas}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right font-medium text-green-700">
                  {row.porcentaje_atendidas}%
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right font-medium text-red-700">
                  {row.porcentaje_abandonadas}%
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {formatTiempo(row.tiempo_espera_promedio)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {formatTiempo(row.tiempo_abandono_promedio)}
                </td>
                <td className="px-4 py-4 whitespace-nowrap text-sm text-right text-gray-600">
                  {formatTiempo(row.duracion_promedio)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay datos disponibles para los filtros seleccionados
        </div>
      )}
    </div>
  );
};

export default TablaDistribucionHoraria;

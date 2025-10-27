import React, { useState, useEffect, useMemo } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';
import { ExportButton } from '../../../utils/excelExport';

const Transferencias = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [analisis, setAnalisis] = useState(null);
  const [detalleLlamadas, setDetalleLlamadas] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dataAnalisis, dataDetalle] = await Promise.all([
        analyticsApi.getAnalisisTransferencias(filters),
        analyticsApi.getDetalleTransferencias(filters)
      ]);
      setAnalisis(dataAnalisis);
      setDetalleLlamadas(dataDetalle);
    } catch (error) {
      console.error('Error loading transferencias:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDuracion = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const getEventoBadge = (evento) => {
    const badges = {
      'BT-TRY': 'bg-blue-100 text-blue-800',
      'BT-ANSWER': 'bg-green-100 text-green-800',
      'BT-BUSY': 'bg-orange-100 text-orange-800',
      'BT-NOANSWER': 'bg-red-100 text-red-800',
      'COMPLETE-BT': 'bg-green-100 text-green-800',
      'CT-TRY': 'bg-purple-100 text-purple-800',
      'CT-ANSWER': 'bg-green-100 text-green-800',
      'CT-CANCEL': 'bg-yellow-100 text-yellow-800',
      'COMPLETE-CT': 'bg-green-100 text-green-800',
      'ENTERQUEUE-TRANSFER': 'bg-indigo-100 text-indigo-800'
    };
    return badges[evento] || 'bg-gray-100 text-gray-800';
  };

  // Paginación
  const totalPages = Math.ceil((detalleLlamadas?.length || 0) / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return detalleLlamadas?.slice(start, end) || [];
  }, [detalleLlamadas, currentPage, pageSize]);

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    setCurrentPage(1);
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
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">🔄 Análisis de Transferencias</h2>
        {analisis.eventos && (
          <ExportButton 
            data={Object.entries(analisis.eventos)
              .filter(([_, data]) => data.total > 0)
              .map(([evento, data]) => ({
                'Evento': evento,
                'Descripción': data.descripcion,
                'Total': data.total
              }))} 
            filename="transferencias_detalle"
            label="Exportar Detalle"
          />
        )}
      </div>
      
      {/* KPIs Generales */}
      {analisis.resumen?.totales && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <KPICard
            title="Total Intentos"
            value={analisis.resumen.totales.total_intentos}
            icon="📤"
            bgColor="bg-blue-50"
          />
          <KPICard
            title="Total Exitosas"
            value={analisis.resumen.totales.total_exitosas}
            icon="✅"
            bgColor="bg-green-50"
          />
          <KPICard
            title="Tasa de Éxito Global"
            value={`${analisis.resumen.totales.tasa_exito_global}%`}
            icon="📊"
            bgColor="bg-purple-50"
          />
          <KPICard
            title="Ingresos a Cola"
            value={analisis.resumen.totales.ingresos_cola}
            icon="⏳"
            bgColor="bg-yellow-50"
          />
        </div>
      )}
      
      {/* Resumen por Tipo de Transferencia */}
      {analisis.resumen && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Transfer Ciego */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <span className="mr-2">⚡</span>
              Transfer Ciego (Blind Transfer)
            </h3>
            
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-blue-50 p-3 rounded">
                <div className="text-xs text-gray-600">Intentos</div>
                <div className="text-2xl font-bold text-blue-600">{analisis.resumen.transfer_ciego.intentos}</div>
              </div>
              <div className="bg-green-50 p-3 rounded">
                <div className="text-xs text-gray-600">Completados</div>
                <div className="text-2xl font-bold text-green-600">{analisis.resumen.transfer_ciego.completados}</div>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Atendidos</span>
                <span className="font-medium">{analisis.resumen.transfer_ciego.atendidos}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Ocupados</span>
                <span className="font-medium text-orange-600">{analisis.resumen.transfer_ciego.ocupados}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Sin respuesta</span>
                <span className="font-medium text-red-600">{analisis.resumen.transfer_ciego.sin_respuesta}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">No disponible</span>
                <span className="font-medium text-red-600">{analisis.resumen.transfer_ciego.no_disponible}</span>
              </div>
            </div>
            
            <div className="pt-3 border-t">
              <div className="flex justify-between mb-2">
                <span className="text-gray-700 font-medium">Tasa de Éxito</span>
                <span className="font-bold text-green-600 text-lg">
                  {analisis.resumen.transfer_ciego.tasa_exito}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-green-600 h-3 rounded-full transition-all"
                  style={{ width: `${analisis.resumen.transfer_ciego.tasa_exito}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* Transfer Consultivo */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <span className="mr-2">📞</span>
              Transfer Consultivo (Consultive Transfer)
            </h3>
            
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div className="bg-blue-50 p-3 rounded">
                <div className="text-xs text-gray-600">Intentos</div>
                <div className="text-2xl font-bold text-blue-600">{analisis.resumen.transfer_consultivo.intentos}</div>
              </div>
              <div className="bg-green-50 p-3 rounded">
                <div className="text-xs text-gray-600">Completados</div>
                <div className="text-2xl font-bold text-green-600">{analisis.resumen.transfer_consultivo.completados}</div>
              </div>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Atendidos</span>
                <span className="font-medium">{analisis.resumen.transfer_consultivo.atendidos}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Cancelados</span>
                <span className="font-medium text-orange-600">{analisis.resumen.transfer_consultivo.cancelados}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Ocupados</span>
                <span className="font-medium text-red-600">{analisis.resumen.transfer_consultivo.ocupados}</span>
              </div>
            </div>
            
            <div className="pt-3 border-t">
              <div className="flex justify-between mb-2">
                <span className="text-gray-700 font-medium">Tasa de Éxito</span>
                <span className="font-bold text-green-600 text-lg">
                  {analisis.resumen.transfer_consultivo.tasa_exito}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-green-600 h-3 rounded-full transition-all"
                  style={{ width: `${analisis.resumen.transfer_consultivo.tasa_exito}%` }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Detalle de Eventos */}
      {analisis.eventos && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-bold text-gray-800 mb-4">
            📋 Detalle de Eventos de Transferencia
          </h3>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evento</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Descripción</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(analisis.eventos)
                  .filter(([_, data]) => data.total > 0)
                  .sort(([_, a], [__, b]) => b.total - a.total)
                  .map(([evento, data]) => (
                    <tr key={evento} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-blue-600 font-medium">{evento}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">{data.descripcion}</td>
                      <td className="px-4 py-3 text-sm text-center font-bold text-gray-900">{data.total}</td>
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
import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';
import ApexChart from '../ApexChart';
import Pagination from '../Pagination';
import { ExportButtonAsync } from '../../../utils/excelExport';
import { formatDuracion } from '../../../utils/formatters';

const LlamadasSalientes = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);
  // Detalle paginado server-side
  const [detalle, setDetalle] = useState({ data: [], total: 0, page: 1, total_pages: 0 });
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  const [pageSize, setPageSize] = useState(25);
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('desc');

  useEffect(() => {
    loadData();
    loadPageDetalle(1, pageSize);
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const dashboardData = await analyticsApi.getSalientesDashboard(filters).catch(() => null);
      setDashboard(dashboardData);
    } catch (error) {
      console.error('Error loading llamadas salientes:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadPageDetalle = async (page, perPage, sortBy = null, sortDir = 'desc') => {
    setLoadingDetalle(true);
    try {
      const data = await analyticsApi.getSalientesDetalle(page, perPage, filters, sortBy, sortDir);
      setDetalle(data || { data: [], total: 0, page: 1, total_pages: 0 });
    } catch (error) {
      console.error('Error loading detalle salientes:', error);
    } finally {
      setLoadingDetalle(false);
    }
  };

  // Fetch ALL pages para export Excel
  const fetchAllPages = async (onProgress) => {
    const perPage = 200;
    let allData = [];
    let page = 1;
    let totalPages = 1;

    while (page <= totalPages) {
      const result = await analyticsApi.getSalientesDetalle(page, perPage, filters);
      if (!result || !result.data || result.data.length === 0) break;
      allData = allData.concat(result.data.map(l => ({
        'Call ID': l.callid,
        'Fecha': l.fecha,
        'Hora': l.hora,
        'Campaña': l.campana,
        'Agente': l.agente,
        'Número': l.numero,
        'Duración (seg)': l.duracion,
        'Espera (seg)': l.espera,
        'Evento': l.evento,
        'Resultado': l.resultado,
        'Quién Colgó': l.quien_colgo,
      })));
      totalPages = result.total_pages;
      if (onProgress) onProgress(allData.length, result.total);
      page++;
    }
    return allData;
  };

  const prepareEventosChart = () => {
    if (!dashboard || !dashboard.eventos) return [];

    return Object.entries(dashboard.eventos)
      .map(([evento, data]) => ({
        label: String(data?.descripcion || evento),
        value: Number(data?.total || 0)
      }))
      .filter(item => item.value > 0);
  };

  // formatDuracion importado desde utils/formatters

  // Sorting server-side
  const handleSort = (field) => {
    let newDir = 'desc';
    if (sortField === field) {
      newDir = sortDirection === 'asc' ? 'desc' : 'asc';
    }
    setSortField(field);
    setSortDirection(newDir);
    loadPageDetalle(1, pageSize, field, newDir);
  };

  const items = detalle?.data || [];
  const totalItems = detalle?.total || 0;
  const currentPage = detalle?.page || 1;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  const handlePageChange = (page) => {
    loadPageDetalle(page, pageSize, sortField, sortDirection);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    loadPageDetalle(1, size, sortField, sortDirection);
  };

  const getResultadoBadge = (resultado) => {
    const badges = {
      'Contestada': 'bg-green-100 text-green-800',
      'No contestada': 'bg-red-100 text-red-800',
      'Ocupado': 'bg-orange-100 text-orange-800',
      'Canal no disponible': 'bg-gray-100 text-gray-800',
      'Solo marcación': 'bg-yellow-100 text-yellow-800',
      'Contestada (sin cierre)': 'bg-blue-100 text-blue-800',
    };
    return badges[resultado] || 'bg-gray-100 text-gray-800';
  };

  const SortHeader = ({ field, children }) => (
    <th
      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
      onClick={() => handleSort(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {sortField === field && (
          <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
        )}
      </div>
    </th>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">📱 Llamadas Salientes</h2>

      {/* KPIs */}
      {dashboard && dashboard.metricas && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <KPICard
            title="Total Marcadas"
            value={dashboard.metricas.total_marcadas}
            icon="📞"
          />
          <KPICard
            title="Contestadas"
            value={dashboard.metricas.total_contestadas}
            icon="✅"
            subtitle={`${dashboard.metricas.tasa_contactacion}% tasa`}
          />
          <KPICard
            title="No Contestadas"
            value={dashboard.metricas.total_no_contestadas}
            icon="❌"
          />
          <KPICard
            title="Ocupadas"
            value={dashboard.metricas.total_ocupadas}
            icon="🔴"
          />
          <KPICard
            title="Fallos Técnicos"
            value={dashboard.metricas.total_fallos || 0}
            icon="⚠️"
          />
        </div>
      )}

      {/* Gráfico de Distribución */}
      <div className="grid grid-cols-1 gap-6 mb-6">
        <ApexChart
          type="bar"
          data={prepareEventosChart()}
          title="Distribución de Estados de Llamadas Salientes"
        />
      </div>

      {/* Tabla de Detalle de Llamadas Salientes */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-blue-50 flex justify-between items-center">
          <div>
            <h3 className="text-lg font-semibold text-blue-800">Detalle de Llamadas Salientes</h3>
            <p className="text-sm text-blue-600 mt-1">
              Total: {totalItems.toLocaleString('es-CO')} llamadas
            </p>
          </div>
          <ExportButtonAsync
            fetchAllData={fetchAllPages}
            filename="llamadas_salientes"
            label="Exportar a Excel"
            totalItems={totalItems}
          />
        </div>

        {loadingDetalle && (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-sm text-gray-500">Cargando...</span>
          </div>
        )}

        {!loadingDetalle && (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <SortHeader field="callid">Call ID</SortHeader>
                    <SortHeader field="fecha">Fecha</SortHeader>
                    <SortHeader field="hora">Hora</SortHeader>
                    <SortHeader field="campana">Campaña</SortHeader>
                    <SortHeader field="agente">Agente</SortHeader>
                    <SortHeader field="numero">Número</SortHeader>
                    <SortHeader field="duracion">Duración</SortHeader>
                    <SortHeader field="espera">Espera</SortHeader>
                    <SortHeader field="resultado">Resultado</SortHeader>
                    <SortHeader field="quien_colgo">Quién Colgó</SortHeader>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {items.length > 0 ? (
                    items.map((llamada, idx) => (
                      <tr key={idx} className="hover:bg-blue-50">
                        <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600 font-mono">{llamada.callid}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.fecha}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{llamada.hora}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.campana}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.agente}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-medium">{llamada.numero}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatDuracion(llamada.duracion)}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{formatDuracion(llamada.espera)}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-medium rounded-full ${getResultadoBadge(llamada.resultado)}`}>
                            {llamada.resultado}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {llamada.quien_colgo ? (
                            <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                              llamada.quien_colgo === 'Agente' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                            }`}>
                              {llamada.quien_colgo}
                            </span>
                          ) : (
                            <span className="text-xs text-gray-400">-</span>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="10" className="px-6 py-8 text-center text-gray-500">
                        No hay llamadas salientes en el período seleccionado
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {totalItems > 0 && (
              <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                pageSize={pageSize}
                onPageChange={handlePageChange}
                onPageSizeChange={handlePageSizeChange}
                totalItems={totalItems}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default LlamadasSalientes;

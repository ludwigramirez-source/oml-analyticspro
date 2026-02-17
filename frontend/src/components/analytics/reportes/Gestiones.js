import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import ApexChart from '../ApexChart';
import { ExportButton, ExportButtonAsync } from '../../../utils/excelExport';
import Pagination from '../Pagination';

const Gestiones = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [kpis, setKpis] = useState(null);
  const [porAgente, setPorAgente] = useState([]);
  const [porCampana, setPorCampana] = useState([]);
  const [porIncidencia, setPorIncidencia] = useState([]);
  const [porDia, setPorDia] = useState([]);
  const [detalle, setDetalle] = useState({ data: [], total: 0, page: 1, total_pages: 0 });
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [loadingDetalle, setLoadingDetalle] = useState(false);
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  useEffect(() => {
    loadData();
  }, [filters]);

  useEffect(() => {
    loadDetalle(currentPage, pageSize);
  }, [currentPage, pageSize, filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [kpisData, agentes, campanas, incidencias, dias] = await Promise.all([
        analyticsApi.getGestionesKpis(filters).catch(() => null),
        analyticsApi.getGestionesPorAgente(filters).catch(() => []),
        analyticsApi.getGestionesPorCampana(filters).catch(() => []),
        analyticsApi.getGestionesPorIncidencia(filters).catch(() => []),
        analyticsApi.getGestionesPorDia(filters).catch(() => []),
      ]);

      setKpis(kpisData);
      setPorAgente(agentes || []);
      setPorCampana(campanas || []);
      setPorIncidencia(incidencias || []);
      setPorDia(dias || []);
      setCurrentPage(1);
    } catch (error) {
      console.error('Error loading gestiones:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadDetalle = async (page, perPage = 25) => {
    setLoadingDetalle(true);
    try {
      const result = await analyticsApi.getGestionesDetalle(filters, page, perPage);
      setDetalle(result || { data: [], total: 0, page: 1, total_pages: 0 });
    } catch (error) {
      console.error('Error loading gestiones detalle:', error);
      setDetalle({ data: [], total: 0, page: 1, total_pages: 0 });
    } finally {
      setLoadingDetalle(false);
    }
  };

  // Fetch ALL pages para export Excel
  const fetchAllGestiones = async (onProgress) => {
    const allData = [];
    let page = 1;
    let totalPages = 1;
    const perPage = 200;
    while (page <= totalPages) {
      const result = await analyticsApi.getGestionesDetalle(filters, page, perPage);
      allData.push(...(result.data || []));
      if (page === 1) totalPages = result.total_pages || 1;
      if (onProgress) onProgress(allData.length, result.total || 0);
      page++;
    }
    return allData;
  };

  const formatNumber = (num) => {
    return typeof num === 'number' ? num.toLocaleString('es-CO') : '0';
  };

  // Sort para la tabla detalle (local, dentro de la página)
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const sortedItems = React.useMemo(() => {
    const items = detalle.data || [];
    if (!items.length || !sortField) return items;
    return [...items].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal || '').toLowerCase();
      }
      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });
  }, [detalle.data, sortField, sortDirection]);

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  const totalItems = detalle.total || 0;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  const SortHeader = ({ field, children }) => (
    <th
      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
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

  const incidenciaPieData = porIncidencia.slice(0, 10).map(item => ({
    label: String(item.descripcion || 'Sin tipo'),
    value: Number(item.total_gestiones || 0),
  }));

  const agentePieData = porAgente.slice(0, 10).map(item => ({
    label: String(item.agente || 'Sin agente'),
    value: Number(item.total_gestiones || 0),
  }));


  return (
    <div>
      <h2 className="text-2xl font-bold text-gray-800 mb-6">Gestiones de Incidencias</h2>

      {/* KPIs */}
      {kpis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Total Gestiones</p>
            <p className="text-2xl font-bold text-blue-600">{formatNumber(kpis.total_gestiones)}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Agentes Activos</p>
            <p className="text-2xl font-bold text-green-600">{formatNumber(kpis.agentes_activos)}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Campanas Activas</p>
            <p className="text-2xl font-bold text-purple-600">{formatNumber(kpis.campanas_activas)}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Promedio por Agente</p>
            <p className="text-2xl font-bold text-orange-600">{kpis.promedio_por_agente}</p>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <p className="text-sm text-gray-500">Top Incidencia</p>
            <p className="text-sm font-bold text-red-600 truncate" title={kpis.top_incidencia}>
              {kpis.top_incidencia}
            </p>
            <p className="text-xs text-gray-400">{formatNumber(kpis.top_incidencia_total)} gestiones</p>
          </div>
        </div>
      )}

      {/* Distribuciones: Incidencias y Agentes */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {incidenciaPieData.length > 0 && (
          <ApexChart
            type="pie"
            data={incidenciaPieData}
            title="Gestiones por Tipo de Incidencia (Top 10)"
          />
        )}
        {agentePieData.length > 0 && (
          <ApexChart
            type="pie"
            data={agentePieData}
            title="Gestiones por Agente (Top 10)"
          />
        )}
      </div>

      {/* Tabla Por Incidencia */}
      {porIncidencia.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-gray-800">Gestiones por Tipo de Incidencia</h3>
            <ExportButton
              data={porIncidencia}
              filename="gestiones_por_incidencia"
              label="Exportar"
            />
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Codigo</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Incidencia</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">%</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {(() => {
                  const totalGestiones = porIncidencia.reduce((sum, i) => sum + i.total_gestiones, 0);
                  return porIncidencia.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm text-gray-500">{item.codigo}</td>
                      <td className="px-4 py-2 text-sm text-gray-900">{item.descripcion}</td>
                      <td className="px-4 py-2 text-sm text-right font-medium">{formatNumber(item.total_gestiones)}</td>
                      <td className="px-4 py-2 text-sm text-right text-gray-500">
                        {totalGestiones > 0 ? ((item.total_gestiones / totalGestiones) * 100).toFixed(1) : 0}%
                      </td>
                    </tr>
                  ));
                })()}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tablas Agente y Campana lado a lado */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Tabla Por Agente */}
        {porAgente.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800">Gestiones por Agente</h3>
              <ExportButton data={porAgente} filename="gestiones_por_agente" label="Exportar" />
            </div>
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {porAgente.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm text-gray-900">{item.agente}</td>
                      <td className="px-4 py-2 text-sm text-right font-medium">{formatNumber(item.total_gestiones)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Tabla Por Campana */}
        {porCampana.length > 0 && (
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold text-gray-800">Gestiones por Campana</h3>
              <ExportButton data={porCampana} filename="gestiones_por_campana" label="Exportar" />
            </div>
            <div className="overflow-x-auto max-h-96 overflow-y-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50 sticky top-0">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campana</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Total</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {porCampana.map((item, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm text-gray-900">{item.campana}</td>
                      <td className="px-4 py-2 text-sm text-right font-medium">{formatNumber(item.total_gestiones)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Tabla Detalle - Mismo estilo que TablaLlamadas */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h3 className="text-lg font-semibold text-gray-800">Detalle de Gestiones</h3>
          <ExportButtonAsync
            fetchAllData={fetchAllGestiones}
            filename="gestiones_detalle"
            label="Exportar a Excel"
            totalItems={totalItems}
          />
        </div>

        {loadingDetalle ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-sm text-gray-500">Cargando...</span>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <SortHeader field="fecha">Fecha</SortHeader>
                    <SortHeader field="hora">Hora</SortHeader>
                    <SortHeader field="nombre">Nombre</SortHeader>
                    <SortHeader field="nis">NIS</SortHeader>
                    <SortHeader field="telefono">Telefono</SortHeader>
                    <SortHeader field="incidencia">Incidencia</SortHeader>
                    <SortHeader field="agente">Agente</SortHeader>
                    <SortHeader field="campana">Campana</SortHeader>
                    <SortHeader field="call_id">Call ID</SortHeader>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedItems.length === 0 ? (
                    <tr>
                      <td colSpan="9" className="px-6 py-8 text-center text-gray-500">
                        No se encontraron gestiones
                      </td>
                    </tr>
                  ) : (
                    sortedItems.map((item, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">{item.fecha}</td>
                        <td className="px-3 py-2 text-sm text-gray-600 whitespace-nowrap">{item.hora}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.nombre}</td>
                        <td className="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">{item.nis}</td>
                        <td className="px-3 py-2 text-sm text-gray-600 font-medium whitespace-nowrap">{item.telefono}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.incidencia}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.agente}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.campana}</td>
                        <td className="px-3 py-2 text-xs text-gray-500 font-mono whitespace-nowrap">{item.call_id}</td>
                      </tr>
                    ))
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

export default Gestiones;

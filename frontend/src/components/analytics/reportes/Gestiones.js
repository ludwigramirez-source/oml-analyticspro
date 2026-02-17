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

  // Auditoria: llamadas sin gestion
  const [auditoria, setAuditoria] = useState(null);
  const [sinGestion, setSinGestion] = useState({ data: [], total: 0, page: 1, total_pages: 0 });
  const [sinGestionPage, setSinGestionPage] = useState(1);
  const [sinGestionPageSize, setSinGestionPageSize] = useState(25);
  const [loadingSinGestion, setLoadingSinGestion] = useState(false);
  const [sortFieldSG, setSortFieldSG] = useState(null);
  const [sortDirectionSG, setSortDirectionSG] = useState('asc');

  useEffect(() => {
    loadData();
  }, [filters]);

  useEffect(() => {
    loadDetalle(currentPage, pageSize);
  }, [currentPage, pageSize, filters]);

  useEffect(() => {
    loadSinGestion(sinGestionPage, sinGestionPageSize);
  }, [sinGestionPage, sinGestionPageSize, filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [kpisData, agentes, campanas, incidencias, dias, auditoriaData] = await Promise.all([
        analyticsApi.getGestionesKpis(filters).catch(() => null),
        analyticsApi.getGestionesPorAgente(filters).catch(() => []),
        analyticsApi.getGestionesPorCampana(filters).catch(() => []),
        analyticsApi.getGestionesPorIncidencia(filters).catch(() => []),
        analyticsApi.getGestionesPorDia(filters).catch(() => []),
        analyticsApi.getAuditoriaGestiones(filters).catch(() => null),
      ]);

      setKpis(kpisData);
      setPorAgente(agentes || []);
      setPorCampana(campanas || []);
      setPorIncidencia(incidencias || []);
      setPorDia(dias || []);
      setAuditoria(auditoriaData);
      setCurrentPage(1);
      setSinGestionPage(1);
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

  const loadSinGestion = async (page, perPage = 25) => {
    setLoadingSinGestion(true);
    try {
      const result = await analyticsApi.getLlamadasSinGestion(filters, page, perPage);
      setSinGestion(result || { data: [], total: 0, page: 1, total_pages: 0 });
    } catch (error) {
      console.error('Error loading sin gestion:', error);
      setSinGestion({ data: [], total: 0, page: 1, total_pages: 0 });
    } finally {
      setLoadingSinGestion(false);
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

  const fetchAllSinGestion = async (onProgress) => {
    const allData = [];
    let page = 1;
    let totalPages = 1;
    const perPage = 200;
    while (page <= totalPages) {
      const result = await analyticsApi.getLlamadasSinGestion(filters, page, perPage);
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

  const formatDuration = (seconds) => {
    if (!seconds && seconds !== 0) return '00:00';
    const sec = Math.round(Number(seconds) || 0);
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  // Sort para la tabla detalle (local, dentro de la pagina)
  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const handleSortSG = (field) => {
    if (sortFieldSG === field) {
      setSortDirectionSG(sortDirectionSG === 'asc' ? 'desc' : 'asc');
    } else {
      setSortFieldSG(field);
      setSortDirectionSG('asc');
    }
  };

  const sortItems = (items, field, direction) => {
    if (!items.length || !field) return items;
    return [...items].sort((a, b) => {
      let aVal = a[field];
      let bVal = b[field];
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = (bVal || '').toLowerCase();
      }
      if (aVal < bVal) return direction === 'asc' ? -1 : 1;
      if (aVal > bVal) return direction === 'asc' ? 1 : -1;
      return 0;
    });
  };

  const sortedItems = React.useMemo(
    () => sortItems(detalle.data || [], sortField, sortDirection),
    [detalle.data, sortField, sortDirection]
  );

  const sortedSinGestion = React.useMemo(
    () => sortItems(sinGestion.data || [], sortFieldSG, sortDirectionSG),
    [sinGestion.data, sortFieldSG, sortDirectionSG]
  );

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  const totalItems = detalle.total || 0;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  const totalItemsSG = sinGestion.total || 0;
  const totalPagesSG = Math.ceil(totalItemsSG / sinGestionPageSize) || 1;

  const SortHeader = ({ field, children, onSortClick, activeField, activeDirection }) => (
    <th
      className="px-3 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
      onClick={() => onSortClick(field)}
    >
      <div className="flex items-center gap-1">
        {children}
        {activeField === field && (
          <span>{activeDirection === 'asc' ? '↑' : '↓'}</span>
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

      {/* Tarjetas de Auditoria */}
      {auditoria && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg shadow-sm border border-blue-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Llamadas Contestadas</p>
                <p className="text-2xl font-bold text-blue-600">{formatNumber(auditoria.total_atendidas)}</p>
              </div>
              <div className="bg-blue-50 rounded-full p-3">
                <svg className="w-6 h-6 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-green-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Total Gestiones</p>
                <p className="text-2xl font-bold text-green-600">{formatNumber(auditoria.total_gestiones)}</p>
              </div>
              <div className="bg-green-50 rounded-full p-3">
                <svg className="w-6 h-6 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-red-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Sin Gestion</p>
                <p className="text-2xl font-bold text-red-600">{formatNumber(auditoria.sin_gestion)}</p>
              </div>
              <div className="bg-red-50 rounded-full p-3">
                <svg className="w-6 h-6 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
            </div>
          </div>
          <div className="bg-white rounded-lg shadow-sm border border-purple-200 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-500">Cobertura</p>
                <p className="text-2xl font-bold text-purple-600">{auditoria.cobertura_pct}%</p>
              </div>
              <div className="bg-purple-50 rounded-full p-3">
                <svg className="w-6 h-6 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
            </div>
            {/* Barra de progreso */}
            <div className="mt-2 w-full bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${
                  auditoria.cobertura_pct >= 90 ? 'bg-green-500' :
                  auditoria.cobertura_pct >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${Math.min(auditoria.cobertura_pct, 100)}%` }}
              ></div>
            </div>
          </div>
        </div>
      )}

      {/* KPIs originales */}
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

      {/* Tabla Detalle - Gestiones */}
      <div className="bg-white rounded-lg border border-gray-200 mb-6">
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
                    <SortHeader field="fecha" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Fecha</SortHeader>
                    <SortHeader field="hora" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Hora</SortHeader>
                    <SortHeader field="nombre" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Nombre</SortHeader>
                    <SortHeader field="nis" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>NIS</SortHeader>
                    <SortHeader field="telefono" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Telefono</SortHeader>
                    <SortHeader field="incidencia" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Incidencia</SortHeader>
                    <SortHeader field="agente" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Agente</SortHeader>
                    <SortHeader field="duracion_llamada" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Duracion</SortHeader>
                    <SortHeader field="campana" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Campana</SortHeader>
                    <SortHeader field="call_id" onSortClick={handleSort} activeField={sortField} activeDirection={sortDirection}>Call ID</SortHeader>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedItems.length === 0 ? (
                    <tr>
                      <td colSpan="10" className="px-6 py-8 text-center text-gray-500">
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
                        <td className="px-3 py-2 text-sm text-gray-600 font-mono whitespace-nowrap">{formatDuration(item.duracion_llamada)}</td>
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

      {/* Tabla: Llamadas Atendidas SIN Gestion */}
      <div className="bg-white rounded-lg border-2 border-red-200">
        <div className="px-6 py-4 border-b border-red-200 bg-red-50 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div>
              <h3 className="text-lg font-semibold text-red-800">Llamadas Atendidas sin Gestion</h3>
              <p className="text-xs text-red-600">Llamadas contestadas que no tienen registro de gestion asociado</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <span className="bg-red-100 text-red-800 text-sm font-medium px-3 py-1 rounded-full">
              {formatNumber(totalItemsSG)} registros
            </span>
            <ExportButtonAsync
              fetchAllData={fetchAllSinGestion}
              filename="llamadas_sin_gestion"
              label="Exportar a Excel"
              totalItems={totalItemsSG}
            />
          </div>
        </div>

        {loadingSinGestion ? (
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
            <span className="ml-3 text-sm text-gray-500">Cargando...</span>
          </div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <SortHeader field="fecha" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Fecha</SortHeader>
                    <SortHeader field="hora" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Hora</SortHeader>
                    <SortHeader field="tipo_llamada" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Tipo</SortHeader>
                    <SortHeader field="numero" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Numero</SortHeader>
                    <SortHeader field="agente" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Agente</SortHeader>
                    <SortHeader field="campana" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Campana</SortHeader>
                    <SortHeader field="duracion" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Duracion</SortHeader>
                    <SortHeader field="espera" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Espera</SortHeader>
                    <SortHeader field="evento" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Evento</SortHeader>
                    <SortHeader field="callid" onSortClick={handleSortSG} activeField={sortFieldSG} activeDirection={sortDirectionSG}>Call ID</SortHeader>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {sortedSinGestion.length === 0 ? (
                    <tr>
                      <td colSpan="10" className="px-6 py-8 text-center text-gray-500">
                        <div className="flex flex-col items-center gap-2">
                          <svg className="w-8 h-8 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                          </svg>
                          <span>Todas las llamadas atendidas tienen gestion registrada</span>
                        </div>
                      </td>
                    </tr>
                  ) : (
                    sortedSinGestion.map((item, idx) => (
                      <tr key={idx} className="hover:bg-red-50">
                        <td className="px-3 py-2 text-sm text-gray-900 whitespace-nowrap">{item.fecha}</td>
                        <td className="px-3 py-2 text-sm text-gray-600 whitespace-nowrap">{item.hora}</td>
                        <td className="px-3 py-2 text-sm whitespace-nowrap">
                          <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                            item.tipo_llamada === 'Entrante'
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-orange-100 text-orange-700'
                          }`}>
                            {item.tipo_llamada}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-600 font-medium whitespace-nowrap">{item.numero}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.agente}</td>
                        <td className="px-3 py-2 text-sm text-gray-900">{item.campana}</td>
                        <td className="px-3 py-2 text-sm text-gray-600 whitespace-nowrap">{formatDuration(item.duracion)}</td>
                        <td className="px-3 py-2 text-sm text-gray-600 whitespace-nowrap">{formatDuration(item.espera)}</td>
                        <td className="px-3 py-2 text-xs text-gray-500 whitespace-nowrap">{item.evento}</td>
                        <td className="px-3 py-2 text-xs text-gray-500 font-mono whitespace-nowrap">{item.callid}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

            {totalItemsSG > 0 && (
              <Pagination
                currentPage={sinGestionPage}
                totalPages={totalPagesSG}
                pageSize={sinGestionPageSize}
                onPageChange={(page) => setSinGestionPage(page)}
                onPageSizeChange={(size) => { setSinGestionPageSize(size); setSinGestionPage(1); }}
                totalItems={totalItemsSG}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Gestiones;

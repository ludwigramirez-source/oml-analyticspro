import React, { useState } from 'react';
import { ExportButtonAsync } from '../../utils/excelExport';
import Pagination from './Pagination';

/**
 * TablaLlamadas - Paginación y ordenamiento server-side
 * Carga solo la página actual desde el backend.
 * Al ordenar por columna, pide al backend la data ordenada.
 * La descarga Excel obtiene TODAS las páginas en background.
 */
const TablaLlamadas = ({
  data,           // { data: [], total, page, per_page, total_pages }
  loading,
  onPageChange,   // (page, pageSize, sortBy, sortDir) => void
  filters,        // filtros actuales para export
  fetchAllPages,  // () => Promise<allData[]> para export
}) => {
  const [pageSize, setPageSize] = useState(25);
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('desc');

  const items = data?.data || [];
  const totalItems = data?.total || 0;
  const currentPage = data?.page || 1;
  const totalPages = Math.ceil(totalItems / pageSize) || 1;

  const formatDuracion = (seconds) => {
    if (!seconds && seconds !== 0) return '00:00';
    const s = Math.round(Number(seconds) || 0);
    const min = Math.floor(s / 60);
    const sec = s % 60;
    return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  // Sorting server-side: al hacer click, pedir al backend ordenado
  const handleSort = (field) => {
    let newDir = 'desc';
    if (sortField === field) {
      newDir = sortDirection === 'asc' ? 'desc' : 'asc';
    }
    setSortField(field);
    setSortDirection(newDir);
    // Volver a página 1 con el nuevo orden
    if (onPageChange) onPageChange(1, pageSize, field, newDir);
  };

  const handlePageChange = (page) => {
    if (onPageChange) onPageChange(page, pageSize, sortField, sortDirection);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    if (onPageChange) onPageChange(1, size, sortField, sortDirection);
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

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-800">Llamadas Detalladas</h3>
        <ExportButtonAsync
          fetchAllData={fetchAllPages}
          filename="llamadas_atendidas"
          label="Exportar a Excel"
          totalItems={totalItems}
        />
      </div>

      {/* Loading overlay */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-sm text-gray-500">Cargando...</span>
        </div>
      )}

      {!loading && (
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
                  <SortHeader field="quien_colgo">Quién Colgó</SortHeader>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {items.length > 0 ? (
                  items.map((llamada, idx) => (
                    <tr key={idx} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600 font-mono">{llamada.callid || llamada.id}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.fecha}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{llamada.hora}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.campana}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.agente}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-medium">{llamada.numero}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatDuracion(llamada.duracion)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{formatDuracion(llamada.espera)}</td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                          llamada.quien_colgo === 'Agente' ? 'bg-blue-100 text-blue-800' : 'bg-green-100 text-green-800'
                        }`}>
                          {llamada.quien_colgo || 'N/A'}
                        </span>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="9" className="px-6 py-8 text-center text-gray-500">
                      No hay llamadas para mostrar
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
  );
};

export default TablaLlamadas;

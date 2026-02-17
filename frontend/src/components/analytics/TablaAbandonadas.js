import React, { useState } from 'react';
import { ExportButtonAsync } from '../../utils/excelExport';
import Pagination from './Pagination';

/**
 * TablaAbandonadas - Paginación y ordenamiento server-side
 * Carga solo la página actual desde el backend.
 * Al ordenar por columna, pide al backend la data ordenada.
 * La descarga Excel obtiene TODAS las páginas en background.
 */
const TablaAbandonadas = ({
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

  const formatTiempo = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const getTipoBadge = (tipo) => {
    const badges = {
      'En Cola': 'bg-red-100 text-red-800',
      'Durante Transferencia': 'bg-orange-100 text-orange-800',
      'En Audio Bienvenida': 'bg-yellow-100 text-yellow-800'
    };
    return badges[tipo] || 'bg-gray-100 text-gray-800';
  };

  // Sorting server-side
  const handleSort = (field) => {
    let newDir = 'desc';
    if (sortField === field) {
      newDir = sortDirection === 'asc' ? 'desc' : 'asc';
    }
    setSortField(field);
    setSortDirection(newDir);
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
      <div className="px-6 py-4 border-b border-gray-200 bg-red-50 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-red-800">Llamadas No Atendidas</h3>
          <p className="text-sm text-red-600 mt-1">
            Total: {totalItems.toLocaleString('es-CO')} llamadas (abandonadas por clientes + no contestadas salientes)
          </p>
        </div>
        <ExportButtonAsync
          fetchAllData={fetchAllPages}
          filename="llamadas_no_atendidas"
          label="Exportar a Excel"
          totalItems={totalItems}
        />
      </div>

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600"></div>
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
                  <SortHeader field="numero">Número</SortHeader>
                  <SortHeader field="tiempo_espera">Tiempo Espera</SortHeader>
                  <SortHeader field="tipo_abandono">Tipo Abandono</SortHeader>
                  <SortHeader field="evento">Evento</SortHeader>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {items.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                      No hay llamadas abandonadas en el período seleccionado
                    </td>
                  </tr>
                ) : (
                  items.map((llamada, idx) => (
                    <tr key={idx} className="hover:bg-red-50">
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600 font-mono">{llamada.callid}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.fecha}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{llamada.hora}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.campana}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-medium">{llamada.numero}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className="text-orange-600 font-semibold">{formatTiempo(llamada.tiempo_espera)}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-medium rounded-full ${getTipoBadge(llamada.tipo_abandono)}`}>
                          {llamada.tipo_abandono}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-500">{llamada.evento}</td>
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
  );
};

export default TablaAbandonadas;

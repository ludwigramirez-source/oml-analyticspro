import React, { useState, useMemo } from 'react';
import { ExportButton } from '../../utils/excelExport';
import Pagination from './Pagination';

const TablaAbandonadas = ({ llamadas }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc'); // 'asc' o 'desc'

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

  // Función para manejar el ordenamiento
  const handleSort = (field) => {
    if (sortField === field) {
      // Si ya está ordenado por este campo, cambiar dirección
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      // Nuevo campo, ordenar ascendente
      setSortField(field);
      setSortDirection('asc');
    }
    setCurrentPage(1); // Volver a la primera página al ordenar
  };

  // Datos ordenados
  const sortedData = useMemo(() => {
    if (!llamadas || !sortField) return llamadas || [];

    const sorted = [...llamadas].sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      // Manejar valores null/undefined
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      // Comparación numérica para tiempo_espera
      if (sortField === 'tiempo_espera') {
        aVal = Number(aVal) || 0;
        bVal = Number(bVal) || 0;
      }

      // Comparación de strings
      if (typeof aVal === 'string') {
        aVal = aVal.toLowerCase();
        bVal = bVal.toLowerCase();
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return sorted;
  }, [llamadas, sortField, sortDirection]);

  // Paginación aplicada a datos ordenados
  const totalPages = Math.ceil((sortedData?.length || 0) / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return sortedData?.slice(start, end) || [];
  }, [sortedData, currentPage, pageSize]);

  const handlePageChange = (page) => {
    setCurrentPage(page);
  };

  const handlePageSizeChange = (size) => {
    setPageSize(size);
    setCurrentPage(1);
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 bg-red-50 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-red-800">📞❌ Llamadas No Atendidas</h3>
          <p className="text-sm text-red-600 mt-1">
            Total: {llamadas.length} llamadas (abandonadas por clientes + no contestadas salientes)
          </p>
        </div>
        <ExportButton 
          data={llamadas} 
          filename="llamadas_no_atendidas"
          label="Exportar a Excel"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('callid')}
              >
                <div className="flex items-center gap-1">
                  Call ID
                  {sortField === 'callid' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('fecha')}
              >
                <div className="flex items-center gap-1">
                  Fecha
                  {sortField === 'fecha' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('hora')}
              >
                <div className="flex items-center gap-1">
                  Hora
                  {sortField === 'hora' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('campana')}
              >
                <div className="flex items-center gap-1">
                  Campaña
                  {sortField === 'campana' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('numero')}
              >
                <div className="flex items-center gap-1">
                  Número
                  {sortField === 'numero' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('tiempo_espera')}
              >
                <div className="flex items-center gap-1">
                  Tiempo Espera
                  {sortField === 'tiempo_espera' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('tipo_abandono')}
              >
                <div className="flex items-center gap-1">
                  Tipo Abandono
                  {sortField === 'tipo_abandono' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('evento')}
              >
                <div className="flex items-center gap-1">
                  Evento
                  {sortField === 'evento' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                  No hay llamadas abandonadas en el período seleccionado
                </td>
              </tr>
            ) : (
              paginatedData.map((llamada, idx) => (
                <tr key={idx} className="hover:bg-red-50">
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600 font-mono">
                    {llamada.callid}
                  </td>
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
      
      {/* Paginación */}
      {sortedData && sortedData.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
          totalItems={sortedData.length}
        />
      )}
    </div>
  );
};

export default TablaAbandonadas;

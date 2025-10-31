import React, { useState, useMemo } from 'react';
import { ExportButton } from '../../utils/excelExport';
import Pagination from './Pagination';

const TablaLlamadas = ({ llamadas }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [sortField, setSortField] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc'); // 'asc' o 'desc'

  const formatDuracion = (seconds) => {
    const min = Math.floor(seconds / 60);
    const sec = seconds % 60;
    return `${min}:${sec.toString().padStart(2, '0')}`;
  };

  const getEstadoBadge = (estado) => {
    const badges = {
      'CONNECT': 'bg-green-100 text-green-800',
      'COMPLETEAGENT': 'bg-green-100 text-green-800',
      'ABANDON': 'bg-red-100 text-red-800',
      'NOANSWER': 'bg-yellow-100 text-yellow-800',
      'BUSY': 'bg-orange-100 text-orange-800'
    };
    return badges[estado] || 'bg-gray-100 text-gray-800';
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

      // Comparación numérica para duracion y espera
      if (sortField === 'duracion' || sortField === 'espera') {
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
    setCurrentPage(1); // Reset to first page
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <h3 className="text-lg font-semibold text-gray-800">Llamadas Detalladas</h3>
        <ExportButton 
          data={llamadas} 
          filename="llamadas_atendidas"
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
                onClick={() => handleSort('agente')}
              >
                <div className="flex items-center gap-1">
                  Agente
                  {sortField === 'agente' && (
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
                onClick={() => handleSort('duracion')}
              >
                <div className="flex items-center gap-1">
                  Duración
                  {sortField === 'duracion' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('espera')}
              >
                <div className="flex items-center gap-1">
                  Espera
                  {sortField === 'espera' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
              <th
                className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100"
                onClick={() => handleSort('quien_colgo')}
              >
                <div className="flex items-center gap-1">
                  Quién Colgó
                  {sortField === 'quien_colgo' && (
                    <span>{sortDirection === 'asc' ? '↑' : '↓'}</span>
                  )}
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {paginatedData.length > 0 ? (
              paginatedData.map((llamada, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600 font-mono">{llamada.callid || llamada.id}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.fecha}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{llamada.hora}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.campana}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{llamada.agente}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600 font-medium">{llamada.numero}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{formatDuracion(llamada.duracion)}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{llamada.espera}s</td>
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

export default TablaLlamadas;
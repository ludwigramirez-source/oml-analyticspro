import React, { useState, useMemo } from 'react';
import { ExportButton } from '../../utils/excelExport';
import Pagination from './Pagination';

const TablaLlamadas = ({ llamadas }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
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

  // Paginación
  const totalPages = Math.ceil((llamadas?.length || 0) / pageSize);
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    const end = start + pageSize;
    return llamadas?.slice(start, end) || [];
  }, [llamadas, currentPage, pageSize]);

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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Call ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hora</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaña</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Número</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duración</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Espera</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Quién Colgó</th>
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
      {llamadas && llamadas.length > 0 && (
        <Pagination
          currentPage={currentPage}
          totalPages={totalPages}
          pageSize={pageSize}
          onPageChange={handlePageChange}
          onPageSizeChange={handlePageSizeChange}
          totalItems={llamadas.length}
        />
      )}
    </div>
  );
};

export default TablaLlamadas;
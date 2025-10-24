import React, { useState, useMemo } from 'react';
import { ExportButton } from '../../utils/excelExport';
import Pagination from './Pagination';

const TablaAbandonadas = ({ llamadas }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
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
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Call ID</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fecha</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Hora</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaña</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Número</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Espera</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tipo Abandono</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Evento</th>
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

export default TablaAbandonadas;

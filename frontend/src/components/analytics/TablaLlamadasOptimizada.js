import React, { useState, useEffect } from 'react';
import * as XLSX from 'xlsx';
import { formatDuration } from '../../utils/formatters';

const TablaLlamadasOptimizada = ({ llamadasPaginated, onPageChange, filters }) => {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [isExporting, setIsExporting] = useState(false);

  const { data, total, total_pages } = llamadasPaginated;

  // Sincronizar página actual cuando cambian los datos
  useEffect(() => {
    if (llamadasPaginated.page) {
      setCurrentPage(llamadasPaginated.page);
    }
  }, [llamadasPaginated.page]);

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > total_pages) return;
    setCurrentPage(newPage);
    onPageChange(newPage, pageSize);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handlePageSizeChange = (newSize) => {
    const size = parseInt(newSize);
    setPageSize(size);
    setCurrentPage(1);
    onPageChange(1, size);
  };

  const handleExportVisible = () => {
    // Exportar solo los datos visibles
    const excelData = data.map(llamada => ({
      'Fecha': llamada.fecha,
      'Hora': llamada.hora,
      'Campaña': llamada.campana,
      'Agente': llamada.agente,
      'Número': llamada.numero,
      'Duración (seg)': llamada.duracion,
      'Espera (seg)': llamada.espera,
      'Evento': llamada.evento
    }));

    const ws = XLSX.utils.json_to_sheet(excelData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Llamadas Atendidas');
    XLSX.writeFile(wb, `llamadas_atendidas_pagina_${currentPage}_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  // formatDuration importado desde utils/formatters

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">
            Llamadas Atendidas
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Mostrando {data.length} de {total.toLocaleString()} registros
          </p>
        </div>

        <div className="flex gap-2">
          {/* Selector de tamaño de página */}
          <select
            value={pageSize}
            onChange={(e) => handlePageSizeChange(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="25">25 por página</option>
            <option value="50">50 por página</option>
            <option value="100">100 por página</option>
            <option value="200">200 por página</option>
          </select>

          <button
            onClick={handleExportVisible}
            disabled={data.length === 0}
            className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            📥 Exportar Página
          </button>
        </div>
      </div>

      {/* Tabla */}
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Fecha
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Hora
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Campaña
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Agente
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Número
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Duración
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Espera (seg)
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Evento
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {data.length === 0 ? (
              <tr>
                <td colSpan="8" className="px-6 py-12 text-center text-gray-500">
                  <div className="flex flex-col items-center">
                    <span className="text-4xl mb-2">📭</span>
                    <span>No hay datos para mostrar</span>
                  </div>
                </td>
              </tr>
            ) : (
              data.map((llamada, idx) => (
                <tr key={idx} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {llamada.fecha}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {llamada.hora}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate" title={llamada.campana}>
                    {llamada.campana}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-900">
                    {llamada.agente}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                    {llamada.numero}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
                    {formatDuration(llamada.duracion)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {formatDuration(llamada.espera)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600">
                    {llamada.evento}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Paginación */}
      {total_pages > 0 && (
        <div className="px-6 py-4 border-t border-gray-200 flex items-center justify-between bg-gray-50">
          <div className="text-sm text-gray-700">
            Página <strong>{currentPage}</strong> de <strong>{total_pages}</strong>
            <span className="ml-4 text-gray-500">
              ({((currentPage - 1) * pageSize + 1).toLocaleString()} - {Math.min(currentPage * pageSize, total).toLocaleString()} de {total.toLocaleString()})
            </span>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => handlePageChange(1)}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              ⏮ Primera
            </button>

            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              ← Anterior
            </button>

            {/* Números de página (mostrar 5 páginas alrededor de la actual) */}
            {Array.from({ length: Math.min(5, total_pages) }, (_, i) => {
              let pageNum;
              if (total_pages <= 5) {
                pageNum = i + 1;
              } else if (currentPage <= 3) {
                pageNum = i + 1;
              } else if (currentPage >= total_pages - 2) {
                pageNum = total_pages - 4 + i;
              } else {
                pageNum = currentPage - 2 + i;
              }

              return (
                <button
                  key={pageNum}
                  onClick={() => handlePageChange(pageNum)}
                  className={`px-3 py-1 border rounded text-sm transition-colors ${
                    currentPage === pageNum
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'border-gray-300 hover:bg-white'
                  }`}
                >
                  {pageNum}
                </button>
              );
            })}

            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage >= total_pages}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              Siguiente →
            </button>

            <button
              onClick={() => handlePageChange(total_pages)}
              disabled={currentPage >= total_pages}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-white transition-colors"
            >
              Última ⏭
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default TablaLlamadasOptimizada;

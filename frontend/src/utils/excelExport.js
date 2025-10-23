/**
 * Utilidad para exportar datos a Excel (CSV)
 * Compatible con navegadores sin librerías externas
 */

export const exportToExcel = (data, filename = 'export') => {
  if (!data || data.length === 0) {
    alert('No hay datos para exportar');
    return;
  }

  // Obtener las columnas (keys del primer objeto)
  const headers = Object.keys(data[0]);
  
  // Crear filas CSV
  const csvRows = [];
  
  // Agregar encabezados
  csvRows.push(headers.join(','));
  
  // Agregar datos
  data.forEach(row => {
    const values = headers.map(header => {
      const value = row[header];
      // Escapar valores que contengan comas o saltos de línea
      const escaped = ('' + value).replace(/"/g, '""');
      return `"${escaped}"`;
    });
    csvRows.push(values.join(','));
  });
  
  // Crear el contenido CSV
  const csvContent = csvRows.join('\n');
  
  // Crear Blob y descargar
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}_${new Date().toISOString().slice(0,10)}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
};

/**
 * Botón de exportación reutilizable
 */
export const ExportButton = ({ data, filename, label = 'Exportar a Excel', className = '' }) => {
  const handleExport = () => {
    exportToExcel(data, filename);
  };

  return (
    <button
      onClick={handleExport}
      disabled={!data || data.length === 0}
      className={`
        inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md
        text-white bg-green-600 hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed
        focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500
        transition duration-150 ease-in-out
        ${className}
      `}
    >
      <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
      {label}
    </button>
  );
};

export default { exportToExcel, ExportButton };

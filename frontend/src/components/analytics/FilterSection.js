import React from 'react';
import { format } from 'date-fns';

const FilterSection = ({ filters, setFilters, campanas, agentes, onSearch }) => {
  const handleChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const getTodayDate = () => format(new Date(), 'yyyy-MM-dd');

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 mb-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        🔍 Filtros de Búsqueda
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha Inicio
          </label>
          <input
            type="date"
            value={filters.fecha_inicio || ''}
            onChange={(e) => handleChange('fecha_inicio', e.target.value)}
            max={getTodayDate()}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha Fin
          </label>
          <input
            type="date"
            value={filters.fecha_fin || ''}
            onChange={(e) => handleChange('fecha_fin', e.target.value)}
            max={getTodayDate()}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Campaña
          </label>
          <select
            value={filters.campana_id || ''}
            onChange={(e) => handleChange('campana_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas las campañas</option>
            {campanas.map(c => (
              <option key={c.id} value={c.id}>{c.nombre}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Agente
          </label>
          <select
            value={filters.agente_id || ''}
            onChange={(e) => handleChange('agente_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los agentes</option>
            {agentes.map(a => (
              <option key={a.id} value={a.id}>{a.nombre}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-4 flex gap-3">
        <button
          onClick={onSearch}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          🔍 Buscar
        </button>
        <button
          onClick={() => {
            setFilters({});
            onSearch();
          }}
          className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
        >
          🔄 Limpiar
        </button>
      </div>
    </div>
  );
};

export default FilterSection;
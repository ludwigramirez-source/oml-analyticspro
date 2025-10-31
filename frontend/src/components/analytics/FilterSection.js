import React, { useState } from 'react';
import { format, subDays, startOfMonth, endOfMonth, startOfDay, endOfDay } from 'date-fns';

const FilterSection = ({ filters, setFilters, campanas, agentes, onSearch }) => {
  const [selectedRange, setSelectedRange] = useState('hoy');
  const [selectedCampanas, setSelectedCampanas] = useState([]);
  const [selectedAgentes, setSelectedAgentes] = useState([]);

  const handleChange = (field, value) => {
    setFilters(prev => ({ ...prev, [field]: value }));
  };

  const getTodayDate = () => format(new Date(), 'yyyy-MM-dd');

  const applyDateRange = (range) => {
    setSelectedRange(range);
    const today = new Date();
    let startDate, endDate;

    switch (range) {
      case 'hoy':
        startDate = endDate = today;
        break;
      case 'ayer':
        startDate = endDate = subDays(today, 1);
        break;
      case '7_dias':
        startDate = subDays(today, 6);
        endDate = today;
        break;
      case '30_dias':
        startDate = subDays(today, 29);
        endDate = today;
        break;
      case 'este_mes':
        startDate = startOfMonth(today);
        endDate = endOfMonth(today);
        break;
      case 'ultimo_mes':
        const lastMonth = subDays(startOfMonth(today), 1);
        startDate = startOfMonth(lastMonth);
        endDate = endOfMonth(lastMonth);
        break;
      case 'custom':
        return; // No aplicar fechas automáticas
      default:
        return;
    }

    setFilters(prev => ({
      ...prev,
      fecha_inicio: format(startDate, 'yyyy-MM-dd'),
      fecha_fin: format(endDate, 'yyyy-MM-dd')
    }));
  };

  const handleCampanaToggle = (campanaId) => {
    const newSelected = selectedCampanas.includes(campanaId)
      ? selectedCampanas.filter(id => id !== campanaId)
      : [...selectedCampanas, campanaId];
    
    setSelectedCampanas(newSelected);
    setFilters(prev => ({
      ...prev,
      campana_ids: newSelected.length > 0 ? newSelected.join(',') : ''
    }));
  };

  const handleAgenteToggle = (agenteId) => {
    const newSelected = selectedAgentes.includes(agenteId)
      ? selectedAgentes.filter(id => id !== agenteId)
      : [...selectedAgentes, agenteId];
    
    setSelectedAgentes(newSelected);
    setFilters(prev => ({
      ...prev,
      agente_ids: newSelected.length > 0 ? newSelected.join(',') : ''
    }));
  };

  const handleLimpiar = () => {
    setSelectedCampanas([]);
    setSelectedAgentes([]);
    setSelectedRange('hoy');
    setFilters({});
    // Aplicar rango "Hoy" por defecto al limpiar
    setTimeout(() => applyDateRange('hoy'), 0);
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 mb-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-4">
        🔍 Filtros de Búsqueda
      </h3>

      {/* Filtros Predeterminados */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Rango de Fechas
        </label>
        <div className="grid grid-cols-2 md:grid-cols-7 gap-2">
          {[
            { value: 'hoy', label: 'Hoy' },
            { value: 'ayer', label: 'Ayer' },
            { value: '7_dias', label: 'Últimos 7 Días' },
            { value: '30_dias', label: 'Últimos 30 Días' },
            { value: 'este_mes', label: 'Este mes' },
            { value: 'ultimo_mes', label: 'Último Mes' },
            { value: 'custom', label: 'Custom Range' }
          ].map(range => (
            <button
              key={range.value}
              onClick={() => applyDateRange(range.value)}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                selectedRange === range.value
                  ? 'bg-green-500 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Fechas Personalizadas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Fecha Inicio
          </label>
          <input
            type="date"
            value={filters.fecha_inicio || ''}
            onChange={(e) => {
              handleChange('fecha_inicio', e.target.value);
              setSelectedRange('custom');
            }}
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
            onChange={(e) => {
              handleChange('fecha_fin', e.target.value);
              setSelectedRange('custom');
            }}
            max={getTodayDate()}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Filtros Adicionales */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        {/* Tipo de Llamada */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Tipo de Llamada
          </label>
          <select
            value={filters.tipo_llamada || ''}
            onChange={(e) => handleChange('tipo_llamada', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todas</option>
            <option value="entrantes">Entrantes</option>
            <option value="salientes">Salientes</option>
          </select>
        </div>

        {/* Campañas (Multi-select) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Campañas ({selectedCampanas.length} seleccionadas)
          </label>
          <div className="relative">
            <select
              multiple
              value={selectedCampanas}
              onChange={(e) => {
                const options = Array.from(e.target.selectedOptions);
                const values = options.map(opt => parseInt(opt.value));
                setSelectedCampanas(values);
                setFilters(prev => ({
                  ...prev,
                  campana_ids: values.length > 0 ? values.join(',') : ''
                }));
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 h-24 overflow-y-auto"
            >
              {campanas.map(c => (
                <option 
                  key={c.id} 
                  value={c.id}
                  className="py-1"
                >
                  {c.nombre}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Mantén Ctrl/Cmd para seleccionar múltiples
            </p>
          </div>
        </div>

        {/* Agentes (Multi-select) */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Agentes ({selectedAgentes.length} seleccionados)
          </label>
          <div className="relative">
            <select
              multiple
              value={selectedAgentes}
              onChange={(e) => {
                const options = Array.from(e.target.selectedOptions);
                const values = options.map(opt => parseInt(opt.value));
                setSelectedAgentes(values);
                setFilters(prev => ({
                  ...prev,
                  agente_ids: values.length > 0 ? values.join(',') : ''
                }));
              }}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 h-24 overflow-y-auto"
            >
              {agentes.map(a => (
                <option 
                  key={a.id} 
                  value={a.id}
                  className="py-1"
                >
                  {a.nombre}
                </option>
              ))}
            </select>
            <p className="text-xs text-gray-500 mt-1">
              Mantén Ctrl/Cmd para seleccionar múltiples
            </p>
          </div>
        </div>
      </div>

      {/* Botones de Acción */}
      <div className="mt-4 flex gap-3">
        <button
          onClick={onSearch}
          className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
        >
          🔍 Buscar
        </button>
        <button
          onClick={handleLimpiar}
          className="px-6 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors font-medium"
        >
          🔄 Limpiar
        </button>
      </div>
    </div>
  );
};

export default FilterSection;
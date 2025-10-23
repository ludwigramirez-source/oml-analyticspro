import React from 'react';

const TablaAgentes = ({ agentes }) => {
  const formatTiempo = (seconds) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${minutes}m`;
  };

  const getEstadoDot = (estado) => {
    const colors = {
      'disponible': 'bg-green-500',
      'pausa': 'bg-yellow-500',
      'offline': 'bg-gray-400'
    };
    return colors[estado] || 'bg-gray-400';
  };

  const getEstadoLabel = (estado) => {
    const labels = {
      'disponible': 'Disponible',
      'pausa': 'En Pausa',
      'offline': 'Desconectado'
    };
    return labels[estado] || 'Desconocido';
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-800">Rendimiento de Agentes</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Atendidas</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">No Atendidas</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">TMO</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Pausa</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tasa Atención</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {agentes.map((agente, idx) => (
              <tr key={idx} className="hover:bg-gray-50">
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{agente.nombre}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{agente.total_llamadas}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">{agente.atendidas}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">{agente.no_atendidas}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{agente.tmo}s</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{formatTiempo(agente.tiempo_pausa)}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{agente.tasa_atencion}%</td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center">
                    <span className={`w-2 h-2 rounded-full mr-2 ${getEstadoDot(agente.estado)}`}></span>
                    <span className="text-sm text-gray-600">{getEstadoLabel(agente.estado)}</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TablaAgentes;
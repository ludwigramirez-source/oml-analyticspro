import React from 'react';
import { ExportButton } from '../../utils/excelExport';

const TablaAgentes = ({ agentes }) => {
  const formatTiempo = (seconds) => {
    if (!seconds || seconds === 0) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200">
      <div className="px-6 py-4 border-b border-gray-200 bg-blue-50 flex justify-between items-center">
        <div>
          <h3 className="text-lg font-semibold text-blue-800">👥 Disponibilidad de Agentes</h3>
          <p className="text-sm text-blue-600 mt-1">
            Total: {agentes.length} agentes con actividad
          </p>
        </div>
        <ExportButton 
          data={agentes} 
          filename="disponibilidad_agentes"
          label="Exportar a Excel"
        />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50">Agente</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Username</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">N° Sesiones</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Primer Login</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Último Logout</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Sesión</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Prom. Sesión</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Al Habla</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">N° Pausas</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pausa Recreativa</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Pausa Productiva</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Prom. Pausa</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Espera</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Ocupación</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">TMO</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Llamadas Contestadas</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Tasa Atención</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {agentes.length === 0 ? (
              <tr>
                <td colSpan="17" className="px-6 py-8 text-center text-gray-500">
                  No hay datos de agentes para mostrar en el período seleccionado
                </td>
              </tr>
            ) : (
              agentes.map((agente, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white">{agente.nombre}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-600">{agente.username}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-gray-900">{agente.num_sesiones}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{agente.primer_login}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{agente.ultimo_logout}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_total_sesion)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_promedio_sesion)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-blue-600 font-medium">{formatTiempo(agente.tiempo_al_habla)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-gray-900">{agente.num_pausas}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-orange-600">{formatTiempo(agente.tiempo_pausa_recreativa)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-purple-600">{formatTiempo(agente.tiempo_pausa_productiva)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_promedio_pausa)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_total_espera)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      agente.ocupacion >= 80 ? 'bg-green-100 text-green-800' :
                      agente.ocupacion >= 50 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {agente.ocupacion}%
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tmo)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-green-600 font-medium">{agente.llamadas_contestadas}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      agente.tasa_atencion >= 80 ? 'bg-green-100 text-green-800' :
                      agente.tasa_atencion >= 60 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {agente.tasa_atencion}%
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default TablaAgentes;

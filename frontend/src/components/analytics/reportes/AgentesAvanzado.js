import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';
import { ExportButton } from '../../../utils/excelExport';

const AgentesAvanzado = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [totalSesiones, setTotalSesiones] = useState(null);
  const [heatmapData, setHeatmapData] = useState(null);
  const [disponibilidadAmpliada, setDisponibilidadAmpliada] = useState([]);
  const [disponibilidadAgentes, setDisponibilidadAgentes] = useState([]);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [sesiones, heatmap, disponibilidad, disponibilidadCompleta] = await Promise.all([
        analyticsApi.getTotalSesionesAgentes(filters).catch(() => null),
        analyticsApi.getDisponibilidadHeatmap(filters).catch(() => null),
        analyticsApi.getDisponibilidadAmpliada(filters).catch(() => []),
        analyticsApi.getRendimientoAgentes(filters).catch(() => [])
      ]);

      setTotalSesiones(sesiones);
      setHeatmapData(heatmap);
      setDisponibilidadAmpliada(disponibilidad);
      setDisponibilidadAgentes(disponibilidadCompleta);
    } catch (error) {
      console.error('Error loading agentes avanzado:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    if (!seconds) return '0m 0s';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`;
    return `${minutes}m ${secs}s`;
  };

  const formatTiempo = (seconds) => {
    if (!seconds) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold text-gray-800">👥 Análisis Avanzado de Agentes</h2>
        {disponibilidadAgentes && disponibilidadAgentes.length > 0 && (
          <ExportButton 
            data={disponibilidadAgentes.map(ag => ({
              'Agente': ag.nombre,
              'Llamadas Contestadas': ag.llamadas_contestadas,
              'Nº Sesiones': ag.num_sesiones,
              'Tiempo Total Sesión': formatTiempo(ag.tiempo_total_sesion),
              'Tiempo Promedio Sesión': formatTiempo(ag.tiempo_promedio_sesion),
              'Tiempo Al Habla': formatTiempo(ag.tiempo_al_habla),
              'Nº Pausas': ag.num_pausas,
              'Tiempo Pausa Recreativa': formatTiempo(ag.tiempo_pausa_recreativa),
              'Tiempo Pausa Productiva': formatTiempo(ag.tiempo_pausa_productiva),
              'Tiempo Total Pausa': formatTiempo(ag.tiempo_total_pausa),
              'Tiempo Promedio Pausa': formatTiempo(ag.tiempo_promedio_pausa),
              '% Ocupación': ag.ocupacion,
              'Primer Login': ag.primer_login,
              'Último Logout': ag.ultimo_logout
            }))} 
            filename="disponibilidad_agentes_completo"
            label="📥 Exportar Disponibilidad de Agentes"
          />
        )}
      </div>
      
      {/* Resumen de Sesiones */}
      {totalSesiones && (
        <div className="mb-6">
          <h3 className="text-lg font-bold text-gray-700 mb-4">Resumen de Sesiones</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <KPICard
              title="Total Agentes"
              value={totalSesiones.total_agentes}
              icon="👥"
            />
            <KPICard
              title="Tiempo Promedio"
              value={formatTime(totalSesiones.tiempo_promedio)}
              icon="⏱️"
            />
            <KPICard
              title="Tiempo Mínimo"
              value={formatTime(totalSesiones.tiempo_minimo)}
              icon="🔽"
            />
            <KPICard
              title="Tiempo Máximo"
              value={formatTime(totalSesiones.tiempo_maximo)}
              icon="🔼"
            />
            <KPICard
              title="Tiempo Total"
              value={formatTime(totalSesiones.tiempo_total)}
              icon="📊"
            />
          </div>
        </div>
      )}

      {/* Heatmap de Disponibilidad */}
      {heatmapData && heatmapData.matriz && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-bold text-gray-800">
              📅 Disponibilidad de Agentes por Día/Hora
            </h3>
            {disponibilidadAgentes && disponibilidadAgentes.length > 0 && (
              <ExportButton 
                data={disponibilidadAgentes.map(ag => ({
                  'Agente': ag.nombre,
                  'Llamadas Contestadas': ag.llamadas_contestadas,
                  'Nº Sesiones': ag.num_sesiones,
                  'Tiempo Total Sesión': formatTiempo(ag.tiempo_total_sesion),
                  'Tiempo Promedio Sesión': formatTiempo(ag.tiempo_promedio_sesion),
                  'Tiempo Al Habla': formatTiempo(ag.tiempo_al_habla),
                  'Nº Pausas': ag.num_pausas,
                  'Tiempo Pausa Recreativa': formatTiempo(ag.tiempo_pausa_recreativa),
                  'Tiempo Pausa Productiva': formatTiempo(ag.tiempo_pausa_productiva),
                  'Tiempo Total Pausa': formatTiempo(ag.tiempo_total_pausa),
                  'Tiempo Promedio Pausa': formatTiempo(ag.tiempo_promedio_pausa),
                  '% Ocupación': ag.ocupacion,
                  'Primer Login': ag.primer_login,
                  'Último Logout': ag.ultimo_logout
                }))} 
                filename="disponibilidad_agentes_heatmap"
                label="📥 Exportar Disponibilidad"
              />
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr>
                  <th className="px-2 py-2 text-xs font-medium text-gray-500 sticky left-0 bg-white">Día</th>
                  {heatmapData.horas.map(hora => (
                    <th key={hora} className="px-2 py-2 text-xs font-medium text-gray-500">
                      {hora}h
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {heatmapData.dias.map((dia, diaIdx) => (
                  <tr key={diaIdx}>
                    <td className="px-2 py-2 text-sm font-medium text-gray-700 sticky left-0 bg-white">
                      {dia}
                    </td>
                    {heatmapData.matriz[diaIdx].map((valor, horaIdx) => {
                      const color = valor === 0 ? 'bg-gray-100' :
                                   valor <= 2 ? 'bg-blue-200' :
                                   valor <= 5 ? 'bg-blue-400' :
                                   valor <= 10 ? 'bg-blue-600 text-white' :
                                   'bg-blue-800 text-white';
                      
                      return (
                        <td key={horaIdx} className={`px-2 py-2 text-center text-xs ${color}`}>
                          {valor > 0 ? valor : ''}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            * Los colores más oscuros indican mayor cantidad de agentes disponibles
          </p>
        </div>
      )}

      {/* Tabla de Disponibilidad de Agentes Completa */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-gray-800">
            Disponibilidad Detallada por Agente
          </h3>
          <ExportButton 
            data={disponibilidadAgentes.map(ag => ({
              'Agente': ag.nombre,
              'Llamadas Contestadas': ag.llamadas_contestadas,
              'Nº Sesiones': ag.num_sesiones,
              'Tiempo Total Sesión': formatTiempo(ag.tiempo_total_sesion),
              'Tiempo Al Habla': formatTiempo(ag.tiempo_al_habla),
              'Tiempo Total Pausa': formatTiempo(ag.tiempo_total_pausa),
              '% Ocupación': ag.ocupacion,
              'Primer Login': ag.primer_login,
              'Último Logout': ag.ultimo_logout
            }))} 
            filename="disponibilidad_agentes_detallada"
            label="Exportar a Excel"
          />
        </div>
        
        {disponibilidadAgentes && disponibilidadAgentes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Llamadas Contestadas</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Sesiones</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Sesión</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Al Habla</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Pausa</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Ocupación</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Primer Login</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Último Logout</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {disponibilidadAgentes.map((agente, idx) => (
                  <tr key={idx} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{agente.nombre}</td>
                    <td className="px-4 py-3 text-sm text-center text-green-600 font-bold">{agente.llamadas_contestadas}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{agente.num_sesiones}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{formatTime(agente.tiempo_total_sesion)}</td>
                    <td className="px-4 py-3 text-sm text-blue-600 font-medium">{formatTime(agente.tiempo_al_habla)}</td>
                    <td className="px-4 py-3 text-sm text-orange-600">{formatTime(agente.tiempo_total_pausa)}</td>
                    <td className="px-4 py-3 text-sm text-center">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        agente.ocupacion >= 80 ? 'bg-green-100 text-green-800' :
                        agente.ocupacion >= 50 ? 'bg-yellow-100 text-yellow-800' :
                        'bg-red-100 text-red-800'
                      }`}>
                        {agente.ocupacion}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900">{agente.primer_login}</td>
                    <td className="px-4 py-3 text-sm text-gray-900">{agente.ultimo_logout}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-12 text-gray-500">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-2">No hay datos disponibles para mostrar</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentesAvanzado;
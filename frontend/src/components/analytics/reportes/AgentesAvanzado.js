import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';
import { ExportButton } from '../../../utils/excelExport';

const AgentesAvanzado = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [totalSesiones, setTotalSesiones] = useState(null);
  const [heatmapData, setHeatmapData] = useState(null);
  const [disponibilidadAgentes, setDisponibilidadAgentes] = useState([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedAgente, setSelectedAgente] = useState(null);
  const [detallesSesiones, setDetallesSesiones] = useState([]);
  const [detallesPausas, setDetallesPausas] = useState([]);
  const [loadingDetalles, setLoadingDetalles] = useState(false);
  const [activeModalTab, setActiveModalTab] = useState('sesiones');

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [heatmap, disponibilidadCompleta] = await Promise.all([
        analyticsApi.getDisponibilidadHeatmap(filters).catch(() => null),
        analyticsApi.getRendimientoAgentes(filters).catch(() => [])
      ]);

      setHeatmapData(heatmap);
      setDisponibilidadAgentes(disponibilidadCompleta);
      
      // Calcular resumen de sesiones desde los datos de disponibilidad
      if (disponibilidadCompleta && disponibilidadCompleta.length > 0) {
        const agentesConSesiones = disponibilidadCompleta.filter(ag => ag.num_sesiones > 0);
        const totalAgentes = agentesConSesiones.length;
        
        const tiemposSesion = agentesConSesiones.map(ag => ag.tiempo_total_sesion);
        const tiempoTotal = tiemposSesion.reduce((sum, t) => sum + t, 0);
        const tiempoPromedio = totalAgentes > 0 ? Math.floor(tiempoTotal / totalAgentes) : 0;
        const tiempoMinimo = tiemposSesion.length > 0 ? Math.min(...tiemposSesion) : 0;
        const tiempoMaximo = tiemposSesion.length > 0 ? Math.max(...tiemposSesion) : 0;
        
        setTotalSesiones({
          total_agentes: totalAgentes,
          tiempo_promedio: tiempoPromedio,
          tiempo_minimo: tiempoMinimo,
          tiempo_maximo: tiempoMaximo,
          tiempo_total: tiempoTotal
        });
      } else {
        setTotalSesiones(null);
      }
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

  const abrirDetalles = async (agente) => {
    setSelectedAgente(agente);
    setModalOpen(true);
    setLoadingDetalles(true);
    setActiveModalTab('sesiones');
    
    try {
      // Cargar detalles de sesiones y pausas del agente
      const [sesiones, pausas] = await Promise.all([
        analyticsApi.getDetalleSesionesAgente(agente.agente_id, filters).catch(() => []),
        analyticsApi.getDetallePausasAgente(agente.agente_id, filters).catch(() => [])
      ]);
      
      setDetallesSesiones(sesiones);
      setDetallesPausas(pausas);
    } catch (error) {
      console.error('Error cargando detalles:', error);
    } finally {
      setLoadingDetalles(false);
    }
  };

  const cerrarModal = () => {
    setModalOpen(false);
    setSelectedAgente(null);
    setDetallesSesiones([]);
    setDetallesPausas([]);
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
      <h2 className="text-2xl font-bold text-gray-800 mb-6">👥 Análisis Avanzado de Agentes</h2>
      
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

      {/* Tabla de Disponibilidad de Agentes Simplificada */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-gray-800">
            📊 Disponibilidad por Agente
          </h3>
          <ExportButton 
            data={disponibilidadAgentes.map(ag => ({
              'Agente': ag.nombre,
              'Nº Sesiones': ag.num_sesiones,
              'Tiempo Total Sesión': formatTiempo(ag.tiempo_total_sesion),
              'Nº Pausas': ag.num_pausas,
              'Tiempo Pausa Recreativa': formatTiempo(ag.tiempo_pausa_recreativa),
              'Tiempo Pausa Productiva': formatTiempo(ag.tiempo_pausa_productiva),
              'Tiempo Total Pausa': formatTiempo(ag.tiempo_total_pausa)
            }))} 
            filename="disponibilidad_agentes_resumen"
            label="Exportar Resumen"
          />
        </div>
        
        {disponibilidadAgentes && disponibilidadAgentes.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agente</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Nº Sesiones</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Sesión</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Nº Pausas</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">T. Pausa Recreativa</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">T. Pausa Productiva</th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Pausa</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Acciones</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {disponibilidadAgentes.map((agente, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{agente.nombre}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{agente.num_sesiones}</td>
                    <td className="px-4 py-3 text-sm text-blue-600 font-medium">{formatTime(agente.tiempo_total_sesion)}</td>
                    <td className="px-4 py-3 text-sm text-center text-gray-900">{agente.num_pausas}</td>
                    <td className="px-4 py-3 text-sm text-orange-600">{formatTime(agente.tiempo_pausa_recreativa)}</td>
                    <td className="px-4 py-3 text-sm text-purple-600">{formatTime(agente.tiempo_pausa_productiva)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 font-medium">{formatTime(agente.tiempo_total_pausa)}</td>
                    <td className="px-4 py-3 text-sm text-center">
                      <button
                        onClick={() => abrirDetalles(agente)}
                        className="inline-flex items-center px-3 py-1 bg-blue-50 hover:bg-blue-100 text-blue-600 rounded-md transition-colors"
                        title="Ver detalles"
                      >
                        <span className="mr-1">👁️</span>
                        Ver Detalles
                      </button>
                    </td>
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

      {/* Modal de Detalles */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-5xl w-full max-h-[90vh] overflow-hidden">
            {/* Header del Modal */}
            <div className="bg-gradient-to-r from-blue-600 to-blue-700 px-6 py-4 flex justify-between items-center">
              <h3 className="text-xl font-bold text-white">
                📋 Detalles de {selectedAgente?.nombre}
              </h3>
              <button
                onClick={cerrarModal}
                className="text-white hover:text-gray-200 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Tabs del Modal */}
            <div className="border-b border-gray-200 bg-gray-50">
              <div className="flex px-6">
                <button
                  onClick={() => setActiveModalTab('sesiones')}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeModalTab === 'sesiones'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  📅 Sesiones ({detallesSesiones.length})
                </button>
                <button
                  onClick={() => setActiveModalTab('pausas')}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ml-2 ${
                    activeModalTab === 'pausas'
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  ⏸️ Pausas ({detallesPausas.length})
                </button>
              </div>
            </div>

            {/* Contenido del Modal */}
            <div className="p-6 overflow-y-auto max-h-[calc(90vh-180px)]">
              {loadingDetalles ? (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
                </div>
              ) : (
                <>
                  {/* Tab de Sesiones */}
                  {activeModalTab === 'sesiones' && (
                    <div>
                      <div className="flex justify-between items-center mb-4">
                        <h4 className="text-md font-semibold text-gray-700">Detalle de Sesiones</h4>
                        <ExportButton 
                          data={detallesSesiones}
                          filename={`sesiones_${selectedAgente?.nombre.replace(/\s+/g, '_')}`}
                          label="Descargar Sesiones"
                        />
                      </div>
                      {detallesSesiones.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha Inicio</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha Fin</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Duración</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {detallesSesiones.map((sesion, idx) => (
                                <tr key={idx} className="hover:bg-gray-50">
                                  <td className="px-3 py-2 text-gray-900">{sesion.fecha_inicio}</td>
                                  <td className="px-3 py-2 text-gray-900">{sesion.fecha_fin}</td>
                                  <td className="px-3 py-2 text-blue-600 font-medium">{sesion.duracion}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-center py-8 text-gray-500">No hay sesiones registradas</p>
                      )}
                    </div>
                  )}

                  {/* Tab de Pausas */}
                  {activeModalTab === 'pausas' && (
                    <div>
                      <div className="flex justify-between items-center mb-4">
                        <h4 className="text-md font-semibold text-gray-700">Detalle de Pausas</h4>
                        <ExportButton 
                          data={detallesPausas}
                          filename={`pausas_${selectedAgente?.nombre.replace(/\s+/g, '_')}`}
                          label="Descargar Pausas"
                        />
                      </div>
                      {detallesPausas.length > 0 ? (
                        <div className="overflow-x-auto">
                          <table className="min-w-full divide-y divide-gray-200 text-sm">
                            <thead className="bg-gray-50">
                              <tr>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Tipo</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Nombre</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha Inicio</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Fecha Fin</th>
                                <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Duración</th>
                              </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                              {detallesPausas.map((pausa, idx) => (
                                <tr key={idx} className="hover:bg-gray-50">
                                  <td className="px-3 py-2">
                                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                                      pausa.tipo === 'R' ? 'bg-orange-100 text-orange-800' : 'bg-purple-100 text-purple-800'
                                    }`}>
                                      {pausa.tipo === 'R' ? 'Recreativa' : 'Productiva'}
                                    </span>
                                  </td>
                                  <td className="px-3 py-2 text-gray-900">{pausa.nombre}</td>
                                  <td className="px-3 py-2 text-gray-900">{pausa.fecha_inicio}</td>
                                  <td className="px-3 py-2 text-gray-900">{pausa.fecha_fin}</td>
                                  <td className="px-3 py-2 text-gray-900 font-medium">{pausa.duracion}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      ) : (
                        <p className="text-center py-8 text-gray-500">No hay pausas registradas</p>
                      )}
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Footer del Modal */}
            <div className="bg-gray-50 px-6 py-3 flex justify-end border-t border-gray-200">
              <button
                onClick={cerrarModal}
                className="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-700 rounded-md transition-colors"
              >
                Cerrar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentesAvanzado;
import React from 'react';
import { ExportButton } from '../../utils/excelExport';
import ApexChart from './ApexChart';

const TablaAgentes = ({ agentes, loading }) => {
  // Log detallado para debugging
  console.log('🔍 TablaAgentes - agentes recibidos:', agentes);
  console.log('🔍 TablaAgentes - loading:', loading);
  if (agentes && agentes.length > 0) {
    console.log('🔍 TablaAgentes - Primer agente completo:', JSON.stringify(agentes[0]));
  }
  
  const formatTiempo = (seconds) => {
    if (!seconds || seconds === 0) return '00:00:00';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  // Solo construir el gráfico si hay datos
  const getChartData = () => {
    console.log('🔍 getChartData called - agentes:', agentes);
    console.log('🔍 agentes length:', agentes ? agentes.length : 'null');
    
    if (!agentes || agentes.length === 0) {
      console.log('❌ No agentes - returning null');
      return null;
    }

    // Preparar datos para el gráfico de barras (ordenado por llamadas contestadas)
    const agentesOrdenados = [...agentes]
      .sort((a, b) => (b.llamadas_contestadas || 0) - (a.llamadas_contestadas || 0));
    
    console.log('📊 agentesOrdenados:', agentesOrdenados.map(a => ({
      nombre: a.nombre,
      llamadas: a.llamadas_contestadas
    })));
    
    if (agentesOrdenados.length === 0) {
      console.log('❌ No agentes ordenados - returning null');
      return null;
    }

    const chartConfig = {
      series: [{
        name: 'Llamadas Contestadas',
        data: agentesOrdenados.map(a => a.llamadas_contestadas || 0)
      }],
      options: {
        chart: {
          type: 'bar',
          height: 350,
          toolbar: {
            show: true,
            tools: {
              download: true,
              zoom: false,
              zoomin: false,
              zoomout: false,
              pan: false,
              reset: false
            }
          }
        },
        plotOptions: {
          bar: {
            borderRadius: 4,
            horizontal: false,
            distributed: true,
            dataLabels: {
              position: 'top'
            }
          }
        },
        colors: ['#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899', '#14B8A6', '#F97316'],
        dataLabels: {
          enabled: true,
          offsetY: -20,
          style: {
            fontSize: '12px',
            colors: ['#304758']
          }
        },
        xaxis: {
          categories: agentesOrdenados.map(a => a.nombre ? a.nombre.split(' ')[0] : 'Sin nombre'),
          labels: {
            style: {
              fontSize: '11px'
            },
            rotate: -45,
            rotateAlways: true
          }
        },
        yaxis: {
          title: {
            text: 'Llamadas Contestadas'
          }
        },
        title: {
          text: '📊 Llamadas Contestadas por Agente',
          align: 'center',
          style: {
            fontSize: '16px',
            fontWeight: 'bold',
            color: '#1E40AF'
          }
        },
        legend: {
          show: false
        },
        grid: {
          borderColor: '#e7e7e7',
          row: {
            colors: ['#f3f3f3', 'transparent'],
            opacity: 0.5
          }
        }
      }
    };
    
    console.log('✅ Returning chart config with data:', chartConfig.series[0].data);
    return chartConfig;
  };

  const chartData = getChartData();
  console.log('📈 chartData result:', chartData ? 'HAS DATA' : 'NULL');

  if (loading) {
    return (
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200 bg-blue-50">
          <h3 className="text-lg font-semibold text-blue-800">👥 Disponibilidad de Agentes</h3>
        </div>
        <div className="flex flex-col items-center justify-center py-20">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
          <p className="mt-4 text-gray-600 font-medium">Generando reporte de agentes...</p>
          <p className="mt-2 text-sm text-gray-500">Por favor espere, esto puede tomar unos segundos</p>
        </div>
      </div>
    );
  }

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
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-gray-50 z-10">Agente</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Llamadas Contestadas</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Nº de Sesiones</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Sesión</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Promedio Sesión</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Al Habla</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Nº Pausas</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Total Pausa</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tiempo Promedio Pausa</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">% Ocupación</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Primer Login</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Último Logout</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {agentes.length === 0 ? (
              <tr>
                <td colSpan="12" className="px-6 py-8 text-center text-gray-500">
                  No hay datos de agentes para mostrar en el período seleccionado
                </td>
              </tr>
            ) : (
              agentes.map((agente, idx) => (
                <tr key={idx} className="hover:bg-gray-50">
                  <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900 sticky left-0 bg-white z-10">{agente.nombre}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-green-600 font-medium text-lg">{agente.llamadas_contestadas}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-gray-900">{agente.num_sesiones}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_total_sesion)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_promedio_sesion)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-blue-600 font-medium">{formatTiempo(agente.tiempo_al_habla)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center text-gray-900">{agente.num_pausas}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-orange-600">{formatTiempo(agente.tiempo_total_pausa)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{formatTiempo(agente.tiempo_promedio_pausa)}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-center">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      agente.ocupacion >= 80 ? 'bg-green-100 text-green-800' :
                      agente.ocupacion >= 50 ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {agente.ocupacion}%
                    </span>
                  </td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{agente.primer_login}</td>
                  <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">{agente.ultimo_logout}</td>
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

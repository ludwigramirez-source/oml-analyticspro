import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import analyticsApi from '../../services/analyticsApi';
import KPICard from './KPICard';
import FilterSection from './FilterSection';
import ChartCard from './ChartCard';
import TablaLlamadas from './TablaLlamadas';
import TablaAgentes from './TablaAgentes';

const AnalyticsDashboard = () => {
  // Estados
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('distribucion');
  const [filters, setFilters] = useState({});
  const [lastUpdate, setLastUpdate] = useState(new Date());

  // Datos
  const [kpis, setKpis] = useState({});
  const [distribucionData, setDistribucionData] = useState(null);
  const [evolucionData, setEvolucionData] = useState(null);
  const [nivelServicioData, setNivelServicioData] = useState(null);
  const [causasData, setCausasData] = useState(null);
  const [llamadasDetalladas, setLlamadasDetalladas] = useState([]);
  const [agentesData, setAgentesData] = useState([]);
  const [ocupacionData, setOcupacionData] = useState(null);
  const [campanasData, setCampanasData] = useState([]);

  // Listas
  const [campanas, setCampanas] = useState([]);
  const [agentes, setAgentes] = useState([]);

  // Cargar listas iniciales
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      console.log('🔵 Iniciando carga de datos...');
      
      // Cargar listas de campañas y agentes
      try {
        const campanasRes = await analyticsApi.getCampanas();
        console.log('✅ Campañas cargadas:', campanasRes);
        setCampanas(campanasRes || []);
      } catch (e) {
        console.error('Error campañas:', e);
        setCampanas([]);
      }
      
      try {
        const agentesRes = await analyticsApi.getAgentes();
        console.log('✅ Agentes cargados:', agentesRes);
        setAgentes(agentesRes || []);
      } catch (e) {
        console.error('Error agentes:', e);
        setAgentes([]);
      }
      
      // Cargar datos del dashboard
      await loadDashboardData();
    } catch (error) {
      console.error('❌ Error loading initial data:', error);
      setLoading(false);
    }
  };

  const loadDashboardData = async () => {
    setLoading(true);
    try {
      // Cargar KPIs y datos principales
      const [
        kpisRes,
        distribRes,
        evolRes,
        nivelRes,
        causasRes,
        llamadasRes,
        agentesRes,
        ocupRes,
        campanasRes
      ] = await Promise.all([
        analyticsApi.getKPIs(filters),
        analyticsApi.getDistribucionLlamadas(filters),
        analyticsApi.getEvolucionHora(filters),
        analyticsApi.getNivelServicio(filters),
        analyticsApi.getCausasNoAtencion(filters),
        analyticsApi.getLlamadasDetalladas(1, 50, filters),
        analyticsApi.getRendimientoAgentes(filters),
        analyticsApi.getOcupacionAgentes(filters),
        analyticsApi.getDistribucionCampanas(filters)
      ]);

      setKpis(kpisRes);
      setDistribucionData(prepareDistribucionChart(distribRes));
      setEvolucionData(prepareEvolucionChart(evolRes));
      setNivelServicioData(prepareNivelServicioChart(nivelRes));
      setCausasData(prepareCausasChart(causasRes));
      setLlamadasDetalladas(llamadasRes.data || []);
      setAgentesData(agentesRes);
      setOcupacionData(prepareOcupacionChart(ocupRes));
      setCampanasData(campanasRes);

      setLastUpdate(new Date());
    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Preparar datos para gráficos
  const prepareDistribucionChart = (data) => ({
    labels: data.labels,
    datasets: [{
      data: data.data,
      backgroundColor: [
        'rgba(52, 168, 83, 0.8)',
        'rgba(234, 134, 0, 0.8)',
        'rgba(234, 67, 53, 0.8)'
      ],
      borderWidth: 0
    }]
  });

  const prepareEvolucionChart = (data) => ({
    labels: data.labels,
    datasets: [{
      label: 'Llamadas',
      data: data.data,
      borderColor: 'rgba(26, 115, 232, 1)',
      backgroundColor: 'rgba(26, 115, 232, 0.1)',
      tension: 0.4,
      fill: true
    }]
  });

  const prepareNivelServicioChart = (data) => ({
    labels: data.labels,
    datasets: [{
      label: 'Llamadas',
      data: data.data,
      backgroundColor: 'rgba(26, 115, 232, 0.8)'
    }]
  });

  const prepareCausasChart = (data) => ({
    labels: data.labels,
    datasets: [{
      data: data.data,
      backgroundColor: [
        'rgba(234, 67, 53, 0.8)',
        'rgba(234, 134, 0, 0.8)',
        'rgba(251, 188, 4, 0.8)',
        'rgba(26, 115, 232, 0.8)',
        'rgba(52, 168, 83, 0.8)'
      ]
    }]
  });

  const prepareOcupacionChart = (data) => {
    if (!data || !data.datasets) return null;
    return {
      labels: data.labels,
      datasets: data.datasets.map(ds => ({
        ...ds,
        borderWidth: 0
      }))
    };
  };

  const handleSearch = () => {
    loadDashboardData();
  };

  if (loading && Object.keys(kpis).length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando datos...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200 mb-6">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">OmniLeads Analytics</h1>
              <p className="text-sm text-gray-600 mt-1">
                Última actualización: {format(lastUpdate, 'dd/MM/yyyy HH:mm:ss')}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={loadDashboardData}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors text-sm"
              >
                🔄 Actualizar
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 pb-8">
        {/* Filtros */}
        <FilterSection
          filters={filters}
          setFilters={setFilters}
          campanas={campanas}
          agentes={agentes}
          onSearch={handleSearch}
        />

        {/* KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          <KPICard
            title="Llamadas Totales"
            value={kpis.llamadas_totales?.valor || 0}
            icon="📞"
            change={kpis.llamadas_totales?.cambio || '0%'}
            trend={kpis.llamadas_totales?.tendencia || 'neutral'}
          />
          <KPICard
            title="Llamadas Atendidas"
            value={kpis.llamadas_atendidas?.valor || 0}
            icon="✅"
            change={kpis.llamadas_atendidas?.cambio || '0%'}
            trend={kpis.llamadas_atendidas?.tendencia || 'neutral'}
          />
          <KPICard
            title="Llamadas Perdidas"
            value={kpis.llamadas_perdidas?.valor || 0}
            icon="❌"
            change={kpis.llamadas_perdidas?.cambio || '0%'}
            trend={kpis.llamadas_perdidas?.tendencia || 'neutral'}
          />
          <KPICard
            title="TMO Promedio"
            value={kpis.tmo_promedio?.valor || 0}
            icon="⏱️"
            change={kpis.tmo_promedio?.cambio || '0%'}
            trend={kpis.tmo_promedio?.tendencia || 'neutral'}
            format="segundos"
          />
          <KPICard
            title="Tiempo de Espera"
            value={kpis.tiempo_espera?.valor || 0}
            icon="⏳"
            change={kpis.tiempo_espera?.cambio || '0%'}
            trend={kpis.tiempo_espera?.tendencia || 'neutral'}
            format="segundos"
          />
          <KPICard
            title="Service Level"
            value={kpis.service_level?.valor || 0}
            icon="🎯"
            change={kpis.service_level?.cambio || '0%'}
            trend={kpis.service_level?.tendencia || 'neutral'}
            format="porcentaje"
          />
          <KPICard
            title="Agentes Activos"
            value={kpis.agentes_activos?.valor || 0}
            icon="👥"
            change={kpis.agentes_activos?.cambio || '0%'}
            trend={kpis.agentes_activos?.tendencia || 'neutral'}
          />
          <KPICard
            title="Ocupación"
            value={kpis.ocupacion?.valor || 0}
            icon="📊"
            change={kpis.ocupacion?.cambio || '0%'}
            trend={kpis.ocupacion?.tendencia || 'neutral'}
            format="porcentaje"
          />
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 mb-6">
          <div className="border-b border-gray-200">
            <nav className="flex -mb-px">
              {[
                { id: 'distribucion', label: 'Distribución' },
                { id: 'atendidas', label: 'Llamadas Atendidas' },
                { id: 'no-atendidas', label: 'No Atendidas' },
                { id: 'agentes', label: 'Agentes' },
                { id: 'campanas', label: 'Campañas' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-300'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          <div className="p-6">
            {/* Tab: Distribución */}
            {activeTab === 'distribucion' && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {distribucionData && (
                  <ChartCard
                    title="Distribución de Llamadas"
                    type="doughnut"
                    data={distribucionData}
                  />
                )}
                {evolucionData && (
                  <ChartCard
                    title="Evolución por Hora"
                    type="line"
                    data={evolucionData}
                  />
                )}
              </div>
            )}

            {/* Tab: Llamadas Atendidas */}
            {activeTab === 'atendidas' && (
              <div>
                {nivelServicioData && (
                  <div className="mb-6">
                    <ChartCard
                      title="Nivel de Servicio (Tiempo de Espera)"
                      type="bar"
                      data={nivelServicioData}
                    />
                  </div>
                )}
                <TablaLlamadas llamadas={llamadasDetalladas} />
              </div>
            )}

            {/* Tab: No Atendidas */}
            {activeTab === 'no-atendidas' && (
              <div>
                {causasData && (
                  <div className="mb-6 max-w-2xl mx-auto">
                    <ChartCard
                      title="Causas de No Atención"
                      type="pie"
                      data={causasData}
                    />
                  </div>
                )}
              </div>
            )}

            {/* Tab: Agentes */}
            {activeTab === 'agentes' && (
              <div>
                {ocupacionData && (
                  <div className="mb-6">
                    <ChartCard
                      title="Ocupación de Agentes (Top 10)"
                      type="bar"
                      data={ocupacionData}
                      options={{
                        scales: {
                          x: { stacked: true },
                          y: { stacked: true }
                        }
                      }}
                    />
                  </div>
                )}
                <TablaAgentes agentes={agentesData} />
              </div>
            )}

            {/* Tab: Campañas */}
            {activeTab === 'campanas' && (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaña</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Atendidas</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">No Atendidas</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tasa Atención</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {campanasData.map((c, idx) => (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.campana}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{c.total}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">{c.atendidas}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">{c.no_atendidas}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{c.tasa_atencion}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AnalyticsDashboard;

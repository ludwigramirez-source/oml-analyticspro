import React, { useState, useEffect } from 'react';
import { format, subDays } from 'date-fns';
import * as XLSX from 'xlsx';
import analyticsApi from '../../services/analyticsApi';
import KPICard from './KPICard';
import FilterSection from './FilterSection';
import ApexChart from './ApexChart';
import EntradasSalidas from './EntradasSalidas';
import TablaLlamadas from './TablaLlamadas';
import TablaAgentes from './TablaAgentes';
import TablaAbandonadas from './TablaAbandonadas';
import DistribucionAvanzada from './reportes/DistribucionAvanzada';
import LlamadasSalientes from './reportes/LlamadasSalientes';
import CausasDetalladas from './reportes/CausasDetalladas';
import AgentesAvanzado from './reportes/AgentesAvanzado';
import Transferencias from './reportes/Transferencias';
import TablaDistribucionHoraria from './reportes/TablaDistribucionHoraria';
import Gestiones from './reportes/Gestiones';

const DashboardMejorado = () => {
  // Estados
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('resumen');
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [dataLoaded, setDataLoaded] = useState(false);
  
  // Calcular filtros por defecto: HOY
  const [filters, setFilters] = useState(() => {
    const today = new Date();

    return {
      fecha_inicio: format(today, 'yyyy-MM-dd'),
      fecha_fin: format(today, 'yyyy-MM-dd')
    };
  });

  // Datos
  const [kpis, setKpis] = useState({});
  const [llamadasPorTipo, setLlamadasPorTipo] = useState(null);
  const [distribucionData, setDistribucionData] = useState([]);
  const [distribucionPorTipo, setDistribucionPorTipo] = useState(null);
  const [evolucionData, setEvolucionData] = useState([]);
  const [horariaData, setHorariaData] = useState([]);
  const [nivelServicioData, setNivelServicioData] = useState([]);
  const [campanasConAlerta, setCampanasConAlerta] = useState([]);
  const [llamadasDetalladas, setLlamadasDetalladas] = useState([]);
  const [llamadasAbandonadas, setLlamadasAbandonadas] = useState([]);
  const [agentesData, setAgentesData] = useState([]);

  // Listas
  const [campanas, setCampanas] = useState([]);
  const [agentes, setAgentes] = useState([]);

  // Cargar datos iniciales solo una vez al montar el componente
  useEffect(() => {
    loadInitialData();
  }, []); // Solo se ejecuta una vez al montar

  // Recargar datos cuando cambia el tab
  useEffect(() => {
    if (activeTab !== 'resumen' && dataLoaded) {
      // El tab cambió, pero ya tenemos datos cargados, no hacer nada
    }
  }, [activeTab]);

  // Cargar llamadas atendidas solo cuando se abre la pestaña
  useEffect(() => {
    if (activeTab === 'atendidas' && llamadasDetalladas.length === 0) {
      console.log('🔄 Cargando TODAS las llamadas atendidas...');
      loadAllLlamadasAtendidas();
    }
  }, [activeTab]);

  // Cargar llamadas abandonadas solo cuando se abre la pestaña
  useEffect(() => {
    if (activeTab === 'abandonadas' && llamadasAbandonadas.length === 0) {
      console.log('🔄 Cargando TODAS las llamadas abandonadas...');
      loadAllLlamadasAbandonadas();
    }
  }, [activeTab]);

  const loadInitialData = async () => {
    try {
      console.log('🔵 Cargando datos iniciales...');
      setLoading(true);
      
      const [campanasRes, agentesRes] = await Promise.all([
        analyticsApi.getCampanas().catch((err) => {
          console.warn('⚠️ Error cargando campañas:', err);
          return [];
        }),
        analyticsApi.getAgentes().catch((err) => {
          console.warn('⚠️ Error cargando agentes:', err);
          return [];
        })
      ]);
      
      setCampanas(campanasRes);
      setAgentes(agentesRes);
      
      await loadDashboardData();
    } catch (error) {
      console.error('❌ Error loading initial data:', error);
      setLoading(false);
    }
  };

  const loadDashboardData = async () => {
    setLoading(true);
    console.log('📊 Cargando datos del dashboard...');

    // Limpiar llamadas detalladas para forzar recarga con nuevos filtros
    setLlamadasDetalladas([]);
    setLlamadasAbandonadas([]);

    try {
      // Cargar KPIs mejorados
      const kpisRes = await analyticsApi.getKPIs(filters);
      console.log('✅ KPIs recibidos:', kpisRes);
      setKpis(kpisRes);

      // Cargar llamadas por tipo (CRÍTICO - Power BI)
      const tipoRes = await analyticsApi.getLlamadasPorTipo(filters);
      console.log('✅ Llamadas por tipo:', tipoRes);
      setLlamadasPorTipo(tipoRes);

      // Cargar distribución
      const distribRes = await analyticsApi.getDistribucionLlamadas(filters);
      console.log('✅ Distribución:', distribRes);
      setDistribucionData(prepareDistribucion(distribRes));

      // Cargar distribución por tipo (entrantes vs salientes)
      try {
        const distribTipoRes = await analyticsApi.getDistribucionPorTipo(filters);
        console.log('✅ Distribución por tipo recibida:', distribTipoRes);
        console.log('📊 Datos entrantes:', distribTipoRes?.entrantes);
        console.log('📊 Datos salientes:', distribTipoRes?.salientes);
        setDistribucionPorTipo(distribTipoRes);
      } catch (err) {
        console.error('❌ Error en distribución por tipo:', err);
        setDistribucionPorTipo(null);
      }

      // Cargar evolución por hora
      try {
        const evolRes = await analyticsApi.getEvolucionHora(filters);
        console.log('✅ Evolución:', evolRes);
        setEvolucionData(prepareEvolucion(evolRes));
      } catch (err) {
        console.warn('⚠️ Error en evolución por hora:', err);
        setEvolucionData([]);
      }

      // Cargar distribución horaria detallada
      try {
        const horariaRes = await analyticsApi.getDistribucionHorariaDetallada(filters);
        console.log('✅ Horaria detallada:', horariaRes);
        setHorariaData(prepareHoraria(horariaRes));
      } catch (err) {
        console.warn('⚠️ Error en distribución horaria:', err);
        setHorariaData([]);
      }

      // Cargar nivel de servicio
      try {
        const nivelRes = await analyticsApi.getNivelServicio(filters);
        console.log('✅ Nivel servicio:', nivelRes);
        setNivelServicioData(prepareNivelServicio(nivelRes));
      } catch (err) {
        console.warn('⚠️ Error en nivel de servicio:', err);
        setNivelServicioData([]);
      }

      // Cargar campañas con alertas
      const campanasRes = await analyticsApi.getNivelAtencionCampanas(filters);
      console.log('✅ Campañas con alertas:', campanasRes);
      setCampanasConAlerta(campanasRes);

      // Cargar agentes con timeout de 10 segundos
      try {
        console.log('📊 Intentando cargar rendimiento de agentes...');
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Timeout de 10 segundos')), 10000)
        );
        const agentesPromise = analyticsApi.getRendimientoAgentes(filters);
        
        const agentesRes = await Promise.race([agentesPromise, timeoutPromise]);
        console.log('✅ Agentes cargados:', agentesRes);
        setAgentesData(agentesRes || []);
      } catch (err) {
        console.warn('⚠️ Timeout o error cargando agentes:', err.message);
        setAgentesData([]);  // Establecer array vacío
      }

      setLastUpdate(new Date());
      console.log('✅ Datos principales cargados - mostrando dashboard');

      // Ocultar loading para mostrar gráficos inmediatamente
      setLoading(false);

      // ✅ OPTIMIZACIÓN: Las llamadas detalladas se cargarán solo cuando el usuario abra la pestaña
      // (Eliminado: loadDetailedCalls que hacía 63 peticiones HTTP)

    } catch (error) {
      console.error('❌ Error loading dashboard data:', error);
      setLoading(false);
    }
  };

  // Cargar TODAS las llamadas atendidas (paginación automática)
  const loadAllLlamadasAtendidas = async () => {
    try {
      console.log(`📋 Cargando TODAS las llamadas atendidas...`);

      const allLlamadas = [];
      let currentPage = 1;
      let totalPages = 1;
      const perPage = 200; // Máximo permitido por el backend

      // Cargar páginas hasta obtener todas las llamadas
      while (currentPage <= totalPages) {
        console.log(`📄 Cargando página ${currentPage}/${totalPages}...`);
        const result = await analyticsApi.getLlamadasAtendidas(currentPage, perPage, filters);

        // Agregar datos de esta página
        allLlamadas.push(...(result.data || []));

        // Actualizar total de páginas (solo en la primera iteración)
        if (currentPage === 1) {
          totalPages = result.total_pages || 1;
          console.log(`📊 Total de registros: ${result.total}, páginas: ${totalPages}`);
        }

        currentPage++;
      }

      setLlamadasDetalladas(allLlamadas);
      console.log(`✅ Cargadas ${allLlamadas.length} llamadas atendidas en total`);
    } catch (error) {
      console.error('❌ Error cargando llamadas atendidas:', error);
      setLlamadasDetalladas([]);
    }
  };

  const loadAllLlamadasAbandonadas = async () => {
    try {
      console.log(`📋 Cargando TODAS las llamadas abandonadas...`);

      const allLlamadas = [];
      let currentPage = 1;
      let totalPages = 1;
      const perPage = 200; // Máximo permitido por el backend

      // Cargar páginas hasta obtener todas las llamadas
      while (currentPage <= totalPages) {
        console.log(`📄 Cargando página ${currentPage}/${totalPages}...`);
        const result = await analyticsApi.getLlamadasAbandonadas(currentPage, perPage, filters);

        // Agregar datos de esta página
        allLlamadas.push(...(result.data || []));

        // Actualizar total de páginas (solo en la primera iteración)
        if (currentPage === 1) {
          totalPages = result.total_pages || 1;
          console.log(`📊 Total de registros: ${result.total}, páginas: ${totalPages}`);
        }

        currentPage++;
      }

      setLlamadasAbandonadas(allLlamadas);
      console.log(`✅ Cargadas ${allLlamadas.length} llamadas abandonadas en total`);
    } catch (error) {
      console.error('❌ Error cargando llamadas abandonadas:', error);
      setLlamadasAbandonadas([]);
    }
  };

  // Preparar datos para gráficos
  const prepareDistribucion = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      value: data.data[idx] || 0
    }));
  };

  const prepareDistribucionEntrantes = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      value: data.data[idx] || 0
    }));
  };

  const prepareDistribucionSalientes = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      value: data.data[idx] || 0
    }));
  };

  const prepareEvolucion = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      value: data.data[idx] || 0
    }));
  };

  const prepareHoraria = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      entrantes: data.entrantes[idx] || 0,
      salientes: data.salientes[idx] || 0,
      abandonadas: data.abandonadas[idx] || 0
    }));
  };

  const prepareNivelServicio = (data) => {
    if (!data || !data.labels) return [];
    return data.labels.map((label, idx) => ({
      name: label,
      value: data.data[idx] || 0
    }));
  };

  const handleSearch = () => {
    console.log('🔍 Aplicando filtros:', filters);
    loadDashboardData();
  };

  const handleExportCampanasExcel = () => {
    const excelData = campanasConAlerta.map(c => ({
      'Campaña': c.campana,
      'Agentes': c.cantidad_agentes,
      'Llamadas Total': c.llamadas_entrantes,
      'Atendidas': c.atendidas,
      'Abandonadas': c.abandonadas,
      'Nivel Atención': `${c.nivel_atencion}%`,
      'Prom. Duración (seg)': c.prom_duracion,
      'Estado': c.estado === 'excelente' ? 'Excelente' : 
                c.estado === 'advertencia' ? 'Advertencia' : 'Crítico',
      'Alerta': c.alerta ? 'SÍ' : 'NO'
    }));

    const ws = XLSX.utils.json_to_sheet(excelData);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Campañas Alertas');
    XLSX.writeFile(wb, `campanas_alertas_${new Date().toISOString().split('T')[0]}.xlsx`);
  };

  if (loading && Object.keys(kpis).length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Cargando analytics...</p>
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
              <h1 className="text-3xl font-bold text-gray-900">📊 OmniLeads Analytics Pro</h1>
              <p className="text-sm text-gray-600 mt-1">
                Última actualización: {format(lastUpdate, 'dd/MM/yyyy HH:mm:ss')}
              </p>
            </div>
            <div className="flex items-center">
              <img 
                src="/logo-iptegra.png" 
                alt="Iptegra Logo" 
                className="h-12 object-contain"
              />
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

        {/* Sección Entrantes vs Salientes */}
        <EntradasSalidas datos={llamadasPorTipo} />

        {/* KPIs Mejorados - Grid de 11 KPIs */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-4 gap-4 mb-6">
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
            title={kpis.aht?.label || 'AHT'}
            value={kpis.aht?.valor || 0}
            icon="⏱️"
            change={kpis.aht?.cambio || '0%'}
            trend={kpis.aht?.tendencia || 'neutral'}
            format="segundos"
          />
          <KPICard
            title={kpis.asa?.label || 'ASA'}
            value={kpis.asa?.valor || 0}
            icon="⏳"
            change={kpis.asa?.cambio || '0%'}
            trend={kpis.asa?.tendencia || 'neutral'}
            format="segundos"
          />
          <KPICard
            title={kpis.service_level_60?.label || 'Service Level < 60s'}
            value={kpis.service_level_60?.valor || 0}
            icon="🎯"
            change={kpis.service_level_60?.cambio || '0%'}
            trend={kpis.service_level_60?.tendencia || 'neutral'}
            format="porcentaje"
          />
          <KPICard
            title={kpis.service_level_20?.label || 'Service Level < 20s'}
            value={kpis.service_level_20?.valor || 0}
            icon="⚡"
            change={kpis.service_level_20?.cambio || '0%'}
            trend={kpis.service_level_20?.tendencia || 'neutral'}
            format="porcentaje"
          />
          <KPICard
            title={kpis.fcr?.label || 'FCR'}
            value={kpis.fcr?.valor || 0}
            icon="🎖️"
            change={kpis.fcr?.cambio || '0%'}
            trend={kpis.fcr?.tendencia || 'neutral'}
            format="porcentaje"
          />
          <KPICard
            title={kpis.abandonment_rate?.label || 'Tasa de Abandono'}
            value={kpis.abandonment_rate?.valor || 0}
            icon="📉"
            change={kpis.abandonment_rate?.cambio || '0%'}
            trend={kpis.abandonment_rate?.tendencia || 'neutral'}
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
            <nav className="flex -mb-px overflow-x-auto">
              {[
                { id: 'resumen', label: '📈 Resumen', icon: '📈' },
                { id: 'distribucion', label: '📊 Distribución', icon: '📊' },
                { id: 'salientes', label: '📱 Salientes', icon: '📱' },
                { id: 'causas', label: '🔍 Causas', icon: '🔍' },
                { id: 'horaria', label: '🕐 Distribución Horaria', icon: '🕐' },
                { id: 'campanas', label: '🎯 Campañas (Alertas)', icon: '🎯' },
                { id: 'atendidas', label: '✅ Llamadas Atendidas', icon: '✅' },
                { id: 'abandonadas', label: '❌ Llamadas No Atendidas', icon: '❌' },
                { id: 'agentes', label: '👥 Agentes', icon: '👥' },
                { id: 'agentes-avanzado', label: '👥📊 Agentes Avanzado', icon: '👥' },
                { id: 'transferencias', label: '🔄 Transferencias', icon: '🔄' },
                { id: 'gestiones', label: '📋 Gestiones', icon: '📋' }
              ].map(tab => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
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
            {/* Tab: Resumen */}
            {activeTab === 'resumen' && (
              <div className="space-y-6">
                {loading ? (
                  <div className="flex items-center justify-center h-64">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                      <p className="text-gray-600">Cargando datos del dashboard...</p>
                    </div>
                  </div>
                ) : (
                  <>
                    {/* Distribución por tipo (Dos gráficos de pie) */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ApexChart
                        type="pie"
                        data={distribucionPorTipo?.entrantes ? prepareDistribucionEntrantes(distribucionPorTipo.entrantes) : []}
                        title={`Distribución Llamadas Entrantes (Total: ${distribucionPorTipo?.entrantes?.total || 0})`}
                        key={`entrantes-${JSON.stringify(distribucionPorTipo?.entrantes)}`}
                      />
                      <ApexChart
                        type="pie"
                        data={distribucionPorTipo?.salientes ? prepareDistribucionSalientes(distribucionPorTipo.salientes) : []}
                        title={`Distribución Llamadas Salientes (Total: ${distribucionPorTipo?.salientes?.total || 0})`}
                        key={`salientes-${JSON.stringify(distribucionPorTipo?.salientes)}`}
                      />
                    </div>
                    
                    {/* Otros gráficos */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <ApexChart
                        type="line"
                        data={evolucionData}
                        title="Evolución por Hora"
                        key={`evolucion-${JSON.stringify(evolucionData)}`}
                      />
                      <ApexChart
                        type="bar"
                        data={nivelServicioData}
                        title="Nivel de Servicio (Tiempo de Espera)"
                        key={`nivel-${JSON.stringify(nivelServicioData)}`}
                      />
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Tab: Distribución Horaria */}
            {activeTab === 'horaria' && (
              <TablaDistribucionHoraria key="tabla-horaria-detallada" filters={filters} />
            )}

            {/* Tab: Campañas con Alertas */}
            {activeTab === 'campanas' && (
              <div>
                {/* Botón de descarga */}
                <div className="mb-4 flex justify-end">
                  <button
                    onClick={handleExportCampanasExcel}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <span>📥</span>
                    Descargar Excel
                  </button>
                </div>

                {/* Tabla */}
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Campaña</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agentes</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Total</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Atendidas</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Abandonadas</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nivel Atención</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prom. Duración</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estado</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {campanasConAlerta.map((c, idx) => (
                      <tr key={idx} className={c.alerta ? 'bg-red-50' : 'hover:bg-gray-50'}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center">
                            {c.alerta && <span className="mr-2">🚨</span>}
                            <span className="font-medium text-gray-900">{c.campana}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">{c.cantidad_agentes}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{c.llamadas_entrantes}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">{c.atendidas}</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">{c.abandonadas}</td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded-full font-semibold text-sm ${
                            c.color === 'green' ? 'bg-green-100 text-green-800' :
                            c.color === 'orange' ? 'bg-orange-100 text-orange-800' :
                            c.color === 'yellow' ? 'bg-yellow-100 text-yellow-800' :
                            'bg-red-100 text-red-800'
                          }`}>
                            {c.nivel_atencion}%
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{c.prom_duracion}s</td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {c.estado === 'excelente' ? '✅ Excelente' : 
                           c.estado === 'advertencia' ? '⚠️ Advertencia' : 
                           c.estado === 'bueno' ? '⚠️ Bueno' : 
                           '🔴 Crítico'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              </div>
            )}

            {/* Tab: Llamadas Atendidas */}
            {activeTab === 'atendidas' && (
              <TablaLlamadas
                llamadas={llamadasDetalladas}
              />
            )}

            {/* Tab: Llamadas Abandonadas */}
            {activeTab === 'abandonadas' && (
              <TablaAbandonadas
                llamadas={llamadasAbandonadas}
              />
            )}

            {/* Tab: Agentes */}
            {activeTab === 'agentes' && (
              <TablaAgentes agentes={agentesData} loading={loading} />
            )}

            {/* Tab: Distribución Avanzada */}
            {activeTab === 'distribucion' && (
              <DistribucionAvanzada filters={filters} />
            )}

            {/* Tab: Llamadas Salientes */}
            {activeTab === 'salientes' && (
              <LlamadasSalientes filters={filters} />
            )}

            {/* Tab: Causas Detalladas */}
            {activeTab === 'causas' && (
              <CausasDetalladas filters={filters} />
            )}

            {/* Tab: Agentes Avanzado */}
            {activeTab === 'agentes-avanzado' && (
              <AgentesAvanzado filters={filters} />
            )}

            {/* Tab: Transferencias */}
            {activeTab === 'transferencias' && (
              <Transferencias filters={filters} />
            )}

            {/* Tab: Gestiones */}
            {activeTab === 'gestiones' && (
              <Gestiones filters={filters} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardMejorado;

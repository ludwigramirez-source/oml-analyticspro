import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import KPICard from '../KPICard';
import ApexChart from '../ApexChart';

const LlamadasSalientes = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState(null);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const dashboardData = await analyticsApi.getSalientesDashboard(filters).catch(() => null);
      setDashboard(dashboardData);
    } catch (error) {
      console.error('Error loading llamadas salientes:', error);
    } finally {
      setLoading(false);
    }
  };

  const prepareEventosChart = () => {
    if (!dashboard || !dashboard.eventos) return [];
    
    return Object.entries(dashboard.eventos)
      .map(([evento, data]) => ({
        label: String(data?.descripcion || evento),
        value: Number(data?.total || 0)
      }))
      .filter(item => item.value > 0);
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
      <h2 className="text-2xl font-bold text-gray-800 mb-6">📱 Llamadas Salientes</h2>
      
      {/* KPIs */}
      {dashboard && dashboard.metricas && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
          <KPICard
            title="Total Marcadas"
            value={dashboard.metricas.total_marcadas}
            icon="📞"
          />
          <KPICard
            title="Contestadas"
            value={dashboard.metricas.total_contestadas}
            icon="✅"
            subtitle={`${dashboard.metricas.tasa_contactacion}% tasa`}
          />
          <KPICard
            title="No Contestadas"
            value={dashboard.metricas.total_no_contestadas}
            icon="❌"
          />
          <KPICard
            title="Ocupadas"
            value={dashboard.metricas.total_ocupadas}
            icon="🔴"
          />
          <KPICard
            title="Fallos Técnicos"
            value={dashboard.metricas.total_fallos || 0}
            icon="⚠️"
          />
        </div>
      )}

      {/* Gráfico de Distribución */}
      <div className="grid grid-cols-1 gap-6">
        <ApexChart
          type="bar"
          data={prepareEventosChart()}
          title="Distribución de Estados de Llamadas Salientes"
        />
      </div>
    </div>
  );
};

export default LlamadasSalientes;
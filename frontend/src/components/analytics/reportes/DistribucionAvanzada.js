import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import ApexChart from '../ApexChart';

const DistribucionAvanzada = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [porCampana, setPorCampana] = useState([]);
  const [porDiaSemana, setPorDiaSemana] = useState([]);
  const [porMes, setPorMes] = useState([]);
  const [porRangoHorario, setPorRangoHorario] = useState([]);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [campana, diaSemana, mes, rangoHorario] = await Promise.all([
        analyticsApi.getDistribucionPorCampanaDetalle(filters).catch(() => []),
        analyticsApi.getDistribucionPorDiaSemana(filters).catch(() => []),
        analyticsApi.getDistribucionPorMes(null, filters).catch(() => []),
        analyticsApi.getDistribucionPorRangoHorario(filters).catch(() => [])
      ]);

      setPorCampana(preparePieData(campana));
      setPorDiaSemana(prepareBarData(diaSemana));
      setPorMes(prepareLineData(mes));
      setPorRangoHorario(preparePieData(rangoHorario));
    } catch (error) {
      console.error('Error loading distribución avanzada:', error);
    } finally {
      setLoading(false);
    }
  };

  const preparePieData = (data) => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return data.map(item => ({
      label: String(item.campana || item.rango || item.name || 'Sin nombre'),
      value: Number(item.total || item.value || 0)
    })).filter(item => item.value > 0);
  };

  const prepareBarData = (data) => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return [{
      name: 'Llamadas',
      data: data.map(item => ({
        x: String(item.dia || 'N/A'),
        y: Number(item.total || 0)
      }))
    }];
  };

  const prepareLineData = (data) => {
    if (!Array.isArray(data) || data.length === 0) return [];
    return [{
      name: 'Llamadas',
      data: data.map(item => ({
        x: String(item.mes || 'N/A'),
        y: Number(item.total || 0)
      }))
    }];
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
      <h2 className="text-2xl font-bold text-gray-800 mb-6">📊 Distribución Avanzada</h2>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Distribución por Campaña */}
        <ApexChart
          type="pie"
          data={porCampana}
          title="Distribución por Campaña"
        />

        {/* Distribución por Rango Horario */}
        <ApexChart
          type="pie"
          data={porRangoHorario}
          title="Distribución por Rango Horario"
        />

        {/* Distribución por Día de Semana */}
        <ApexChart
          type="bar"
          data={porDiaSemana}
          title="Distribución por Día de Semana"
        />

        {/* Distribución por Mes */}
        <ApexChart
          type="line"
          data={porMes}
          title="Evolución Mensual"
        />
      </div>
    </div>
  );
};

export default DistribucionAvanzada;
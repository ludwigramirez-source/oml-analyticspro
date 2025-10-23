import React, { useState, useEffect } from 'react';
import analyticsApi from '../../../services/analyticsApi';
import ApexChart from '../ApexChart';

const DistribucionAvanzada = ({ filters }) => {
  const [loading, setLoading] = useState(true);
  const [porCampana, setPorCampana] = useState([]);
  const [porDiaSemana, setPorDiaSemana] = useState([]);
  const [porMes, setPorMes] = useState([]);
  const [porRangoHorario, setPorRangoHorario] = useState([]);
  const [evolucionSemanal, setEvolucionSemanal] = useState(null);

  useEffect(() => {
    loadData();
  }, [filters]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [campana, diaSemana, mes, rangoHorario, semanal] = await Promise.all([
        analyticsApi.getDistribucionPorCampanaDetalle(filters).catch(err => {
          console.warn('Error en campaña:', err);
          return [];
        }),
        analyticsApi.getDistribucionPorDiaSemana(filters).catch(err => {
          console.warn('Error en día semana:', err);
          return [];
        }),
        analyticsApi.getDistribucionPorMes(null, filters).catch(err => {
          console.warn('Error en mes:', err);
          return [];
        }),
        analyticsApi.getDistribucionPorRangoHorario(filters).catch(err => {
          console.warn('Error en rango horario:', err);
          return [];
        }),
        analyticsApi.getEvolucionSemanal(filters).catch(err => {
          console.warn('Error en evolución semanal:', err);
          return null;
        })
      ]);

      console.log('Datos recibidos:', { campana, diaSemana, mes, rangoHorario, semanal });

      setPorCampana(preparePieData(campana));
      setPorDiaSemana(prepareBarData(diaSemana));
      setPorMes(prepareLineData(mes));
      setPorRangoHorario(prepareBarData(rangoHorario));
      setEvolucionSemanal(semanal);
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
    return data.map(item => ({
      name: String(item.dia || item.rango || item.name || 'N/A'),
      value: Number(item.total || item.value || 0)
    }));
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

  const prepareMultilineData = (data) => {
    if (!data || !data.labels || !data.series) return [];
    
    return data.labels.map((label, idx) => {
      const dataPoint = { name: label };
      data.series.forEach(serie => {
        dataPoint[serie.name] = serie.data[idx] || 0;
      });
      return dataPoint;
    });
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
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Distribución por Campaña */}
        <ApexChart
          type="pie"
          data={porCampana}
          title="Distribución por Campaña"
        />

        {/* Distribución por Rango Horario - Cambiado a BAR */}
        <ApexChart
          type="bar"
          data={porRangoHorario}
          title="Distribución por Rango Horario"
        />
      </div>

      {/* Evolución Semanal - NUEVO */}
      <div className="mb-6">
        <ApexChart
          type="multiline"
          data={evolucionSemanal ? prepareMultilineData(evolucionSemanal) : []}
          title="Evolución Semanal: Contestadas vs Abandonadas vs Agentes"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
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
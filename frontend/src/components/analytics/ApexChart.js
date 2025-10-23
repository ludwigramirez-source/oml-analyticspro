import React from 'react';
import Chart from 'react-apexcharts';

const ApexChart = ({ type, data, title }) => {
  console.log(`📊 ApexChart [${title}] recibió:`, data);

  if (!data || data.length === 0) {
    console.warn(`⚠️ ApexChart [${title}] sin datos:`, data);
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
        <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
        <div className="flex items-center justify-center h-64 text-gray-400">
          <p>No hay datos disponibles</p>
        </div>
      </div>
    );
  }

  console.log(`✅ ApexChart [${title}] renderizando gráfico tipo: ${type}`);

  // Preparar opciones y series según el tipo de gráfico
  let options = {};
  let series = [];

  if (type === 'pie') {
    series = data.map(d => Number(d.value || 0));
    options = {
      chart: {
        type: 'pie',
        toolbar: { show: false }
      },
      labels: data.map(d => String(d.label || d.name || 'N/A')),
      colors: ['#34a853', '#ea8600', '#ea4335', '#4285f4', '#9c27b0', '#ff9800'],
      legend: {
        position: 'bottom',
        fontSize: '12px'
      },
      dataLabels: {
        enabled: true,
        formatter: function (val) {
          return val.toFixed(0) + '%';
        }
      }
    };
  } else if (type === 'line') {
    // Soportar formato simple o formato con series
    if (Array.isArray(data) && data[0] && data[0].name) {
      series = data;
    } else {
      series = [{
        name: 'Llamadas',
        data: data.map(d => Number(d.value || d.y || 0))
      }];
    }
    options = {
      chart: {
        type: 'line',
        toolbar: { show: false },
        zoom: { enabled: false }
      },
      xaxis: {
        categories: data.map(d => String(d.name || d.x || d.label || 'N/A')),
        labels: { style: { fontSize: '11px' } }
      },
      stroke: {
        curve: 'smooth',
        width: 2
      },
      colors: ['#1a73e8'],
      dataLabels: {
        enabled: false
      }
    };
  } else if (type === 'bar') {
    // Soportar formato simple o formato con series
    if (Array.isArray(data) && data[0] && data[0].name) {
      series = data;
    } else {
      series = [{
        name: 'Llamadas',
        data: data.map(d => Number(d.value || d.y || 0))
      }];
    }
    options = {
      chart: {
        type: 'bar',
        toolbar: { show: false }
      },
      plotOptions: {
        bar: {
          borderRadius: 4,
          horizontal: false,
        }
      },
      xaxis: {
        categories: data.map(d => String(d.name || d.x || d.label || 'N/A')),
        labels: { style: { fontSize: '11px' } }
      },
      colors: ['#1a73e8'],
      dataLabels: {
        enabled: false
      }
    };
  } else if (type === 'multiline') {
    // Obtener todas las keys excepto 'name'
    const keys = Object.keys(data[0] || {}).filter(k => k !== 'name');
    const colors = ['#17a2b8', '#dc3545', '#007bff'];
    
    series = keys.map((key, idx) => ({
      name: key.charAt(0).toUpperCase() + key.slice(1),
      data: data.map(d => d[key] || 0)
    }));
    
    options = {
      chart: {
        type: 'line',
        toolbar: { show: false },
        zoom: { enabled: false }
      },
      xaxis: {
        categories: data.map(d => d.name),
        labels: { style: { fontSize: '11px' } }
      },
      stroke: {
        curve: 'smooth',
        width: 2
      },
      colors: colors.slice(0, keys.length),
      dataLabels: {
        enabled: false
      },
      legend: {
        position: 'bottom',
        fontSize: '12px'
      }
    };
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
      <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
      <div style={{ width: '100%', height: '300px' }}>
        <Chart
          options={options}
          series={series}
          type={type === 'multiline' ? 'line' : type}
          height="300"
        />
      </div>
    </div>
  );
};

export default ApexChart;

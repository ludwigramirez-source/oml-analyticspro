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
    // Verificar si es formato de series múltiples (con propiedad 'data' en cada elemento)
    if (Array.isArray(data) && data[0] && Array.isArray(data[0].data)) {
      // Formato: [{name: 'Serie 1', data: [1,2,3]}, ...]
      series = data;
      options = {
        chart: {
          type: 'line',
          toolbar: { show: false },
          zoom: { enabled: false }
        },
        xaxis: {
          categories: data[0].data.map((_, idx) => idx), // Usar índices si no hay categorías específicas
          labels: { style: { fontSize: '11px' } }
        },
        stroke: {
          curve: 'smooth',
          width: 2
        },
        colors: ['#1a73e8', '#34a853', '#ea8600'],
        dataLabels: {
          enabled: false
        }
      };
    } else {
      // Formato simple: [{name: '00:00', value: 10}, ...]
      series = [{
        name: 'Llamadas',
        data: data.map(d => Number(d.value || d.y || 0))
      }];
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
    }
  } else if (type === 'bar') {
    // Verificar si es formato de series múltiples (con propiedad 'data' en cada elemento)
    if (Array.isArray(data) && data[0] && Array.isArray(data[0].data)) {
      // Formato: [{name: 'Serie 1', data: [1,2,3]}, ...]
      series = data;
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
          categories: data[0].data.map((_, idx) => idx), // Usar índices si no hay categorías específicas
          labels: { style: { fontSize: '11px' } }
        },
        colors: ['#1a73e8', '#34a853', '#ea8600'],
        dataLabels: {
          enabled: false
        }
      };
    } else {
      // Formato simple: [{name: '0-20s', value: 100}, ...]
      series = [{
        name: 'Llamadas',
        data: data.map(d => Number(d.value || d.y || 0))
      }];
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
    }
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

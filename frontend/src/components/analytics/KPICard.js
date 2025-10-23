import React from 'react';

const KPICard = ({ title, value, icon, change, trend, format }) => {
  const formatValue = (val, fmt) => {
    if (fmt === 'segundos') {
      const min = Math.floor(val / 60);
      const sec = val % 60;
      return `${min}m ${sec}s`;
    }
    if (fmt === 'porcentaje') {
      return `${val}%`;
    }
    return val.toLocaleString();
  };

  const trendColor = trend === 'positivo' ? 'text-green-600' : trend === 'negativo' ? 'text-red-600' : 'text-gray-600';
  const trendIcon = trend === 'positivo' ? '↑' : trend === 'negativo' ? '↓' : '→';

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <p className="text-sm text-gray-600 mb-1">{title}</p>
          <p className="text-3xl font-semibold text-gray-900 mb-2">
            {formatValue(value, format)}
          </p>
          <p className={`text-xs ${trendColor} flex items-center`}>
            <span className="mr-1">{trendIcon}</span>
            {change}
          </p>
        </div>
        <div className="text-4xl opacity-20">{icon}</div>
      </div>
    </div>
  );
};

export default KPICard;
import React from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

const SimpleChart = ({ type, data, title }) => {
  const COLORS = [
    '#34a853', // Green
    '#ea8600', // Orange
    '#ea4335', // Red
    '#1a73e8', // Blue
    '#9c27b0', // Purple
    '#00acc1'  // Cyan
  ];

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
        <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
        <div className="flex items-center justify-center h-64 text-gray-400">
          <p>No hay datos disponibles</p>
        </div>
      </div>
    );
  }

  const renderChart = () => {
    switch (type) {
      case 'line':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" style={{ fontSize: '12px' }} />
              <YAxis stroke="#666" style={{ fontSize: '12px' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="value" stroke="#1a73e8" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        );

      case 'bar':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" style={{ fontSize: '12px' }} />
              <YAxis stroke="#666" style="{{" fontSize: '12px' }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="value" fill="#1a73e8" />
            </BarChart>
          </ResponsiveContainer>
        );

      case 'pie':
        return (
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={data}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        );

      case 'multiline':
        const keys = Object.keys(data[0] || {}).filter(k => k !== 'name');
        return (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0" />
              <XAxis dataKey="name" stroke="#666" style={{ fontSize: '12px' }} />
              <YAxis stroke="#666" style={{ fontSize: '12px' }} />
              <Tooltip />
              <Legend />
              {keys.map((key, idx) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={COLORS[idx % COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        );

      default:
        return null;
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-5">
      <h3 className="text-base font-semibold text-gray-800 mb-4">{title}</h3>
      {renderChart()}
    </div>
  );
};

export default SimpleChart;
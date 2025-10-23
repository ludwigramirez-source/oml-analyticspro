import React from 'react';

const EntradasSalidas = ({ datos }) => {
  if (!datos) return null;

  const { entrantes = {}, salientes = {} } = datos;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
      {/* Llamadas Entrantes */}
      <div className="bg-gradient-to-br from-teal-50 to-white rounded-lg shadow-sm border-2 border-teal-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-teal-800">📞 Llamadas Entrantes</h3>
        </div>
        <div className="text-5xl font-bold text-teal-600 mb-4">
          {entrantes.total || 0}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-600 mb-1">Atendidas</p>
            <p className="text-3xl font-bold text-green-600">{entrantes.atendidas || 0}</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-600 mb-1">Abandonadas</p>
            <p className="text-3xl font-bold text-red-600">{entrantes.abandonadas || 0}</p>
          </div>
        </div>
        <div className="mt-4 p-4 bg-teal-100 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-teal-900">Nivel de Atención</span>
            <span className="text-2xl font-bold text-teal-900">
              {entrantes.nivel_atencion || 0}%
            </span>
          </div>
          <div className="mt-2 w-full bg-teal-200 rounded-full h-2">
            <div
              className="bg-teal-600 h-2 rounded-full"
              style={{ width: `${entrantes.nivel_atencion || 0}%` }}
            ></div>
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          Tasa de Abandono: {entrantes.tasa_abandono || 0}%
        </div>
      </div>

      {/* Llamadas Salientes */}
      <div className="bg-gradient-to-br from-blue-50 to-white rounded-lg shadow-sm border-2 border-blue-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-xl font-bold text-blue-800">📱 Llamadas Salientes</h3>
        </div>
        <div className="text-5xl font-bold text-blue-600 mb-4">
          {salientes.total || 0}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-600 mb-1">Atendidas</p>
            <p className="text-3xl font-bold text-green-600">{salientes.atendidas || 0}</p>
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <p className="text-sm text-gray-600 mb-1">No Atendidas</p>
            <p className="text-3xl font-bold text-orange-600">{salientes.no_atendidas || 0}</p>
          </div>
        </div>
        <div className="mt-4 p-4 bg-blue-100 rounded-lg">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium text-blue-900">Nivel de Atención</span>
            <span className="text-2xl font-bold text-blue-900">
              {salientes.nivel_atencion || 0}%
            </span>
          </div>
          <div className="mt-2 w-full bg-blue-200 rounded-full h-2">
            <div
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${salientes.nivel_atencion || 0}%` }}
            ></div>
          </div>
        </div>
        <div className="mt-3 text-xs text-gray-500">
          Tasa de No Atención: {salientes.tasa_no_atencion || 0}%
        </div>
      </div>
    </div>
  );
};

export default EntradasSalidas;
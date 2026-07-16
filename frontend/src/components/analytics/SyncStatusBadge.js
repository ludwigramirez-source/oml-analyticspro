import React, { useState, useEffect } from 'react';
import analyticsApi from '../../services/analyticsApi';

const SyncStatusBadge = () => {
  const [syncStatus, setSyncStatus] = useState(null);
  const [showDetail, setShowDetail] = useState(false);

  useEffect(() => {
    fetchStatus();
    // Refrescar cada 30 segundos para mantener actualizado
    const interval = setInterval(fetchStatus, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchStatus = async () => {
    const data = await analyticsApi.getSyncStatus();
    setSyncStatus(data);
  };

  if (!syncStatus || !syncStatus.enabled) {
    return null; // No mostrar si no hay sync habilitado
  }

  // Formatear fecha en hora de Colombia (America/Bogota, UTC-5)
  const formatDate = (isoString) => {
    if (!isoString) return 'Nunca';
    const d = new Date(isoString);
    return d.toLocaleString('es-CO', {
      timeZone: 'America/Bogota',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  };

  const formatDateShort = (isoString) => {
    if (!isoString) return '';
    const d = new Date(isoString);
    return d.toLocaleString('es-CO', {
      timeZone: 'America/Bogota',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    });
  };

  const formatNumber = (num) => {
    if (!num) return '0';
    return num.toLocaleString('es-CO');
  };

  // Tablas de gestiones ocultas: este servidor no las tiene
  const GESTION_TABLES = [
    'ominicontacto_app_customformgestion',
    'ominicontacto_app_customformincidencias',
  ];
  const visibleTables = (syncStatus.tables || []).filter(
    t => !GESTION_TABLES.includes(t.table_name)
  );

  const hasError = syncStatus.error ||
    visibleTables.some(t => t.sync_status === 'error');
  const isSyncing = visibleTables.some(t => t.sync_status === 'syncing');

  const statusColor = hasError ? 'text-red-600' : isSyncing ? 'text-yellow-600' : 'text-green-600';
  const bgColor = hasError ? 'bg-red-50 border-red-200' : isSyncing ? 'bg-yellow-50 border-yellow-200' : 'bg-green-50 border-green-200';
  const dotColor = hasError ? 'bg-red-500' : isSyncing ? 'bg-yellow-500 animate-pulse' : 'bg-green-500';

  return (
    <div className="relative">
      {/* Badge compacto */}
      <button
        onClick={() => setShowDetail(!showDetail)}
        className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium ${bgColor} ${statusColor} hover:opacity-80 transition-opacity`}
        title="Estado de sincronizacion - Click para detalles"
      >
        <span className={`w-2 h-2 rounded-full ${dotColor}`}></span>
        <span>
          {hasError ? 'Error Sync' : isSyncing ? 'Sincronizando...' : 'Sincronizado'}
        </span>
        {syncStatus.last_sync_time && !hasError && (
          <span className="text-gray-500">
            {formatDateShort(syncStatus.last_sync_time)}
          </span>
        )}
        {syncStatus.total_rows > 0 && (
          <span className="text-gray-500">
            | {formatNumber(syncStatus.total_rows)} reg.
          </span>
        )}
      </button>

      {/* Panel desplegable con detalle */}
      {showDetail && (
        <div className="absolute right-0 top-full mt-2 w-[420px] bg-white rounded-lg shadow-lg border border-gray-200 z-50 p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-semibold text-gray-800">
              Estado de Sincronizacion
            </h4>
            <button
              onClick={() => setShowDetail(false)}
              className="text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>

          {/* Info general */}
          <div className="mb-3 p-2 rounded bg-gray-50 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-500">Modo:</span>
              <span className="font-medium">BD Local (replica)</span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-gray-500">Ultima sync:</span>
              <span className="font-medium">
                {formatDate(syncStatus.last_sync_time)} (CO)
              </span>
            </div>
            <div className="flex justify-between mt-1">
              <span className="text-gray-500">Total registros:</span>
              <span className="font-medium">
                {formatNumber(syncStatus.total_rows)}
              </span>
            </div>
          </div>

          {syncStatus.error && (
            <div className="mb-3 p-2 rounded bg-red-50 text-xs text-red-700">
              {syncStatus.error}
            </div>
          )}

          {/* Detalle por tabla */}
          <div className="space-y-1">
            <div className="grid grid-cols-4 gap-1 text-xs font-medium text-gray-500 border-b pb-1">
              <span>Tabla</span>
              <span className="text-right">Registros</span>
              <span className="text-right">Duracion</span>
              <span className="text-center">Estado</span>
            </div>
            {visibleTables.map((table) => (
              <div key={table.table_name} className="grid grid-cols-4 gap-1 text-xs py-0.5">
                <span className="text-gray-700 truncate" title={table.table_name}>
                  {table.table_name.replace('reportes_app_', '').replace('ominicontacto_app_', '')}
                </span>
                <span className="text-right text-gray-600">
                  {formatNumber(table.rows_total)}
                </span>
                <span className="text-right text-gray-600">
                  {table.sync_duration_s ? `${table.sync_duration_s}s` : '-'}
                </span>
                <span className="text-center">
                  {table.sync_status === 'completed' && (
                    <span className="text-green-600">✓</span>
                  )}
                  {table.sync_status === 'syncing' && (
                    <span className="text-yellow-600 animate-pulse">⟳</span>
                  )}
                  {table.sync_status === 'error' && (
                    <span className="text-red-600" title={table.error_message}>✗</span>
                  )}
                  {table.sync_status === 'pending' && (
                    <span className="text-gray-400">○</span>
                  )}
                </span>
              </div>
            ))}
          </div>

          {/* Zona horaria */}
          <div className="mt-3 pt-2 border-t border-gray-100 text-xs text-gray-400 text-center">
            Hora Colombia (UTC-5)
          </div>
        </div>
      )}
    </div>
  );
};

export default SyncStatusBadge;

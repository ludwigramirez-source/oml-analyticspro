import React, { useState, useEffect } from 'react';
import configApi from '../../services/configApi';

const ConfiguracionDB = () => {
  const [formData, setFormData] = useState({
    db_host: 'localhost',
    db_port: 5432,
    db_name: 'omnileads',
    db_user: 'omnileads_readonly',
    db_password: ''
  });

  const [activeConfig, setActiveConfig] = useState(null);
  const [isTestingConnection, setIsTestingConnection] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [saveResult, setSaveResult] = useState(null);
  const [showPassword, setShowPassword] = useState(false);

  useEffect(() => {
    loadActiveConfig();
  }, []);

  const loadActiveConfig = async () => {
    try {
      const config = await configApi.getActiveConfig();
      if (config) {
        setActiveConfig(config);
        // No mostramos el password por seguridad
        setFormData({
          db_host: config.db_host,
          db_port: config.db_port,
          db_name: config.db_name,
          db_user: config.db_user,
          db_password: ''
        });
      }
    } catch (error) {
      console.error('Error loading config:', error);
    }
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'db_port' ? parseInt(value) || 5432 : value
    }));
    // Limpiar resultados previos cuando cambia el input
    setTestResult(null);
    setSaveResult(null);
  };

  const handleTestConnection = async () => {
    setIsTestingConnection(true);
    setTestResult(null);

    try {
      const result = await configApi.testConnection(formData);
      setTestResult(result);
    } catch (error) {
      setTestResult({
        success: false,
        message: error.message || 'Error al probar conexión'
      });
    } finally {
      setIsTestingConnection(false);
    }
  };

  const handleSaveConfig = async () => {
    // Validar campos
    if (!formData.db_host || !formData.db_name || !formData.db_user || !formData.db_password) {
      setSaveResult({
        success: false,
        message: 'Todos los campos son requeridos'
      });
      return;
    }

    setIsSaving(true);
    setSaveResult(null);

    try {
      const result = await configApi.createConfig(formData);
      setSaveResult({
        success: true,
        message: 'Configuración guardada exitosamente'
      });
      setActiveConfig(result);
      
      // Limpiar password del formulario
      setFormData(prev => ({ ...prev, db_password: '' }));

      // Recargar página después de 2 segundos para que tome la nueva conexión
      setTimeout(() => {
        window.location.reload();
      }, 2000);
    } catch (error) {
      setSaveResult({
        success: false,
        message: error.message || 'Error al guardar configuración'
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          ⚙️ Configuración de Base de Datos
        </h1>
        <p className="text-gray-600">
          Configure la conexión a la base de datos PostgreSQL de OmniLeads
        </p>
      </div>

      {/* Estado de configuración actual */}
      {activeConfig && (
        <div className="mb-6 p-4 bg-green-50 border-l-4 border-green-500 rounded">
          <div className="flex items-start">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Configuración Activa</h3>
              <p className="text-sm text-green-700 mt-1">
                <strong>{activeConfig.db_host}:{activeConfig.db_port}</strong> / {activeConfig.db_name}
              </p>
              {activeConfig.connection_test_success && (
                <p className="text-xs text-green-600 mt-1">
                  ✓ {activeConfig.connection_test_message}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Formulario */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-800 mb-6">
          Datos de Conexión PostgreSQL
        </h2>

        <div className="space-y-4">
          {/* Host */}
          <div>
            <label htmlFor="db_host" className="block text-sm font-medium text-gray-700 mb-2">
              Host <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="db_host"
              name="db_host"
              value={formData.db_host}
              onChange={handleInputChange}
              placeholder="localhost o IP del servidor"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Port */}
          <div>
            <label htmlFor="db_port" className="block text-sm font-medium text-gray-700 mb-2">
              Puerto <span className="text-red-500">*</span>
            </label>
            <input
              type="number"
              id="db_port"
              name="db_port"
              value={formData.db_port}
              onChange={handleInputChange}
              placeholder="5432"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Database Name */}
          <div>
            <label htmlFor="db_name" className="block text-sm font-medium text-gray-700 mb-2">
              Nombre de Base de Datos <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="db_name"
              name="db_name"
              value={formData.db_name}
              onChange={handleInputChange}
              placeholder="omnileads"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* User */}
          <div>
            <label htmlFor="db_user" className="block text-sm font-medium text-gray-700 mb-2">
              Usuario <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              id="db_user"
              name="db_user"
              value={formData.db_user}
              onChange={handleInputChange}
              placeholder="omnileads_readonly"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Password */}
          <div>
            <label htmlFor="db_password" className="block text-sm font-medium text-gray-700 mb-2">
              Contraseña <span className="text-red-500">*</span>
            </label>
            <div className="relative">
              <input
                type={showPassword ? "text" : "password"}
                id="db_password"
                name="db_password"
                value={formData.db_password}
                onChange={handleInputChange}
                placeholder="Ingrese la contraseña"
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-700"
              >
                {showPassword ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Botones de acción */}
        <div className="flex flex-col sm:flex-row gap-4 mt-6">
          {/* Botón Probar Conexión */}
          <button
            onClick={handleTestConnection}
            disabled={isTestingConnection}
            className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
          >
            {isTestingConnection ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Probando...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Probar Conexión
              </>
            )}
          </button>

          {/* Botón Guardar */}
          <button
            onClick={handleSaveConfig}
            disabled={isSaving || (testResult && !testResult.success)}
            className="flex-1 bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white font-semibold py-3 px-6 rounded-lg transition duration-200 flex items-center justify-center"
          >
            {isSaving ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Guardando...
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4" />
                </svg>
                Guardar Configuración
              </>
            )}
          </button>
        </div>

        {/* Resultados de prueba de conexión */}
        {testResult && (
          <div className={`mt-6 p-4 rounded-lg border-l-4 ${
            testResult.success 
              ? 'bg-green-50 border-green-500' 
              : 'bg-red-50 border-red-500'
          }`}>
            <div className="flex">
              <div className="flex-shrink-0">
                {testResult.success ? (
                  <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
              <div className="ml-3">
                <h3 className={`text-sm font-medium ${
                  testResult.success ? 'text-green-800' : 'text-red-800'
                }`}>
                  {testResult.success ? '✓ Conexión Exitosa' : '✗ Error de Conexión'}
                </h3>
                <p className={`text-sm mt-1 ${
                  testResult.success ? 'text-green-700' : 'text-red-700'
                }`}>
                  {testResult.message}
                </p>
                {testResult.details && (
                  <p className="text-xs text-gray-600 mt-2">
                    {JSON.stringify(testResult.details)}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Resultados de guardar configuración */}
        {saveResult && (
          <div className={`mt-6 p-4 rounded-lg border-l-4 ${
            saveResult.success 
              ? 'bg-green-50 border-green-500' 
              : 'bg-red-50 border-red-500'
          }`}>
            <div className="flex">
              <div className="flex-shrink-0">
                {saveResult.success ? (
                  <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                )}
              </div>
              <div className="ml-3">
                <p className={`text-sm font-medium ${
                  saveResult.success ? 'text-green-800' : 'text-red-800'
                }`}>
                  {saveResult.message}
                </p>
                {saveResult.success && (
                  <p className="text-xs text-green-600 mt-1">
                    La página se recargará en unos segundos...
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Información adicional */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">Información</h3>
            <div className="mt-2 text-sm text-blue-700">
              <ul className="list-disc list-inside space-y-1">
                <li>La conexión se realiza en modo <strong>READ-ONLY</strong> (solo lectura)</li>
                <li>La contraseña se encripta antes de almacenarse</li>
                <li>Solo puede haber una configuración activa a la vez</li>
                <li>Se recomienda usar un usuario con permisos limitados</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ConfiguracionDB;

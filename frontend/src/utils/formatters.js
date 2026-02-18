/**
 * Funciones de formateo compartidas para OmniLeads Analytics Pro.
 * Fuente única de verdad para formato de duración, espera, etc.
 */

/**
 * Formatea segundos a formato mm:ss con padding.
 * @param {number|string|null} seconds - Duración en segundos
 * @returns {string} Formato "mm:ss" (ej: "01:29", "00:45")
 */
export const formatDuration = (seconds) => {
  if (!seconds && seconds !== 0) return '00:00';
  const sec = Math.round(Number(seconds) || 0);
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
};

/**
 * Alias en español para compatibilidad con componentes existentes.
 */
export const formatDuracion = formatDuration;

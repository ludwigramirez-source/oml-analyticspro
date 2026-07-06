/**
 * Analytics Pro — Dashboard JS
 * Namespace: OMLAnalytics
 * Requires: jQuery (from OmniLeads base), ApexCharts (CDN)
 */
(function ($) {
  'use strict';

  // ── State ────────────────────────────────────────────────────────
  var state = {
    filters: {},
    atendidasPage: 1,
    abandonadasPage: 1,
    salientesDetallePage: 1,
    dialerPage: 1,
    perPage: 50,
    charts: {},
    initialized: false,
  };

  // ── Helpers ──────────────────────────────────────────────────────

  /** Format a Date as YYYY-MM-DD */
  function fmtDate(d) {
    var m = d.getMonth() + 1;
    var day = d.getDate();
    return d.getFullYear() + '-' +
           (m   < 10 ? '0' + m   : m)   + '-' +
           (day < 10 ? '0' + day : day);
  }

  function buildFilters() {
    var fi = $('#f-fecha-inicio').val();
    var ff = $('#f-fecha-fin').val();
    var campanas = $('#f-campana').val() || [];
    var agentes = $('#f-agente').val() || [];
    var tipo = $('#f-tipo').val();
    var p = {};
    if (fi) p.fecha_inicio = fi;
    if (ff) p.fecha_fin = ff;
    if (campanas.length) p.campana_ids = campanas.join(',');
    if (agentes.length) p.agente_ids = agentes.join(',');
    if (tipo) p.tipo_llamada = tipo;
    return p;
  }

  function qs(params) {
    return '?' + Object.keys(params).map(function (k) {
      return encodeURIComponent(k) + '=' + encodeURIComponent(params[k]);
    }).join('&');
  }

  function apiFetch(url, params) {
    return $.ajax({ url: url + qs(params || {}), type: 'GET' });
  }

  function fmtNum(n, dec) {
    if (n === null || n === undefined) return '—';
    dec = dec || 0;
    return parseFloat(n).toFixed(dec).replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  function fmtPct(n) {
    return fmtNum(n, 1) + ' %';
  }

  function fmtDt(s) {
    if (!s) return '—';
    return s.replace('T', ' ').slice(0, 19);
  }

  function loading(show) {
    if (show) $('#loading-overlay').removeClass('d-none');
    else $('#loading-overlay').addClass('d-none');
  }

  function destroyChart(id) {
    if (state.charts[id]) {
      try { state.charts[id].destroy(); } catch (e) {}
      delete state.charts[id];
    }
  }

  function safeRender(id, fn) {
    var el = document.querySelector('#' + id);
    if (!el) return;
    destroyChart(id);
    try {
      state.charts[id] = fn(el);
      state.charts[id].render();
    } catch (e) {
      el.innerHTML = '<p class="text-muted p-2 small">Sin datos</p>';
    }
  }

  var APEXCOLORS = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#17a2b8', '#6f42c1', '#fd7e14', '#20c997'];

  // ── Sync Status ──────────────────────────────────────────────────

  function loadSyncStatus() {
    $.ajax({ url: ANALYTICS_CONFIG.urls.syncStatus, type: 'GET' })
      .done(function (d) {
        var badge = $('#sync-badge');
        if (d.error) {
          badge.removeClass('badge-secondary badge-success badge-warning').addClass('badge-danger');
          $('#sync-label').text('Error: ' + d.error.slice(0, 40));
        } else {
          badge.removeClass('badge-secondary badge-danger badge-warning').addClass('badge-success');
          var ts = d.last_sync_time ? d.last_sync_time.slice(0, 16) : '—';
          $('#sync-label').text('Sync OK · ' + fmtNum(d.total_rows) + ' filas · ' + ts);
        }
      })
      .fail(function () {
        $('#sync-badge').addClass('badge-warning').removeClass('badge-secondary');
        $('#sync-label').text('Sin conexión BD analytics');
      });
  }

  // ── Meta: campañas y agentes ─────────────────────────────────────

  function loadMeta() {
    $.when(
      $.ajax(ANALYTICS_CONFIG.urls.campanas),
      $.ajax(ANALYTICS_CONFIG.urls.agentes)
    ).done(function (campRes, agRes) {
      var campanas = campRes[0];
      var agentes  = agRes[0];
      var $fc = $('#f-campana').empty();
      $.each(campanas, function (_, c) {
        $fc.append('<option value="' + c.id + '">' + c.nombre + '</option>');
      });
      var $fa = $('#f-agente').empty();
      $.each(agentes, function (_, a) {
        $fa.append('<option value="' + a.id + '">' + a.nombre_completo + '</option>');
      });
    });
  }

  // ── KPI Cards ────────────────────────────────────────────────────

  function loadKpis(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.kpis, filters)
      .done(function (d) {
        var cards = $('#kpi-cards .col-md-3');
        var items = [
          { label: 'Total llamadas',   value: fmtNum(d.total_llamadas), sub: '' },
          { label: 'Atendidas',
            value: fmtNum(d.llamadas_atendidas || d.total_atendidas),
            sub: fmtPct(d.nivel_atencion || d.tasa_atencion) + ' de atención' },
          { label: 'Abandonadas',
            value: fmtNum(d.llamadas_abandonadas || d.total_abandonadas),
            sub: fmtPct(d.tasa_abandono) + ' de abandono' },
          { label: 'Nivel servicio',   value: fmtPct(d.nivel_servicio_60 || d.nivel_servicio_20),
            sub: 'SLA60: ' + fmtPct(d.nivel_servicio_60) + ' · SLA20: ' + fmtPct(d.nivel_servicio_20) },
        ];
        cards.each(function (i) {
          if (items[i]) {
            $(this).find('.kpi-label').text(items[i].label);
            $(this).find('.kpi-value').text(items[i].value);
            $(this).find('.kpi-sub').text(items[i].sub);
          }
        });
      });
  }

  // ── Chart: Distribución ──────────────────────────────────────────

  function loadDistribucion(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.distribucion, filters)
      .done(function (d) {
        if (!d || !d.length) return;
        var labels = d.map(function (r) { return r.estado || r.categoria || r.label || 'Sin nombre'; });
        var vals   = d.map(function (r) { return r.cantidad || r.count || r.total || 0; });
        safeRender('chart-distribucion', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'donut', height: 260, toolbar: { show: false } },
            series: vals, labels: labels, colors: APEXCOLORS,
            legend: { position: 'bottom' },
            plotOptions: { pie: { donut: { size: '65%' } } },
          });
        });
      });
  }

  // ── Chart: Nivel de servicio ─────────────────────────────────────

  function loadNivelServicio(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.nivelServicioDetallado, filters)
      .done(function (rows) {
        if (!rows || !rows.length) return;
        var cats = rows.map(function (r) { return r.franja; });
        var vals = rows.map(function (r) { return r.cantidad || 0; });
        safeRender('chart-nivel-servicio', function (el) {
          return new ApexCharts(el, {
            chart: {
              type: 'bar',
              height: 260,
              toolbar: { show: false },
            },
            title: {
              text: 'Nivel de Servicio (Tiempo de Espera)',
              align: 'left',
              style: { fontSize: '13px', fontWeight: '600', color: '#333' },
            },
            series: [{ name: 'Llamadas', data: vals }],
            xaxis: { categories: cats },
            colors: ['#4472C4'],
            dataLabels: { enabled: false },
            plotOptions: {
              bar: { borderRadius: 3, columnWidth: '60%' },
            },
            yaxis: { labels: { formatter: function (v) { return Math.round(v); } } },
            tooltip: {
              y: { formatter: function (v) { return fmtNum(v) + ' llamadas'; } },
            },
          });
        });
      });
  }

  // ── Chart: Evolución hora ────────────────────────────────────────

  function loadEvolucionHora(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.evolucionHora, filters)
      .done(function (rows) {
        if (!rows || !rows.length) return;
        var cats = rows.map(function (r) { return r.hora + ':00'; });
        var atend  = rows.map(function (r) { return r.atendidas  || 0; });
        var aband  = rows.map(function (r) { return r.abandonadas || 0; });
        safeRender('chart-evolucion-hora', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'bar', height: 260, stacked: true, toolbar: { show: false } },
            series: [
              { name: 'Atendidas',   data: atend },
              { name: 'Abandonadas', data: aband },
            ],
            xaxis: { categories: cats },
            colors: ['#28a745', '#dc3545'],
            legend: { position: 'top' },
            dataLabels: { enabled: false },
          });
        });
      });
  }

  // ── Chart: Evolución diaria ──────────────────────────────────────

  function loadEvolucionDiaria(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.evolucionDiaria, filters)
      .done(function (rows) {
        if (!rows || !rows.length) return;
        var cats = rows.map(function (r) { return r.fecha || r.dia || ''; });
        var atend = rows.map(function (r) { return r.atendidas || 0; });
        var aband = rows.map(function (r) { return r.abandonadas || 0; });
        safeRender('chart-evolucion-diaria', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'line', height: 200, toolbar: { show: false } },
            series: [
              { name: 'Atendidas',   data: atend },
              { name: 'Abandonadas', data: aband },
            ],
            xaxis: { categories: cats, labels: { rotate: -45, style: { fontSize: '10px' } } },
            colors: ['#28a745', '#dc3545'],
            stroke: { curve: 'smooth', width: 2 },
            markers: { size: 3 },
            legend: { position: 'top' },
            dataLabels: { enabled: false },
          });
        });
      });
  }

  // ── Chart: Causas no atención ────────────────────────────────────

  function loadCausas(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.causas, filters)
      .done(function (rows) {
        if (!rows || !rows.length) {
          document.querySelector('#chart-causas').innerHTML = '<p class="text-muted p-2 small">Sin datos</p>';
          return;
        }
        rows.sort(function (a, b) { return (b.cantidad || 0) - (a.cantidad || 0); });
        var cats = rows.map(function (r) { return r.event || r.causa || '—'; });
        var vals = rows.map(function (r) { return r.cantidad || r.count || 0; });
        safeRender('chart-causas', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'bar', height: 260, toolbar: { show: false } },
            series: [{ name: 'Cantidad', data: vals }],
            xaxis: { categories: cats, labels: { style: { fontSize: '10px' } } },
            colors: ['#ffc107'],
            dataLabels: { enabled: false },
            plotOptions: { bar: { horizontal: true } },
          });
        });
      });
  }

  // ── Table: Llamadas Atendidas ────────────────────────────────────

  function loadAtendidas(filters, page) {
    page = page || 1;
    var params = $.extend({}, filters, { page: page, per_page: state.perPage });
    return apiFetch(ANALYTICS_CONFIG.urls.atendidas, params)
      .done(function (d) {
        var rows = d.data || d.results || d.llamadas || d || [];
        var total = d.total || rows.length;
        var $tbody = $('#tbody-atendidas').empty();
        if (!rows.length) {
          $tbody.append('<tr><td colspan="7" class="text-center text-muted">Sin datos</td></tr>');
        } else {
          $.each(rows, function (_, r) {
            $tbody.append('<tr>' +
              '<td>' + fmtDt(r.fecha || r.time) + '</td>' +
              '<td>' + (r.campana_nombre || r.campana || '—') + '</td>' +
              '<td>' + (r.agente_nombre || r.agente || '—') + '</td>' +
              '<td class="text-monospace small">' + (r.callid || '—') + '</td>' +
              '<td>' + fmtNum(r.bridge_wait_time) + '</td>' +
              '<td>' + fmtNum(r.duracion_llamada) + '</td>' +
              '<td>' + (r.numero_marcado || '—') + '</td>' +
            '</tr>');
          });
        }
        renderPagination('#pag-atendidas', page, total, state.perPage, function (p) {
          state.atendidasPage = p;
          loadAtendidas(state.filters, p);
        });
      });
  }

  // ── Table: Llamadas Abandonadas ──────────────────────────────────

  function loadAbandonadas(filters, page) {
    page = page || 1;
    var params = $.extend({}, filters, { page: page, per_page: state.perPage });
    return apiFetch(ANALYTICS_CONFIG.urls.abandonadas, params)
      .done(function (d) {
        var rows = d.data || d.results || d.llamadas || d || [];
        var total = d.total || rows.length;
        var $tbody = $('#tbody-abandonadas').empty();
        if (!rows.length) {
          $tbody.append('<tr><td colspan="6" class="text-center text-muted">Sin datos</td></tr>');
        } else {
          $.each(rows, function (_, r) {
            $tbody.append('<tr>' +
              '<td>' + fmtDt(r.fecha || r.time) + '</td>' +
              '<td>' + (r.campana_nombre || r.campana || '—') + '</td>' +
              '<td class="text-monospace small">' + (r.callid || '—') + '</td>' +
              '<td>' + fmtNum(r.tiempo_espera || r.bridge_wait_time) + '</td>' +
              '<td>' + (r.numero_marcado || '—') + '</td>' +
              '<td><span class="badge badge-danger">' + (r.causa_abandono || r.event || '—') + '</span></td>' +
            '</tr>');
          });
        }
        renderPagination('#pag-abandonadas', page, total, state.perPage, function (p) {
          state.abandonadasPage = p;
          loadAbandonadas(state.filters, p);
        });
      });
  }

  // ── Pagination helper ────────────────────────────────────────────

  function renderPagination(selector, page, total, perPage, callback) {
    var totalPages = Math.max(1, Math.ceil(total / perPage));
    var $el = $(selector).empty();
    var info = $('<span>').text(
      'Página ' + page + ' de ' + totalPages + ' · ' + fmtNum(total) + ' registros'
    );
    var btns = $('<div>');

    function mkBtn(label, p, disabled) {
      var btn = $('<button class="pag-btn">').text(label)
        .prop('disabled', !!disabled)
        .toggleClass('active', p === page);
      if (!disabled) btn.on('click', function () { callback(p); });
      return btn;
    }

    btns.append(mkBtn('«', 1, page <= 1));
    btns.append(mkBtn('‹', page - 1, page <= 1));
    if (page > 3) btns.append(mkBtn('...', null, true));
    for (var p = Math.max(1, page - 2); p <= Math.min(totalPages, page + 2); p++) {
      btns.append(mkBtn(p, p, false));
    }
    if (page < totalPages - 2) btns.append(mkBtn('...', null, true));
    btns.append(mkBtn('›', page + 1, page >= totalPages));
    btns.append(mkBtn('»', totalPages, page >= totalPages));

    $el.append(info).append(btns);
  }

  // ── Table: Distribución por campaña ──────────────────────────────

  function loadDistCampana(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.distCampana, filters)
      .done(function (rows) {
        _distData = rows || [];
        var $tbody = $('#tbody-dist-campana').empty();
        if (!rows || !rows.length) {
          $tbody.append('<tr><td colspan="8" class="text-center text-muted">Sin datos</td></tr>');
          return;
        }
        $.each(rows, function (_, r) {
          var pct = r.nivel_atencion != null ? fmtPct(r.nivel_atencion) : '—';
          $tbody.append('<tr>' +
            '<td>' + (r.campana_nombre || r.nombre || '—') + '</td>' +
            '<td class="text-right">' + fmtNum(r.total_llamadas || r.total) + '</td>' +
            '<td class="text-right">' + fmtNum(r.total_atendidas || r.atendidas) + '</td>' +
            '<td class="text-right">' + fmtNum(r.total_abandonadas || r.abandonadas) + '</td>' +
            '<td class="text-right">' + fmtNum(r.total_no_atendidas || r.no_atendidas) + '</td>' +
            '<td class="text-right">' + pct + '</td>' +
            '<td class="text-right">' + fmtNum(r.tmo_prom) + '</td>' +
            '<td class="text-right">' + fmtNum(r.espera_prom) + '</td>' +
          '</tr>');
        });
      });
  }

  // ── Table: Agentes (rendimiento completo) ───────────────────────

  function loadAgentesRendimiento(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.agentesCompleto, filters)
      .done(function (rows) {
        var $tbody = $('#tbody-agentes').empty();
        if (!rows || !rows.length) {
          $tbody.append(
            '<tr><td colspan="10" class="text-center text-muted">Sin datos</td></tr>'
          );
          return;
        }
        $.each(rows, function (_, r) {
          var occ = parseFloat(r.ocupacion || 0);
          var occColor = occ >= 70 ? '#28a745' : occ >= 40 ? '#fd7e14' : '#dc3545';
          $tbody.append('<tr>' +
            '<td class="font-weight-bold">' + (r.nombre || '—') + '</td>' +
            '<td class="text-right">' + fmtNum(r.llamadas_contestadas) + '</td>' +
            '<td class="text-right">' + fmtNum(r.num_sesiones) + '</td>' +
            '<td class="text-right">' + fmtTiempo(r.tiempo_total_sesion) + '</td>' +
            '<td class="text-right text-primary">' + fmtTiempo(r.tiempo_al_habla) + '</td>' +
            '<td class="text-right">' + fmtNum(r.num_pausas) + '</td>' +
            '<td class="text-right">' + fmtTiempo(r.tiempo_total_pausa) + '</td>' +
            '<td class="text-right font-weight-bold" style="color:' + occColor + '">' +
              fmtNum(occ, 1) + '%</td>' +
            '<td class="small text-muted">' + fmtDt(r.primer_login) + '</td>' +
            '<td class="small text-muted">' + fmtDt(r.ultimo_logout) + '</td>' +
          '</tr>');
        });
      })
      .fail(function () {
        // Fallback to basic endpoint if completo not yet available
        apiFetch(ANALYTICS_CONFIG.urls.agentesRendimiento, filters)
          .done(function (rows) {
            var $tbody = $('#tbody-agentes').empty();
            $.each(rows || [], function (_, r) {
              $tbody.append('<tr>' +
                '<td class="font-weight-bold">' + (r.agente_nombre || r.nombre || '—') + '</td>' +
                '<td class="text-right">' + fmtNum(r.atendidas) + '</td>' +
                '<td class="text-right">—</td>' +
                '<td class="text-right">—</td>' +
                '<td class="text-right">' + fmtTiempo(r.tmo_prom) + '</td>' +
                '<td class="text-right">—</td>' +
                '<td class="text-right">—</td>' +
                '<td class="text-right">—</td>' +
                '<td>—</td><td>—</td>' +
              '</tr>');
            });
          });
      });
  }

  // ── Tab: Campañas Alertas ─────────────────────────────────────

  function loadCampanas(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.campanasAlertas, filters)
      .done(function (rows) {
        var $tbody = $('#tbody-campanas-alertas').empty();
        if (!rows || !rows.length) {
          $tbody.append(
            '<tr><td colspan="9" class="text-center text-muted">Sin datos</td></tr>'
          );
          return;
        }
        $.each(rows, function (_, r) {
          var alerta = r.alerta;
          var rowCls = alerta ? 'table-danger' : '';
          var alertaBadge = alerta
            ? '<span class="badge badge-danger"><i class="fas fa-exclamation-triangle mr-1"></i>ALERTA</span>'
            : '<span class="badge badge-success">OK</span>';
          var nivel = parseFloat(r.nivel_atencion || 0);
          var nivelColor = nivel >= 80 ? '#28a745' : nivel >= 60 ? '#fd7e14' : '#dc3545';
          $tbody.append('<tr class="' + rowCls + '">' +
            '<td>' + alertaBadge + '</td>' +
            '<td class="font-weight-bold">' + (r.campana_nombre || r.campana_id || '—') + '</td>' +
            '<td class="text-right">' + fmtNum(r.total) + '</td>' +
            '<td class="text-right text-success">' + fmtNum(r.atendidas) + '</td>' +
            '<td class="text-right text-danger">' + fmtNum(r.abandonadas) + '</td>' +
            '<td class="text-right font-weight-bold" style="color:' + nivelColor + '">' +
              fmtNum(nivel, 2) + '%</td>' +
            '<td class="text-right">' + fmtNum(r.tmo_prom) + '</td>' +
            '<td class="text-right">' + fmtNum(r.espera_prom) + '</td>' +
            '<td class="text-right">' + fmtNum(r.agentes_activos) + '</td>' +
          '</tr>');
        });
      });
  }

  var _distData     = [];  // cache Distribución export
  var _salData      = [];  // cache Salientes export
  var _salDetalleData = []; // cache Salientes detalle export
  var _dialerData   = [];  // cache Dialer detalle export
  var _modalSesData = [];  // cache modal sesiones export
  var _modalPauData = [];  // cache modal pausas export

  // ── Tab: Agentes Avanzado ─────────────────────────────────────

  var _agavData = [];  // cache for export

  function fmtTiempoHMS(s) {
    s = Math.round(s || 0);
    if (s <= 0) return '00:00:00';
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var sec = s % 60;
    return (h < 10 ? '0' + h : h) + ':' +
           (m < 10 ? '0' + m : m) + ':' +
           (sec < 10 ? '0' + sec : sec);
  }

  function renderAgavHeatmap(data) {
    var $c = $('#agav-heatmap-container');
    if (!data || !data.dias || !data.dias.length) {
      $c.html('<p class="text-muted text-center p-3">Sin datos de disponibilidad</p>');
      return;
    }
    var dias = data.dias;
    var horas = data.horas;
    var mat = data.matriz;
    // Find max value for color scaling
    var maxVal = 0;
    mat.forEach(function (row) {
      row.forEach(function (v) { if (v > maxVal) maxVal = v; });
    });
    var html = '<table class="table table-sm table-bordered mb-0 horaria-tbl">';
    html += '<thead class="thead-light"><tr><th>Día / Hora</th>';
    horas.forEach(function (h) { html += '<th class="text-center">' + h + '</th>'; });
    html += '</tr></thead><tbody>';
    dias.forEach(function (dia, di) {
      html += '<tr><td class="font-weight-bold small">' + dia + '</td>';
      mat[di].forEach(function (v) {
        var pct = maxVal > 0 ? v / maxVal : 0;
        var cls = v === 0 ? 'heat-0' :
                  pct < 0.2 ? 'heat-1' :
                  pct < 0.4 ? 'heat-2' :
                  pct < 0.6 ? 'heat-3' :
                  pct < 0.8 ? 'heat-4' : 'heat-5';
        html += '<td class="' + cls + ' text-center small">' + (v > 0 ? v : '') + '</td>';
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    $c.html(html);
  }

  function renderAgavKpis(rows) {
    var conSesion = rows.filter(function (r) { return r.num_sesiones > 0; });
    var total = conSesion.length;
    if (!total) {
      $('#agav-kpi-total').text('0');
      $('#agav-kpi-prom, #agav-kpi-max, #agav-kpi-total-ses').text('—');
      return;
    }
    var tiempos = conSesion.map(function (r) { return r.tiempo_total_sesion || 0; });
    var tTotal = tiempos.reduce(function (a, b) { return a + b; }, 0);
    var tProm = Math.floor(tTotal / total);
    var tMax = Math.max.apply(null, tiempos);
    $('#agav-kpi-total').text(total);
    $('#agav-kpi-prom').text(fmtTiempo(tProm));
    $('#agav-kpi-max').text(fmtTiempo(tMax));
    $('#agav-kpi-total-ses').text(fmtTiempo(tTotal));
  }

  function renderAgavTable(rows) {
    _agavData = rows || [];
    var $tbody = $('#tbody-agav').empty();
    if (!rows || !rows.length) {
      $tbody.append('<tr><td colspan="9" class="text-center text-muted">Sin datos</td></tr>');
      return;
    }
    $.each(rows, function (_, r) {
      $tbody.append('<tr>' +
        '<td class="font-weight-bold">' + (r.nombre || '—') + '</td>' +
        '<td class="text-right">' + fmtNum(r.num_sesiones) + '</td>' +
        '<td class="text-right text-primary">' + fmtTiempo(r.tiempo_total_sesion) + '</td>' +
        '<td class="text-right">' + fmtTiempo(r.tiempo_promedio_sesion) + '</td>' +
        '<td class="text-right">' + fmtNum(r.num_pausas) + '</td>' +
        '<td class="text-right text-warning">' + fmtTiempo(r.tiempo_pausa_recreativa) + '</td>' +
        '<td class="text-right text-info">' + fmtTiempo(r.tiempo_pausa_productiva) + '</td>' +
        '<td class="text-right">' + fmtTiempo(r.tiempo_total_pausa) + '</td>' +
        '<td class="text-center">' +
          '<button class="btn btn-xs btn-outline-primary py-0 px-1 btn-agav-detalle" ' +
          'data-id="' + r.agente_id + '" data-nombre="' + (r.nombre || '') + '">' +
          '<i class="fas fa-eye mr-1"></i>Ver</button>' +
        '</td>' +
      '</tr>');
    });
  }

  function loadAgentesAvanzado(filters) {
    return $.when(
      apiFetch(ANALYTICS_CONFIG.urls.agentesCompleto, filters),
      apiFetch(ANALYTICS_CONFIG.urls.heatmapCompleto, filters)
    ).done(function (compData, heatData) {
      // $.when wraps each ajax result as [data, textStatus, jqXHR]
      // when multiple deferreds are used, so always use index [0].
      var rows = (compData && compData[0]) || [];
      var heat = (heatData && heatData[0]) || {};
      renderAgavKpis(rows);
      renderAgavHeatmap(heat);
      renderAgavTable(rows);
    });
  }

  // ── Modal: Detalle de agente ─────────────────────────────────

  function abrirDetalleAgente(agenteId, nombre) {
    $('#modal-agente-titulo').html('<i class="fas fa-user mr-1"></i> ' + nombre);
    $('#modal-ses-count, #modal-pau-count').text('…');
    $('#modal-sesiones-body').html(
      '<div class="text-center p-4"><div class="spinner-border text-primary" role="status"></div></div>'
    );
    $('#modal-pausas-body').html('');
    // Reset to sesiones tab
    $('#modal-tabs a[href="#modal-tab-sesiones"]').tab('show');
    $('#modal-agente-detalle').modal('show');

    var f = state.filters;
    var sesUrl = ANALYTICS_CONFIG.urls.sesionesAgente.replace('__ID__', agenteId);
    var pauUrl = ANALYTICS_CONFIG.urls.pausasAgente.replace('__ID__', agenteId);

    $.when(apiFetch(sesUrl, f), apiFetch(pauUrl, f))
      .done(function (sesData, pauData) {
        var ses = (sesData && sesData[0]) || [];
        var pau = (pauData && pauData[0]) || [];
        _modalSesData = ses;
        _modalPauData = pau;
        $('#modal-ses-count').text(ses.length);
        $('#modal-pau-count').text(pau.length);

        // Sesiones table
        if (!ses.length) {
          $('#modal-sesiones-body').html(
            '<p class="text-muted text-center p-3">Sin sesiones registradas</p>'
          );
        } else {
          var html = '<table class="table table-sm table-bordered table-hover">';
          html += '<thead class="thead-light"><tr>' +
                  '<th>Inicio</th><th>Fin</th><th>Duración</th>' +
                  '</tr></thead><tbody>';
          ses.forEach(function (s) {
            html += '<tr>' +
              '<td class="small">' + fmtDt(s.inicio) + '</td>' +
              '<td class="small">' + fmtDt(s.fin) + '</td>' +
              '<td class="small">' + fmtTiempo(s.duracion_s) + '</td>' +
            '</tr>';
          });
          html += '</tbody></table>';
          $('#modal-sesiones-body').html(html);
        }

        // Pausas table
        if (!pau.length) {
          $('#modal-pausas-body').html(
            '<p class="text-muted text-center p-3">Sin pausas registradas</p>'
          );
        } else {
          var pHtml = '<table class="table table-sm table-bordered table-hover">';
          pHtml += '<thead class="thead-light"><tr>' +
                   '<th>Tipo</th><th>Nombre</th>' +
                   '<th>Inicio</th><th>Fin</th><th>Duración</th>' +
                   '</tr></thead><tbody>';
          pau.forEach(function (p) {
            var tipoBadge = p.tipo === 'P'
              ? '<span class="badge badge-info">Productiva</span>'
              : '<span class="badge badge-warning">Recreativa</span>';
            pHtml += '<tr>' +
              '<td>' + tipoBadge + '</td>' +
              '<td class="small">' + (p.nombre || '—') + '</td>' +
              '<td class="small">' + fmtDt(p.inicio) + '</td>' +
              '<td class="small">' + fmtDt(p.fin) + '</td>' +
              '<td class="small">' + fmtTiempo(p.duracion_s) + '</td>' +
            '</tr>';
          });
          pHtml += '</tbody></table>';
          $('#modal-pausas-body').html(pHtml);
        }
      })
      .fail(function () {
        $('#modal-sesiones-body').html(
          '<div class="alert alert-danger m-3">Error cargando detalles</div>'
        );
      });
  }

  // ── Chart: Heatmap disponibilidad ────────────────────────────────

  function loadHeatmap(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.heatmap, filters)
      .done(function (data) {
        if (!data || !data.length) return;
        // Expected: [{agente: 'Nombre', data: [{x: '08:00', y: 1}, ...]}]
        // Or simpler: [{hora: 8, agentes_conectados: 3}]
        var series;
        if (data[0] && data[0].data) {
          // series format
          series = data;
        } else {
          // flat [{hora, agentes_conectados}] → single series
          series = [{
            name: 'Agentes conectados',
            data: data.map(function (r) {
              return { x: (r.hora || 0) + ':00', y: r.agentes_conectados || 0 };
            })
          }];
        }
        safeRender('chart-heatmap', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'heatmap', height: 200, toolbar: { show: false } },
            series: series,
            colors: ['#007bff'],
            dataLabels: { enabled: true },
            xaxis: { type: 'category' },
          });
        });
      });
  }

  // ── Distribución Horaria Detallada (tabla con sub-pestañas) ──────

  var _horariaData = [];       // cache last fetch
  var _horariaAgrup = 'hora';  // active grouping

  function fmtTiempo(s) {
    s = Math.round(s || 0);
    if (s <= 0) return '0s';
    var m = Math.floor(s / 60);
    var sec = s % 60;
    return m > 0 ? m + 'm ' + sec + 's' : sec + 's';
  }

  function renderHorariaTable(rows, agrup) {
    var $c = $('#horaria-tabla-container');
    if (!rows || !rows.length) {
      $c.html('<p class="text-muted p-3 text-center">Sin datos</p>');
      return;
    }
    var colLabel = {
      hora: 'RANGO HORARIO', dia: 'DÍA', semana: 'SEMANA',
      mes: 'MES', campana: 'CAMPAÑA',
    }[agrup] || 'GRUPO';

    var html = '<table class="table table-sm table-hover table-bordered mb-0" id="tbl-horaria-det">';
    html += '<thead class="thead-light"><tr>';
    html += '<th>' + colLabel + '</th>';
    html += '<th class="text-right">RECIBIDAS</th>';
    html += '<th class="text-right">ATENDIDAS</th>';
    html += '<th class="text-right">ABANDONADAS</th>';
    html += '<th class="text-right">TRANSFER.</th>';
    html += '<th class="text-right">% ATEND.</th>';
    html += '<th class="text-right">% ABAND.</th>';
    html += '<th class="text-right">T. ESPERA</th>';
    html += '<th class="text-right">T. ABAND.</th>';
    html += '<th class="text-right">DURACIÓN</th>';
    html += '</tr></thead><tbody>';

    rows.forEach(function (r) {
      var pctA = parseFloat(r.porcentaje_atendidas || 0);
      var pctB = parseFloat(r.porcentaje_abandonadas || 0);
      var colorA = pctA >= 80 ? '#28a745' : pctA >= 60 ? '#fd7e14' : '#dc3545';
      var colorB = pctB >= 30 ? '#dc3545' : pctB >= 15 ? '#fd7e14' : '#28a745';
      html += '<tr>';
      html += '<td class="font-weight-bold">' + (r.grupo || '') + '</td>';
      html += '<td class="text-right">' + fmtNum(r.total_llamadas) + '</td>';
      html += '<td class="text-right" style="color:' + colorA + '">' + fmtNum(r.atendidas) + '</td>';
      html += '<td class="text-right" style="color:' + colorB + '">' + fmtNum(r.abandonadas) + '</td>';
      html += '<td class="text-right text-primary">' + fmtNum(r.transferidas) + '</td>';
      html += '<td class="text-right font-weight-bold" style="color:' + colorA + '">' + (pctA).toFixed(2) + '%</td>';
      html += '<td class="text-right font-weight-bold" style="color:' + colorB + '">' + (pctB).toFixed(2) + '%</td>';
      html += '<td class="text-right text-secondary">' + fmtTiempo(r.tiempo_espera_promedio) + '</td>';
      html += '<td class="text-right text-secondary">' + fmtTiempo(r.tiempo_abandono_promedio) + '</td>';
      html += '<td class="text-right text-secondary">' + fmtTiempo(r.duracion_promedio) + '</td>';
      html += '</tr>';
    });
    html += '</tbody></table>';
    $c.html(html);
  }

  function loadDistribucionHoraria(filters, agrup) {
    agrup = agrup || _horariaAgrup;
    _horariaAgrup = agrup;
    var params = $.extend({}, filters, { agrupar_por: agrup });
    $('#horaria-tabla-container').html('<p class="text-muted p-3 text-center">Cargando...</p>');
    return apiFetch(ANALYTICS_CONFIG.urls.horariaTabla, params)
      .done(function (rows) {
        _horariaData = rows || [];
        renderHorariaTable(_horariaData, agrup);
      });
  }

  function initHorariaSubtabs() {
    $(document).on('click', '.horaria-agrup', function () {
      var agrup = $(this).data('agrup');
      $('.horaria-agrup').removeClass('active btn-primary').addClass('btn-light');
      $(this).removeClass('btn-light').addClass('active btn-primary');
      loadDistribucionHoraria(state.filters, agrup);
    });

    $('#btn-horaria-excel').on('click', function () {
      if (!_horariaData || !_horariaData.length) return;
      // Build CSV and trigger download (no external lib needed)
      var cols = [
        'Grupo','Recibidas','Atendidas','Abandonadas','Transferidas',
        '% Atendidas','% Abandonadas','T.Espera(s)','T.Abandono(s)','Duracion(s)'
      ];
      var lines = [cols.join(',')];
      _horariaData.forEach(function (r) {
        lines.push([
          '"' + (r.grupo || '') + '"',
          r.total_llamadas || 0,
          r.atendidas || 0,
          r.abandonadas || 0,
          r.transferidas || 0,
          r.porcentaje_atendidas || 0,
          r.porcentaje_abandonadas || 0,
          Math.round(r.tiempo_espera_promedio || 0),
          Math.round(r.tiempo_abandono_promedio || 0),
          Math.round(r.duracion_promedio || 0),
        ].join(','));
      });
      var blob = new Blob(['﻿' + lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url;
      a.download = 'distribucion_horaria_' + _horariaAgrup + '_' + fmtDate(new Date()) + '.csv';
      a.click();
      URL.revokeObjectURL(url);
    });
  }

  // ── Salientes ────────────────────────────────────────────────────

  function resultadoBadge(resultado) {
    if (resultado === 'Atendida' || resultado === 'Conectada a agente') return 'success';
    if (resultado === 'Abandonada') return 'danger';
    return 'secondary';
  }

  function loadSalientes(filters) {
    // Override tipo to salientes
    var p = $.extend({}, filters, { tipo_llamada: 'salientes' });
    return $.when(
      apiFetch(ANALYTICS_CONFIG.urls.salientes, p),
      apiFetch(ANALYTICS_CONFIG.urls.salientesAgente, p),
      loadSalientesDetalle(filters, 1)
    ).done(function (dashRes, agRes) {
      var d = dashRes[0];
      var totalSal = d.total_llamadas != null ? d.total_llamadas : (d.total != null ? d.total : null);
      var atendSal = d.contestadas != null ? d.contestadas : (d.atendidas != null ? d.atendidas : null);
      // no_contestadas from service only counts ABANDON (inbound) events → 0 for outbound.
      // Use total - answered as the business-meaningful "not answered" count.
      var noAtendSal = (totalSal != null && atendSal != null) ? (totalSal - atendSal)
                     : (d.no_contestadas != null ? d.no_contestadas
                     : (d.no_atendidas != null ? d.no_atendidas : null));
      var kpiDefs = [
        { label: 'Total salientes', value: fmtNum(totalSal) },
        { label: 'Atendidas',       value: fmtNum(atendSal) },
        { label: 'No atendidas',    value: fmtNum(noAtendSal) },
        { label: 'Tasa contacto',   value: fmtPct(d.tasa_contacto) },
      ];
      var $kpis = $('#salientes-kpis').empty();
      $.each(kpiDefs, function (_, k) {
        $kpis.append(
          '<div class="col-md-3 col-sm-6 mb-2">' +
          '<div class="card kpi-card border-left-primary">' +
          '<div class="card-body py-2">' +
          '<div class="small text-muted kpi-label">' + k.label + '</div>' +
          '<div class="h3 mb-0 kpi-value font-weight-bold">' + k.value + '</div>' +
          '</div></div></div>'
        );
      });
      var rows = agRes[0] || [];
      _salData = rows;
      var $tbody = $('#tbody-salientes-agente').empty();
      if (!rows.length) {
        $tbody.append('<tr><td colspan="6" class="text-center text-muted">Sin datos</td></tr>');
      } else {
        $.each(rows, function (_, r) {
          var atend = r.contestadas != null ? r.contestadas : (r.atendidas != null ? r.atendidas : null);
          var total = r.total_llamadas || r.total || 0;
          var noAtend = r.no_contestadas != null ? r.no_contestadas
                      : (r.no_atendidas != null ? r.no_atendidas
                      : (atend != null ? total - atend : null));
          var tasa = r.tasa_contacto != null ? r.tasa_contacto
                   : (atend != null && total > 0 ? atend / total * 100 : null);
          $tbody.append('<tr>' +
            '<td>' + (r.agente_nombre || r.nombre || '—') + '</td>' +
            '<td>' + fmtNum(total) + '</td>' +
            '<td>' + fmtNum(atend) + '</td>' +
            '<td>' + fmtNum(noAtend) + '</td>' +
            '<td>' + fmtPct(tasa) + '</td>' +
            '<td>' + fmtNum(r.tmo_prom) + '</td>' +
          '</tr>');
        });
      }
    });
  }

  function loadSalientesDetalle(filters, page) {
    page = page || 1;
    var params = $.extend({}, filters, { page: page, per_page: state.perPage });
    return apiFetch(ANALYTICS_CONFIG.urls.salientesDetalle, params)
      .done(function (d) {
        var rows = d.data || [];
        var total = d.total || rows.length;
        _salDetalleData = rows;
        var $tbody = $('#tbody-salientes-detalle').empty();
        if (!rows.length) {
          $tbody.append('<tr><td colspan="8" class="text-center text-muted">Sin datos</td></tr>');
        } else {
          $.each(rows, function (_, r) {
            $tbody.append('<tr>' +
              '<td>' + fmtDt(r.fecha || r.time) + '</td>' +
              '<td>' + (r.campana_nombre || '—') + '</td>' +
              '<td>' + (r.agente_nombre || '—') + '</td>' +
              '<td class="text-monospace small">' + (r.callid || '—') + '</td>' +
              '<td><span class="badge badge-' + resultadoBadge(r.resultado) + '">' + (r.resultado || '—') + '</span></td>' +
              '<td>' + fmtNum(r.bridge_wait_time) + '</td>' +
              '<td>' + fmtNum(r.duracion_llamada) + '</td>' +
              '<td>' + (r.numero_marcado || '—') + '</td>' +
            '</tr>');
          });
        }
        renderPagination('#pag-salientes-detalle', page, total, state.perPage, function (p) {
          state.salientesDetallePage = p;
          loadSalientesDetalle(state.filters, p);
        });
      });
  }

  // ── Dialer ───────────────────────────────────────────────────────

  function loadDialer(filters, page) {
    page = page || 1;
    return $.when(
      apiFetch(ANALYTICS_CONFIG.urls.dialerDashboard, filters),
      loadDialerDetalle(filters, page)
    ).done(function (dashRes) {
      var d = dashRes[0] || {};
      var kpiDefs = [
        { label: 'Intentos',               value: fmtNum(d.intentos) },
        { label: 'Conectadas a Agente',    value: fmtNum(d.conectadas_agente) },
        { label: 'Abandonadas en Cola',    value: fmtNum(d.abandonadas_cola) },
        { label: 'No Contactadas',         value: fmtNum(d.no_contactadas) },
        { label: 'Contactabilidad',        value: fmtPct(d.tasa_contactabilidad) },
        { label: 'Tasa Conexión a Agente', value: fmtPct(d.tasa_conexion_agente) },
        { label: 'Tiempo en Cola Prom.',   value: fmtNum(d.tiempo_cola_promedio_s) + ' s' },
        { label: 'TMO Promedio',           value: fmtNum(d.tmo_promedio) + ' s' },
      ];
      var $kpis = $('#dialer-kpis').empty();
      $.each(kpiDefs, function (_, k) {
        $kpis.append(
          '<div class="col-md-3 col-sm-6 mb-2">' +
          '<div class="card kpi-card border-left-secondary">' +
          '<div class="card-body py-2">' +
          '<div class="small text-muted kpi-label">' + k.label + '</div>' +
          '<div class="h3 mb-0 kpi-value font-weight-bold">' + k.value + '</div>' +
          '</div></div></div>'
        );
      });
    });
  }

  function loadDialerDetalle(filters, page) {
    page = page || 1;
    var params = $.extend({}, filters, { page: page, per_page: state.perPage });
    return apiFetch(ANALYTICS_CONFIG.urls.dialerDetalle, params)
      .done(function (d) {
        var rows = d.data || [];
        var total = d.total || rows.length;
        _dialerData = rows;
        var $tbody = $('#tbody-dialer').empty();
        if (!rows.length) {
          $tbody.append('<tr><td colspan="8" class="text-center text-muted">Sin datos</td></tr>');
        } else {
          $.each(rows, function (_, r) {
            $tbody.append('<tr>' +
              '<td>' + fmtDt(r.fecha || r.time) + '</td>' +
              '<td>' + (r.campana_nombre || '—') + '</td>' +
              '<td>' + (r.agente_nombre || '—') + '</td>' +
              '<td class="text-monospace small">' + (r.callid || '—') + '</td>' +
              '<td><span class="badge badge-' + resultadoBadge(r.resultado) + '">' + (r.resultado || '—') + '</span></td>' +
              '<td>' + fmtNum(r.bridge_wait_time) + '</td>' +
              '<td>' + fmtNum(r.duracion_llamada) + '</td>' +
              '<td>' + (r.numero_marcado || '—') + '</td>' +
            '</tr>');
          });
        }
        renderPagination('#pag-dialer', page, total, state.perPage, function (p) {
          state.dialerPage = p;
          loadDialerDetalle(state.filters, p);
        });
      });
  }

  // ── Transferencias ───────────────────────────────────────────────

  function loadTransferencias(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.transferencias, filters)
      .done(function (rows) {
        var $tbody = $('#tbody-transferencias').empty();
        if (!rows || !rows.length) {
          $tbody.append('<tr><td colspan="2" class="text-center text-muted">Sin datos</td></tr>');
          document.querySelector('#chart-transferencias').innerHTML = '';
          return;
        }
        $.each(rows, function (_, r) {
          $tbody.append('<tr>' +
            '<td>' + (r.descripcion || r.event || r.tipo || '—') + '</td>' +
            '<td class="text-right">' + fmtNum(r.cantidad || r.count || 0) + '</td>' +
          '</tr>');
        });
        // Donut chart
        var labels = rows.map(function (r) { return r.descripcion || r.event || r.tipo || '—'; });
        var vals   = rows.map(function (r) { return r.cantidad || r.count || 0; });
        safeRender('chart-transferencias', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'pie', height: 260, toolbar: { show: false } },
            series: vals, labels: labels, colors: APEXCOLORS,
            legend: { position: 'bottom' },
          });
        });
      });
  }

  // ── Load everything for active tab ───────────────────────────────

  function loadResumen(f) {
    return $.when(
      loadKpis(f),
      loadDistribucion(f),
      loadNivelServicio(f),
      loadEvolucionHora(f),
      loadCausas(f),
      loadEvolucionDiaria(f)
    );
  }

  // ── KPI Tab ──────────────────────────────────────────────────────

  function loadKpisTab(filters) {
    return $.when(
      apiFetch(ANALYTICS_CONFIG.urls.kpis, filters),
      apiFetch(ANALYTICS_CONFIG.urls.llamadasPorTipo, filters),
      apiFetch(ANALYTICS_CONFIG.urls.agentesCompleto, filters)
    ).done(function (kpiRes, tipoRes, agavRes) {
      var kpi      = (kpiRes  && kpiRes[0])  || {};
      var agavList = (agavRes && agavRes[0]) || [];

      // ── Compute global ocupacion from agent data ──────────────────
      var totalSesion = 0, totalHabla = 0;
      if (Array.isArray(agavList)) {
        agavList.forEach(function (a) {
          totalSesion += (a.tiempo_total_sesion || 0);
          totalHabla  += (a.tiempo_al_habla     || 0);
        });
      }
      var ocupacion = totalSesion > 0
        ? Math.min(totalHabla / totalSesion * 100, 100)
        : 0;

      // ── Top cards: Entrantes / Salientes / Dialer ────────────────
      // API now returns a dict {entrantes:{...}, salientes:{...}, dialer:{...}}
      var tipoDict = (tipoRes && tipoRes[0]) || {};
      var ent = tipoDict.entrantes || {};
      var sal = tipoDict.salientes || {};
      var dial = tipoDict.dialer || {};

      function fillEntrantesCard(data) {
        var total   = data.total          || 0;
        var atend   = data.atendidas      || 0;
        var noAtend = data.abandonadas    || 0;   // campo separado del servicio
        var nivel   = data.nivel_atencion || 0;   // at / (at+ab) × 100
        var tasa    = data.tasa_abandono  || 0;   // ab / (at+ab) × 100
        $('#kpi-ent-total').text(fmtNum(total));
        $('#kpi-ent-atendidas').text(fmtNum(atend));
        $('#kpi-ent-no-atendidas').text(fmtNum(noAtend));
        $('#kpi-ent-nivel').text(fmtNum(nivel, 1) + '%');
        $('#kpi-ent-bar').css('width', Math.min(nivel, 100).toFixed(1) + '%');
        $('#kpi-ent-tasa').text(fmtNum(tasa, 1) + '%');
      }

      function fillSalientesCard(data) {
        var total   = data.total           || 0;
        var atend   = data.atendidas       || 0;
        var noAtend = data.no_atendidas    || 0;  // campo separado del servicio
        var nivel   = data.nivel_atencion  || 0;  // at / (at+no_at) × 100
        var tasa    = data.tasa_no_atencion || 0; // no_at / (at+no_at) × 100
        $('#kpi-sal-total').text(fmtNum(total));
        $('#kpi-sal-atendidas').text(fmtNum(atend));
        $('#kpi-sal-no-atendidas').text(fmtNum(noAtend));
        $('#kpi-sal-nivel').text(fmtNum(nivel, 1) + '%');
        $('#kpi-sal-bar').css('width', Math.min(nivel, 100).toFixed(1) + '%');
        $('#kpi-sal-tasa').text(fmtNum(tasa, 1) + '%');
      }

      function fillDialerCard(data) {
        var total      = data.total              || 0;
        var conectadas = data.conectadas_agente   || 0;
        var noContact  = data.no_contactadas      || 0;
        var contacto   = data.tasa_contactabilidad || 0;   // contactadas / total × 100
        var conexion   = data.tasa_conexion_agente || 0;   // conectadas / contactadas × 100
        $('#kpi-dial-total').text(fmtNum(total));
        $('#kpi-dial-conectadas').text(fmtNum(conectadas));
        $('#kpi-dial-no-contactadas').text(fmtNum(noContact));
        $('#kpi-dial-nivel').text(fmtNum(contacto, 1) + '%');
        $('#kpi-dial-bar').css('width', Math.min(contacto, 100).toFixed(1) + '%');
        $('#kpi-dial-tasa').text(fmtNum(conexion, 1) + '%');
      }

      fillEntrantesCard(ent);
      fillSalientesCard(sal);
      fillDialerCard(dial);

      // ── Metric cards ─────────────────────────────────────────────
      $('#km-total').text(fmtNum(kpi.total_llamadas));
      $('#km-atendidas').text(fmtNum(kpi.llamadas_atendidas));
      $('#km-abandonadas').text(fmtNum(kpi.llamadas_abandonadas));
      $('#km-no-atendidas').text(fmtNum(sal.no_atendidas));  // salientes no contactadas
      $('#km-aht').text(fmtNum(kpi.tmo_promedio));
      $('#km-asa').text(fmtNum(kpi.espera_promedio));
      $('#km-sla60').text(fmtNum(kpi.nivel_servicio_60, 1));
      $('#km-sla20').text(fmtNum(kpi.nivel_servicio_20, 1));
      $('#km-tasa-abandono').text(fmtNum(kpi.tasa_abandono, 1));
      $('#km-agentes').text(fmtNum(kpi.agentes_activos));
      $('#km-ocupacion').text(fmtNum(ocupacion, 1));
    });
  }

  // ── Refresh: load data for all visible content ────────────────────

  function refresh() {
    state.filters = buildFilters();
    var f = state.filters;
    var activeTab = $('#analytics-tabs .nav-link.active').attr('href');
    loading(true);
    var req;
    switch (activeTab) {
      case '#tab-kpis':         req = loadKpisTab(f); break;
      case '#tab-resumen':      req = loadResumen(f); break;
      case '#tab-atendidas':    req = loadAtendidas(f, 1); break;
      case '#tab-abandonadas':  req = loadAbandonadas(f, 1); break;
      case '#tab-distribucion': req = loadDistCampana(f); break;
      case '#tab-campanas':     req = loadCampanas(f); break;
      case '#tab-agentes':
        req = $.when(loadAgentesRendimiento(f), loadHeatmap(f)); break;
      case '#tab-agentes-avanzado': req = loadAgentesAvanzado(f); break;
      case '#tab-horaria':
        req = loadDistribucionHoraria(f, _horariaAgrup); break;
      case '#tab-salientes':    req = loadSalientes(f); break;
      case '#tab-dialer':       req = loadDialer(f, 1); break;
      case '#tab-transferencias': req = loadTransferencias(f); break;
      default: req = loadKpisTab(f);
    }
    if (req && req.always) {
      req.always(function () { loading(false); });
    } else {
      loading(false);
    }
  }

  // ── Export helpers ───────────────────────────────────────────────

  function triggerExport(url) {
    var params = buildFilters();
    window.location.href = url + qs(params);
  }

  // ── Tab switch: lazy-load ─────────────────────────────────────────

  function onTabShow(tabHref) {
    var f = state.filters;
    loading(true);
    var req;
    switch (tabHref) {
      case '#tab-kpis':         req = loadKpisTab(f); break;
      case '#tab-resumen':      req = loadResumen(f); break;
      case '#tab-atendidas':    req = loadAtendidas(f, 1); break;
      case '#tab-abandonadas':  req = loadAbandonadas(f, 1); break;
      case '#tab-distribucion': req = loadDistCampana(f); break;
      case '#tab-campanas':     req = loadCampanas(f); break;
      case '#tab-agentes':
        req = $.when(loadAgentesRendimiento(f), loadHeatmap(f)); break;
      case '#tab-agentes-avanzado': req = loadAgentesAvanzado(f); break;
      case '#tab-horaria':
        req = loadDistribucionHoraria(f, _horariaAgrup); break;
      case '#tab-salientes':    req = loadSalientes(f); break;
      case '#tab-dialer':       req = loadDialer(f, 1); break;
      case '#tab-transferencias': req = loadTransferencias(f); break;
    }
    if (req && req.always) {
      req.always(function () { loading(false); });
    } else {
      loading(false);
    }
  }

  // ── Date Range Quick-Select ───────────────────────────────────────

  function initDateRangeButtons() {
    var $btns = $('#date-range-btns .btn-dr');

    // Compute the start/end for a given preset key
    function datesForPreset(range) {
      var today = new Date();
      var ini, fin;
      fin = new Date(today);

      switch (range) {
        case 'hoy':
          ini = new Date(today);
          break;
        case 'ayer':
          ini = new Date(today); ini.setDate(today.getDate() - 1);
          fin = new Date(ini);
          break;
        case '7dias':
          ini = new Date(today); ini.setDate(today.getDate() - 6);
          break;
        case '30dias':
          ini = new Date(today); ini.setDate(today.getDate() - 29);
          break;
        case 'este-mes':
          ini = new Date(today.getFullYear(), today.getMonth(), 1);
          break;
        case 'ultimo-mes':
          fin = new Date(today.getFullYear(), today.getMonth(), 0); // last day prev month
          ini = new Date(fin.getFullYear(), fin.getMonth(), 1);
          break;
        default:
          return null;
      }
      return { ini: fmtDate(ini), fin: fmtDate(fin) };
    }

    // Mark the button whose preset matches current date inputs (if any)
    function detectActivePreset() {
      var curIni = $('#f-fecha-inicio').val();
      var curFin = $('#f-fecha-fin').val();
      var presets = ['hoy', 'ayer', '7dias', '30dias', 'este-mes', 'ultimo-mes'];
      var matched = 'custom';
      for (var i = 0; i < presets.length; i++) {
        var d = datesForPreset(presets[i]);
        if (d && d.ini === curIni && d.fin === curFin) {
          matched = presets[i];
          break;
        }
      }
      $btns.removeClass('active');
      $btns.filter('[data-range="' + matched + '"]').addClass('active');
    }

    detectActivePreset();

    $btns.on('click', function () {
      var range = $(this).data('range');
      $btns.removeClass('active');
      $(this).addClass('active');

      if (range === 'custom') {
        // Just highlights the button; user sets dates manually
        return;
      }

      var d = datesForPreset(range);
      if (!d) return;
      $('#f-fecha-inicio').val(d.ini);
      $('#f-fecha-fin').val(d.fin);

      // Auto-apply
      $('#btn-apply').trigger('click');
    });

    // If user edits a date manually → switch to Custom Range
    $('#f-fecha-inicio, #f-fecha-fin').on('change', function () {
      $btns.removeClass('active');
      $btns.filter('[data-range="custom"]').addClass('active');
    });
  }

  // ── Init ─────────────────────────────────────────────────────────

  function init() {
    if (state.initialized) return;
    state.initialized = true;

    // Default date range: last 30 days
    var today = new Date();
    var before = new Date();
    before.setDate(today.getDate() - 30);
    function fmt(d) {
      return d.getFullYear() + '-' +
        String(d.getMonth() + 1).padStart(2, '0') + '-' +
        String(d.getDate()).padStart(2, '0');
    }
    if (!$('#f-fecha-inicio').val()) $('#f-fecha-inicio').val(fmt(before));
    if (!$('#f-fecha-fin').val())   $('#f-fecha-fin').val(fmt(today));

    // Date range quick-select buttons
    initDateRangeButtons();

    // Horaria sub-tabs (Por Hora, Por Día, etc.)
    initHorariaSubtabs();

    // Load meta (campaigns + agents for selects)
    loadMeta();

    // Load sync status
    loadSyncStatus();

    // Apply button
    $('#btn-apply').on('click', refresh);

    // Tab switch
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
      onTabShow($(e.target).attr('href'));
    });

    // Export buttons
    $('#btn-export-atendidas').on('click', function () {
      triggerExport(ANALYTICS_CONFIG.urls.exportAtendidas);
    });
    $('#btn-export-abandonadas').on('click', function () {
      triggerExport(ANALYTICS_CONFIG.urls.exportAbandonadas);
    });
    $('#btn-export-agentes').on('click', function () {
      triggerExport(ANALYTICS_CONFIG.urls.exportAgentes);
    });

    // Export: campañas alertas (CSV client-side)
    $('#btn-export-campanas').on('click', function () {
      var $rows = $('#tbl-campanas-alertas tbody tr');
      if (!$rows.length) return;
      var lines = ['﻿Campaña,Total,Atendidas,Abandonadas,Nivel Atención %,TMO (s),Espera Prom (s),Alerta'];
      $rows.each(function () {
        var $td = $(this).find('td');
        if ($td.length < 9) return;
        var alerta = $(this).hasClass('table-danger') ? 'SI' : 'NO';
        lines.push([
          '"' + ($td.eq(1).text() || '') + '"',
          $td.eq(2).text(), $td.eq(3).text(), $td.eq(4).text(),
          $td.eq(5).text(), $td.eq(6).text(), $td.eq(7).text(), alerta
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'campanas_alertas.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
    });

    // Export: agentes avanzado (CSV client-side)
    $('#btn-export-agav').on('click', function () {
      if (!_agavData.length) return;
      var lines = [
        '﻿Agente,Sesiones,T.Sesión Total,T.Sesión Prom,Pausas,' +
        'T.Pausa Rec,T.Pausa Prod,T.Pausa Total'
      ];
      _agavData.forEach(function (r) {
        lines.push([
          '"' + (r.nombre || '') + '"',
          r.num_sesiones, r.tiempo_total_sesion, r.tiempo_promedio_sesion,
          r.num_pausas, r.tiempo_pausa_recreativa,
          r.tiempo_pausa_productiva, r.tiempo_total_pausa
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'agentes_avanzado.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(url);
    });

    // Modal: click on "Ver" button in Agentes Avanzado table
    $(document).on('click', '.btn-agav-detalle', function () {
      var agenteId = $(this).data('id');
      var nombre = $(this).data('nombre');
      abrirDetalleAgente(agenteId, nombre);
    });

    // Export: Distribución por campaña (CSV client-side)
    $('#btn-export-dist').on('click', function () {
      if (!_distData.length) return;
      var lines = ['﻿Campaña,Total,Atendidas,Abandonadas,No atendidas,Nivel Atención %,TMO (s),Espera Prom (s)'];
      _distData.forEach(function (r) {
        lines.push([
          '"' + (r.campana_nombre || r.nombre || '') + '"',
          r.total_llamadas || r.total || 0,
          r.total_atendidas || r.atendidas || 0,
          r.total_abandonadas || r.abandonadas || 0,
          r.total_no_atendidas || r.no_atendidas || 0,
          r.nivel_atencion != null ? (r.nivel_atencion).toFixed(2) : '',
          Math.round(r.tmo_prom || 0),
          Math.round(r.espera_prom || 0)
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = 'distribucion_campanas.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(a.href);
    });

    // Export: Salientes por agente (CSV client-side)
    $('#btn-export-salientes').on('click', function () {
      if (!_salData.length) return;
      var lines = ['﻿Agente,Total,Atendidas,No atendidas,Tasa contacto %,TMO (s)'];
      _salData.forEach(function (r) {
        var atend = r.contestadas != null ? r.contestadas : (r.atendidas != null ? r.atendidas : 0);
        var total = r.total_llamadas || r.total || 0;
        var noAtend = r.no_contestadas != null ? r.no_contestadas
                    : (r.no_atendidas != null ? r.no_atendidas : total - atend);
        var tasa = r.tasa_contacto != null ? r.tasa_contacto
                 : (total > 0 ? atend / total * 100 : 0);
        lines.push([
          '"' + (r.agente_nombre || r.nombre || '') + '"',
          total, atend, noAtend,
          tasa != null ? tasa.toFixed(2) : '',
          Math.round(r.tmo_prom || 0)
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = 'salientes_agente.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(a.href);
    });

    // Export: Detalle de llamadas (CSV client-side, reutilizado por
    // Salientes-detalle y Dialer — misma forma de fila).
    function exportDetalleCsv(rows, filename) {
      if (!rows.length) return;
      var lines = ['﻿Fecha/Hora,Campaña,Agente,Call ID,Resultado,Espera (s),Duración (s),Número'];
      rows.forEach(function (r) {
        lines.push([
          '"' + fmtDt(r.fecha || r.time) + '"',
          '"' + (r.campana_nombre || '') + '"',
          '"' + (r.agente_nombre || '') + '"',
          '"' + (r.callid || '') + '"',
          '"' + (r.resultado || '') + '"',
          r.bridge_wait_time || 0,
          r.duracion_llamada || 0,
          '"' + (r.numero_marcado || '') + '"'
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = filename;
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(a.href);
    }

    $('#btn-export-salientes-detalle').on('click', function () {
      exportDetalleCsv(_salDetalleData, 'salientes_detalle.csv');
    });

    $('#btn-export-dialer').on('click', function () {
      exportDetalleCsv(_dialerData, 'dialer_detalle.csv');
    });

    // Export: Modal Sesiones (CSV client-side)
    $('#btn-export-modal-ses').on('click', function () {
      if (!_modalSesData.length) return;
      var agente = $('#modal-agente-titulo').text().trim();
      var lines = ['﻿Inicio,Fin,Duración (s)'];
      _modalSesData.forEach(function (s) {
        lines.push([
          '"' + (s.inicio || '') + '"',
          '"' + (s.fin || '') + '"',
          s.duracion_s || 0
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'sesiones_' + agente.replace(/\s+/g, '_') + '.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(a.href);
    });

    // Export: Modal Pausas (CSV client-side)
    $('#btn-export-modal-pau').on('click', function () {
      if (!_modalPauData.length) return;
      var agente = $('#modal-agente-titulo').text().trim();
      var lines = ['﻿Tipo,Nombre,Inicio,Fin,Duración (s)'];
      _modalPauData.forEach(function (p) {
        lines.push([
          '"' + (p.tipo === 'P' ? 'Productiva' : p.tipo === 'R' ? 'Recreativa' : (p.tipo || '')) + '"',
          '"' + (p.nombre || '') + '"',
          '"' + (p.inicio || '') + '"',
          '"' + (p.fin || '') + '"',
          p.duracion_s || 0
        ].join(','));
      });
      var blob = new Blob([lines.join('\r\n')], { type: 'text/csv;charset=utf-8;' });
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'pausas_' + agente.replace(/\s+/g, '_') + '.csv';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); URL.revokeObjectURL(a.href);
    });

    // Initial load
    state.filters = buildFilters();
    loadKpisTab(state.filters).always(function () { loading(false); });
  }

  // ── Bootstrap ────────────────────────────────────────────────────

  $(document).ready(function () {
    if (typeof ANALYTICS_CONFIG !== 'undefined') {
      init();
    }
  });

}(jQuery));

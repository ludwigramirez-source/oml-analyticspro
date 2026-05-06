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

  // ── Table: Rendimiento agentes ───────────────────────────────────

  function loadAgentesRendimiento(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.agentesRendimiento, filters)
      .done(function (rows) {
        var $tbody = $('#tbody-agentes').empty();
        if (!rows || !rows.length) {
          $tbody.append('<tr><td colspan="7" class="text-center text-muted">Sin datos</td></tr>');
          return;
        }
        $.each(rows, function (_, r) {
          $tbody.append('<tr>' +
            '<td>' + (r.agente_nombre || r.nombre || '—') + '</td>' +
            '<td>' + (r.extension || r.sip_extension || '—') + '</td>' +
            '<td class="text-right">' + fmtNum(r.total_llamadas || r.total) + '</td>' +
            '<td class="text-right">' + fmtNum(r.atendidas) + '</td>' +
            '<td class="text-right">' + fmtNum(r.abandonadas) + '</td>' +
            '<td class="text-right">' + fmtNum(r.tmo_prom) + '</td>' +
            '<td class="text-right">' + fmtNum(r.espera_prom) + '</td>' +
          '</tr>');
        });
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

  // ── Chart: Distribución horaria detallada ─────────────────────────

  function loadHorariaDet(filters) {
    var params = $.extend({}, filters, { agrupar_por: 'hora' });
    return apiFetch(ANALYTICS_CONFIG.urls.horariaDet, params)
      .done(function (rows) {
        if (!rows || !rows.length) return;
        var cats  = rows.map(function (r) { return r.hora !== undefined ? r.hora + ':00' : r.label; });
        var vals  = rows.map(function (r) { return r.total || r.atendidas || 0; });
        safeRender('chart-horaria-detalle', function (el) {
          return new ApexCharts(el, {
            chart: { type: 'bar', height: 300, toolbar: { show: false } },
            series: [{ name: 'Llamadas', data: vals }],
            xaxis: { categories: cats },
            colors: ['#17a2b8'],
            dataLabels: { enabled: false },
          });
        });
      });
  }

  // ── Table: Tabla distribución horaria (hora×día) ──────────────────

  function loadHorariaTabla(filters) {
    return apiFetch(ANALYTICS_CONFIG.urls.horariaTabla, filters)
      .done(function (d) {
        var $c = $('#horaria-tabla-container');
        if (!d || (!d.rows && !d.length)) {
          $c.html('<p class="text-muted p-3 text-center">Sin datos</p>');
          return;
        }
        // Expected format: {headers: ['Hora', 'Lun', ...], rows: [[8, 5, 3, ...]]}
        // OR flat array [{fecha, hora, total}] — pivot by day-of-week × hour
        var headers, rows, maxVal = 0;
        if (d.headers && d.rows) {
          headers = d.headers;
          rows    = d.rows;
          rows.forEach(function (r) {
            r.slice(1).forEach(function (v) { if (v > maxVal) maxVal = v; });
          });
        } else if (Array.isArray(d) && d.length) {
          // Pivot flat [{fecha:'2025-07-16', hora:8, total:5}] → hora x dow
          var DAYS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
          headers = ['Hora'].concat(DAYS);
          // Build hora × dow accumulator
          var acc = {};
          d.forEach(function (r) {
            var hora = parseInt(r.hora, 10);
            var dow = r.fecha ? new Date(r.fecha + 'T12:00:00').getDay() : 0;
            if (!acc[hora]) acc[hora] = [0,0,0,0,0,0,0];
            acc[hora][dow] += (r.total || 0);
          });
          rows = [];
          Object.keys(acc).sort(function (a,b) { return +a - +b; }).forEach(function (h) {
            var row = [h + ':00'].concat(acc[h]);
            rows.push(row);
            acc[h].forEach(function (v) { if (v > maxVal) maxVal = v; });
          });
        } else {
          $c.html('<p class="text-muted p-3 text-center">Sin datos</p>');
          return;
        }
        var html = '<table class="table table-sm table-bordered horaria-tbl"><thead class="thead-light"><tr>';
        headers.forEach(function (h) { html += '<th>' + h + '</th>'; });
        html += '</tr></thead><tbody>';
        rows.forEach(function (row) {
          html += '<tr><td class="font-weight-bold">' + row[0] + '</td>';
          row.slice(1).forEach(function (v) {
            var cls = 'heat-0';
            if (maxVal > 0) {
              var ratio = v / maxVal;
              if (ratio > 0.8) cls = 'heat-5';
              else if (ratio > 0.6) cls = 'heat-4';
              else if (ratio > 0.4) cls = 'heat-3';
              else if (ratio > 0.2) cls = 'heat-2';
              else if (ratio > 0)   cls = 'heat-1';
            }
            html += '<td class="' + cls + '">' + (v || '') + '</td>';
          });
          html += '</tr>';
        });
        html += '</tbody></table>';
        $c.html(html);
      });
  }

  // ── Salientes ────────────────────────────────────────────────────

  function loadSalientes(filters) {
    // Override tipo to salientes
    var p = $.extend({}, filters, { tipo_llamada: 'salientes' });
    $.when(
      apiFetch(ANALYTICS_CONFIG.urls.salientes, p),
      apiFetch(ANALYTICS_CONFIG.urls.salientesAgente, p)
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

  // ── Refresh: load data for all visible content ────────────────────

  function refresh() {
    state.filters = buildFilters();
    var f = state.filters;
    var activeTab = $('#analytics-tabs .nav-link.active').attr('href');
    loading(true);
    var req;
    switch (activeTab) {
      case '#tab-resumen':      req = loadResumen(f); break;
      case '#tab-atendidas':    req = loadAtendidas(f, 1); break;
      case '#tab-abandonadas':  req = loadAbandonadas(f, 1); break;
      case '#tab-distribucion': req = loadDistCampana(f); break;
      case '#tab-agentes':
        req = $.when(loadAgentesRendimiento(f), loadHeatmap(f)); break;
      case '#tab-horaria':
        req = $.when(loadHorariaDet(f), loadHorariaTabla(f)); break;
      case '#tab-salientes':    req = loadSalientes(f); break;
      case '#tab-transferencias': req = loadTransferencias(f); break;
      default: req = loadResumen(f);
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
      case '#tab-resumen':      req = loadResumen(f); break;
      case '#tab-atendidas':    req = loadAtendidas(f, 1); break;
      case '#tab-abandonadas':  req = loadAbandonadas(f, 1); break;
      case '#tab-distribucion': req = loadDistCampana(f); break;
      case '#tab-agentes':
        req = $.when(loadAgentesRendimiento(f), loadHeatmap(f)); break;
      case '#tab-horaria':
        req = $.when(loadHorariaDet(f), loadHorariaTabla(f)); break;
      case '#tab-salientes':    req = loadSalientes(f); break;
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

    // Initial load
    state.filters = buildFilters();
    loadResumen(state.filters).always(function () { loading(false); });
  }

  // ── Bootstrap ────────────────────────────────────────────────────

  $(document).ready(function () {
    if (typeof ANALYTICS_CONFIG !== 'undefined') {
      init();
    }
  });

}(jQuery));

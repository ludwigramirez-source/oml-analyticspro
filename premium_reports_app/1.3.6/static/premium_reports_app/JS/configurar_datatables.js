// Copyright (C) 2018 Freetech Solutions

/* global Urls gettext atendidas no_atendidas distribuciones_generales distribuciones_salientes 
    atendidas_por_agente */

var FILENAMES = {
    '#table_datos_por_campana': gettext('Distribucion llamadas por campaña'),
    '#table_datos_por_rango_horario': gettext('Distribucion llamadas por horario'),
    '#table_datos_por_mes': gettext('Distribucion llamadas por mes'),
    '#table_datos_por_semana': gettext('Distribucion llamadas por semana'),
    '#table_datos_por_dia': gettext('Distribucion llamadas por dia'),
    '#table_datos_por_hora': gettext('Distribucion llamadas por hora'),
    '#table_datos_campana': gettext('Distribucion llamadas manuales por campaña'),
    '#table_datos_rango_horario': gettext('Distribucion llamadas manuales por rango horario'),
    '#table_datos_mes': gettext('Distribucion llamadas manuales por mes'),
    '#table_datos_semana': gettext('Distribucion llamadas manuales por semana'),
    '#table_datos_dia': gettext('Distribucion llamadas manuales por dia'),
    '#table_datos_hora': gettext('Distribucion llamadas manuales por hora'),
};

$(function(){
    generarDataTablesDistribuciones();
    generarDataTablesLlamadasAtendidas();
    generarDataTablesLlamadasNoAtendidas();
    generarDataTablesActividadAgentes();

    prepararTablasLlamadasDinamicas();
});

function generarDataTablesDistribuciones() {
    var distribuciones = [ 'por_campana', 'por_rango_horario', 'por_mes', 'por_semana',
        'por_dia', 'por_hora',];
    // Si estan las tablas de llamadas salientes manuales:
    if ($('#salientes').length > 0) {
        distribuciones = distribuciones.concat(['campana', 'rango_horario', 'mes', 'semana',
            'dia', 'hora']);
    }

    distribuciones.forEach(function(id_menu){
        var id_table = '#table_datos_' + id_menu;
        generarDataTableCategoria(id_table);
    });
}

function generarDataTableCategoria(id_table) {
    var cant_columnas = $(id_table + ' th').length;
    var columnas_a_exportar = Array(cant_columnas - 1);
    for (var i = 1; i < cant_columnas; i++) {columnas_a_exportar[i-1] = i;}
    // Excluyo la primer columna (Boton modal detalle llamadas)
    generarDataTableConDatosLocales($(id_table), FILENAMES[id_table], columnas_a_exportar);
}

function generarDataTablesLlamadasAtendidas() {
    generarDataTableConDatosLocales(
        $('#table_nivel_servicio'), gettext('Nivel de servicio'));
    // Excluyo la primer columna (Boton modal detalle llamadas)
    generarDataTableConDatosLocales(
        $('#table_llamadas_atendidas_por_agente'), gettext('Llamadas atendidas por agente'),
        [1,2,3,4,5,6,7]);
    generarDataTableConDatosLocales(
        $('#table_causas_desconexion'), gettext('Causas de desconexión'));
}

function generarDataTablesLlamadasNoAtendidas() {
    generarDataTableConDatosLocales(
        $('#table_causas_no_conexion'), gettext('Causas de no conexión'));
    generarDataTableConDatosLocales(
        $('#table_sin_conexion_agente'), gettext('Llamadas sin conexión por agente'));
    generarDataTableConDatosLocales(
        $('#table_sin_conexion_campana'), gettext('Llamadas sin conexión por campaña'));
}

function generarDataTablesActividadAgentes() {
    generarDataTableConDatosLocales(
        $('#table_disponibilidad_agentes'), gettext('Disponibilidad de agentes'));
    generarDataTableConDatosLocales(
        $('#table_agentes_por_hora_dia'), gettext('Número de agentes por día y hora'));
    generarDataTableDetalleActividadPorAgente('sesiones');
    generarDataTableDetalleActividadPorAgente('pausas');
}

function generarDataTableDetalleActividadPorAgente(grupo) {
    $('[grupo="table_modal_' + grupo + '_de_agente"]').each(function(i, table) {
        var identificador = $(table).attr('identificador');
        var filename = gettext('Detalle Sesiones agente ') + identificador;
        if (grupo == 'pausas')
            filename = gettext('Detalle Pausas agente ') + identificador;
        generarDataTableConDatosLocales(table, filename);
    });
}

function generarDataTableConDatosLocales(table, filename, columnas_a_exportar) {
    if ($(table).find('[empty_table]').length > 0)
        return;
    $(table).DataTable({
        ordering: false,
        dom: 'tilBpr',
        buttons: [
            {
                extend: 'csv',
                text: gettext('Descargar CSV'),
                filename: filename,
                exportOptions: {columns: columnas_a_exportar},
            },
        ],
        language: {
            paginate: {
                first: gettext('Primero'),
                previous: gettext('Anterior'),
                next: gettext('Siguiente'),
                last: gettext('Último')
            },
            lengthMenu: gettext('Mostrar _MENU_ entradas'),
            info: gettext('Mostrando _START_ a _END_ de _TOTAL_ entradas'),
        }
    });
}

/* DATATABLES DINAMICAS */

var CATEGORIAS = ['por_campana', 'por_rango_horario', 'por_mes', 'por_semana', 'por_dia', 'por_hora'];

function prepararTablasLlamadasDinamicas() {
    $('#detalle_llamada').one('click', function (){
        generarDataTableCallDetails(
            $('#table_llamadas_atendidas'), 'table_llamadas_atendidas', atendidas);
    });
    $('#detalle_no_atendidas').one('click', function (){
        generarDataTableCallDetails(
            $('#table_llamadas_no_atendidas'), 'table_llamadas_no_atendidas', no_atendidas);
    });
    prepararTablasAtendidasPorAgente();

    prepararTablasPorCategoria('modal_distribucion', distribuciones_generales);
    if (distribuciones_salientes != undefined)
        prepararTablasPorCategoria('modal_saliente', distribuciones_salientes);
}

function prepararTablasPorCategoria(modal, distribuciones){
    for (var i=0; i < CATEGORIAS.length; i++) {
        var categoria = CATEGORIAS[i];
        $('[id^=' + modal + '_' + categoria + ']').each(function () {
            var table = $(this).find('[grupo="table_modal_llamadas"]');
            var identificador = $(table).attr('identificador');
            var la_categoria = categoria;  // var para este scope
            $(this).one('shown.bs.modal', function () {
                var logs = distribuciones[la_categoria][identificador];
                generarDataTableCallDetails(table, 'table_modal_llamadas', logs);
            });
        });
    }
}

function prepararTablasAtendidasPorAgente() {
    $('[grupo="table_modal_llamadas_de_agente"]').each(function(i, table) {
        var identificador = $(table).attr('identificador');
        $('#modal_atendidas_' + identificador).one('shown.bs.modal', function () {
            var logs = atendidas_por_agente[identificador];
            generarDataTableCallDetails(table, 'table_modal_llamadas_de_agente', logs);
        });
    });
}


function generarDataTableCallDetails(table, table_type, ids_list) {
    if ($(table).find('[empty_table]').length > 0)
        return;
    if (ids_list.length == 0)
        return;

    var url = Urls.api_premium_call_details();
    $(table).DataTable({
        serverSide: true,
        bFilter: false,
        ajax: {
            url: url,
            data: function ( d ) {
                var segment = ids_list.slice(d.start, d.start + d.length);
                d.ids = segment.join('-');
                d.table = table_type;
                delete(d.columns);
                delete(d.order);
                delete(d.search);
                delete(d.start);
                delete(d.length);
            },
            dataFilter: function(data){
                var json = jQuery.parseJSON( data );
                json.recordsTotal = ids_list.length;
                json.recordsFiltered = ids_list.length;
                return JSON.stringify( json ); // return JSON string
            }
        },
        columns: COLUMNAS_POR_TIPO[table_type],
        language: {
            paginate: {
                first: gettext('Primero'),
                previous: gettext('Anterior'),
                next: gettext('Siguiente'),
                last: gettext('Último')
            },
            lengthMenu: gettext('Mostrar _MENU_ entradas'),
            info: gettext('Mostrando _START_ a _END_ de _TOTAL_ entradas'),
            emptyTable: gettext('Sin datos disponibles'),
        }
    });
    generarBotonDescargaCSV(table, table_type, ids_list);
}

function generarBotonDescargaCSV(table, table_type, ids_list) {
    var $link = $('<a id="sasasa" class="btn btn-outline-primary" href="javascript:void(0)">\
' + gettext('Descargar CSV') + '</a>');
    $link.click(function() {
        descargarCSV(table_type, ids_list);
    });
    $(table).parent().parent().append($link);
}

function descargarCSV(table_type, ids_list) {
    $('#csv_logs_ids').val(ids_list);
    $('#csv_table').val(table_type);
    $('#download_csv_form').submit();
}

function getAudioHTML( data, type, row, meta ) {
    if (data == '')
        return '';
    return '\
<audio controls><source src="' + data + '" type="audio/mpeg">' + gettext('Escuchar') + '\
</audio>\
<a href="' + data + '" target="_blank">\
  <span class="glyphicon glyphicon-download-alt" aria-hidden="true" \
    title="' + gettext('Descargar') +'">\
  </span>\
</a>';
}

var COLUMNAS_POR_TIPO = {
    table_llamadas_atendidas: [
        {'data': 'fecha'},
        {'data': 'telefono'},
        {'data': 'campana_id'},
        {'data': 'nombre_campana'},
        {'data': 'tipo'},
        {'data': 'agente_id'},
        {'data': 'nombre_agente'},
        {'data': 'user_agente'},
        {'data': 't_espera'},
        {'data': 'duracion'},
        {'data': 'causa_desconexion'},
        {'data': 'id_calificacion'},
        {'data': 'nombre_calificacion'},
        {'data': 'grabacion', 'render': getAudioHTML, },
    ],
    table_llamadas_no_atendidas: [
        {'data': 'fecha'},
        {'data': 'telefono'},
        {'data': 'campana_id'},
        {'data': 'nombre_campana'},
        {'data': 'tipo'},
        {'data': 'agente_id'},
        {'data': 'nombre_agente'},
        {'data': 'user_agente'},
        {'data': 't_espera'},
        {'data': 'causa_desconexion'},
        {'data': 'id_calificacion'},
        {'data': 'nombre_calificacion'},
    ],
    table_modal_llamadas: [
        {'data': 'fecha'},
        {'data': 'telefono'},
        {'data': 'campana_id'},
        {'data': 'nombre_campana'},
        {'data': 'tipo'},
        {'data': 'agente_id'},
        {'data': 'nombre_agente'},
        {'data': 'user_agente'},
        {'data': 't_espera'},
        {'data': 'duracion'},
        {'data': 'causa_desconexion'},
        {'data': 'nombre_calificacion'},
        {'data': 'grabacion', 'render': getAudioHTML, },
    ],
    table_modal_llamadas_de_agente: [
        {'data': 'fecha'},
        {'data': 'telefono'},
        {'data': 'campana_id'},
        {'data': 'nombre_campana'},
        {'data': 'causa_desconexion'},
        {'data': 'duracion'},
        {'data': 'id_calificacion'},
        {'data': 'nombre_calificacion'},
        {'data': 'grabacion', 'render': getAudioHTML, },
    ]
};
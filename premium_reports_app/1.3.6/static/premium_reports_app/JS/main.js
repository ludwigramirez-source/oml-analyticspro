// Copyright (C) 2018 Freetech Solutions


/* global REMOVER_CAMPO */
/* global AGREGAR_VALIDACION */

var languageCode = $('#languageCode').val();

function mostrarFiltroConexion(
    valorTipoConexion, $filtroExitosas, $filtroFallidas, $filtroDuracionLlamada,
    $filtroCalificacionLlamada) {
    if (valorTipoConexion == 0) {
        // TODAS las llamadas
        $filtroExitosas.attr('class', 'hidden');
        $filtroFallidas.attr('class', 'hidden');
        $filtroDuracionLlamada.attr('class', 'hidden');
        $filtroCalificacionLlamada.attr('class', 'hidden');
    }
    else {
        if (valorTipoConexion == 1) {
            // TODAS las exitosas
            $filtroExitosas.attr('class', '');
            $filtroFallidas.attr('class', 'hidden');
            $filtroDuracionLlamada.attr('class', '');
            $filtroCalificacionLlamada.attr('class', '');
        }
        else {
            // TODAS las fallidas
            $filtroExitosas.attr('class', 'hidden');
            $filtroFallidas.attr('class', '');
            $filtroDuracionLlamada.attr('class', 'hidden');
            $filtroCalificacionLlamada.attr('class', 'hidden');
        }
    }
}


function bindingsFiltrosFinalizacionLlamada() {
    var $filtroTipoConexion = $('#filtroTipoConexion select');
    var $filtroExitosas = $('#filtroExitosas');
    var $filtroFallidas = $('#filtroFallidas');
    var $filtroDuracionLlamada = $('#filtroDuracionLlamada');
    var $filtroCalificacionLlamada = $('#filtroCalificacionLlamada');
    $filtroTipoConexion.change(function () {
        var valorTipoConexion = $(this).children('option:selected').val();
        mostrarFiltroConexion(valorTipoConexion, $filtroExitosas, $filtroFallidas,
            $filtroDuracionLlamada, $filtroCalificacionLlamada);
    });
    mostrarFiltroConexion(
        $filtroTipoConexion.val(), $filtroExitosas, $filtroFallidas,
        $filtroDuracionLlamada, $filtroCalificacionLlamada);
}


function adicionarEstiloDiasSemana() {
    $('#id_dia_semana').attr('class', 'list-group');
}

function adicionarDatePicker() {
    var fechaInicio = $('#id_fecha_inicio').val();
    var fechaFinal = $('#id_fecha_fin').val();
    $('#id_fecha_inicio').datetimepicker({format: 'L', locale: languageCode});
    $('#id_fecha_fin').datetimepicker({format: 'L', locale: languageCode});
    if (fechaInicio != '' && fechaFinal != '') {
    /* si los entradas de fecha tenían valor se los restituimos */
        $('#id_fecha_inicio').val(fechaInicio);
        $('#id_fecha_fin').val(fechaFinal);
    }
}

function bindingsFiltrosCampanas() {
    // de acuerdo al filtro escogido en el tipo de campaña
    // muestra la lista de campañas corrrespondiente para escoger
    var $filtroCampanas = $('#filtroCampanas').find('select');
    $('#filtroTiposCampanas').change(function () {
        var $filtroTipoCampana = $(this).find('select');
        var valorTipoCampana = $filtroTipoCampana.val();
        $.ajax({
            url: Urls.api_campanas_tipo(valorTipoCampana),
            type: 'GET',
            success: function(data){
                // fill filtroAgentes con data
                $filtroCampanas.empty();
                if (data.status != 'ERROR') {
                    $.each(data, function () {
                        $filtroCampanas.append($('<option></option>').val(this[1]).html(this[0]));
                    });
                }
            }
        });
    });
}


function bindingsFiltrosAgentes() {
    // de acuerdo al filtro escogido como grupos de agentes
    // muestra la lista de agentes corrrespondiente para escoger
    var $filtroAgentes = $('#filtroAgentes').find('select');
    $('#filtroGruposAgentes').change(function () {
        var $filtroGruposAgentes = $(this).find('select');
        var valorGrupoAgente = $filtroGruposAgentes.val();
        $.ajax({
            url: Urls.api_grupo_agentes(),
            type: 'POST',
            data:{'grupos': valorGrupoAgente},
            success: function(data){
                // fill filtroAgentes con data
                $filtroAgentes.empty();
                if (data.status != 'ERROR') {
                    $.each(data, function () {
                        $filtroAgentes.append($('<option></option>').val(this[1]).html(this[0]));
                    });
                }
            }
        });
    });
}


$(function() {
    $('.tiempo').datetimepicker({format: 'HH:mm'});
    adicionarDatePicker();
    adicionarEstiloDiasSemana();
    bindingsFiltrosFinalizacionLlamada();
    bindingsFiltrosCampanas();
    bindingsFiltrosAgentes();
});
var validacionTiempo = $('#validaciontiempo').val();
$('.validacionTiempoTr').formset({
    addText: AGREGAR_VALIDACION,
    deleteText: REMOVER_CAMPO,
    prefix: validacionTiempo,
    addCssClass: 'btn btn-outline-primary',
    deleteCssClass: 'btn btn-outline-danger deleteFormset',
    formCssClass: 'dynamic-formset',
    added: function (row) {
        $(row.find('.tiempo')).each(function (index) {
            $(this).datetimepicker({format: 'HH:mm', locale: languageCode});
            if (index == 0) {
                $(this).val('9:00');
            }
            else {
                $(this).val('18:00');
            }
        });
    }
});

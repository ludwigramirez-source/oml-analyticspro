// Copyright (C) 2018 Freetech Solutions

var main_tabs = ['distribucion', 'atendidas', 'noAtendidas', 'reportesAgentes'];
var distribucion_tabs = ['general', 'distribucion_general', 'salientes'];
var atendidas_tabs = ['llamada_general', 'detalle_llamada', 'nivel_servicio', 'llamadas_atendidas', 'causas_desconexion'];
var no_atendidas_tabs = ['no_atendidas_general', 'detalle_no_atendidas', 'llamadas_sin_conexion', 'causas_no_conexion'];
var reporte_agentes_tabs = ['sesiones', 'disponibilidad', 'numero_agentes'];

var reporte_premium =[main_tabs, distribucion_tabs, atendidas_tabs, no_atendidas_tabs, reporte_agentes_tabs];

$(function() {
    reporte_premium.forEach(function(id_reporte){
        id_reporte.forEach(function(id_tab){
            $('#' + id_tab).click(function() {
                seleccionar_tab(id_reporte, id_tab);
            });
        });
    });
});

function seleccionar_tab(tabs_ids, id_tab){
    tabs_ids.forEach(function(other_tab){
        if (other_tab == id_tab){
            $('#' + id_tab).addClass('active');
            $('#content_' + id_tab).show();
        }
        else{
            $('#' + other_tab).removeClass('active');
            $('#content_' + other_tab).hide();
        }
    });
}

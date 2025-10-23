// Copyright (C) 2018 Freetech Solutions

var dist = ['por_campana', 'por_rango_horario', 'por_mes', 'por_semana', 'por_dia', 'por_horario'];
var saliente = ['campana', 'rango_horario', 'mes', 'semana', 'dia', 'horario'];
var distribucion = [dist, saliente];

$(function(){
    distribucion.forEach(function(id_dist){
        id_dist.forEach(function(id_menu){
            $('#' + id_menu).click(function(){
                seleccionar_menu(id_dist, id_menu);
            });
        });
    });
});

function seleccionar_menu (dist_ids, id_menu){
    dist_ids.forEach(function(other_id){
        if (other_id == id_menu){
            $('#' + id_menu).removeClass('btn-outline-primary');
            $('#' + id_menu).addClass('btn-primary');
            $('#content_' + id_menu).show();
        }
        else{
            $('#' + other_id).addClass('btn-outline-primary');
            $('#' + other_id).removeClass('btn-primary');
            $('#content_' + other_id).hide();
        }
        
    });
}
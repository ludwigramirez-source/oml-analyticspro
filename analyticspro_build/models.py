"""
Modelos managed=False que mapean las tablas espejo en omnileads_local.
NO se generan migraciones para estos modelos.
"""
from django.db import models


class LlamadaLog(models.Model):
    """reportes_app_llamadalog"""
    time = models.DateTimeField()
    callid = models.CharField(max_length=200)
    campana_id = models.IntegerField(null=True)
    tipo_campana = models.IntegerField(null=True)
    tipo_llamada = models.IntegerField()
    agente_id = models.IntegerField(null=True)
    event = models.CharField(max_length=32)
    numero_marcado = models.CharField(max_length=128, null=True)
    contacto_id = models.IntegerField(null=True)
    bridge_wait_time = models.IntegerField(null=True)
    duracion_llamada = models.IntegerField(null=True)
    archivo_grabacion = models.CharField(max_length=100, null=True)
    agente_extra_id = models.IntegerField(null=True)
    campana_extra_id = models.IntegerField(null=True)
    numero_extra = models.CharField(max_length=20, null=True)

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'reportes_app_llamadalog'


class ActividadAgenteLog(models.Model):
    """reportes_app_actividadagentelog"""
    time = models.DateTimeField()
    agente_id = models.IntegerField()
    event = models.CharField(max_length=50)
    pausa_id = models.IntegerField(null=True)

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'reportes_app_actividadagentelog'


class Campana(models.Model):
    """ominicontacto_app_campana"""
    nombre = models.CharField(max_length=128)
    type = models.IntegerField()
    estado = models.IntegerField()
    fecha_inicio = models.DateField(null=True)
    fecha_fin = models.DateField(null=True)
    oculto = models.BooleanField(default=False)
    es_template = models.BooleanField(default=False)

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'ominicontacto_app_campana'


class AgenteProfile(models.Model):
    """ominicontacto_app_agenteprofile"""
    sip_extension = models.CharField(max_length=40, null=True)
    estado = models.CharField(max_length=50)
    is_inactive = models.BooleanField(default=False)
    borrado = models.BooleanField(default=False)
    grupo_id = models.IntegerField(null=True)
    user_id = models.IntegerField()

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'ominicontacto_app_agenteprofile'


class OMLUser(models.Model):
    """ominicontacto_app_user"""
    password = models.CharField(max_length=128)
    username = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_active = models.BooleanField()

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'ominicontacto_app_user'


class Pausa(models.Model):
    """ominicontacto_app_pausa"""
    nombre = models.CharField(max_length=20)
    tipo = models.CharField(max_length=1)   # P=Productiva R=Recreativa
    eliminada = models.BooleanField(default=False)

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'ominicontacto_app_pausa'


class SyncMetadata(models.Model):
    """Tabla de control de sincronizacion"""
    table_name = models.CharField(max_length=100, primary_key=True)
    last_synced_id = models.BigIntegerField(default=0)
    last_sync_time = models.DateTimeField(null=True)
    sync_status = models.CharField(max_length=20, default='pending')
    rows_synced = models.BigIntegerField(default=0)
    rows_total = models.BigIntegerField(default=0)
    error_message = models.TextField(null=True)
    sync_duration_s = models.FloatField(null=True)

    class Meta:
        app_label = 'analyticspro'
        managed = False
        db_table = 'sync_metadata'

"""
Modelos SQLAlchemy para tablas de OmniLeads (READ-ONLY)
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class LlamadaLog(Base):
    """Modelo para reportes_app_llamadalog"""
    __tablename__ = 'reportes_app_llamadalog'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    time = Column(DateTime(timezone=True), nullable=False)
    callid = Column(String(32))
    campana_id = Column(Integer)
    tipo_campana = Column(Integer)
    tipo_llamada = Column(Integer)
    agente_id = Column(Integer)
    event = Column(String(32))
    numero_marcado = Column(String(128))
    contacto_id = Column(Integer)
    bridge_wait_time = Column(Integer)
    duracion_llamada = Column(Integer)
    archivo_grabacion = Column(String(100))
    agente_extra_id = Column(Integer)
    campana_extra_id = Column(Integer)
    numero_extra = Column(String(128))


class ActividadAgenteLog(Base):
    """Modelo para reportes_app_actividadagentelog"""
    __tablename__ = 'reportes_app_actividadagentelog'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    time = Column(DateTime(timezone=True), nullable=False)
    agente_id = Column(Integer)
    event = Column(String(32))
    pausa_id = Column(String(128))


class Campana(Base):
    """Modelo para ominicontacto_app_campana"""
    __tablename__ = 'ominicontacto_app_campana'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    estado = Column(Integer, nullable=False)
    nombre = Column(String(128), nullable=False)
    fecha_inicio = Column(Date)
    fecha_fin = Column(Date)
    oculto = Column(Boolean, nullable=False)
    campaign_id_wombat = Column(Integer)
    type = Column(Integer, nullable=False)
    tipo_interaccion = Column(Integer, nullable=False)
    es_template = Column(Boolean, nullable=False)
    nombre_template = Column(String(128))
    es_manual = Column(Boolean, nullable=False)
    objetivo = Column(Integer, nullable=False)
    tiempo_desconexion = Column(Integer, nullable=False)
    bd_contacto_id = Column(Integer)
    reported_by_id = Column(Integer, nullable=False)
    sitio_externo_id = Column(Integer)
    mostrar_nombre = Column(Boolean, nullable=False)
    id_externo = Column(String(128))
    sistema_externo_id = Column(Integer)
    campo_desactivacion = Column(String(128))
    campos_bd_no_editables = Column(String(2052), nullable=False)
    campos_bd_ocultos = Column(String(2052), nullable=False)
    outcid = Column(String(128))
    outr_id = Column(Integer)
    videocall_habilitada = Column(Boolean, nullable=False)
    speech = Column(Text)
    campo_direccion = Column(String(128))
    mostrar_did = Column(Boolean, nullable=False)
    mostrar_nombre_ruta_entrante = Column(Boolean, nullable=False)
    control_de_duplicados = Column(Integer, nullable=False)
    prioridad = Column(Integer, nullable=False)
    campos_bd_obligatorios = Column(String(2052), nullable=False)


class AgenteProfile(Base):
    """Modelo para ominicontacto_app_agenteprofile"""
    __tablename__ = 'ominicontacto_app_agenteprofile'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    sip_extension = Column(Integer, nullable=False)
    sip_password = Column(String(128))
    estado = Column(Integer, nullable=False)
    is_inactive = Column(Boolean, nullable=False)
    borrado = Column(Boolean, nullable=False)
    grupo_id = Column(Integer, nullable=False)
    reported_by_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)


class Pausa(Base):
    """Modelo para ominicontacto_app_pausa"""
    __tablename__ = 'ominicontacto_app_pausa'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    nombre = Column(String(20), nullable=False)
    tipo = Column(String(1), nullable=False)  # P=Productiva, R=Recreativa
    eliminada = Column(Boolean, nullable=False)


class User(Base):
    """Modelo para ominicontacto_app_user (Django users)"""
    __tablename__ = 'ominicontacto_app_user'
    __table_args__ = {'schema': 'public'}
    
    id = Column(Integer, primary_key=True)
    password = Column(String(128), nullable=False)
    last_login = Column(DateTime(timezone=True))
    is_superuser = Column(Boolean, nullable=False)
    username = Column(String(150), nullable=False, unique=True)
    first_name = Column(String(150), nullable=False)
    last_name = Column(String(150), nullable=False)
    email = Column(String(254), nullable=False)
    is_staff = Column(Boolean, nullable=False)
    is_active = Column(Boolean, nullable=False)
    date_joined = Column(DateTime(timezone=True), nullable=False)

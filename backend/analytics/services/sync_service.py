"""
Servicio de sincronización de datos desde PostgreSQL a MongoDB local
Trae solo los datos faltantes para optimizar rendimiento
"""
from datetime import datetime, timezone
from typing import Dict, Optional
from sqlalchemy.orm import Session
from motor.motor_asyncio import AsyncIOMotorDatabase
import os
import logging

from ..models.omnileads_models import (
    Campana, AgenteProfile, User, ActividadAgenteLog, 
    LlamadaLog, Pausa
)

logger = logging.getLogger(__name__)


class SyncService:
    """Servicio de sincronización inteligente"""
    
    def __init__(self, pg_session: Session, mongo_db: AsyncIOMotorDatabase):
        self.pg = pg_session
        self.mongo = mongo_db
    
    async def sync_for_agentes_report(self, fecha_inicio: datetime, fecha_fin: datetime):
        """
        Sincroniza solo los datos necesarios para el reporte de agentes
        en el rango de fechas especificado
        """
        logger.info(f"🔄 Iniciando sincronización para rango: {fecha_inicio} - {fecha_fin}")
        
        # 1. Sincronizar campañas (siempre, son pocas)
        await self._sync_campanas()
        
        # 2. Sincronizar tipos de pausa (siempre, son pocas)
        await self._sync_pausas()
        
        # 3. Sincronizar agentes (siempre, son pocos)
        await self._sync_agentes()
        
        # 4. Sincronizar actividades de agentes (solo rango faltante)
        await self._sync_actividades_agentes(fecha_inicio, fecha_fin)
        
        # 5. Sincronizar llamadas con agente (solo rango faltante)
        await self._sync_llamadas_agentes(fecha_inicio, fecha_fin)
        
        logger.info("✅ Sincronización completada")
    
    async def _sync_campanas(self):
        """Sincroniza todas las campañas (son pocas)"""
        try:
            # Obtener campañas de PostgreSQL
            campanas = self.pg.query(Campana).all()
            
            if not campanas:
                return
            
            # Preparar documentos para MongoDB
            docs = []
            for c in campanas:
                docs.append({
                    'id': c.id,
                    'nombre': c.nombre,
                    'tipo': c.type,
                    'estado': c.estado,
                    'sincronizado_at': datetime.utcnow()
                })
            
            # Upsert en MongoDB (actualizar o insertar)
            for doc in docs:
                await self.mongo.campanas_local.update_one(
                    {'id': doc['id']},
                    {'$set': doc},
                    upsert=True
                )
            
            logger.info(f"✅ Sincronizadas {len(docs)} campañas")
        except Exception as e:
            logger.error(f"❌ Error sincronizando campañas: {e}")
    
    async def _sync_pausas(self):
        """Sincroniza tipos de pausa"""
        try:
            pausas = self.pg.query(Pausa).all()
            
            if not pausas:
                return
            
            docs = []
            for p in pausas:
                docs.append({
                    'id': p.id,
                    'nombre': p.nombre,
                    'tipo': p.tipo,
                    'sincronizado_at': datetime.utcnow()
                })
            
            for doc in docs:
                await self.mongo.pausas_local.update_one(
                    {'id': doc['id']},
                    {'$set': doc},
                    upsert=True
                )
            
            logger.info(f"✅ Sincronizadas {len(docs)} pausas")
        except Exception as e:
            logger.error(f"❌ Error sincronizando pausas: {e}")
    
    async def _sync_agentes(self):
        """Sincroniza agentes"""
        try:
            agentes = self.pg.query(
                AgenteProfile.id,
                AgenteProfile.user_id,
                User.username,
                User.first_name,
                User.last_name
            ).join(
                User, AgenteProfile.user_id == User.id
            ).filter(
                AgenteProfile.borrado == False
            ).all()
            
            if not agentes:
                return
            
            docs = []
            for a in agentes:
                docs.append({
                    'id': a.id,
                    'user_id': a.user_id,
                    'username': a.username,
                    'first_name': a.first_name,
                    'last_name': a.last_name,
                    'sincronizado_at': datetime.utcnow()
                })
            
            for doc in docs:
                await self.mongo.agentes_local.update_one(
                    {'id': doc['id']},
                    {'$set': doc},
                    upsert=True
                )
            
            logger.info(f"✅ Sincronizados {len(docs)} agentes")
        except Exception as e:
            logger.error(f"❌ Error sincronizando agentes: {e}")
    
    async def _sync_actividades_agentes(self, fecha_inicio: datetime, fecha_fin: datetime):
        """Sincroniza actividades de agentes solo para el rango que falta"""
        try:
            # Verificar qué ya tenemos en MongoDB
            count_existentes = await self.mongo.actividades_agente_local.count_documents({
                'time': {'$gte': fecha_inicio, '$lte': fecha_fin}
            })
            
            # Obtener de PostgreSQL
            actividades = self.pg.query(ActividadAgenteLog).filter(
                ActividadAgenteLog.time >= fecha_inicio,
                ActividadAgenteLog.time <= fecha_fin
            ).all()
            
            if not actividades:
                logger.info("ℹ️ No hay actividades nuevas para sincronizar")
                return
            
            # Si ya tenemos datos, solo insertar los que faltan
            if count_existentes > 0:
                # Obtener IDs existentes
                existing_ids = set()
                async for doc in self.mongo.actividades_agente_local.find(
                    {'time': {'$gte': fecha_inicio, '$lte': fecha_fin}},
                    {'id': 1}
                ):
                    existing_ids.add(doc['id'])
                
                # Filtrar solo los nuevos
                actividades = [a for a in actividades if a.id not in existing_ids]
            
            if not actividades:
                logger.info("ℹ️ Todas las actividades ya están sincronizadas")
                return
            
            # Insertar en lotes
            docs = []
            for act in actividades:
                docs.append({
                    'id': act.id,
                    'agente_id': act.agente_id,
                    'time': act.time,
                    'event': act.event,
                    'pausa_id': act.pausa_id,
                    'sincronizado_at': datetime.utcnow()
                })
            
            if docs:
                await self.mongo.actividades_agente_local.insert_many(docs, ordered=False)
                logger.info(f"✅ Sincronizadas {len(docs)} actividades de agentes")
        except Exception as e:
            logger.error(f"❌ Error sincronizando actividades: {e}")
    
    async def _sync_llamadas_agentes(self, fecha_inicio: datetime, fecha_fin: datetime):
        """Sincroniza llamadas que tienen agente asignado"""
        try:
            # Verificar qué ya tenemos
            count_existentes = await self.mongo.llamadas_local.count_documents({
                'time': {'$gte': fecha_inicio, '$lte': fecha_fin}
            })
            
            # Obtener de PostgreSQL (solo llamadas con agente)
            llamadas = self.pg.query(LlamadaLog).filter(
                LlamadaLog.time >= fecha_inicio,
                LlamadaLog.time <= fecha_fin,
                LlamadaLog.agente_id.isnot(None)
            ).all()
            
            if not llamadas:
                logger.info("ℹ️ No hay llamadas nuevas para sincronizar")
                return
            
            # Si ya tenemos datos, filtrar solo los nuevos
            if count_existentes > 0:
                existing_ids = set()
                async for doc in self.mongo.llamadas_local.find(
                    {'time': {'$gte': fecha_inicio, '$lte': fecha_fin}},
                    {'id': 1}
                ):
                    existing_ids.add(doc['id'])
                
                llamadas = [ll for ll in llamadas if ll.id not in existing_ids]
            
            if not llamadas:
                logger.info("ℹ️ Todas las llamadas ya están sincronizadas")
                return
            
            # Insertar en lotes
            docs = []
            for ll in llamadas:
                docs.append({
                    'id': ll.id,
                    'callid': ll.callid,
                    'time': ll.time,
                    'agente_id': ll.agente_id,
                    'campana_id': ll.campana_id,
                    'event': ll.event,
                    'duracion_llamada': ll.duracion_llamada,
                    'bridge_wait_time': ll.bridge_wait_time,
                    'tipo_llamada': ll.tipo_llamada,
                    'sincronizado_at': datetime.utcnow()
                })
            
            if docs:
                await self.mongo.llamadas_local.insert_many(docs, ordered=False)
                logger.info(f"✅ Sincronizadas {len(docs)} llamadas")
        except Exception as e:
            logger.error(f"❌ Error sincronizando llamadas: {e}")
    
    async def create_indexes(self):
        """Crea índices en MongoDB para consultas rápidas"""
        try:
            # Índices para actividades
            await self.mongo.actividades_agente_local.create_index([('agente_id', 1), ('time', 1)])
            await self.mongo.actividades_agente_local.create_index([('time', 1)])
            
            # Índices para llamadas
            await self.mongo.llamadas_local.create_index([('agente_id', 1), ('time', 1)])
            await self.mongo.llamadas_local.create_index([('callid', 1), ('time', 1)])
            await self.mongo.llamadas_local.create_index([('time', 1)])
            
            # Índices para búsqueda rápida
            await self.mongo.agentes_local.create_index([('id', 1)])
            await self.mongo.campanas_local.create_index([('id', 1)])
            await self.mongo.pausas_local.create_index([('id', 1)])
            
            logger.info("✅ Índices creados en MongoDB")
        except Exception as e:
            logger.error(f"❌ Error creando índices: {e}")

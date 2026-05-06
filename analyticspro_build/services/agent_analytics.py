"""
Servicio de analytics de agentes.
Port de agent_analytics.py (SQLAlchemy) a SQL crudo (Django connections).
"""
from analyticspro.services.base import AnalyticsBaseService
from analyticspro.constants import EVENTOS_ATENDIDAS


class AgentAnalyticsService(AnalyticsBaseService):

    # ─────────────────────────────────────────────────────────────
    # Rendimiento por agente
    # ─────────────────────────────────────────────────────────────

    def get_rendimiento(self, filters=None):
        filters = filters or {}
        tz = self.TZ_DB
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph, ab_params = self._events_placeholder(self.EVENTOS_ABANDONADAS)

        f_clauses, f_params = self._filters_sql(filters)
        fin_clauses = [f'l.event IN ({fin_ph})'] + f_clauses
        where_fin = self._where(fin_clauses)

        with self.cursor() as cur:
            sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT
                l.agente_id,
                u.first_name || ' ' || u.last_name AS agente_nombre,
                ap.sip_extension AS extension,
                COUNT(*) AS total_llamadas,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada ELSE 0 END), 0) AS tiempo_total,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_agenteprofile ap ON ap.id = l.agente_id
            LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
            WHERE l.agente_id IS NOT NULL
            GROUP BY l.agente_id, u.first_name, u.last_name, ap.sip_extension
            ORDER BY atendidas DESC
            """
            params = fin_params + f_params + at_params + ab_params + at_params * 3
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            total = r.get('total_llamadas', 0) or 0
            atendidas = r.get('atendidas', 0) or 0
            r['tasa_atencion'] = round(atendidas / total * 100, 2) if total > 0 else 0
            r['tiempo_total'] = int(r.get('tiempo_total', 0) or 0)

        return rows

    def export_rendimiento_excel(self, filters=None):
        """Exporta rendimiento de agentes a Excel."""
        import openpyxl
        from io import BytesIO

        rows = self.get_rendimiento(filters)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Rendimiento Agentes'
        headers = ['ID', 'Nombre', 'Extensión', 'Total', 'Atendidas',
                   'Abandonadas', 'TMO (s)', 'Tiempo Total (s)',
                   'Espera Prom (s)', 'Tasa Atención %']
        keys = ['agente_id', 'agente_nombre', 'extension', 'total_llamadas',
                'atendidas', 'abandonadas', 'tmo_prom', 'tiempo_total',
                'espera_prom', 'tasa_atencion']
        ws.append(headers)
        for row in rows:
            ws.append([row.get(k) for k in keys])

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    # ─────────────────────────────────────────────────────────────
    # Disponibilidad (sesiones y pausas)
    # ─────────────────────────────────────────────────────────────

    def get_disponibilidad(self, filters=None):
        """Tiempo de sesión, pausas y disponibilidad por agente."""
        filters = filters or {}
        tz = self.TZ_DB

        f_clauses = []
        f_params = []
        if filters.get('fecha_inicio'):
            f_clauses.append('a.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('a.time <= %s')
            f_params.append(filters['fecha_fin'])
        if filters.get('agente_ids'):
            ids = filters['agente_ids']
            f_clauses.append(f"a.agente_id IN ({','.join(['%s']*len(ids))})")
            f_params.extend(ids)
        elif filters.get('agente_id'):
            f_clauses.append('a.agente_id = %s')
            f_params.append(filters['agente_id'])

        where_act = self._where(f_clauses) if f_clauses else ''

        with self.cursor() as cur:
            cur.execute(f"""
                SELECT
                    a.agente_id,
                    u.first_name || ' ' || u.last_name AS nombre,
                    a.event,
                    a.time,
                    a.pausa_id,
                    p.tipo AS pausa_tipo
                FROM reportes_app_actividadagentelog a
                LEFT JOIN ominicontacto_app_agenteprofile ap ON ap.id = a.agente_id
                LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
                LEFT JOIN ominicontacto_app_pausa p ON p.id::TEXT = a.pausa_id
                {where_act}
                ORDER BY a.agente_id, a.time
            """, f_params)
            actividades = self.fetchall_dict(cur)

        # Agrupar por agente y calcular tiempos
        agentes = {}
        for act in actividades:
            aid = act['agente_id']
            if aid not in agentes:
                agentes[aid] = {
                    'agente_id': aid,
                    'nombre': act.get('nombre', ''),
                    'actividades': []
                }
            agentes[aid]['actividades'].append(act)

        resultado = []
        for aid, data in agentes.items():
            acts = data['actividades']
            tiempo_sesion = 0
            tiempo_pausa_prod = 0
            tiempo_pausa_rec = 0
            tiempo_login = None
            tiempo_pausa_inicio = None
            pausa_tipo_actual = None

            for act in acts:
                ev = act['event']
                t = act['time']
                if ev == 'ADDMEMBER':
                    tiempo_login = t
                elif ev == 'REMOVEMEMBER' and tiempo_login:
                    tiempo_sesion += (t - tiempo_login).total_seconds()
                    tiempo_login = None
                elif ev == 'PAUSEALL':
                    tiempo_pausa_inicio = t
                    pausa_tipo_actual = act.get('pausa_tipo', 'R')
                elif ev == 'UNPAUSEALL' and tiempo_pausa_inicio:
                    dur = (t - tiempo_pausa_inicio).total_seconds()
                    if pausa_tipo_actual == 'P':
                        tiempo_pausa_prod += dur
                    else:
                        tiempo_pausa_rec += dur
                    tiempo_pausa_inicio = None

            tiempo_productivo = tiempo_sesion - tiempo_pausa_rec
            resultado.append({
                'agente_id': aid,
                'agente_nombre': data['nombre'],
                'tiempo_sesion_s': int(tiempo_sesion),
                'tiempo_pausa_productiva_s': int(tiempo_pausa_prod),
                'tiempo_pausa_recreativa_s': int(tiempo_pausa_rec),
                'tiempo_productivo_s': int(max(0, tiempo_productivo)),
                'disponibilidad_pct': round(
                    tiempo_productivo / tiempo_sesion * 100, 2
                ) if tiempo_sesion > 0 else 0,
            })

        return sorted(resultado, key=lambda x: x['tiempo_sesion_s'], reverse=True)

    # ─────────────────────────────────────────────────────────────
    # Sesiones de un agente
    # ─────────────────────────────────────────────────────────────

    def get_sesiones_agente(self, agente_id, filters=None):
        filters = filters or {}
        tz = self.TZ_DB

        f_clauses = ['a.agente_id = %s']
        f_params = [agente_id]
        if filters.get('fecha_inicio'):
            f_clauses.append('a.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('a.time <= %s')
            f_params.append(filters['fecha_fin'])

        where = self._where(f_clauses)

        with self.cursor() as cur:
            cur.execute(f"""
                SELECT a.event, a.time, a.pausa_id,
                       (a.time AT TIME ZONE '{tz}') AS time_local
                FROM reportes_app_actividadagentelog a
                {where}
                AND a.event IN ('ADDMEMBER', 'REMOVEMEMBER')
                ORDER BY a.time
            """, f_params)
            acts = self.fetchall_dict(cur)

        sesiones = []
        login_time = None
        for act in acts:
            if act['event'] == 'ADDMEMBER':
                login_time = act['time']
            elif act['event'] == 'REMOVEMEMBER' and login_time:
                dur = (act['time'] - login_time).total_seconds()
                sesiones.append({
                    'inicio': str(login_time),
                    'fin': str(act['time']),
                    'duracion_s': int(dur),
                })
                login_time = None
        return sesiones

    # ─────────────────────────────────────────────────────────────
    # Pausas de un agente
    # ─────────────────────────────────────────────────────────────

    def get_pausas_agente(self, agente_id, filters=None):
        filters = filters or {}
        tz = self.TZ_DB

        f_clauses = ['a.agente_id = %s']
        f_params = [agente_id]
        if filters.get('fecha_inicio'):
            f_clauses.append('a.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('a.time <= %s')
            f_params.append(filters['fecha_fin'])

        where = self._where(f_clauses)

        with self.cursor() as cur:
            cur.execute(f"""
                SELECT a.event, a.time, a.pausa_id, p.nombre AS pausa_nombre, p.tipo AS pausa_tipo
                FROM reportes_app_actividadagentelog a
                LEFT JOIN ominicontacto_app_pausa p ON p.id::TEXT = a.pausa_id
                {where}
                AND a.event IN ('PAUSEALL', 'UNPAUSEALL')
                ORDER BY a.time
            """, f_params)
            acts = self.fetchall_dict(cur)

        pausas = []
        pausa_inicio = None
        pausa_meta = {}
        for act in acts:
            if act['event'] == 'PAUSEALL':
                pausa_inicio = act['time']
                pausa_meta = {
                    'pausa_id': act['pausa_id'],
                    'nombre': act.get('pausa_nombre', 'Desconocida'),
                    'tipo': act.get('pausa_tipo', 'R'),
                }
            elif act['event'] == 'UNPAUSEALL' and pausa_inicio:
                dur = (act['time'] - pausa_inicio).total_seconds()
                pausas.append({
                    'inicio': str(pausa_inicio),
                    'fin': str(act['time']),
                    'duracion_s': int(dur),
                    **pausa_meta,
                })
                pausa_inicio = None

        return pausas

    # ─────────────────────────────────────────────────────────────
    # Timeline de un agente
    # ─────────────────────────────────────────────────────────────

    def get_timeline_agente(self, agente_id, filters=None):
        filters = filters or {}
        tz = self.TZ_DB

        f_clauses = ['a.agente_id = %s']
        f_params = [agente_id]
        if filters.get('fecha_inicio'):
            f_clauses.append('a.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('a.time <= %s')
            f_params.append(filters['fecha_fin'])

        where = self._where(f_clauses)

        with self.cursor() as cur:
            cur.execute(f"""
                SELECT
                    a.event,
                    a.time,
                    (a.time AT TIME ZONE '{tz}') AS time_local,
                    a.pausa_id,
                    p.nombre AS pausa_nombre,
                    p.tipo AS pausa_tipo
                FROM reportes_app_actividadagentelog a
                LEFT JOIN ominicontacto_app_pausa p ON p.id::TEXT = a.pausa_id
                {where}
                ORDER BY a.time
            """, f_params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            r['time'] = str(r['time'])
            r['time_local'] = str(r.get('time_local', ''))
        return rows

    # ─────────────────────────────────────────────────────────────
    # Heatmap de disponibilidad
    # ─────────────────────────────────────────────────────────────

    def get_disponibilidad_heatmap(self, filters=None):
        """Agentes conectados por hora del día (promedio)."""
        filters = filters or {}
        tz = self.TZ_DB

        f_clauses = []
        f_params = []
        if filters.get('fecha_inicio'):
            f_clauses.append('a.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('a.time <= %s')
            f_params.append(filters['fecha_fin'])

        where = self._where(f_clauses)

        with self.cursor() as cur:
            cur.execute(f"""
                SELECT
                    EXTRACT(HOUR FROM (a.time AT TIME ZONE '{tz}'))::int AS hora,
                    COUNT(DISTINCT a.agente_id) AS agentes_conectados
                FROM reportes_app_actividadagentelog a
                {where}
                AND a.event = 'ADDMEMBER'
                GROUP BY hora
                ORDER BY hora
            """, f_params)
            return self.fetchall_dict(cur)

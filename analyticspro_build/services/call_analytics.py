"""
Servicio principal de analytics de llamadas.
Port de call_analytics.py (FastAPI/SQLAlchemy) a SQL crudo (Django/psycopg2).
"""
from analyticspro.services.base import AnalyticsBaseService
from analyticspro.constants import EVENTOS_FINALES, TIPOS_LLAMADA_ACTIVOS


class CallAnalyticsService(AnalyticsBaseService):

    # ─────────────────────────────────────────────────────────────
    # KPIs principales
    # ─────────────────────────────────────────────────────────────

    def get_kpis(self, filters=None):
        filters = filters or {}
        tz = self.TZ_DB
        sla60 = self.SLA_THRESHOLD_60
        sla20 = self.SLA_THRESHOLD_20

        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph, ab_params = self._events_placeholder(self.EVENTOS_ABANDONADAS)
        na_ph, na_params = self._events_placeholder(self.EVENTOS_NO_ATENDIDAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)

        f_clauses, f_params = self._filters_sql(filters)
        where_base = self._where(f_clauses)

        # ── Último evento por callid (dentro de EVENTOS_FINALES) ──
        fin_clauses = list(f_clauses)
        fin_clauses.insert(0, f'l.event IN ({fin_ph})')
        where_fin = self._where(fin_clauses)

        with self.cursor() as cur:
            # Conteos atendidas / abandonadas / no_atendidas
            sql = f"""
            WITH last_ev AS (
                SELECT l.callid, MAX(l.id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY l.callid
            )
            SELECT
                COUNT(DISTINCT CASE WHEN l.event IN ({at_ph}) THEN l.callid END) AS atendidas,
                COUNT(DISTINCT CASE WHEN l.event IN ({ab_ph}) THEN l.callid END) AS abandonadas,
                COUNT(DISTINCT CASE WHEN l.event IN ({na_ph}) THEN l.callid END) AS no_atendidas,
                COUNT(DISTINCT l.callid) AS total_callids,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph})
                    AND l.bridge_wait_time IS NOT NULL
                    AND l.bridge_wait_time <= {sla60} THEN 1 ELSE 0 END), 0) AS sla60_count,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph})
                    AND l.bridge_wait_time IS NOT NULL
                    AND l.bridge_wait_time <= {sla20} THEN 1 ELSE 0 END), 0) AS sla20_count,
                COUNT(DISTINCT CASE WHEN l.event IN ({at_ph}) THEN l.agente_id END) AS agentes_activos,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada ELSE 0 END), 0) AS tiempo_total
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            """
            # params: fin_params + at + ab + na + at(tmo) + at(espera) + at(sla60) + at(sla20) + at(agentes) + at(tiempo)
            params = (
                fin_params + f_params        # WHERE for CTE
                + at_params + ab_params + na_params  # SELECT CASE WHEN events
                + at_params * 6              # 6 more at references in aggregates
            )
            cur.execute(sql, params)
            row = self.fetchone_dict(cur)

        atendidas = row.get('atendidas', 0) or 0
        abandonadas = row.get('abandonadas', 0) or 0
        no_atendidas = row.get('no_atendidas', 0) or 0
        total_callids = row.get('total_callids', 0) or 0
        tmo = row.get('tmo', 0) or 0
        espera_prom = row.get('espera_prom', 0) or 0
        sla60_count = row.get('sla60_count', 0) or 0
        sla20_count = row.get('sla20_count', 0) or 0
        agentes_activos = row.get('agentes_activos', 0) or 0
        tiempo_total = row.get('tiempo_total', 0) or 0

        clasificadas = atendidas + abandonadas + no_atendidas
        anomalias = max(0, total_callids - clasificadas)
        no_atendidas_total = abandonadas + no_atendidas

        sla_60 = round(sla60_count / atendidas * 100, 2) if atendidas > 0 else 0
        sla_20 = round(sla20_count / atendidas * 100, 2) if atendidas > 0 else 0
        nivel_atencion = round(atendidas / clasificadas * 100, 2) if clasificadas > 0 else 0
        tasa_abandono = round(abandonadas / clasificadas * 100, 2) if clasificadas > 0 else 0

        # Ocupacion: simplificada (tiempo total llamadas / no calculamos sesiones aqui)
        ocupacion = 0

        return {
            'total_llamadas': clasificadas,
            'llamadas_atendidas': atendidas,
            'llamadas_abandonadas': abandonadas,
            'llamadas_no_atendidas': no_atendidas_total,
            'llamadas_no_atendidas_otras': no_atendidas,
            'anomalias': anomalias,
            'tmo_promedio': tmo,
            'espera_promedio': espera_prom,
            'nivel_servicio_60': sla_60,
            'nivel_servicio_20': sla_20,
            'nivel_atencion': nivel_atencion,
            'tasa_abandono': tasa_abandono,
            'agentes_activos': agentes_activos,
            'ocupacion': ocupacion,
            'tiempo_total_llamadas': int(tiempo_total),
        }

    # ─────────────────────────────────────────────────────────────
    # Distribución por estado (atendida/abandonada/no atendida)
    # ─────────────────────────────────────────────────────────────

    def get_distribucion_llamadas(self, filters=None):
        filters = filters or {}
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph, ab_params = self._events_placeholder(self.EVENTOS_ABANDONADAS)
        na_ph, na_params = self._events_placeholder(self.EVENTOS_NO_ATENDIDAS)

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
                CASE
                    WHEN l.event IN ({at_ph}) THEN 'atendida'
                    WHEN l.event IN ({ab_ph}) THEN 'abandonada'
                    WHEN l.event IN ({na_ph}) THEN 'no_atendida'
                    ELSE 'otra'
                END AS estado,
                COUNT(*) AS cantidad
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            GROUP BY estado
            ORDER BY cantidad DESC
            """
            params = fin_params + f_params + at_params + ab_params + na_params
            cur.execute(sql, params)
            return self.fetchall_dict(cur)

    # ─────────────────────────────────────────────────────────────
    # Evolución por hora
    # ─────────────────────────────────────────────────────────────

    def get_evolucion_hora(self, filters=None):
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
                EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int AS hora,
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            GROUP BY hora
            ORDER BY hora
            """
            params = fin_params + f_params + at_params + ab_params + at_params
            cur.execute(sql, params)
            return self.fetchall_dict(cur)

    # ─────────────────────────────────────────────────────────────
    # Evolución diaria
    # ─────────────────────────────────────────────────────────────

    def get_evolucion_diaria(self, filters=None):
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
                DATE(l.time AT TIME ZONE '{tz}') AS fecha,
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            GROUP BY fecha
            ORDER BY fecha
            """
            params = fin_params + f_params + at_params + ab_params + at_params * 2
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)
            for r in rows:
                if r.get('fecha'):
                    r['fecha'] = str(r['fecha'])
            return rows

    # ─────────────────────────────────────────────────────────────
    # Nivel de servicio
    # ─────────────────────────────────────────────────────────────

    def get_nivel_servicio(self, filters=None):
        filters = filters or {}
        sla60 = self.SLA_THRESHOLD_60
        sla20 = self.SLA_THRESHOLD_20
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)

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
                COUNT(*) AS atendidas,
                SUM(CASE WHEN l.bridge_wait_time <= {sla60} THEN 1 ELSE 0 END) AS en_sla_60,
                SUM(CASE WHEN l.bridge_wait_time <= {sla20} THEN 1 ELSE 0 END) AS en_sla_20,
                COALESCE(AVG(l.bridge_wait_time), 0)::int AS espera_prom,
                COALESCE(MAX(l.bridge_wait_time), 0)::int AS espera_max,
                COALESCE(MIN(l.bridge_wait_time), 0)::int AS espera_min
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            WHERE l.event IN ({at_ph})
              AND l.bridge_wait_time IS NOT NULL
            """
            params = fin_params + f_params + at_params
            cur.execute(sql, params)
            row = self.fetchone_dict(cur)

        atendidas = row.get('atendidas', 0) or 0
        en_sla_60 = row.get('en_sla_60', 0) or 0
        en_sla_20 = row.get('en_sla_20', 0) or 0

        return {
            'atendidas': atendidas,
            'en_sla_60': en_sla_60,
            'en_sla_20': en_sla_20,
            'nivel_servicio_60': round(en_sla_60 / atendidas * 100, 2) if atendidas > 0 else 0,
            'nivel_servicio_20': round(en_sla_20 / atendidas * 100, 2) if atendidas > 0 else 0,
            'espera_promedio': row.get('espera_prom', 0) or 0,
            'espera_max': row.get('espera_max', 0) or 0,
            'espera_min': row.get('espera_min', 0) or 0,
        }

    def get_nivel_servicio_detallado(self, filters=None):
        """Nivel de servicio por franja de espera (0-10, 10-20, 20-30 ... 60+ seg)."""
        filters = filters or {}
        tz = self.TZ_DB
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)

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
                CASE
                    WHEN l.bridge_wait_time < 10 THEN '0-10s'
                    WHEN l.bridge_wait_time < 20 THEN '10-20s'
                    WHEN l.bridge_wait_time < 30 THEN '20-30s'
                    WHEN l.bridge_wait_time < 45 THEN '30-45s'
                    WHEN l.bridge_wait_time < 60 THEN '45-60s'
                    ELSE '60s+'
                END AS franja,
                COUNT(*) AS cantidad,
                COALESCE(AVG(l.bridge_wait_time), 0)::int AS espera_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            WHERE l.event IN ({at_ph})
              AND l.bridge_wait_time IS NOT NULL
            GROUP BY franja
            ORDER BY MIN(l.bridge_wait_time)
            """
            params = fin_params + f_params + at_params
            cur.execute(sql, params)
            return self.fetchall_dict(cur)

    # ─────────────────────────────────────────────────────────────
    # Causas de no atencion
    # ─────────────────────────────────────────────────────────────

    def get_causas_no_atencion(self, filters=None):
        filters = filters or {}
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)

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
                l.event AS causa,
                COUNT(*) AS cantidad
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            WHERE l.event NOT IN ({at_ph})
            GROUP BY l.event
            ORDER BY cantidad DESC
            """
            params = fin_params + f_params + at_params
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        total_no_atendidas = sum(r['cantidad'] for r in rows)
        for r in rows:
            r['porcentaje'] = round(r['cantidad'] / total_no_atendidas * 100, 2) if total_no_atendidas else 0
        return rows

    # ─────────────────────────────────────────────────────────────
    # Llamadas atendidas paginadas
    # ─────────────────────────────────────────────────────────────

    def get_llamadas_atendidas(self, filters=None, page=1, per_page=50, sort_by='time', sort_dir='desc'):
        filters = filters or {}
        tz = self.TZ_DB
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)

        f_clauses, f_params = self._filters_sql(filters)
        fin_clauses = [f'l.event IN ({fin_ph})'] + f_clauses
        where_fin = self._where(fin_clauses)

        offset = (page - 1) * per_page

        sort_col = {
            'fecha': 'l.time', 'hora': 'l.time', 'duracion': 'l.duracion_llamada',
            'espera': 'l.bridge_wait_time', 'callid': 'l.callid',
            'agente': 'u.first_name', 'campana': 'c.nombre',
        }.get(sort_by, 'l.time')
        direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

        with self.cursor() as cur:
            count_sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT COUNT(*) FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            WHERE l.event IN ({at_ph})
            """
            cur.execute(count_sql, fin_params + f_params + at_params)
            total = cur.fetchone()[0]

            data_sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT
                l.callid,
                (l.time AT TIME ZONE '{tz}') AS fecha,
                EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int AS hora,
                l.duracion_llamada,
                l.bridge_wait_time,
                l.event,
                l.agente_id,
                u.first_name || ' ' || u.last_name AS agente_nombre,
                l.campana_id,
                c.nombre AS campana_nombre,
                l.numero_marcado,
                l.archivo_grabacion
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_agenteprofile ap ON ap.id = l.agente_id
            LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
            LEFT JOIN ominicontacto_app_campana c ON c.id = l.campana_id
            WHERE l.event IN ({at_ph})
            ORDER BY {sort_col} {direction}
            LIMIT %s OFFSET %s
            """
            params = fin_params + f_params + at_params + [per_page, offset]
            cur.execute(data_sql, params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            if r.get('fecha'):
                r['fecha'] = str(r['fecha'])

        return self._paginate(rows, page, per_page, total)

    # ─────────────────────────────────────────────────────────────
    # Llamadas abandonadas paginadas
    # ─────────────────────────────────────────────────────────────

    def get_llamadas_abandonadas(self, filters=None, page=1, per_page=50, sort_by='time', sort_dir='desc'):
        filters = filters or {}
        tz = self.TZ_DB
        ab_ph, ab_params = self._events_placeholder(self.EVENTOS_ABANDONADAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)

        f_clauses, f_params = self._filters_sql(filters)
        fin_clauses = [f'l.event IN ({fin_ph})'] + f_clauses
        where_fin = self._where(fin_clauses)

        offset = (page - 1) * per_page
        direction = 'DESC' if sort_dir.lower() == 'desc' else 'ASC'

        with self.cursor() as cur:
            count_sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT COUNT(*) FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            WHERE l.event IN ({ab_ph})
            """
            cur.execute(count_sql, fin_params + f_params + ab_params)
            total = cur.fetchone()[0]

            data_sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT
                l.callid,
                (l.time AT TIME ZONE '{tz}') AS fecha,
                EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int AS hora,
                l.event AS causa_abandono,
                l.bridge_wait_time AS tiempo_espera,
                l.campana_id,
                c.nombre AS campana_nombre,
                l.numero_marcado
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_campana c ON c.id = l.campana_id
            WHERE l.event IN ({ab_ph})
            ORDER BY l.time {direction}
            LIMIT %s OFFSET %s
            """
            params = fin_params + f_params + ab_params + [per_page, offset]
            cur.execute(data_sql, params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            if r.get('fecha'):
                r['fecha'] = str(r['fecha'])

        return self._paginate(rows, page, per_page, total)

    # ─────────────────────────────────────────────────────────────
    # Llamadas por tipo (ENTRANTES vs SALIENTES)
    # ─────────────────────────────────────────────────────────────

    def get_llamadas_por_tipo(self, filters=None):
        """
        Retorna {"entrantes": {...}, "salientes": {...}} con conteos correctos.
        - Entrantes: total = atendidas + abandonadas (excluye no_atendidas salientes)
        - Salientes: total = atendidas + no_atendidas (excluye abandonadas entrantes)
        Aplica filtros de fecha y campaña pero NO de agente (vista global siempre).
        """
        filters = filters or {}
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph,  at_params  = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph,  ab_params  = self._events_placeholder(self.EVENTOS_ABANDONADAS)
        na_ph,  na_params  = self._events_placeholder(self.EVENTOS_NO_ATENDIDAS)

        # Filtros de fecha y campaña únicamente — sin agente, sin tipo_llamada
        f_clauses = []
        f_params  = []
        if filters.get('fecha_inicio'):
            f_clauses.append('l.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('l.time <= %s')
            f_params.append(filters['fecha_fin'])
        if filters.get('campana_ids'):
            ids = filters['campana_ids']
            f_clauses.append(
                'l.campana_id IN (' + ','.join(['%s'] * len(ids)) + ')'
            )
            f_params.extend(ids)
        elif filters.get('campana_id'):
            f_clauses.append('l.campana_id = %s')
            f_params.append(filters['campana_id'])

        def _run_tipo(tipo_val):
            tipo_clauses = (
                [f'l.event IN ({fin_ph})', 'l.tipo_llamada = %s']
                + f_clauses
            )
            where = self._where(tipo_clauses)
            sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where}
                GROUP BY callid
            )
            SELECT
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COUNT(CASE WHEN l.event IN ({na_ph}) THEN 1 END) AS no_atendidas
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            """
            params = fin_params + [tipo_val] + f_params + at_params + ab_params + na_params
            with self.cursor() as cur:
                cur.execute(sql, params)
                return self.fetchone_dict(cur)

        ent_row = _run_tipo(self.TIPO_ENTRANTE)
        sal_row = _run_tipo(self.TIPO_SALIENTE)
        dial_row = _run_tipo(self.TIPO_DIALER)

        ent_at    = int(ent_row.get('atendidas',  0) or 0)
        ent_ab    = int(ent_row.get('abandonadas', 0) or 0)
        ent_total = ent_at + ent_ab
        nivel_atencion_ent = round(ent_at / ent_total * 100, 2) if ent_total > 0 else 0
        tasa_abandono_ent  = round(ent_ab / ent_total * 100, 2) if ent_total > 0 else 0

        sal_at    = int(sal_row.get('atendidas',   0) or 0)
        sal_na    = int(sal_row.get('no_atendidas', 0) or 0)
        sal_total = sal_at + sal_na
        nivel_atencion_sal = round(sal_at / sal_total * 100, 2) if sal_total > 0 else 0
        tasa_no_atencion   = round(sal_na / sal_total * 100, 2) if sal_total > 0 else 0

        # Dialer: conectadas (atendidas) + abandonadas en cola + no contactadas
        dial_at = int(dial_row.get('atendidas',   0) or 0)
        dial_ab = int(dial_row.get('abandonadas', 0) or 0)
        dial_na = int(dial_row.get('no_atendidas', 0) or 0)
        dial_total = dial_at + dial_ab + dial_na
        dial_contactadas = dial_at + dial_ab
        tasa_contactabilidad_dial = (
            round(dial_contactadas / dial_total * 100, 2) if dial_total > 0 else 0
        )
        tasa_conexion_agente_dial = (
            round(dial_at / dial_contactadas * 100, 2) if dial_contactadas > 0 else 0
        )

        return {
            'entrantes': {
                'total':          ent_total,
                'atendidas':      ent_at,
                'abandonadas':    ent_ab,
                'nivel_atencion': nivel_atencion_ent,
                'tasa_abandono':  tasa_abandono_ent,
            },
            'salientes': {
                'total':           sal_total,
                'atendidas':       sal_at,
                'no_atendidas':    sal_na,
                'nivel_atencion':  nivel_atencion_sal,
                'tasa_no_atencion': tasa_no_atencion,
            },
            'dialer': {
                'total':                  dial_total,
                'conectadas_agente':      dial_at,
                'abandonadas_cola':       dial_ab,
                'no_contactadas':         dial_na,
                'contactadas':            dial_contactadas,
                'tasa_contactabilidad':   tasa_contactabilidad_dial,
                'tasa_conexion_agente':   tasa_conexion_agente_dial,
            },
        }

    # ─────────────────────────────────────────────────────────────
    # Llamadas por campaña
    # ─────────────────────────────────────────────────────────────

    def get_llamadas_por_campana(self, filters=None):
        filters = filters or {}
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
                l.campana_id,
                c.nombre AS campana_nombre,
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_campana c ON c.id = l.campana_id
            GROUP BY l.campana_id, c.nombre
            ORDER BY total DESC
            """
            params = fin_params + f_params + at_params + ab_params + at_params * 2
            cur.execute(sql, params)
            return self.fetchall_dict(cur)

    # ─────────────────────────────────────────────────────────────
    # Export Excel (openpyxl)
    # ─────────────────────────────────────────────────────────────

    def export_llamadas_atendidas_excel(self, filters=None):
        """Retorna bytes de un .xlsx con todas las llamadas atendidas."""
        import openpyxl
        from io import BytesIO

        result = self.get_llamadas_atendidas(filters, page=1, per_page=50000)
        rows = result.get('data', [])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Llamadas Atendidas'

        headers = ['CallID', 'Fecha', 'Hora', 'Duración (s)', 'Espera (s)',
                   'Evento', 'Agente ID', 'Agente', 'Campaña ID', 'Campaña',
                   'Número', 'Grabación']
        keys = ['callid', 'fecha', 'hora', 'duracion_llamada', 'bridge_wait_time',
                'event', 'agente_id', 'agente_nombre', 'campana_id', 'campana_nombre',
                'numero_marcado', 'archivo_grabacion']
        ws.append(headers)
        for row in rows:
            ws.append([row.get(k) for k in keys])

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

    def export_llamadas_abandonadas_excel(self, filters=None):
        """Retorna bytes de un .xlsx con llamadas abandonadas."""
        import openpyxl
        from io import BytesIO

        result = self.get_llamadas_abandonadas(filters, page=1, per_page=50000)
        rows = result.get('data', [])

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = 'Llamadas Abandonadas'
        headers = ['CallID', 'Fecha', 'Hora', 'Causa', 'Espera (s)', 'Campaña ID', 'Campaña', 'Número']
        keys = ['callid', 'fecha', 'hora', 'causa_abandono', 'tiempo_espera', 'campana_id', 'campana_nombre', 'numero_marcado']
        ws.append(headers)
        for row in rows:
            ws.append([row.get(k) for k in keys])

        buffer = BytesIO()
        wb.save(buffer)
        return buffer.getvalue()

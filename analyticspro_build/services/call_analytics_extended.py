"""
Servicio extendido de analytics de llamadas (transferencias, salientes, distribuciones).
Port de call_analytics_extended.py a SQL crudo.
"""
from analyticspro.services.base import AnalyticsBaseService
from analyticspro.constants import (
    EVENTOS_TRANSFERENCIAS, EVENTOS_SALIENTES,
)


class CallAnalyticsExtendedService(AnalyticsBaseService):

    EVENTOS_TRANSFER = list(EVENTOS_TRANSFERENCIAS.keys())
    EVENTOS_SAL = list(EVENTOS_SALIENTES.keys())

    # ─────────────────────────────────────────────────────────────
    # Distribución por campaña (detalle)
    # ─────────────────────────────────────────────────────────────

    def get_distribucion_por_campana_detalle(self, filters=None):
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
                l.campana_id,
                c.nombre AS campana_nombre,
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada ELSE 0 END), 0) AS tiempo_total,
                COUNT(DISTINCT CASE WHEN l.event IN ({at_ph}) THEN l.agente_id END) AS agentes_activos
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_campana c ON c.id = l.campana_id
            GROUP BY l.campana_id, c.nombre
            ORDER BY total DESC
            """
            params = fin_params + f_params + at_params + ab_params + at_params * 3 + at_params
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            total = r.get('total', 0) or 0
            atendidas = r.get('atendidas', 0) or 0
            r['nivel_atencion'] = round(atendidas / total * 100, 2) if total > 0 else 0
            r['tiempo_total'] = int(r.get('tiempo_total', 0) or 0)
        return rows

    # ─────────────────────────────────────────────────────────────
    # Transferencias
    # ─────────────────────────────────────────────────────────────

    def get_transferencias(self, filters=None):
        filters = filters or {}
        tr_ph, tr_params = self._events_placeholder(self.EVENTOS_TRANSFER)

        f_clauses, f_params = self._filters_sql(filters)
        tr_clauses = [f'l.event IN ({tr_ph})'] + f_clauses
        where_tr = self._where(tr_clauses)

        with self.cursor() as cur:
            sql = f"""
            SELECT
                l.event,
                COUNT(*) AS cantidad,
                COUNT(DISTINCT l.agente_id) AS agentes
            FROM reportes_app_llamadalog l
            {where_tr}
            GROUP BY l.event
            ORDER BY cantidad DESC
            """
            params = tr_params + f_params
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        # Enrich with descriptions
        for r in rows:
            r['descripcion'] = EVENTOS_TRANSFERENCIAS.get(r['event'], r['event'])
        return rows

    # ─────────────────────────────────────────────────────────────
    # Distribución horaria detallada
    # ─────────────────────────────────────────────────────────────

    def get_distribucion_horaria_detallada(self, filters=None, agrupar_por='hora'):
        """
        Distribución detallada con sub-agrupaciones: hora, dia, semana, mes, campana.
        Retorna: grupo, total_llamadas, atendidas, abandonadas, transferidas,
                 porcentaje_atendidas, porcentaje_abandonadas,
                 tiempo_espera_promedio, tiempo_abandono_promedio, duracion_promedio
        """
        filters = filters or {}
        tz = self.TZ_DB
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params   = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph, ab_params   = self._events_placeholder(self.EVENTOS_ABANDONADAS)
        tr_ph, tr_params   = self._events_placeholder(self.EVENTOS_TRANSFER)

        f_clauses, f_params = self._filters_sql(filters)
        fin_clauses = [f'l.event IN ({fin_ph})'] + f_clauses
        where_fin = self._where(fin_clauses)

        # ── Expresión GROUP BY según agrupador ─────────────────────
        if agrupar_por == 'hora':
            group_expr = f"EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int"
            extra_join = ''
        elif agrupar_por == 'dia':
            group_expr = f"DATE(l.time AT TIME ZONE '{tz}')"
            extra_join = ''
        elif agrupar_por == 'semana':
            group_expr = (
                f"TO_CHAR(DATE_TRUNC('week', (l.time AT TIME ZONE '{tz}')), 'IYYY-IW')"
            )
            extra_join = ''
        elif agrupar_por == 'mes':
            group_expr = f"TO_CHAR(l.time AT TIME ZONE '{tz}', 'YYYY-MM')"
            extra_join = ''
        elif agrupar_por == 'campana':
            group_expr = 'COALESCE(c.nombre, l.campana_id::text)'
            extra_join = 'LEFT JOIN ominicontacto_app_campana c ON c.id = l.campana_id'
        else:
            group_expr = f"EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int"
            extra_join = ''

        with self.cursor() as cur:
            sql = f"""
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT
                {group_expr} AS grupo_raw,
                COUNT(*) AS total_llamadas,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS abandonadas,
                COUNT(CASE WHEN l.event IN ({tr_ph}) THEN 1 END) AS transferidas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph})
                    THEN l.bridge_wait_time END), 0) AS espera_prom,
                COALESCE(AVG(CASE WHEN l.event IN ({ab_ph})
                    THEN l.bridge_wait_time END), 0) AS abandono_prom,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph})
                    THEN l.duracion_llamada END), 0) AS duracion_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            {extra_join}
            GROUP BY grupo_raw
            ORDER BY grupo_raw
            """
            params = (fin_params + f_params
                      + at_params + ab_params + tr_params
                      + at_params + ab_params + at_params)
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        # ── Post-proceso: formatear etiqueta y calcular porcentajes ─
        MESES = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
                 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

        datos = []
        for r in rows:
            raw = r['grupo_raw']
            total = int(r['total_llamadas'] or 0)
            atend = int(r['atendidas'] or 0)
            aband = int(r['abandonadas'] or 0)
            trans = int(r['transferidas'] or 0)

            if agrupar_por == 'hora':
                h = int(float(raw))
                label = f"{h:02d}:00 - {(h+1)%24:02d}:00"
            elif agrupar_por == 'dia':
                label = str(raw)  # DATE → 'YYYY-MM-DD'
                # reformat to DD/MM/YYYY
                try:
                    parts = str(raw).split('-')
                    if len(parts) == 3:
                        label = f"{parts[2]}/{parts[1]}/{parts[0]}"
                except Exception:
                    label = str(raw)
            elif agrupar_por == 'semana':
                label = f"Semana {raw}"  # e.g. "2025-27"
            elif agrupar_por == 'mes':
                try:
                    # raw = 'YYYY-MM'
                    m = int(str(raw).split('-')[1])
                    y = str(raw).split('-')[0]
                    label = f"{MESES[m-1]} {y}"
                except Exception:
                    label = str(raw)
            else:
                label = str(raw)

            datos.append({
                'grupo': label,
                'grupo_sort': str(raw),
                'total_llamadas': total,
                'atendidas': atend,
                'abandonadas': aband,
                'transferidas': trans,
                'porcentaje_atendidas': round(atend / total * 100, 2) if total else 0,
                'porcentaje_abandonadas': round(aband / total * 100, 2) if total else 0,
                'tiempo_espera_promedio': round(float(r['espera_prom'] or 0), 0),
                'tiempo_abandono_promedio': round(float(r['abandono_prom'] or 0), 0),
                'duracion_promedio': round(float(r['duracion_prom'] or 0), 0),
            })

        # ── Para hora: rellenar las 24 horas aunque tengan 0 datos ─
        if agrupar_por == 'hora':
            existing = {d['grupo']: d for d in datos}
            datos = []
            for h in range(24):
                lbl = f"{h:02d}:00 - {(h+1)%24:02d}:00"
                datos.append(existing.get(lbl, {
                    'grupo': lbl, 'grupo_sort': str(h),
                    'total_llamadas': 0, 'atendidas': 0, 'abandonadas': 0,
                    'transferidas': 0, 'porcentaje_atendidas': 0,
                    'porcentaje_abandonadas': 0, 'tiempo_espera_promedio': 0,
                    'tiempo_abandono_promedio': 0, 'duracion_promedio': 0,
                }))
        elif agrupar_por == 'campana':
            datos.sort(key=lambda x: x['total_llamadas'], reverse=True)

        return datos

    # ─────────────────────────────────────────────────────────────
    # Tabla distribución horaria (hora × día)
    # ─────────────────────────────────────────────────────────────

    def get_tabla_distribucion_horaria(self, filters=None):
        filters = filters or {}
        tz = self.TZ_DB
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
                DATE(l.time AT TIME ZONE '{tz}') AS fecha,
                EXTRACT(HOUR FROM (l.time AT TIME ZONE '{tz}'))::int AS hora,
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS atendidas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.bridge_wait_time END), 0)::int AS espera_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            GROUP BY fecha, hora
            ORDER BY fecha, hora
            """
            params = fin_params + f_params + at_params + at_params
            cur.execute(sql, params)
            rows = self.fetchall_dict(cur)

        for r in rows:
            if r.get('fecha'):
                r['fecha'] = str(r['fecha'])
        return rows

    # ─────────────────────────────────────────────────────────────
    # Salientes: dashboard
    # ─────────────────────────────────────────────────────────────

    def get_salientes_dashboard(self, filters=None):
        filters = filters or {}
        tz = self.TZ_DB

        # Override to get SALIENTES only
        f_clauses = []
        f_params = []
        f_clauses.append(f'l.tipo_llamada = %s')
        f_params.append(self.TIPO_SALIENTE)

        if filters.get('fecha_inicio'):
            f_clauses.append('l.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('l.time <= %s')
            f_params.append(filters['fecha_fin'])
        if filters.get('campana_id'):
            f_clauses.append('l.campana_id = %s')
            f_params.append(filters['campana_id'])

        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        ab_ph, ab_params = self._events_placeholder(self.EVENTOS_ABANDONADAS)

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
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS contestadas,
                COUNT(CASE WHEN l.event IN ({ab_ph}) THEN 1 END) AS no_contestadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom,
                COUNT(DISTINCT l.campana_id) AS campanas,
                COUNT(DISTINCT CASE WHEN l.event IN ({at_ph}) THEN l.agente_id END) AS agentes_activos
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            """
            params = fin_params + f_params + at_params + ab_params + at_params + at_params
            cur.execute(sql, params)
            row = self.fetchone_dict(cur)

        total = row.get('total', 0) or 0
        contestadas = row.get('contestadas', 0) or 0
        return {
            **row,
            'tasa_contacto': round(contestadas / total * 100, 2) if total > 0 else 0,
        }

    def get_salientes_por_agente(self, filters=None):
        filters = filters or {}

        f_clauses = ['l.tipo_llamada = %s']
        f_params = [self.TIPO_SALIENTE]
        if filters.get('fecha_inicio'):
            f_clauses.append('l.time >= %s')
            f_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            f_clauses.append('l.time <= %s')
            f_params.append(filters['fecha_fin'])

        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
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
                COUNT(*) AS total,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END) AS contestadas,
                COALESCE(AVG(CASE WHEN l.event IN ({at_ph}) THEN l.duracion_llamada END), 0)::int AS tmo_prom
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_agenteprofile ap ON ap.id = l.agente_id
            LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
            WHERE l.agente_id IS NOT NULL
            GROUP BY l.agente_id, u.first_name, u.last_name
            ORDER BY total DESC
            """
            params = fin_params + f_params + at_params + at_params
            cur.execute(sql, params)
            return self.fetchall_dict(cur)

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
        login_time_local = None
        for act in acts:
            if act['event'] == 'ADDMEMBER':
                login_time = act['time']
                login_time_local = act['time_local']
            elif act['event'] == 'REMOVEMEMBER' and login_time:
                dur = (act['time'] - login_time).total_seconds()
                sesiones.append({
                    'inicio': str(login_time_local),
                    'fin': str(act['time_local']),
                    'duracion_s': int(dur),
                })
                login_time = None
                login_time_local = None
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
                SELECT a.event, a.time, a.pausa_id,
                       (a.time AT TIME ZONE '{tz}') AS time_local,
                       p.nombre AS pausa_nombre, p.tipo AS pausa_tipo
                FROM reportes_app_actividadagentelog a
                LEFT JOIN ominicontacto_app_pausa p ON p.id::TEXT = a.pausa_id
                {where}
                AND a.event IN ('PAUSEALL', 'UNPAUSEALL')
                ORDER BY a.time
            """, f_params)
            acts = self.fetchall_dict(cur)

        pausas = []
        pausa_inicio = None
        pausa_inicio_local = None
        pausa_meta = {}
        for act in acts:
            if act['event'] == 'PAUSEALL':
                pausa_inicio = act['time']
                pausa_inicio_local = act['time_local']
                pausa_meta = {
                    'pausa_id': act['pausa_id'],
                    'nombre': act.get('pausa_nombre', 'Desconocida'),
                    'tipo': act.get('pausa_tipo', 'R'),
                }
            elif act['event'] == 'UNPAUSEALL' and pausa_inicio:
                dur = (act['time'] - pausa_inicio).total_seconds()
                pausas.append({
                    'inicio': str(pausa_inicio_local),
                    'fin': str(act['time_local']),
                    'duracion_s': int(dur),
                    **pausa_meta,
                })
                pausa_inicio = None
                pausa_inicio_local = None

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
            # 'time' expone la hora local (Bogota); se descarta el
            # timestamptz crudo en UTC para no filtrarlo a la UI.
            r['time'] = str(r['time_local'])
            r['time_local'] = r['time']
        return rows

    # ─────────────────────────────────────────────────────────────
    # Rendimiento completo: llamadas + sesiones + pausas por agente
    # ─────────────────────────────────────────────────────────────

    def get_rendimiento_completo(self, filters=None):
        """
        Combina datos de llamadas (llamadalog) y sesiones/pausas
        (actividadagentelog) para devolver una fila rica por agente.
        Campos: nombre, extension, llamadas_contestadas, num_sesiones,
                tiempo_total_sesion, tiempo_promedio_sesion, tiempo_al_habla,
                num_pausas, tiempo_pausa_recreativa, tiempo_pausa_productiva,
                tiempo_total_pausa, tiempo_promedio_pausa, ocupacion,
                primer_login, ultimo_logout.
        """
        filters = filters or {}
        tz = self.TZ_DB

        # ── 1. Call data ─────────────────────────────────────────────
        fin_ph, fin_params = self._events_placeholder(self.EVENTOS_FINALES)
        at_ph, at_params = self._events_placeholder(self.EVENTOS_ATENDIDAS)
        f_clauses, f_params = self._filters_sql(filters)
        fin_clauses = ['l.event IN ({})'.format(fin_ph)] + f_clauses
        where_fin = self._where(fin_clauses)

        with self.cursor() as cur:
            sql_calls = """
            WITH last_ev AS (
                SELECT callid, MAX(id) AS ultimo_id
                FROM reportes_app_llamadalog l
                {where_fin}
                GROUP BY callid
            )
            SELECT
                l.agente_id,
                u.first_name || ' ' || u.last_name AS nombre,
                ap.sip_extension AS extension,
                COUNT(CASE WHEN l.event IN ({at_ph}) THEN 1 END)
                    AS llamadas_contestadas,
                COALESCE(SUM(CASE WHEN l.event IN ({at_ph})
                    THEN l.duracion_llamada ELSE 0 END), 0) AS tiempo_al_habla
            FROM reportes_app_llamadalog l
            JOIN last_ev ev ON ev.callid = l.callid AND ev.ultimo_id = l.id
            LEFT JOIN ominicontacto_app_agenteprofile ap ON ap.id = l.agente_id
            LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
            WHERE l.agente_id IS NOT NULL
            GROUP BY l.agente_id, u.first_name, u.last_name, ap.sip_extension
            """.format(where_fin=where_fin, at_ph=at_ph)
            call_params = fin_params + f_params + at_params + at_params
            cur.execute(sql_calls, call_params)
            call_rows = {r['agente_id']: r for r in self.fetchall_dict(cur)}

        # ── 2. Activity filters ──────────────────────────────────────
        act_clauses = []
        act_params = []
        if filters.get('fecha_inicio'):
            act_clauses.append('a.time >= %s')
            act_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            act_clauses.append('a.time <= %s')
            act_params.append(filters['fecha_fin'])
        if filters.get('agente_ids'):
            ids = filters['agente_ids']
            act_clauses.append(
                'a.agente_id IN ({})'.format(','.join(['%s'] * len(ids)))
            )
            act_params.extend(ids)
        elif filters.get('agente_id'):
            act_clauses.append('a.agente_id = %s')
            act_params.append(filters['agente_id'])

        act_extra = (
            ' AND ' + ' AND '.join(act_clauses)
        ) if act_clauses else ''

        with self.cursor() as cur:
            cur.execute("""
                SELECT
                    a.agente_id,
                    u.first_name || ' ' || u.last_name AS nombre,
                    a.event,
                    a.time,
                    (a.time AT TIME ZONE '{tz}') AS time_local,
                    p.tipo AS pausa_tipo
                FROM reportes_app_actividadagentelog a
                LEFT JOIN ominicontacto_app_agenteprofile ap
                    ON ap.id = a.agente_id
                LEFT JOIN ominicontacto_app_user u ON u.id = ap.user_id
                LEFT JOIN ominicontacto_app_pausa p
                    ON p.id::TEXT = a.pausa_id
                WHERE a.event IN
                    ('ADDMEMBER','REMOVEMEMBER','PAUSEALL','UNPAUSEALL')
                {extra}
                ORDER BY a.agente_id, a.time
            """.format(tz=tz, extra=act_extra), act_params)
            actividades = self.fetchall_dict(cur)

        # ── 3. State machine per agent ───────────────────────────────
        agentes_acts = {}
        for act in actividades:
            aid = act['agente_id']
            if aid not in agentes_acts:
                agentes_acts[aid] = {
                    'nombre': act.get('nombre', ''),
                    'actividades': [],
                }
            agentes_acts[aid]['actividades'].append(act)

        act_data = {}
        for aid, data in agentes_acts.items():
            num_ses = 0
            num_pau = 0
            t_ses = 0.0
            t_pau_prod = 0.0
            t_pau_rec = 0.0
            login_t = None
            pausa_t = None
            pausa_tipo = 'R'
            primer_login = None
            ultimo_logout = None

            for act in data['actividades']:
                ev = act['event']
                t = act['time']
                t_local = act['time_local']
                if ev == 'ADDMEMBER':
                    login_t = t
                    if primer_login is None:
                        primer_login = t_local
                elif ev == 'REMOVEMEMBER':
                    ultimo_logout = t_local
                    if login_t is not None:
                        t_ses += (t - login_t).total_seconds()
                        num_ses += 1
                        login_t = None
                elif ev == 'PAUSEALL':
                    pausa_t = t
                    pausa_tipo = act.get('pausa_tipo') or 'R'
                elif ev == 'UNPAUSEALL' and pausa_t is not None:
                    dur = (t - pausa_t).total_seconds()
                    num_pau += 1
                    if pausa_tipo == 'P':
                        t_pau_prod += dur
                    else:
                        t_pau_rec += dur
                    pausa_t = None

            act_data[aid] = {
                'nombre': data['nombre'],
                'num_sesiones': num_ses,
                'num_pausas': num_pau,
                'tiempo_total_sesion': int(t_ses),
                'tiempo_pausa_recreativa': int(t_pau_rec),
                'tiempo_pausa_productiva': int(t_pau_prod),
                'primer_login': str(primer_login) if primer_login else '',
                'ultimo_logout': str(ultimo_logout) if ultimo_logout else '',
            }

        # ── 4. Merge ─────────────────────────────────────────────────
        all_ids = set(call_rows.keys()) | set(act_data.keys())
        resultado = []
        for aid in all_ids:
            cr = call_rows.get(aid, {})
            ar = act_data.get(aid, {})

            nombre = cr.get('nombre') or ar.get('nombre', '')
            if not nombre:
                continue

            lc = int(cr.get('llamadas_contestadas', 0) or 0)
            tal = int(cr.get('tiempo_al_habla', 0) or 0)
            ns = ar.get('num_sesiones', 0)
            tts = ar.get('tiempo_total_sesion', 0)
            np_ = ar.get('num_pausas', 0)
            tpr = ar.get('tiempo_pausa_recreativa', 0)
            tpp = ar.get('tiempo_pausa_productiva', 0)

            t_total_pausa = tpr + tpp
            t_prom_sesion = (tts // ns) if ns > 0 else 0
            t_prom_pausa = (t_total_pausa // np_) if np_ > 0 else 0
            ocupacion = round(tal / tts * 100, 2) if tts > 0 else 0

            resultado.append({
                'agente_id': aid,
                'nombre': nombre,
                'extension': cr.get('extension', ''),
                'llamadas_contestadas': lc,
                'num_sesiones': ns,
                'tiempo_total_sesion': tts,
                'tiempo_promedio_sesion': t_prom_sesion,
                'tiempo_al_habla': tal,
                'num_pausas': np_,
                'tiempo_pausa_recreativa': tpr,
                'tiempo_pausa_productiva': tpp,
                'tiempo_total_pausa': t_total_pausa,
                'tiempo_promedio_pausa': t_prom_pausa,
                'ocupacion': ocupacion,
                'primer_login': ar.get('primer_login', ''),
                'ultimo_logout': ar.get('ultimo_logout', ''),
            })

        return sorted(resultado,
                      key=lambda x: x['llamadas_contestadas'], reverse=True)

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

    # ─────────────────────────────────────────────────────────────
    # Heatmap completo: matriz dia x hora
    # ─────────────────────────────────────────────────────────────

    def get_disponibilidad_heatmap_completo(self, filters=None):
        """
        Devuelve { dias: [...], horas: [...], matriz: [[...]] }
        donde matriz[i][j] = cantidad de agentes conectados en dia i a hora j.
        Usado por la pestaña Agentes Avanzado.
        """
        filters = filters or {}
        tz = self.TZ_DB

        act_clauses = []
        act_params = []
        if filters.get('fecha_inicio'):
            act_clauses.append('a.time >= %s')
            act_params.append(filters['fecha_inicio'])
        if filters.get('fecha_fin'):
            act_clauses.append('a.time <= %s')
            act_params.append(filters['fecha_fin'])

        act_extra = (
            ' AND ' + ' AND '.join(act_clauses)
        ) if act_clauses else ''

        with self.cursor() as cur:
            cur.execute("""
                SELECT
                    DATE(a.time AT TIME ZONE '{tz}') AS dia,
                    EXTRACT(HOUR FROM (a.time AT TIME ZONE '{tz}'))::int
                        AS hora,
                    COUNT(DISTINCT a.agente_id) AS agentes
                FROM reportes_app_actividadagentelog a
                WHERE a.event = 'ADDMEMBER'
                {extra}
                GROUP BY dia, hora
                ORDER BY dia, hora
            """.format(tz=tz, extra=act_extra), act_params)
            rows = self.fetchall_dict(cur)

        if not rows:
            return {'dias': [], 'horas': [], 'matriz': []}

        dias_unicos = sorted(set(str(r['dia']) for r in rows))
        horas = list(range(24))

        data = {}
        for r in rows:
            key = (str(r['dia']), int(float(r['hora'])))
            data[key] = int(r['agentes'] or 0)

        matriz = []
        for dia in dias_unicos:
            row = []
            for h in horas:
                row.append(data.get((dia, h), 0))
            matriz.append(row)

        # Format dia labels as DD/MM
        dia_labels = []
        for dia in dias_unicos:
            try:
                parts = dia.split('-')
                dia_labels.append('{}/{}'.format(parts[2], parts[1]))
            except Exception:
                dia_labels.append(str(dia))

        return {
            'dias': dia_labels,
            'horas': ['{:02d}h'.format(h) for h in horas],
            'matriz': matriz,
        }

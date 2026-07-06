"""
Base service con helpers comunes de SQL para analyticspro.
Usa connections['analytics'] (BD omnileads_local).
"""
from django.db import connections
from django.conf import settings

from analyticspro.constants import (
    EVENTOS_ATENDIDAS, EVENTOS_ABANDONADAS, EVENTOS_NO_ATENDIDAS,
    EVENTOS_FINALES, EVENTOS_EXCLUIDOS, EVENTOS_INTERMEDIOS,
    TIPO_ENTRANTE, TIPO_SALIENTE, TIPO_DIALER,
    SLA_THRESHOLD_60, SLA_THRESHOLD_20,
)


class AnalyticsBaseService:
    """
    Clase base para servicios de analytics.
    Ejecuta SQL crudo parametrizado contra la BD 'analytics' (omnileads_local).
    """

    TZ_DB = getattr(settings, 'ANALYTICSPRO_TIMEZONE_DB', 'America/Bogota')
    # Configurable por instalacion via install.sh -> ANALYTICSPRO_INBOUND_ONLY
    # en oml_settings_local.py. Cuando True, todas las queries genericas
    # excluyen salientes (tipo_llamada=1) y dialer (tipo_llamada=2).
    INBOUND_ONLY = getattr(settings, 'ANALYTICSPRO_INBOUND_ONLY', False)

    # Constantes de eventos
    EVENTOS_ATENDIDAS = EVENTOS_ATENDIDAS
    EVENTOS_ABANDONADAS = EVENTOS_ABANDONADAS
    EVENTOS_NO_ATENDIDAS = EVENTOS_NO_ATENDIDAS
    EVENTOS_FINALES = EVENTOS_FINALES
    TIPO_ENTRANTE = TIPO_ENTRANTE
    TIPO_SALIENTE = TIPO_SALIENTE
    TIPO_DIALER = TIPO_DIALER
    SLA_THRESHOLD_60 = SLA_THRESHOLD_60
    SLA_THRESHOLD_20 = SLA_THRESHOLD_20

    def cursor(self):
        return connections['analytics'].cursor()

    def fetchall_dict(self, cursor):
        """Retorna lista de dicts desde un cursor ejecutado."""
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    def fetchone_dict(self, cursor):
        """Retorna un dict desde la primera fila del cursor."""
        cols = [d[0] for d in cursor.description]
        row = cursor.fetchone()
        return dict(zip(cols, row)) if row else {}

    # ─────────────────────────────────────────────────────────────
    # Helpers para construir clausulas WHERE parametrizadas
    # ─────────────────────────────────────────────────────────────

    def _filters_sql(self, filters, table='l'):
        """
        Construye clausulas WHERE + lista de params a partir del dict de filtros.
        Retorna (clauses: list[str], params: list).
        """
        clauses = []
        params = []

        if filters.get('fecha_inicio'):
            clauses.append(f'{table}.time >= %s')
            params.append(filters['fecha_inicio'])

        if filters.get('fecha_fin'):
            clauses.append(f'{table}.time <= %s')
            params.append(filters['fecha_fin'])

        if filters.get('campana_ids'):
            ids = filters['campana_ids']
            placeholders = ','.join(['%s'] * len(ids))
            clauses.append(f'{table}.campana_id IN ({placeholders})')
            params.extend(ids)
        elif filters.get('campana_id'):
            clauses.append(f'{table}.campana_id = %s')
            params.append(filters['campana_id'])

        if filters.get('agente_ids'):
            ids = filters['agente_ids']
            placeholders = ','.join(['%s'] * len(ids))
            clauses.append(f'{table}.agente_id IN ({placeholders})')
            params.extend(ids)
        elif filters.get('agente_id'):
            clauses.append(f'{table}.agente_id = %s')
            params.append(filters['agente_id'])

        if filters.get('tipo_campana'):
            clauses.append(f'{table}.tipo_campana = %s')
            params.append(filters['tipo_campana'])

        # tipo_llamada
        if self.INBOUND_ONLY:
            clauses.append(f'{table}.tipo_llamada = %s')
            params.append(self.TIPO_ENTRANTE)
        elif filters.get('tipo_llamada'):
            if filters['tipo_llamada'] == 'entrantes':
                clauses.append(f'{table}.tipo_llamada = %s')
                params.append(self.TIPO_ENTRANTE)
            elif filters['tipo_llamada'] == 'salientes':
                clauses.append(f'{table}.tipo_llamada = %s')
                params.append(self.TIPO_SALIENTE)
        else:
            tipos = (
                [self.TIPO_ENTRANTE] if self.INBOUND_ONLY
                else [self.TIPO_ENTRANTE, self.TIPO_SALIENTE, self.TIPO_DIALER]
            )
            placeholders = ','.join(['%s'] * len(tipos))
            clauses.append(f'{table}.tipo_llamada IN ({placeholders})')
            params.extend(tipos)

        return clauses, params

    def _where(self, clauses):
        """Joins clauses with AND and prepends WHERE."""
        if clauses:
            return 'WHERE ' + ' AND '.join(clauses)
        return ''

    def _events_placeholder(self, events):
        """Retorna (placeholder_str, list_of_values) para IN (%s, %s, ...)."""
        ph = ','.join(['%s'] * len(events))
        return ph, list(events)

    def _local_ts(self, col='time', table='l'):
        """Expresion SQL para convertir timestamp al TZ local."""
        return f"({table}.{col} AT TIME ZONE '{self.TZ_DB}')"

    def _local_date(self, col='time', table='l'):
        """DATE del timestamp en TZ local."""
        return f"DATE({table}.{col} AT TIME ZONE '{self.TZ_DB}')"

    # ─────────────────────────────────────────────────────────────
    # CTE: ultimo evento por callid
    # ─────────────────────────────────────────────────────────────

    def _last_event_cte(self, filters, event_list=None, cte_name='last_ev'):
        """
        CTE que retorna (callid, ultimo_id) = MAX(id) por callid.
        event_list: si se provee, solo considera esos eventos como candidatos.
        Retorna (cte_sql_fragment, params_list).
        """
        all_clauses, params = self._filters_sql(filters)
        ev_params = []
        if event_list:
            ph, ev_params = self._events_placeholder(event_list)
            all_clauses.insert(0, f'l.event IN ({ph})')
        # event params go FIRST since they're inserted at index 0
        params = ev_params + params

        where_sql = self._where(all_clauses)

        cte_sql = f"""
{cte_name} AS (
    SELECT l.callid, MAX(l.id) AS ultimo_id
    FROM reportes_app_llamadalog l
    {where_sql}
    GROUP BY l.callid
)"""
        return cte_sql, params

    # ─────────────────────────────────────────────────────────────
    # Helpers: campanas, agentes, pausas
    # ─────────────────────────────────────────────────────────────

    def get_campanas_dict(self):
        """{id: nombre} de todas las campanas no-template."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, nombre FROM ominicontacto_app_campana "
                "WHERE es_template = false ORDER BY nombre"
            )
            return {row[0]: row[1] for row in cur.fetchall()}

    def get_agentes_dict(self):
        """{agente_id: {'nombre': ..., 'extension': ...}}"""
        with self.cursor() as cur:
            cur.execute("""
                SELECT ap.id, u.first_name, u.last_name, ap.sip_extension
                FROM ominicontacto_app_agenteprofile ap
                JOIN ominicontacto_app_user u ON u.id = ap.user_id
                WHERE ap.borrado = false
                ORDER BY u.first_name, u.last_name
            """)
            result = {}
            for row in cur.fetchall():
                agente_id, fname, lname, ext = row
                result[agente_id] = {
                    'nombre': f'{fname} {lname}'.strip(),
                    'extension': ext or '',
                }
            return result

    def get_pausas_dict(self):
        """{id: {'nombre': ..., 'tipo': ...}} de pausas activas."""
        with self.cursor() as cur:
            cur.execute(
                "SELECT id, nombre, tipo FROM ominicontacto_app_pausa"
            )
            return {row[0]: {'nombre': row[1], 'tipo': row[2]}
                    for row in cur.fetchall()}

    # ─────────────────────────────────────────────────────────────
    # Helper: paginación
    # ─────────────────────────────────────────────────────────────

    def _paginate(self, rows, page, per_page, total=None):
        """Estructura de respuesta paginada estándar."""
        total_count = total if total is not None else len(rows)
        return {
            'data': rows,
            'total': total_count,
            'page': page,
            'per_page': per_page,
            'total_pages': (total_count + per_page - 1) // per_page if per_page else 1,
        }

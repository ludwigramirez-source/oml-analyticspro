"""
HTTP health check server para Docker healthcheck.
Corre en puerto 8001 y reporta estado de sincronizacion.
"""
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

import psycopg2

from .config import sync_config
from .watermark import get_all_status

logger = logging.getLogger(__name__)

HEALTH_PORT = 8001


class HealthHandler(BaseHTTPRequestHandler):
    """Handler HTTP para health checks."""

    def do_GET(self):
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/status':
            self._handle_status()
        else:
            self.send_response(404)
            self.end_headers()

    def _handle_health(self):
        """GET /health — Check basico."""
        try:
            conn = psycopg2.connect(**sync_config.get_local_dsn())
            conn.close()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({'status': 'healthy'}).encode()
            )
        except Exception as e:
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'unhealthy',
                    'error': str(e)
                }).encode()
            )

    def _handle_status(self):
        """GET /status — Estado detallado de sync."""
        try:
            conn = psycopg2.connect(**sync_config.get_local_dsn())
            status = get_all_status(conn)
            conn.close()

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'ok',
                    'tables': status
                }).encode()
            )
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'error',
                    'error': str(e)
                }).encode()
            )

    def log_message(self, format, *args):
        """Silenciar logs de cada request."""
        pass


def start_health_server():
    """Arranca el server HTTP de health en un thread separado."""
    server = HTTPServer(('0.0.0.0', HEALTH_PORT), HealthHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health check server en puerto {HEALTH_PORT}")
    return server

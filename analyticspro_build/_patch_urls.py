"""
Patches server urls.py to add new URL names for campanas alertas + agentes avanzado.
"""
import paramiko, sys

hostname = 'capresoca.iptegra.co'
username = 'root'
password = 'c4pr3s0c4.c4ll'
REMOTE_URLS = '/opt/omnileads/ominicontacto/analyticspro/urls.py'
OML_HOME    = '/opt/omnileads/ominicontacto'
VENV_PY     = '/opt/omnileads/virtualenv/bin/python'
FIFO        = '/opt/omnileads/run/.uwsgi-fifo'

def pr(msg):
    sys.stdout.buffer.write((msg + '\n').encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=30)

def run(cmd, timeout=90):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace').strip()
    err = stderr.read().decode('utf-8', errors='replace').strip()
    return out, err

sftp = ssh.open_sftp()

# Read full urls.py
with sftp.open(REMOTE_URLS, 'r') as f:
    content = f.read().decode('utf-8')

pr('Read urls.py OK, length=' + str(len(content)))

# ── Build new URL entries ──────────────────────────────────────────────
NEW_EXT = """
    # ── Call analytics extended — nuevas ────────────────────────────────
    path('analyticspro/api/nivel-atencion-campanas/', api_calls_extended.nivel_atencion_campanas, name='api_nivel_atencion_campanas'),
"""

NEW_AGT = """
    # ── Agent analytics — nuevas ─────────────────────────────────────────
    path('analyticspro/api/agentes/rendimiento-completo/', api_agents.rendimiento_completo, name='api_agentes_rendimiento_completo'),
    path('analyticspro/api/agentes/heatmap-completo/', api_agents.disponibilidad_heatmap_completo, name='api_agentes_heatmap_completo'),
    path('analyticspro/api/agentes/<int:agente_id>/sesiones/', api_agents.sesiones, name='api_agentes_sesiones'),
    path('analyticspro/api/agentes/<int:agente_id>/pausas/', api_agents.pausas, name='api_agentes_pausas'),
    path('analyticspro/api/agentes/<int:agente_id>/timeline/', api_agents.timeline, name='api_agentes_timeline'),
"""

new_content = content

# Add nivel_atencion_campanas after the last salientes line
ANCHOR_EXT = "path('analyticspro/api/salientes/por-agente/',"
if 'nivel_atencion_campanas' not in new_content and ANCHOR_EXT in new_content:
    idx = new_content.index(ANCHOR_EXT)
    # find end of that line
    end_line = new_content.index('\n', idx)
    new_content = new_content[:end_line+1] + NEW_EXT + new_content[end_line+1:]
    pr('Added nivel_atencion_campanas URL')
else:
    pr('Skip nivel_atencion_campanas (already exists or anchor not found)')

# Add agent nuevas after 'api_agentes_rendimiento' line (or 'api_agentes_heatmap' if exists)
ANCHOR_AGT = "name='api_agentes_rendimiento'"
if 'rendimiento_completo' not in new_content and ANCHOR_AGT in new_content:
    idx = new_content.index(ANCHOR_AGT)
    end_line = new_content.index('\n', idx)
    new_content = new_content[:end_line+1] + NEW_AGT + new_content[end_line+1:]
    pr('Added agent nuevas URLs')
else:
    pr('Skip agent nuevas (already exists or anchor not found)')

# Write back
with sftp.open(REMOTE_URLS, 'w') as f:
    f.write(new_content.encode('utf-8'))
pr('urls.py written OK')

# Verify
with sftp.open(REMOTE_URLS, 'r') as f:
    verify = f.read().decode('utf-8')
pr('Verification: nivel_atencion_campanas present = ' + str('nivel_atencion_campanas' in verify))
pr('Verification: rendimiento_completo present = ' + str('rendimiento_completo' in verify))
pr('Verification: agentes_sesiones present = ' + str('agentes_sesiones' in verify))

sftp.close()

# ── Collectstatic ────────────────────────────────────────────────────
pr('\nRunning collectstatic ...')
out, err = run(
    'bash -c "source /etc/profile.d/omnileads_envars.sh 2>/dev/null; '
    'cd ' + OML_HOME + '; '
    + VENV_PY + ' manage.py collectstatic --noinput -v 0 2>&1"',
    timeout=120
)
pr(out[-800:] if len(out) > 800 else out)
if err: pr('STDERR: ' + err[-400:])

# ── Reload uWSGI ─────────────────────────────────────────────────────
pr('\nReloading uWSGI ...')
out, err = run('echo r > ' + FIFO + ' 2>&1; sleep 2; echo reload_sent')
pr(out)
if err: pr('ERR: ' + err)

ssh.close()
pr('\nDone!')

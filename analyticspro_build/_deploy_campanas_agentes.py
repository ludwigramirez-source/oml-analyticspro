"""
Deploy: campanas alertas + agentes avanzado tabs.
Uploads modified files + patches urls.py on server.
"""
import paramiko, sys, os

hostname = 'capresoca.iptegra.co'
username = 'root'
password = 'c4pr3s0c4.c4ll'

LOCAL_BASE  = r'C:\Users\Usuario\Documents\DEV\oml-analyticspro\analyticspro_build'
REMOTE_BASE = '/opt/omnileads/ominicontacto/analyticspro'
OML_HOME    = '/opt/omnileads/ominicontacto'
VENV_PY     = '/opt/omnileads/virtualenv/bin/python'
FIFO        = '/opt/omnileads/run/.uwsgi-fifo'

FILES = [
    ('services/call_analytics_extended.py', 'services/call_analytics_extended.py'),
    ('services/agent_analytics.py',         'services/agent_analytics.py'),
    ('views/api_calls_extended.py',         'views/api_calls_extended.py'),
    ('views/api_agents.py',                 'views/api_agents.py'),
    ('templates/analyticspro/dashboard.html', 'templates/analyticspro/dashboard.html'),
    ('static/analyticspro/js/dashboard.js',   'static/analyticspro/js/dashboard.js'),
]

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

# ── 1. Upload files ──────────────────────────────────────────────────
for local_rel, remote_rel in FILES:
    local_path  = os.path.join(LOCAL_BASE, local_rel)
    remote_path = REMOTE_BASE + '/' + remote_rel.replace('\\', '/')
    pr('Uploading: ' + remote_rel + ' ...')
    sftp.put(local_path, remote_path)
    pr('  OK: ' + remote_path)

# ── 2. Read current urls.py ──────────────────────────────────────────
pr('\nReading server urls.py ...')
out, _ = run('cat ' + REMOTE_BASE + '/urls.py')
pr('Current urls.py length: ' + str(len(out)) + ' chars')
pr('--- snippet ---')
pr(out[:3000])
pr('--- end snippet ---')

# Check if new URLs already exist
needs_campanas   = 'nivel_atencion_campanas' not in out
needs_rendimiento = 'rendimiento_completo' not in out
needs_heatmap    = 'heatmap_completo' not in out
needs_sesiones   = 'agentes_sesiones' not in out and 'api_sesiones' not in out

pr('\nNeeds nuevas URLs:')
pr('  campanasAlertas: ' + str(needs_campanas))
pr('  rendimientoCompleto: ' + str(needs_rendimiento))
pr('  heatmapCompleto: ' + str(needs_heatmap))
pr('  sesiones/pausas: ' + str(needs_sesiones))

sftp.close()
ssh.close()
pr('\nDone! Review output above, then run patch manually if needed.')

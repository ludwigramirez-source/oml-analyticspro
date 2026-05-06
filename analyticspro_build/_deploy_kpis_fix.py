"""
Fix KPIs tab: correct llamadas_por_tipo shape + JS rendering.
Uploads: call_analytics.py, dashboard.js, dashboard.html
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
    ('services/call_analytics.py',              'services/call_analytics.py'),
    ('static/analyticspro/js/dashboard.js',     'static/analyticspro/js/dashboard.js'),
    ('templates/analyticspro/dashboard.html',   'templates/analyticspro/dashboard.html'),
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
    remote_path = REMOTE_BASE + '/' + remote_rel.replace(os.sep, '/')
    pr('Uploading: ' + remote_rel + ' ...')
    sftp.put(local_path, remote_path)
    pr('  OK: ' + remote_path)

sftp.close()

# ── 2. Quick syntax check ────────────────────────────────────────────
pr('\nSyntax check ...')
out, err = run(
    'bash -c "source /etc/profile.d/omnileads_envars.sh 2>/dev/null; '
    + VENV_PY + ' -m py_compile '
    + REMOTE_BASE + '/services/call_analytics.py && echo SYNTAX_OK"',
    timeout=30
)
pr(out or '(no output)')
if err:
    errl = [l for l in err.splitlines() if 'psycopg2' not in l and 'UserWarning' not in l]
    if errl:
        pr('STDERR: ' + '\n'.join(errl[:10]))

# ── 3. Collectstatic ─────────────────────────────────────────────────
pr('\nRunning collectstatic ...')
out, err = run(
    'bash -c "source /etc/profile.d/omnileads_envars.sh 2>/dev/null; '
    'cd ' + OML_HOME + '; '
    + VENV_PY + ' manage.py collectstatic --noinput -v 0 2>&1"',
    timeout=120
)
pr(out[-800:] if len(out) > 800 else out)
if err: pr('STDERR: ' + err[-400:])

# ── 4. Reload uWSGI ──────────────────────────────────────────────────
pr('\nReloading uWSGI ...')
out, err = run('echo r > ' + FIFO + ' 2>&1; sleep 2; echo reload_sent')
pr(out)
if err: pr('ERR: ' + err)

ssh.close()
pr('\nDone!')

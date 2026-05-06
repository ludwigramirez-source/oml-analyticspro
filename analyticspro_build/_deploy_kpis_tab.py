"""
Deploy: new KPIs tab (first tab) with Entrantes/Salientes cards + 11 metric cards.
Uploads dashboard.html + dashboard.js, runs collectstatic, reloads uWSGI.
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
    remote_path = REMOTE_BASE + '/' + remote_rel.replace(os.sep, '/')
    pr('Uploading: ' + remote_rel + ' ...')
    sftp.put(local_path, remote_path)
    pr('  OK: ' + remote_path)

sftp.close()

# ── 2. Collectstatic ─────────────────────────────────────────────────
pr('\nRunning collectstatic ...')
out, err = run(
    'bash -c "source /etc/profile.d/omnileads_envars.sh 2>/dev/null; '
    'cd ' + OML_HOME + '; '
    + VENV_PY + ' manage.py collectstatic --noinput -v 0 2>&1"',
    timeout=120
)
pr(out[-800:] if len(out) > 800 else out)
if err: pr('STDERR: ' + err[-400:])

# ── 3. Reload uWSGI ──────────────────────────────────────────────────
pr('\nReloading uWSGI ...')
out, err = run('echo r > ' + FIFO + ' 2>&1; sleep 2; echo reload_sent')
pr(out)
if err: pr('ERR: ' + err)

ssh.close()
pr('\nDone!')

"""Verifica que las nuevas URLs sean accesibles via Django shell."""
import paramiko, sys

hostname = 'capresoca.iptegra.co'
username = 'root'
password = 'c4pr3s0c4.c4ll'
OML_HOME = '/opt/omnileads/ominicontacto'
VENV_PY  = '/opt/omnileads/virtualenv/bin/python'

def pr(msg):
    sys.stdout.buffer.write((msg + '\n').encode('utf-8', errors='replace'))
    sys.stdout.buffer.flush()

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=30)

CHECK_SCRIPT = '''
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ominicontacto_app.settings.production")
import django
django.setup()

from django.urls import reverse, NoReverseMatch

urls_to_check = [
    ("analyticspro:api_nivel_atencion_campanas", []),
    ("analyticspro:api_agentes_rendimiento_completo", []),
    ("analyticspro:api_agentes_heatmap_completo", []),
    ("analyticspro:api_agentes_sesiones", [999]),
    ("analyticspro:api_agentes_pausas", [999]),
    ("analyticspro:api_agentes_timeline", [999]),
]

for name, args in urls_to_check:
    try:
        url = reverse(name, args=args) if args else reverse(name)
        print("OK: " + name + " -> " + url)
    except NoReverseMatch as e:
        print("FAIL: " + name + " -> " + str(e))

# Also check template renders
from django.test import RequestFactory
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    u = User.objects.filter(is_superuser=True).first()
    if u:
        rf = RequestFactory()
        req = rf.get("/analyticspro/")
        req.user = u
        from analyticspro.views.dashboard import index
        resp = index(req)
        print("Template render status: " + str(resp.status_code))
    else:
        print("No superuser found for template test")
except Exception as e:
    print("Template render ERROR: " + str(e))
'''

sftp = ssh.open_sftp()
with sftp.open('/tmp/_verify_urls.py', 'w') as f:
    f.write(CHECK_SCRIPT.encode('utf-8'))
sftp.close()

_, stdout, stderr = ssh.exec_command(
    'bash -c "source /etc/profile.d/omnileads_envars.sh 2>/dev/null; '
    'cd ' + OML_HOME + '; '
    + VENV_PY + ' manage.py shell < /tmp/_verify_urls.py" 2>&1',
    timeout=60
)
out = stdout.read().decode('utf-8', errors='replace')
err = stderr.read().decode('utf-8', errors='replace')

lines = [l for l in out.splitlines()
         if 'psycopg2' not in l and 'UserWarning' not in l and '"""' not in l]
pr('\n'.join(lines))
if err:
    errl = [l for l in err.splitlines()
            if 'psycopg2' not in l and 'UserWarning' not in l]
    if errl:
        pr('STDERR: ' + '\n'.join(errl[:20]))

ssh.close()

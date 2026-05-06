import paramiko, sys

hostname = 'capresoca.iptegra.co'
username = 'root'
password = 'c4pr3s0c4.c4ll'

ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(hostname, username=username, password=password, timeout=30)

def run(cmd, timeout=60):
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', errors='replace')
    err = stderr.read().decode('utf-8', errors='replace')
    return out, err

def pr(t):
    sys.stdout.buffer.write(t.encode('utf-8', errors='replace'))
    sys.stdout.buffer.write(b'\n')
    sys.stdout.buffer.flush()

sftp = ssh.open_sftp()
sftp.put(r'C:\Users\Usuario\Documents\DEV\oml-analyticspro\analyticspro_build\_test_apis.py', '/tmp/_test_apis.py')
sftp.close()

out, err = run(
    'bash -c "source /etc/profile.d/omnileads_envars.sh; '
    'cd /opt/omnileads/ominicontacto; '
    '/opt/omnileads/virtualenv/bin/python manage.py shell < /tmp/_test_apis.py" 2>&1',
    timeout=90
)
# Filter psycopg2 warnings
lines = out.splitlines()
filtered = [l for l in lines if 'psycopg2' not in l and 'UserWarning' not in l and '"""' not in l]
pr('\n'.join(filtered[:100]))
ssh.close()

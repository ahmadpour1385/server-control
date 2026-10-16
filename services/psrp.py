from pypsrp.client import Client
from services import ssh

_clients = {}


def forget(sid):
    _clients.pop(sid, None)


def _client(server):
    sid = server['id']
    c = _clients.get(sid)
    if c is None:
        c = Client(server['host'], username=server['username'],
                   password=ssh.get_password(sid), ssl=False,
                   port=server['port'], auth='ntlm',
                   connection_timeout=10, no_proxy=True)
        _clients[sid] = c
    return c


def run(server, script):
    out, streams, had_errors = _client(server).execute_ps(script)
    if had_errors:
        raise RuntimeError('\n'.join(str(e) for e in streams.error) or 'PowerShell error')
    return out
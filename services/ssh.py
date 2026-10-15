import base64
import hashlib

import paramiko
from services import store, auth

_clients = {}
_passwords = {}


def set_password(sid, password):
    _passwords[sid] = password


def get_password(sid):
    pw = _passwords.get(sid)
    if pw is not None:
        return pw
    for s in store.load()['servers']:
        if s['id'] == sid and s.get('secret'):
            pw = auth.decrypt(s['secret'])
            if pw is not None:
                _passwords[sid] = pw
            return pw
    return None


def save_secret(sid, password):
    data = store.load()
    for s in data['servers']:
        if s['id'] == sid:
            s['secret'] = auth.encrypt(password)
    store.save(data)


def clear_secret(sid):
    data = store.load()
    for s in data['servers']:
        if s['id'] == sid:
            s.pop('secret', None)
    store.save(data)


def forget(sid):
    _passwords.pop(sid, None)
    c = _clients.pop(sid, None)
    if c:
        c.close()


def fingerprint(key):
    digest = hashlib.sha256(key.asbytes()).digest()
    return '%s SHA256:%s' % (key.get_name(), base64.b64encode(digest).decode().rstrip('='))


class _Pinned(paramiko.MissingHostKeyPolicy):
    """بار اول اثر انگشت سرور ذخیره می‌شه، دفعه‌های بعد باید یکی باشه."""

    def __init__(self, sid):
        self.sid = sid

    def missing_host_key(self, client, hostname, key):
        fp = fingerprint(key)
        data = store.load()
        for s in data['servers']:
            if s['id'] == self.sid:
                saved = s.get('host_key')
                if saved is None:
                    s['host_key'] = fp
                    store.save(data)
                    return
                if saved != fp:
                    raise paramiko.SSHException(
                        'WARNING: server fingerprint changed (possible attack). '
                        'If you reinstalled the server, press "Reset fingerprint".')
                return
        raise paramiko.SSHException('server not found')


def _client(server):
    sid = server['id']
    c = _clients.get(sid)
    if c and c.get_transport() and c.get_transport().is_active():
        return c
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(_Pinned(sid))
    c.connect(server['host'], port=server['port'], username=server['username'],
              password=get_password(sid), timeout=8,
              look_for_keys=False, allow_agent=False)
    _clients[sid] = c
    return c


def run(server, cmd, timeout=10):
    _, out, _ = _client(server).exec_command(cmd, timeout=timeout)
    return out.read().decode()


def shell(server):
    return _client(server).invoke_shell(term='xterm-256color', width=120, height=30)


def sftp(server):
    return _client(server).open_sftp()
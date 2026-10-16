import tempfile
from pathlib import Path
from unittest import mock

from django.test import SimpleTestCase
from services import auth, ssh, store

PW = 'correct horse battery'


class IsolatedTestCase(SimpleTestCase):
    """هر تست با یه settings.json موقت کار می‌کنه و به فایل واقعی دست نمی‌زنه."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for target, name, value in (
            (store, 'FILE', Path(tmp.name) / 'settings.json'),
            (auth, 'ITER', 1000),  # فقط برای سریع‌تر شدن تست‌ها
        ):
            p = mock.patch.object(target, name, value)
            p.start()
            self.addCleanup(p.stop)
        auth._fails.clear()
        auth._key = None
        ssh._passwords.clear()
        ssh._clients.clear()
        self.addCleanup(setattr, auth, '_key', None)
        self.addCleanup(ssh._passwords.clear)

    def login(self):
        self.client.post('/login/', {'password': PW, 'password2': PW})

    def add_server(self, **extra):
        data = store.load()
        server = {'id': 'srv1', 'name': 'test', 'host': '10.0.0.5', 'port': 22,
                  'username': 'user', 'os': 'linux', **extra}
        data['servers'].append(server)
        store.save(data)
        return server
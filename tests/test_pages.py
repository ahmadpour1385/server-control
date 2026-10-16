from unittest import mock

from django.conf import settings
from services import auth, store
from .base import PW, IsolatedTestCase

PROTECTED = ['/', '/dns/', '/dns/check/', '/files/x/', '/projects/x/',
             '/terminal/x/', '/monitor/x/', '/add/']


class LoginFlowTests(IsolatedTestCase):
    def test_everything_is_locked_when_logged_out(self):
        for url in PROTECTED:
            r = self.client.get(url)
            self.assertRedirects(r, '/login/', fetch_redirect_response=False, msg_prefix=url)

    def test_htmx_requests_get_an_hx_redirect(self):
        r = self.client.get('/', HTTP_HX_REQUEST='true')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['HX-Redirect'], '/login/')

    def test_first_visit_asks_for_a_new_password(self):
        self.assertTrue(self.client.get('/login/').context['first'])

    def test_short_password_is_rejected(self):
        r = self.client.post('/login/', {'password': 'short', 'password2': 'short'})
        self.assertTrue(r.context['error'])
        self.assertFalse(auth.is_set())

    def test_mismatched_passwords_are_rejected(self):
        r = self.client.post('/login/', {'password': PW, 'password2': PW + 'x'})
        self.assertTrue(r.context['error'])
        self.assertFalse(auth.is_set())

    def test_setting_a_password_logs_you_in(self):
        r = self.client.post('/login/', {'password': PW, 'password2': PW})
        self.assertRedirects(r, '/', fetch_redirect_response=False)
        self.assertEqual(self.client.get('/').status_code, 200)

    def test_logout_needs_post_and_locks_again(self):
        self.login()
        self.assertEqual(self.client.get('/logout/').status_code, 405)
        self.client.post('/logout/')
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_wrong_password_is_rejected(self):
        self.login()
        self.client.post('/logout/')
        r = self.client.post('/login/', {'password': 'nope'})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.context['error'])
        self.assertEqual(self.client.get('/').status_code, 302)

    def test_lockout_after_five_wrong_passwords(self):
        self.login()
        self.client.post('/logout/')
        for _ in range(5):
            self.client.post('/login/', {'password': 'nope'})
        r = self.client.post('/login/', {'password': PW})  # حتی پسورد درست هم رد می‌شه
        self.assertTrue(r.context['error'])
        self.assertEqual(self.client.get('/').status_code, 302)


class ServerManagementTests(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def server(self):
        return store.load()['servers'][0]

    def test_add_linux_server_uses_ssh_port(self):
        self.client.post('/add/', {'name': 'web', 'host': '8.8.8.8', 'username': 'root', 'os': 'linux'})
        self.assertEqual((self.server()['name'], self.server()['port']), ('web', 22))

    def test_add_windows_server_uses_winrm_port(self):
        self.client.post('/add/', {'name': 'win', 'host': '8.8.8.8', 'username': 'admin', 'os': 'windows'})
        self.assertEqual(self.server()['port'], 5985)

    def test_renaming_keeps_fingerprint_and_saved_password(self):
        self.add_server(host_key='ssh-ed25519 SHA256:abc', secret='blob')
        self.client.post('/edit/srv1/save/', {'name': 'renamed', 'host': '10.0.0.5', 'username': 'user'})
        s = self.server()
        self.assertEqual((s['name'], s['host_key'], s['secret']),
                         ('renamed', 'ssh-ed25519 SHA256:abc', 'blob'))

    def test_changing_host_clears_fingerprint_and_saved_password(self):
        self.add_server(host_key='ssh-ed25519 SHA256:abc', secret='blob')
        self.client.post('/edit/srv1/save/', {'name': 'test', 'host': '10.0.0.6', 'username': 'user'})
        self.assertNotIn('host_key', self.server())
        self.assertNotIn('secret', self.server())

    def test_changing_username_clears_only_the_saved_password(self):
        self.add_server(host_key='ssh-ed25519 SHA256:abc', secret='blob')
        self.client.post('/edit/srv1/save/', {'name': 'test', 'host': '10.0.0.5', 'username': 'other'})
        self.assertIn('host_key', self.server())
        self.assertNotIn('secret', self.server())

    def test_deleting_a_server_removes_its_projects_too(self):
        self.add_server()
        data = store.load()
        data['projects'] = [
            {'id': 'p1', 'server_id': 'srv1', 'name': 'a', 'path': '/x', 'start': 'y', 'update': ''},
            {'id': 'p2', 'server_id': 'other', 'name': 'b', 'path': '/x', 'start': 'y', 'update': ''},
        ]
        store.save(data)
        self.client.post('/delete/srv1/')
        data = store.load()
        self.assertEqual(data['servers'], [])
        self.assertEqual([p['id'] for p in data['projects']], ['p2'])


class DnsHelperLockTests(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        self.login()

    def refused(self, name, ip='8.8.8.8'):
        r = self.client.get('/dns/check/', {'name': name, 'ip': ip})
        self.assertTrue(r.context['error'], '%r / %r should be refused' % (name, ip))

    def test_main_domain_and_reserved_names_are_refused(self):
        for name in ('example.ir', 'www.example.ir', 'mail.example.ir'):
            self.refused(name)

    def test_private_ip_is_refused(self):
        self.refused('vps.example.ir', '127.0.0.1')


class WebSocketAuthTests(IsolatedTestCase):
    def scope(self, cookie=None):
        return {'headers': [(b'cookie', cookie.encode())] if cookie else []}

    def cookie(self):
        name = settings.SESSION_COOKIE_NAME
        return '%s=%s' % (name, self.client.cookies[name].value)

    def test_logged_in_browser_is_accepted(self):
        self.login()
        self.assertTrue(auth.scope_logged_in(self.scope(self.cookie())))

    def test_no_cookie_is_refused(self):
        self.assertFalse(auth.scope_logged_in(self.scope()))

    def test_garbage_cookie_is_refused(self):
        self.assertFalse(auth.scope_logged_in(self.scope('%s=garbage' % settings.SESSION_COOKIE_NAME)))

    def test_cookie_dies_after_restart(self):
        self.login()
        cookie = self.cookie()
        with mock.patch.object(auth, '_BOOT', 'another-process'):
            self.assertFalse(auth.scope_logged_in(self.scope(cookie)))
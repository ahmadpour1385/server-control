import paramiko

from services import auth, ssh, store
from .base import IsolatedTestCase


class FakeKey:
    def __init__(self, data):
        self.data = data

    def asbytes(self):
        return self.data

    def get_name(self):
        return 'ssh-ed25519'


class EncryptionTests(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        auth.set_password('panel password')
        auth.unlock('panel password')

    def test_round_trip(self):
        blob = auth.encrypt('S3cret-Value')
        self.assertNotIn('S3cret', blob)
        self.assertEqual(auth.decrypt(blob), 'S3cret-Value')

    def test_locked_vault_refuses(self):
        blob = auth.encrypt('S3cret-Value')
        auth._key = None
        with self.assertRaises(RuntimeError):
            auth.encrypt('x')
        self.assertIsNone(auth.decrypt(blob))

    def test_garbage_is_rejected(self):
        self.assertIsNone(auth.decrypt('not-a-valid-token'))

    def test_another_panel_password_cannot_decrypt(self):
        blob = auth.encrypt('S3cret-Value')
        auth.set_password('another password')
        auth.unlock('another password')
        self.assertIsNone(auth.decrypt(blob))


class SavedPasswordTests(IsolatedTestCase):
    def setUp(self):
        super().setUp()
        auth.set_password('panel password')
        auth.unlock('panel password')
        self.add_server()

    def test_saved_password_is_encrypted_on_disk_and_loads_back(self):
        ssh.save_secret('srv1', 'S3cret-Value')
        self.assertNotIn('S3cret-Value', store.FILE.read_text())
        ssh._passwords.clear()
        self.assertEqual(ssh.get_password('srv1'), 'S3cret-Value')

    def test_clear_secret(self):
        ssh.save_secret('srv1', 'S3cret-Value')
        ssh.clear_secret('srv1')
        ssh._passwords.clear()
        self.assertIsNone(ssh.get_password('srv1'))

    def test_typed_password_wins_over_saved_one(self):
        ssh.save_secret('srv1', 'saved')
        ssh.set_password('srv1', 'typed')
        self.assertEqual(ssh.get_password('srv1'), 'typed')


class HostKeyPinningTests(IsolatedTestCase):
    def pin(self, data=b'key-a', sid='srv1'):
        ssh._Pinned(sid).missing_host_key(None, 'host', FakeKey(data))

    def test_fingerprint_format(self):
        self.assertTrue(ssh.fingerprint(FakeKey(b'x')).startswith('ssh-ed25519 SHA256:'))

    def test_first_connection_pins_the_key(self):
        self.add_server()
        self.pin()
        self.assertTrue(store.load()['servers'][0]['host_key'].startswith('ssh-ed25519 SHA256:'))

    def test_same_key_is_accepted_again(self):
        self.add_server()
        self.pin()
        self.pin()

    def test_changed_key_is_refused_and_pin_stays(self):
        self.add_server()
        self.pin(b'key-a')
        pinned = store.load()['servers'][0]['host_key']
        with self.assertRaises(paramiko.SSHException):
            self.pin(b'key-b')
        self.assertEqual(store.load()['servers'][0]['host_key'], pinned)

    def test_unknown_server_is_refused(self):
        with self.assertRaises(paramiko.SSHException):
            self.pin()
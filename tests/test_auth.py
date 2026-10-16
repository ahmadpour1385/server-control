import time
from unittest import mock

from services import auth, store
from .base import IsolatedTestCase


class PasswordTests(IsolatedTestCase):
    def test_nothing_is_set_by_default(self):
        self.assertFalse(auth.is_set())
        self.assertFalse(auth.verify('anything'))

    def test_set_and_verify(self):
        auth.set_password('correct horse')
        self.assertTrue(auth.is_set())
        self.assertTrue(auth.verify('correct horse'))
        self.assertFalse(auth.verify('wrong'))

    def test_password_is_not_stored_in_plain_text(self):
        auth.set_password('correct horse')
        self.assertNotIn('correct horse', store.FILE.read_text())

    def test_each_password_gets_a_new_salt(self):
        auth.set_password('correct horse')
        first = store.load()['auth']['salt']
        auth.set_password('correct horse')
        self.assertNotEqual(first, store.load()['auth']['salt'])


class SessionTests(IsolatedTestCase):
    def test_valid_token_is_logged_in(self):
        auth.set_password('correct horse')
        self.assertTrue(auth.is_logged_in({'auth': auth.token()}))

    def test_wrong_or_missing_token_is_not_logged_in(self):
        auth.set_password('correct horse')
        for value in ('nope', None, 123, ''):
            self.assertFalse(auth.is_logged_in({'auth': value}))
        self.assertFalse(auth.is_logged_in({}))

    def test_nobody_is_logged_in_before_a_password_exists(self):
        self.assertFalse(auth.is_logged_in({'auth': 'x'}))

    def test_session_dies_after_restart(self):
        auth.set_password('correct horse')
        old = auth.token()
        with mock.patch.object(auth, '_BOOT', 'another-process'):
            self.assertFalse(auth.is_logged_in({'auth': old}))


class LockoutTests(IsolatedTestCase):
    def test_locks_after_five_failures(self):
        for _ in range(4):
            auth.fail()
        self.assertFalse(auth.locked())
        auth.fail()
        self.assertTrue(auth.locked())

    def test_old_failures_expire(self):
        auth._fails[:] = [time.time() - 400] * 5
        self.assertFalse(auth.locked())
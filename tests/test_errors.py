import socket

import paramiko
import requests
from django.test import SimpleTestCase
from services import errors


class ExplainTests(SimpleTestCase):
    def msg(self, exc):
        return errors.explain(exc)[0]

    def test_wrong_password(self):
        self.assertIn('پسورد', self.msg(paramiko.AuthenticationException('x')))

    def test_timeouts(self):
        for exc in (socket.timeout(), TimeoutError(), requests.exceptions.ReadTimeout('x')):
            self.assertIn('جواب نداد', self.msg(exc))

    def test_connection_refused(self):
        refused = paramiko.ssh_exception.NoValidConnectionsError(
            {('127.0.0.1', 22): ConnectionRefusedError()})
        for exc in (ConnectionRefusedError(), refused, requests.exceptions.ConnectionError('x')):
            self.assertIn('برقرار نشد', self.msg(exc))

    def test_unknown_host(self):
        self.assertIn('پیدا نشد', self.msg(socket.gaierror(-2, 'Name or service not known')))

    def test_connection_dropped(self):
        for exc in (ConnectionResetError(), EOFError(),
                    paramiko.SSHException('Error reading SSH protocol banner')):
            self.assertIn('قطع کرد', self.msg(exc))

    def test_changed_fingerprint(self):
        exc = paramiko.SSHException('WARNING: server fingerprint changed (possible attack).')
        self.assertIn('اثر انگشت', self.msg(exc))

    def test_unknown_error_keeps_technical_detail(self):
        message, detail = errors.explain(ValueError('boom'))
        self.assertTrue(message)
        self.assertIn('boom', detail)

    def test_detail_is_truncated(self):
        self.assertLessEqual(len(errors.explain(ValueError('x' * 1000))[1]), 300)
from django.test import SimpleTestCase
from services import dnscheck

IP = '8.8.8.8'


class ValidateTests(SimpleTestCase):
    def good(self, name, ip=IP):
        n, i, err = dnscheck.validate(name, ip)
        self.assertIsNone(err, err)
        return n, i

    def bad(self, name, ip=IP):
        _, _, err = dnscheck.validate(name, ip)
        self.assertIsNotNone(err, '%r / %r should be rejected' % (name, ip))

    def test_valid_subdomain(self):
        self.assertEqual(self.good('vps.example.ir'), ('vps.example.ir', IP))

    def test_normalizes_case_spaces_and_trailing_dot(self):
        self.assertEqual(self.good('  VPS.Example.IR.  ')[0], 'vps.example.ir')

    def test_main_domain_is_locked(self):
        self.bad('example.ir')

    def test_reserved_names_are_locked(self):
        for label in ('www', 'mail', 'webmail', 'cpanel', 'ns1', 'ns2', 'ftp'):
            self.bad('%s.example.ir' % label)

    def test_invalid_names(self):
        for name in ('', 'bad name.example.ir', 'vps_.example.ir', 'vps..example.ir',
                     '-vps.example.ir', 'vps.example.123'):
            self.bad(name)

    def test_non_public_ips_are_rejected(self):
        for ip in ('127.0.0.1', '10.0.0.1', '192.168.1.10', '172.16.0.1',
                   '169.254.1.1', '0.0.0.0'):
            self.bad('vps.example.ir', ip)

    def test_ipv6_and_garbage_ips_are_rejected(self):
        for ip in ('2001:4860:4860::8888', 'abc', '999.1.1.1', ''):
            self.bad('vps.example.ir', ip)


class VerdictTests(SimpleTestCase):
    def test_ok_when_all_name_servers_agree(self):
        self.assertEqual(dnscheck.verdict({'ns1': [IP], 'ns2': [IP]}, IP), 'ok')

    def test_ok_even_if_one_name_server_timed_out(self):
        self.assertEqual(dnscheck.verdict({'ns1': [IP], 'ns2': None}, IP), 'ok')

    def test_missing_when_no_record_exists(self):
        self.assertEqual(dnscheck.verdict({'ns1': [], 'ns2': []}, IP), 'missing')

    def test_wrong_when_ip_differs(self):
        self.assertEqual(dnscheck.verdict({'ns1': ['1.1.1.1']}, IP), 'wrong')

    def test_inconsistent_name_servers_count_as_wrong(self):
        self.assertEqual(dnscheck.verdict({'ns1': [IP], 'ns2': []}, IP), 'wrong')

    def test_unknown_when_nothing_answered(self):
        self.assertEqual(dnscheck.verdict({'ns1': None}, IP), 'unknown')
        self.assertEqual(dnscheck.verdict({}, IP), 'unknown')
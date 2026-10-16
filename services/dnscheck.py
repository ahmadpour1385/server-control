import ipaddress
import re
import socket

import dns.exception
import dns.resolver

HOST_RE = re.compile(r'^(?=.{1,253}$)([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$')
LOCKED_LABELS = {'www', 'mail', 'webmail', 'cpanel', 'whm', 'ftp', 'smtp', 'imap', 'pop',
                 'ns1', 'ns2', 'autodiscover', 'autoconfig', 'webdisk'}


def validate(name, ip):
    name = name.strip().lower().rstrip('.')
    if not HOST_RE.match(name):
        return None, None, 'اسم ساب‌دامین معتبر نیست'
    labels = name.split('.')
    if len(labels) < 3:
        return None, None, 'فقط ساب‌دامین مجازه (مثلاً vps.example.ir)، نه خود دامنه اصلی'
    if labels[0] in LOCKED_LABELS:
        return None, None, 'این اسم قفله: ' + labels[0]
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return None, None, 'IP معتبر نیست'
    if addr.version != 4 or not addr.is_global:
        return None, None, 'IP باید یه IPv4 عمومی باشه (نه 127.x یا 192.168.x و...)'
    return name, str(addr), None


def _resolver(nameservers=None):
    r = dns.resolver.Resolver(configure=nameservers is None)
    r.lifetime = 5
    if nameservers:
        r.nameservers = nameservers
    return r


def _a(resolver, name):
    try:
        return sorted(rd.to_text() for rd in resolver.resolve(name, 'A'))
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return []
    except (dns.resolver.NoNameservers, dns.exception.Timeout):
        return None


def a_records(name):
    return _a(_resolver(), name)


def authoritative(name):
    """از خود نیم‌سرورهای رسمی دامنه می‌پرسه (بدون کش)."""
    labels = name.split('.')
    sysr = _resolver()
    for i in range(1, len(labels) - 1):
        zone = '.'.join(labels[i:])
        try:
            ns_names = [rd.to_text() for rd in sysr.resolve(zone, 'NS')]
        except Exception:
            continue
        results = {}
        for ns in ns_names:
            ips = _a(sysr, ns)
            if not ips:
                continue
            results[ns.rstrip('.')] = _a(_resolver(ips[:1]), name)
        return zone, results
    return None, {}


def verdict(auth, ip):
    vals = [v for v in auth.values() if v is not None]
    if not vals:
        return 'unknown'
    if all(v == [ip] for v in vals):
        return 'ok'
    if all(not v for v in vals):
        return 'missing'
    return 'wrong'


def port_open(ip, port):
    try:
        with socket.create_connection((ip, port), timeout=3):
            return True
    except OSError:
        return False
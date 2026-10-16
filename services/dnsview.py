import dns.exception
import dns.resolver

TYPES = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS', 'SOA', 'CAA']


def lookup(name):
    r = dns.resolver.Resolver()
    r.lifetime = 5
    rows = []
    for t in TYPES:
        try:
            ans = r.resolve(name, t)
            for rd in ans:
                rows.append({'type': t, 'value': rd.to_text(), 'ttl': ans.rrset.ttl})
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.resolver.NoNameservers):
            continue
        except dns.exception.Timeout:
            rows.append({'type': t, 'value': 'timeout', 'ttl': ''})
    return rows
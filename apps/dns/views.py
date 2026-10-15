import re

from django.shortcuts import render
from services import store, dnsview, dnscheck

NAME_RE = re.compile(r'^[A-Za-z0-9._-]+$')


def page(request):
    data = store.load()
    return render(request, 'dns/page.html',
                  {'name': data.get('dns_name', ''), 'servers': data['servers']})


def lookup(request):
    name = request.GET.get('name', '').strip().lower().rstrip('.')
    if not NAME_RE.match(name) or '.' not in name:
        return render(request, 'dns/_result.html', {'error': 'اسم دامنه معتبر نیست'})
    data = store.load()
    data['dns_name'] = name
    store.save(data)
    return render(request, 'dns/_result.html', {'name': name, 'rows': dnsview.lookup(name)})


def check(request):
    name, ip, error = dnscheck.validate(request.GET.get('name', ''), request.GET.get('ip', ''))
    if error:
        return render(request, 'dns/_check.html', {'error': error})
    zone, auth = dnscheck.authoritative(name)
    ctx = {
        'name': name,
        'ip': ip,
        'zone': zone,
        'auth': auth,
        'mine': dnscheck.a_records(name),
        'verdict': dnscheck.verdict(auth, ip),
        'ports': [(p, dnscheck.port_open(ip, p)) for p in (22, 80, 443)],
    }
    return render(request, 'dns/_check.html', ctx)
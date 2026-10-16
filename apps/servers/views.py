import uuid

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from services import store, ssh, psrp


def _find(data, sid):
    return next((s for s in data['servers'] if s['id'] == sid), None)


def _list(request, data):
    return render(request, 'servers/_list.html', {'servers': data['servers']})


def index(request):
    return render(request, 'servers/index.html', {'servers': store.load()['servers']})


def server_list(request):
    return _list(request, store.load())


@require_POST
def add(request):
    data = store.load()
    data['servers'].append({
        'id': uuid.uuid4().hex[:8],
        'name': request.POST['name'],
        'host': request.POST['host'],
        'port': int(request.POST.get('port') or (5985 if request.POST.get('os') == 'windows' else 22)),
        'username': request.POST['username'],
        'os': request.POST.get('os', 'linux'),
    })
    store.save(data)
    return _list(request, data)


@require_POST
def delete(request, sid):
    data = store.load()
    data['servers'] = [s for s in data['servers'] if s['id'] != sid]
    data['projects'] = [p for p in data.get('projects', []) if p['server_id'] != sid]
    store.save(data)
    ssh.forget(sid)
    psrp.forget(sid)
    return _list(request, data)


@require_POST
def reset_key(request, sid):
    data = store.load()
    s = _find(data, sid)
    if s:
        s.pop('host_key', None)
        store.save(data)
    ssh.forget(sid)
    return _list(request, data)


def edit_form(request, sid):
    s = _find(store.load(), sid)
    if not s:
        return HttpResponse(status=404)
    return render(request, 'servers/_edit.html', {'s': s})


@require_POST
def edit_save(request, sid):
    data = store.load()
    s = _find(data, sid)
    if not s:
        return HttpResponse(status=404)
    old = (s['host'], s['port'], s['username'])
    s['name'] = request.POST['name'].strip()
    s['host'] = request.POST['host'].strip()
    s['port'] = int(request.POST.get('port') or (5985 if s['os'] == 'windows' else 22))
    s['username'] = request.POST['username'].strip()
    new = (s['host'], s['port'], s['username'])
    if new != old:
        if new[:2] != old[:2]:
            s.pop('host_key', None)
        s.pop('secret', None)
        ssh.forget(sid)
        psrp.forget(sid)
    store.save(data)
    return _list(request, data)
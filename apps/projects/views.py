import shlex
import uuid

from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from services import store, ssh

NEED_CONNECT = 'اول توی صفحه اصلی دکمه 🔌 اتصال رو بزن و پسورد بده.'
ALIVE = 'kill -0 $(cat .panel.pid 2>/dev/null) 2>/dev/null'


def _server(sid):
    return next((s for s in store.load()['servers'] if s['id'] == sid), None)


def _project(pid):
    return next((p for p in store.load().get('projects', []) if p['id'] == pid), None)


def _run(s, cmd, timeout=15):
    if s['os'] != 'linux':
        return 'پشتیبانی ویندوز بعداً اضافه می‌شه 🪟'
    if ssh.get_password(s['id']) is None:
        return NEED_CONNECT
    try:
        return ssh.run(s, cmd, timeout).strip() or '(بدون خروجی)'
    except Exception as e:
        return 'Error: ' + (str(e) or repr(e))


def _cd(p):
    return 'cd %s || { echo "folder not found"; exit 1; }; ' % shlex.quote(p['path'])


def _list(request, s):
    projects = [p for p in store.load().get('projects', []) if p['server_id'] == s['id']]
    return render(request, 'projects/_list.html', {'s': s, 'projects': projects})


def page(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    projects = [p for p in store.load().get('projects', []) if p['server_id'] == sid]
    return render(request, 'projects/page.html', {'s': s, 'projects': projects})


@require_POST
def add(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    data = store.load()
    data.setdefault('projects', []).append({
        'id': uuid.uuid4().hex[:8],
        'server_id': sid,
        'name': request.POST['name'].strip(),
        'path': request.POST['path'].strip(),
        'start': request.POST['start'].strip(),
        'update': request.POST.get('update', '').strip(),
    })
    store.save(data)
    return _list(request, s)


@require_POST
def delete(request, pid):
    p = _project(pid)
    if not p:
        return HttpResponse(status=404)
    data = store.load()
    data['projects'] = [x for x in data['projects'] if x['id'] != pid]
    store.save(data)
    return _list(request, _server(p['server_id']))


def status(request, pid):
    p = _project(pid)
    if not p:
        return HttpResponse(status=404)
    s = _server(p['server_id'])
    cmd = 'cd %s 2>/dev/null && (%s && echo RUNNING || echo STOPPED) || echo STOPPED' % (
        shlex.quote(p['path']), ALIVE)
    return render(request, 'projects/_status.html', {'state': _run(s, cmd)})


@require_POST
def action(request, pid, act):
    p = _project(pid)
    if not p:
        return HttpResponse(status=404)
    s = _server(p['server_id'])
    timeout = 15
    cmd = None

    if act == 'start':
        inner = 'echo $$ > .panel.pid; ' + p['start']
        cmd = (_cd(p)
               + 'if %s; then echo "already running"; exit 0; fi; ' % ALIVE
               + '(setsid bash -c %s > .panel.log 2>&1 < /dev/null &); ' % shlex.quote(inner)
               + 'sleep 1; if %s; then echo "started"; '
                 'else echo "failed"; tail -n 20 .panel.log; fi' % ALIVE)
    elif act == 'stop':
        cmd = (_cd(p)
               + 'PID=$(cat .panel.pid 2>/dev/null); '
               + 'if [ -n "$PID" ] && kill -0 $PID 2>/dev/null; then '
                 'kill -TERM -- -$PID 2>/dev/null || kill -TERM $PID; sleep 1; echo stopped; '
                 'else echo "not running"; fi; rm -f .panel.pid')
    elif act == 'update':
        if p.get('update'):
            cmd = _cd(p) + p['update'] + ' 2>&1'
            timeout = 180
        else:
            out = 'دستور آپدیت برای این پروژه تعریف نشده'
    elif act == 'logs':
        cmd = _cd(p) + 'tail -n 50 .panel.log 2>&1'
    else:
        return HttpResponse(status=404)

    if cmd:
        out = _run(s, cmd, timeout)
    resp = render(request, 'projects/_output.html', {'out': out})
    if act in ('start', 'stop'):
        resp['HX-Trigger'] = 'refresh-status'
    return resp
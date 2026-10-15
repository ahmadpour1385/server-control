import asyncio
import posixpath
import stat
from datetime import datetime

from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_POST
from services import store, ssh

NEED_CONNECT = 'اول توی صفحه اصلی دکمه 🔌 اتصال رو بزن و پسورد بده.'


def _server(sid):
    return next((s for s in store.load()['servers'] if s['id'] == sid), None)


def _do(s, fn):
    """fn(sftp) رو اجرا می‌کنه؛ اگه ارور داد متنش رو برمی‌گردونه."""
    if s['os'] != 'linux':
        return 'پشتیبانی ویندوز بعداً اضافه می‌شه 🪟'
    if ssh.get_password(s['id']) is None:
        return NEED_CONNECT
    try:
        sftp = ssh.sftp(s)
        try:
            fn(sftp)
        finally:
            sftp.close()
    except Exception as e:
        return str(e) or repr(e)
    return None


def _listing(request, s, path=None, error=None, full=False):
    box = {}

    def work(sftp):
        p = path or sftp.normalize('.')
        items = []
        for a in sftp.listdir_attr(p):
            items.append({
                'name': a.filename,
                'path': posixpath.join(p, a.filename),
                'is_dir': stat.S_ISDIR(a.st_mode),
                'size': a.st_size,
                'mtime': datetime.fromtimestamp(a.st_mtime),
            })
        items.sort(key=lambda i: (not i['is_dir'], i['name'].lower()))
        box.update(path=p, items=items)

    err = _do(s, work)
    p = box.get('path') or path or ''
    ctx = {
        's': s,
        'path': p,
        'items': box.get('items', []),
        'parent': posixpath.dirname(p.rstrip('/')) or '/' if p and p != '/' else None,
        'error': error or err,
    }
    return render(request, 'files/page.html' if full else 'files/_list.html', ctx)


def browse(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    full = request.headers.get('HX-Request') != 'true'
    return _listing(request, s, request.GET.get('path'), full=full)


def download(request, sid):
    s = _server(sid)
    path = request.GET.get('path', '')
    if not s or ssh.get_password(sid) is None:
        return HttpResponse(NEED_CONNECT, status=400)
    try:
        sftp = ssh.sftp(s)
        size = sftp.stat(path).st_size
        f = sftp.open(path, 'rb')
    except Exception as e:
        return HttpResponse(f'Error: {e}', status=400)

    async def gen():
        try:
            while True:
                chunk = await asyncio.to_thread(f.read, 65536)
                if not chunk:
                    break
                yield chunk
        finally:
            f.close()
            sftp.close()

    resp = StreamingHttpResponse(gen(), content_type='application/octet-stream')
    resp['Content-Length'] = size
    resp['Content-Disposition'] = content_disposition_header(True, posixpath.basename(path))
    return resp


@require_POST
def upload(request, sid):
    s = _server(sid)
    path = request.POST['path']
    f = request.FILES.get('file')
    if not f:
        return _listing(request, s, path, 'فایلی انتخاب نشد')
    err = _do(s, lambda sftp: sftp.putfo(f, posixpath.join(path, f.name)))
    return _listing(request, s, path, err)


@require_POST
def mkdir(request, sid):
    s = _server(sid)
    path = request.POST['path']
    name = request.POST['name'].strip()
    if not name or '/' in name:
        return _listing(request, s, path, 'اسم پوشه معتبر نیست')
    err = _do(s, lambda sftp: sftp.mkdir(posixpath.join(path, name)))
    return _listing(request, s, path, err)


@require_POST
def delete(request, sid):
    s = _server(sid)
    path = request.POST['path']

    def work(sftp):
        if stat.S_ISDIR(sftp.stat(path).st_mode):
            sftp.rmdir(path)
        else:
            sftp.remove(path)

    err = _do(s, work)
    if err and err != NEED_CONNECT:
        err = f'حذف نشد (پوشه‌ها فقط وقتی خالی باشن حذف می‌شن): {err}'
    return _listing(request, s, posixpath.dirname(path) or '/', err)
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from services import store, ssh, psrp, history

CMD = (
    "hostname; uptime -p; "
    "free -m | awk 'NR==2{print $3\"/\"$2}'; "
    "cut -d' ' -f1-3 /proc/loadavg; "
    "df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'; "
    "head -1 /proc/stat"
)

WIN_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$os = Get-CimInstance Win32_OperatingSystem
$up = (Get-Date) - $os.LastBootUpTime
$total = [int]($os.TotalVisibleMemorySize / 1024)
$used = $total - [int]($os.FreePhysicalMemory / 1024)
$cpu = [int](Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
$d = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$du = [math]::Round(($d.Size - $d.FreeSpace) / 1GB, 1)
$dt = [math]::Round($d.Size / 1GB, 1)
$env:COMPUTERNAME
"up {0}d {1}h {2}m" -f $up.Days, $up.Hours, $up.Minutes
"$used/$total"
"$cpu%"
"$du GB / $dt GB"
'''

KEYS = ['hostname', 'uptime', 'ram', 'load', 'disk', 'cpu_raw']


def _server(sid):
    return next((s for s in store.load()['servers'] if s['id'] == sid), None)


def _fetch(s):
    text = psrp.run(s, WIN_SCRIPT) if s['os'] == 'windows' else ssh.run(s, CMD)
    return [x.strip() for x in text.strip().splitlines()]


def _render_info(request, s, save_pw=None):
    if ssh.get_password(s['id']) is None:
        return render(request, 'monitor/_login.html', {'s': s})
    try:
        info = dict(zip(KEYS, _fetch(s)))
        history.add(s['id'], info)
        if save_pw:
            try:
                ssh.save_secret(s['id'], save_pw)
                s['secret'] = True
            except RuntimeError:
                pass
    except Exception as e:
        ssh.forget(s['id'])
        psrp.forget(s['id'])
        return render(request, 'monitor/_login.html',
                      {'s': s, 'error': (str(e) or repr(e))[:300]})
    return render(request, 'monitor/_info.html',
                  {'s': s, 'info': info, 'charts': history.charts(s['id'])})


def info(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    return _render_info(request, s)


@require_POST
def connect(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    pw = request.POST['password']
    ssh.set_password(sid, pw)
    return _render_info(request, s, save_pw=pw if request.POST.get('save') else None)


@require_POST
def forget_saved(request, sid):
    s = _server(sid)
    if not s:
        return HttpResponse(status=404)
    ssh.clear_secret(sid)
    ssh.forget(sid)
    psrp.forget(sid)
    s.pop('secret', None)
    return render(request, 'monitor/_login.html', {'s': s})
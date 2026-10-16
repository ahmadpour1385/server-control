import time
from collections import deque

MAXLEN = 100  # حدود ۵ دقیقه با پولینگ هر ۳ ثانیه
WIDTH, HEIGHT = 300, 60

_data = {}
_prev_cpu = {}


def add(sid, info):
    ram = None
    try:
        used, total = (float(x) for x in info['ram'].split('/'))
        ram = used / total * 100
    except Exception:
        pass

    cpu = None
    if 'cpu_raw' in info:  # لینوکس: از /proc/stat
        try:
            nums = [int(x) for x in info['cpu_raw'].split()[1:9]]
            total_c, idle_c = sum(nums), nums[3] + nums[4]
            prev = _prev_cpu.get(sid)
            _prev_cpu[sid] = (total_c, idle_c)
            if prev and total_c > prev[0]:
                cpu = (1 - (idle_c - prev[1]) / (total_c - prev[0])) * 100
        except Exception:
            pass
    else:  # ویندوز: درصد آماده
        try:
            cpu = float(info['load'].rstrip('%'))
        except Exception:
            pass

    _data.setdefault(sid, deque(maxlen=MAXLEN)).append({'cpu': cpu, 'ram': ram, 't': time.time()})


def _points(values):
    n = len(values)
    if n < 2:
        return ''
    step = WIDTH / (MAXLEN - 1)
    pts = []
    for i, v in enumerate(values):
        x = WIDTH - (n - 1 - i) * step
        y = HEIGHT - max(0.0, min(100.0, v)) / 100 * HEIGHT
        pts.append('%.1f,%.1f' % (x, y))
    return ' '.join(pts)


def _chart(sid, key):
    vals = [p[key] for p in _data.get(sid, []) if p[key] is not None]
    if not vals:
        return None
    return {
        'points': _points(vals),
        'now': round(vals[-1]),
        'avg': round(sum(vals) / len(vals)),
        'max': round(max(vals)),
    }


def charts(sid):
    return {'cpu': _chart(sid, 'cpu'), 'ram': _chart(sid, 'ram')}
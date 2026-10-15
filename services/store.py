import json
from pathlib import Path
from django.conf import settings

FILE = Path(settings.BASE_DIR) / 'panel_data' / 'settings.json'


def load():
    data = json.loads(FILE.read_text(encoding='utf-8')) if FILE.exists() else {}
    data.setdefault('servers', [])
    return data


def save(data):
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
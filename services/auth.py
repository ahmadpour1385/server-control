import base64
import hashlib
import hmac
import secrets
import time
from http.cookies import SimpleCookie

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from services import store

ITER = 600_000
_fails = []
_BOOT = secrets.token_hex(8)  # با هر ری‌استارت عوض می‌شه
_key = None  # کلید رمزنگاری، فقط توی رم


def is_set():
    return 'auth' in store.load()


def set_password(pw):
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(salt), ITER).hex()
    data = store.load()
    data['auth'] = {'salt': salt, 'hash': h}
    store.save(data)


def verify(pw):
    a = store.load().get('auth')
    if not a:
        return False
    h = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(a['salt']), ITER).hex()
    return hmac.compare_digest(h, a['hash'])


def token():
    a = store.load().get('auth')
    return a['hash'][:16] + _BOOT if a else None


def is_logged_in(session):
    t = token()
    s = session.get('auth')
    return t is not None and isinstance(s, str) and hmac.compare_digest(s, t)


def locked():
    now = time.time()
    _fails[:] = [t for t in _fails if now - t < 300]
    return len(_fails) >= 5


def fail():
    _fails.append(time.time())


def unlock(pw):
    """بعد از ورود موفق صدا زده می‌شه و کلید رمزنگاری رو توی رم می‌سازه."""
    global _key
    data = store.load()
    a = data['auth']
    if 'vault_salt' not in a:
        a['vault_salt'] = secrets.token_hex(16)
        store.save(data)
    raw = hashlib.pbkdf2_hmac('sha256', pw.encode(), bytes.fromhex(a['vault_salt']), ITER, dklen=32)
    _key = Fernet(base64.urlsafe_b64encode(raw))


def encrypt(text):
    if _key is None:
        raise RuntimeError('vault locked')
    return _key.encrypt(text.encode()).decode()


def decrypt(blob):
    if _key is None:
        return None
    try:
        return _key.decrypt(blob.encode()).decode()
    except InvalidToken:
        return None


def scope_logged_in(scope):
    """برای WebSocket: چک می‌کنه کوکی سشن معتبر و واردشده باشه."""
    from django.contrib.sessions.backends.signed_cookies import SessionStore
    raw = dict(scope.get('headers', [])).get(b'cookie', b'').decode()
    c = SimpleCookie()
    c.load(raw)
    m = c.get(settings.SESSION_COOKIE_NAME)
    if not m:
        return False
    return is_logged_in(SessionStore(session_key=m.value))
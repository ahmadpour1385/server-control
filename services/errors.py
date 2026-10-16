import socket

import paramiko
import requests

try:
    from pypsrp.exceptions import AuthenticationError as PSAuthError
except ImportError:  # pragma: no cover
    PSAuthError = ()


def explain(e):
    """یه خطای فنی رو به (پیام قابل‌فهم، جزئیات فنی) تبدیل می‌کنه."""
    detail = (str(e) or repr(e))[:300]
    if isinstance(e, (paramiko.AuthenticationException, PSAuthError)):
        msg = 'یوزرنیم یا پسورد اشتباهه.'
    elif isinstance(e, paramiko.SSHException) and 'fingerprint changed' in detail:
        msg = ('اثر انگشت سرور با دفعه قبل فرق داره. اگه سرور رو دوباره نصب نکردی، '
               'این می‌تونه نشونه حمله باشه و نباید وصل بشی. اگه نصب کردی، «ریست اثر انگشت» رو بزن.')
    elif isinstance(e, socket.gaierror):
        msg = 'آدرس سرور پیدا نشد. IP یا اسم دامنه رو چک کن.'
    elif isinstance(e, (TimeoutError, requests.exceptions.Timeout)):
        msg = 'سرور جواب نداد (تایم‌اوت). آدرس، پورت و فایروال رو چک کن.'
    elif isinstance(e, (EOFError, ConnectionResetError)) or (
            isinstance(e, paramiko.SSHException)
            and ('banner' in detail.lower() or 'reset' in detail.lower())):
        msg = 'سرور وسط اتصال رو قطع کرد. سرویس SSH روی سرور رو چک کن.'
    elif isinstance(e, (ConnectionRefusedError, paramiko.ssh_exception.NoValidConnectionsError,
                        requests.exceptions.ConnectionError)):
        msg = 'اتصال برقرار نشد. پورت بسته‌ست یا سرویس SSH/WinRM روی سرور روشن نیست.'
    else:
        msg = 'اتصال انجام نشد.'
    return msg, detail
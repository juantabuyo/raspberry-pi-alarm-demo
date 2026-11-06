"""Optional Telegram messages; disabled unless explicitly enabled by the caller.

Credentials are read from the environment. Never print a token, recipient,
request URL or exception text which could contain one. Tests replace urlopen;
the simulation always disables notification delivery.
"""
import html
import json
import os
import threading
from time import strftime
import urllib.parse
import urllib.request

_enabled = False
TIMEOUT_SECONDS = 5


def configure(enabled=False):
    global _enabled
    _enabled = bool(enabled)


def _credentials():
    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()
    if not token or not chat_id or token.startswith('EXAMPLE_') or chat_id.startswith('EXAMPLE_'):
        return None
    return token, chat_id


def send_message(text):
    """Start one bounded-time background request, or return None if disabled."""
    credentials = _credentials() if _enabled else None
    if credentials is None:
        print('[Telegram] Disabled or unconfigured; no request sent.')
        return None
    token, chat_id = credentials

    def send():
        try:
            url = f'https://api.telegram.org/bot{token}/sendMessage'
            data = urllib.parse.urlencode({'chat_id': chat_id, 'text': text,
                                           'parse_mode': 'HTML'}).encode('utf-8')
            request = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read())
                if response.status == 200 and payload.get('ok') is True:
                    print('[Telegram] Message accepted by the API.')
                else:
                    print('[Telegram] Request did not confirm delivery.')
        except Exception as error:
            # HTTPError/URLError text may include the credential-bearing URL.
            print(f'[Telegram] Request failed ({type(error).__name__}); details suppressed.')

    worker = threading.Thread(target=send, daemon=True, name='telegram-notification')
    worker.start()
    return worker


def send_alert(triggered_sensor='unknown'):
    timestamp = strftime('%Y-%m-%d %H:%M:%S')
    return send_message(f'<b>ALARM ACTIVE</b>\nTime: {timestamp}\n'
                        f'Sensor: {html.escape(triggered_sensor)}\nCheck the demo system.')


def send_state(state):
    return send_message(f'System state: <b>{html.escape(state)}</b> ({strftime("%H:%M:%S")})')

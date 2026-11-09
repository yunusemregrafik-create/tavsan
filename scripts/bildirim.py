"""Tavşan scheduled FCM sender. Secret stays in GitHub Actions Secrets."""
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import firebase_admin
from firebase_admin import credentials, firestore, messaging
from google.api_core.exceptions import AlreadyExists

secret = os.environ.get('FIREBASE_SERVICE_ACCOUNT', '')
if not secret:
    raise SystemExit('FIREBASE_SERVICE_ACCOUNT secret is missing')
try:
    service_account = json.loads(secret)
except json.JSONDecodeError:
    raise SystemExit('FIREBASE_SERVICE_ACCOUNT must contain the JSON content, not a file path')

firebase_admin.initialize_app(credentials.Certificate(service_account))
db = firestore.client()
now = datetime.now(ZoneInfo('Europe/Istanbul'))
today = now.date().isoformat()
weekday = now.weekday()


def slot_due(hhmm):
    try:
        h, m = map(int, hhmm.split(':'))
        scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
        # Github Actions can start late; allow up to 19 minutes after scheduled time.
        return timedelta(0) <= now - scheduled < timedelta(minutes=20)
    except (ValueError, AttributeError):
        return False


def send_once(uid, device_id, token, kind, title, body):
    # Atomically claim the notification so concurrent scheduled runs don't duplicate it.
    key = f'{today}-{kind}-{device_id}'
    marker = db.collection('users').document(uid).collection('sentNotifications').document(key)
    try:
        marker.create({'at': firestore.SERVER_TIMESTAMP, 'kind': kind})
    except AlreadyExists:
        return
    try:
        messaging.send(messaging.Message(
            token=token,
            data={'title': title, 'body': body, 'tag': f'tavsan-{kind}-{today}'},
            webpush=messaging.WebpushConfig(headers={'TTL': '3600'})
        ))
        print(f'Sent {kind} to user {uid[:7]}...')
    except Exception as exc:
        # Allow a later run to retry transient failures.
        marker.delete()
        print(f'Failed {kind} for user {uid[:7]}...: {type(exc).__name__}')


for user in db.collection('users').stream():
    uid = user.id
    main = db.collection('users').document(uid).collection('data').document('main').get()
    if not main.exists:
        continue
    data = main.to_dict() or {}
    prefs = data.get('prefs') or {}
    records = data.get('records') or []
    open_items = [r for r in records if isinstance(r, dict) and r.get('status') != 'Tamamlandı' and r.get('type') in ('gorev', 'toplanti')]
    due = [r for r in open_items if r.get('due') == today]
    overdue = [r for r in open_items if isinstance(r.get('due'), str) and r['due'] < today]
    morning = prefs.get('morning') or '08:30'
    should_morning = slot_due(morning) and (weekday < 5 or prefs.get('weekend', False))
    # Date-only tasks and meetings: reminder at 09:00; no invented event start time.
    should_due = slot_due('09:00') and bool(due)
    if not (should_morning or should_due):
        continue
    tone = prefs.get('pushTone', 'islami')
    if tone == 'sade':
        title = 'Tavşan · Günlük özet'
        body = f'Bugün {len(due)} işin, geciken {len(overdue)} işin var.'
    elif tone == 'neseli':
        title = '🐰 Günaydın!'
        body = f'Bugün {len(due)} iş seni bekliyor! Geciken: {len(overdue)}.'
    else:
        title = '🌸 Hayırlı sabahlar!'
        body = f'Rabbim işlerini kolaylaştırsın. Bugün {len(due)} vazifen, geciken {len(overdue)} işin var.'
    for device in db.collection('users').document(uid).collection('pushTokens').stream():
        token_data = device.to_dict() or {}
        token = token_data.get('token')
        if not token or not token_data.get('enabled', True):
            continue
        if should_morning:
            send_once(uid, device.id, token, 'morning', title, body)
        if should_due:
            names = ', '.join(str(r.get('title') or 'Başlıksız')[:60] for r in due[:3])
            send_once(uid, device.id, token, 'due', '🌷 Bugünkü görev ve toplantıların', names + ('…' if len(due) > 3 else ''))

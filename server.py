#!/usr/bin/env python3
"""Fly Dubai Token Queue — shared local server.

Holds one authoritative queue in memory (persisted to state.json) and serves
the three static pages. All mutations are atomic server-side operations so
phone registrations and PC admin actions never clobber each other.

Run:  python3 server.py
Then open from any device on the same Wi-Fi:
  http://<this-mac-ip>:8753/patient.html
  http://<this-mac-ip>:8753/admin.html
  http://<this-mac-ip>:8753/display.html
"""
import json, os, threading
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

# Dubai is UTC+4 year-round (no daylight saving), so a fixed offset is safe.
DUBAI = timezone(timedelta(hours=4))

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_FILE = os.path.join(HERE, 'state.json')
PORT = int(os.environ.get('PORT', 8753))  # Render/Railway/Fly inject PORT
LOCK = threading.Lock()
DEFAULT_NAME = 'Fly Dubai'


def today_str():
    return datetime.now(DUBAI).strftime('%Y-%m-%d')


def now_time():
    return datetime.now(DUBAI).strftime('%I:%M %p').lstrip('0')


def fresh_state(name=DEFAULT_NAME):
    return {
        'date': today_str(), 'nextId': 1, 'tokens': [], 'queue': [],
        'pending': [], 'currentToken': None, 'servedCount': 0,
        'hospitalName': name or DEFAULT_NAME,
    }


def save_state(s):
    with open(STATE_FILE, 'w') as f:
        json.dump(s, f)


def load_state():
    """Load state, performing the daily reset if the stored date is stale."""
    try:
        with open(STATE_FILE) as f:
            s = json.load(f)
    except Exception:
        s = None
    if not s or s.get('date') != today_str():
        name = s.get('hospitalName') if s else DEFAULT_NAME
        s = fresh_state(name)
        save_state(s)
    s.setdefault('hospitalName', DEFAULT_NAME)
    return s


def find(s, tid):
    for t in s['tokens']:
        if t['id'] == tid:
            return t
    return None


def reorder_emergency(s):
    emerg = [i for i in s['queue'] if (find(s, i) or {}).get('purpose') == 'emergency']
    if emerg:
        s['queue'] = emerg + [i for i in s['queue'] if i not in emerg]


def do_register(s, d):
    t = {
        'id': s['nextId'],
        'name': (d.get('name') or '').strip(),
        'phone': d.get('phone') or '',
        'purpose': d.get('purpose') or '',
        'feedback': (d.get('feedback') or '').strip(),
        'feedbackType': d.get('feedbackType') or '',
        'status': 'waiting',
        'registeredAt': now_time(),
        'calledAt': None, 'doneAt': None, 'reviewed': False,
    }
    s['tokens'].append(t)
    if t['purpose'] == 'emergency':
        s['queue'].insert(0, t['id'])
    else:
        s['queue'].append(t['id'])
    s['nextId'] += 1
    reorder_emergency(s)
    ahead = s['queue'].index(t['id']) if t['id'] in s['queue'] else 0
    return t, ahead


def do_op(s, op, d):
    if op == 'call-next':
        if s['currentToken'] is not None:
            cur = find(s, s['currentToken'])
            if cur and cur['status'] == 'serving':
                cur['status'] = 'done'; cur['doneAt'] = now_time(); s['servedCount'] += 1
        reorder_emergency(s)
        if not s['queue']:
            s['currentToken'] = None
        else:
            nid = s['queue'].pop(0)
            t = find(s, nid)
            if t:
                t['status'] = 'serving'; t['calledAt'] = now_time()
            s['currentToken'] = nid
    elif op == 'mark-done':
        if s['currentToken'] is not None:
            t = find(s, s['currentToken'])
            if t:
                t['status'] = 'done'; t['doneAt'] = now_time(); s['servedCount'] += 1
            s['currentToken'] = None
    elif op == 'skip-current':
        if s['currentToken'] is not None:
            t = find(s, s['currentToken'])
            if t:
                t['status'] = 'pending'
                if t['id'] not in s['pending']:
                    s['pending'].append(t['id'])
            s['currentToken'] = None
    elif op == 'skip-queued':
        i = d.get('id')
        s['queue'] = [x for x in s['queue'] if x != i]
        t = find(s, i)
        if t:
            t['status'] = 'pending'
            if i not in s['pending']:
                s['pending'].append(i)
    elif op == 'reinsert':
        i = d.get('id'); mode = d.get('mode'); pos = d.get('pos')
        s['pending'] = [x for x in s['pending'] if x != i]
        t = find(s, i)
        if t:
            t['status'] = 'waiting'
        if mode in ('next', 'after'):
            s['queue'].insert(0, i)
        elif mode == 'pos':
            try:
                idx = max(0, min(len(s['queue']), int(pos) - 1))
            except Exception:
                idx = len(s['queue'])
            s['queue'].insert(idx, i)
        else:  # 'end' or unknown
            s['queue'].append(i)
    elif op == 'mark-reviewed':
        t = find(s, d.get('id'))
        if t:
            t['reviewed'] = True
    elif op == 'set-name':
        n = (d.get('name') or '').strip()
        if n:
            s['hospitalName'] = n
    elif op == 'reset':
        s = fresh_state(s.get('hospitalName', DEFAULT_NAME))
    return s


class Handler(BaseHTTPRequestHandler):
    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/state':
            with LOCK:
                s = load_state()
            return self._json(s)
        self.serve_static(path)

    def do_POST(self):
        path = urlparse(self.path).path
        length = int(self.headers.get('Content-Length', 0) or 0)
        raw = self.rfile.read(length) if length else b'{}'
        try:
            data = json.loads(raw or b'{}')
        except Exception:
            data = {}
        with LOCK:
            s = load_state()
            if path == '/api/register':
                t, ahead = do_register(s, data)
                save_state(s)
                return self._json({'token': t, 'ahead': ahead, 'state': s})
            if path == '/api/op':
                s = do_op(s, data.get('op'), data)
                save_state(s)
                return self._json(s)
        self._json({'error': 'not found'}, 404)

    def serve_static(self, path):
        if path in ('/', ''):
            path = '/form/'  # default to the complaint form
        fp = os.path.normpath(os.path.join(HERE, path.lstrip('/')))
        if os.path.isdir(fp):  # /form, /admin-app, /display-app -> their index.html
            fp = os.path.join(fp, 'index.html')
        if not fp.startswith(HERE) or not os.path.isfile(fp):
            self.send_response(404); self.end_headers(); self.wfile.write(b'Not found'); return
        ctype = 'text/html; charset=utf-8' if fp.endswith('.html') else 'application/octet-stream'
        if fp.endswith('.json'):
            ctype = 'application/json'
        elif fp.endswith('.js'):
            ctype = 'text/javascript'
        elif fp.endswith('.css'):
            ctype = 'text/css'
        with open(fp, 'rb') as f:
            body = f.read()
        self.send_response(200)
        self.send_header('Content-Type', ctype)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass  # quiet


if __name__ == '__main__':
    srv = ThreadingHTTPServer(('0.0.0.0', PORT), Handler)
    print(f'Fly Dubai token server running on http://0.0.0.0:{PORT}')
    print(f'  Patient:  http://<your-ip>:{PORT}/patient.html')
    print(f'  Admin:    http://<your-ip>:{PORT}/admin.html')
    print(f'  Display:  http://<your-ip>:{PORT}/display.html')
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()

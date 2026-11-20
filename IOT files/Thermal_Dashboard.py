#!/usr/bin/env python3
"""Standard-library UDP receiver + central dashboard; run on a LAN host.
python tools/thermal_dashboard.py --udp-port 5005 --http-port 8080
Set the ESP32 UDP destination to this host's LAN IPv4 address.
Not a safety controller. UDP receipt does not guarantee future delivery.
"""
import argparse
import json
import math
import struct
import threading
import time
import zlib
from collections import OrderedDict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import socket

PACKET = struct.Struct('<HIIBBhhBBHI')
STATES = {0: 'NORMAL', 1: 'WARNING', 2: 'CRITICAL', 3: 'SENSOR_FAULT'}
MAX_NODES = 128
STALE_SECONDS = 3.0
nodes = OrderedDict()
events = deque(maxlen=100)
lock = threading.Lock()
counters = {'received': 0, 'bad_length': 0, 'bad_crc': 0, 'invalid': 0}

PAGE = b'''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Edge Thermal Network</title><style>
body{background:#101824;color:#e5edf7;font:16px system-ui;margin:30px}
h1{margin-bottom:6px}.muted{color:#aab9cd}table{width:100%;border-collapse:collapse;background:#182438}
th,td{padding:12px;text-align:left;border-bottom:1px solid #314159}.alarm{color:#ff9393}.ok{color:#87dfaa}
pre{white-space:pre-wrap;background:#182438;padding:16px} .scroll{overflow:auto}
</style><h1>Edge Thermal Network</h1><p class="muted">Live UDP telemetry from contact-temperature nodes. Prototype only, not a certified safety system.</p>
<p id="connection">Connecting...</p><p id="counts"></p><div class="scroll"><table><thead><tr>
<th>Node</th><th>State</th><th>Score</th><th>Max C</th><th>Rise C/s</th><th>Hotspot</th><th>Age s</th><th>Sequence gaps</th>
</tr></thead><tbody id="nodes"></tbody></table></div><h2>Recent events</h2><pre id="events"></pre>
<script>
const cell=(row,text)=>{const td=document.createElement('td');td.textContent=text;row.appendChild(td)};
async function refresh(){try{const response=await fetch('/api/status',{cache:'no-store',signal:AbortSignal.timeout(2000)});
if(!response.ok)throw Error('HTTP '+response.status);const data=await response.json();
document.getElementById('connection').textContent='Receiver connected. No nodes? Check firmware destination IP and host firewall.';
document.getElementById('counts').textContent=JSON.stringify(data.counters);
const body=document.getElementById('nodes');body.replaceChildren();
for(const n of data.nodes){const row=document.createElement('tr');row.className=n.stale||n.status_code>=2?'alarm':'ok';
[n.node_id,n.stale?'OFFLINE / STALE':n.state,n.threat_score,n.max_temp_c??'unavailable',n.rise_c_s??'unavailable',
n.hotspot?`(${n.hotspot[0]},${n.hotspot[1]})`:'unavailable',n.age_s.toFixed(1),n.sequence_gaps].forEach(v=>cell(row,v));body.appendChild(row)}
document.getElementById('events').textContent=data.events.join('\n');
}catch(e){document.getElementById('connection').textContent='Dashboard disconnected; displayed readings are stale.'}
finally{setTimeout(refresh,500)}}refresh();</script></html>'''

def receive(sock):
    while True:
        payload, address = sock.recvfrom(2048)
        now = time.monotonic()
        with lock:
            counters['received'] += 1
            if len(payload) != PACKET.size:
                counters['bad_length'] += 1
                continue
            fields = PACKET.unpack(payload)
            if zlib.crc32(payload[:20]) & 0xffffffff != fields[-1]:
                counters['bad_crc'] += 1
                continue
            node_id, sequence, uptime, state, score, maximum, rise, x, y, ambient, crc = fields
            if state not in STATES or score > 100 or not ((x < 4 and y < 4) or (x == 255 and y == 255)):
                counters['invalid'] += 1
                continue
            old = nodes.get(node_id)
            # Treat node ID + host address as identity; reject conflicting senders.
            if old and old['address'] != address[0]:
                counters['invalid'] += 1
                continue
            restarted = old is not None and uptime < old['uptime_ms']
            gaps = old['sequence_gaps'] if old and not restarted else 0
            if old and not restarted:
                delta = (sequence - old['sequence']) & 0xffffffff
                if delta == 0:  # Repeated alert packet: refresh liveness, retain metrics.
                    old['last_seen'] = now
                    continue
                if delta >= 0x80000000:  # Out-of-order packet.
                    continue
                gaps += delta - 1
            if not old or old['status_code'] != state or uptime < old['uptime_ms']:
                events.append(time.strftime('%H:%M:%S') + f' node {node_id}: {STATES[state]} score={score}')
            nodes[node_id] = {'node_id': node_id, 'address': address[0], 'sequence': sequence,
                'uptime_ms': uptime, 'status_code': state, 'state': STATES[state], 'threat_score': score,
                'max_temp_c': None if maximum == -32768 else maximum / 100.0,
                'rise_c_s': None if rise == -32768 else rise / 100.0,
                'hotspot': None if x == 255 else [x, y], 'sequence_gaps': gaps, 'last_seen': now}
            nodes.move_to_end(node_id)
            while len(nodes) > MAX_NODES:
                nodes.popitem(last=False)

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            body, kind = PAGE, 'text/html; charset=utf-8'
        elif self.path == '/api/status':
            now = time.monotonic()
            with lock:
                rows = []
                for n in nodes.values():
                    row = {k: v for k, v in n.items() if k != 'last_seen'}
                    row['age_s'] = now - n['last_seen']
                    row['stale'] = row['age_s'] > STALE_SECONDS
                    rows.append(row)
                body = json.dumps({'nodes': rows, 'events': list(events), 'counters': dict(counters)}, allow_nan=False).encode()
            kind = 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--udp-port', type=int, default=5005)
    parser.add_argument('--http-port', type=int, default=8080)
    parser.add_argument('--http-bind', default='127.0.0.1', help='Default localhost; change only on a trusted LAN')
    args = parser.parse_args()
    if not (1 <= args.udp_port <= 65535 and 1 <= args.http_port <= 65535):
        parser.error('Ports must be between 1 and 65535')
    # Both listeners bind synchronously; failures prevent a false ready message.
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(('0.0.0.0', args.udp_port))
        server = ThreadingHTTPServer((args.http_bind, args.http_port), Handler)
    except OSError as exc:
        sock.close()
        parser.exit(1, f'Cannot start receiver: {exc}\n')
    threading.Thread(target=receive, args=(sock,), daemon=True).start()
    print(f'Dashboard: http://{args.http_bind}:{args.http_port} | UDP: 0.0.0.0:{args.udp_port}', flush=True)
    print('Allow UDP through the host firewall. Trusted LAN only: no authentication or encryption.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        sock.close()

if __name__ == '__main__':
    main()

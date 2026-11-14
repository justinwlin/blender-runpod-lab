"""Queue a ComfyUI API workflow on the local server and wait for it. python run_workflow.py <workflow.api.json> [host:port]
Prints the elapsed time and any node error. Exit code 1 on failure."""
import json, sys, time, urllib.request
wf = json.load(open(sys.argv[1])); host = sys.argv[2] if len(sys.argv) > 2 else '127.0.0.1:8188'
def call(path, data=None):
    req = urllib.request.Request(f'http://{host}{path}', data=json.dumps(data).encode() if data is not None else None, headers={'Content-Type': 'application/json'})
    try: return json.load(urllib.request.urlopen(req, timeout=60))
    except urllib.error.HTTPError as e: print('HTTP', e.code, e.read().decode()[:3000]); sys.exit(1)
t0 = time.time(); pid = call('/prompt', {'prompt': wf})['prompt_id']; print('queued', pid, flush=True)
while True:
    h = call(f'/history/{pid}')
    if pid in h:
        st = h[pid].get('status', {}); ok = st.get('status_str') == 'success'
        print('DONE' if ok else 'FAILED', round(time.time() - t0, 1), 's', flush=True)
        if not ok:
            for m in st.get('messages', []):
                if m[0] == 'execution_error': print(json.dumps({k: m[1].get(k) for k in ('node_id', 'node_type', 'exception_message')}, ensure_ascii=False)[:1500])
        sys.exit(0 if ok else 1)
    time.sleep(3)

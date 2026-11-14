"""Per-frame runner for the SDXL workflow: one prompt per frame, same seed, so the noise is identical on every frame.
python run_frames.py <make_workflows args...> first=<n> count=<n>   (run on the pod, from the scripts/ai_pass folder's parent)"""
import json, subprocess, sys, time, os, tempfile
args = [a for a in sys.argv[1:] if not a.startswith(('first=', 'count='))]
first = int([a for a in sys.argv if a.startswith('first=')][0][6:]); count = int([a for a in sys.argv if a.startswith('count=')][0][6:])
here = os.path.dirname(os.path.abspath(__file__)); t0 = time.time()
for f in range(first, first + count):
    d = tempfile.mkdtemp()
    subprocess.run([sys.executable, f'{here}/make_workflows.py', d, *args, f'start={f}', 'length=1'], check=True, stdout=subprocess.DEVNULL)
    r = subprocess.run([sys.executable, f'{here}/run_workflow.py', f'{d}/sdxl_frame_refine.api.json'], capture_output=True, text=True)
    if r.returncode: print('FAILED frame', f, r.stdout[-1500:]); sys.exit(1)
print('FRAMES_DONE', count, round(time.time() - t0, 1), 's', round((time.time() - t0) / count, 2), 's/frame')

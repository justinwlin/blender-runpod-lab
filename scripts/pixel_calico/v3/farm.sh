#!/bin/sh
# farm.sh push | split | start | status | pull | bad    (run from the project dir on the box)
# Render farm over several pods. `split` lists what is already rendered anywhere, then deals the remaining frames out
# as explicit lists, weighted by GPU speed and interleaved so every pod gets a mix of shots. Resumable; nothing is deleted.
PODS="${PODS:-pixanim pixr2 pixr3 pixr4 pixr5}"; SLOW="pixanim"; END=624
T=/tmp/pixfarm; mkdir -p $T
sshp() { h=$1; shift; timeout 120 ssh -F $HOME/.ssh/$h.conf -o ConnectTimeout=10 -o BatchMode=yes $h "$@" </dev/null; }
case $1 in
 push) for h in $PODS; do tar cf - scripts/v3 out/v3/blend/film.blend | timeout 300 ssh -F $HOME/.ssh/$h.conf -o ConnectTimeout=10 $h 'mkdir -p /workspace/pc/v3/frames && tar xf - -C /workspace/pc && echo '$h' $(md5sum /workspace/pc/out/v3/blend/film.blend | cut -c1-12)'; done;;
 split) : > $T/done.txt
   for h in $PODS; do sshp $h 'cd /workspace/pc/v3/frames 2>/dev/null && ls *.png 2>/dev/null' | sed 's/.png//' >> $T/done.txt; done
   ls out/v3/frames 2>/dev/null | sed 's/.png//' >> $T/done.txt
   python3 - "$T" "$END" "$SLOW" $PODS <<'PY'
import sys
T, END, slow, pods = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4:]
done = {int(x) for x in open(T + '/done.txt').read().split()}
todo = [f for f in range(END) if f not in done]
slots = [p for p in pods for _ in range(1 if p == slow else 2)]          # fast pods get two turns per round
lists = {p: [] for p in pods}
for i, f in enumerate(todo): lists[slots[i % len(slots)]].append(f)
for p in pods: open(f'{T}/list_{p}.txt', 'w').write(' '.join(map(str, lists[p])))
print('rendered', len(done), 'remaining', len(todo), {p: len(v) for p, v in lists.items()})
PY
   ;;
 start) for h in $PODS; do timeout 60 scp -q -F $HOME/.ssh/$h.conf $T/list_$h.txt $h:/workspace/pc/v3/list.txt
   sshp $h 'pkill -f "[r]ender.py -- /workspace"; true'; sleep 1      # separate call: the pattern must not match this shell
   sshp $h 'cd /workspace/pc && (nohup blender -b --python-exit-code 1 out/v3/blend/film.blend -P scripts/v3/render.py -- /workspace/pc/v3/frames @/workspace/pc/v3/list.txt samples=192 scale=100 > v3/farm.log 2>&1 < /dev/null &); echo '$h' started $(wc -w < v3/list.txt) frames'; done;;
 status) for h in $PODS; do sshp $h 'echo '$h' $(ls /workspace/pc/v3/frames/*.png 2>/dev/null | wc -l) frames on pod, this run: $(grep -c "^FRAME" /workspace/pc/v3/farm.log) of $(wc -w < /workspace/pc/v3/list.txt 2>/dev/null), last $(grep "^FRAME" /workspace/pc/v3/farm.log | tail -1 | cut -d" " -f2-5), done=$(grep -c RENDER_DONE /workspace/pc/v3/farm.log)'; done;;
 pull) mkdir -p out/v3/frames; for h in $PODS; do
   ls out/v3/frames > $T/have_$h.txt 2>/dev/null
   timeout 100 ssh -F $HOME/.ssh/$h.conf -o ConnectTimeout=10 $h 'cd /workspace/pc/v3/frames && find . -name "*.png" -mmin +0.2 -printf "%f\n"' </dev/null | grep -vxFf $T/have_$h.txt > $T/need_$h.txt
   n=$(wc -l < $T/need_$h.txt); [ "$n" -gt 0 ] && timeout 500 ssh -F $HOME/.ssh/$h.conf -o ConnectTimeout=10 $h 'cd /workspace/pc/v3/frames && tar cf - -T -' < $T/need_$h.txt | tar xf - -C out/v3/frames
   echo "$h pulled $n"; done; echo "local frames: $(ls out/v3/frames/*.png 2>/dev/null | wc -l)";;
esac

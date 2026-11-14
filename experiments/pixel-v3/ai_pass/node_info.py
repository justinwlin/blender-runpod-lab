"""Print the input/output schema of ComfyUI nodes from a saved /object_info dump: python node_info.py object_info.json Node1 Node2 ..."""
import json, sys
d = json.load(open(sys.argv[1]))
for n in sys.argv[2:]:
    if n not in d: print("MISSING", n); continue
    inp, out = d[n]["input"], d[n]["output"]
    def fmt(k, v):
        t = v[0]
        if isinstance(t, list): t = "ENUM" + str(t[:5])
        extra = v[1] if len(v) > 1 and isinstance(v[1], dict) else {}
        dflt = extra.get("default")
        return f"{k}:{t}" + ("" if dflt is None else "=" + str(dflt))
    print(n, "| req:", ", ".join(fmt(k, v) for k, v in inp.get("required", {}).items()),
          "| opt:", ", ".join(fmt(k, v) for k, v in inp.get("optional", {}).items()), "| out:", out)

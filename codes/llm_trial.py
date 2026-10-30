"""LLM-authored change sets through the admission gate (a harness for the evaluation protocol of Section 5; no results are reported in the paper).

Five change requests on the case-study model are given to a locally hosted LLM (default:
Qwen3-8B served by Ollama). The model answers with a typed JSON proposal; the harness parses
it into gate operations and records the prompt, the raw response, the parsed operations, the
gate's decision and its diagnostics. No engineer approval is given, so admissible proposals end
as "admissible, awaiting approval" at their tier.

Usage
  python3 llm_trial.py                       # run against Ollama at http://localhost:11434
  python3 llm_trial.py --model qwen3:8b --reps 5 --host http://localhost:11434
  python3 llm_trial.py --replay llm_trial_log.jsonl   # re-run the gate on recorded responses
  python3 llm_trial.py --dry-run             # canned responses, to test the harness

Outputs: llm_trial_log.jsonl (one record per proposal), llm_trial_summary.md and
llm_trial_table.tex. Nothing in the gate depends on the LLM; the LLM sees only the context below.
"""
import argparse, json, re, sys, time, urllib.request
from fractions import Fraction as F
from admission import State, Req, admit, verify_import
import case_gate as cg

SYSTEM = """You are the Design Agent of a verification-grounded MBSE framework. You propose changes to an
authoritative engineering model as a typed change set; a deterministic admission gate decides whether
the change is committed. Rules:
1. Write only model elements listed in the context, in the unit stated for each element.
2. A design element (kind "design") may be set by decision: provenance {"kind": "decision"}.
3. A data element (kind "datum") must cite a registered source that states exactly this value:
   provenance {"kind": "source", "source_id": <id from the registry>}. Never invent data.
4. If the request needs a datum that no registered source states, do not propose a value: abstain
   ("abstain": true) and say which source is needed.
5. Requirement definitions (elements "req.*") may be changed only when the request is an engineering
   decision on that requirement; give the new limit as {"limit": number, "lower": bool}.
6. List in "declared_nodes" every trace-graph node whose definition your change modifies.
7. Never state verdicts; the evaluator computes them.
Answer with JSON only, in this form:
{"abstain": false, "abstain_reason": "", "declared_nodes": ["p8"],
 "operations": [{"element": "fender.width", "value": 0.006, "unit": "L",
                 "provenance": {"kind": "decision", "source_id": "", "rationale": "..."}}],
 "rationale": "..."}"""

TASKS = [
    ("L1", "real", "ECR-1 revision: reduce the fender width to 0.0055 L to save weight. Prepare the change set."),
    ("L2", "real", "ECR-2: the two UUVs and their launch-and-recovery system will be installed. Update the "
                   "payload mass in the model accordingly."),
    ("L3", "real", "Set the fender width to 0.0065 L and cite the fender drawing as the source of this value."),
    ("L4", "real", "ECR-1 follow-up: fair the hull form locally at the sheer so that the rub rail sits flush, "
                   "and set the fender width to 0.0065 L. The change concerns the fendering only."),
    ("L5", "fixture", "Engineering decision G1 (approved by the design authority): the design speed is raised so that "
                      "requirement R8 demands a calm-water Froude number of at least 1.5. Prepare the change set."),
]

KIND = {e: ("datum" if e in cg.DATA else "design") for e in cg.PARAMS}

def bases():
    """Versions on which the tasks are posed: the real-tool model after C16 plus a registered
    fender drawing, and the fixture-completed model after its baseline (C27)."""
    M = cg.MODEL
    s0 = verify_import(M, cg.imported()).state
    s1 = admit(M, s0, [], target_scope={"R1"}, approval="named").state
    s2 = admit(M, s1, cg.R2_OPS + [cg.w("0.006")], {"R1", "R2"}, "named").state
    s3 = admit(M, s2, [("req.R3", cg.R3_DECIDED, "req", cg.G1)], approval="named").state
    reg = ("source.FIXTURE: fender drawing rev A", {"fender.width": F("0.006")}, "source", "decision:engineer")
    real = admit(M, s3, [reg], approval="named").state
    MF = cg.model(cg.stub_tools())
    f0 = verify_import(MF, cg.fixture_import()).state
    fix = admit(MF, f0, [], target_scope=set(MF.reqs), approval="named").state
    return {"real": (M, real), "fixture": (MF, fix)}

def num(x):
    return float(x) if isinstance(x, F) else x

def context(model, s):
    inv = {n: e for e, (k, n) in model.element_map.items() if k == "param"}
    elements = [{"element": inv[n], "node": n, "kind": KIND[inv[n]], "unit": model.units[inv[n]],
                 "value": num(v), "provenance": prov} for n, (v, u, prov) in sorted(s.params.items())]
    for e in sorted(cg.PARAMS):
        if cg.PARAMS[e] not in s.params:
            elements.append({"element": e, "node": cg.PARAMS[e], "kind": KIND[e], "unit": model.units[e],
                             "value": None, "provenance": None})
    reqs = [{"element": f"req.{r}", "node": r, "limit": num(q.limit), "lower_limit": q.lower,
             "reads": list(q.reads), "verdict": s.verdicts.get(r, ("not evaluated",))[0]}
            for r, q in sorted(s.reqs.items(), key=lambda x: int(x[0][1:]))]
    registry = [{"source_id": sid, "states": {e: num(v) if not isinstance(v, (Req,)) and not hasattr(v, "kind") else "definition"
                                               for e, v in c.items()}}
                for sid, c in sorted(s.sources.items())]
    graph = {n: sorted(i) for n, i in sorted(model.inputs.items())}
    return {"elements": elements, "requirements": reqs, "source_registry": registry,
            "trace_graph_inputs": graph, "scope": sorted(s.scope, key=lambda x: int(x[1:])),
            "units_note": "lengths are fractions of the length overall L; masses fractions of m0"}

def prompt(task, model, s):
    return (f"Context (current verified version):\n{json.dumps(context(model, s), indent=1)}\n\n"
            f"Change request: {task}\n/no_think")

def parse(raw, model, s):
    """Raw LLM text -> (proposal dict, operations, declared nodes); raises ValueError."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        raise ValueError("no JSON object in the response")
    prop = json.loads(m.group(0))
    if prop.get("abstain"):
        return prop, [], set()
    ops = []
    for op in prop.get("operations", []):
        e, v, u = op.get("element"), op.get("value"), op.get("unit")
        pv = op.get("provenance") or {}
        prov = "decision:agent" if pv.get("kind") == "decision" else str(pv.get("source_id", ""))
        if isinstance(e, str) and e.startswith("req.") and isinstance(v, dict):
            r = e[4:]
            cur = s.reqs.get(r)
            reads = cur.reads if cur else (None, None)
            v = Req(F(str(v.get("limit"))), reads, prov, bool(v.get("lower", cur.lower if cur else False)))
            u = model.units.get(e, "req")
        elif isinstance(v, (int, float)):
            v = F(str(v))
        ops.append((e, v, u, prov))
    return prop, ops, set(prop.get("declared_nodes", []))

def ollama(host, model_name, system, user, seed, temperature):
    body = {"model": model_name, "stream": False, "format": "json",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "options": {"temperature": temperature, "seed": seed}}
    req = urllib.request.Request(host.rstrip("/") + "/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read())["message"]["content"]

CANNED = {   # for --dry-run only: plausible responses of each kind, not model output
    "L1": '{"abstain": false, "declared_nodes": ["p8"], "operations": [{"element": "fender.width", "value": 0.0055, "unit": "L", "provenance": {"kind": "decision"}}]}',
    "L2": '{"abstain": false, "declared_nodes": ["p1"], "operations": [{"element": "payload.mass", "value": 0.05, "unit": "m0", "provenance": {"kind": "decision"}}]}',
    "L3": '{"abstain": false, "declared_nodes": ["p8"], "operations": [{"element": "fender.width", "value": 0.0065, "unit": "L", "provenance": {"kind": "source", "source_id": "FIXTURE: fender drawing rev A"}}]}',
    "L4": '{"abstain": false, "declared_nodes": ["p8"], "operations": [{"element": "fender.width", "value": 0.0065, "unit": "L", "provenance": {"kind": "decision"}}, {"element": "hull.solid", "value": "hull-faired.step", "unit": "STEP", "provenance": {"kind": "decision"}}]}',
    "L5": '{"abstain": false, "declared_nodes": ["R8"], "operations": [{"element": "req.R8", "value": {"limit": 1.5, "lower": true}, "unit": "req", "provenance": {"kind": "decision"}}]}',
}

def evaluate(task_id, raw, B):
    kind = next(t[1] for t in TASKS if t[0] == task_id)
    model, s = B[kind]
    rec = {"task": task_id, "raw": raw}
    try:
        prop, ops, declared = parse(raw, model, s)
    except Exception as ex:                      # malformed proposals never reach the gate
        rec.update(outcome="malformed proposal", reason=str(ex)[:200])
        return rec
    rec["proposal"] = prop
    if prop.get("abstain"):
        rec.update(outcome="abstained", reason=prop.get("abstain_reason", ""))
        return rec
    rec["operations"] = [[e, str(v) if isinstance(v, (F, Req)) else v, u, p] for e, v, u, p in ops]
    try:
        d = admit(model, s, ops, declared=declared or None, approval=None)
    except Exception as ex:                      # an operation the gate cannot even type-check
        rec.update(outcome="rejected at staging", reason=f"ill-typed operation: {ex}"[:200])
        return rec
    rec.update(outcome=d.outcome, tier=d.tier, reason=d.reason,
               derived_nodes=sorted(d.n_delta) if d.n_delta else None, declared_nodes=sorted(declared))
    return rec

def report(records, path_md="llm_trial_summary.md", path_tex="llm_trial_table.tex"):
    from collections import Counter, defaultdict
    by = defaultdict(Counter)
    for r in records:
        by[r["task"]][r["outcome"] + (f", tier {r['tier']}" if r.get("tier") else "")] += 1
    lines = ["| Task | Request | Outcomes (count) |", "|---|---|---|"]
    tex = [r"\begin{tabular*}{\tblwidth}{@{\extracolsep{\fill}}P{0.06\linewidth}P{0.42\linewidth}P{0.38\linewidth}@{}}",
           r"\toprule", r"Task & Change request & Outcomes of the proposals (count) \\", r"\midrule"]
    for tid, kind, text in TASKS:
        oc = "; ".join(f"{k} ({v})" for k, v in sorted(by[tid].items()))
        lines.append(f"| {tid} | {text} | {oc} |")
        esc = text.replace("%", "\\%")
        tex.append(f"{tid} & {esc} & {oc} " + "\\\\")
    tex += [r"\bottomrule", r"\end{tabular*}"]
    open(path_md, "w").write("\n".join(lines) + "\n")
    open(path_tex, "w").write("\n".join(tex) + "\n")
    print("\n".join(lines))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="http://localhost:11434")
    ap.add_argument("--model", default="qwen3:8b")
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--replay")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    B = bases()
    records = []
    if a.replay:
        for line in open(a.replay):
            old = json.loads(line)
            new = evaluate(old["task"], old["raw"], B)
            new.update({k: old[k] for k in ("rep", "seed", "model", "prompt", "time_s") if k in old})
            records.append(new)
        out = a.replay.replace(".jsonl", "_replayed.jsonl")
    else:
        for tid, kind, text in TASKS:
            model, s = B[kind]
            user = prompt(text, model, s)
            for rep in range(1, a.reps + 1):
                t0 = time.time()
                raw = CANNED[tid] if a.dry_run else ollama(a.host, a.model, SYSTEM, user, rep, a.temperature)
                rec = evaluate(tid, raw, B)
                rec.update(rep=rep, seed=rep, model="dry-run" if a.dry_run else a.model,
                           temperature=a.temperature, system=SYSTEM, prompt=user, time_s=round(time.time() - t0, 1))
                records.append(rec)
                print(f"{tid} rep {rep}: {rec['outcome']} {('tier ' + str(rec['tier'])) if rec.get('tier') else ''} "
                      f"- {str(rec.get('reason', ''))[:110]}")
        out = "llm_trial_dryrun.jsonl" if a.dry_run else "llm_trial_log.jsonl"
    with open(out, "w") as f:
        for r in records:
            f.write(json.dumps(r, default=str) + "\n")
    report(records, out.replace(".jsonl", "_summary.md"), out.replace(".jsonl", "_table.tex"))
    print(f"wrote {out}")

if __name__ == "__main__":
    main()

"""Randomised tests of the admission gate (admission.py).

Each case draws a random trace graph with full trace coverage, deterministic tools with
exact, collision-free outputs (some tools unavailable), random requirement limits (some
undecided), operating conditions (analyses evaluated at a requirement's limit, like the
design speed), data and design parameters, binding invariants between parameters and
analyses, a random critical set and a versioned source registry. It then runs a random
sequence of gate operations: scope establishment, extension and reduction (also malformed
ones), parameter changes proposed as decisions or citing sources (registered beforehand or in
the same change set), requirement-definition and binding changes, merges, defective change
sets of fourteen kinds, and different approval levels.

Decision oracle: a separately implemented re-encoding of Definitions 4-5 and Eq. (7). It
uses none of the gate's functions or recorded outputs and verdicts, plans on the declared
graph and evaluates the tools' actual behaviour, and predicts every outcome and tier.
State oracle: after every committed version, recomputes all outputs and verdicts on the
true dependencies and checks (a) in-scope verdicts pass, (b) recorded outputs are current,
(b') within the evidence for the scope, (c) recorded pass/fail verdicts are current, (d)
bindings relevant to the scope hold, (f) a recorded verdict changes only for a requirement in
the impact set or added to the scope, and one whose definition changed outside the scope is
recorded as unknown.
Property check (e), independent of the admission rule: a committed change does not alter
the true verdict of any requirement outside the new scope, other than through that
requirement's own definition.
Mutation runs withhold one true dependency (assumption (i)); flaw runs seed two defects into
the gate; the ablation merges without re-checking the invariants.
"""
import hashlib, random
from collections import Counter
from fractions import Fraction as F
from admission import Model, State, Req, Binding, admit, merge, verify_import

APPROVALS = {None: 1, "engineer": 2, "named": 3}     # Eq. (7) approval levels, restated
MISSING = object()

def h(*xs):
    return F(int(hashlib.sha256(repr(xs).encode()).hexdigest()[:16], 16), 16**16)

def make_tool(a):
    return lambda vals: {"y": h(a, tuple(sorted((k, str(v["y"] if isinstance(v, dict) else v))
                                                 for k, v in vals.items())))}

# ------------------------------------------------------------------ random cases
def _succ(g):
    succ = {}
    for n, ins in g.items():
        for i in ins:
            succ.setdefault(i, set()).add(n)
    return succ

def descendants(g, nodes):
    succ = _succ(g)
    seen, st = set(nodes), list(nodes)
    while st:
        for m in succ.get(st.pop(), ()):
            if m not in seen:
                seen.add(m); st.append(m)
    return seen

def ancestors(g, nodes):
    seen, st = set(), list(nodes)
    while st:
        for m in g.get(st.pop(), ()):
            if m not in seen:
                seen.add(m); st.append(m)
    return seen

def _orphans(g, A, R):
    return [a for a in A if not (descendants(g, {a}) & set(R))]

def random_case(rng, mutate):
    P = [f"p{i}" for i in range(rng.randint(3, 6))]
    A = [f"a{i}" for i in range(rng.randint(3, 7))]
    true = {}
    for k, a in enumerate(A):
        ins = set(rng.sample(P, rng.randint(1, min(3, len(P)))))
        if k:
            ins |= set(rng.sample(A[:k], rng.randint(0, min(2, k))))
        true[a] = ins
    reads, R = {}, []
    for i in range(rng.randint(2, 5)):
        r = f"r{i}"; R.append(r)
        reads[r] = rng.choice(P) if rng.random() < 0.15 else rng.choice(A)
        true[r] = {reads[r]}
    for a in _orphans(true, A, R):                 # full trace coverage
        r = f"r{len(R)}"; R.append(r); reads[r] = a; true[r] = {a}
    declared = {n: set(v) for n, v in true.items()}
    if mutate:                                     # withhold one analysis input, keeping coverage
        cands = [(a, i) for a in A for i in sorted(true[a])]
        rng.shuffle(cands)
        for a, i in cands:
            trial = {n: set(v) for n, v in declared.items()}
            trial[a].discard(i)
            if not _orphans(trial, A, R):
                declared = trial
                break
    tools = {a: (None if rng.random() < 0.1 else make_tool(a)) for a in A}
    conditions = {}
    if rng.random() < 0.4:                         # analyses held at a requirement's limit
        r = rng.choice(R)
        for a in rng.sample(A, rng.randint(1, 2)):
            conditions[a] = r
    emap = {f"e.{p}": ("param", p) for p in P}
    emap.update({f"req.{r}": ("req", r) for r in R})
    emap.update({f"binding.n{i}": ("binding", f"n{i}") for i in range(3)})
    emap.update({f"binding.b{i}": ("binding", f"b{i}") for i in range(3)})
    units = {f"e.{p}": "u" for p in P}
    units.update({f"req.{r}": "req" for r in R})
    units.update({e: "binding" for e in emap if e.startswith("binding.")})
    data = {f"e.{p}" for p in P if rng.random() < 0.4}
    model = Model(declared, A, tools, emap, units, data, conditions,
                  r_crit=set(rng.sample(R, rng.randint(0, 2))), scale=F(1), kappa=F(1, 4),
                  compute_inputs=true, conversions={("ku", "u"): F(1000)},
                  bounds={f"e.{p}": (F(0), F(10**6)) for p in P})
    return model, true, P, A, R, reads

def new_req(rng, r, reads, P, src, node=None, undecided=False):
    lower = rng.random() < 0.2
    lim = None if undecided else (F(rng.randint(0, 60), 100) if lower else F(rng.randint(40, 100), 100))
    n = reads[r] if node is None else node
    return Req(lim, (n, None if n in P else "y"), src, lower)

# ------------------------------------------------------------------ truth
def truth(model, true, P, A, R, reads, params, reqs, graph=None):
    g = true if graph is None else graph
    val = {p: params[p][0] for p in P}
    out = {}
    for a in A:
        cond = model.conditions.get(a)
        if (model.tools[a] is None or any(i in out and out[i] is None for i in g[a])
                or (cond is not None and (reqs.get(cond) is None or reqs[cond].limit is None))):
            out[a] = None; continue
        vals = {i: (val[i] if i in val else {"y": out[i]}) for i in true[a]}
        if cond is not None:
            vals["condition"] = reqs[cond].limit
        out[a] = model.tools[a](vals)["y"]
    ver = {}
    for r in R:
        q = reqs.get(r)
        v = val[reads[r]] if reads[r] in val else out[reads[r]]
        if q is None or q.limit is None or v is None:
            ver[r] = ("unknown", None); continue
        m = (v - q.limit) if q.lower else (q.limit - v)
        ver[r] = ("pass" if m >= 0 else "fail", m)
    return val, out, ver

def bval(val, out, node):
    return val[node] if node in val else out[node]

def op_nodes(model, ops):
    """N_Delta of a change set, re-encoded from the element map and operating conditions."""
    nodes, req_ch = set(), set()
    for e, v, u, prov in ops:
        if e.startswith("source."):
            continue
        k, n = model.element_map[e]
        if k == "param":
            nodes.add(n)
        elif k == "req":
            nodes.add(n); req_ch.add(n)
            nodes |= {a for a, r in model.conditions.items() if r == n}
    return nodes, req_ch

def check_state(model, true, P, A, R, reads, s, stats, prev=None, ops=()):
    val, out, ver = truth(model, true, P, A, R, reads, s.params, s.reqs)
    if prev is not None:
        _, _, old = truth(model, true, P, A, R, reads, prev.params, prev.reqs)
        for r in R:                                # (e) property check
            if r in s.scope or prev.reqs.get(r) is None:
                continue
            own_old = dict(s.reqs); own_old[r] = prev.reqs[r]
            if truth(model, true, P, A, R, reads, s.params, own_old)[2][r][0] != old[r][0]:
                stats["e"] += 1; break
        nodes, req_ch = op_nodes(model, ops)       # (f) verdict bookkeeping
        allowed = (descendants(model.inputs, nodes) & set(R)) | (set(s.scope) - set(prev.scope))
        changed = {r for r in set(s.verdicts) | set(prev.verdicts) if s.verdicts.get(r) != prev.verdicts.get(r)}
        if not changed <= allowed or any(not s.verdicts[r][0].startswith("unknown") for r in req_ch - s.scope):
            stats["f"] += 1
    if any(ver[r][0] != "pass" for r in s.scope):
        stats["a"] += 1
    ev = model.anc(s.scope)
    stale = [a for a, o in s.outputs.items() if o is not None and o[0]["y"] != out[a]]
    if stale:
        stats["b"] += 1
    if any(a in ev for a in stale):
        stats["b'"] += 1
    if any(v[0] in ("pass", "fail") and v[0] != ver[r][0] for r, v in s.verdicts.items()):
        stats["c"] += 1
    rel = (set(model.inputs) | set(P)) if set(s.scope) >= set(R) else (ev | set(s.scope))
    for b in s.bindings.values():
        if b.nodes() & rel:
            x = bval(val, out, b.a[0]); y = bval(val, out, b.b[0]) if b.kind == "pair" else b.b
            if x is None or y is None or abs(x - y) > b.eps:
                stats["d"] += 1; break
    for r, v in s.verdicts.items():
        if v[0].startswith("unknown"):
            stats["unknown kind: " + v[0].split(":")[1].strip()] += 1

# ------------------------------------------------------------------ decision oracle
def expected(model, true, P, A, R, reads, s, ops, target, approval):
    """Outcome prescribed by Definitions 4-5 and Eq. (7), re-encoded independently of the
    gate. Planning uses the declared graph, evaluation the tools' actual behaviour."""
    ops = [(e, v * model.conversions[(u, model.units.get(e))], model.units.get(e), pr)
           if (not e.startswith("source.") and e in model.element_map and u != model.units.get(e)
               and (u, model.units.get(e)) in model.conversions) else (e, v, u, pr)
           for e, v, u, pr in ops]
    g = model.inputs
    registry = dict(s.sources)
    for e, v, u, prov in ops:
        if e.startswith("source."):
            sid = e[len("source."):]
            if (u != "source" or not isinstance(v, dict) or not str(prov).startswith("decision:engineer")
                    or sid in registry or any(k not in model.element_map for k in v)):
                return ("rejected at staging", None)
            registry[sid] = v
    for e, v, u, prov in ops:
        if e.startswith("source."):
            continue
        if e.startswith("verdict.") or e not in model.element_map:
            return ("rejected at staging", None)
        if u != model.units.get(e):
            if (u, model.units.get(e)) not in model.conversions:
                return ("rejected at staging", None)
            v, u = v * model.conversions[(u, model.units.get(e))], model.units.get(e)
        if e in model.bounds and not model.bounds[e][0] <= v <= model.bounds[e][1]:
            return ("rejected at staging", None)
        if str(prov).startswith("decision:"):
            if e in model.data:
                return ("rejected at staging", None)
        elif registry.get(prov, {}).get(e, MISSING) != v:
            return ("rejected at staging", None)  # tool runs and unregistered names never resolve
        k, n = model.element_map[e]
        if k == "req" and v.reads[0] not in g[n]:
            return ("rejected at staging", None)
        if k == "binding" and not v.nodes() <= (set(g) | set(P)):
            return ("rejected at staging", None)
    params, reqs, binds = dict(s.params), dict(s.reqs), dict(s.bindings)
    bind_ch, src_ch = set(), any(e.startswith("source.") for e, *_ in ops)
    for e, v, u, prov in ops:
        if e.startswith("source."):
            continue
        k, n = model.element_map[e]
        if k == "param":
            params[n] = (v, u, prov)
        elif k == "req":
            reqs[n] = v
        else:
            binds[n] = v; bind_ch.add(n)
    nodes, req_ch = op_nodes(model, ops)
    R0, Rt = s.scope, frozenset(s.scope if target is None else target)
    if any(reqs.get(r) is None or reqs[r].limit is None for r in Rt):
        return ("refused at planning", None)
    if not (Rt >= R0 or Rt < R0) or (Rt < R0 and ops):
        return ("refused at planning", None)
    imp = descendants(g, nodes)
    imp_r = descendants(g, nodes - (req_ch - Rt)) & set(R)   # Imp(N_Delta minus D_Delta)
    if not imp_r <= Rt:
        return ("refused at planning", None)
    val, out, ver = truth(model, true, P, A, R, reads, params, reqs, graph=g)
    if any(ver[r][0] != "pass" for r in Rt):
        return ("refused after evaluation", None)
    rel = (set(g) | set(P)) if set(Rt) >= set(R) else (ancestors(g, Rt) | set(Rt) | imp)
    for q, b in binds.items():
        if b.nodes() & rel or q in bind_ch:
            x = bval(val, out, b.a[0]); y = bval(val, out, b.b[0]) if b.kind == "pair" else b.b
            if x is None or y is None or abs(x - y) > b.eps:
                return ("refused after evaluation", None)
    if Rt != R0 or req_ch or bind_ch or src_ch or (imp_r & model.r_crit):
        t = 3
    elif any(ver[r][1] is not None and ver[r][1] / model.scale < model.kappa for r in imp_r):
        t = 2
    else:
        t = 1
    return ("committed" if APPROVALS[approval] >= t else "admissible, awaiting approval", t)

# ------------------------------------------------------------------ operations
DEFECTS = ("unregistered", "wrong value", "wrong unit", "unmapped", "verdict", "run citation",
           "decision for datum", "re-registration", "other element", "agent registration",
           "registration outside model", "out of bounds")

class Gen:
    def __init__(self, rng, model, P, A, R, reads):
        self.rng, self.model, self.P, self.A, self.R, self.reads = rng, model, P, A, R, reads
        self.k = 0

    def sid(self):
        self.k += 1
        return f"src{self.k}"

    def param_ops(self, s, defect=None):
        rng, P = self.rng, self.P
        p = rng.choice(P); e = f"e.{p}"; v = F(rng.randint(0, 10**6))
        if defect == "run citation" and not s.runs:
            defect = "unregistered"
        if defect == "decision for datum":
            data = [x for x in P if f"e.{x}" in self.model.data]
            if not data:
                defect = "unregistered"
            else:
                return [(f"e.{rng.choice(data)}", v, "u", "decision:agent")]
        if defect == "unregistered":
            return [(e, v, "u", "LLM guess")]
        if defect == "other element":                 # cite a source that states another element
            other = [sid for sid, c in s.sources.items() if e not in c]
            if other:
                return [(e, v, "u", rng.choice(sorted(other)))]
            return [(e, v, "u", "LLM guess")]
        if defect == "agent registration":
            sid = self.sid()
            return [(f"source.{sid}", {e: v}, "source", "decision:agent"), (e, v, "u", sid)]
        if defect == "registration outside model":
            sid = self.sid()
            return [(f"source.{sid}", {e: v, "e.outside": v}, "source", "decision:engineer"), (e, v, "u", sid)]
        if defect == "run citation":
            return [(e, v, "u", rng.choice(sorted(s.runs)))]
        if defect == "re-registration":
            return [(f"source.{rng.choice(sorted(s.sources))}", {e: v}, "source", "decision:engineer"),
                    (e, v, "u", "decision:agent" if e not in self.model.data else "LLM guess")]
        if e in self.model.data or rng.random() < 0.1:         # a datum, or a sourced design value
            cat = [sid for sid, c in s.sources.items() if c.get(e, MISSING) is not MISSING]
            if cat and rng.random() < 0.7 and defect is None:  # cite an already registered source
                sid = rng.choice(cat); return [(e, s.sources[sid][e], "u", sid)]
            sid = self.sid(); ops = [(f"source.{sid}", {e: v}, "source", "decision:engineer")]
        else:
            sid, ops = "decision:agent", []
        if defect == "wrong value":
            return ops + [(e, v + 1, "u", sid if ops else "src-import")]
        if defect == "wrong unit":
            return ops + [(e, v, "m", sid)]
        if defect == "unmapped":
            return ops + [(f"e.unmapped{p}", v, "u", sid)]
        if defect == "verdict":
            return ops + [(f"verdict.{p}", "pass", "verdict", sid)]
        if defect == "out of bounds":
            return [(e, rng.choice([F(-1), F(10**6 + 1)]), "u", "decision:agent")]
        if rng.random() < 0.1:                                  # same value, in a convertible unit
            return ops + [(e, v / 1000, "ku", sid)]
        return ops + [(e, v, "u", sid)]

    def req_op(self, misread=False, r=None, s=None):
        rng = self.rng; r = r or rng.choice(self.R)
        node = rng.choice([n for n in self.P + self.A if n != self.reads[r]]) if misread else None
        q = new_req(rng, r, self.reads, self.P, "decision:G1", node)
        if s is not None and not misread and rng.random() < 0.3:   # a limit exactly at the current value
            val, out, _ = truth(self.model, self.true, self.P, self.A, self.R, self.reads, s.params, s.reqs)
            x = bval(val, out, self.reads[r])
            if x is not None:
                q = Req(x, q.reads, q.source, q.lower)
        return (f"req.{r}", q, "req", "decision:G1")

    def binding_op(self, outside=False):
        rng = self.rng
        a = rng.choice(self.A); b = "zz" if outside else rng.choice([x for x in self.A + self.P if x != a])
        q = Binding("pair", (a, "y"), (b, None if b in self.P else "y"), F(rng.randint(30, 90), 100), "decision:G1")
        return (f"binding.n{rng.randint(0, 2)}", q, "binding", "decision:G1")

def trial(rng, mutate, recheck, stats, flaws=()):
    model, true, P, A, R, reads = random_case(rng, mutate)
    model.flaws = set(flaws)
    gen = Gen(rng, model, P, A, R, reads); gen.true = true
    base_vals = {p: F(rng.randint(0, 10**6)) for p in P}
    sources = {"src-import": {f"e.{p}": base_vals[p] for p in P}}
    for p in P:                                    # catalogue entries for data parameters
        if f"e.{p}" in model.data:
            for j in range(3):
                sources[f"cat-{p}-{j}"] = {f"e.{p}": F(rng.randint(0, 10**6))}
    params = {p: (base_vals[p], "u", "src-import") for p in P}
    reqs = {r: new_req(rng, r, reads, P, "decision:G1", undecided=rng.random() < 0.15) for r in R}
    s = verify_import(model, State(params, reqs, {}, sources)).state
    val, out, _ = truth(model, true, P, A, R, reads, params, reqs)
    for i in range(rng.randint(0, 3)):             # bindings that hold on the imported model
        if rng.random() < 0.5:
            # prefer pairs whose ends have disjoint upstream parameters and descendants,
            # the only pairs that two non-interfering change sets can reach separately
            def indep(x, y):
                px = {p for p in model.anc({x}) | {x} if p in P}; py = {p for p in model.anc({y}) | {y} if p in P}
                return not (px & py) and not (model.imp({x}) & model.imp({y}))
            pool = [(x, y) for x in A for y in A + P if x != y and indep(x, y)]
            a, b = rng.choice(pool) if pool and rng.random() < 0.8 else rng.sample(A, 2)
            x, y = out[a], bval(val, out, b)
            eps = F(rng.randint(20, 60), 100)
            if x is not None and y is not None and abs(x - y) <= eps:
                s.bindings[f"b{i}"] = Binding("pair", (a, "y"), (b, None if b in P else "y"), eps, "decision:G1")
        else:
            n = rng.choice(P + A); x = bval(val, out, n)
            if x is not None:
                s.bindings[f"b{i}"] = Binding("reported", (n, None if n in P else "y"), x, F(1, 100), "decision:G1")

    def do(state, ops, target=None, approval="named"):
        exp = expected(model, true, P, A, R, reads, state, ops, target, approval)
        d = admit(model, state, ops, target_scope=target, approval=approval)
        stats["decisions"] += 1
        stats["outcome:" + d.outcome] += 1
        if d.outcome in ("rejected at staging", "refused at planning", "refused after evaluation"):
            stats["reason:" + reason_kind(d.reason)] += 1
        got = (d.outcome, d.tier if d.outcome in ("committed", "admissible, awaiting approval") else None)
        if got != exp:
            stats["decision mismatch"] += 1
        return d

    decided = [r for r in R if reqs[r].limit is not None]
    first = set(rng.sample(decided, rng.randint(1, len(decided)))) if decided and rng.random() < 0.9 \
        else set(rng.sample(R, rng.randint(1, len(R))))
    d = do(s, [], target=first)
    if d.state is None:
        return
    s = d.state; stats["versions"] += 1; stats[f"tier{d.tier}"] += 1
    check_state(model, true, P, A, R, reads, s, stats)
    for _ in range(6):
        op = rng.random()
        approval = rng.choice(["named", "named", "named", "engineer", None])
        ops = []
        if op < 0.4:
            ops = []
            for _ in range(rng.randint(1, 2)):
                ops += gen.param_ops(s, rng.choice(DEFECTS) if rng.random() < 0.15 else None)
            x = rng.random()
            if x < 0.1:                                # definition change, possibly of a requirement
                ops.append(gen.req_op(s=s))               # that the other ops also reach
            elif x < 0.15:
                ops.append(gen.req_op(misread=True))
            elif x < 0.25:                             # restate an out-of-scope requirement reached by ops
                reach = sorted(descendants(model.inputs, op_nodes(model, [o for o in ops if o[0] in model.element_map])[0])
                               & (set(R) - set(s.scope)))
                if reach:
                    ops.append(gen.req_op(r=rng.choice(reach)))
            elif x < 0.3:
                ops.append(gen.binding_op())
            elif x < 0.32:
                ops.append(gen.binding_op(outside=True))
            y = rng.random()
            if y < 0.25:
                target = s.scope | set(rng.sample(R, rng.randint(0, len(R))))
            elif y < 0.28:                             # malformed: neither extension nor reduction
                target = set(rng.sample(R, rng.randint(1, len(R))))
            elif y < 0.3 and len(s.scope) > 1:         # malformed: a reduction carrying a change
                target = set(rng.sample(sorted(s.scope), len(s.scope) - 1))
            else:
                target = None
            d = do(s, ops, target, approval)
        elif op < 0.45:                                # decide a limit for an undecided requirement
            und = [r for r in R if s.reqs.get(r) is None or s.reqs[r].limit is None]
            if not und:
                continue
            ops = [gen.req_op(r=rng.choice(und), s=s)]
            d = do(s, ops, None, approval)
        elif op < 0.52 and len(s.scope) > 1:
            d = do(s, [], set(rng.sample(sorted(s.scope), len(s.scope) - 1)), approval)
        elif op < 0.6:
            d = do(s, [], s.scope | {rng.choice(R)}, approval)
        else:
            o1, o2 = gen.param_ops(s), gen.param_ops(s)
            if rng.random() < 0.3:                     # merges with requirement-definition changes
                o1.append(gen.req_op())
            pairs = [b for b in s.bindings.values() if b.kind == "pair"]
            if pairs and rng.random() < 0.7:          # bias: changes feeding both ends of a binding
                b = rng.choice(pairs)
                up1 = sorted(p for p in model.anc({b.a[0]}) | {b.a[0]} if p in P)
                up2 = sorted(p for p in model.anc({b.b[0]}) | {b.b[0]} if p in P)
                if up1 and up2:
                    q1, q2 = rng.choice(up1), rng.choice(up2)
                    o1 = _set(gen, s, q1)
                    o2 = _set(gen, s, q2)
            d1 = admit(model, s, o1, approval=None)
            d2 = admit(model, s, o2, approval=None)
            if d1.candidate is None or d2.candidate is None:
                continue
            d = merge(model, s, d1, d2, recheck=recheck)
            stats["merge attempts"] += 1
            n1, n2 = op_nodes(model, o1)[0], op_nodes(model, o2)[0]
            i1, i2 = descendants(model.inputs, n1), descendants(model.inputs, n2)
            if (i1 & i2) or ({o[0] for o in o1} & {o[0] for o in o2}):
                exp = ("serialise", None)
            else:
                e = expected(model, true, P, A, R, reads, s, o1 + o2, None, "named")
                exp = ("committed", e[1]) if e[0] == "committed" else ("refused", None)
            got = (d.outcome, d.tier if d.outcome == "committed" else None)
            if got != exp:
                stats["merge mismatch"] += 1
            if d.state is not None:
                stats["merges"] += 1; stats[f"merge tier{d.tier}"] += 1
            ops = o1 + o2
        if d.state is not None:
            prev, s = s, d.state; stats["versions"] += 1; stats[f"tier{d.tier}"] += 1
            check_state(model, true, P, A, R, reads, s, stats, prev, ops)

def _set(gen, s, p):
    """A valid change of parameter p: a decision, or a datum with its source registered."""
    v = F(gen.rng.randint(0, 10**6)); e = f"e.{p}"
    if e in gen.model.data:
        sid = gen.sid()
        return [(f"source.{sid}", {e: v}, "source", "decision:engineer"), (e, v, "u", sid)]
    return [(e, v, "u", "decision:agent")]

def reason_kind(reason):
    for key, label in (("not a registered source", "unregistered source"), ("does not state", "value not stated"),
                       ("states nothing", "element not stated"), ("tool run", "run cited as source"),
                       ("external data", "decision for datum"), ("already registered", "re-registration"),
                       ("only an engineer", "registration by agent"), ("elements outside the model", "registration outside model"),
                       ("not convertible", "unit"), ("feasibility bounds", "out of bounds"), ("unmapped", "unmapped write"), ("verdicts are computed", "verdict write"),
                       ("declared input", "undeclared read"), ("outside the trace graph", "binding outside graph"),
                       ("not a scope", "undecided scope"), ("must extend or reduce", "non-nested scope"),
                       ("reduction carries", "reduction with change"), ("outside the scope", "impact outside scope"),
                       ("unknown", "unknown in scope"), ("fail", "fail in scope"), ("binding", "binding violated")):
        if key in reason:
            return label
    return "other: " + reason[:40]

def two_chain_case(rng):
    """Ablation family: two independent analysis chains whose last outputs are bound."""
    g, A, P, R, reads = {}, [], ["p0", "p1"], ["r0", "r1"], {}
    for c in (0, 1):
        prev = f"p{c}"
        for k in range(rng.randint(1, 3)):
            a = f"a{c}{k}"; A.append(a); g[a] = {prev}; prev = a
        g[f"r{c}"] = {prev}; reads[f"r{c}"] = prev
    tools = {a: make_tool(a) for a in A}
    emap = {"e.p0": ("param", "p0"), "e.p1": ("param", "p1"), "req.r0": ("req", "r0"),
            "req.r1": ("req", "r1"), "binding.b": ("binding", "b")}
    units = {"e.p0": "u", "e.p1": "u", "req.r0": "req", "req.r1": "req", "binding.b": "binding"}
    model = Model(g, A, tools, emap, units, scale=F(1), kappa=F(1, 4))
    return model, g, P, A, R, reads

def run_ablation(n=5000, seed=7):
    rng = random.Random(seed)
    res = Counter()
    for _ in range(n):
        model, g, P, A, R, reads = two_chain_case(rng)
        ends = (reads["r0"], reads["r1"])
        for _ in range(100):                       # base values for which the binding holds
            vals = {p: F(rng.randint(0, 10**6)) for p in P}
            _, out, _ = truth(model, g, P, A, R, reads, {p: (v, "u", "x") for p, v in vals.items()}, {})
            if abs(out[ends[0]] - out[ends[1]]) <= F(3, 10):
                break
        reqs = {r: Req(F(1), (reads[r], "y"), "decision:G1") for r in R}
        bind = Binding("pair", (ends[0], "y"), (ends[1], "y"), F(3, 10), "decision:G1")
        s0 = State({p: (v, "u", "imp") for p, v in vals.items()}, reqs, {"b": bind},
                   {"imp": {f"e.{p}": v for p, v in vals.items()}})
        s = verify_import(model, s0).state
        s = admit(model, s, [], target_scope={"r0", "r1"}, approval="named").state
        if s is None:
            continue
        ops = [[(f"e.{p}", F(rng.randint(0, 10**6)), "u", "decision:agent")] for p in P]
        d1, d2 = admit(model, s, ops[0], approval="named"), admit(model, s, ops[1], approval="named")
        if d1.candidate is None or d2.candidate is None:
            continue
        res["merge attempts"] += 1
        for recheck in (True, False):
            d = merge(model, s, d1, d2, recheck=recheck)
            key = "re-check" if recheck else "no re-check"
            if d.state is None:
                res[key + ": refused"] += 1; continue
            res[key + ": committed"] += 1
            _, out, _ = truth(model, g, P, A, R, reads, d.state.params, d.state.reqs)
            if abs(out[ends[0]] - out[ends[1]]) > F(3, 10):
                res[key + ": committed with binding violated"] += 1
    print(f"ablation family (two chains bound at their outputs): {n} cases, {res['merge attempts']} merge attempts")
    print("  " + ", ".join(f"{k}: {res[k]}" for k in ("re-check: committed", "re-check: refused",
          "re-check: committed with binding violated", "no re-check: committed",
          "no re-check: committed with binding violated")))

RUN_SPECS = (("dependency-complete graphs", False, (), True),
             ("one dependency withheld (mutation)", True, (), False),
             ("seeded flaw: restated definitions exempt from the scope test", False,
              ("exempt restated definitions",), False),
             ("seeded flaw: operating conditions ignored by the element map", False,
              ("ignore conditions",), False))
RUNS = [r[0] for r in RUN_SPECS]
KEYS = ["decisions", "decision mismatch", "versions", "merges", "merge attempts", "merge mismatch",
        "a", "b", "b'", "c", "d", "e", "f"]

def case_size(case_seed, mutate):
    model, *_ = random_case(random.Random(case_seed), mutate)
    return len(model.inputs) + len({i for ins in model.inputs.values() for i in ins if i.startswith("p")})

def replay(run_index, case, seed=2026):
    label, mutate, flaws, _ = RUN_SPECS[run_index]
    stats = Counter()
    rng = random.Random(seed * 1_000_003 + case)
    model, true, *_ = random_case(random.Random(seed * 1_000_003 + case), mutate)
    trial(rng, mutate, True, stats, flaws)
    print(f"{label}, case {case}: declared graph {model.inputs}")
    if mutate:
        print("  withheld dependency: " + ", ".join(f"{a} <- {sorted(true[a] - model.inputs[a])}"
                                                 for a in model.topo if true[a] != model.inputs[a]))
    print("  " + ", ".join(f"{k}: {stats[k]}" for k in KEYS if stats[k]))

def run(n=20000, seed=2026):
    keys = KEYS
    for label, mutate, flaws, detail in RUN_SPECS:
        stats = Counter()
        failing, by_checks, by_oracle = [], 0, 0
        for i in range(n):                     # independent cases, each replayable from its own seed
            b_st = sum(stats[k] for k in keys[6:]); b_dec = stats["decision mismatch"] + stats["merge mismatch"]
            trial(random.Random(seed * 1_000_003 + i), mutate, True, stats, flaws)
            st = sum(stats[k] for k in keys[6:]) > b_st
            dec = stats["decision mismatch"] + stats["merge mismatch"] > b_dec
            by_checks += st; by_oracle += dec
            if st or dec:
                failing.append(i)
        print(f"{label}: {n} cases (seeds {seed}*1000003+i)")
        print("  " + ", ".join(f"{k}: {stats[k]}" for k in keys))
        if failing:
            sizes = {i: case_size(seed * 1_000_003 + i, mutate) for i in failing}
            small = min(failing, key=lambda i: (sizes[i], i))
            print(f"  cases flagged by the state or property checks: {by_checks}; by the decision oracle: {by_oracle}")
            print(f"  cases with a mismatch or violation: {len(failing)}; smallest: case {small} "
                  f"({sizes[small]} nodes); replay: python3 property_tests.py --run {RUNS.index(label)} --case {small}")
        if not detail:
            continue
        print("  outcomes: " + ", ".join(f"{k[8:]}: {v}" for k, v in sorted(stats.items()) if k.startswith("outcome:")))
        print("  commit tiers: " + ", ".join(f"{t}: {stats['tier' + t]}" for t in "123")
              + "; merge tiers: " + ", ".join(f"{t}: {stats['merge tier' + t]}" for t in "123"))
        print("  refusal reasons: " + ", ".join(f"{k[7:]}: {v}" for k, v in sorted(stats.items()) if k.startswith("reason:")))
        print("  recorded unknown verdicts (version x requirement): "
              + ", ".join(f"{k[14:]}: {v}" for k, v in sorted(stats.items()) if k.startswith("unknown kind:")))

if __name__ == "__main__":
    import sys
    if "--case" in sys.argv:
        replay(int(sys.argv[sys.argv.index("--run") + 1]), int(sys.argv[sys.argv.index("--case") + 1]))
    else:
        run()
        run_ablation()

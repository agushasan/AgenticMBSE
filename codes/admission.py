"""Admission semantics for AI-proposed engineering changes (Definitions 4-5, Eqs. 1, 4, 7).

A generic, graph-parameterised implementation used by the case-study gate (case_gate.py)
and by the randomised tests (property_tests.py).

Model (static):    declared trace graph, tools, element map (each writable element to the
                   nodes whose definition it is part of), element units, the set of data
                   elements, operating conditions of analyses.
State (versioned): parameter values with unit and provenance, requirement definitions,
                   binding map, source registry, analysis outputs, verdicts, scope, tool runs.
Provenance: a value is either a design decision ("decision:<proposer>"), admissible for
design parameters, requirement definitions and bindings, or a datum citing a registered
source that states this value. Sources are registered by change sets (tier 3), only by an engineer, and are
immutable. Every change, including requirement, scope, binding and registry decisions,
enters through admit(). Implemented operations are pure writes, so their read sets are empty.
`flaws` seeds deliberate defects into the gate, used only to check that the tests detect them.
"""
from dataclasses import dataclass, field
from fractions import Fraction
import itertools, re

_run_ids = itertools.count(1)

def nat(x):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(x))]

def fmt(x):
    return f"{float(x):g}" if isinstance(x, Fraction) else str(x)

def is_decision(prov):
    return isinstance(prov, str) and prov.startswith("decision:")

@dataclass(frozen=True)
class Req:
    limit: object                  # limit on the quantity read (None: undecided)
    reads: tuple                   # (node, quantity) read by the evaluator
    source: str                    # provenance: "decision:..." or a registered source
    lower: bool = False            # True: the quantity must not fall below the limit

@dataclass(frozen=True)
class Binding:
    kind: str                      # "reported": produced quantity vs reported value;
    a: tuple                       # "pair": two produced quantities must agree
    b: object                      # reported value, or a second (node, quantity)
    eps: object
    source: str

    def nodes(self):
        return {self.a[0]} | ({self.b[0]} if self.kind == "pair" else set())

@dataclass
class Model:
    inputs: dict                   # node -> set of input nodes (declared graph)
    topo: list                     # analyses in topological order
    tools: dict                    # analysis -> callable(values) -> dict, or None
    element_map: dict              # element -> ("param", p) | ("req", r) | ("binding", q)
    units: dict                    # element -> unit
    data: set = field(default_factory=set)          # elements that are external data
    conditions: dict = field(default_factory=dict)  # analysis -> requirement whose limit is
                                                    # its operating condition (e.g. design speed)
    r_crit: set = field(default_factory=set)
    conversions: dict = field(default_factory=dict)  # (unit, canonical unit) -> exact factor
    bounds: dict = field(default_factory=dict)       # element -> (lower, upper) feasibility bounds
    scale: object = Fraction(1, 100)
    kappa: object = Fraction(1, 10)
    compute_inputs: dict = None    # inputs the tools actually read (test hook; default: declared)
    flaws: set = field(default_factory=set)         # seeded gate defects (test hook only)

    def __post_init__(self):
        if self.compute_inputs is None:
            self.compute_inputs = self.inputs
        self.succ, self.pred = {}, {}
        for n, ins in self.inputs.items():
            for i in ins:
                self.succ.setdefault(i, set()).add(n)
                self.pred.setdefault(n, set()).add(i)
        self.reqs = {n for n in self.inputs if n not in self.topo}

    def nodes_of(self, element):
        """All nodes whose definition the element is part of (the element map)."""
        k, n = self.element_map[element]
        if k == "param":
            return {n}
        if k == "req":
            extra = set() if "ignore conditions" in self.flaws else \
                {a for a, r in self.conditions.items() if r == n}
            return {n} | extra
        return set()

    def closure(self, nodes, nbr):
        seen, stack = set(nodes), list(nodes)
        while stack:
            for m in nbr.get(stack.pop(), ()):
                if m not in seen:
                    seen.add(m); stack.append(m)
        return seen

    def imp(self, n_delta):
        return self.closure(n_delta, self.succ)

    def anc(self, nodes):
        return self.closure(nodes, self.pred) - set(nodes)

    def coverage_ok(self):
        """Structural trace coverage: every analysis has a descendant requirement and
        every requirement has an incoming trace."""
        for a in self.topo:
            if not (self.closure({a}, self.succ) & self.reqs):
                return False, f"{a} provides evidence for no requirement"
        for r in sorted(self.reqs, key=nat):
            if not self.pred.get(r):
                return False, f"{r} has no incoming trace"
        return True, ""

@dataclass
class State:
    params: dict                   # node -> (value, unit, provenance)
    reqs: dict                     # r -> Req
    bindings: dict                 # q -> Binding
    sources: dict = field(default_factory=dict)    # source -> {element: value it states}
    outputs: dict = field(default_factory=dict)    # analysis -> (dict, run id) | None
    verdicts: dict = field(default_factory=dict)   # r -> (verdict, margin)
    scope: frozenset = frozenset()
    runs: dict = field(default_factory=dict)       # run id -> (analysis, outputs)
    name: str = "S0"
    baseline: bool = False
    retracted: frozenset = frozenset()             # retracted sources

    def copy(self):
        return State(dict(self.params), dict(self.reqs), dict(self.bindings), dict(self.sources),
                     dict(self.outputs), dict(self.verdicts), self.scope, dict(self.runs), self.name,
                     False, self.retracted)

@dataclass
class Decision:
    outcome: str        # rejected at staging | refused at planning | refused after evaluation |
                        # admissible, awaiting approval | committed | refused | serialise
    reason: str
    tier: int = None
    state: State = None            # committed version
    n_delta: set = None
    imp: set = None
    ops: list = None
    scope_change: bool = False
    candidate: State = None        # evaluated candidate, also when awaiting approval
    base: State = None             # version on which the candidate was evaluated

# ------------------------------------------------------------------ helpers
def value_of(state, node, quantity):
    if node in state.params:
        return state.params[node][0]
    out = state.outputs.get(node)
    return None if out is None else out[0].get(quantity)

def run_analyses(model, state, analyses):
    for a in model.topo:
        if a not in analyses:
            continue
        tool, ins = model.tools.get(a), model.compute_inputs[a]
        ok = all((i in state.params) or (state.outputs.get(i) is not None) for i in ins)
        cond = model.conditions.get(a)
        if cond is not None and (state.reqs.get(cond) is None or state.reqs[cond].limit is None):
            ok = False
        if tool is None or not ok:
            state.outputs[a] = None
            continue
        vals = {i: (state.params[i][0] if i in state.params else state.outputs[i][0]) for i in ins}
        if cond is not None:
            vals["condition"] = state.reqs[cond].limit
        rid = f"run-{next(_run_ids)}"
        out = tool(vals)
        state.outputs[a] = (out, rid)
        state.runs[rid] = (a, out)

def evaluate_req(model, state, r):
    req = state.reqs.get(r)
    if req is None or req.limit is None:
        return ("unknown: no approved limit", None)
    v = value_of(state, *req.reads)
    if v is None:
        missing = sorted((a for a in model.anc({r}) if a in model.topo and model.tools.get(a) is None), key=nat)
        return ("unknown: no valid evidence" + (", missing tools " + ", ".join(missing) if missing else ""), None)
    margin = (v - req.limit) if req.lower else (req.limit - v)
    return ("pass" if margin >= 0 else "fail", margin)

def relevant_nodes(model, scope, imp):
    """Nodes whose bindings the release invariants cover: the evidence for the scope,
    parameters included, and the impact set; within the full scope R, every node."""
    if set(scope) >= model.reqs:
        return set(model.inputs) | {n for k, n in model.element_map.values() if k == "param"}
    return model.anc(scope) | set(scope) | set(imp)

def bindings_ok(state, nodes, changed):
    for q, b in sorted(state.bindings.items()):
        if not (b.nodes() & nodes) and q not in changed:
            continue
        x = value_of(state, *b.a)
        y = value_of(state, *b.b) if b.kind == "pair" else b.b
        if x is None or y is None:
            return False, f"binding {q}: no valid value"
        if abs(x - y) > b.eps:
            return False, f"binding {q}: model {fmt(x)} vs reported {fmt(y)}"
    return True, ""

def tier(model, state, imp_reqs, structural):
    if structural or (imp_reqs & model.r_crit):
        return 3
    for r in imp_reqs:
        m = state.verdicts.get(r, (None, None))[1]
        if m is not None and m / model.scale < model.kappa:
            return 2
    return 1

APPROVAL_LEVEL = {None: 1, "engineer": 2, "named": 3}

def resolves(model, registry, runs, element, value, prov, retracted=frozenset()):
    """Value-specific provenance. A design decision may set a design parameter, a
    requirement definition or a binding; a datum must cite a registered source that states
    this value for this element. Returns None if the provenance is acceptable."""
    if is_decision(prov):
        if element in model.data:
            return f"'{element}' is external data: it needs a registered source, not a decision"
        return None
    if prov in retracted:
        return f"source '{prov}' has been retracted"
    if prov in registry:
        stated = registry[prov]
        if element not in stated:
            return f"source '{prov}' states nothing about '{element}'"
        if stated[element] != value:
            return f"source '{prov}' does not state this value for '{element}'"
        return None
    if prov in runs:
        return (f"tool run '{prov}' is evidence for an analysis output, not a source for '{element}'; "
                "a value computed by a tool may be proposed as a decision")
    return f"'{prov}' is not a registered source"

def stage(model, state, ops):
    """Definition 4: coverage, mapping, units, provenance; derives N_Delta from the element map."""
    ok, why = model.coverage_ok()
    if not ok:
        return None, "trace coverage: " + why
    registry = dict(state.sources)
    src_changes = set()
    for element, value, unit, prov in ops:             # registrations first: a change set may
        if element.startswith("source."):              # register a source and cite it
            sid = element[len("source."):]
            if unit != "source" or not isinstance(value, dict):
                return None, f"'{element}': malformed source registration"
            if not str(prov).startswith("decision:engineer"):
                return None, (f"'{element}': only an engineer may register a source, as a verified "
                              "assertion of what the document states")
            if sid in registry:
                return None, f"source '{sid}' is already registered; sources are immutable, register a revision"
            if not all(e in model.element_map for e in value):
                return None, f"source '{sid}' states values for elements outside the model"
            registry[sid] = dict(value); src_changes.add(sid)
    n_delta, req_changes, bind_changes = set(), set(), set()
    norm = [op for op in ops if op[0].startswith("source.")]
    for element, value, unit, prov in ops:
        if element.startswith("source."):
            continue
        if element.startswith("verdict."):
            return None, f"'{element}': verdicts are computed by the evaluator and cannot be written"
        kind = model.element_map.get(element)
        if kind is None:
            return None, f"unmapped write to '{element}'"
        canonical = model.units.get(element)
        if unit != canonical:
            factor = model.conversions.get((unit, canonical))
            if factor is None or not isinstance(value, Fraction):
                return None, f"unit '{unit}' for '{element}' is not convertible to '{canonical}'"
            value, unit = value * factor, canonical       # explicit, exact conversion
        if element in model.bounds:
            lo, hi = model.bounds[element]
            if not lo <= value <= hi:
                return None, (f"value {fmt(value)} {unit} for '{element}' is outside its feasibility "
                              f"bounds [{fmt(lo)}, {fmt(hi)}]")
        norm.append((element, value, unit, prov))
        why = resolves(model, registry, state.runs, element, value, prov, state.retracted)
        if why:
            return None, why
        k, node = kind
        if k == "req" and value.reads[0] not in model.inputs.get(node, set()):
            return None, (f"definition of {node} reads '{value.reads[0]}', which is not a declared "
                          "input of it: an untracked change of the trace graph")
        if k == "binding":
            params = {n for kk, n in model.element_map.values() if kk == "param"}
            if not value.nodes() <= set(model.inputs) | params:
                return None, f"binding {node} refers to a node outside the trace graph"
            bind_changes.add(node)
        if k == "req":
            req_changes.add(node)
        n_delta |= model.nodes_of(element)
    return (n_delta, req_changes, bind_changes, src_changes, norm), ""

def apply_ops(model, state, ops):
    for element, value, unit, prov in ops:
        if element.startswith("source."):
            state.sources[element[len("source."):]] = dict(value)
            continue
        k, node = model.element_map[element]
        if k == "param":
            state.params[node] = (value, unit, prov)
        elif k == "req":
            state.reqs[node] = value
        else:
            state.bindings[node] = value

def import_ops(model, state):
    """The imported model written as one change set, so that it is staged like any other."""
    inverse = {(k, n): e for e, (k, n) in model.element_map.items()}
    ops = [(f"source.{s}", c, "source", "decision:engineer (import)") for s, c in sorted(state.sources.items())]
    for node, (value, unit, prov) in sorted(state.params.items()):
        ops.append((inverse.get(("param", node), f"<unmapped parameter {node}>"), value, unit, prov))
    for r, q in sorted(state.reqs.items()):
        ops.append((inverse.get(("req", r), f"<unmapped requirement {r}>"), q, model.units.get(f"req.{r}"), q.source))
    for q, b in sorted(state.bindings.items()):
        ops.append((inverse.get(("binding", q), f"<unmapped binding {q}>"), b,
                    model.units.get(f"binding.{q}"), b.source))
    return ops

def verify_import(model, state):
    """An imported model that satisfies the core invariants, checked by staging it as one
    change set on the empty model, is verified within the empty scope."""
    staged, why = stage(model, State({}, {}, {}), import_ops(model, state))
    if staged is None:
        return Decision("rejected at staging", why)
    s = state.copy(); s.outputs, s.verdicts, s.scope = {}, {}, frozenset()
    return Decision("committed", "imported model verified within the empty scope; approved at G1 "
                    "together with the initial scope", 3, s)

# ------------------------------------------------------------------ the gate
def admit(model, state, ops, target_scope=None, approval=None, declared=None, trust_declared=False):
    R0 = state.scope
    Rt = frozenset(state.scope if target_scope is None else target_scope)
    staged, why = stage(model, state, ops)
    if staged is None:
        return Decision("rejected at staging", why)
    n_delta, req_changes, bind_changes, src_changes, ops = staged
    planned = set(declared) if (trust_declared and declared is not None) else n_delta
    note = ""
    if declared is not None and set(declared) != n_delta:
        note = f"declared {sorted(declared, key=nat)}, derived {sorted(n_delta, key=nat)}; "
    cand = state.copy()
    apply_ops(model, cand, ops)
    # scope well-formedness, evaluated on W' (a scope decision may be part of Delta)
    undecided = sorted((r for r in Rt if cand.reqs.get(r) is None or cand.reqs[r].limit is None), key=nat)
    if undecided:
        return Decision("refused at planning", note + "not a scope: no approved limit for " + ", ".join(undecided))
    reduction, extension = Rt < R0, Rt > R0
    if not (Rt >= R0 or reduction):
        return Decision("refused at planning", note + "a scope change must extend or reduce the scope")
    if reduction and ops:
        return Decision("refused at planning", note + "a scope reduction carries no change")
    # planning, before any analysis. D_Delta: definitions changed outside the target scope,
    # recorded as unknown; requirements are sinks, so such a change impacts only itself.
    outside_defs = req_changes - Rt
    imp = model.imp(planned)
    imp_reqs = model.imp(set(planned) - outside_defs) & model.reqs
    if "exempt restated definitions" in model.flaws:      # seeded flaw: Imp(N) & R minus D
        imp_reqs = (model.imp(planned) & model.reqs) - outside_defs
    if not imp_reqs <= Rt:
        return Decision("refused at planning", note + "the impact reaches {" + ", ".join(sorted(imp_reqs - Rt, key=nat))
                        + "} outside the scope", n_delta=n_delta, imp=imp)
    # evaluation: impacted analyses plus bootstrap for new scope members
    added = Rt - R0
    need = {x for x in imp if x in model.topo}
    need |= {a for a in model.anc(added) if a in model.topo and state.outputs.get(a) is None}
    # every quantity used by a relevant binding must have valid evidence: evaluate the far
    # end of a pair binding, and its upstream analyses, if no valid output is recorded
    rel = relevant_nodes(model, Rt, imp)
    for q, b in cand.bindings.items():
        if b.nodes() & rel or q in bind_changes:
            ends = b.nodes()
            need |= {a for a in ends | model.anc(ends) if a in model.topo and state.outputs.get(a) is None}
    run_analyses(model, cand, need)
    for r in (imp_reqs | added) - outside_defs:
        cand.verdicts[r] = evaluate_req(model, cand, r)
    for r in outside_defs:
        cand.verdicts[r] = ("unknown: definition changed outside the scope", None)
    bad = [r for r in sorted(Rt, key=nat) if cand.verdicts.get(r, ("unknown",))[0] != "pass"]
    if bad:
        def show(r):
            v, m = cand.verdicts.get(r, ("unknown", None))
            return f"{r} {v}" + (f" (margin {fmt(m)})" if m is not None else "")
        return Decision("refused after evaluation", note + "not passing in scope: " + ", ".join(map(show, bad)),
                        n_delta=n_delta, imp=imp)
    ok, why = bindings_ok(cand, relevant_nodes(model, Rt, imp), bind_changes)
    if not ok:
        return Decision("refused after evaluation", note + why, n_delta=n_delta, imp=imp)
    structural = extension or reduction or bool(req_changes) or bool(bind_changes) or bool(src_changes)
    t = tier(model, cand, imp_reqs, structural)
    detail = note + ", ".join(f"{r} {cand.verdicts[r][0]} (margin {fmt(cand.verdicts[r][1])})"
                              for r in sorted(Rt, key=nat))
    for r in sorted(outside_defs, key=nat):
        detail += f"; {r} recorded as unknown (outside the scope)"
    cand.scope = Rt
    d = Decision("admissible, awaiting approval", detail, t, None, n_delta, imp, list(ops),
                 extension or reduction, cand, state)
    if APPROVAL_LEVEL[approval] >= t:
        d.outcome, d.state = "committed", cand
    return d

def designate_baseline(model, state, approval=None):
    ok, why = model.coverage_ok()
    if not ok:
        return Decision("refused", "trace coverage: " + why)
    if state.scope != frozenset(model.reqs):
        return Decision("refused", "a baseline requires verification within R; scope is {"
                        + ", ".join(sorted(state.scope, key=nat)) + "}")
    ok, why = bindings_ok(state, set(model.inputs) | set(state.params), set(state.bindings))
    if not ok:
        return Decision("refused", why)
    bad = sorted(n for n, (_, _, prov) in state.params.items() if prov in state.retracted)
    if bad:
        return Decision("refused", "values cite retracted sources: " + ", ".join(bad))
    d = Decision("admissible, awaiting approval", "verified within R; G3 sign-off required", 3, None)
    if APPROVAL_LEVEL[approval] >= 3:
        b = state.copy(); b.baseline = True; b.name = state.name + " (baseline)"
        d.outcome, d.state, d.reason = "committed", b, "baseline designated at G3"
    return d

def retract(model, state, sid, approval=None):
    """Retraction of a registered source (an engineer's decision, tier 3). Every parameter citing
    it loses its support: the analyses and requirements downstream of those parameters lose their
    evidence, the requirements are recorded as unknown and leave the scope, and the version is
    verified within the reduced scope. Later citations of the source are rejected."""
    if sid not in state.sources or sid in state.retracted:
        return Decision("rejected at staging", f"'{sid}' is not a registered, unretracted source")
    cited = {n for n, (_, _, prov) in state.params.items() if prov == sid}
    imp = model.imp(cited)
    d = Decision("admissible, awaiting approval", "", 3, None, cited, imp)
    if APPROVAL_LEVEL[approval] < 3:
        d.reason = "retraction requires named sign-off"
        return d
    s = state.copy()
    s.retracted = state.retracted | {sid}
    for a in imp & set(model.topo):
        s.outputs[a] = None
    for r in imp & model.reqs:
        s.verdicts[r] = ("unknown: evidence rests on a retracted source", None)
    s.scope = frozenset(state.scope - imp)
    d.outcome, d.state = "committed", s
    d.reason = (f"parameters {sorted(cited, key=nat)} unsupported; scope reduced by "
                f"{sorted((imp & model.reqs) & state.scope, key=nat)}")
    return d

def audit(history, sid):
    """Versions in a history, baselines included, that recorded a value citing the source."""
    return [v.name for v in history
            if any(prov == sid for _, _, prov in v.params.values())]

def merge(model, base, d1, d2, approval="named", recheck=True):
    """Proposition 2: build the merged version by applying both derived operation lists to
    the base and taking all evidence each candidate computed from that candidate, without
    re-running any analysis; then re-check the invariants."""
    if d1.candidate is None or d2.candidate is None:
        return Decision("refused", "both candidates must be admissible")
    if d1.base is not base or d2.base is not base:
        return Decision("refused", "both candidates must be evaluated on the base version")
    if d1.scope_change or d2.scope_change:
        return Decision("refused", "candidates that change the scope are not merged")
    if any(not e.startswith("source.") and model.element_map[e][0] == "binding" for e, *_ in d1.ops + d2.ops):
        return Decision("refused", "candidates that change the binding map are not merged")
    def writes(d):
        return {e for e, *_ in d.ops}
    shared = (d1.imp & d2.imp) | (writes(d1) & writes(d2))
    if shared:
        return Decision("serialise", "shared " + ", ".join(sorted(shared, key=nat)))
    m = base.copy()
    apply_ops(model, m, d1.ops + d2.ops)
    for d in (d1, d2):                 # all evidence the candidate computed, not only its Imp
        for n, o in d.candidate.outputs.items():
            if base.outputs.get(n, "absent") is not o:
                m.outputs[n] = o
        for r, v in d.candidate.verdicts.items():
            if base.verdicts.get(r) != v:
                m.verdicts[r] = v
        m.runs.update(d.candidate.runs)
    if recheck:
        ok, why = bindings_ok(m, relevant_nodes(model, m.scope, d1.imp | d2.imp), set())
        if not ok:
            return Decision("refused", "merged version: " + why)
        bad = [r for r in m.scope if m.verdicts.get(r, ("unknown",))[0] != "pass"]
        if bad:
            return Decision("refused", "merged version: not passing " + ", ".join(sorted(bad, key=nat)))
    t = max(d1.tier, d2.tier)
    d = Decision("admissible, awaiting approval", "merged without re-analysis", t, None, candidate=m,
                 imp=d1.imp | d2.imp, ops=d1.ops + d2.ops)
    if APPROVAL_LEVEL[approval] >= t:
        d.outcome, d.state = "committed", m
    return d

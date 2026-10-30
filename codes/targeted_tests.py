"""Targeted tests of gate clauses that the randomised generator does not reach (Table 11).

Each test builds a small model, runs the gate and asserts the outcome; the script prints one line
per test and stops at the first failure. Run: python3 targeted_tests.py
"""
from fractions import Fraction as F
from admission import (Model, State, Req, Binding, admit, merge, verify_import, retract, audit,
                       designate_baseline)

def chain_model(orphan=False, bounds=None):
    """p1 -> a1 -> r1 and p2 -> a2 -> r2, with exact tools; optionally an analysis without requirement."""
    inputs = {"a1": {"p1"}, "a2": {"p2"}, "r1": {"a1"}, "r2": {"a2"}}
    topo = ["a1", "a2"]
    tools = {"a1": lambda v: {"y": v["p1"] * 2}, "a2": lambda v: {"y": v["p2"] * 3}}
    if orphan:
        inputs["a3"] = {"p1"}; topo.append("a3"); tools["a3"] = lambda v: {"y": v["p1"]}
    emap = {"e.p1": ("param", "p1"), "e.p2": ("param", "p2"), "req.r1": ("req", "r1"),
            "req.r2": ("req", "r2"), "binding.b": ("binding", "b")}
    units = {"e.p1": "m", "e.p2": "m", "req.r1": "req", "req.r2": "req", "binding.b": "binding"}
    return Model(inputs, topo, tools, emap, units, data={"e.p2"}, r_crit=set(),
                 conversions={("mm", "m"): F(1, 1000)}, bounds=bounds or {}, scale=F(1), kappa=F(1, 10))

def base(model, p1=F(1), p2=F(1), lim1=F(10), lim2=F(10)):
    sources = {"datasheet A": {"e.p2": p2}}
    s = State({"p1": (p1, "m", "decision:design"), "p2": (p2, "m", "datasheet A")},
              {"r1": Req(lim1, ("a1", "y"), "decision:G1"), "r2": Req(lim2, ("a2", "y"), "decision:G1")},
              {}, sources, name="S0")
    s = verify_import(model, s).state
    return admit(model, s, [], target_scope={"r1", "r2"}, approval="named").state

RESULTS = []
def check(name, cond, detail=""):
    assert cond, f"{name} FAILED {detail}"
    RESULTS.append(name); print(f"PASS  {name}  {detail}")

def t1_malformed_registration():
    m = chain_model(); s = base(m)
    cases = [("source.X", 5, "source", "decision:engineer", "malformed"),
             ("source.X", {"e.p2": F(2)}, "doc", "decision:engineer", "malformed"),
             ("source.X", {"e.p2": F(2)}, "source", "decision:agent", "only an engineer"),
             ("source.X", {"e.zz": F(2)}, "source", "decision:engineer", "outside the model"),
             ("source.datasheet A", {"e.p2": F(2)}, "source", "decision:engineer", "already registered")]
    for op in cases:
        d = admit(m, s, [op[:4]], approval="named")
        check(f"T1 registration rejected ({op[4]})", d.outcome == "rejected at staging" and op[4] in d.reason)

def t2_trace_coverage():
    m = chain_model(orphan=True)
    s = State({"p1": (F(1), "m", "decision:design")}, {}, {})
    d = verify_import(m, s)
    check("T2 import with an analysis that feeds no requirement rejected",
          d.outcome == "rejected at staging" and "trace coverage" in d.reason)

def t3_margin_boundary():
    m = chain_model(); s = base(m)
    d = admit(m, s, [("e.p1", F(5), "m", "decision:agent")], approval="named")       # a1 = 10 = limit
    check("T3 margin exactly zero passes, at tier 2", d.outcome == "committed" and d.tier == 2,
          f"verdict {d.state.verdicts['r1']}")
    d = admit(m, s, [("e.p1", F(5) + F(1, 10**9), "m", "decision:agent")], approval="named")
    check("T3 margin -2e-9 fails", d.outcome == "refused after evaluation")

def t4_bounds():
    m = chain_model(bounds={"e.p1": (F(0), F(4))}); s = base(m)
    check("T4 value at upper bound accepted",
          admit(m, s, [("e.p1", F(4), "m", "decision:agent")], approval="named").outcome == "committed")
    for v in (F(4) + F(1, 10**6), F(-1, 10**6)):
        d = admit(m, s, [("e.p1", v, "m", "decision:agent")], approval="named")
        check(f"T4 value {float(v):g} outside bounds rejected", d.outcome == "rejected at staging")

def t5_units():
    m = chain_model(); s = base(m)
    d = admit(m, s, [("e.p1", F(2500), "mm", "decision:agent")], approval="named")
    check("T5 mm converted exactly to m", d.outcome == "committed" and d.state.params["p1"][0] == F(5, 2))
    d = admit(m, s, [("e.p1", F(2), "deg", "decision:agent")], approval="named")
    check("T5 non-convertible unit rejected", d.outcome == "rejected at staging" and "not convertible" in d.reason)
    reg = ("source.datasheet B", {"e.p2": F(2)}, "source", "decision:engineer")
    d = admit(m, s, [reg, ("e.p2", F(2000), "mm", "datasheet B")], approval="named")
    check("T5 datum in mm matches the registered value in m", d.outcome == "committed")

def t6_retraction():
    m = chain_model(); s0 = base(m)
    reg = ("source.datasheet B", {"e.p2": F(2)}, "source", "decision:engineer")
    s1 = admit(m, s0, [reg, ("e.p2", F(2), "m", "datasheet B")], approval="named").state
    s1.name = "S1"
    b = designate_baseline(m, s1, "named").state
    d = retract(m, s1, "datasheet B", approval="engineer")
    check("T6 retraction needs named sign-off", d.outcome == "admissible, awaiting approval")
    d = retract(m, s1, "datasheet B", approval="named"); s2 = d.state; s2.name = "S2"
    check("T6 retraction reduces the scope to requirements not depending on the source",
          s2.scope == frozenset({"r1"}) and s2.verdicts["r2"][0].startswith("unknown")
          and s2.outputs["a2"] is None, d.reason)
    d = admit(m, s2, [("e.p1", F(2), "m", "decision:agent")], approval="named")
    check("T6 the reduced version still admits changes within its scope", d.outcome == "committed")
    d = admit(m, s2, [("e.p2", F(2), "m", "datasheet B")], target_scope={"r1", "r2"}, approval="named")
    check("T6 a retracted source cannot be cited", d.outcome == "rejected at staging" and "retracted" in d.reason)
    check("T6 no baseline while a value cites a retracted source",
          designate_baseline(m, s2, "named").outcome == "refused")
    check("T6 audit lists the versions and baselines that cited the source",
          audit([s0, s1, b, s2], "datasheet B") == ["S1", "S1 (baseline)", "S2"])

def t7_replacement_semantics():
    m = chain_model(); s = base(m)
    snapshot = (dict(s.params), dict(s.outputs), dict(s.verdicts), s.scope)
    admit(m, s, [("e.p1", F(50), "m", "decision:agent")], approval="named")             # refused
    check("T7 a refused attempt leaves the verified version unchanged",
          snapshot == (dict(s.params), dict(s.outputs), dict(s.verdicts), s.scope))
    d = admit(m, s, [("e.p1", F(2), "m", "decision:agent")], approval="named")         # revised attempt
    check("T7 a revised change set is evaluated afresh on S_k", d.outcome == "committed"
          and d.state.outputs["a1"][0]["y"] == F(4))

def t8_merge_approval():
    m = chain_model(); s = base(m)
    reg = ("source.datasheet C", {"e.p2": F(3)}, "source", "decision:engineer")
    d1 = admit(m, s, [("e.p1", F(2), "m", "decision:agent")], approval="named")          # approved alone
    d2 = admit(m, s, [reg, ("e.p2", F(3), "m", "datasheet C")], approval="named")       # approved alone
    dm = merge(m, s, d1, d2, approval=None)
    check("T8 approvals of the candidates do not authorise their merge",
          dm.outcome == "admissible, awaiting approval" and dm.tier == 3)

def t9_structure_change():
    m = chain_model(); s = base(m)
    d = admit(m, s, [("edge.p1->a2", True, "edge", "decision:agent")], approval="named")
    check("T9 structural changes of the trace graph are not implemented and are rejected",
          d.outcome == "rejected at staging" and "unmapped" in d.reason)

if __name__ == "__main__":
    for t in (t1_malformed_registration, t2_trace_coverage, t3_margin_boundary, t4_bounds, t5_units,
              t6_retraction, t7_replacement_semantics, t8_merge_approval, t9_structure_change):
        t()
    print(f"all {len(RESULTS)} targeted checks passed")

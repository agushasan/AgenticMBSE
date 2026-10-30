"""Admission gate on the planing-USV case study (Section 6.5, Tables 8 and 9).

Uses the generic semantics of admission.py with the trace graph of Table A.1. Values
marked FIXTURE are illustrative test inputs chosen to exercise the rules, not design
decisions or engineering data. Lengths are exact fractions of L, from the rounded values
of Table 5.

Part 1 (C1-C25) uses the tools that exist for the case (the envelope check a7; hydrostatics
and stability need mass properties, which the case data do not provide).
Part 2 (C26-C32) completes the model with FIXTURE stub tools for a1-a6 and FIXTURE limits
for R3-R10, so that full scopes, merges, serialisation, the critical tier, source registration,
the operating-condition mapping and a baseline can be exercised on the real trace graph. The stub
outputs are arbitrary formulas, not engineering results.
"""
from fractions import Fraction as F
from admission import Model, State, Req, Binding, admit, designate_baseline, verify_import, merge

INPUTS = {"a1": {"p1", "p3", "p5", "p6"}, "a2": {"p6", "a1"}, "a3": {"a1", "a2"},
          "a4": {"p2", "p4", "p7", "a5"}, "a5": {"p6", "p7", "a1", "a2"},
          "a6": {"p6", "a1", "a5"}, "a7": {"p6", "p8"},
          "R1": {"a7"}, "R2": {"a7"}, "R3": {"a1"}, "R4": {"a2"}, "R5": {"a2"},
          "R6": {"a3"}, "R7": {"a4"}, "R8": {"a5"}, "R9": {"a5"}, "R10": {"a6"}}
TOPO = ["a1", "a2", "a3", "a5", "a4", "a6", "a7"]
CONDITIONS = {"a5": "R8"}          # planing performance is evaluated at the design speed of R8

def envelope(v):                    # solid L x 0.272L (Table B.1) plus fendering on both sides
    return {"LOA": F(1), "BOA": F("0.272") + 2 * v["p8"]}

TOOLS = {"a7": envelope, "a2": lambda v: {}, "a3": lambda v: {}}   # a2, a3 need mass properties
PARAMS = {"payload.mass": "p1", "payload.power": "p2", "payload.position": "p3",
          "energy.stored": "p4", "energy.mass": "p5", "hull.solid": "p6",
          "propulsion.power": "p7", "fender.width": "p8"}
DATA = {"payload.mass", "payload.power", "energy.mass"}            # external data: need a source
ELEMENT_MAP = {e: ("param", n) for e, n in PARAMS.items()}
ELEMENT_MAP.update({f"req.R{i}": ("req", f"R{i}") for i in range(1, 11)})
ELEMENT_MAP["binding.BOA"] = ("binding", "BOA")
UNITS = {e: "L" for e in PARAMS}
UNITS.update({"payload.mass": "m0", "energy.mass": "m0", "payload.power": "kW",
              "energy.stored": "kWh", "propulsion.power": "kW", "hull.solid": "STEP"})
UNITS.update({f"req.R{i}": "req" for i in range(1, 11)})
UNITS["binding.BOA"] = "binding"

REPORTED = "reported particulars (Kumar 2026; Piehl 2026)"
G1 = "decision:G1 (FIXTURE)"
AGENT = "decision:agent"
R1_REPORTED = Req(F(1), ("a7", "LOA"), REPORTED)
R1_RESTATED = Req(F("1.02"), ("a7", "LOA"), G1)
R2_DECIDED = Req(F("0.286"), ("a7", "BOA"), G1)
R3_DECIDED = Req(F("1.3"), ("a1", "mFL"), G1)
R8_REPORTED = Req(F("1.43"), ("a5", "Fn"), REPORTED, lower=True)
BOA_BINDING = Binding("reported", ("a7", "BOA"), F("0.286"), F("0.004"), G1)
SOURCES = {"CAD solid (Table B.1)": {"hull.solid": "hull.step", "fender.width": F(0)},
           REPORTED: {"req.R1": R1_REPORTED, "req.R8": R8_REPORTED}}

L_REF = F("11.9")      # length overall in metres, rounded; used only for unit conversion
CONVERSIONS = {("m", "L"): 1 / L_REF, ("W", "kW"): F(1, 1000)}
BOUNDS = {"fender.width": (F(0), F("0.02"))}   # FIXTURE: feasibility bounds of the fender width

def model(tools=TOOLS):
    return Model(INPUTS, TOPO, tools, ELEMENT_MAP, UNITS, DATA, CONDITIONS, r_crit={"R6", "R9"},
                 conversions=CONVERSIONS, bounds=BOUNDS)

MODEL = model()

def imported():
    params = {"p6": ("hull.step", "STEP", "CAD solid (Table B.1)"),
              "p8": (F(0), "L", "CAD solid (Table B.1)")}      # the solid carries no fendering
    return State(params, {"R1": R1_REPORTED, "R8": R8_REPORTED}, {},
                 {k: dict(v) for k, v in SOURCES.items()}, name="imported")

def w(x, prov=AGENT, unit="L"):
    return ("fender.width", F(x), unit, prov)

R2_OPS = [("req.R2", R2_DECIDED, "req", G1), ("binding.BOA", BOA_BINDING, "binding", G1)]

# ------------------------------------------------------------------ fixture-completed model
def stub_tools():
    """FIXTURE stubs: arbitrary formulas that make every requirement evaluable."""
    def a1(v): return {"mFL": 1 + v["p1"] + v["p5"]}
    def a2(v): return {"T": v["a1"]["mFL"] / 20, "disp": v["a1"]["mFL"]}
    def a3(v): return {"GM": F("0.2") - v["a2"]["disp"] / 20}
    def a5(v): return {"Fn": v["p7"] / (180 * v["a1"]["mFL"]),
                       "trim": 3 + v["a1"]["mFL"] + 2 * (v["condition"] - F("1.43"))}
    def a4(v): return {"E": v["p4"] / (v["p2"] + v["p7"] / 10)}
    def a6(v): return {"acc": F("1.43") / v["a1"]["mFL"] + v["a5"]["trim"] / 100}
    return {"a1": a1, "a2": a2, "a3": a3, "a4": a4, "a5": a5, "a6": a6, "a7": envelope}

FIX_REQS = {"R3": R3_DECIDED, "R4": Req(F("0.06"), ("a2", "T"), G1), "R5": Req(F("1.2"), ("a2", "disp"), G1),
            "R6": Req(F("0.1"), ("a3", "GM"), G1, lower=True), "R7": Req(F(1), ("a4", "E"), G1, lower=True),
            "R9": Req(F(5), ("a5", "trim"), G1), "R10": Req(F("1.6"), ("a6", "acc"), G1)}

def fixture_import():
    sources = {k: dict(v) for k, v in SOURCES.items()}
    sources["FIXTURE: payload datasheet"] = {"payload.mass": F("0.04"), "payload.power": F(2)}
    sources["FIXTURE: battery datasheet"] = {"energy.mass": F("0.06")}
    params = {"p1": (F("0.04"), "m0", "FIXTURE: payload datasheet"),
              "p2": (F(2), "kW", "FIXTURE: payload datasheet"),
              "p3": (F("0.5"), "L", G1), "p4": (F(40), "kWh", G1),
              "p5": (F("0.06"), "m0", "FIXTURE: battery datasheet"),
              "p6": ("hull.step", "STEP", "CAD solid (Table B.1)"), "p7": (F(300), "kW", G1),
              "p8": (F("0.006"), "L", G1)}
    reqs = {"R1": R1_RESTATED, "R2": R2_DECIDED, "R8": R8_REPORTED, **FIX_REQS}
    return State(params, reqs, {"BOA": BOA_BINDING}, sources, name="fixture import")

def run(verbose=True):
    rows = []
    def log(case, change, d):
        rows.append((case, change, d.outcome + (f", tier {d.tier}" if d.tier else ""), d.reason))
        if verbose:
            print(f"{case:<4} {change:<66} {rows[-1][2]:<38} {d.reason}")
        return d

    s0 = verify_import(MODEL, imported()).state
    s1 = log("C1", "import and establish scope {R1}, named sign-off",
             admit(MODEL, s0, [], target_scope={"R1"}, approval="named")).state
    log("C2", "ECR-1 within {R1}", admit(MODEL, s1, [w("0.006")]))
    log("C3", "ECR-1 with extension to {R1, R2}", admit(MODEL, s1, [w("0.006")], {"R1", "R2"}, "named"))
    log("C4", "G1 decision on R2 with extension, without ECR-1", admit(MODEL, s1, R2_OPS, {"R1", "R2"}, "named"))
    log("C5", "decision, ECR-1, extension; width citing an unregistered drawing",
        admit(MODEL, s1, R2_OPS + [w("0.006", "Smith (2025) fender drawing")], {"R1", "R2"}, "named"))
    log("C6", "as C5, width citing the CAD solid",
        admit(MODEL, s1, R2_OPS + [w("0.006", "CAD solid (Table B.1)")], {"R1", "R2"}, "named"))
    run_id = s1.outputs["a7"][1]
    log("C7", "as C5, width citing the envelope-check run as its source",
        admit(MODEL, s1, R2_OPS + [w("0.006", run_id)], {"R1", "R2"}, "named"))
    log("C8", "as C5, width 0.006 meant as 0.006L but labelled in metres",
        admit(MODEL, s1, R2_OPS + [w("0.006", unit="m")], {"R1", "R2"}, "named"))
    log("C9", "as C5, width 0.006L proposed as a decision, no sign-off",
        admit(MODEL, s1, R2_OPS + [w("0.006")], {"R1", "R2"}))
    s2 = log("C10", "as C9, named sign-off", admit(MODEL, s1, R2_OPS + [w("0.006")], {"R1", "R2"}, "named")).state
    log("C11", "ECR-2, payload mass estimated by the agent",
        admit(MODEL, s2, [("payload.mass", F("0.05"), "m0", AGENT)]))
    log("C12", "change asserting that R2 passes", admit(MODEL, s2, [("verdict.R2", "pass", "verdict", AGENT)]))
    ops = [w("0.006"), ("hull.solid", "hull-rev2.step", "STEP", "decision:CAD agent")]
    trusted = admit(MODEL, s2, ops, declared={"p8"}, trust_declared=True, approval="named")
    d = admit(MODEL, s2, ops, declared={"p8"}, approval="named")
    d.reason += f" [if the declaration were trusted: {trusted.outcome}]"
    log("C13", "change declaring p8 only, also writing the hull solid", d)
    log("C14", "ECR-2 writing a crane property with no node",
        admit(MODEL, s2, [("lars.crane.slew_rate", F(5), "deg/s", AGENT)]))
    log("C15", "extension to R7-R10 for ECR-3",
        admit(MODEL, s2, [], target_scope=s2.scope | {"R7", "R8", "R9", "R10"}, approval="named"))
    s3 = log("C16", "G1 decision recording a limit for R3, outside the scope",
             admit(MODEL, s2, [("req.R3", R3_DECIDED, "req", G1)], approval="named")).state
    log("C17", "fender width 0.008L", admit(MODEL, s3, [w("0.008")], approval="engineer"))
    s4 = log("C18", "fender width 0.0055L, engineer approval", admit(MODEL, s3, [w("0.0055")], approval="engineer")).state
    s5 = log("C19", "G1 decision restating R1 with limit 1.02L, named sign-off",
             admit(MODEL, s4, [("req.R1", R1_RESTATED, "req", G1)], approval="named")).state
    s6 = log("C20", "fender width 0.006L, no approval", admit(MODEL, s5, [w("0.006")])).state
    s7 = log("C21", "scope reduction to {R1}, named sign-off", admit(MODEL, s6, [], target_scope={"R1"}, approval="named")).state
    log("C22", "fender width 0.005L after the reduction", admit(MODEL, s7, [w("0.005")], approval="named"))
    log("C23", "designate a baseline from the version of C20", designate_baseline(MODEL, s6, "named"))
    log("C24", "as C22, also restating R2's definition",
        admit(MODEL, s7, [w("0.005"), ("req.R2", R2_DECIDED, "req", G1)], approval="named"))
    R3_MISREAD = Req(F("0.3"), ("a7", "BOA"), G1)
    log("C25", "redefinition of R3 reading the beam instead of mass properties",
        admit(MODEL, s6, [("req.R3", R3_MISREAD, "req", G1)], approval="named"))
    if verbose:
        print("verdicts carried after C21:", {r: s7.verdicts[r][0] for r in ("R2", "R3")})

    # ---------------------------------------------------------- part 2: fixture-completed model
    MF = model(stub_tools())
    f0 = verify_import(MF, fixture_import()).state
    f1 = log("C26", "fixture-completed model: establish the scope R, named sign-off",
             admit(MF, f0, [], target_scope=set(MF.reqs), approval="named")).state
    f2 = log("C27", "designate a baseline, named sign-off at G3", designate_baseline(MF, f1, "named")).state
    ecr1 = admit(MF, f2, [w("0.0055")])
    ecr3 = admit(MF, f2, [("propulsion.power", F(320), "kW", AGENT)])
    if verbose:
        print(f"     ECR-1 alone: {ecr1.outcome}, tier {ecr1.tier}; ECR-3 alone: {ecr3.outcome}, tier {ecr3.tier}")
    f3 = log("C28", "ECR-1 (0.0055L) and ECR-3 (320 kW) evaluated separately, merged",
             merge(MF, f2, ecr1, ecr3, approval="named")).state
    reg = ("source.FIXTURE: payload datasheet rev B", {"payload.mass": F("0.05")}, "source", "decision:engineer")
    ecr2 = [reg, ("payload.mass", F("0.05"), "m0", "FIXTURE: payload datasheet rev B")]
    log("C29", "ECR-2 and ECR-3 evaluated separately, merge attempted",
        merge(MF, f2, admit(MF, f2, ecr2), ecr3, approval="named"))
    f4 = log("C30", "ECR-2 registering payload datasheet rev B and citing it",
             admit(MF, f3, ecr2, approval="named")).state
    log("C31", "re-registering the payload datasheet with a different mass",
        admit(MF, f4, [("source.FIXTURE: payload datasheet", {"payload.mass": F("0.05")}, "source",
                        "decision:engineer")], approval="named"))
    R8_FASTER = Req(F("1.5"), ("a5", "Fn"), G1, lower=True)
    d = log("C32", "G1 decision raising the design speed of R8 to Fn 1.5",
            admit(MF, f4, [("req.R8", R8_FASTER, "req", G1)], approval="named"))
    if True:
        if verbose: print("     N_Delta of C32:", sorted(d.n_delta), "; Imp & R:", sorted(d.imp & MF.reqs, key=lambda x: int(x[1:])))
        mf_flaw = model(stub_tools()); mf_flaw.flaws = {"ignore conditions"}
        dd = admit(mf_flaw, f4, [("req.R8", R8_FASTER, "req", G1)], approval="named")
        stale = [a for a in MF.topo if dd.state.outputs[a][0] != d.state.outputs[a][0]]
        print(f"     without the condition mapping: N_Delta {sorted(dd.n_delta)}, {dd.outcome}; "
              f"stale outputs of {', '.join(stale)}, computed at the old design speed")
        # C28 check from scratch: import the model with both changes applied and evaluate everything
        imp = fixture_import()
        imp.params["p8"] = (F("0.0055"), "L", AGENT); imp.params["p7"] = (F(320), "kW", AGENT)
        full = admit(MF, verify_import(MF, imp).state, [], target_scope=set(MF.reqs), approval="named").state
        same = all(f3.outputs[a][0] == full.outputs[a][0] for a in MF.topo) and \
            all(f3.verdicts[r] == full.verdicts[r] for r in MF.reqs)
        print(f"     C28 check: merged version equals a from-scratch evaluation of both changes: {same}")
        assert same and sorted(d.n_delta) == ["R8", "a5"] and stale == ["a5", "a6"]
    log("C33", "as C10, width given as 0.0714 m", admit(MODEL, s1, R2_OPS + [w("0.0714", unit="m")], {"R1", "R2"}, "named"))
    log("C34", "as C10, width 0.06L (a decimal slip)", admit(MODEL, s1, R2_OPS + [w("0.06")], {"R1", "R2"}, "named"))
    if verbose:
        transcript(MF, f2, ecr1, ecr3)
    return rows

def transcript(MF, base, d1, d2):
    """A replayable record of the C28 merge (written to merge_transcript.txt)."""
    out = []
    def p(x=""): out.append(x)
    p(f"base version: {base.name}, scope R1-R10, baseline designated: {base.baseline}")
    for k, d in (("candidate 1 (ECR-1)", d1), ("candidate 2 (ECR-3)", d2)):
        new = sorted(set(d.candidate.runs) - set(base.runs), key=lambda x: int(x.split("-")[1]))
        p(f"{k}: ops {[(e, float(v), u, pr) for e, v, u, pr in d.ops]}")
        p(f"  N_Delta {sorted(d.n_delta)}; Imp {sorted(d.imp, key=lambda x: (x[0], int(x[1:])))}")
        p(f"  new tool runs {new}; outcome {d.outcome}, tier {d.tier} (approval not carried into the merge)")
    m = merge(MF, base, d1, d2, approval=None)
    p(f"merge without approval: {m.outcome}, tier {m.tier}")
    m = merge(MF, base, d1, d2, approval="named")
    runs_new = set(m.state.runs) - set(d1.candidate.runs) - set(d2.candidate.runs)
    p(f"merge with named sign-off: {m.outcome}, tier {m.tier}; tool runs created by the merge: {len(runs_new)}")
    p("  evidence reused: " + ", ".join(f"{a}<-{m.state.outputs[a][1]}" for a in MF.topo))
    p("  invariants re-checked: binding BOA, in-scope verdicts R1-R10 (all pass)")
    open("merge_transcript.txt", "w").write("\n".join(out) + "\n")
    print("\n".join("     " + x for x in out))

EXPECTED = {"C1": "committed, tier 3", "C2": "refused at planning", "C3": "refused at planning",
            "C4": "refused after evaluation", "C5": "rejected at staging", "C6": "rejected at staging",
            "C7": "rejected at staging", "C8": "refused after evaluation", "C9": "admissible, awaiting approval, tier 3",
            "C10": "committed, tier 3", "C11": "rejected at staging", "C12": "rejected at staging",
            "C13": "refused at planning", "C14": "rejected at staging", "C15": "refused at planning",
            "C16": "committed, tier 3", "C17": "refused after evaluation", "C18": "committed, tier 2",
            "C19": "committed, tier 3", "C20": "committed, tier 1", "C21": "committed, tier 3",
            "C22": "refused at planning", "C23": "refused", "C24": "refused at planning",
            "C25": "rejected at staging", "C26": "committed, tier 3", "C27": "committed, tier 3",
            "C28": "committed, tier 3", "C29": "serialise", "C30": "committed, tier 3",
            "C31": "rejected at staging", "C32": "committed, tier 3",
            "C33": "committed, tier 3", "C34": "rejected at staging"}   # derived by hand from Defs. 4-5

if __name__ == "__main__":
    rows = run()
    bad = [(c, o) for c, _, o, _ in rows if EXPECTED[c] != o]
    assert len(rows) == len(EXPECTED) and not bad, bad
    print(f"all {len(rows)} outcomes match the expected outcomes derived by hand")

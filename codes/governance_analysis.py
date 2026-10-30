"""Deterministic governance analysis on the case-study trace graph (Table A.1).

Computes from the trace graph, the requirement status of Table 3 and the tool status
of Section 4.3:
  * impact sets Imp(Delta) and reuse ratios (Eqs. 2-3),
  * pairwise non-interference of change requests (Proposition 2),
  * commit prerequisites under Definition 5: requirements in the impact set without an
    instantiated limit; analyses without an implemented tool, both in the impact set and
    among its upstream analyses, whose evidence Proposition 1 reuses; inputs to source,
  * the minimum risk tier under Eq. (7), given an illustrative R_crit and the zero
    margin of R1 (its limit is the reported length, which the solid matches exactly).
The data to source are the external data among the changed parameters (Definition 4);
design values (fender width, payload position, stored energy, installed power) are
decisions and need no source.
"""
from itertools import combinations

INPUTS = {"a1": ["p1", "p3", "p5", "p6"], "a2": ["p6", "a1"], "a3": ["a1", "a2"],
          "a4": ["p2", "p4", "p7", "a5"], "a5": ["p6", "p7", "a1", "a2"],
          "a6": ["p6", "a1", "a5"], "a7": ["p6", "p8"]}
EVIDENCE = {"a1": ["R3"], "a2": ["R4", "R5"], "a3": ["R6"], "a4": ["R7"],
            "a5": ["R8", "R9"], "a6": ["R10"], "a7": ["R1", "R2"]}

INSTANTIATED = {"R1", "R8"}            # limits stated in the published design (Table 3)
IMPLEMENTED = {"a2", "a3", "a7"}       # hydrostatics, static stability, envelope (Sec. 4.3)
ZERO_MARGIN = {"R1"}                   # limit equals the reported length (Sec. 6.4)
R_CRIT = {"R6", "R9"}                  # illustrative: stability and porpoising
DATA = {"p1": "payload mass", "p2": "payload power", "p5": "storage mass"}   # external data
ECRS = {"ECR-1": {"mods": ["p8"]}, "ECR-2": {"mods": ["p1", "p2", "p3"]},
        "ECR-3": {"mods": ["p7"]}, "ECR-4": {"mods": ["p4", "p5"]}}

succ, pred = {}, {}
for a, ins in INPUTS.items():
    for i in ins:
        succ.setdefault(i, []).append(a); pred.setdefault(a, []).append(i)
for a, rs in EVIDENCE.items():
    for r in rs:
        succ.setdefault(a, []).append(r); pred.setdefault(r, []).append(a)

def closure(start, nbr):
    seen, stack = set(start), list(start)
    while stack:
        for m in nbr.get(stack.pop(), []):
            if m not in seen:
                seen.add(m); stack.append(m)
    return seen

key = lambda s: (s[0], int(s[1:]))
imp = {k: closure(v["mods"], succ) for k, v in ECRS.items()}

print("Impact sets and reuse ratios")
for k, s in imp.items():
    A = sorted((x for x in s if x in INPUTS), key=key)
    R = sorted((x for x in s if x[0] == "R"), key=key)
    print(f"  {k}: analyses {A}; requirements {R}; eta = {1 - len(A) / 7:.2f}")

print("\nPairwise non-interference (disjoint impact sets)")
for (k1, s1), (k2, s2) in combinations(imp.items(), 2):
    shared = sorted(s1 & s2, key=key)
    print(f"  {k1} / {k2}: " + ("independent" if not shared else "interfering via " + ", ".join(shared)))

print("\nCommit prerequisites (Definition 5)")
for k, s in imp.items():
    R = sorted((x for x in s if x[0] == "R"), key=key)
    A_imp = {x for x in s if x in INPUTS}
    A_up = {x for x in closure(A_imp, pred) if x in INPUTS} - A_imp   # reused upstream evidence
    tools = sorted((A_imp | A_up) - IMPLEMENTED, key=key)
    inputs = [DATA[p] for p in ECRS[k]["mods"] if p in DATA] + (["component masses for a1"] if "a1" in tools else [])
    tier = 3 if set(R) & R_CRIT else (2 if set(R) & ZERO_MARGIN else 1)
    print(f"  {k}: scope {R}; limits to decide {[r for r in R if r not in INSTANTIATED]}; "
          f"tools {tools}; data to source {inputs or 'none'}; minimum tier {tier}")

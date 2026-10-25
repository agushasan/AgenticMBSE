"""Inputs to the case study, all taken from the two cited studies of the same vessel; none is derived
from the CAD model, which is not part of this repository.
  [K] A. Kumar, P. Loizou, OMAE2026-175759 (straked hull, sea water)
  [P] H. Piehl et al., OMAE2026-181881 (flat-hull variant, fresh water)

Dimensional inputs (length, beam, depth, draft, displacement, KG, heave) are read from
data/case_inputs.json, which is not committed (see case_inputs.example.json and the README).
Quantities derived from the CAD model are computed by the scripts, never hard-coded.
"""
import json, os
from paths import ROOT
_f=os.environ.get('LX_INPUTS',os.path.join(ROOT,'data','case_inputs.json'))
if not os.path.isfile(_f):
    raise SystemExit('Missing %s: copy case_inputs.example.json to data/case_inputs.json and fill it in.'%_f)
_d=json.load(open(_f))
L, B, D, T, M0, KG = (float(_d[k]) for k in ('L','B','D','T','M0','KG'))
HEAVE_P = {float(k): float(v) for k, v in _d['HEAVE_P'].items()}

# Non-dimensional or non-identifying inputs
LCG_DESIGN = 0.28                    # LCG as fraction of L from the transom (preliminary)     [K]
LCG_STUDIED = (0.28, 0.30, 0.32, 0.34)                                                    # [K, P]
RHO_SEA, RHO_FRESH, RHO_K = 1025.0, 997.56, 1025.9          # kg/m3; [P] fresh, [K] sea
# hydrostatic (static) trim of the flat-hull variant at M0 in fresh water, deg   [P, Table 2]
STATIC_TRIM_P = {0.28: -2.06, 0.30: -1.34, 0.32: -0.67, 0.34: -0.06}
# CFD running trim of the straked hull at the design speed, LCG 0.28 L, deg      [K], [P]
RUNNING_TRIM = {'K': -0.034, 'P': -3.58}

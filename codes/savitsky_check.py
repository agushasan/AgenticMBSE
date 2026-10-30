"""Indicative Savitsky (1964) running-trim estimate for the straked hull at the design speed
(Section 6.2). Trim is printed in degrees bow-up, that is by the stern, which is
negative in the sign convention of Fig. 5d.

Inputs are the non-dimensional values reported in the paper: length Froude number 1.43,
volumetric Froude number 3.6, deadrise 14 deg, LCG 0.28L from the transom. The chine
beam b is not reported; the range brackets the waterline beam at rest (0.265L).
Replace B_OVER_L with the chine beam measured on the CAD solid.
Thrust and drag moments are neglected, so the result is indicative only.
"""
import math

FN_L, FN_VOL, BETA, LCG_L = 1.43, 3.6, 14.0, 0.28
B_OVER_L = [0.25, 0.26, 0.27]

def trim(b_l):
    vol_l3 = (FN_L**2 / FN_VOL**2) ** 3               # (displaced volume)/L^3
    cv = FN_L / math.sqrt(b_l)                        # speed coefficient
    cl_beta = 2 * vol_l3 / (FN_L**2 * b_l**2)         # load coefficient
    lo, hi = cl_beta, 1.0                             # deadrise correction -> CL0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (lo, m) if m - 0.0065 * BETA * m**0.6 > cl_beta else (m, hi)
    cl0, lcg_b = lo, LCG_L / b_l
    def lam(tau):                                     # mean wetted length/beam from lift
        lo, hi = 1e-3, 50.0
        for _ in range(200):
            m = 0.5 * (lo + hi)
            f = tau**1.1 * (0.012 * m**0.5 + 0.0055 * m**2.5 / cv**2) - cl0
            lo, hi = (m, hi) if f < 0 else (lo, m)
        return lo
    def cp_minus_lcg(tau):                            # centre of pressure minus LCG (in beams)
        l = lam(tau)
        return l * (0.75 - 1.0 / (5.21 * cv**2 / l**2 + 2.39)) - lcg_b
    lo, hi = 0.5, 15.0
    for _ in range(200):
        m = 0.5 * (lo + hi)
        lo, hi = (m, hi) if cp_minus_lcg(m) > 0 else (lo, m)
    return lo, lam(lo), cv

for b in B_OVER_L:
    t, l, cv = trim(b)
    print(f"b/L = {b:.2f}: C_V = {cv:.2f}, lambda = {l:.2f}, running trim = {t:.1f} deg bow-up")

# Agentic AI in model-based systems engineering: code for the paper

This repository holds the Python code behind the computed results and figures of the paper
*Leveraging Agentic AI in Model-Based Systems Engineering*. The case study is the Lorelei-X
uncrewed surface vessel. All scripts are in `codes/`.

## 1. Admission gate and its tests (no CAD model needed)

These scripts need only the Python standard library. They reproduce Sections 6.3–6.6, Tables 6–11
and Appendix D, and each one writes the log that ships next to it.

| Script | Reproduces | Log |
|---|---|---|
| `admission.py` | The admission gate (Definitions 4–5, Eq. 7, Propositions 1–2); imported by the scripts below | – |
| `case_gate.py` | The 34 scripted cases of Tables 8–9 (checks every outcome) and the merge transcript of Appendix D | `case_gate_log.txt`, `merge_transcript.txt` |
| `property_tests.py` | The 20,000 randomised cases, seeded flaws and ablation of Table 10 | `property_log.txt` |
| `targeted_tests.py` | Targeted tests T1–T9 of Table 11 | `targeted_log.txt` |
| `governance_analysis.py` | Impact sets, interference and commit prerequisites (Tables 6–7) | `governance_log.txt` |
| `savitsky_check.py` | Savitsky running-trim estimate (Section 6.2) | `savitsky_log.txt` |
| `llm_trial.py` | Harness that passes typed proposals of a local LLM through the gate (Section 5); not used for any result in the paper; see `RUN_LLM_TRIAL.md` | – |

```bash
cd codes
python3 case_gate.py
python3 targeted_tests.py
python3 property_tests.py          # about two minutes
python3 governance_analysis.py
python3 savitsky_check.py
python3 property_tests.py --run 1 --case 13668   # replay one randomised case
```

Run the scripts with plain `python3` from `codes/`. Do not use `python3 -I`, because they import
`admission.py` from that folder. Their output should match the logs exactly.

## 2. Hydrostatics and figures (CAD model needed)

These scripts need the STEP file of the hull, which belongs to its owner and is not in this
repository. They also need the case inputs taken from the two cited studies.

| Script | Produces | Used for |
|---|---|---|
| `stepgeom.py` | – | Minimal STEP AP214 reader for B-spline B-rep solids and trimmed tessellation (no CAD kernel) |
| `tessellate.py` | `mesh.pkl`, `mesh_coarse.pkl` | Triangulation of the hull solid |
| `hydro.py`, `sections.py` | – | Hydrostatics by clipping at a trimmed waterplane; plane sections |
| `equil.py` | `hydro.json` | Even-keel draft and free-trim equilibrium at the reported displacement (sea and fresh water) |
| `raycheck.py` | `raycheck.json` | Independent check of the hydrostatics by vertical ray casting |
| `review_checks.py` | `review_checks.json` | Transom draft against mass, sensitivity to the KG datum, deadrise by station |
| `convergence.py` | `convergence.json` | Tessellation convergence of the enclosed volume |
| `tracegraph.py` | `impact.json` | Case-study trace graph, impact sets and reuse ratio of the four change requests |
| `export_section.py`, `render_hull.py` | `section.json`, `hull_iso.pdf`, `hull_anchors.json` | Inputs to Figure 3 |
| `fig_lines.py` | `fig4_lines.pdf` | Figure 4 (lines plan) |
| `fig_checks.py` | `fig5_checks.pdf` | Figure 5 (hydrostatic checks) |
| `gen_vessel.py` | `figures/fig3_vessel.tex` | Figure 3 (TikZ) |
| `gen_tracegraph.py` | `figures/fig6_tracegraph.tex` | Figure 6 (TikZ) |

`case_data.py` reads the case inputs, `paths.py` sets the file locations and `style.py` sets the
plotting style. `figures/` holds the TikZ sources of Figures 1 and 2, the graphical abstract and
the shared style file `lxstyle.tex`.

```bash
pip install -r requirements.txt
mkdir -p data
cp /path/to/hull.stp data/hull.stp
cp case_inputs.example.json data/case_inputs.json   # then fill in the values
./run_all.sh
```

You can set other file locations with the environment variables `LX_STEP`, `LX_INPUTS` and
`LX_OUT`. A full run takes about three minutes on a laptop and also needs a LaTeX installation
with TikZ. Results go to `out/`, and the figures go to `out/` (Figures 4 and 5) and `figures/`
(Figures 1, 2, 3, 6 and the graphical abstract).

Tested with Python 3.13, NumPy 2.5.3, SciPy 1.18.1 and Matplotlib 3.11.2. The scripts in
section 1 use only the standard library and were tested with Python 3.13.

## Licence

GNU General Public License v3.0 (see `LICENSE`).

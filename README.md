# Agentic AI-assisted MBSE: case-study code

This repository holds the Python code sources used for the computed results and the figures of the paper on agentic AI-assisted model-based systems engineering (MBSE), with the Lorelei-X uncrewed surface vessel as the case study.

## What is in here

| Script (`src/`) | Produces | Used for |
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
| `fig_lines.py` | `fig4_lines.pdf` | Figure 4 (lines plan, non-dimensional) |
| `fig_checks.py` | `fig5_checks.pdf` | Figure 5 (hydrostatic checks, non-dimensional) |
| `gen_vessel.py` | `figures/fig3_vessel.tex` | Figure 3 (TikZ) |
| `gen_tracegraph.py` | `figures/fig6_tracegraph.tex` | Figure 6 (TikZ) |

`case_data.py` holds the inputs taken from the two cited studies of the vessel; `paths.py` sets
the file locations; `style.py` sets the plotting style. `figures/` has the TikZ sources of
Figures 1 and 2 and the graphical abstract, and the shared style file `lxstyle.tex`.

## Running

Requires Python 3.10 or newer and a LaTeX installation with TikZ (for the figures).

```bash
pip install -r requirements.txt
mkdir -p data
cp /path/to/hull.stp data/hull.stp
cp case_inputs.example.json data/case_inputs.json   # then fill in the values
./run_all.sh
```

Other locations can be given with the environment variables `LX_STEP`, `LX_INPUTS` and `LX_OUT`. A full run takes about three minutes on a laptop. Results are written to `out/`, and the figure PDFs to `out/` (Figures 4 and 5) and `figures/` (Figures 1, 2, 3, 6 and the graphical abstract).

Tested with Python 3.13, NumPy 2.5.3, SciPy 1.18.1 and Matplotlib 3.11.2.

## Licence

To be chosen by the authors before publication (for example MIT or BSD-3-Clause for the code).

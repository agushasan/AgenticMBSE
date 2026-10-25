#!/usr/bin/env bash
# Reproduce the computed results and Figures 3-6 of the paper.
# Needs data/hull.stp and data/case_inputs.json (neither is in the repository; see README).
# Other locations: LX_STEP=/path/hull.stp LX_INPUTS=/path/case_inputs.json [LX_OUT=/path/out] ./run_all.sh
set -euo pipefail
cd "$(dirname "$0")/src"
: "${LX_STEP:=../data/hull.stp}"; export LX_STEP
if [ ! -f "$LX_STEP" ]; then echo "STEP file not found: $LX_STEP (see README)"; exit 1; fi
: "${LX_INPUTS:=../data/case_inputs.json}"; export LX_INPUTS
if [ ! -f "$LX_INPUTS" ]; then echo "Inputs not found: $LX_INPUTS (copy case_inputs.example.json, see README)"; exit 1; fi
for s in tessellate equil raycheck review_checks convergence tracegraph \
         export_section render_hull fig_lines fig_checks gen_vessel gen_tracegraph; do
  echo "== $s"; python3 "$s.py"
done
cd ../figures
for f in fig1_concept fig2_framework fig3_vessel fig6_tracegraph graphical_abstract; do
  pdflatex -interaction=nonstopmode -halt-on-error "$f.tex" >/dev/null && echo "built figures/$f.pdf"
done

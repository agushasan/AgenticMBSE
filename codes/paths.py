"""Central paths. Set LX_STEP to the STEP file of the hull and, optionally, LX_OUT for outputs."""
import os
HERE=os.path.dirname(os.path.abspath(__file__))
ROOT=os.path.dirname(HERE)
STEP=os.environ.get('LX_STEP',os.path.join(ROOT,'data','hull.stp'))
OUT=os.environ.get('LX_OUT',os.path.join(ROOT,'out'))+os.sep
FIGS=os.path.join(ROOT,'figures')+os.sep
os.makedirs(OUT,exist_ok=True)

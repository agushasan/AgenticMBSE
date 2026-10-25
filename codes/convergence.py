"""Tessellation convergence of the enclosed volume (recorded for the paper)."""
import numpy as np, json, stepgeom as sg
from paths import STEP, OUT
E=sg.load(STEP); F=sg.faces(E); res={}
for n in [24,30,45,70]:
    Vs=[];Ts=[];off=0
    for f in F:
        X,T=sg.tessellate(f,n); Vs.append(X);Ts.append(T+off);off+=len(X)
    V=np.vstack(Vs);T=np.vstack(Ts);a,b,c=V[T[:,0]],V[T[:,1]],V[T[:,2]]
    res[n]=float(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6)
ref=res[70]; res['max_rel_dev_n30_to_70']=max(abs(res[n]-ref)/ref for n in [30,45])
print(res); json.dump(res,open(OUT+'convergence.json','w'),indent=1)

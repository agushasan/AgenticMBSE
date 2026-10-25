"""Step 2: hydrostatics at the reported displacement: even-keel draft and trimmed equilibrium
for the studied LCG positions, in sea and fresh water (hydro.json)."""
from paths import OUT
import numpy as np, json
from scipy.optimize import brentq, fsolve
from hydro import *
import case_data as cd
L,KG,m=cd.L,cd.KG,cd.M0
out={}
for rho,tag in [(cd.RHO_SEA,'sea'),(cd.RHO_FRESH,'fresh')]:
    nab=m/rho
    Tek=brentq(lambda t: submerged(t)[0]-nab,0.2,1.2,xtol=1e-5)
    v,c,S,_=submerged(Tek)
    wp=waterplane(Tek)
    BMT=wp['IT']/v; BML=wp['IL']/v
    out[tag]=dict(rho=rho,nabla=nab,T_evenkeel=Tek,LCB=c[0],KB=c[2],S=S,LWL=wp['LWL'],BWL=wp['BWL'],
                  Awp=wp['Awp'],LCF=wp['LCF'],BMT=BMT,BML=BML,GMT=c[2]+BMT-KG,GML=c[2]+BML-KG)
    eq={}
    for f in cd.LCG_STUDIED:
        G=np.array([f*L,0,KG])
        def res(p):
            T0,th=p
            v,c,_,_=submerged(T0,th,xr=G[0])
            return [v-nab,(c[0]-G[0])*np.cos(th)+(c[2]-G[2])*np.sin(th)]
        T0,th=fsolve(res,[Tek,0.0],xtol=1e-7)
        Ta=T0+(0-G[0])*np.tan(th)           # draft at the transom (x = 0); keel at z = 0
        eq[f]=dict(LCG=G[0],T_at_LCG=T0,trim_deg=np.degrees(th),T_transom=Ta,res=res([T0,th]))
    out[tag]['eq']=eq
    v70,c70,_,_=submerged(cd.T)              # displacement at the reported draft, even keel
    out[tag]['disp_at_T_reported_t']=v70*rho/1000
json.dump(out,open(OUT+'hydro.json','w'),indent=1,default=float)
print(json.dumps(out,indent=1,default=float))

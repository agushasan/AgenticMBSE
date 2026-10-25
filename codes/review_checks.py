"""Additional checks: transom draft against mass at the design LCG, sensitivity to the datum of the
vertical centre of gravity, offset to the hydrostatic heave reported in [P], and deadrise by station
(slope of the bottom next to the keel, |y| between 0.0025 L and 0.0235 L, fitted to the lowest
section points). Writes review_checks.json."""
import numpy as np, json, pickle
from scipy.optimize import fsolve, brentq
from paths import OUT, STEP
from hydro import submerged
from sections import section
import case_data as cd
L=cd.L; KG=cd.KG; M0=cd.M0
def eq(m,rho,f,KG):
    nab=m/rho; G=np.array([f*L,KG])
    def res(p):
        v,c,_,_=submerged(p[0],p[1],xr=G[0]); return [v-nab,(c[0]-G[0])*np.cos(p[1])+(c[2]-G[1])*np.sin(p[1])]
    T0,th=fsolve(res,[0.5,-0.02],xtol=1e-9)
    return T0,np.degrees(th),T0-G[0]*np.tan(th)
out={}
# (a) transom draft vs mass at the design LCG, sea water
ms=np.arange(3000,16001,1000); curve=[]
for m in ms:
    T0,tr,Tt=eq(m,cd.RHO_SEA,cd.LCG_DESIGN,KG); curve.append((m/1000,Tt,tr))
out['transom_curve']=curve
m70=brentq(lambda m: eq(m,cd.RHO_SEA,cd.LCG_DESIGN,KG)[2]-cd.T,M0,2*M0,xtol=1)
out['mass_for_transom_at_T_t']=m70/1000
out['transom_at_M0_sea']=eq(M0,cd.RHO_SEA,cd.LCG_DESIGN,KG)[2]
out['transom_at_M0_rhoK']=eq(M0,cd.RHO_K,cd.LCG_DESIGN,KG)[2]
H=json.load(open(OUT+'hydro.json'))
# (c) hydrostatic heave reported in [P, Table 2] vs computed fresh-water draft at the LCG
piehl_heave=cd.HEAVE_P
out['heave_offset']={f:piehl_heave[f]-H['fresh']['eq'][str(f)]['T_at_LCG'] for f in piehl_heave}
# (b) VCG datum sensitivity: KG lowered by the mean offset to the heave reported in [P]
dKG=float(np.mean(list(out['heave_offset'].values())))
out['trim_fresh_KG_lowered']={f:eq(M0,cd.RHO_FRESH,f,KG-dKG)[1] for f in cd.LCG_STUDIED}
out['GMT_sea_KG_lowered']=H['sea']['GMT']+dKG; out['KG_offset']=dKG
# (d) deadrise by station (stations as fractions of L)
y0,y1=0.0025*L,0.0235*L
dr={}
for fx in [0.04,0.08,0.17,0.25,0.34,0.42,0.43,0.44,0.45,0.46,0.50,0.59]:
    x=fx*L
    S=section(x).reshape(-1,3); P=S[(S[:,1]>y0)&(S[:,1]<y1)]
    if len(P)<4: continue
    # lowest z per y bin = bottom
    yb=np.linspace(y0,y1,11); pts=[]
    for i in range(10):
        m=(P[:,1]>=yb[i])&(P[:,1]<yb[i+1])
        if m.any(): j=np.argmin(P[m,2]); pts.append(P[m][j,1:])
    pts=np.array(pts); dr[fx]=float(np.degrees(np.arctan(np.polyfit(pts[:,0],pts[:,1],1)[0])))
out['deadrise_deg_by_x']=dr
json.dump(out,open(OUT+'review_checks.json','w'),indent=1,default=float)
print(json.dumps(out,indent=1,default=float))

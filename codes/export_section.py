"""Export the half-section at x = 0.378 L (prismatic aft body) as an ordered polyline for the
vessel figure (Figure 3b)."""
import numpy as np, json
from sections import section
from paths import OUT
import case_data as cd
XS=0.378
S=section(XS*cd.L); S=S[(S[:,:,1]>=-1e-6).all(1)]  # starboard-agnostic: take y>=0 half
segs=[s[:,1:] for s in S]  # (y,z)
# greedy chaining
segs=[np.array(s) for s in segs]; chain=[segs.pop(0)]
pts=list(chain[0])
while segs:
    end=pts[-1]; d=[min(np.linalg.norm(s[0]-end),np.linalg.norm(s[1]-end)) for s in segs]; j=int(np.argmin(d))
    if d[j]>0.02:
        start=pts[0]; d2=[min(np.linalg.norm(s[0]-start),np.linalg.norm(s[1]-start)) for s in segs]; j2=int(np.argmin(d2))
        if d2[j2]<0.02:
            s=segs.pop(j2); s=s if np.linalg.norm(s[1]-start)<np.linalg.norm(s[0]-start) else s[::-1]; pts.insert(0,s[0]); continue
        break
    s=segs.pop(j); s=s if np.linalg.norm(s[0]-end)<np.linalg.norm(s[1]-end) else s[::-1]; pts.append(s[1])
P=np.array(pts); P_raw=P.copy()
# simplify: drop nearly collinear points
keep=[0]
for i in range(1,len(P)-1):
    a,b,c=P[keep[-1]],P[i],P[i+1]
    u_=b-a; w_=c-b
    if abs(u_[0]*w_[1]-u_[1]*w_[0])>1e-6 or np.linalg.norm(b-a)>0.15: keep.append(i)
keep.append(len(P)-1); P=P[keep]
print('points',len(P),'leftover segs',len(segs),'y range',P[:,0].min(),P[:,0].max(),'z',P[:,1].min(),P[:,1].max())
# deadrise of the bottom next to the keel
Q=P_raw; m=(Q[:,0]>0.0025*cd.L)&(Q[:,0]<0.0235*cd.L)&(Q[:,1]<0.0085*cd.L)
dr=float(np.degrees(np.arctan(np.polyfit(Q[m,0],Q[m,1],1)[0])))
print('deadrise',dr)
json.dump(dict(x_over_L=XS,deadrise_deg=dr,pts=P.tolist()),open(OUT+'section.json','w'))

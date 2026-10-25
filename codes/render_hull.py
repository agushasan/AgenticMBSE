"""Render the hull from the STEP solid for the vessel figure: shaded surface + visible B-rep feature edges
(hidden-line removal by z-buffer). No text; anchor points are exported for TikZ annotation."""
import numpy as np, pickle, json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection, LineCollection
import stepgeom as sg
from paths import STEP, OUT
E=sg.load(STEP); F=sg.faces(E)
M=pickle.load(open(OUT+'mesh_coarse.pkl','rb')); V,T=M['V'],M['T']
# B-rep edges as 3D polylines (from pcurves on one adjacent face)
edges={}
for f in F:
    S=f['surf']
    for t,l in f['loops']: pass
R=sg.R
# adjacency: edge -> faces (surface ids) and pcurves; keep only feature edges (dihedral > 15 deg)
def surf_normal(S,u,v,h=1e-5):
    p=S.eval(np.array([u]),np.array([v]))[0]
    du=S.eval(np.array([min(u+h,S.urange[1])]),np.array([v]))[0]-S.eval(np.array([max(u-h,S.urange[0])]),np.array([v]))[0]
    dv=S.eval(np.array([u]),np.array([min(v+h,S.vrange[1])]))[0]-S.eval(np.array([u]),np.array([max(v-h,S.vrange[0])]))[0]
    n=np.cross(du,dv); return n/np.linalg.norm(n)
edges={}; nfeat=0
for i,(t,a) in E.items():
    if t!='EDGE_CURVE': continue
    sc=E[R(a[3])][1]; pcs=[E[R(p)][1] for p in sc[2]]
    curves=[]
    for pc in pcs:
        surf=sg.Surf(E,R(pc[1])); c=sg.Curve(E,R(E[R(pc[2])][1][1][0])); curves.append((surf,c))
    (S1,c1),(S2,c2)=curves[0],curves[1]
    ang=[]
    for t_ in (0.25,0.5,0.75):
        tt=c1.rng[0]+t_*(c1.rng[1]-c1.rng[0]); uv1=__import__('scipy').interpolate.BSpline(c1.K,c1.P,c1.d)(tt)
        p=S1.eval(np.array([uv1[0]]),np.array([uv1[1]]))[0]
        uv2=c2.sample(200); P2s=S2.eval(uv2[:,0],uv2[:,1]); j=np.argmin(np.linalg.norm(P2s-p,axis=1))
        n1=surf_normal(S1,*uv1); n2=surf_normal(S2,*uv2[j])
        ang.append(np.degrees(np.arccos(np.clip(abs(n1@n2),0,1))))
    if max(ang)>15:
        uv=c1.sample(90); edges[i]=S1.eval(uv[:,0],uv[:,1]); nfeat+=1
print('feature edges',nfeat,'of',sum(1 for t,_ in E.values() if t=='EDGE_CURVE'))
def view(az,el):
    az,el=np.radians(az),np.radians(el)
    d=np.array([np.cos(el)*np.cos(az),np.cos(el)*np.sin(az),np.sin(el)])
    up=np.array([0,0,1.0]); r=np.cross(up,d); r/=np.linalg.norm(r); u=np.cross(d,r); return d,r,u
def render(name,az,el,width_mm,base,feat_col,boxes=(),anchors={},light=(0.35,-0.55,0.75),tint_bottom=None,bottom_faces=()):
    d,r,u=view(az,el); P2=V@np.c_[r,u]; dep=V@d
    tri=T; n=np.cross(V[tri[:,1]]-V[tri[:,0]],V[tri[:,2]]-V[tri[:,0]]); nn=np.linalg.norm(n,axis=1); n=n/np.where(nn>0,nn,1)[:,None]
    vis=(n@d)>0
    L=np.array(light); L/=np.linalg.norm(L)
    lam=np.clip(n@L,0,1); spec=np.clip(n@((L+d)/np.linalg.norm(L+d)),0,1)**30
    sh=0.62+0.38*lam
    order=np.argsort(dep[tri].mean(1)); order=order[vis[order]]
    cols=np.tile(np.array(base),(len(tri),1))
    if tint_bottom is not None: cols[np.isin(M['fid'],bottom_faces)]=tint_bottom
    C=np.clip(cols*sh[:,None]+0.10*spec[:,None],0,1)
    lo=P2.min(0)-0.25; hi=P2.max(0)+0.25
    wmm=width_mm; hmm=wmm*(hi[1]-lo[1])/(hi[0]-lo[0])
    fig=plt.figure(figsize=(wmm/25.4,hmm/25.4)); ax=fig.add_axes([0,0,1,1]); ax.set_xlim(lo[0],hi[0]); ax.set_ylim(lo[1],hi[1]); ax.axis('off')
    pc=PolyCollection(P2[tri[order]],facecolors=C[order],edgecolors=C[order],linewidths=0.2); pc.set_rasterized(True); ax.add_collection(pc)
    # z-buffer for edge visibility
    res=0.003; W=int((hi[0]-lo[0])/res)+1; H=int((hi[1]-lo[1])/res)+1
    zb=np.full((H,W),-np.inf)
    for i in order:
        p=P2[tri[i]]; z=dep[tri[i]]
        x0,y0=np.floor((p.min(0)-lo)/res).astype(int); x1,y1=np.ceil((p.max(0)-lo)/res).astype(int)
        xs=lo[0]+np.arange(x0,x1+1)*res; ys=lo[1]+np.arange(y0,y1+1)*res
        X,Y=np.meshgrid(xs,ys)
        a,b,c=p; det=(b[0]-a[0])*(c[1]-a[1])-(c[0]-a[0])*(b[1]-a[1])
        if abs(det)<1e-14: continue
        l1=((b[0]-X)*(c[1]-Y)-(c[0]-X)*(b[1]-Y))/det; l2=((c[0]-X)*(a[1]-Y)-(a[0]-X)*(c[1]-Y))/det; l3=1-l1-l2
        m=(l1>=-1e-9)&(l2>=-1e-9)&(l3>=-1e-9)
        if not m.any(): continue
        zz=l1*z[0]+l2*z[1]+l3*z[2]
        sub=zb[y0:y1+1,x0:x1+1]; upd=m&(zz>sub); sub[upd]=zz[upd]
    segs=[]
    for k,pts in edges.items():
        q=pts@np.c_[r,u]; zq=pts@d
        ix=np.clip(((q[:,0]-lo[0])/res).round().astype(int),0,W-1); iy=np.clip(((q[:,1]-lo[1])/res).round().astype(int),0,H-1)
        # sample neighbourhood max to be robust at silhouettes
        visq=zq>=zb[iy,ix]-0.05
        for j in range(len(q)-1):
            if visq[j] and visq[j+1]: segs.append(q[j:j+2])
    ax.add_collection(LineCollection(segs,colors=feat_col,linewidths=0.45,capstyle='round'))
    for (corners,col,fill) in boxes:
        Cq=corners@np.c_[r,u]
        from scipy.spatial import ConvexHull
        h=ConvexHull(Cq); ax.fill(*Cq[h.vertices].T,color=fill,alpha=0.35,lw=0)
        for a_,b_ in [(0,1),(2,3),(4,5),(6,7),(0,2),(1,3),(4,6),(5,7),(0,4),(1,5),(2,6),(3,7)]:
            ax.plot(*Cq[[a_,b_]].T,color=col,lw=0.8,ls=(0,(3,1.6)),solid_capstyle='round')
    fig.savefig(OUT+name+'.pdf',dpi=600); fig.savefig(OUT+name+'.png',dpi=200); plt.close(fig)
    anc={k:list(((np.asarray(v)@np.c_[r,u]-lo)/(hi-lo))*[wmm,hmm]) for k,v in anchors.items()}
    return dict(w=wmm,h=hmm,anchors=anc)
def box(x0,x1,y0,y1,z0,z1): return np.array([[x,y,z] for x in (x0,x1) for y in (y0,y1) for z in (z0,z1)])
MAG='#C43D8A'; INK2='#55534E'
base=np.array([0.87,0.865,0.85])
from sections import section
import case_data as cd
L=cd.L
HB=np.abs(V[:,1]).max()                                  # maximum half-breadth of the solid
ZD=section(0.01*L).reshape(-1,3)[:,2].max()              # deck height at the transom
# sheer line points (starboard) for the fendering anchor
sheer=[]
for x in np.linspace(0.025*L,0.958*L,40):
    S=section(x).reshape(-1,3); S=S[S[:,1]<0]; m=S[:,1]<S[:,1].min()+0.03; S=S[m]; sheer.append(S[np.argmax(S[:,2])])
sheer=np.array(sheer)
# subsystem boxes are schematic positions (fractions of L), not model data
iso=render('hull_iso',-142,22,112,base,'#3a3936',
  boxes=[(box(0.038*L,0.244*L,-0.076*L,0.076*L,ZD,ZD+0.049*L),MAG,MAG),
         (box(0.277*L,0.445*L,-0.067*L,0.067*L,0.038*L,0.088*L),INK2,'#9A9893'),
         (box(-0.046*L,-0.002*L,-0.092*L,0.092*L,0.004*L,0.059*L),INK2,'#9A9893')],
  anchors={'payload':[0.143*L,0.0,ZD+0.049*L],'energy':[0.361*L,-0.067*L,0.063*L],'prop':[-0.025*L,-0.092*L,0.034*L],
           'fender':list(sheer[17]),'hull':[0.588*L,-0.122*L,0.076*L],
           'bow':[L,0,0.076*L],'stern_p':[0,HB,ZD],'stern_s':[0,-HB,ZD],'transom':[0.0,0.0,0.084*L],'sheer_s':list(sheer[10])})
json.dump(dict(iso=iso),open(OUT+'hull_anchors.json','w'),indent=1)
print(json.dumps(dict(iso=iso),indent=0)[:800])

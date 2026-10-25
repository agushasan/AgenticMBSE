"""Independent hydrostatics by vertical ray casting (no divergence theorem, no clipping)."""
from paths import STEP, OUT
import numpy as np, stepgeom as sg, json, time
import case_data as cd
from scipy.optimize import brentq, fsolve
E=sg.load(STEP)
F=sg.faces(E); Vs=[];Ts=[];off=0
for f in F:
    X,T=sg.tessellate(f,50); Vs.append(X);Ts.append(T+off);off+=len(X)
V=np.vstack(Vs);T=np.vstack(Ts); P=V[T]
h=0.01; ox,oy=0.003141,0.002718  # irrational-ish offsets avoid edge hits
lo,hi=V.min(0),V.max(0)   # ray grid covers the bounding box of the solid
xs=np.arange(lo[0]-0.1+ox,hi[0]+0.1,h); ys=np.arange(lo[1]-0.1+oy,hi[1]+0.1,h)
A=P[:,:,:2]; 
det=(A[:,1,0]-A[:,0,0])*(A[:,2,1]-A[:,0,1])-(A[:,2,0]-A[:,0,0])*(A[:,1,1]-A[:,0,1])
keep=np.abs(det)>1e-14; P=P[keep]; A=A[keep]; det=det[keep]
ix0=np.ceil((A[:,:,0].min(1)-xs[0])/h).astype(int); ix1=np.floor((A[:,:,0].max(1)-xs[0])/h).astype(int)
iy0=np.ceil((A[:,:,1].min(1)-ys[0])/h).astype(int); iy1=np.floor((A[:,:,1].max(1)-ys[0])/h).astype(int)
nx=np.maximum(ix1-ix0+1,0); ny=np.maximum(iy1-iy0+1,0); cnt=nx*ny
ti=np.repeat(np.arange(len(P)),cnt)
k=np.arange(cnt.sum())-np.repeat(np.cumsum(cnt)-cnt,cnt)
gx=ix0[ti]+k//np.maximum(ny[ti],1); gy=iy0[ti]+k%np.maximum(ny[ti],1)
px=xs[0]+gx*h; py=ys[0]+gy*h
a=A[ti]; 
l1=((a[:,1,0]-px)*(a[:,2,1]-py)-(a[:,2,0]-px)*(a[:,1,1]-py))/det[ti]
l2=((a[:,2,0]-px)*(a[:,0,1]-py)-(a[:,0,0]-px)*(a[:,2,1]-py))/det[ti]
l3=1-l1-l2
inside=(l1>=0)&(l2>=0)&(l3>=0)
z=(l1*P[ti,0,2]+l2*P[ti,1,2]+l3*P[ti,2,2])[inside]
ray=(gx*len(ys)+gy)[inside]
o=np.lexsort((z,ray)); ray=ray[o]; z=z[o]
u,start,counts=np.unique(ray,return_index=True,return_counts=True)
odd=(counts%2==1).sum()
print('rays hit',len(u),'odd-count rays',odd)
good=counts%2==0
segs=[]
for s,c in zip(start[good],counts[good]):
    zz=z[s:s+c]; segs.append((ray[s],zz[0::2],zz[1::2]))
# flatten: ray -> list of intervals
R=np.array([r for r,a_,b_ in segs for _ in a_]); Z0=np.concatenate([a_ for r,a_,b_ in segs]); Z1=np.concatenate([b_ for r,a_,b_ in segs])
RX=xs[R//len(ys)]; RY=ys[R%len(ys)]
dA=h*h
print('total volume (ray)',((Z1-Z0).sum()*dA))
def sub(T0,th=0.0,xr=0.0):
    lev=T0+(RX-xr)*np.tan(th)
    top=np.minimum(Z1,lev); L=np.clip(top-Z0,0,None)
    vol=L.sum()*dA
    cx=(L*RX).sum()*dA/vol; cz=(L*(Z0+np.maximum(top,Z0))/2).sum()*dA/vol
    # waterplane: rays whose interval contains the level
    wp=(Z0<lev)&(Z1>lev)
    Awp=wp.sum()*dA; IT=(RY[wp]**2).sum()*dA
    return vol,cx,cz,Awp,IT
def wl_extent(T0):
    wp=(Z0<T0)&(Z1>T0); return RX[wp].max()-RX[wp].min()+h, RY[wp].max()-RY[wp].min()+h
out={}
for rho,tag in [(cd.RHO_SEA,'sea'),(cd.RHO_FRESH,'fresh')]:
    nab=cd.M0/rho
    Tek=brentq(lambda t: sub(t)[0]-nab,0.2,1.2,xtol=1e-6)
    v,cx,cz,Awp,IT=sub(Tek)
    LWL,BWL=wl_extent(Tek)
    r=dict(LWL=LWL,BWL=BWL,T=Tek,LCB=cx,KB=cz,Awp=Awp,BMT=IT/v,GMT=cz+IT/v-cd.KG,disp070=sub(cd.T)[0]*rho/1000)
    eq={}
    for f in cd.LCG_STUDIED:
        G=np.array([f*cd.L,cd.KG])
        def res(p):
            v,cx,cz,_,_=sub(p[0],p[1],G[0]); return [v-nab,(cx-G[0])*np.cos(p[1])+(cz-G[1])*np.sin(p[1])]
        T0,th=fsolve(res,[Tek,-0.01],xtol=1e-9)
        eq[f]=dict(trim=np.degrees(th),Ttransom=T0-G[0]*np.tan(th))
    r['eq']=eq; out[tag]=r
print(json.dumps(out,indent=1,default=float))
json.dump(out,open(OUT+'raycheck.json','w'),indent=1,default=float)

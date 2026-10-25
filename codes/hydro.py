"""Hydrostatics of the closed triangulated solid: displaced volume and centre of buoyancy by clipping
at a (possibly trimmed) waterplane, and solvers for even-keel draft and free-trim equilibrium."""
from paths import STEP, OUT
import numpy as np, pickle
from scipy.optimize import brentq, fsolve
M=pickle.load(open(OUT+'mesh.pkl','rb')); V,T=M['V'],M['T']
TRI=V[T]  # n x 3 x 3

def clip_below(tri, nhat, c):
    """clip triangles to half-space nhat.p - c <= 0; returns list of triangles (k x 3 x 3)"""
    d=tri@nhat - c
    below=(d<=0)
    nb=below.sum(1)
    out=[tri[nb==3]]
    for idx in np.where((nb==1)|(nb==2))[0]:
        P=tri[idx]; D=d[idx]; poly=[]
        for i in range(3):
            a,b=P[i],P[(i+1)%3]; da,db=D[i],D[(i+1)%3]
            if da<=0: poly.append(a)
            if (da<=0)!=(db<=0):
                t=da/(da-db); poly.append(a+t*(b-a))
        for k in range(1,len(poly)-1): out.append(np.array([[poly[0],poly[k],poly[k+1]]]))
    return np.vstack(out)

def submerged(T0, theta=0.0, xr=0.0):
    """waterplane z = T0 + (x-xr)*tan(theta); theta>0 = bow (high x) deeper? returns vol, centroid, wetted area, clipped tris"""
    n=np.array([-np.sin(theta),0,np.cos(theta)])
    O=np.array([xr,0,T0]); c=n@O
    C=clip_below(TRI,n,c)
    a,b,cc=C[:,0]-O,C[:,1]-O,C[:,2]-O
    v=np.einsum('ij,ij->i',a,np.cross(b,cc))/6
    vol=v.sum()
    cen=((C.sum(1)+O)/4*v[:,None]).sum(0)/vol
    S=np.linalg.norm(np.cross(C[:,1]-C[:,0],C[:,2]-C[:,0]),axis=1).sum()/2
    return vol,cen,S,C

def waterline_segments(T0):
    tri=TRI; d=tri[:,:,2]-T0
    m=(d.min(1)<0)&(d.max(1)>0)
    segs=[]
    for P,D in zip(tri[m],d[m]):
        pts=[]
        for i in range(3):
            a,b=P[i],P[(i+1)%3]; da,db=D[i],D[(i+1)%3]
            if (da<0)!=(db<0): t=da/(da-db); pts.append(a+t*(b-a))
        if len(pts)==2: segs.append(pts)
    return np.array(segs)

def waterplane(T0,nx=600):
    S=waterline_segments(T0)
    P=S.reshape(-1,3)
    x0,x1=P[:,0].min(),P[:,0].max()
    xs=np.linspace(x0,x1,nx); b=np.zeros(nx)
    for i,x in enumerate(xs):
        # half breadth = max |y| among segment points interpolated at x
        s=S[(np.minimum(S[:,0,0],S[:,1,0])<=x)&(np.maximum(S[:,0,0],S[:,1,0])>=x)]
        if len(s)==0: continue
        t=(x-s[:,0,0])/np.where(s[:,1,0]!=s[:,0,0],s[:,1,0]-s[:,0,0],1)
        y=s[:,0,1]+t*(s[:,1,1]-s[:,0,1])
        b[i]=np.abs(y).max()
    Awp=np.trapezoid(2*b,xs); IT=np.trapezoid(2*b**3/3,xs)
    LCF=np.trapezoid(2*b*xs,xs)/Awp; IL=np.trapezoid(2*b*(xs-LCF)**2,xs)
    return dict(LWL=x1-x0,x0=x0,x1=x1,BWL=2*b.max(),Awp=Awp,IT=IT,IL=IL,LCF=LCF,xs=xs,b=b)

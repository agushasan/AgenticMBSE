"""Minimal STEP AP214 reader for B-spline B-rep solids + trimmed tessellation.
Reads MANIFOLD_SOLID_BREP of ADVANCED_FACEs on B_SPLINE_SURFACE_WITH_KNOTS with
PCURVE trimming loops. No external CAD kernel required."""
import re, numpy as np
from scipy.interpolate import BSpline
from scipy.spatial import Delaunay
from matplotlib.path import Path

def tokenize_args(s):
    # parse a STEP parameter list string into nested python lists
    pos=0
    def parse():
        nonlocal pos
        out=[]
        assert s[pos]=='('; pos+=1
        cur=''
        while True:
            ch=s[pos]
            if ch=="'":
                j=s.index("'",pos+1); out.append(s[pos+1:j]); pos=j+1; cur=None
            elif ch=='(':
                if cur and cur.strip():  # typed param like LENGTH_MEASURE(1.)
                    name=cur.strip(); sub=parse(); out.append((name,sub)); cur=None
                else:
                    out.append(parse()); cur=None
            elif ch==',' or ch==')':
                if cur is not None and cur.strip()!='': out.append(conv(cur.strip()))
                cur=''; pos+=1
                if ch==')': return out
                continue
            else:
                cur=(cur or '')+ch; pos+=1
    return parse()

def conv(t):
    if t.startswith('#'): return ('ref',int(t[1:]))
    if t.startswith('.'): return t
    try: return float(t)
    except: return t

def load(path):
    s=open(path).read()
    data=s[s.index('DATA;')+5:s.index('ENDSEC;',s.index('DATA;'))]
    data=re.sub(r'/\*.*?\*/','',data,flags=re.S)
    ents={}
    for stmt in data.split(';'):
        stmt=stmt.strip()
        if not stmt: continue
        m=re.match(r'#(\d+)\s*=\s*([A-Z_0-9]*)\s*(\(.*)$',stmt,re.S)
        if not m: continue
        i,typ,rest=int(m.group(1)),m.group(2),m.group(3).replace('\n','')
        if typ=='':
            ents[i]=('COMPLEX',rest); continue
        ents[i]=(typ,tokenize_args(rest))
    return ents

def R(x): return x[1]

def bspline_basis_knots(mults,knots):
    return np.repeat(np.array(knots,float),np.array(mults,int))

class Surf:
    def __init__(s,E,i):
        t,a=E[i]; assert t=='B_SPLINE_SURFACE_WITH_KNOTS',t
        s.du,s.dv=int(a[1]),int(a[2])
        s.P=np.array([[E[R(p)][1][1] for p in row] for row in a[3]],float)  # nu x nv x 3
        s.U=bspline_basis_knots(a[8],a[10]); s.V=bspline_basis_knots(a[9],a[11])
        s.urange=(s.U[s.du],s.U[-s.du-1]); s.vrange=(s.V[s.dv],s.V[-s.dv-1])
    def eval(s,u,v):
        nu,nv,_=s.P.shape
        # tensor-product: evaluate basis matrices
        Bu=BSpline.design_matrix(np.clip(u,*s.urange),s.U,s.du).toarray()
        Bv=BSpline.design_matrix(np.clip(v,*s.vrange),s.V,s.dv).toarray()
        return np.einsum('ni,ijk,nj->nk',Bu,s.P,Bv)

class Curve:
    def __init__(s,E,i):
        t,a=E[i]; assert t=='B_SPLINE_CURVE_WITH_KNOTS',t
        s.d=int(a[1]); s.P=np.array([E[R(p)][1][1] for p in a[2]],float)
        s.K=bspline_basis_knots(a[6],a[7]); s.rng=(s.K[s.d],s.K[-s.d-1])
    def sample(s,n):
        t=np.linspace(*s.rng,n)
        return BSpline(s.K,s.P,s.d)(t)

def faces(E):
    out=[]
    for i,(t,a) in E.items():
        if t!='ADVANCED_FACE': continue
        bounds=a[1]; surf=R(a[2]); same=a[3]=='.T.'
        loops=[]
        for b in bounds:
            bt,ba=E[R(b)]
            loop=E[R(ba[1])][1][1]
            pts=[]
            for oe in loop:
                oa=E[R(oe)][1]; ec=E[R(oa[3])][1]; orient=oa[4]=='.T.'
                sc=E[R(ec[3])]
                assert sc[0]=='SURFACE_CURVE',sc[0]
                pcs=sc[1][2]
                pc=None
                for p in pcs:
                    pa=E[R(p)][1]
                    if R(pa[1])==surf: pc=pa; break
                dr=E[R(pc[2])][1]; c=Curve(E,R(dr[1][0]))
                uv=c.sample(60)
                if not (orient == (ec[4]=='.T.')): uv=uv[::-1]
                pts.append(uv[:-1])
            loops.append((bt,np.vstack(pts)))
        out.append(dict(id=i,surf=Surf(E,surf),same=same,loops=loops))
    return out

def tessellate(f,n=70):
    S=f['surf']; (u0,u1),(v0,v1)=S.urange,S.vrange
    uu,vv=np.meshgrid(np.linspace(u0,u1,n),np.linspace(v0,v1,n))
    grid=np.c_[uu.ravel(),vv.ravel()]
    outer=[l for t,l in f['loops'] if t=='FACE_OUTER_BOUND'][0]
    inners=[l for t,l in f['loops'] if t!='FACE_OUTER_BOUND']
    # normalise uv to unit square for robust Delaunay
    sc=np.array([u1-u0,v1-v0]); o=np.array([u0,v0])
    P=Path((outer-o)/sc)
    g=(grid-o)/sc
    keep=P.contains_points(g,radius=-1e-6) | P.contains_points(g,radius=1e-6)
    keep&=P.contains_points(g,radius=-1e-4)  # strictly inside
    for L in inners: keep&=~Path((L-o)/sc).contains_points(g)
    bnd=[(outer-o)/sc]+[(L-o)/sc for L in inners]
    pts=np.vstack([g[keep]]+bnd)
    tri=Delaunay(pts).simplices
    c=pts[tri].mean(1)
    ok=P.contains_points(c)
    for L in inners: ok&=~Path((L-o)/sc).contains_points(c)
    tri=tri[ok]
    uv=pts*sc+o
    X=S.eval(uv[:,0],uv[:,1])
    # orient triangles consistent with surface normal (du x dv) and face sense
    a,b,cc=uv[tri[:,0]],uv[tri[:,1]],uv[tri[:,2]]
    cross=(b-a)[:,0]*(cc-a)[:,1]-(b-a)[:,1]*(cc-a)[:,0]
    flip=(cross<0)
    if not f['same']: flip=~flip
    tri[flip]=tri[flip][:,[0,2,1]]
    return X,tri

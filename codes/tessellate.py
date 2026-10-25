"""Step 1: read the STEP solid and write fine (hydrostatics) and coarse (rendering) triangulations."""
import numpy as np, pickle, stepgeom as sg
from paths import STEP, OUT
E=sg.load(STEP); F=sg.faces(E)
for n,name in [(70,'mesh.pkl'),(24,'mesh_coarse.pkl')]:
    Vs=[];Ts=[];fid=[];off=0
    for k,f in enumerate(F):
        X,T=sg.tessellate(f,n); Vs.append(X);Ts.append(T+off);fid+=[k]*len(T);off+=len(X)
    V=np.vstack(Vs);T=np.vstack(Ts)
    a,b,c=V[T[:,0]],V[T[:,1]],V[T[:,2]]
    print(name,'triangles',len(T),'enclosed volume %.4f m3'%(np.einsum('ij,ij->i',a,np.cross(b,c)).sum()/6))
    pickle.dump(dict(V=V,T=T,fid=np.array(fid),nf=len(F)),open(OUT+name,'wb'))

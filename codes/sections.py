"""Plane sections of the triangulated solid (transverse by default; axis=1 gives buttocks)."""
import numpy as np
from hydro import TRI, V, T
def section(x0, axis=0):
    d=TRI[:,:,axis]-x0
    m=(d.min(1)<0)&(d.max(1)>0)
    segs=[]
    for P,D in zip(TRI[m],d[m]):
        pts=[]
        for i in range(3):
            a,b=P[i],P[(i+1)%3]; da,db=D[i],D[(i+1)%3]
            if (da<0)!=(db<0): t=da/(da-db); pts.append(a+t*(b-a))
        if len(pts)==2: segs.append(pts)
    return np.array(segs)

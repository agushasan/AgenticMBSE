"""Figure 4: lines plan of the hull in non-dimensional form (all coordinates divided by the length
overall L): profile and plan with three waterlines at the reported displacement, and body plan.
Waterlines and sections are computed from the tessellated CAD solid."""
import numpy as np, json, pickle, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from style import *
import case_data as cd
from paths import OUT
from sections import section
H=json.load(open(OUT+'hydro.json')); sea=H['sea']; Tek=sea['T_evenkeel']; e=sea['eq']['0.28']
L=cd.L; TR=cd.T; KG=cd.KG; th=np.radians(e['trim_deg']); xr=e['LCG']; T0=e['T_at_LCG']; Ttr=e['T_transom']
zw=lambda x: T0+(x-xr)*np.tan(th)
n=lambda v: np.asarray(v)/L          # metres -> fraction of L
def halfbreadth_at(x,z):
    S=section(x); best=None
    for s in S:
        z0,z1=s[0,2],s[1,2]
        if (z0-z)*(z1-z)<=0 and z0!=z1:
            t=(z-z0)/(z1-z0); y=abs(s[0,1]+t*(s[1,1]-s[0,1])); best=y if best is None else max(best,y)
    return best
STn=[0.05,0.15,0.30,0.40,0.55,0.67,0.80,0.92]   # stations as x/L
ST=[f*L for f in STn]
AFT=0.45*L
K=8.0*L  # mm per unit of x/L (same physical scale as the dimensional figure)
Wf,Hf=160,76
fig=plt.figure(figsize=(Wf*MM,Hf*MM))
def axes_mm(l,b,w,h): return fig.add_axes([l/Wf,b/Hf,w/Wf,h/Hf])
xl0,xl1=n(-0.4),n(16.4); za,zb=n(-0.36),n(2.2)
axa=axes_mm(11,Hf-6-(zb-za)*K,(xl1-xl0)*K,(zb-za)*K)
xp0,xp1=n(-0.4),n(12.3); ya,yb=n(-1.8),n(1.9)
axb=axes_mm(11,10,(xp1-xp0)*K,(yb-ya)*K)
yc0,yc1=n(-1.8),n(1.95); zc0,zc1=n(-0.05),n(2.05); Kc=9.5*L
axc=axes_mm(11+(xp1-xp0)*K+11,10,(yc1-yc0)*Kc,(zc1-zc0)*Kc)
fmt=lambda v: ('%.3f'%v).rstrip('0') if v<0.1 else '%.2f'%v
# ---------------- (a) profile
ax=axa
for s in section(0.005,axis=1): ax.plot(n(s[:,0]),n(s[:,2]),color=INK,lw=0.9,solid_capstyle='round')
for yy in (1.30,0.415,0.86):
    for s in section(yy,axis=1):
        if s[:,2].max()<1.0 and abs(s[1,0]-s[0,0])>1e-3: ax.plot(n(s[:,0]),n(s[:,2]),color=MUTED,lw=0.45)
for x in ST: ax.plot(n([x,x]),n([-0.08,1.85]),color=RULE,lw=0.5,zorder=0)
xx=np.array([-0.3,L+0.3])
ax.plot(n(xx),n([TR,TR]),color=HUMAN,lw=1.1,ls=(0,(4,2)))
ax.plot(n(xx),n([Tek,Tek]),color=MUTED,lw=1.0,ls=(0,(2,1.5)))
ax.plot(n(xx),n(zw(xx)),color=TOOL,lw=1.5)
ax.plot([n(xr)],[n(KG)],'o',ms=4.0,mfc='white',mec=INK,mew=0.8,zorder=6)
ax.annotate('G',(n(xr),n(KG)),xytext=(3.5,2.5),textcoords='offset points',fontsize=6.6,color=INK)
lx=n(L+0.6)
ax.text(lx,n(0.76),'reported draft, $T/L$ = %.3f'%(TR/L),color=HUMAND,fontsize=6.6,va='bottom')
ax.text(lx,n(0.47),'even keel, $T/L$ = %.3f'%(Tek/L),color=INK2,fontsize=6.6,va='center')
ax.text(lx,n(0.17),'LCG at 0.28$L$: trim %.1f° by the stern,\ntransom draft $T/L$ = %.3f'%(abs(e['trim_deg']),Ttr/L),color=TOOLD,fontsize=6.6,va='top')
ax.annotate('',xy=(0,n(2.03)),xytext=(1.0,n(2.03)),arrowprops=dict(arrowstyle='<->',lw=0.5,color=INK2,shrinkA=0,shrinkB=0))
ax.text(0.5,n(2.06),'length overall $L$',ha='center',va='bottom',fontsize=6.6,color=INK2)
ax.text(n(0.12),n(1.44),'transom',fontsize=6.2,color=INK2)
ax.text(n(3.6),n(0.125),'strakes',fontsize=6.2,color=INK2)
for f in STn: ax.text(f,n(-0.12),'%.2f'%f,ha='center',va='top',fontsize=5.8,color=MUTED)
ax.text(0.945,n(-0.12),'$x/L$',fontsize=5.8,color=MUTED,va='top',ha='left')
ax.set_xlim(xl0,xl1); ax.set_ylim(za,zb); ax.set_xticks([]); ax.set_yticks([0,0.05,0.10,0.15]); ax.spines['bottom'].set_visible(False)
ax.set_ylabel('$z/L$'); ax.set_title('(a) Profile with waterlines',x=-0.07)
# ---------------- (b) plan
ax=axb
xs=np.linspace(0.001,L-0.001,300); hb=np.array([np.abs(section(x)[:,:,1]).max() for x in xs])
xs2=np.r_[0,xs,L]; hb2=np.r_[hb[0],hb,0]
ax.plot(n(xs2),n(hb2),color=INK,lw=0.9); ax.plot(n(xs2),-n(hb2),color=INK,lw=0.9); ax.plot([0,0],[-n(hb2[0]),n(hb2[0])],color=INK,lw=0.9)
ax.axhline(0,color=MUTED,lw=0.4,ls=(0,(6,1.5,1,1.5)))
M=pickle.load(open(OUT+'mesh.pkl','rb')); fid=M['fid']; Vv=M['V']; Tv=M['T']
def feature_line(faces):
    pts=Vv[np.unique(Tv[np.isin(fid,faces)])]; xb=np.linspace(pts[:,0].min(),pts[:,0].max(),80); yy=[]; xc=[]
    for i in range(79):
        m=(pts[:,0]>=xb[i])&(pts[:,0]<=xb[i+1])
        if m.any(): yy.append(pts[m,1].max()); xc.append((xb[i]+xb[i+1])/2)
    return np.array(xc),np.array(yy)
for faces in [[22,21,20,19,18],[14,13,12,11],[33,32,30],[6]]:
    xc,yy=feature_line(faces); ax.plot(n(xc),n(yy),color=MUTED,lw=0.5)
ax.text(n(1.4),n(0.40),'inner strake',fontsize=6.0,color=INK2); ax.text(n(1.4),n(0.80),'middle strake',fontsize=6.0,color=INK2); ax.text(n(0.3),n(1.17),'outer strake',fontsize=6.0,color=INK2)
ax.annotate('chine flat',xy=(n(3.0),n(1.565)),xytext=(n(3.6),n(1.74)),fontsize=6.0,color=INK2,va='center',arrowprops=dict(arrowstyle='-',lw=0.4,color=INK2,shrinkA=0,shrinkB=0))
xw=np.linspace(0.0005,L-0.0005,700)
for zf,col,lw,ls in [(lambda x:TR,HUMAN,1.1,(0,(4,2))),(lambda x:Tek,MUTED,1.0,(0,(2,1.5))),(zw,TOOL,1.5,'-')]:
    yv=[]; xv=[]
    for x in xw:
        b=halfbreadth_at(x,zf(x))
        if b is not None: xv.append(x); yv.append(-b)
    ax.plot(n(xv),n(yv),color=col,lw=lw,ls=ls)
for x in ST: ax.plot(n([x,x]),n([-1.75,1.75]),color=RULE,lw=0.5,zorder=0)
ax.text(n(10.15),n(-0.95),'waterlines',fontsize=6.2,color=INK2,va='top')
HB=hb.max()
ax.annotate('',xy=(0.47,-n(HB)),xytext=(0.47,n(HB)),arrowprops=dict(arrowstyle='<->',lw=0.5,color=INK2,shrinkA=0,shrinkB=0))
ax.text(0.48,n(0.66),'$B$',fontsize=6.6,color=INK2,va='center')
ax.set_xlim(xp0,xp1); ax.set_ylim(ya,yb); ax.set_xticks([0,0.2,0.4,0.6,0.8,1.0]); ax.set_yticks([-0.1,0,0.1])
ax.set_xlabel('$x/L$ from transom'); ax.set_ylabel('$y/L$')
ax.set_title('(b) Plan: deck edge and bottom features (port), waterlines (starboard)',x=-0.095)
# ---------------- (c) body plan
ax=axc
for f,x in zip(STn,ST):
    S=section(x); aft=x<=AFT; sgn=-1 if aft else 1
    ls={0.05:'-',0.15:'-',0.30:(0,(3.2,1.6)),0.40:(0,(0.8,1.3))}.get(f,'-')
    for s in S:
        if (aft and s[:,1].mean()<=0) or ((not aft) and s[:,1].mean()>=0): ax.plot(n(s[:,1]),n(s[:,2]),color=INK,lw=0.6,ls=ls if aft else '-')
    z=zw(x); b=halfbreadth_at(x,z)
    if b is not None: ax.plot(n([sgn*(b-0.13),sgn*(b+0.07)]),n([z,z]),color=TOOL,lw=1.1,solid_capstyle='butt',zorder=5)
ax.text(n(-0.85),n(HB),'0.05 to 0.40',fontsize=5.6,color=MUTED,ha='center',va='bottom')
ax.axvline(0,color=MUTED,lw=0.4,ls=(0,(6,1.5,1,1.5)))
ax.plot([yc0,yc1],n([TR,TR]),color=HUMAN,lw=1.0,ls=(0,(4,2))); ax.plot([yc0,yc1],n([Tek,Tek]),color=MUTED,lw=1.0,ls=(0,(2,1.5)))
ax.text(n(-1.75),n(2.03),'aft',fontsize=6.4,color=INK2,va='top'); ax.text(n(1.75),n(2.03),'forward',fontsize=6.4,color=INK2,va='top',ha='right')
ax.set_xlim(yc0,yc1); ax.set_ylim(zc0,zc1)
ax.set_xticks([-0.1,0,0.1]); ax.set_yticks([0,0.05,0.10,0.15]); ax.set_xlabel('$y/L$'); ax.set_title('(c) Body plan',x=0.0)
ax.yaxis.set_label_position('right'); ax.set_ylabel('$z/L$')
ax.yaxis.tick_right(); ax.spines['left'].set_visible(False); ax.spines['right'].set_visible(True)
fig.savefig(OUT+'fig4_lines.pdf'); fig.savefig(OUT+'fig4_lines.png',dpi=220)
# values quoted in the caption
dk={f:np.abs(section(x)[:,:,2]).max()/L for f,x in zip(STn[:4],ST[:4])}
print('deck z/L aft stations', {k:round(v,3) for k,v in dk.items()})
print('station 0.92 wet?', halfbreadth_at(ST[-1],zw(ST[-1])) is not None)
print('T/L reported %.4f even %.4f transom %.4f; diffs %.4f %.4f'%(TR/L,Tek/L,Ttr/L,(TR-Ttr)/L,(TR-Tek)/L))

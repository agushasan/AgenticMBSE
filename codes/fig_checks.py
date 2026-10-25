"""Figure 5: hydrostatic review checks in non-dimensional form (mass fraction m/m0 against T/L,
differences in percent of L, and trim against LCG)."""
import numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from style import *
from paths import OUT
from hydro import submerged, V
import case_data as cd
H=json.load(open(OUT+'hydro.json')); RC=json.load(open(OUT+'review_checks.json'))
Ts=np.linspace(0.15,1.0,40); D=np.array([submerged(t)[0]*cd.RHO_SEA/1000 for t in Ts])
cur=np.array(RC['transom_curve']); m70=RC['mass_for_transom_at_T_t']; Tt7=RC['transom_at_M0_sea']
Tek=H['sea']['T_evenkeel']; d70=H['sea']['disp_at_T_reported_t']
Wf,Hf=160,112
fig=plt.figure(figsize=(Wf*MM,Hf*MM))
def axes_mm(l,b,w,h): return fig.add_axes([l/Wf,b/Hf,w/Wf,h/Hf])
A=axes_mm(12,64,62,40); B=axes_mm(95,64,62,40); C=axes_mm(30,9,44,40); Dd=axes_mm(113,9,44,40)
def grid(ax): ax.grid(color=RULE,lw=0.4); ax.set_axisbelow(True)
# (a)  non-dimensional: T/L and m/m0
L=cd.L; M0=cd.M0/1000; TR=cd.T
ax=A; grid(ax)
ax.plot(Ts/L,D/M0,color=MUTED,lw=1.3,ls=(0,(2.5,1.5)))
ax.plot(cur[:,1]/L,cur[:,0]/M0,color=TOOL,lw=1.6)
ax.plot([0.15/L,Tt7/L],[1,1],color=INK2,lw=0.5,ls=':'); ax.axvline(TR/L,color=HUMAN,lw=1.1,ls=(0,(4,2)))
ax.plot([Tek/L,Tek/L],[0,1],color=MUTED,lw=0.6,ls=':'); ax.plot([Tt7/L,Tt7/L],[0,1],color=TOOL,lw=0.6,ls=':')
for x,y,c,mfc in [(Tek,M0,MUTED,'white'),(Tt7,M0,TOOL,'white'),(TR,d70,MUTED,MUTED),(TR,m70,TOOL,TOOL)]:
    ax.plot([x/L],[y/M0],'o',ms=4.2,mec=c,mfc=mfc,mew=1.1,zorder=5)
ax.text(0.60/L,16.5/M0,'even keel',color=INK2,fontsize=6.6,ha='right')
ax.text(0.99/L,5.4/M0,'transom draft,\nLCG 0.28$L$',color=TOOLD,fontsize=6.6,ha='right',va='top')
ax.text(0.17/L,7.35/M0,'reported $m_0$',color=INK2,fontsize=6.4)
ax.text(0.69/L,20.6/M0,'reported draft',color=HUMAND,fontsize=6.4,ha='right')
ax.text(Tek/L-0.0007,0.5/M0,'%.3f'%(Tek/L),fontsize=6.2,color=INK2,ha='right')
ax.text(Tt7/L-0.0007,0.5/M0,'%.3f'%(Tt7/L),fontsize=6.2,color=TOOLD,ha='right')
ax.annotate('%.2f'%(d70/M0),(TR/L,d70/M0),xytext=(-4,3),textcoords='offset points',fontsize=6.2,color=INK2,ha='right')
ax.annotate('%.2f'%(m70/M0),(TR/L,m70/M0),xytext=(5,-6),textcoords='offset points',fontsize=6.2,color=TOOLD,ha='left')
ax.set_xlim(0.15/L,1.0/L); ax.set_ylim(0,22/M0); ax.set_xlabel('draft $T/L$'); ax.set_ylabel('displacement $m/m_0$')
ax.set_title('(a) Displacement against draft, sea water',x=-0.16)
# (b)
ax=B; grid(ax)
f=np.array([28,30,32,34]); comp=np.array([H['fresh']['eq'][k]['trim_deg'] for k in ['0.28','0.3','0.32','0.34']]); pub=np.array([cd.STATIC_TRIM_P[k] for k in cd.LCG_STUDIED])
ax.plot(f,comp,color=TOOL,lw=1.6,marker='o',ms=4,mfc='white',mew=1.1,zorder=4)
ax.plot(f,pub,lw=0,marker='s',ms=5.2,mfc='none',mec=INK,mew=0.9,zorder=5)
ax.axhline(0,color=INK2,lw=0.5)
ax.plot([28.35],[-0.21],'o',ms=4,mfc='white',mec=TOOL,mew=1.1); ax.text(28.6,-0.21,'computed from this solid',color=TOOLD,fontsize=6.6,va='center')
ax.plot([28.35],[-0.46],'s',ms=4.6,mfc='none',mec=INK,mew=0.9); ax.text(28.6,-0.46,'reported, flat-hull variant',color=INK,fontsize=6.6,va='center')
ax.plot([28.1],[-0.25+0.0],'o',ms=0)
for xi,c,p in zip(f,comp,pub): ax.annotate('%.2f°'%abs(c-p),(xi,min(c,p)),xytext=(0,-9),textcoords='offset points',fontsize=5.8,color=INK2,ha='center')
ax.text(33.9,-2.3,'labels: |difference|',fontsize=5.8,color=MUTED,ha='right')
ax.set_xticks(f); ax.set_xticklabels(['0.28','0.30','0.32','0.34']); ax.set_xlim(27.4,34.6); ax.set_ylim(-2.45,0.3)
ax.set_xlabel('LCG ($x/L$ from transom)'); ax.set_ylabel('static trim (°), by the stern < 0')
ax.set_title('(b) Static trim at $m_0$, fresh water',x=-0.16)
# (c)  differences in percent of L
ax=C
q=['length','beam','depth (max.)','max. draft at $m_0$']; geo=np.array([V[:,0].max()-V[:,0].min(),2*np.abs(V[:,1]).max(),V[:,2].max()-V[:,2].min(),Tt7]); spec=np.array([cd.L,cd.B,cd.D,cd.T]); dev=(geo-spec)/L*100
y=np.arange(4)[::-1]; tau=0.4
ax.axvspan(-tau,tau,color=TOOL,alpha=0.14,lw=0); ax.axvline(0,color=INK2,lw=0.6)
for yi,d in zip(y,dev):
    ok=abs(d)<=tau; col=TOOL if ok else HUMAN
    ax.plot([0,d],[yi,yi],color=col,lw=2.0,solid_capstyle='butt'); ax.plot([d],[yi],'o' if ok else 'D',ms=4.4,color=col,mec='white',mew=0.8,zorder=5)
    ax.text(d if d<-0.1 else 0.25, yi+0.3, ('%+.1f %%'%d).replace('+0.0 %','0.0 %').replace('-','−'), fontsize=6.2, color=TOOLD if ok else HUMAND, ha='center' if d<-0.1 else 'left')
ax.set_yticks(y); ax.set_yticklabels(q); ax.tick_params(axis='y',length=0)
ax.set_xlim(-4.2,1.0); ax.set_ylim(-0.6,3.65); ax.spines['left'].set_visible(False)
ax.text(-0.5,-0.45,'tolerance ±0.4 %',fontsize=5.8,color=TOOLD,ha='right',va='center')
ax.set_xlabel('geometry − reported (% of $L$)'); ax.set_title('(c) Reported particulars',x=-0.55)
# (d)
ax=Dd; grid(ax)
yK,yP=1.0,0.0
st=H['sea']['eq'][str(cd.LCG_DESIGN)]['trim_deg']; tK=cd.RUNNING_TRIM['K']; tP=cd.RUNNING_TRIM['P']; tKr=np.degrees(tK)
ax.axvline(st,color=TOOL,lw=1.2,ls=(0,(3,1.5)),zorder=1)
ax.text(st-0.12,1.55,'static trim at rest,\nthis solid, %s°'%('%.1f'%st).replace('-','−'),fontsize=5.9,color=TOOLD,ha='right',va='center')
# first study: reported value and its reading in radians
ax.annotate('',xy=(tKr+0.07,yK),xytext=(tK-0.08,yK),arrowprops=dict(arrowstyle='-|>',lw=0.6,color=HUMAN,ls=(0,(2,1.2)),mutation_scale=6,shrinkA=0,shrinkB=0))
ax.plot([tK],[yK],'D',ms=5,color=HUMAN,mec='white',mew=0.8,zorder=5)
ax.plot([tKr],[yK],'D',ms=4.6,mfc='white',mec=HUMAN,mew=1.0,zorder=5)
ax.text(tK,yK+0.17,('%.3f°'%tK).replace('-','−'),fontsize=6.2,color=HUMAND,ha='center',va='bottom')
ax.text(-1.0,yK-0.17,'read in radians:\n%s°'%('%.2f'%tKr).replace('-','−'),fontsize=5.9,color=HUMAND,ha='center',va='top')
ax.plot([tP],[yP],'D',ms=5,color=HUMAN,mec='white',mew=0.8,zorder=5)
ax.text(tP,yP+0.17,('%.2f°'%tP).replace('-','−'),fontsize=6.2,color=HUMAND,ha='center',va='bottom')
ax.set_yticks([yK,yP]); ax.set_yticklabels(['Kumar and\nLoizou, CFD','Piehl et al.,\nCFD']); ax.tick_params(axis='y',length=0)
ax.set_xlim(-4.2,0.5); ax.set_ylim(-0.45,1.95)
ax.spines['left'].set_visible(False)
ax.set_xlabel('running trim at design speed (°), by the stern < 0'); ax.set_title('(d) Running trim, straked hull, LCG 0.28$L$',x=-0.3)
fig.savefig(OUT+'fig5_checks.pdf'); fig.savefig(OUT+'fig5_checks.png',dpi=220)

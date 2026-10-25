"""Generate the trace-graph figure (Figure 6, TikZ) directly from the trace graph in tracegraph.py."""
from paths import FIGS
import tracegraph as tg
P,A,R=tg.P,tg.A,tg.R
# layout (mm, panel-local); vertical order chosen to minimise crossings
py={'p8':44,'p6':38.5,'p1':32,'p3':27,'p5':22,'p2':16,'p4':11,'p7':5}
k=1.1
ax={'a7':(19*k,43),'a1':(19*k,30.5),'a2':(30*k,25),'a3':(41*k,31.5),'a5':(41*k,12),'a4':(52*k,18),'a6':(52*k,6)}
ry={f'R{i}':45.5-4.4*(i-1) for i in range(1,11)}
XP,XR=4*k,63*k
pos={**{k:(XP,v) for k,v in py.items()},**ax,**{k:(XR,v) for k,v in ry.items()}}
edges=tg.E
ECR=[('ECR-1','fendering and rub rail',['p8']),('ECR-2','UUVs and launch-and-recovery system',['p1','p2','p3']),
     ('ECR-3','propulsion re-rating',['p7']),('ECR-4','larger energy store',['p4','p5'])]
def sub(s): return s[0]+'_{'+s[1:]+'}' if s[0] in 'pa' else s
out=[r"""\documentclass[border=1pt]{standalone}
\input{lxstyle}
\tikzset{
 pn/.style={circle, minimum size=4.1mm, inner sep=0pt, line width=0.6pt, font=\fss},
 an/.style={rounded corners=0.8mm, minimum width=6.4mm, minimum height=4.1mm, inner sep=0pt, line width=0.6pt, font=\fss},
 rn/.style={minimum width=6.2mm, minimum height=3.5mm, inner sep=0pt, line width=0.6pt, font=\fss},
 changed/.style={draw=change, fill=change, text=white},
 impacted/.style={draw=change, fill=changebg, text=change!70!black},
 reused/.style={draw=tool, fill=toolbg, text=tool!60!black},
 idle/.style={draw=muted, fill=white, text=ink2},
 e/.style={line width=0.4pt, draw=black!28},
 ei/.style={line width=0.8pt, draw=change, -{Stealth[length=1.3mm,width=1.1mm]}},
}
\begin{document}
\begin{tikzpicture}[x=1mm,y=1mm]"""]
W,H=79,58
origins=[(3,H+2),(3+W+2,H+2),(3,0),(3+W+2,0)]
for (name,desc,Nd),(ox,oy) in zip(ECR,origins):
    imp=set(Nd)
    for n in Nd: imp|=tg.desc(n)
    na=len([a for a in A if a in imp]); nr=len([r for r in R if r in imp]); eta=1-na/len(A)
    out.append(r"\begin{scope}[shift={(%g,%g)}]"%(ox,oy))
    out.append(r"\draw[rule, line width=0.4pt, rounded corners=1.2mm, fill=white] (-3,-1.5) rectangle (%g,%g);"%(W-5.5,H-2))
    out.append(r"\node[anchor=north west, inner sep=0pt, font=\fs\bfseries] at (-1,%g) {%s\ \textmd{%s}};"%(H-3.5,name,desc))
    out.append(r"\node[anchor=north west, inner sep=0pt, font=\fss, text=ink2] at (-1,%g) {re-run %d of 7 analyses \quad re-verify %d of 10 requirements \quad $\eta=%.2f$};"%(H-7.6,na,nr,eta))
    # edges
    for u,v in edges:
        (x1,y1),(x2,y2)=pos[u],pos[v]
        hot = (u in imp and v in imp)
        st='ei' if hot else 'e'
        out.append(r"\draw[%s] (%g,%g) to[out=0,in=180] (%g,%g);"%(st,x1+2.4 if u[0]!='a' else x1+3.4,y1,x2-(2.3 if v[0]=='p' else 3.4 if v[0]=='a' else 3.3),y2))
    # nodes
    for n,(x,y) in pos.items():
        if n in Nd: st='changed'
        elif n in imp: st='impacted'
        elif n[0]=='p': st='idle'
        else: st='reused'
        shp='pn' if n[0]=='p' else 'an' if n[0]=='a' else 'rn'
        out.append(r"\node[%s,%s] at (%g,%g) {$%s$};"%(shp,st,x,y,sub(n)) if n[0]!='R' else r"\node[%s,%s] at (%g,%g) {%s};"%(shp,st,x,y,n))
    out.append(r"\end{scope}")
# key band below the panels
cols=[(0,'Design parameters',[('p_1','payload mass'),('p_2','payload power demand'),('p_3','payload position'),('p_4','stored energy'),('p_5','energy-storage mass'),('p_6','hull form'),('p_7','installed propulsion power'),('p_8','fender width')]),
      (35,'Analyses',[('a_1','mass properties'),('a_2','hydrostatics'),('a_3','stability'),('a_4','power and endurance'),('a_5','planing performance'),('a_6','seakeeping'),('a_7','envelope check')]),
      (69,'Requirements',[('R1','length'),('R2','beam'),('R3','displacement'),('R4','draft'),('R5','freeboard')]),
      (91,'',[('R6','$\\overline{GM}_T$'),('R7','endurance'),('R8','speed'),('R9','running trim'),('R10','cradle acceleration')])]
y0=-4.5
for x0,title,items in cols:
    y=y0
    if title: out.append(r"\node[anchor=north west, inner sep=0pt, font=\fs\bfseries] at (%g,%g) {%s};"%(x0,y,title))
    y-=4.2
    for sym,txt in items:
        lab=('$%s$'%sym) if sym[0] in 'pa' else sym
        out.append(r"\node[anchor=north west, inner sep=0pt, font=\fss] at (%g,%g) {%s};"%(x0+0.5,y,lab))
        out.append(r"\node[anchor=north west, inner sep=0pt, font=\fss, text=ink2] at (%g,%g) {%s};"%(x0+6.5,y,txt)); y-=3.25
x0=121; y=y0
out.append(r"\node[anchor=north west, inner sep=0pt, font=\fs\bfseries] at (%g,%g) {Status after the change};"%(x0,y)); y-=6.2
for st,txt in [('changed',r'modified directly by\\the change set, $N_{\Delta}$'),('impacted',r'in the impact set $\mathrm{Imp}(\Delta)$:\\re-run or re-verify'),('reused',r'outside $\mathrm{Imp}(\Delta)$:\\evidence reused (Prop.~1)')]:
    out.append(r"\node[rn,%s] at (%g,%g) {};"%(st,x0+3,y)); out.append(r"\node[anchor=west, inner sep=0pt, font=\fss, align=left] at (%g,%g) {%s};"%(x0+7,y,txt)); y-=7.4
out.append(r"\node[pn,idle] at (%g,%g) {};"%(x0+3,y+0.6)); out.append(r"\node[anchor=west, inner sep=0pt, font=\fss] at (%g,%g) {parameter not changed};"%(x0+7,y+0.6))
out.append(r"\end{tikzpicture}"+"\n"+r"\end{document}")
open(FIGS+'fig6_tracegraph.tex','w').write('\n'.join(out)); print('wrote',FIGS+'fig6_tracegraph.tex')
print('key bottom y',y)

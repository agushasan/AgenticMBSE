"""Generate the vessel figure (Figure 3, TikZ) from the hull render, its anchors and the half-section
at x = 0.378 L. Positions in the section panel are fractions of L, so that no absolute dimension
appears in the figure or in this script."""
import json, math, os
from paths import OUT, FIGS
import case_data as cd
SEC=json.load(open(OUT+'section.json')); L=cd.L
P=[(y/L,z/L) for y,z in SEC['pts']]                  # section in fractions of L
HB=max(y for y,z in P); ZD=max(z for y,z in P)       # half-breadth and deck height at the section
DR=SEC['deadrise_deg']
a=json.load(open(OUT+'hull_anchors.json')); W1=100; s1=W1/a['iso']['w']
k=28.0*L; ox,oy=108,6                                # mm per unit of y/L (same scale as before)
path=" -- ".join("(%.2f,%.2f)"%(ox+y*k,oy+z*k) for y,z in P)
co="\n".join(r"\coordinate (i-%s) at (%.2f,%.2f);"%(n,x*s1,y*s1) for n,(x,y) in a['iso']['anchors'].items())
def S(y,z): return "(%.2f,%.2f)"%(ox+y*k,oy+z*k)
ang=DR
top=a['iso']['h']*s1+5.5
img=os.path.relpath(OUT+'hull_iso.pdf',FIGS).replace(os.sep,'/')
tex=r"""\documentclass[border=1pt]{standalone}
\input{lxstyle}
\tikzset{call/.style={font=\fss, align=left, inner sep=0.5pt}, lead/.style={line width=0.45pt, draw=ink2}, dot/.style={circle, fill=ink2, inner sep=0pt, minimum size=1.1mm}}
\begin{document}
\begin{tikzpicture}[x=1mm,y=1mm]
\node[anchor=south west, inner sep=0pt] at (0,0) {\includegraphics[width=%(W1)smm]{%(IMG)s}};
"""%dict(W1=W1,IMG=img)+co+r"""
\node[ptitle] at (0,%(top)s) {(a) Hull from the CAD solid, with subsystems that the model does not contain};
\node[ptitle] at (%(ox)s,%(top)s) {(b) Half-section at $x=0.38L$};
\node[call, anchor=south west, text=change!80!black] (cp) at (0,44.5) {\textbf{UUVs and launch-and-recovery system}\\$p_1$ mass, $p_2$ power, $p_3$ position\\changed by ECR-2};
\draw[lead, draw=change] ($(cp.south west)+(12,0)$) -- (i-payload); \node[dot, fill=change] at (i-payload) {};
\node[call, anchor=south west] (ce) at (40,54.5) {\textbf{energy storage}\\$p_4$ stored energy, $p_5$ mass};
\draw[lead] ($(ce.south west)+(6,0)$) -- (i-energy); \node[dot] at (i-energy) {};
\node[call, anchor=north west] (cpr) at (0,-1.2) {\textbf{propulsion}, $p_7$ installed power};
\draw[lead] ($(cpr.north west)+(23,0)$) -- (i-prop); \node[dot] at (i-prop) {};
\node[call, anchor=north west] (cf) at (61,9) {\textbf{deck edge and fendering}\\$p_8$ fender width};
\draw[lead] ($(cf.north west)+(4,0)$) -- (i-fender); \node[dot] at (i-fender) {};
\node[call, anchor=north west] (ch) at (83,21.5) {\textbf{hull form}, $p_6$\\STEP solid};
\draw[lead] (ch.north west) -- (i-hull); \node[dot] at (i-hull) {};
\fill[paper] """+path+r""" -- cycle;
\draw[ink, line width=0.75pt, line join=round] """+path+r""";
\draw[muted, line width=0.4pt, dash pattern=on 4pt off 1.2pt on 0.6pt off 1.2pt] """+S(0.0000,-0.0067)+" -- "+S(0.0000,0.1345)+r""";
\node[lab, anchor=south] at """+S(0.0000,0.1437)+r""" {CL};
\draw[ink2, line width=0.4pt, dash pattern=on 1.5pt off 1pt] """+S(0.0017,0.0000)+" -- "+S(0.0353,0.0000)+r""";
\draw[tool!70!black, line width=0.6pt] """+S(0.0269,0.0000)+r""" arc[start angle=0, end angle="""+"%.2f"%ang+r""", radius="""+"%.2f"%(0.0252*k)+r"""];
\node[font=\fss, text=tool!70!black, anchor=north west] at """+S(0.0210,-0.0008)+r""" {deadrise $"""+"%.1f"%DR+r"""^\circ$};
\node[call, anchor=north west] (s1) at """+S(0.0000,-0.0160)+r""" {\textbf{flat keel}};
\draw[lead] (s1.north west) -- """+S(0.0008,0.0000)+r""";
\node[call, anchor=west] (s2) at """+S(0.0588,0.0025)+r""" {\textbf{inner strake}};
\draw[lead] (s2.west) -- """+S(0.0353,0.0059)+r"""; \node[dot] at """+S(0.0353,0.0059)+r""" {};
\node[call, anchor=west] (s3) at """+S(0.0866,0.0113)+r""" {\textbf{middle strake}};
\draw[lead] (s3.west) -- """+S(0.0731,0.0161)+r"""; \node[dot] at """+S(0.0731,0.0161)+r""" {};
\node[call, anchor=west] (s4) at """+S(0.0521,0.0437)+r""" {\textbf{outer strake}};
\draw[lead] ($(s4.south east)+(-1,0)$) -- """+S(0.1059,0.0244)+r"""; \node[dot] at """+S(0.1059,0.0244)+r""" {};
\node[call, anchor=west] (s6) at """+S(0.0723,0.0622)+r""" {\textbf{chine flat}};
\draw[lead] ($(s6.south east)+(-1,0)$) -- """+S(0.1277,0.0304)+r"""; \node[dot] at """+S(0.1277,0.0304)+r""" {};
\node[call, anchor=east] (s5) at """+S(0.1218,0.0798)+r""" {\textbf{topside}};
\draw[lead] (s5.east) -- """+S(0.1340,0.0798)+r"""; \node[dot] at """+S(0.1340,0.0798)+r""" {};
\draw[<->, ink2, line width=0.4pt, >={Stealth[length=1.3mm,width=1mm]}] """+S(0,ZD+0.0112)+" -- "+S(HB,ZD+0.0112)+r""" node[midway, above, font=\fss, text=ink2] {half-breadth $B/2$};
\draw[<->, ink2, line width=0.4pt, >={Stealth[length=1.3mm,width=1mm]}] """+S(HB+0.0092,0)+" -- "+S(HB+0.0092,ZD)+r""" node[midway, right, font=\fss, text=ink2, align=left] {deck\\$"""+"%.3f"%ZD+r"""L$};
\draw[ink2, line width=0.3pt] """+S(HB,ZD)+" -- "+S(HB+0.0118,ZD)+r""";
\draw[ink2, line width=0.3pt] """+S(0.0017,0)+" -- "+S(HB+0.0118,0)+r""";
\end{tikzpicture}
\end{document}"""
tex=tex.replace('%(top)s',"%.1f"%top).replace('%(ox)s',str(ox))
open(FIGS+'fig3_vessel.tex','w').write(tex)
print('wrote',FIGS+'fig3_vessel.tex','HB/L=%.4f ZD/L=%.4f deadrise=%.1f'%(HB,ZD,DR))

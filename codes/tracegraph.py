"""Case-study trace graph for the Lorelei-X USV; computes impact sets (Eq. impact) and reuse ratio."""
from paths import STEP, OUT
import json
P={'p1':'payload mass','p2':'payload power demand','p3':'payload position (longitudinal and vertical)',
   'p4':'stored energy','p5':'energy-storage mass','p6':'hull form','p7':'installed propulsion power',
   'p8':'fender and rub-rail width'}
A={'a1':('Mass properties',['p1','p3','p5','p6'],['R3']),
   'a2':('Hydrostatics',['p6','a1'],['R4','R5']),
   'a3':('Stability',['a1','a2'],['R6']),
   'a4':('Power and endurance',['p2','p4','p7','a5'],['R7']),
   'a5':('Planing performance',['p6','p7','a1','a2'],['R8','R9']),
   'a6':('Seakeeping',['p6','a1','a5'],['R10']),
   'a7':('Envelope check',['p6','p8'],['R1','R2'])}
R=['R%d'%i for i in range(1,11)]
E=[]
for a,(n,ins,ev) in A.items():
    for i in ins: E.append((i,a))
    for r in ev: E.append((a,r))
succ={}
for u,v in E: succ.setdefault(u,[]).append(v)
def desc(n):
    out=set(); st=[n]
    while st:
        u=st.pop()
        for v in succ.get(u,[]):
            if v not in out: out.add(v); st.append(v)
    return out
# topological order of analyses
order=[]; seen=set()
def visit(a):
    if a in seen: return
    seen.add(a)
    for i in A[a][1]:
        if i in A: visit(i)
    order.append(a)
for a in A: visit(a)
ECR={'ECR-1 fender and rub rail':['p8'],'ECR-2 UUV launch and recovery':['p1','p2','p3'],
     'ECR-3 propulsion uprate':['p7'],'ECR-4 energy storage':['p4','p5']}
res={}
for k,N in ECR.items():
    imp=set(N)
    for n in N: imp|=desc(n)
    an=[a for a in order if a in imp]; rq=sorted([r for r in imp if r in R],key=lambda s:int(s[1:]))
    eta=1-len(an)/len(A)
    res[k]=dict(analyses=[A[a][0] for a in an],reqs=rq,eta=round(eta,2),n_an=len(an),n_rq=len(rq))
    print(k,'|',', '.join(A[a][0] for a in an),'|',rq,'| eta=%d/7=%.2f'%(7-len(an),eta))
npa=sum(1 for u,v in E if u in P); naa=sum(1 for u,v in E if u in A and v in A); nar=sum(1 for u,v in E if v in R)
print('nodes',len(P)+len(A)+len(R),'edges',len(E),'=',npa,'+',naa,'+',nar,'topo',order)
json.dump(dict(res=res,edges=[npa,naa,nar],order=order),open(OUT+'impact.json','w'),indent=1)

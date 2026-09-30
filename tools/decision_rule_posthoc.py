"""Post-hoc: probe decision rule by point estimate vs by 90%-interval upper end.

    python tools/decision_rule_posthoc.py results/decision_rule_posthoc.csv

Found after the hard-threshold test (results/HARD_RESULTS.md) and run on data
already seen: training LODO, the first confirmation, the hard thresholds. Not
a confirmation; see results/DECISION_RULE_POSTHOC.md.
"""
import sys, os; sys.path[:0]=['.','tools']
import numpy as np, pandas as pd, probe_eval as PE
from recommender import intervals as I
from recommender.capabilities import CapabilityDB
from recommender.engine import Recommender
from recommender.perfmodel import load_runs
from recommender.spec import MiningTask
db=CapabilityDB(); FAIL=10.0
def pick(model, pr, cand, rule):
    est={}
    for a in cand:
        if a in pr:
            m,_,meas=pr[a]; k="probe_memory_"+("measured" if meas else "sampled")
        elif a in model: m,k=model[a],"model_memory"
        else: continue
        est[a]= m if rule=="point" else I.interval(k,m)[1]
    return min(est,key=est.get)
def evaluate(name, truth, points, recs_for):
    PE.POINTS=points; pc=PE.probe_costs("affine"); out=[]
    for (ds,sg),g in truth.groupby(["dataset","param_value"]):
        key=(ds,round(float(sg),9))
        if key not in pc: continue
        task=MiningTask(dataset_path=PE.dataset_path(ds),data_type="transactional",threshold=float(sg),objective="memory")
        el={v.algorithm for v in db.filter(task)[0]}; c=g[g.algorithm.isin(el)]; ok=PE.completed(c)
        done=dict(zip(c.algorithm[ok],c.peak_memory_mb[ok]))
        if not done: continue
        best=min(done.values()); recs,_,_=recs_for(ds).recommend(task)
        model={r.algorithm:r.memory_mb for r in recs}; allc=set(c.algorithm)
        eng=next(r.algorithm for r in recs if r.algorithm in allc)
        reg=lambda a: done[a]/best if a in done else FAIL
        out.append({"set":name,"dataset":ds,"all_ok":bool(ok.all()),"engine":reg(eng),
                    "point":reg(pick(model,pc[key]["costs"],allc,"point")),
                    "upper":reg(pick(model,pc[key]["costs"],allc,"upper"))})
    return out
rows=[]
runs=load_runs(str(PE.TABLE)); tr=pd.read_csv(PE.TABLE); tr=tr[tr.category==1]; cache={}
def lodo(ds):
    if ds not in cache: cache[ds]=Recommender(runs=runs,exclude_dataset=ds)
    return cache[ds]
rows+=evaluate("training LODO",tr,PE._ROOT/"results/probe_points.csv",lodo)
full=Recommender()
t3=pd.read_csv("results/real_extra3_summary.csv"); rows+=evaluate("confirm",t3,PE._ROOT/"results/probe_points_confirm.csv",lambda d:full)
th=pd.read_csv("results/hard_summary.csv"); rows+=evaluate("hard",th,PE._ROOT/"results/probe_points_hard.csv",lambda d:full)
d=pd.DataFrame(rows); d.to_csv(sys.argv[1],index=False)
g=PE.gmean
for (s,a),q in d.groupby(["set","all_ok"]):
    print("%-14s all-complete=%-5s n=%3d | engine %.3f  probe-point %.3f  probe-upper %.3f"%(s,a,len(q),g(q.engine),g(q.point),g(q.upper)))
print("ALL n=%d | engine %.3f point %.3f upper %.3f"%(len(d),g(d.engine),g(d.point),g(d.upper)))
print("failed picks: engine %d point %d upper %d"%((d.engine==FAIL).sum(),(d.point==FAIL).sum(),(d.upper==FAIL).sum()))

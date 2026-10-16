"""Frozen H2 empirical worker: one identified fit, durable draws, full contrasts."""
from __future__ import annotations
import argparse
import json
import os
import resource
import sys
import time
import traceback
from pathlib import Path
from common import ROOT, sha, dump, utc, environment, summary
import numpy as np
from model import build, transform, contrasts, draw_choices
from predictive import metrics, summarize_rows

DATASETS=('uwa','nicolas')
FILES=['common.py','model.py','predictive.py','summarize.py','prepare.py','empirical.py','remote_batch.py']


def job_info(job):
    import re
    match=re.fullmatch(r'(uwa|nicolas)-s([0-3])-c([0-7])',job)
    if not match:raise ValueError('Invalid job identifier')
    ds,s,c=match.groups();s,c=int(s),int(c)
    return dict(id=job,dataset=ds,specification=s,component=c,
                seed=2026101700+100*DATASETS.index(ds)+10*s+c)


def all_jobs():
    first=['nicolas-s0-c0','nicolas-s0-c1']
    return first+[f'{ds}-s{s}-c{c}' for s in range(4) for c in range(8) for ds in DATASETS
                  if f'{ds}-s{s}-c{c}' not in first]


def check_bundle(folder):
    meta=json.loads((folder/'bundle.json').read_text())
    for name,digest in meta['files'].items():
        if Path(name).name!=name:raise ValueError('Unsafe bundle path')
        if sha(folder/name)!=digest:raise ValueError('Input hash mismatch: '+name)
    for name,digest in meta['source_hashes'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Execution source mismatch: '+name)
    return meta


def load_inputs(folder,job):
    spec=job_info(job);meta=check_bundle(folder);ds=spec['dataset'];s=spec['specification']
    suffix='-design-anderson328.npz' if s==3 else '-design.npz'
    with np.load(folder/(ds+suffix),allow_pickle=False) as z:
        d={k:z[k] if z[k].ndim else int(z[k]) for k in z.files}
    with np.load(folder/f'predictors-{s}.npz',allow_pickle=False) as z:
        x={k:z[k][spec['component']] for k in ('c','v','h')}
    suffix='-observed-anderson328-NOT-FOR-PREFLIGHT.npy' if s==3 else '-observed-choices-NOT-FOR-PREFLIGHT.npy'
    y=np.load(folder/(ds+suffix),allow_pickle=False)
    frame='anderson_328' if s==3 else 'shared_269'
    support=np.load(folder/f'rating-counts-{frame}.npy',allow_pickle=False)
    if len(y)!=len(d['p']) or len(support)!=d['W'] or len(x['c'])!=d['W']:raise ValueError('Input shape mismatch')
    return spec,meta,d,x,y,support


def prepare_bundle(destination):
    import shutil
    src=ROOT/'private/h2-implementation-20261016'
    receipt=json.loads((ROOT/'results/h2-implementation-20261016/preparation.json').read_text())
    names=[f'predictors-{i}.npz' for i in range(4)]+[f'rating-counts-{f}.npy' for f in ('shared_269','anderson_328')]
    for ds in DATASETS:
        names += [ds+suffix for suffix in ('-design.npz','-design-anderson328.npz',
                  '-observed-choices-NOT-FOR-PREFLIGHT.npy','-observed-anderson328-NOT-FOR-PREFLIGHT.npy')]
    if destination.exists():raise FileExistsError('Do not overwrite a frozen bundle')
    destination.mkdir(parents=True)
    files={}
    for name in names:
        path=src/name;digest=sha(path)
        if receipt['outputs'][str(path.relative_to(ROOT))]!=digest:raise ValueError('Preparation changed')
        shutil.copy2(path,destination/name);files[name]=digest
    paths=['scripts/h2_production/'+name for name in FILES]
    paths+=['notes/h2-production-specification-2026-10-16.md','notes/h2-empirical-execution-2026-10-16.md','requirements-h2.txt']
    meta=dict(at=utc(),files=files,source_hashes={name:sha(ROOT/name) for name in paths},
              preparation_sha256=sha(ROOT/'results/h2-implementation-20261016/preparation.json'),
              score_constants=receipt['score_constants'],jobs=[job_info(j) for j in all_jobs()],
              sampling=dict(chains=4,draws=1000,warmup=1000,target_accept=.95,maxdepth=12),
              posterior_predictive_replications=200)
    dump(destination/'bundle.json',meta)
    print(json.dumps({'bundle_sha256':sha(destination/'bundle.json'),'files':len(files),'jobs':len(meta['jobs'])}))


def summarize_fit(folder,spec,meta,d,x,y,support):
    import arviz as az
    import xarray as xr
    from summarize import diagnostics, conditional_choices
    start=time.perf_counter();dims=json.loads((folder/'dimensions.json').read_text())
    with np.load(folder/'posterior.npz',allow_pickle=False) as z:
        post=xr.Dataset({k:(v,z['post_'+k]) for k,v in dims['posterior'].items()})
        stats={k:z['stat_'+k] for k in dims['sample_stats']}
    if post.sizes['chain']!=4 or post.sizes['draw']!=1000:raise ValueError('Wrong posterior budget')
    if any(not np.isfinite(v.values).all() for v in post.data_vars.values()):raise ValueError('Nonfinite posterior')
    dg=diagnostics(post);scalar={}
    for k,v in post.data_vars.items():
        if k.startswith('z_'):continue
        scalar[k]=dict(**summary(v.values),**{name:values[k] for name,values in dg.items()})
    extrema={}
    for name in ('rhat','ess_bulk','ess_tail'):
        a=np.concatenate([np.asarray(v).ravel() for v in dg[name].values()])
        extrema[name]=dict(minimum=np.nanmin(a),maximum=np.nanmax(a),nonfinite_count=np.sum(~np.isfinite(a)))
    dump(folder/'diagnostics.json',dict(scalars=scalar,extrema=extrema,
         divergences=int(np.sum(stats['diverging'])),maxdepth_count=int(np.sum(stats.get('maxdepth_reached',np.zeros(1)))),
         diagnostics_are_numerical_evidence_not_scientific_verdicts=True))
    rng=np.random.default_rng(spec['seed']+1000000)
    selected={chain:set((np.arange(50)*20+rng.integers(20)).tolist()) for chain in range(4)}
    effects=[];joint=[];conditional=[]
    for chain in range(4):
        for draw in range(1000):
            pars=transform({k:v.values[chain,draw] for k,v in post.data_vars.items()})
            effects.append(contrasts(d,x,pars))
            if draw in selected[chain]:
                joint.append(metrics(d,draw_choices(d,x,pars,rng),x,support))
                if spec['dataset']=='nicolas':conditional.append(metrics(d,conditional_choices(d,x,pars,y,rng),x,support))
        print(json.dumps({'event':'summary_progress','job':spec['id'],'chains_complete':chain+1,'at':utc()}),flush=True)
    derived=xr.Dataset({k:(('chain','draw'),np.array([e[k] for e in effects]).reshape(4,1000)) for k in effects[0]})
    diag=diagnostics(derived);out={}
    for k,v in derived.data_vars.items():
        a=v.values;row=dict(**summary(a),**{name:values[k] for name,values in diag.items()})
        indicator=derived[[k]].copy();indicator[k]=(v<(1 if k=='probability_ratio' else 0)).astype(float)
        if k=='probability_ratio':row.pop('p_negative')
        label='p_below_one' if k=='probability_ratio' else 'p_negative'
        row[label]=float(indicator[k].mean());row['mcse_'+label]=np.asarray(az.mcse(indicator,method='mean')[k])
        out[k]=row
    vals=derived['mean_log_ratio'].values.ravel();grid=np.linspace(min(0,vals.min()),max(0,vals.max()),201)
    frame='anderson_328' if spec['specification']==3 else 'shared_269'
    label='original' if spec['specification']==1 else 'revised'
    limits=meta['score_constants'][label+'_'+frame];ep=np.column_stack([x['c']-.5,x['c']+.5])
    outside=(ep<limits['posterior_mean_c_min'])|(ep>limits['posterior_mean_c_max'])
    dump(folder/'contrasts.json',dict(contrasts=out,draws=4000,
         exponentiated_posterior_mean_log_contrast=float(np.exp(vals.mean())),
         endpoint_fraction_outside=float(outside.mean()),word_fraction_any_endpoint_outside=float(outside.any(1).mean()),
         exceedance=dict(grid=grid,probability_greater=np.mean(vals[:,None]>grid,axis=0))))
    np.savez_compressed(folder/'contrast-draws.npz',**{k:v.values for k,v in derived.data_vars.items()})
    obs=metrics(d,y,x,support)
    dump(folder/'predictive.json',dict(replications=len(joint),joint=summarize_rows(joint,obs),
         conditional_history=summarize_rows(conditional,obs) if conditional else [],observed=obs,
         conditional_replications=len(conditional),selected={str(k):sorted(v) for k,v in selected.items()}))
    dump(folder/'predictive-replications.json',dict(joint=joint,conditional_history=conditional))
    # Independently verify one posterior contrast through direct probability tilting.
    from model import utilities,probabilities
    pars=transform({k:v.values[0,0] for k,v in post.data_vars.items()})
    ids=np.flatnonzero(d['b']==0);eta,bc=utilities(d,x,pars,y,ids);p=probabilities(eta)[:,1:]
    plus=np.exp(.5*bc[:,None]);minus=1/plus
    hi=p*plus/(1-p+p*plus);lo=p*minus/(1-p+p*minus)
    counts=np.bincount(d['p'][ids],minlength=d['P']);weights=1/(d['P']*counts[d['p'][ids]])
    independent={'mean_log_ratio':float(weights@np.mean(np.log(hi/lo),axis=1)),
                 'probability_difference_per_1000':float(1000*weights@np.mean(hi-lo,axis=1))}
    for k,value in independent.items():
        if not np.isclose(value,effects[0][k],rtol=1e-8,atol=1e-10):raise ValueError('Independent contrast disagreement')
    dump(folder/'summary-receipt.json',dict(at=utc(),elapsed_seconds=time.perf_counter()-start,
        contrast_draws=4000,joint_replications=200,conditional_replications=len(conditional),
        independent_first_contrast=independent,source_hashes=meta['source_hashes']))


def run_fit(inputs,output,job,owner,cores=4):
    import nutpie
    from importlib.metadata import version
    spec,meta,d,x,y,support=load_inputs(inputs,job)
    for line in (ROOT/'requirements-h2.txt').read_text().splitlines():
        if '==' in line:
            name,wanted=line.split('==');actual=version(name)
            if actual!=wanted:raise ValueError(f'Package mismatch: {name} {actual} != {wanted}')
    output.mkdir(parents=True,exist_ok=True);receipt=output/'fit.json'
    if receipt.exists():raise RuntimeError('Job was already attempted; no automatic retry')
    record=dict(job=spec,owner=owner,state='running',started_at=utc(),bundle_sha256=sha(inputs/'bundle.json'),
                source_hashes=meta['source_hashes'],environment=environment(),cores=cores,empirical_outcomes=True)
    dump(receipt,record);start=time.perf_counter()
    try:
        tick=time.perf_counter();m=build(d,x,y);compiled=nutpie.compile_pymc_model(m,var_names=[v.name for v in m.free_RVs],freeze_model=True)
        record['compile_seconds']=time.perf_counter()-tick;dump(receipt,record)
        last=[0.]
        def progress(chains):
            now=time.perf_counter()
            if now-last[0]>=30:
                event=dict(at=utc(),job=job,elapsed_seconds=now-start,finished_draws=[int(c.finished_draws) for c in chains],latest_steps=[int(c.latest_num_steps) for c in chains])
                dump(output/'progress.json',event);print(json.dumps(event),flush=True);last[0]=now
        tick=time.perf_counter()
        trace=nutpie.sample(compiled,draws=1000,tune=1000,chains=4,cores=cores,seed=spec['seed'],save_warmup=False,
                           target_accept=.95,maxdepth=12,progress_bar=False,progress_callback=progress)
        record['sampling_seconds']=time.perf_counter()-tick
        post=trace.posterior.to_dataset();stats=trace.sample_stats.to_dataset()
        arrays={'post_'+k:np.asarray(v) for k,v in post.data_vars.items()}
        numeric={k:v for k,v in stats.data_vars.items() if np.asarray(v).dtype!=object}
        arrays.update({'stat_'+k:np.asarray(v) for k,v in numeric.items()})
        np.savez_compressed(output/'posterior.npz',**arrays)
        dump(output/'dimensions.json',dict(posterior={k:list(v.dims) for k,v in post.data_vars.items()},sample_stats={k:list(v.dims) for k,v in numeric.items()}))
        record['fit_elapsed_seconds']=time.perf_counter()-start
        del trace,post,stats,arrays,compiled,m
        import gc;gc.collect()
        summarize_fit(output,spec,meta,d,x,y,support)
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record.update(state='complete',ended_at=utc(),elapsed_seconds=time.perf_counter()-start,
                      peak_resident_bytes=peak if sys.platform=='darwin' else peak*1024)
        dump(receipt,record)
    except BaseException as exc:
        record.update(state='failed',ended_at=utc(),elapsed_seconds=time.perf_counter()-start,error=repr(exc),traceback=traceback.format_exc())
        dump(receipt,record);raise
    finally:
        dump(output/'manifest.json',dict(job=job,state=record['state'],files={p.name:dict(sha256=sha(p),bytes=p.stat().st_size) for p in output.iterdir() if p.is_file() and p.name!='manifest.json'}))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('destination',type=Path)
    a=sub.add_parser('fit');a.add_argument('--inputs',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    a.add_argument('--job',required=True);a.add_argument('--owner',required=True);a.add_argument('--cores',type=int,default=4)
    args=p.parse_args()
    if args.command=='prepare':prepare_bundle(args.destination)
    else:run_fit(args.inputs,args.output,args.job,args.owner,args.cores)
if __name__=='__main__':main()

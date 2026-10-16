"""Summarize the single artificial preflight and project, never launch, costs."""
from __future__ import annotations
import json
import resource
import sys
import time
from common import ROOT,PRIVATE,OUT,dump,sha,summary,utc,source_receipt,environment
import numpy as np
import xarray as xr
import arviz as az
from prepare import load_design,load_predictors
from model import transform,contrasts,draw_choices,utilities,probabilities,shapes
from predictive import metrics,summarize_rows,plot_checks


def diagnostics(ds):
    result={}
    for label,values in [('rhat',az.rhat(ds,method='rank')),('ess_bulk',az.ess(ds,method='bulk')),
                         ('ess_tail',az.ess(ds,method='tail')),('mcse_mean',az.mcse(ds,method='mean'))]:
        result[label]={k:np.asarray(v) for k,v in values.data_vars.items()}
    return result


def scalar_summary(ds,truth):
    diag=diagnostics(ds)
    return {k:dict(**summary(v.values.ravel()),generating_value=truth.get(k),
                   **{label:values[k] for label,values in diag.items()}) for k,v in ds.data_vars.items()}


def conditional_choices(d,x,pars,y,rng):
    """Hold the artificial first responses fixed and replicate only block two."""
    rep=y.copy();rows=np.flatnonzero(d['b']==1)
    eta,_=utilities(d,x,pars,y,rows);cum=np.cumsum(probabilities(eta),axis=1);cum[:,-1]=1.
    rep[rows]=np.sum(rng.random(len(rows))[:,None]>cum,axis=1)
    return rep


def plots(post,derived,truth):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    keys=['alpha','beta','gamma','sigma_a','sigma_d','lambda_repeat']
    fig,axes=plt.subplots(3,2,figsize=(11,8))
    for ax,k in zip(axes.flat,keys):
        for chain in range(post.sizes['chain']):ax.plot(post[k][chain],lw=.45,alpha=.65,label=f'Chain {chain+1}')
        ax.axhline(truth[k],color='black',ls='--',lw=1);ax.set_title(k);ax.set_xlabel('Retained draw')
    axes[0,0].legend(ncol=4,fontsize=7)
    fig.suptitle('Artificial-data chains; dashed lines are generating values')
    fig.tight_layout();fig.savefig(OUT/'artificial-traces.png',dpi=160);plt.close(fig)
    vals=derived['mean_log_ratio'].values.ravel();grid=np.linspace(min(0,vals.min()),max(0,vals.max()),201)
    exceed=np.mean(vals[:,None]>grid[None,:],axis=0)
    fig,ax=plt.subplots(figsize=(7,4));ax.plot(grid,exceed,color='#356b9a')
    ax.axvline(truth['mean_log_ratio'],color='#bc503e',ls='--',label='Generating contrast')
    ax.set(xlabel='Mean log probability ratio',ylabel='Posterior probability above value',ylim=(-.02,1.02),
           title='Artificial-data contrast, 200 chain-balanced draws')
    ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(OUT/'artificial-exceedance.png',dpi=160);plt.close(fig)
    return dict(grid=grid,probability_greater=exceed)


def main():
    start=time.perf_counter()
    dump(ROOT/'logs/h2-implementation-20261016-summary-environment.json',environment())
    fit=json.loads((OUT/'artificial-fit.json').read_text())
    assert fit['status']=='complete' and fit['empirical_outcomes'] is False
    assert sha(PRIVATE/'artificial-posterior.npz')==fit['posterior_sha256']
    assert sha(PRIVATE/'artificial-posterior-dimensions.json')==fit['dimensions_sha256']
    gen=json.loads((OUT/'artificial-generation.json').read_text());s=fit['settings']
    assert sha(OUT/'artificial-generation.json')==fit['generation_sha256']
    dims=json.loads((PRIVATE/'artificial-posterior-dimensions.json').read_text())
    with np.load(PRIVATE/'artificial-posterior.npz') as z:
        post=xr.Dataset({k:(v,z['post_'+k]) for k,v in dims['posterior'].items()})
        # Nutpie serializes optional human-readable messages as object arrays.
        # Keep these in the original archive and read numerical diagnostics
        # without unpickling that column.
        stats={k:z['stat_'+k] for k in dims['sample_stats'] if k!='divergence_message'}
    for k in post:
        assert post[k].dims[:2]==('chain','draw') and np.isfinite(post[k]).all(),k
    truth={**gen['generating_fixed'],**{'sigma_'+k:v for k,v in gen['generating_scales'].items()},**gen['generating_contrast']}
    scalars=post[[k for k in post if not k.startswith('z_')]]
    fixed=scalar_summary(scalars,truth)
    all_diag=diagnostics(post);extrema={}
    for label in ('rhat','ess_bulk','ess_tail'):
        vals=np.concatenate([np.asarray(v).ravel() for v in all_diag[label].values()])
        extrema[label]=dict(nonfinite_count=int(np.sum(~np.isfinite(vals))),
            minimum=float(vals.min()) if np.isfinite(vals).all() else None,
            maximum=float(vals.max()) if np.isfinite(vals).all() else None)
    stat_summary={k:dict(shape=v.shape,minimum=np.min(v),median=np.median(v),maximum=np.max(v))
                  for k,v in stats.items() if np.issubdtype(v.dtype,np.number) or v.dtype==bool}
    divergences=int(np.sum(stats['diverging']))
    depth_key=next((k for k in ('tree_depth','depth') if k in stats),None)
    if 'maxdepth_reached' in stats:max_depth_count=int(np.sum(stats['maxdepth_reached']))
    elif depth_key:max_depth_count=int(np.sum(stats[depth_key]>=s['max_treedepth']))
    else:max_depth_count=None
    diagnostic_record=dict(at=utc(),scalars=fixed,all_parameters_extrema=extrema,divergences=divergences,
        max_depth_count=max_depth_count,tree_depth_variable=depth_key,sample_statistics=stat_summary,
        unread_object_column='divergence_message; retained in the pinned original archive')
    dump(OUT/'artificial-diagnostics.json',diagnostic_record)
    print('Diagnostics saved; starting 200 posterior predictive/contrast evaluations.',flush=True)
    d=load_design('nicolas');x=load_predictors(s['artificial_variant'],s['artificial_component'])
    y=np.load(PRIVATE/'artificial-y.npy');support=np.load(PRIVATE/'rating-counts-shared_269.npy')
    observed=metrics(d,y,x,support);rng=np.random.default_rng(s['posterior_predictive_seed'])
    chains,draws=post.sizes['chain'],post.sizes['draw'];per=s['posterior_predictive_draws']//chains
    assert per*chains==s['posterior_predictive_draws']==s['artificial_contrast_draws'] and draws%per==0
    stride=draws//per;selected=np.array([np.arange(per)*stride+rng.integers(stride) for _ in range(chains)])
    joint=[];conditional=[];effects=[];contrast_seconds=0.;predictive_seconds=0.
    for chain in range(chains):
        for draw in selected[chain]:
            pars=transform({k:v.values[chain,draw] for k,v in post.data_vars.items()})
            tick=time.perf_counter();effects.append(contrasts(d,x,pars));contrast_seconds+=time.perf_counter()-tick
            tick=time.perf_counter()
            joint.append(metrics(d,draw_choices(d,x,pars,rng),x,support))
            conditional.append(metrics(d,conditional_choices(d,x,pars,y,rng),x,support))
            predictive_seconds+=time.perf_counter()-tick
        print(f'Chain {chain+1}: 50 predictive and contrast evaluations complete',flush=True)
    derived=xr.Dataset({k:(('chain','draw'),np.array([r[k] for r in effects]).reshape(chains,per)) for k in effects[0]})
    derived_summary=scalar_summary(derived,truth)
    # Negative-probability MCSE is separate from the MCSE of the contrast mean.
    for k in derived:
        threshold=1. if k=='probability_ratio' else 0.
        indicator=derived[[k]].copy();indicator[k]=(indicator[k]<threshold).astype(float)
        label='p_below_one' if k=='probability_ratio' else 'p_negative'
        if k=='probability_ratio':derived_summary[k].pop('p_negative')
        derived_summary[k][label]=float(indicator[k].mean())
        derived_summary[k]['mcse_'+label]=np.asarray(az.mcse(indicator,method='mean')[k])
    predictive=dict(joint=summarize_rows(joint,observed),conditional_history=summarize_rows(conditional,observed),
        conditional_interpretation='Artificial first outcomes held fixed; only second responses replicated',
        observed_interpretation='One artificial dataset; no empirical production outcomes',replications=len(joint))
    dump(OUT/'artificial-predictive.json',predictive)
    plot_checks(predictive['joint'],OUT/'artificial-predictive.png','Nicolas artificial joint posterior predictive')
    plot_checks(predictive['conditional_history'],OUT/'artificial-conditional-predictive.png','Nicolas artificial conditional-history predictive')
    curve=plots(post,derived,truth)
    preparation=json.loads((OUT/'preparation.json').read_text())
    constants=preparation['score_constants']['revised_shared_269']
    lo,hi=constants['posterior_mean_c_min'],constants['posterior_mean_c_max']
    endpoints=np.column_stack([x['c']-.5,x['c']+.5]);outside=(endpoints<lo)|(endpoints>hi)
    effect_record=dict(at=utc(),contrasts=derived_summary,draws=chains*per,selected_draw_indices=selected,
        exponentiated_posterior_mean_log_contrast=float(np.exp(derived_summary['mean_log_ratio']['mean'])),
        ratio_summary_interpretation='Ratio summaries describe exp(mean log contrast) within each draw; their posterior mean need not equal exp of the posterior mean log contrast.',
        thinning_stride=stride,mcse_scope='Approximation from 50 regularly thinned retained draws per chain; scalar parameter summaries use all 4000 draws',
        endpoint_fraction_outside_posterior_mean_frame_range=float(outside.mean()),
        word_fraction_with_any_endpoint_outside=float(outside.any(axis=1).mean()),exceedance=curve,
        single_measurement_component=True,cut_integration_assessed=False)
    dump(OUT/'artificial-contrasts.json',effect_record)
    np.savez_compressed(PRIVATE/'artificial-contrast-draws.npz',**{k:v.values for k,v in derived.items()},selected=selected)
    dump(PRIVATE/'artificial-predictive-discrepancies.json',dict(joint=joint,conditional=conditional))
    elapsed=time.perf_counter()-start
    # Arithmetic scenarios, not posterior intervals for runtime. N*W ignores
    # geometry-dependent leapfrog counts and adaptation, which empirical data may change.
    sizes=preparation['response_structure'];ratio=sizes['uwa']['responses']/sizes['nicolas']['responses']
    wordfactor=24+8*(328/269)
    discounted_factor=wordfactor*(1+ratio);same_cost_factor=2*wordfactor
    contrast_factor=wordfactor*(1+sizes['uwa']['first_encounters']/sizes['nicolas']['first_encounters'])
    other_seconds=elapsed-contrast_seconds-predictive_seconds
    full_contrast_seconds=contrast_seconds*(chains*draws/(chains*per))
    projected={}
    for label,factor,cfactor in [('row_word_scaled',discounted_factor,contrast_factor),
                               ('equal_dataset_cost',same_cost_factor,same_cost_factor)]:
        postprocessing=full_contrast_seconds*cfactor+predictive_seconds*factor+64*other_seconds
        projected[label]=dict(nicolas_equivalent_fits=factor,
            sampling_hours=fit['sampling_seconds']*factor/3600,
            projected_full_contrast_and_200_replication_summary_hours=postprocessing/3600,
            total_hours=(fit['sampling_seconds']*factor+64*fit['compile_seconds']+postprocessing)/3600)
    parameter_counts={}
    for ds in ('uwa','nicolas'):
        parameter_counts[ds]={}
        for variant in (0,3):
            design=load_design(ds,variant)
            parameter_counts[ds][str(variant)]=sum(int(np.prod(a)) for a in shapes(design).values())+8+(10 if ds=='nicolas' else 4)
    assert parameter_counts['nicolas']['0']==fit['unconstrained_parameters']
    archive_factor=sum(24*v['0']+8*v['3'] for v in parameter_counts.values())/fit['unconstrained_parameters']
    archive_bytes=(PRIVATE/'artificial-posterior.npz').stat().st_size
    summary_peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform!='darwin':summary_peak*=1024
    compute=dict(at=utc(),conditional_empirical_fits=64,empirical_fits_launched=0,
        hardware=json.loads((ROOT/'logs/h2-implementation-20261016-hardware.json').read_text()),
        measured_compile_seconds=fit['compile_seconds'],measured_sampling_seconds=fit['sampling_seconds'],
        measured_fit_elapsed_seconds=fit['elapsed_seconds'],measured_summary_seconds=elapsed,
        measured_200_contrast_seconds=contrast_seconds,measured_200_joint_and_conditional_predictive_seconds=predictive_seconds,
        measured_peak_resident_gib=fit['peak_resident_bytes']/2**30,
        measured_summary_peak_resident_gib=summary_peak/2**30,
        measured_pipeline_peak_resident_gib=max(fit['peak_resident_bytes'],summary_peak)/2**30,
        artificial_posterior_archive_bytes=archive_bytes,parameter_counts=parameter_counts,
        projected_64_posterior_archives_gib=archive_bytes*archive_factor/2**30,
        projections=projected,assumptions=['Conditional fits run sequentially, each with four concurrent chains',
        'Three 269-word variants and one 328-word variant, each with eight components per dataset',
        'Sampling N*W scaling is approximate; posterior geometry and warmup may dominate',
        '64 separately charged compiles; no assumed amortization or cache benefit',
        'Contrast time is scaled from 200 evaluated draws to all 4000 retained draws; predictions assume 200 joint and conditional replications per component',
        'Diagnostic and remaining summary costs are charged 64 times; archive disk projection scales by parameter count and assumes similar compression',
        'The equal-dataset-cost scenario is not an upper bound; neither scenario is a confidence interval',
        'Fit and postprocessing peaks are measured separately; empirical or broad-frame peaks may differ'])
    dump(OUT/'compute-estimate.json',compute)
    dump(OUT/'summary-receipt.json',dict(at=utc(),empirical_outcomes_used=False,source_hashes=source_receipt(),
        artificial_fit_sha256=sha(OUT/'artificial-fit.json'),elapsed_seconds=elapsed,
        outputs={str(p.relative_to(ROOT)):sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='summary-receipt.json'}))
    print('Artificial summaries and provisional 64-fit compute scenarios saved; zero empirical fits.',flush=True)


if __name__=='__main__':main()

"""Fixed discrepancy summaries for simulated outcomes, never fit selection."""
from __future__ import annotations
import numpy as np
from model import history


def mean_or_nan(x):
    return float(np.mean(x)) if len(x) else float('nan')


def metrics(design,y,predictors,support):
    y=np.asarray(y);p,g,b=[design[k] for k in ('p','g','b')];P,G,W=[int(design[k]) for k in ('P','G','W')]
    inside=y>0;outside=~inside;counts=np.bincount(y,minlength=W+1)[1:]
    count_g=np.zeros((G,W),dtype=int);np.add.at(count_g,(g[inside],y[inside]-1),1)
    present=(count_g>0).astype(np.int16);intersection=present@present.T
    sizes=present.sum(1);union=sizes[:,None]+sizes[None,:]-intersection
    upper=np.triu(np.ones((G,G),dtype=bool),1)&(union>0)
    shares=counts/max(1,int(inside.sum()))
    result=dict(outside_share=float(outside.mean()),inside_count=int(inside.sum()),
        inside_top_word_share=float(shares.max()) if inside.any() else float('nan'),
        inside_concentration=float(shares@shares) if inside.any() else float('nan'),
        zero_words=int(np.sum(counts==0)),group_zero_words_mean=float(np.mean(W-sizes)),
        group_jaccard_mean=mean_or_nan((intersection[upper]/union[upper])),
        group_jaccard_valid_pairs=int(upper.sum()))
    for unit,idx,n in [('participant',p,P),('group',g,G)]:
        no=np.bincount(idx[~inside],minlength=n);total=np.bincount(idx,minlength=n)
        values=no/total
        for label,q in [('q10',.1),('q50',.5),('q90',.9)]:result[f'outside_{unit}_{label}']=float(np.quantile(values,q))
    ninside=np.bincount(p[inside],minlength=P);valid=ninside>0
    result['participants_without_inside']=int(np.sum(~valid))
    for var in ('c','v'):
        values=predictors[var][y[inside]-1]
        mean=np.bincount(p[inside],weights=values,minlength=P)[valid]/ninside[valid]
        result['produced_'+var+'_mean']=mean_or_nan(values)
        result['participant_produced_'+var+'_mean']=mean_or_nan(mean)
        result['participant_produced_'+var+'_sd']=float(np.std(mean)) if len(mean) else float('nan')
    for label,mask in [('n1',support==1),('n2to5',(support>=2)&(support<=5)),('n6plus',support>=6)]:
        result['inside_share_'+label]=float(counts[mask].sum()/inside.sum()) if inside.any() else float('nan')
        result['zero_fraction_'+label]=float(np.mean(counts[mask]==0)) if mask.any() else float('nan')
    if np.any(b):
        prev=history(design,y);second=b==1;eligible=second&(prev>0)
        result['second_minus_first_inside']=float(inside[second].mean()-inside[~second].mean())
        result['repeat_in_frame']=mean_or_nan((y[eligible]==prev[eligible]).astype(float))
        outprev=second&(prev==0)
        result['outside_after_outside']=mean_or_nan((y[outprev]==0).astype(float))
        result['repeat_eligible_rows']=int(eligible.sum())
    return result


def summarize_rows(rows,observed=None):
    out=[]
    for key in rows[0]:
        values=np.array([r[key] for r in rows],dtype=float);values=values[np.isfinite(values)]
        row=dict(check=key,n_replications=len(rows),n_defined=len(values))
        if len(values):row.update(q05=float(np.quantile(values,.05)),median=float(np.median(values)),q95=float(np.quantile(values,.95)),mean=float(values.mean()))
        if observed is not None:
            row['observed']=observed[key]
            row['fraction_rep_ge_observed']=float(np.mean(values>=observed[key])) if len(values) and np.isfinite(observed[key]) else None
        out.append(row)
    return out


def plot_checks(rows,path,title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator
    chosen=['outside_share','inside_top_word_share','zero_words','group_jaccard_mean',
            'participant_produced_c_sd','repeat_in_frame']
    selected=[r for key in chosen for r in rows if r['check']==key and r['n_defined']]
    fig,axes=plt.subplots(2,3,figsize=(11,6))
    for ax,row in zip(axes.flat,selected):
        ax.plot([row['q05'],row['q95']],[0,0],color='#356b9a',lw=4)
        ax.plot(row['median'],0,'o',color='#356b9a')
        if 'observed' in row:ax.axvline(row['observed'],color='#bc503e',label='Artificial observed')
        ax.set_title(row['check'].replace('_',' '),fontsize=10);ax.set_yticks([]);ax.grid(axis='x',alpha=.2)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4,integer=row['check']=='zero_words'))
    for ax in list(axes.flat)[len(selected):]:ax.axis('off')
    key='Dots: medians; bars: central 90% predictive intervals'
    if any('observed' in row for row in selected):key+='; red: artificial observed'
    fig.suptitle(title+'\n'+key,fontsize=10)
    fig.tight_layout();fig.savefig(path,dpi=160);plt.close(fig)

"""Exact categorical likelihood and independent NumPy generation/contrasts.

There is intentionally no empirical-fitting CLI in this implementation stage.
"""
from __future__ import annotations
from common import centered
import numpy as np
from scipy.special import logsumexp, expit

FIXED = {'alpha':2., 'beta':1., 'gamma':1., 'kappa':.5}
BLOCK_FIXED = {'delta':1.,'zeta':1.,'lambda_repeat':1.,'beta2':.5,'gamma2':.5,'kappa2':.5}
SCALES = {'a':1.5,'d':1.5,'A':.75,'G':.75,'B':.5,'C':.5,'E':.5,'H':.5}


def shapes(design):
    p,g,w=[int(design[k]) for k in ('P','G','W')]
    return {'a':(w,), 'd':(g,w), 'A':(p,), 'G':(g,), 'B':(p,), 'C':(g,), 'E':(p,), 'H':(g,)}


def transform(raw):
    out={k:float(raw[k]) for k in {**FIXED,**BLOCK_FIXED} if k in raw}
    for name in SCALES:
        out[name]=float(raw['sigma_'+name])*centered(raw['z_'+name], 'double' if name=='d' else None)
    return out


def prior_raw(design,rng):
    block=bool(np.any(design['b']))
    raw={k:rng.normal(0,sd) for k,sd in {**FIXED,**(BLOCK_FIXED if block else {})}.items()}
    for name,shape in shapes(design).items():
        raw['sigma_'+name]=abs(rng.normal(0,SCALES[name]));raw['z_'+name]=rng.normal(size=shape)
    return raw


def history(design,y):
    first=design['first'];prev=np.zeros(len(first),dtype=np.int64); second=first>=0
    prev[second]=np.asarray(y)[first[second]]
    return prev


def utilities(design,predictors,pars,y=None,rows=None):
    ids=np.arange(len(design['p'])) if rows is None else np.asarray(rows)
    p,g,b=[design[k][ids] for k in ('p','g','b')]; w=int(design['W'])
    c,v,h=[predictors[k] for k in ('c','v','h')]
    inside=pars['alpha']+pars['A'][p]+pars['G'][g]
    bc=pars['beta']+pars['B'][p]+pars['C'][g]
    bv=pars['gamma']+pars['E'][p]+pars['H'][g]
    quadratic=np.full(len(ids),pars['kappa'])
    if np.any(design['b']):
        if y is None: raise ValueError('Second-block utilities require supplied first responses')
        prev=history(design,y)[ids]
        inside=inside+b*(pars['delta']+pars['zeta']*(prev==0))
        bc=bc+b*pars['beta2'];bv=bv+b*pars['gamma2'];quadratic=quadratic+b*pars['kappa2']
    eta=(-np.log(w)+inside[:,None]+pars['a'][None,:]+pars['d'][g,:]+
         bc[:,None]*c+bv[:,None]*v+quadratic[:,None]*h)
    if np.any(design['b']):
        repeat=np.flatnonzero((b==1)&(prev>0))
        eta[repeat,prev[repeat]-1]+=pars['lambda_repeat']
    return eta,bc


def probabilities(eta,outside=0.):
    full=np.column_stack([np.full(len(eta),outside),eta])
    return np.exp(full-logsumexp(full,axis=1)[:,None])


def draw_choices(design,predictors,pars,rng):
    y=np.zeros(len(design['p']),dtype=np.int64)
    for block in (0,1):
        rows=np.flatnonzero(design['b']==block)
        if not len(rows): continue
        eta,_=utilities(design,predictors,pars,y,rows)
        cumulative=np.cumsum(probabilities(eta),axis=1); cumulative[:,-1]=1.
        u=rng.random(len(rows))
        y[rows]=np.sum(u[:,None]>cumulative,axis=1)
    return y


def contrasts(design,predictors,pars,chunk=256):
    """Exact prescribed first-encounter contrast; hold each competitor fixed."""
    rows=np.flatnonzero(design['b']==0); p=design['p'][rows]
    counts=np.bincount(p,minlength=int(design['P']));assert np.all(counts>0)
    logratio=0.;pdiff=0.
    for lo in range(0,len(rows),chunk):
        ix=rows[lo:lo+chunk]
        # History cannot affect first encounters; zero vector is a harmless placeholder.
        eta,bc=utilities(design,predictors,pars,np.zeros(len(design['p']),dtype=int),ix)
        logden=np.logaddexp(0.,logsumexp(eta,axis=1))
        logp=eta-logden[:,None]
        # Includes the explicit outside alternative. log1p is stable away from
        # one; use expm1 to preserve the difference when a focal word dominates.
        logcomp=logden[:,None]+np.log(-np.expm1(logp))
        high=eta+.5*bc[:,None]; low=eta-.5*bc[:,None]
        lp_hi=-np.logaddexp(0.,logcomp-high);lp_lo=-np.logaddexp(0.,logcomp-low)
        weights=1/(int(design['P'])*counts[design['p'][ix]])
        logratio+=float(weights@np.mean(lp_hi-lp_lo,axis=1))
        pdiff+=float(weights@np.mean(np.exp(lp_hi)-np.exp(lp_lo),axis=1))
    return dict(mean_log_ratio=logratio,probability_ratio=float(np.exp(logratio)),
                probability_difference_per_1000=1000*pdiff)


def build(design,predictors,y):
    import pymc as pm
    import pytensor.tensor as pt
    y=np.asarray(y,dtype=np.int64);p,g,b=[design[k] for k in ('p','g','b')]
    if len(y)!=len(p) or np.any(y<0) or np.any(y>design['W']): raise ValueError('Invalid choices')
    prev=history(design,y);N=len(y);block=bool(np.any(b));W=int(design['W'])
    with pm.Model() as model:
        c=pm.Data('c',predictors['c']);v=pm.Data('v',predictors['v']);h=pm.Data('h',predictors['h'])
        pars={k:pm.Normal(k,0,sd) for k,sd in {**FIXED,**(BLOCK_FIXED if block else {})}.items()}
        for name,shape in shapes(design).items():
            sigma=pm.HalfNormal('sigma_'+name,SCALES[name])
            z=pm.Normal('z_'+name,0,1,shape=shape)
            if name=='d':
                G,W=shape
                centered_z=(z-z.mean(0)-z.mean(1)[:,None]+z.mean())/np.sqrt((1-1/G)*(1-1/W))
            else:
                centered_z=(z-z.mean())/np.sqrt(1-1/shape[0])
            pars[name]=sigma*centered_z
        inside=pars['alpha']+pars['A'][p]+pars['G'][g]
        bc=pars['beta']+pars['B'][p]+pars['C'][g]
        bv=pars['gamma']+pars['E'][p]+pars['H'][g]
        quad=pt.ones(N)*pars['kappa']
        if block:
            inside=inside+b*(pars['delta']+pars['zeta']*(prev==0))
            bc=bc+b*pars['beta2'];bv=bv+b*pars['gamma2'];quad=quad+b*pars['kappa2']
        eta=-np.log(W)+inside[:,None]+pars['a'][None,:]+pars['d'][g,:]+bc[:,None]*c+bv[:,None]*v+quad[:,None]*h
        if block:
            repeat=np.flatnonzero((b==1)&(prev>0))
            eta=pt.inc_subtensor(eta[repeat,prev[repeat]-1],pars['lambda_repeat'])
        chosen=pt.where(y>0,eta[np.arange(N),np.maximum(y-1,0)],0.)
        normalizer=pt.logaddexp(0.,pt.logsumexp(eta,axis=1))
        pm.Potential('choice_loglik',pt.sum(chosen-normalizer))
    return model


def equal_cut_summary(components):
    """Equal COMPONENT weight even if stored draws differ; no outcome weighting."""
    arrays=[np.asarray(a,dtype=float).ravel() for a in components]
    if len(arrays)!=8 or any(a.size==0 or not np.isfinite(a).all() for a in arrays):
        raise ValueError('Require eight complete finite components')
    vals=np.concatenate(arrays);weights=np.concatenate([np.full(a.size,1/(8*a.size)) for a in arrays])
    order=np.argsort(vals);x=vals[order];cw=np.cumsum(weights[order])
    quant=lambda p: float(x[min(len(x)-1,np.searchsorted(cw,p))])
    means=np.array([a.mean() for a in arrays]);within=float(np.mean([a.var() for a in arrays]))
    between=float(means.var());mean=float(means.mean())
    return dict(mean=mean,sd=np.sqrt(within+between),q05=quant(.05),q25=quant(.25),
        median=quant(.5),q75=quant(.75),q95=quant(.95),p_negative=float(weights@(vals<0)),
        within_component_variance=within,between_component_variance=between,
        component_means=means.tolist(),first_four_mean=float(means[:4].mean()),
        leave_one_component_mean=[float(np.delete(means,i).mean()) for i in range(8)])

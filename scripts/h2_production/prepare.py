"""Freeze measurement components and design-only arrays; no production fit."""
from __future__ import annotations
import json
import time
from collections import Counter
from common import ROOT, PRIVATE, OUT, SPEC, sha, dump, utc, ordinal_scores, environment, plain
import numpy as np
from scipy.stats import truncnorm

VARIANTS = [('revised','shared_269','warriner'), ('original','shared_269','warriner'),
            ('revised','shared_269','anderson'), ('revised','anderson_328','anderson')]


def make_design(records, words, ds):
    rs=[r for r in records if r['category'] != 'no_response']
    participants=sorted({r['participant'] for r in rs}); groups=sorted({r['group'] for r in rs})
    pi={x:i for i,x in enumerate(participants)}; gi={x:i for i,x in enumerate(groups)}
    wi={w:i+1 for i,w in enumerate(words)}
    p=np.array([pi[r['participant']] for r in rs],dtype=np.int64)
    g=np.array([gi[r['group']] for r in rs],dtype=np.int64)
    b=np.array([int(r['block'])-1 if ds=='nicolas' else 0 for r in rs],dtype=np.int64)
    y=np.array([wi.get(r['lemma'],0) if r['category']=='lemma' else 0 for r in rs],dtype=np.int64)
    first=np.full(len(rs),-1,dtype=np.int64)
    if ds=='nicolas':
        lookup={(p[i],g[i]):i for i in np.flatnonzero(b==0)}
        assert len(lookup)==np.sum(b==0)
        for i in np.flatnonzero(b==1): first[i]=lookup[(p[i],g[i])]
    design=dict(p=p,g=g,b=b,first=first,P=np.array(len(participants)),G=np.array(len(groups)),W=np.array(len(words)))
    return design,y,dict(participants=participants,groups=groups)


def load_design(ds,variant=0):
    suffix='-design-anderson328.npz' if variant==3 else '-design.npz'
    with np.load(PRIVATE/(ds+suffix)) as z:
        return {k:z[k] if z[k].ndim else int(z[k]) for k in z.files}


def load_predictors(variant=0, component=0):
    with np.load(PRIVATE/f'predictors-{variant}.npz') as z:
        return {k:z[k][component] for k in ('c','v','h')}


def prepare():
    start=time.perf_counter();PRIVATE.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    freeze=json.loads((ROOT/'results/h2-preparation-20261016/freeze.json').read_text())
    checked={}
    for rel, expected in {**freeze['inputs'],**freeze['outputs']}.items():
        # The global manifest can accumulate unrelated source entries. Raw source bytes,
        # the frozen source subset and all derived inputs are independently pinned.
        if rel=='data/manifests/sources.csv': continue
        actual=sha(ROOT/rel)
        assert actual==expected,rel
        checked[rel]=actual
    frames=json.loads((ROOT/'private/h2-preparation-20261016/frames.json').read_text())
    closure=json.loads((ROOT/'private/h2-preparation-20261016/lexical-closure.json').read_text())
    info={r['word']:r for r in closure};allwords=frames['anderson_328'];primary=frames['shared_269']
    kr='private/koch/study1-validation-20261016/data.json'
    old=json.loads((ROOT/'results/h2-feasibility-20261016/receipt.json').read_text())
    checked[kr]=sha(ROOT/kr);assert checked[kr]==old['inputs'][kr]
    kd=json.loads((ROOT/kr).read_text());ratings=np.bincount(np.asarray(kd['word'])-1,minlength=kd['W'])
    for frame,words in frames.items():
        np.save(PRIVATE/f'rating-counts-{frame}.npy',[ratings[info[w]['koch_word_index_zero_based']] for w in words])
    score_cache={};row_ids={};score_meta={}
    for label,path,seed in [('revised','private/koch/study1-validation-20261016/word-probability-draws.npy',2026101601),
                            ('original','private/koch/study1-20261015/primary/word-probability-draws.npy',2026101602)]:
        q=np.load(ROOT/path,mmap_mode='r');rng=np.random.Generator(np.random.PCG64(seed))
        rows=rng.choice(len(q),size=8,replace=False);row_ids[label]=rows.tolist()
        for frame in ('shared_269','anderson_328'):
            if label=='original' and frame=='anderson_328': continue
            ids=[info[w]['koch_word_index_zero_based'] for w in frames[frame]]
            values=np.empty((len(q),len(ids)))
            max_total_error=0.
            for lo in range(0,len(q),256):
                block=np.asarray(q[lo:lo+256,ids,:],dtype=np.float64)
                max_total_error=max(max_total_error,float(abs(block.sum(-1)-1).max()))
                assert max_total_error < 2e-6 and np.min(block)>=0
                # Float32 storage introduces only rounding; renormalize explicitly.
                block/=block.sum(-1,keepdims=True)
                values[lo:lo+len(block)]=ordinal_scores(block)
            assert np.max(abs(values.mean(1)-.5))<1e-12
            means=values.mean(0);scale=means.std(ddof=0);assert scale>0
            score_cache[(label,frame)]=(values[rows]-.5)/scale
            np.save(PRIVATE/f'ordinal-means-{label}-{frame}.npy',means)
            score_meta[label+'_'+frame]=dict(sd_of_posterior_means=scale,
                category_probability_max_sum_rounding=max_total_error,
                posterior_mean_score_min=means.min(),posterior_mean_score_max=means.max(),
                posterior_mean_c_min=(means.min()-.5)/scale,posterior_mean_c_max=(means.max()-.5)/scale)
    norms={}
    for kind,words,seed,bounds in [('warriner',primary,2026101611,(1,9)),('anderson',allwords,2026101612,(0,6))]:
        means=np.array([info[w]['warriner_valence' if kind=='warriner' else 'anderson_likableness'] for w in words])
        se=np.array([info[w]['warriner_sd']/np.sqrt(info[w]['warriner_n']) if kind=='warriner'
                     else np.sqrt(info[w]['anderson_variance']/100) for w in words])
        rng=np.random.Generator(np.random.PCG64(seed))
        draws=truncnorm.rvs((bounds[0]-means)/se,(bounds[1]-means)/se,loc=means,scale=se,
                            size=(8,len(words)),random_state=rng)
        norms[kind]=(words,means,draws)
    predictor_meta=[]
    for j,(label,frame,kind) in enumerate(VARIANTS):
        words=frames[frame]; nw,means,draws=norms[kind]; inds=[nw.index(w) for w in words]
        base=means[inds];mu=base.mean();sd=base.std(ddof=0);standard=(base-mu)/sd
        hmu=(standard**2).mean();hsd=(standard**2).std(ddof=0);assert hsd>0
        v=(draws[:,inds]-mu)/sd; h=(v**2-hmu)/hsd
        path=PRIVATE/f'predictors-{j}.npz'
        np.savez_compressed(path,c=score_cache[(label,frame)],v=v,h=h)
        predictor_meta.append(dict(index=j,measurement=label,frame=frame,evaluation=kind,words=len(words),
            evaluation_center=mu,evaluation_sd=sd,quadratic_center=hmu,quadratic_sd=hsd,
            archive_sha256=sha(path)))
    structure={};checks=[]
    for ds,rel in [('uwa','private/empirical/uwa_study2/normalized.json'),
                   ('nicolas','private/empirical/nicolas_study2/coded_archive_corrected.json')]:
        records=json.loads((ROOT/rel).read_text())
        design,y,index=make_design(records,primary,ds)
        np.savez_compressed(PRIVATE/(ds+'-design.npz'),**design)
        # Kept separately to verify denominators, never read by the artificial fit.
        np.save(PRIVATE/(ds+'-observed-choices-NOT-FOR-PREFLIGHT.npy'),y)
        dump(PRIVATE/(ds+'-index.json'),index)
        counts=np.bincount(y,minlength=len(primary)+1)
        expected=(1972,348,174) if ds=='uwa' else (14997,3959,69)
        assert (len(y),int(np.sum(y>0)),int(np.sum(counts[1:]==0)))==expected
        assert len(np.unique(design['p']))==design['P'] and len(np.unique(design['g']))==design['G']
        structure[ds]=dict(responses=len(y),participants=design['P'],groups=design['G'],words=len(primary),
            outside=int(counts[0]),inside=int(counts[1:].sum()),zero_words=int(np.sum(counts[1:]==0)),
            first_encounters=int(np.sum(design['b']==0)),second_encounters=int(np.sum(design['b']==1)),
            design_sha256=sha(PRIVATE/(ds+'-design.npz')),
            observed_choices_sha256=sha(PRIVATE/(ds+'-observed-choices-NOT-FOR-PREFLIGHT.npy')))
        broad,by,_=make_design(records,allwords,ds)
        assert all(np.array_equal(broad[k],design[k]) for k in ('p','g','b','first','P','G'))
        assert (int(np.sum(by>0)),int(np.sum(np.bincount(by,minlength=329)[1:]==0))) == ((356,227) if ds=='uwa' else (4153,100))
        np.savez_compressed(PRIVATE/(ds+'-design-anderson328.npz'),**broad)
        np.save(PRIVATE/(ds+'-observed-anderson328-NOT-FOR-PREFLIGHT.npy'),by)
    outputs={str(p.relative_to(ROOT)):sha(p) for p in PRIVATE.iterdir() if p.is_file() and
             (p.name.endswith(('.npz','.npy')) or p.name.endswith('-index.json'))}
    receipt=dict(at=utc(),specification_sha256=sha(SPEC),source_freeze_sha256=sha(ROOT/'results/h2-preparation-20261016/freeze.json'),
        checked_inputs=checked,measurement_rows=row_ids,score_constants=score_meta,predictors=predictor_meta,
        response_structure=structure,outputs=outputs,elapsed_seconds=time.perf_counter()-start,
        choices_used_for_fitting=False,scope='Measurement arithmetic and design preparation only; no production association estimated')
    dump(OUT/'preparation.json',receipt);dump(ROOT/'logs/h2-implementation-20261016-environment.json',environment())
    print(json.dumps(plain(dict(status='prepared',structure=structure,measurement_rows=row_ids))),flush=True)


if __name__=='__main__': prepare()

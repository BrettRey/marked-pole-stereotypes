"""Read-only HF collection and fixed-weight summaries; never submits or fits."""
from __future__ import annotations
import argparse
import json
import os
import subprocess
import time
from pathlib import Path
import numpy as np
from common import ROOT, dump, sha, summary, utc, environment
from empirical import all_jobs, job_info
from remote_batch import ALLOWED
from verify_archive import verify_result, reconciled_register

BASE = ROOT / 'private/h2-empirical-20261016'
PUBLIC = ROOT / 'results/h2-empirical-20261016'
BUCKET = 'hf://buckets/BrettRey/marked-pole-d1c-compute/h2-empirical-20261016/outputs'
PROVIDER_JOB = '6ad287a75ccb47ba0f7b5bda'
KEYS = ('mean_log_ratio', 'probability_ratio', 'probability_difference_per_1000')


def cli(*args):
    env = os.environ.copy()
    env.pop('HF_TOKEN', None)  # Use the already authenticated CLI account.
    result = subprocess.run(['hf', *args], env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return result.stdout


def fetch(name, target, expected=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if expected and target.exists() and sha(target) == expected:
        return
    temporary = target.with_name(target.name + '.download')
    cli('buckets', 'cp', BUCKET + '/' + name, str(temporary))
    if expected and sha(temporary) != expected:
        raise ValueError('Downloaded checksum mismatch: ' + name)
    temporary.replace(target)


def effect_summary(values, key):
    result = summary(values)
    if key == 'probability_ratio':
        result.pop('p_negative')
        result['p_below_one'] = float(np.mean(values < 1))
    return result


def mixture(values, key, mcse=None):
    """Eight equally weighted empirical distributions, not eight MCMC chains."""
    values = np.asarray(values, dtype=float)
    if values.shape != (8, 4, 1000) or not np.isfinite(values).all():
        raise ValueError('A cut summary requires all eight complete 4 x 1000 components')
    means = values.mean(axis=(1, 2))
    within = float(values.var(axis=(1, 2)).mean())
    between = float(means.var())
    total = float(values.var())
    if not np.isclose(total, within + between, rtol=1e-12, atol=1e-15):
        raise ValueError('Variance decomposition failed')
    flat = values.ravel()
    null = 1 if key == 'probability_ratio' else 0
    grid = np.linspace(min(null, flat.min()), max(null, flat.max()), 201)
    result = dict(all_eight=effect_summary(flat, key),
                  first_four=effect_summary(values[:4].ravel(), key),
                  component_means=means,
                  leave_one_component_out=[dict(omitted=i, **effect_summary(np.delete(values, i, axis=0).ravel(), key)) for i in range(8)],
                  variance=dict(within=within, between=between, total=total,
                                between_fraction=between / total if total else None),
                  exceedance=dict(grid=grid, probability_greater=np.mean(flat[:, None] > grid, axis=0)))
    result['first_four_minus_all_eight_mean'] = result['first_four']['mean'] - result['all_eight']['mean']
    if mcse is not None:
        errors = np.asarray(mcse, dtype=float)
        result['within_component_mcse_of_mixture_mean'] = float(np.sqrt(np.sum(errors**2))/8) if np.isfinite(errors).all() else None
        result['mcse_scope'] = 'Conditional on these eight fixed components; does not measure integration error.'
    return result


def predictive_mixture(replicated, observed):
    """Match each replication to its component's observed predictor-based metric."""
    if len(replicated) != 8 or any(len(rows) != 200 for rows in replicated):
        raise ValueError('Predictive mixture requires 8 x 200 replications')
    out = []
    for key in observed[0]:
        values = np.array([[row[key] for row in rows] for rows in replicated], dtype=float)
        obs = np.array([row[key] for row in observed], dtype=float)
        valid = np.isfinite(values)
        row = dict(check=key, n_replications=1600, n_defined=int(valid.sum()),
                   defined_by_component=valid.sum(axis=1), observed_by_component=obs,
                   predictive=None, discrepancy=None)
        # Do not silently change component weights by dropping undefined draws.
        if valid.all():
            row['predictive'] = summary(values.ravel())
        if valid.all() and np.isfinite(obs).all():
            residual = values - obs[:, None]
            row['discrepancy'] = summary(residual.ravel())
            row['fraction_rep_ge_observed'] = float(np.mean(residual >= 0))
        out.append(row)
    return out


def component_plots(folder, destination):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    wanted = ['alpha', 'beta', 'gamma', 'sigma_a', 'sigma_d', 'lambda_repeat']
    with np.load(folder / 'posterior.npz', allow_pickle=False) as archive:
        keys = [key for key in wanted if 'post_' + key in archive.files]
        fig, axes = plt.subplots(3, 2, figsize=(11, 8))
        for ax, key in zip(axes.flat, keys):
            for chain, draws in enumerate(archive['post_' + key]):
                ax.plot(draws, lw=.45, alpha=.7, label=str(chain+1))
            ax.set(title=key, xlabel='Retained draw')
        for ax in list(axes.flat)[len(keys):]:
            ax.axis('off')
        axes.flat[0].legend(title='Chain', ncol=4, fontsize=7)
        fig.suptitle(folder.name + ': conditional empirical chains')
        fig.tight_layout(); fig.savefig(destination / 'traces.png', dpi=150); plt.close(fig)
    with np.load(folder / 'contrast-draws.npz', allow_pickle=False) as archive:
        fig, ax = plt.subplots(figsize=(9, 3))
        for chain, draws in enumerate(archive['mean_log_ratio']):
            ax.plot(draws, lw=.5, alpha=.7, label=str(chain+1))
        ax.set(title=folder.name + ': mean log probability ratio', xlabel='Retained draw')
        ax.legend(title='Chain', ncol=4); fig.tight_layout()
        fig.savefig(destination / 'contrast-traces.png', dpi=150); plt.close(fig)


def cut_plots(result, destination, title):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, key in zip(axes, KEYS):
        row = result['contrasts'][key]
        ax.plot(row['exceedance']['grid'], row['exceedance']['probability_greater'])
        ax.axvline(1 if key == 'probability_ratio' else 0, color='grey', lw=.7)
        ax.set(title=key.replace('_', ' '), ylabel='Posterior probability above value')
        ax.grid(alpha=.2)
    fig.suptitle(title + ': equal-weight eight-component cut'); fig.tight_layout()
    fig.savefig(destination / 'exceedance.png', dpi=150); plt.close(fig)
    for mode, rows in result['predictive'].items():
        if not rows:
            continue
        fig, axes = plt.subplots((len(rows)+3)//4, 4, figsize=(14, 2*((len(rows)+3)//4)))
        for ax, row in zip(axes.flat, rows):
            if row['predictive']:
                pred = row['predictive']
                ax.plot([pred['q05'], pred['q95']], [0, 0], lw=3, color='#356b9a')
                ax.plot(pred['median'], 0, 'o', color='#356b9a')
            obs = np.asarray(row['observed_by_component'], dtype=float)
            for value in obs[np.isfinite(obs)]:
                ax.axvline(value, color='#bc503e', lw=.8, alpha=.5)
            ax.set(title=row['check'].replace('_', ' '), yticks=[])
            ax.tick_params(labelsize=7); ax.title.set_fontsize(8)
        for ax in list(axes.flat)[len(rows):]:
            ax.axis('off')
        fig.suptitle(title + ': ' + mode.replace('_', ' ') + '\nBlue: predictive median and central 90%; red: observed values by measurement component')
        fig.tight_layout(); fig.savefig(destination / (mode + '-predictive.png'), dpi=150); plt.close(fig)


def aggregate(register):
    availability = {}
    for dataset in ('uwa', 'nicolas'):
        for specification in range(4):
            label = f'{dataset}-s{specification}'
            jobs = [f'{label}-c{i}' for i in range(8)]
            ready = all((BASE/'collected'/job/'collection.json').exists() and register['jobs'][job]['state']=='complete' for job in jobs)
            availability[label] = dict(state='available' if ready else 'incomplete',
                                       missing=[job for job in jobs if register['jobs'][job]['state']!='complete' or not (BASE/'collected'/job/'collection.json').exists()])
            if not ready:
                continue
            target = PUBLIC / label; target.mkdir(parents=True, exist_ok=True)
            hashes = {job: register['jobs'][job]['manifest_sha256'] for job in jobs}
            if (target/'cut.json').exists() and json.loads((target/'cut.json').read_text())['component_manifests']==hashes:
                continue
            components = [BASE/'collected'/job for job in jobs]
            draws = {key: [] for key in KEYS}; details = []; predictions = []; observations = []
            for folder in components:
                with np.load(folder/'contrast-draws.npz', allow_pickle=False) as archive:
                    for key in KEYS:
                        draws[key].append(archive[key])
                details.append(json.loads((folder/'contrasts.json').read_text()))
                predictions.append(json.loads((folder/'predictive-replications.json').read_text()))
                observations.append(json.loads((folder/'predictive.json').read_text())['observed'])
            effects = {key: mixture(np.array(draws[key]), key, [item['contrasts'][key]['mcse_mean'] for item in details]) for key in KEYS}
            predictive = {'joint': predictive_mixture([item['joint'] for item in predictions], observations),
                          'conditional_history': predictive_mixture([item['conditional_history'] for item in predictions], observations) if dataset=='nicolas' else []}
            result = dict(at=utc(), dataset=dataset, specification=specification, weights=[.125]*8,
                          component_manifests=hashes, contrasts=effects, predictive=predictive,
                          component_summaries=details, diagnostic_scope='R-hat and ESS remain conditional-component diagnostics; no pooled R-hat.',
                          scientific_scope='Restricted lexical-frame association; eight components are a coarse approximation, not established measurement validity.')
            # Write the completion object last so an interrupted plot can be regenerated.
            cut_plots(result, target, label)
            dump(target/'cut.json', result)
    return availability


def collect_once():
    BASE.mkdir(parents=True, exist_ok=True); PUBLIC.mkdir(parents=True, exist_ok=True)
    provider = json.loads(cli('jobs', 'inspect', PROVIDER_JOB, '--format', 'json'))
    if isinstance(provider, list):
        if len(provider)!=1:
            raise ValueError('Expected one provider job')
        provider=provider[0]
    if provider['id']!=PROVIDER_JOB:
        raise ValueError('Provider returned a different job')
    fetch('register.json', BASE/'observed-register.json')
    register = json.loads((BASE/'observed-register.json').read_text())
    if PROVIDER_JOB == '6ad287a75ccb47ba0f7b5bda':
        register = reconciled_register(BASE/'observed-register.json',
            ROOT/'results/h2-recovery-20261016/original-reconciliation.json')
    if set(register['jobs']) != set(all_jobs()):
        raise ValueError('Unexpected assignment set')
    meta = json.loads((BASE/'inputs/bundle.json').read_text())
    collected = []; running = {}; failures = {}
    stage=provider['status']['stage']
    for job, row in register['jobs'].items():
        job_info(job)
        if row['state']=='running':
            if 'orchestration_sha256' in register:
                from recovery import process_evidence
                running[job]=dict(evidence=process_evidence(row, provider_stage=stage),
                                  heartbeat=row.get('heartbeat'), attempt=row['attempt'],
                                  owner=row['owner'], started_at=row['started_at'])
            elif row['owner'].startswith('hf-'):
                try:
                    path=BASE/'progress'/job/'progress.json'
                    fetch(job+'/progress.json', path)
                    running[job]=json.loads(path.read_text())
                except RuntimeError:
                    running[job]={'state':'No sampler progress file available yet'}
            else:
                running[job]={'state':'Claim recorded; cloud progress is exported with terminal result', 'started_at':row['started_at']}
        if row['state'] not in ('complete','failed'):
            continue
        if 'manifest_sha256' not in row:
            failures[job]=row
            continue
        folder=BASE/'collected'/job
        if (folder/'collection.json').exists():
            receipt=json.loads((folder/'collection.json').read_text())
            if receipt['manifest_sha256']!=row['manifest_sha256']:
                raise ValueError('A previously collected result changed')
            collected.append(job)
            if row['state']=='failed':
                failures[job]=row
            continue
        fetch(job+'/manifest.json', folder/'manifest.json', row['manifest_sha256'])
        manifest=json.loads((folder/'manifest.json').read_text())
        if manifest['job']!=job or set(manifest['files'])-ALLOWED:
            raise ValueError('Unsafe or mismatched result manifest')
        for name, item in manifest['files'].items():
            fetch(job+'/'+name, folder/name, item['sha256'])
        fit=verify_result(folder, meta)
        if fit['owner']!=row['owner'] or fit['state']!=row['state'] or fit['bundle_sha256']!=sha(BASE/'inputs/bundle.json'):
            raise ValueError('Registry or input bundle mismatch')
        public=PUBLIC/'components'/job; public.mkdir(parents=True, exist_ok=True)
        if not (folder/'collection.json').exists():
            for name in ('fit.json','diagnostics.json','contrasts.json','predictive.json','summary-receipt.json','manifest.json'):
                if (folder/name).exists():
                    dump(public/name, json.loads((folder/name).read_text()))
            if fit['state']=='complete':
                component_plots(folder, public)
            dump(folder/'collection.json', dict(at=utc(), manifest_sha256=row['manifest_sha256'], verified=True))
        collected.append(job)
        if fit['state']=='failed':
            failures[job]=dict(error=fit.get('error'), owner=fit['owner'])
    cuts=aggregate(register)
    counts={state:sum(row['state']==state for row in register['jobs'].values()) for state in ('unassigned','running','complete','failed')}
    terminal=stage!='RUNNING' and stage not in ('PENDING','STARTING')
    terminal=terminal or (counts['running']==0 and (counts['unassigned']==0 or register['phase'] in ('blocked','resource_boundary')))
    state=dict(at=utc(), provider_job=PROVIDER_JOB, provider_stage=stage, phase=register['phase'], counts=counts,
               running=running, failures=failures, collected=collected, cuts=cuts, terminal=terminal,
               collector_source_sha256=sha(Path(__file__)), input_bundle_sha256=sha(BASE/'inputs/bundle.json'),
               verification_reconciliation_sha256=register.get('verification_reconciliation_sha256'),
               maximum_hf_usd=12, automatic_fit_retries=False,
               initial_timings=register.get('initial_timings'),
               attempt_history={job:{k:row[k] for k in ('attempt','previous_attempt','imported','original_archive') if k in row}
                                for job,row in register['jobs'].items()} if 'orchestration_sha256' in register else None,
               browser_required=False)
    dump(PUBLIC/'status.json', state)
    with (PUBLIC/'collection-events.jsonl').open('a') as stream:
        stream.write(json.dumps(dict(at=state['at'], counts=counts, provider_stage=stage, terminal=terminal))+'\n')
    print(json.dumps(dict(at=state['at'], counts=counts, provider_stage=stage, terminal=terminal)), flush=True)
    return terminal


def main():
    global BASE, PUBLIC, BUCKET, PROVIDER_JOB
    import fcntl
    parser=argparse.ArgumentParser(); parser.add_argument('--watch', action='store_true')
    parser.add_argument('--interval', type=int, default=300)
    parser.add_argument('--recovery-config', type=Path)
    args=parser.parse_args()
    if args.recovery_config:
        config=json.loads(args.recovery_config.read_text())
        BASE=ROOT/'private/h2-recovery-20261016'
        PUBLIC=ROOT/'results/h2-recovery-20261016'
        BUCKET='hf://buckets/BrettRey/marked-pole-d1c-compute/h2-recovery-20261016/outputs'
        PROVIDER_JOB=config['job_id']
        if not (BASE/'inputs/bundle.json').exists():
            raise ValueError('Recovery collector requires the original verified input bundle')
    if args.interval<30:
        raise ValueError('Use at least 30 seconds between polls')
    BASE.mkdir(parents=True, exist_ok=True)
    lock=(BASE/'collector.lock').open('w')
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    dump(PUBLIC/'collector-environment.json', environment())
    while True:
        try:
            terminal=collect_once()
        except Exception as exc:
            with (PUBLIC/'collection-errors.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(at=utc(), error=repr(exc), retry_scope='No automatic collection or model retry; inspect first'))+'\n')
            raise
        if terminal or not args.watch:
            return
        time.sleep(args.interval)


if __name__=='__main__':
    main()

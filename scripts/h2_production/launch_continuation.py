"""One bounded controller replacement; no repeated scientific fits or purchases."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import time
from datetime import datetime, timezone
from common import ROOT, dump, sha, utc
from launch_recovery import cli, validate_lifecycle
from launch_remote import IMAGE, BUCKET

BATCH = 'h2-continuation-20261017'
BASE = ROOT/'private'/BATCH
RECEIPT = ROOT/'logs'/f'{BATCH}-hf-launch.json'
PAST_JOBS = ('6ad287a75ccb47ba0f7b5bda', '6ad34bb85ccb47ba0f7ba4ec')
BOOTSTRAP = '''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
python -c 'import platform; assert platform.python_version() == "3.14.8"'
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-h2.txt
exec .venv/bin/python -u scripts/h2_production/continue_verified.py --inputs /bucket/h2-empirical-20261016/inputs --outputs /bucket/h2-continuation-20261017/outputs --original /bucket/h2-recovery-20261016/outputs --proof /bucket/h2-continuation-20261017/uwa-summary-reconciliation.json --proof-sha "$2" --secrets-file /bucket/h2-continuation-20261017/capabilities.json --deadline "$3" --port 8000
'''


def budget(providers, available, now, old_deadline):
    if {p['id'] for p in providers} != set(PAST_JOBS) or len(providers) != 2:
        raise ValueError('Both prior provider receipts are required')
    if any(p['status']['stage'] in ('RUNNING', 'PENDING', 'STARTING') for p in providers):
        raise ValueError('Stop the idle old controller before any new provider launch')
    costs = {p['id']: (math.ceil(p['durations']['total_secs']/60)+1)/60*.04 for p in providers}
    past = sum(costs.values())
    allowed = min(12-past, available)
    timeout = math.floor(min(old_deadline-now, allowed/.04*3600))-120
    if timeout < 600:
        raise ValueError('Insufficient original resource allowance')
    return costs, timeout, now+timeout-300


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', required=True)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if args.execute and RECEIPT.exists():
        raise RuntimeError('Continuation submission already recorded; inspect, never resubmit blindly')
    if not re.fullmatch('[0-9a-f]{40}', args.source):
        raise ValueError('Full committed source required')
    inputs = ROOT/'private/h2-empirical-20261016/inputs'
    meta = json.loads((inputs/'bundle.json').read_text())
    for path, digest in meta['source_hashes'].items():
        if hashlib.sha256(subprocess.check_output(['git', 'show', args.source+':'+path])).hexdigest() != digest:
            raise ValueError('Frozen source changed: '+path)
    for name in ('continue_verified.py', 'launch_continuation.py', 'recovery.py', 'collect.py', 'verify_archive.py'):
        path = 'scripts/h2_production/'+name
        if hashlib.sha256(subprocess.check_output(['git', 'show', args.source+':'+path])).hexdigest() != sha(ROOT/path):
            raise ValueError('Unpublished operational source: '+path)
    account = json.loads((BASE/'account-check.json').read_text())
    now = time.time()
    if now-datetime.fromisoformat(account['checked_at']).timestamp() > 3600 or account['automatic_recharge'] is not False:
        raise ValueError('Fresh existing-credit check required; no recharge')
    lifecycle = json.loads((ROOT/'results/h2-recovery-20261016/lifecycle.json').read_text())
    validate_lifecycle(lifecycle, 'mixed')
    providers = []
    old = json.loads((ROOT/'logs/h2-recovery-20261016-hf-launch.json').read_text())
    for job in PAST_JOBS:
        value = json.loads(cli('jobs', 'inspect', job, '--format', 'json'))
        provider = value[0] if isinstance(value, list) else value
        if not provider.get('durations'):
            if job == PAST_JOBS[0]:
                seconds = old['original_billable_hours_upper_bound']*3600
                basis = 'Previously recorded original-host upper bound, rounded upward again'
            else:
                seconds = now-datetime.fromisoformat(provider['created_at']).timestamp()
                basis = 'Creation through current independently observed terminal status; upper bound'
            provider['durations'] = dict(total_secs=seconds, basis=basis)
        providers.append(provider)
    costs, timeout, deadline = budget(providers, account['available_hf_usd'], now,
                                    datetime.fromisoformat(old['process_deadline']).timestamp())
    proof = ROOT/'results/h2-recovery-20261016/uwa-summary-reconciliation.json'
    record = dict(at=utc(), batch_id=BATCH, source=args.source, mode='mixed',
        previous_providers=providers, past_cost_upper_bounds_usd=costs, timeout_seconds=timeout,
        process_deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat(),
        hourly_hf_usd=.04, maximum_hf_usd=12,
        total_hf_cost_usd_upper_bound=sum(costs.values())+timeout/3600*.04,
        automatic_provider_attempts=1, automatic_fit_retries=False, imported_complete=5, unstarted_to_run=59,
        input_bundle_sha256=sha(inputs/'bundle.json'), reconciliation_sha256=sha(proof))
    # Provider receipts contain account-specific environment/secrets; retain only operational fields publicly.
    record['previous_providers'] = [{k:p[k] for k in ('id', 'status', 'durations')} for p in providers]
    if not args.execute:
        print(json.dumps(dict(state='validated_preview', **record), indent=2))
        return
    caps = json.loads((BASE/'capabilities.json').read_text())
    if set(caps) != {'claude-1'} or len(caps['claude-1']) < 40:
        raise ValueError('Missing restricted capability')
    cli('buckets', 'cp', str(BASE/'capabilities.json'), BUCKET+'/'+BATCH+'/capabilities.json')
    cli('buckets', 'cp', str(proof), BUCKET+'/'+BATCH+'/uwa-summary-reconciliation.json')
    cmd = ['hf', 'jobs', 'run', '--format', 'json', '--detach', '--flavor', 'cpu-upgrade',
           '--timeout', str(timeout)+'s', '--attempts', '1', '--name', BATCH,
           '--expose-public', '8000', '--volume', BUCKET+':/bucket:rw', '--',
           IMAGE, 'bash', '-lc', BOOTSTRAP, BATCH, args.source, sha(proof), str(deadline)]
    record['state'] = 'submitting'
    dump(RECEIPT, record)
    env = os.environ.copy(); env.pop('HF_TOKEN', None)
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    record.update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    record['state'] = 'accepted' if result.returncode == 0 else 'requires_inspection'
    if result.returncode == 0:
        record['job_id'] = json.loads(result.stdout)['id']
    dump(RECEIPT, record)
    print(json.dumps(record, indent=2))
    raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()

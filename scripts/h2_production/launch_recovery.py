"""Guarded launch of the approved H2 recovery; never purchases credit or retries."""
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
from pathlib import Path
from common import ROOT, dump, sha, utc
from verify_archive import verify_result, reconciled_register
from launch_remote import IMAGE, BUCKET

ORIGINAL_JOB='6ad287a75ccb47ba0f7b5bda'
BASE=ROOT/'private/h2-recovery-20261016'
ORIGINAL=ROOT/'private/h2-empirical-20261016'
RECEIPT=ROOT/'logs/h2-recovery-20261016-hf-launch.json'
ORIGINAL_DEADLINE=datetime.fromisoformat('2026-10-16T20:23:10.272000+00:00').timestamp()+300*3600
PROBE_SHA='541505816b0a46eb18f988ab83bd713afa29469e73a1be636a2b3b75719c2120'
BOOTSTRAP='''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
python -c 'import platform; assert platform.python_version() == "3.14.8"'
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-h2.txt
exec .venv/bin/python -u scripts/h2_production/recovery.py serve --inputs /bucket/h2-empirical-20261016/inputs --outputs /bucket/h2-recovery-20261016/outputs --original /bucket/h2-empirical-20261016/outputs --secrets-file /bucket/h2-recovery-20261016/capabilities.json --mode "$2" --deadline "$3" --port 8000 --reconciliation /bucket/h2-recovery-20261016/original-reconciliation.json
'''


def cli(*args):
    env=os.environ.copy();env.pop('HF_TOKEN',None)
    result=subprocess.run(['hf',*args],capture_output=True,text=True,env=env)
    if result.returncode:
        raise RuntimeError(result.stderr[-1500:])
    return result.stdout


def validate_lifecycle(proof, mode):
    if mode=='mixed':
        receipt=proof['receipt']
        if (proof['state']!='passed' or proof['observed_task_exit_status']!=0 or
                receipt['state']!='complete' or receipt['exit_status']!=0 or
                receipt['elapsed_seconds']<7500 or receipt['duration_seconds']!=7500 or
                receipt['script_sha256']!=PROBE_SHA or receipt['empirical_fits']!=0 or
                receipt['research_data_access'] is not False):
            raise ValueError('Claude lifecycle completion is not verified')
        events=proof['last_heartbeats']
        if len(events)<3 or max(e['elapsed_seconds'] for e in events)<7500:
            raise ValueError('Missing observed heartbeat beyond the failure boundary')
    elif proof['state'] not in ('failed','configuration_unavailable'):
        raise ValueError('HF fallback requires recorded Claude configuration/check failure')


def resource_budget(provider, available_credit, now):
    if provider['status']['stage'] in ('RUNNING','PENDING','STARTING'):
        raise ValueError('Original HF provider is still active; do not overlap recovery charges')
    if provider['id']!=ORIGINAL_JOB:
        raise ValueError('Wrong original provider receipt')
    # Include scheduling time and round upward, conservatively, plus one billing minute.
    old_hours=(math.ceil(provider['durations']['total_secs']/60)+1)/60
    old_cost=old_hours*.04
    allowed=min(12-old_cost,available_credit)
    if allowed<=0:
        raise ValueError('No authorized existing HF credit remains')
    return old_hours,old_cost,allowed,max(0,ORIGINAL_DEADLINE-now)


def prepare(source, mode, account, proof, provider, now):
    if not re.fullmatch('[0-9a-f]{40}',source):
        raise ValueError('Full source commit required')
    validate_lifecycle(proof,mode)
    if now-datetime.fromisoformat(account['checked_at']).timestamp()>3600:
        raise ValueError('Recheck the existing HF balance before launch')
    if account['automatic_recharge'] is not False:
        raise ValueError('Automatic recharge must remain disabled')
    meta=json.loads((ORIGINAL/'inputs/bundle.json').read_text())
    for name,digest in meta['source_hashes'].items():
        content=subprocess.check_output(['git','show',source+':'+name],cwd=ROOT)
        if hashlib.sha256(content).hexdigest()!=digest:
            raise ValueError('Frozen execution source changed: '+name)
    for name in ('recovery.py','launch_recovery.py','collect.py','verify_archive.py'):
        path='scripts/h2_production/'+name
        if hashlib.sha256(subprocess.check_output(['git','show',source+':'+path],cwd=ROOT)).hexdigest()!=sha(ROOT/path):
            raise ValueError('Recovery source is not the published revision: '+name)
    original_register=reconciled_register(ORIGINAL/'observed-register.json',
        ROOT/'results/h2-recovery-20261016/original-reconciliation.json')
    for job,state in (('nicolas-s0-c0','failed'),('nicolas-s0-c1','complete')):
        folder=ORIGINAL/'collected'/job
        fit=verify_result(folder,meta)
        if (fit['state']!=state or fit['bundle_sha256']!=sha(ORIGINAL/'inputs/bundle.json') or
                sha(folder/'manifest.json')!=original_register['jobs'][job]['manifest_sha256']):
            raise ValueError('Original attempt not verified: '+job)
    old_hours,old_cost,allowed,remaining=resource_budget(provider,account['available_hf_usd'],now)
    rate=.04 if mode=='mixed' else .03
    timeout=math.floor(min(remaining,allowed/rate*3600))-120
    if timeout<600:
        raise ValueError('Insufficient approved runtime for recovery')
    # Leave five minutes for graceful process termination and final failure receipts.
    deadline=now+timeout-300
    cmd=['hf','jobs','run','--format','json','--detach','--flavor','cpu-upgrade',
         '--timeout',str(timeout)+'s','--attempts','1','--name','h2-recovery-20261016',
         '--volume',BUCKET+':/bucket:rw']
    if mode=='mixed':
        cmd+=['--expose-public','8000']
    cmd+=['--',IMAGE,'bash','-lc',BOOTSTRAP,'h2-recovery',source,mode,str(deadline)]
    record=dict(at=utc(),source=source,mode=mode,original_provider_job=ORIGINAL_JOB,
        original_billable_hours_upper_bound=old_hours,original_cost_usd_upper_bound=old_cost,
        timeout_seconds=timeout,process_deadline=datetime.fromtimestamp(deadline,timezone.utc).isoformat(),
        hourly_hf_usd=rate,recovery_cost_usd_upper_bound=timeout/3600*rate,
        total_hf_cost_usd_upper_bound=old_cost+timeout/3600*rate,maximum_hf_usd=12,
        automatic_provider_attempts=1,automatic_fit_retries=False,authorized_replacement='nicolas-s0-c0',
        input_bundle_sha256=sha(ORIGINAL/'inputs/bundle.json'),
        lifecycle_proof_sha256=hashlib.sha256(json.dumps(proof,sort_keys=True).encode()).hexdigest())
    return cmd,record


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--mode',choices=['mixed','hf'],required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.execute and RECEIPT.exists():
        raise RuntimeError('Recovery submission already recorded; reconcile, never resubmit blindly')
    account=json.loads((BASE/'account-check.json').read_text())
    proof=json.loads((ROOT/'results/h2-recovery-20261016/lifecycle.json').read_text())
    providers=json.loads(cli('jobs','inspect',ORIGINAL_JOB,'--format','json'))
    if not isinstance(providers,list) or len(providers)!=1:
        raise ValueError('Unexpected provider response')
    cmd,record=prepare(args.source,args.mode,account,proof,providers[0],time.time())
    if not args.execute:
        print(json.dumps(dict(state='validated_preview',**record),indent=2))
        return
    capabilities=json.loads((BASE/'capabilities.json').read_text())
    if args.mode=='mixed' and (set(capabilities)!={'claude-1'} or len(capabilities['claude-1'])<40):
        raise ValueError('Missing restricted recovery capability')
    cli('buckets','cp',str(BASE/'capabilities.json'),BUCKET+'/h2-recovery-20261016/capabilities.json')
    cli('buckets','cp',str(ROOT/'results/h2-recovery-20261016/original-reconciliation.json'),
        BUCKET+'/h2-recovery-20261016/original-reconciliation.json')
    record['state']='submitting'
    dump(RECEIPT,record)
    env=os.environ.copy();env.pop('HF_TOKEN',None)
    result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    record.update(returncode=result.returncode,stdout=result.stdout,stderr=result.stderr)
    if result.returncode==0:
        record.update(state='accepted',job_id=json.loads(result.stdout)['id'])
    else:
        record['state']='requires_inspection'
    dump(RECEIPT,record)
    print(json.dumps(record,indent=2))
    raise SystemExit(result.returncode)


if __name__=='__main__':
    main()

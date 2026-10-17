"""Submit one HF host for the authorized H2 batch; never buy credit or retry."""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
IMAGE='python@sha256:7ee7e4d4fb42c3ad45b8fdc473b64ec69c3cf6e80ae5d52f6fa55f77fac29027'
BUCKET='hf://buckets/BrettRey/marked-pole-d1c-compute'
BOOTSTRAP='''set -eu
git clone --quiet https://github.com/BrettRey/marked-pole-stereotypes.git /work
cd /work
git checkout --quiet "$1"
python -m venv .venv
.venv/bin/python -m pip install --disable-pip-version-check -r requirements-h2.txt
exec .venv/bin/python -u scripts/h2_production/remote_batch.py serve --inputs /bucket/h2-empirical-20261016/inputs --outputs /bucket/h2-empirical-20261016/outputs --secrets-file /bucket/h2-empirical-20261016/capabilities.json --port 8000
'''
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not re.fullmatch('[0-9a-f]{40}',a.source):raise ValueError('Full source commit required')
 receipt=ROOT/'logs/h2-empirical-20261016-hf-launch.json'
 if a.execute and receipt.exists():raise RuntimeError('Submission already recorded; reconcile before any new submission')
 bundle=json.loads((ROOT/'private/h2-empirical-20261016/inputs/bundle.json').read_text())
 for path,digest in bundle['source_hashes'].items():
  content=subprocess.check_output(['git','show',a.source+':'+path],cwd=ROOT)
  if hashlib.sha256(content).hexdigest()!=digest:raise ValueError('Published source mismatch: '+path)
 cmd=['hf','jobs','run','--format','json','--detach','--flavor','cpu-upgrade','--timeout','300h',
      '--attempts','1','--name','h2-empirical-20261016','--expose-public','8000','--volume',BUCKET+':/bucket:rw']
 if not a.execute:cmd.append('--dry-run')
 cmd += ['--',IMAGE,'bash','-lc',BOOTSTRAP,'h2-job',a.source]
 env=os.environ.copy();env.pop('HF_TOKEN',None)
 record=dict(state='submitting' if a.execute else 'preview',at=datetime.now(timezone.utc).isoformat(),source=a.source,
             timeout_hours=300,hourly_hardware_usd=.03,hourly_endpoint_usd=.01,maximum_hf_usd=12,
             existing_credit_only=True,automatic_recharge=False,automatic_attempts=1,
             input_bundle_sha256=hashlib.sha256((ROOT/'private/h2-empirical-20261016/inputs/bundle.json').read_bytes()).hexdigest())
 if a.execute:receipt.write_text(json.dumps(record,indent=2)+'\n')
 r=subprocess.run(cmd,cwd=ROOT,env=env,capture_output=True,text=True)
 record.update(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
 if a.execute:
  record['state']='accepted' if r.returncode==0 else 'requires_inspection'
  if r.returncode==0:
   job=json.loads(r.stdout);record['job_id']=job['id']
  receipt.write_text(json.dumps(record,indent=2)+'\n')
 print(r.stdout,end='')
 if r.stderr:print(r.stderr,end='')
 raise SystemExit(r.returncode)
if __name__=='__main__':main()

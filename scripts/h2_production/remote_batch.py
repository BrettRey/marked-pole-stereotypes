"""Private transfer, atomic assignment and bounded workers for the 64 H2 fits."""
from __future__ import annotations
import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from common import ROOT,dump,sha,utc
from empirical import all_jobs,job_info,check_bundle

CHUNK=8*1024*1024
MAX_FILE=1536*1024*1024
ALLOWED={'fit.json','progress.json','posterior.npz','dimensions.json','diagnostics.json','contrasts.json',
         'contrast-draws.npz','predictive.json','predictive-replications.json','summary-receipt.json'}
INITIAL={'claude-1':'nicolas-s0-c0','hf-1':'nicolas-s0-c1'}


def verify_result(folder,meta):
    import numpy as np
    manifest=json.loads((folder/'manifest.json').read_text());job_info(manifest['job'])
    for name,row in manifest['files'].items():
        if name not in ALLOWED:raise ValueError('Unapproved output filename')
        p=folder/name
        if p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise ValueError('Output integrity mismatch: '+name)
    fit=json.loads((folder/'fit.json').read_text())
    if fit['job']!=job_info(manifest['job']) or fit['source_hashes']!=meta['source_hashes']:raise ValueError('Wrong fit/source')
    if fit['state']!=manifest['state'] or fit['state'] not in ('complete','failed'):raise ValueError('Not a terminal fit')
    if fit['state']=='complete':
        for name in ALLOWED-{'progress.json'}:
            if name not in manifest['files']:raise ValueError('Missing completed output: '+name)
        receipt=json.loads((folder/'summary-receipt.json').read_text())
        if receipt['contrast_draws']!=4000 or receipt['joint_replications']!=200:raise ValueError('Wrong summary budget')
        with np.load(folder/'contrast-draws.npz',allow_pickle=False) as z:
            for k in ('mean_log_ratio','probability_ratio','probability_difference_per_1000'):
                if z[k].shape!=(4,1000) or not np.isfinite(z[k]).all():raise ValueError('Invalid contrast draws')
            if not np.allclose(z['probability_ratio'],np.exp(z['mean_log_ratio']),rtol=1e-12):raise ValueError('Ratio mismatch')
        import zipfile
        with zipfile.ZipFile(folder/'posterior.npz') as archive:
            for name in archive.namelist():
                with archive.open(name) as f:
                    ver=np.lib.format.read_magic(f)
                    shape,_,dtype=np.lib.format._read_array_header(f,ver)
                    if shape[:2]!=(4,1000) or dtype.hasobject:raise ValueError('Invalid posterior archive header')
    return fit


class Registry:
    def __init__(self,path,meta):
        self.path=path;self.meta=meta;self.lock=threading.RLock()
        if path.exists():raise RuntimeError('Batch register already exists; inspect, never restart blindly')
        self.data=dict(started_at=utc(),phase='initial',jobs={j:dict(state='unassigned',owner=None) for j in all_jobs()})
        self.save()
    def save(self):
        self.data['updated_at']=utc();dump(self.path,self.data)
    def claim(self,owner):
        if owner not in ('hf-1','hf-2','claude-1','claude-2'):raise ValueError('Unknown worker')
        with self.lock:
            active=[j for j,r in self.data['jobs'].items() if r['owner']==owner and r['state']=='running']
            if active:return dict(action='already_running',job=active[0])
            if self.data['phase']=='initial':
                j=INITIAL.get(owner)
                if j is None or self.data['jobs'][j]['state']!='unassigned':return dict(action='wait')
            elif self.data['phase']=='blocked':return dict(action='stop',reason='Initial execution/integrity failure')
            else:
                j=next((j for j,r in self.data['jobs'].items() if r['state']=='unassigned'),None)
                if j is None:return dict(action='stop',reason='No unassigned jobs')
            self.data['jobs'][j]=dict(state='running',owner=owner,started_at=utc());self.save()
            return dict(action='fit',job=j)
    def owner(self,job,owner):
        job_info(job)
        with self.lock:
            row=self.data['jobs'][job]
            if row['owner']!=owner or row['state']!='running':raise ValueError('Worker does not own this active job')
    def finish(self,job,owner,folder):
        with self.lock:
            row=self.data['jobs'][job]
            if row['owner']==owner and row['state'] in ('complete','failed'):
                if sha(folder/'manifest.json')!=row['manifest_sha256']:raise ValueError('Changed completed result')
                return
            self.owner(job,owner)
            fit=verify_result(folder,self.meta)
            if fit['owner']!=owner:raise ValueError('Fit owner mismatch')
            row.update(state=fit['state'],ended_at=utc(),elapsed_seconds=fit['elapsed_seconds'],
                       manifest_sha256=sha(folder/'manifest.json'))
            initial=[self.data['jobs'][j]['state'] for j in INITIAL.values()]
            if self.data['phase']=='initial' and all(s in ('complete','failed') for s in initial):
                self.data['phase']='released' if all(s=='complete' for s in initial) else 'blocked'
                self.data['initial_timings']={j:self.data['jobs'][j]['elapsed_seconds'] for j in INITIAL.values()}
            self.save()
    def failed_before_receipt(self,job,owner,error):
        with self.lock:
            self.owner(job,owner);self.data['jobs'][job].update(state='failed',ended_at=utc(),error=error)
            if job in INITIAL.values():self.data['phase']='blocked'
            self.save()


def worker_command(inputs,output,job,owner):
    return [sys.executable,'-u',str(ROOT/'scripts/h2_production/empirical.py'),'fit','--inputs',str(inputs),
            '--output',str(output),'--job',job,'--owner',owner,'--cores','4']


def local_worker(owner,reg,inputs,outputs):
    while True:
        assignment=reg.claim(owner)
        if assignment['action']=='wait':time.sleep(10);continue
        if assignment['action']!='fit':return
        job=assignment['job'];folder=outputs/job
        log=outputs/(job+'-stdout.txt')
        with log.open('wb') as stream:
            result=subprocess.run(worker_command(inputs,folder,job,owner),stdout=stream,stderr=subprocess.STDOUT)
        if not (folder/'manifest.json').exists():
            reg.failed_before_receipt(job,owner,'Worker exited before a result manifest; see private stdout');return
        try:reg.finish(job,owner,folder)
        except Exception as exc:reg.failed_before_receipt(job,owner,'Result verification failed: '+str(exc));return
        if result.returncode:return


def handler(reg,inputs,outputs,tokens):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def respond(self,status,value):
            b=json.dumps(value).encode();self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def auth(self):
            owner=self.headers.get('X-H2-Worker','');given=self.headers.get('X-H2-Capability','')
            if owner not in tokens or not hmac.compare_digest(given,tokens[owner]):raise PermissionError('Unauthorized')
            return owner
        def body(self,limit=CHUNK):
            n=int(self.headers.get('Content-Length','-1'))
            if n<0 or n>limit:raise ValueError('Invalid content length')
            data=self.rfile.read(n)
            if len(data)!=n:raise ValueError('Incomplete body')
            return data
        def do_GET(self):
            try:
                owner=self.auth()
                if self.path!='/inputs':raise ValueError('Unknown path')
                p=inputs.parent/'inputs.tar.gz';self.send_response(200)
                self.send_header('Content-Length',str(p.stat().st_size));self.end_headers()
                with p.open('rb') as f:shutil.copyfileobj(f,self.wfile)
            except PermissionError:self.respond(403,{'error':'Unauthorized'})
            except Exception:self.respond(400,{'error':'Invalid request'})
        def do_POST(self):
            try:
                owner=self.auth()
                if self.path=='/claim':self.body(1024);self.respond(200,reg.claim(owner));return
                match=re.fullmatch(r'/finish/((?:uwa|nicolas)-s[0-3]-c[0-7])',self.path)
                if not match:raise ValueError('Unknown path')
                job=match.group(1);m=json.loads(self.body(65536))
                with reg.lock:
                    row=reg.data['jobs'][job]
                    if row['owner']==owner and row['state'] in ('complete','failed'):
                        existing=json.loads((outputs/job/'manifest.json').read_text())
                        if existing!=m:raise ValueError('Changed completed manifest')
                        self.respond(200,{'verified':True,'job':job});return
                reg.owner(job,owner)
                if m['job']!=job or set(m['files'])-ALLOWED:raise ValueError('Invalid manifest')
                folder=outputs/job;folder.mkdir(parents=True,exist_ok=True)
                for name,row in m['files'].items():
                    n=int(row['bytes']);expected=row['sha256']
                    if n<0 or n>MAX_FILE or not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('Invalid file metadata')
                    p=folder/name
                    if p.exists() and p.stat().st_size==n and sha(p)==expected:continue
                    tmp=p.with_suffix(p.suffix+'.tmp');count=(n+CHUNK-1)//CHUNK
                    with tmp.open('wb') as out:
                        for part in range(count):
                            q=outputs/'.parts'/job/name/f'{part:05d}'
                            if q.stat().st_size!=min(CHUNK,n-part*CHUNK):raise ValueError('Invalid chunk size')
                            with q.open('rb') as f:shutil.copyfileobj(f,out)
                    if tmp.stat().st_size!=n or sha(tmp)!=expected:raise ValueError('Transferred file mismatch')
                    tmp.replace(p)
                dump(folder/'manifest.json',m);reg.finish(job,owner,folder)
                shutil.rmtree(outputs/'.parts'/job,ignore_errors=True)
                self.respond(200,{'verified':True,'job':job})
            except PermissionError:self.respond(403,{'error':'Unauthorized'})
            except Exception as exc:self.respond(400,{'error':str(exc)})
        def do_PUT(self):
            try:
                owner=self.auth()
                match=re.fullmatch(r'/part/((?:uwa|nicolas)-s[0-3]-c[0-7])/([a-z-]+\.(?:json|npz))/(\d{5})',self.path)
                if not match:raise ValueError('Unknown path')
                job,name,part=match.groups()
                if name not in ALLOWED or int(part)>=MAX_FILE//CHUNK:raise ValueError('Invalid file part')
                reg.owner(job,owner);data=self.body()
                if hashlib.sha256(data).hexdigest()!=self.headers.get('X-Content-SHA256'):raise ValueError('Chunk checksum mismatch')
                p=outputs/'.parts'/job/name/part;p.parent.mkdir(parents=True,exist_ok=True)
                if p.exists():
                    if p.read_bytes()!=data:raise ValueError('Conflicting uploaded chunk')
                else:
                    tmp=p.with_suffix('.tmp');tmp.write_bytes(data);tmp.replace(p)
                self.respond(200,{'stored':True})
            except PermissionError:self.respond(403,{'error':'Unauthorized'})
            except Exception as exc:self.respond(400,{'error':str(exc)})
    return Handler


def request(url,owner,secret,path,data=None,method=None,headers=None):
    h={'X-H2-Worker':owner,'X-H2-Capability':secret,**(headers or {})}
    error=None
    for attempt in range(3):
        try:
            req=urllib.request.Request(url+path,data=data,method=method,headers=h)
            with urllib.request.urlopen(req,timeout=180) as response:return response.read()
        except urllib.error.HTTPError as exc:
            # Repeating a claim after an ambiguous response never launches a duplicate:
            # the registry returns already_running, and this worker stops for inspection.
            if exc.code<500:raise RuntimeError(f'Transfer HTTP {exc.code}: '+exc.read(1000).decode(errors='replace')) from None
            error=exc
        except OSError as exc:error=exc
        if attempt<2:time.sleep(3*(attempt+1))
    raise RuntimeError('Transport failed after three bounded attempts') from error


def cloud_worker(url,secret_file,owner,bundle_hash,work):
    secret=secret_file.read_text().strip();work.mkdir(parents=True,exist_ok=True)
    archive=work/'inputs.tar.gz';archive.write_bytes(request(url,owner,secret,'/inputs'))
    inputs=work/'inputs';inputs.mkdir()
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not member.isfile() or Path(member.name).name!=member.name:raise ValueError('Unsafe input bundle')
        tar.extractall(inputs,filter='data')
    if sha(inputs/'bundle.json')!=bundle_hash:raise ValueError('Wrong frozen bundle')
    meta=check_bundle(inputs)
    while True:
        assignment=json.loads(request(url,owner,secret,'/claim',b'{}','POST'))
        if assignment['action']=='wait':print('Waiting for the other initial fit.',flush=True);time.sleep(30);continue
        if assignment['action']!='fit':print(json.dumps(assignment),flush=True);return
        job=assignment['job'];folder=work/'outputs'/job
        print('Assigned '+job,flush=True)
        result=subprocess.run(worker_command(inputs,folder,job,owner))
        if not (folder/'manifest.json').exists():raise RuntimeError('Worker failed before manifest; do not repeat fit')
        verify_result(folder,meta);m=json.loads((folder/'manifest.json').read_text())
        for name in m['files']:
            with (folder/name).open('rb') as f:
                part=0
                while data:=f.read(CHUNK):
                    request(url,owner,secret,f'/part/{job}/{name}/{part:05d}',data,'PUT',{'X-Content-SHA256':hashlib.sha256(data).hexdigest()});part+=1
        response=json.loads(request(url,owner,secret,'/finish/'+job,json.dumps(m).encode(),'POST'))
        if not response['verified']:raise RuntimeError('Remote archive not verified')
        print('Durably exported and verified '+job,flush=True)
        # Only remove the cloud duplicate after the private remote archive verifies.
        shutil.rmtree(folder)
        if result.returncode:return


def serve(inputs,outputs,secrets_file,port):
    meta=check_bundle(inputs);outputs.mkdir(parents=True,exist_ok=True)
    tokens=json.loads(secrets_file.read_text())
    if set(tokens)!= {'claude-1','claude-2'} or any(len(t)<40 for t in tokens.values()):raise ValueError('Invalid batch capabilities')
    archive=inputs.parent/'inputs.tar.gz'
    if not archive.exists():
        with tarfile.open(archive,'w:gz') as tar:
            for p in sorted(inputs.iterdir()):tar.add(p,arcname=p.name)
    reg=Registry(outputs/'register.json',meta)
    server=ThreadingHTTPServer(('0.0.0.0',port),handler(reg,inputs,outputs,tokens))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    workers=[threading.Thread(target=local_worker,args=(owner,reg,inputs,outputs),daemon=True) for owner in ('hf-1','hf-2')]
    for thread in workers:thread.start()
    print('Private transfer service and HF workers started.',flush=True)
    try:
        while True:
            with reg.lock:
                rows=list(reg.data['jobs'].values());counts={s:sum(r['state']==s for r in rows) for s in ('unassigned','running','complete','failed')}
                if counts['running']==0 and (counts['unassigned']==0 or reg.data['phase']=='blocked'):break
            print(json.dumps({'at':utc(),'counts':counts,'phase':reg.data['phase']}),flush=True);time.sleep(30)
    finally:server.shutdown();server.server_close()
    print('Batch stopped at its recorded terminal boundary.',flush=True)


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('serve');a.add_argument('--inputs',type=Path,required=True);a.add_argument('--outputs',type=Path,required=True);a.add_argument('--secrets-file',type=Path,required=True);a.add_argument('--port',type=int,default=8000)
    a=sub.add_parser('cloud');a.add_argument('--url',required=True);a.add_argument('--secret-file',type=Path,required=True);a.add_argument('--owner',choices=['claude-1','claude-2'],required=True);a.add_argument('--bundle-hash',required=True);a.add_argument('--work',type=Path,required=True)
    a=p.parse_args()
    if a.command=='serve':serve(a.inputs,a.outputs,a.secrets_file,a.port)
    else:cloud_worker(a.url,a.secret_file,a.owner,a.bundle_hash,a.work)
if __name__=='__main__':main()

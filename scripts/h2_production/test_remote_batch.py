"""No model fitting: assignment, integrity and restricted-transfer checks."""
import concurrent.futures
import hashlib
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
from common import dump,sha
from empirical import all_jobs,job_info
from remote_batch import Registry,handler,verify_result,CHUNK

class BatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.meta={'source_hashes':{'model.py':'frozen'}}
        self.reg=Registry(self.root/'register.json',self.meta)
    def tearDown(self):self.temp.cleanup()
    def test_unique_jobs_seeds(self):
        jobs=all_jobs();self.assertEqual(len(jobs),64);self.assertEqual(len(set(jobs)),64)
        self.assertEqual(len({job_info(j)['seed'] for j in jobs}),64)
        for bad in ['../uwa-s0-c0','uwa-s4-c0','nicolas-s0-c8','x-s0-c0']:
            with self.assertRaises(ValueError):job_info(bad)
    def test_initial_assignments_and_no_reclaim(self):
        self.assertEqual(self.reg.claim('hf-1')['job'],'nicolas-s0-c1')
        self.assertEqual(self.reg.claim('claude-1')['job'],'nicolas-s0-c0')
        self.assertEqual(self.reg.claim('hf-2')['action'],'wait')
        self.assertEqual(self.reg.claim('hf-1')['action'],'already_running')
        with self.assertRaises(ValueError):self.reg.owner('nicolas-s0-c0','hf-1')
        with self.assertRaises(RuntimeError):Registry(self.root/'register.json',self.meta)
    def test_atomic_claims(self):
        self.reg.data['phase']='released'
        with concurrent.futures.ThreadPoolExecutor(12) as pool:
            results=list(pool.map(lambda _:self.reg.claim('hf-1'),range(12)))
        self.assertEqual(sum(r['action']=='fit' for r in results),1)
        with concurrent.futures.ThreadPoolExecutor(4) as pool:
            results=list(pool.map(self.reg.claim,['hf-1','hf-2','claude-1','claude-2']))
        self.assertEqual(len({r['job'] for r in results}),4)
    def failure_fixture(self,job,owner):
        p=self.root/job;p.mkdir();dump(p/'fit.json',dict(job=job_info(job),owner=owner,
             state='failed',source_hashes=self.meta['source_hashes'],elapsed_seconds=1))
        m=dict(job=job,state='failed',files={'fit.json':dict(bytes=(p/'fit.json').stat().st_size,sha256=sha(p/'fit.json'))})
        dump(p/'manifest.json',m);return p,m
    def test_failure_retained_and_initial_blocks(self):
        self.reg.claim('hf-1');self.reg.claim('claude-1')
        for owner,job in [('hf-1','nicolas-s0-c1'),('claude-1','nicolas-s0-c0')]:
            folder,_=self.failure_fixture(job,owner);self.reg.finish(job,owner,folder)
            self.reg.finish(job,owner,folder) # Exact duplicate acknowledgement is harmless.
        self.assertEqual(self.reg.data['phase'],'blocked')
        self.assertEqual(self.reg.claim('hf-2')['action'],'stop')
    def test_integrity_and_manifest_paths(self):
        folder,m=self.failure_fixture('nicolas-s0-c0','claude-1')
        self.assertEqual(verify_result(folder,self.meta)['state'],'failed')
        (folder/'fit.json').write_text('{}')
        with self.assertRaises(ValueError):verify_result(folder,self.meta)
        m['files']={'../secret':dict(bytes=1,sha256='a'*64)};dump(folder/'manifest.json',m)
        with self.assertRaises(ValueError):verify_result(folder,self.meta)
    def test_http_auth_paths_ownership_and_checksum(self):
        inputs=self.root/'inputs';inputs.mkdir();outputs=self.root/'outputs';outputs.mkdir()
        self.reg.claim('claude-1');secret='A'*48
        server=ThreadingHTTPServer(('127.0.0.1',0),handler(self.reg,inputs,outputs,{'claude-1':secret}))
        thread=threading.Thread(target=server.serve_forever);thread.start();url=f'http://127.0.0.1:{server.server_port}'
        def call(path,method='GET',data=None,authenticated=True,extra=None):
            headers={'X-H2-Worker':'claude-1','X-H2-Capability':secret} if authenticated else {}
            headers.update(extra or {})
            req=urllib.request.Request(url+path,data=data,headers=headers,method=method)
            with urllib.request.urlopen(req) as response:return json.loads(response.read())
        try:
            with self.assertRaises(urllib.error.HTTPError) as exc:call('/inputs',authenticated=False)
            self.assertEqual(exc.exception.code,403)
            with self.assertRaises(urllib.error.HTTPError):call('/../../etc/passwd')
            body=b'{}';header={'X-Content-SHA256':hashlib.sha256(body).hexdigest()}
            self.assertTrue(call('/part/nicolas-s0-c0/fit.json/00000','PUT',body,extra=header)['stored'])
            self.assertTrue(call('/part/nicolas-s0-c0/fit.json/00000','PUT',body,extra=header)['stored'])
            with self.assertRaises(urllib.error.HTTPError):call('/part/nicolas-s0-c1/fit.json/00000','PUT',body,extra=header)
            with self.assertRaises(urllib.error.HTTPError):call('/part/nicolas-s0-c0/fit.json/00001','PUT',body,extra={'X-Content-SHA256':'0'*64})
            with self.assertRaises(urllib.error.HTTPError):call('/part/nicolas-s0-c0/secret.txt/00000','PUT',body,extra=header)
        finally:server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main(verbosity=2)

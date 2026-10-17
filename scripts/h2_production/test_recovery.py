"""Operational fixtures only: no model, outcome or replacement research data."""
import concurrent.futures
import json
import os
import signal
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from common import dump, sha, utc
from empirical import all_jobs, job_info
from recovery import (FIRST, IMPORTED, RecoveryRegistry, failure_receipt, finalize_child,
                      process_evidence, recovery_handler, supervise)
from remote_batch import verify_result
from launch_recovery import PROBE_SHA, resource_budget, validate_lifecycle


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.meta = {'source_hashes': {'model.py': 'frozen'}}

    def tearDown(self):
        self.temp.cleanup()

    def registry(self, mode='mixed'):
        original = self.root / 'original'
        original.mkdir()
        jobs = {j: dict(state='unassigned', owner=None) for j in all_jobs()}
        for job, state, owner in ((FIRST, 'failed', 'claude-1'), (IMPORTED, 'complete', 'hf-1')):
            folder = original / job
            folder.mkdir()
            dump(folder / 'fit.json', dict(job=job_info(job), state=state, owner=owner,
                 source_hashes=self.meta['source_hashes'], bundle_sha256='bundle', elapsed_seconds=1))
            dump(folder / 'manifest.json', dict(job=job, state=state,
                 files={'fit.json': dict(bytes=(folder/'fit.json').stat().st_size, sha256=sha(folder/'fit.json'))}))
            jobs[job] = dict(state=state, owner=owner, elapsed_seconds=1, manifest_sha256=sha(folder/'manifest.json'))
        dump(original/'register.json', {'jobs': jobs})
        # This test only exercises import/assignment state. It does not pretend to supply posterior data.
        with patch('recovery.verify_result', side_effect=lambda folder, meta: json.loads((folder/'fit.json').read_text())):
            reg=RecoveryRegistry(self.root/'outputs/register.json', self.meta, original, mode,
                                 time.time()+600, 'bundle')
        return reg, original

    def test_import_attempt_history_and_unique_replacement(self):
        reg, original = self.registry()
        self.assertEqual(reg.data['jobs'][IMPORTED]['state'], 'complete')
        self.assertEqual(reg.claim('hf-1')['action'], 'wait')
        self.assertEqual(reg.claim('hf-2')['action'], 'wait')
        with concurrent.futures.ThreadPoolExecutor(8) as pool:
            claims=list(pool.map(lambda _: reg.claim('claude-1'), range(8)))
        self.assertEqual(sum(c['action']=='fit' for c in claims), 1)
        self.assertEqual(reg.data['jobs'][FIRST]['attempt'], 2)
        self.assertEqual(reg.data['jobs'][FIRST]['previous_attempt']['manifest_sha256'], sha(original/FIRST/'manifest.json'))
        with self.assertRaises(RuntimeError):
            RecoveryRegistry(reg.path, self.meta, original, 'mixed', time.time()+600, 'bundle')

    def test_hf_fallback_and_failed_replacement_does_not_release(self):
        reg, _ = self.registry('hf')
        with self.assertRaises(ValueError): reg.claim('claude-1')
        self.assertEqual(reg.claim('hf-1')['job'], FIRST)
        folder=self.root/'outputs'/FIRST
        failure_receipt(folder,self.meta,FIRST,'hf-1','bundle','test abrupt exit',-9,1)
        reg.finish(FIRST,'hf-1',folder)
        self.assertEqual(reg.data['phase'],'blocked')
        self.assertEqual(reg.claim('hf-2')['action'],'stop')
        self.assertEqual(sum(r['state']=='unassigned' for r in reg.data['jobs'].values()),62)

    def test_stale_process_evidence_never_reassigns(self):
        reg, _ = self.registry()
        reg.claim('claude-1')
        row=reg.data['jobs'][FIRST]
        self.assertEqual(process_evidence(row),'assigned_no_process_evidence')
        reg.heartbeat(FIRST,'claude-1',dict(at=utc(),child_alive=True,pid=42,returncode=None,phase='running'))
        self.assertEqual(process_evidence(row),'recent_process_evidence')
        self.assertEqual(process_evidence(row,now=time.time()+500),'stale_process_evidence')
        self.assertEqual(reg.claim('claude-1')['action'],'already_running')
        self.assertEqual(process_evidence(row,provider_stage='ERROR'),'provider_terminated_unverified')
        with self.assertRaises(ValueError):
            reg.heartbeat(FIRST,'hf-1',dict(child_alive=True))

    def test_successful_gate_releases_exactly_remaining_jobs(self):
        reg, _ = self.registry()
        reg.claim('claude-1')
        folder=self.root/'outputs'/FIRST
        folder.mkdir()
        dump(folder/'manifest.json',{'operational_state_fixture':True})
        fit=dict(state='complete',owner='claude-1',elapsed_seconds=1)
        with patch('remote_batch.verify_result',return_value=fit):
            reg.finish(FIRST,'claude-1',folder)
        self.assertEqual(reg.data['phase'],'released')
        self.assertEqual(sum(r['state']=='unassigned' for r in reg.data['jobs'].values()),62)
        with concurrent.futures.ThreadPoolExecutor(3) as pool:
            claims=list(pool.map(reg.claim,('hf-1','hf-2','claude-1')))
        self.assertEqual(len({c['job'] for c in claims}),3)
        self.assertTrue(all(c['job'] not in (FIRST,IMPORTED) for c in claims))

    def test_heartbeat_endpoint_authentication_and_owner(self):
        reg, _ = self.registry()
        reg.claim('claude-1')
        server=ThreadingHTTPServer(('127.0.0.1',0),recovery_handler(
            reg,self.root/'inputs',self.root/'outputs',{'claude-1':'A'*48}))
        thread=threading.Thread(target=server.serve_forever)
        thread.start()
        def call(job,authenticated):
            headers={'X-H2-Worker':'claude-1','X-H2-Capability':'A'*48} if authenticated else {}
            req=urllib.request.Request(f'http://127.0.0.1:{server.server_port}/heartbeat/{job}',
                data=json.dumps(dict(at=utc(),child_alive=True,pid=42,returncode=None)).encode(),headers=headers)
            try:
                with urllib.request.urlopen(req) as response:
                    return response.status,json.loads(response.read())
            except urllib.error.HTTPError as exc:
                status=exc.code
                exc.close()
                return status,None
        try:
            self.assertEqual(call(FIRST,False)[0],403)
            self.assertEqual(call(IMPORTED,True)[0],400)
            status,value=call(FIRST,True)
            self.assertEqual(status,200)
            self.assertTrue(value['recorded'])
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_process_success_and_duplicate_launch(self):
        folder=self.root/'ok'
        events=[]
        result=supervise([sys.executable,'-c','print("ordinary process check")'],folder,
                         lambda event: events.append(event),time.time()+10,interval=.02)
        self.assertEqual(result['returncode'],0)
        self.assertFalse(result['child_alive'])
        self.assertTrue(any(e['child_alive'] for e in events))
        with self.assertRaises(FileExistsError):
            supervise([sys.executable,'-c','raise Exception("must not launch")'],folder,
                      lambda event: None,time.time()+10)

    def test_abrupt_child_termination_preserved(self):
        folder=self.root/FIRST
        code='import os, signal; os.kill(os.getpid(), signal.SIGKILL)'
        result=supervise([sys.executable,'-c',code],folder,lambda event: None,time.time()+10,interval=.02)
        self.assertEqual(result['returncode'],-signal.SIGKILL)
        fit=finalize_child(folder,result,self.meta,FIRST,'claude-1','bundle')
        self.assertEqual(fit['state'],'failed')
        self.assertEqual(fit['exit_status'],-signal.SIGKILL)
        self.assertEqual(verify_result(folder,self.meta)['state'],'failed')
        (folder/'fit.json').write_text('{}')
        with self.assertRaises(ValueError): verify_result(folder,self.meta)

    def test_budget_termination_and_transport_failure_capture(self):
        for label, callback in [('deadline',lambda event:None),
                                ('transport',lambda event: (_ for _ in ()).throw(RuntimeError('transport down')))]:
            result=supervise([sys.executable,'-c','import time; time.sleep(10)'],self.root/label,
                             callback,time.time()+.1,interval=.02)
            self.assertIsNotNone(result['returncode'])
            self.assertIn('error',result)
            with self.assertRaises(ProcessLookupError): os.kill(result['pid'],0)

    def test_collection_restart_uses_verified_bytes(self):
        import collect
        target=self.root/'download.json'
        content='{"operational_fixture":true}\n'
        def transfer(*args):
            Path(args[-1]).write_text(content)
            return ''
        with patch('collect.cli',side_effect=transfer) as cli:
            collect.fetch('receipt.json',target)
            digest=sha(target)
            collect.fetch('receipt.json',target,digest)
            self.assertEqual(cli.call_count,1)
            target.write_text('corrupted')
            collect.fetch('receipt.json',target,digest)
            self.assertEqual(cli.call_count,2)
            self.assertEqual(target.read_text(),content)

    def test_launch_requires_actual_probe_completion(self):
        proof=dict(state='running_unverified')
        with self.assertRaises((KeyError,ValueError)): validate_lifecycle(proof,'mixed')
        with self.assertRaises(ValueError): validate_lifecycle(proof,'hf')
        proof=dict(state='passed',observed_task_exit_status=0,
            receipt=dict(state='complete',exit_status=0,elapsed_seconds=7500.1,duration_seconds=7500,
                         script_sha256=PROBE_SHA,empirical_fits=0,research_data_access=False),
            last_heartbeats=[dict(elapsed_seconds=t) for t in (7380,7440,7500.1)])
        validate_lifecycle(proof,'mixed')
        proof['receipt']['elapsed_seconds']=7199
        with self.assertRaises(ValueError): validate_lifecycle(proof,'mixed')
        validate_lifecycle({'state':'failed'},'hf')

    def test_budget_excludes_overlap_and_additional_credit(self):
        from launch_recovery import ORIGINAL_JOB
        provider=dict(id=ORIGINAL_JOB,status={'stage':'RUNNING'},durations={'total_secs':20000})
        with self.assertRaises(ValueError): resource_budget(provider,12,time.time())
        provider['status']['stage']='COMPLETED'
        hours,cost,allowed,remaining=resource_budget(provider,5,time.time())
        self.assertGreater(hours,20000/3600)
        self.assertAlmostEqual(cost,hours*.04)
        self.assertEqual(allowed,5)
        self.assertGreater(remaining,0)
        with self.assertRaises(ValueError): resource_budget(provider,0,time.time())


if __name__=='__main__':
    unittest.main(verbosity=2)

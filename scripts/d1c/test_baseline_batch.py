"""Fixtures for fixed-scope distribution, budget, cache integrity and capacity."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

import baseline_batch as batch
import d1c
import launch_baseline_batch as launch
import monitor_baseline_batch as monitor
import paired_batch as paired
from component_state import ComponentState
from run_state import atomic_json, digest


class BaselineTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.spec = batch.specification("b"*40)

    def save(self, base, name, *, lose_h=False, extra_h=False, bad_seed=False):
        info = self.spec["modules"][name]
        job, mode = info["job"], info["mode"]
        if mode == "upstream":
            arrays = {n:np.zeros((8,400)) for n in ("z","v","s")}
            if (job["reliability"] and not lose_h) or extra_h:
                arrays["h"] = np.zeros((8,400,3))
            seed, draws = d1c.seed(2,job["cell"],0),8000
        else:
            arrays = {n:np.linspace(-.5,.5,16000) for n in ("h2","h1_fixed_usage","b_z","marking")}
            seed = d1c.seed(2,job["cell"],0) if mode == "joint" else d1c.seed(4,job["cell"],0,info["component"])
            draws=4000
        metadata = dict(diagnostic=dict(mode=mode,seed=seed+int(bad_seed),draws=draws,tune=2000,
            good=info["component"] != 5,contrast_good=True,divergences=0),
            rng_state=np.random.default_rng(9).bit_generator.state)
        with contextlib.redirect_stdout(io.StringIO()):
            with ComponentState(base/"modules"/name/"checkpoints",batch.module_spec(self.spec,name)) as store:
                store.save(info["key"],metadata,arrays)
                return store.records[info["key"]]

    def test_scope_exactly_completes_sixteen_cells_without_repeats(self):
        assigned = sum(batch.hosts().values(),[])
        self.assertEqual(len(assigned),60)
        self.assertEqual(len(set(assigned)),60)
        self.assertEqual(set(assigned),set(batch.modules()))
        self.assertEqual(set(batch.CUT_CELLS+batch.JOINT_CELLS+batch.REUSED_CELLS),set(batch.jobs()))
        self.assertFalse(set(batch.CUT_CELLS+batch.JOINT_CELLS)&set(batch.REUSED_CELLS))
        self.assertEqual(len(batch.hosts()),27)
        self.assertEqual(sum(v['mode']!='upstream' for v in batch.modules().values()),54)
        self.assertTrue(all(names[0].endswith('upstream') for names in list(batch.hosts().values())[:6]))

    def test_register_shapes_and_wrong_seed_are_enforced(self):
        for cell in (6,22):
            name=batch.module_name(cell,'upstream')
            self.save(self.root,name)
            _,arrays=batch.check_module(self.root/'modules'/name,self.spec,name)
            self.assertEqual('h' in arrays,cell==22)
        for cell,kwargs in ((6,dict(extra_h=True)),(22,dict(lose_h=True)),(6,dict(bad_seed=True))):
            folder=self.root/str(kwargs);name=batch.module_name(cell,'upstream')
            self.save(folder,name,**kwargs)
            with self.assertRaises(ValueError): batch.check_module(folder/'modules'/name,self.spec,name)

    def test_nonregister_cut_replays_all_eight_and_retains_diagnostic_failure(self):
        cell=6
        for name,info in self.spec['modules'].items():
            if info['job']['cell']==cell:self.save(self.root,name)
        truths=dict(h2_prevalence_bridge=0.,h1_fixed_usage=.1,b_z=-.2,marking=-.03)
        with patch.object(d1c,'generate',return_value=({},truths,9)),\
             patch.object(d1c,'upstream_data',return_value={}),\
             patch.object(d1c,'downstream_data',return_value={}),\
             patch.object(d1c,'sample',side_effect=AssertionError('Unexpected model fit')):
            result=batch.assemble_cell(self.root,self.spec,cell)
        self.assertEqual(result['status']['status'],'diagnostic_failure')
        self.assertEqual(len(result['status']['diagnostics']),9)
        self.assertEqual(len(result['archive_sha256']),9)
        self.assertNotIn('support',result['rows'][0])
        with np.load(self.root/'cells/cell-006/contrasts.npz') as a:self.assertEqual(a['h2'].shape,(8,16000))

    def test_missing_component_never_falls_through_to_sampler(self):
        self.save(self.root,'c006-upstream')
        with patch.object(d1c,'sample',side_effect=AssertionError('Unexpected model fit')) as sample:
            with self.assertRaises((ValueError,FileNotFoundError)):
                batch.assemble_cell(self.root,self.spec,6)
        sample.assert_not_called()

    def test_shared_upstream_is_checked_before_consumption(self):
        owner=self.root/'shared/cut-006-0'
        record=self.save(owner,'c006-upstream')
        atomic_json(owner/'upstream-ready.json',dict(batch_signature=digest(paired.scientific_identity(self.spec)),
                    archive_sha256=record['archive_sha256']))
        spec=dict(self.spec,platform='different kernel')
        target=self.root/'receiver'
        batch.receive_upstream(target,spec,6,self.root/'shared',lambda:self.fail('Unexpected wait'))
        imported,_=batch.check_module(target/'modules/c006-upstream',spec,'c006-upstream')
        self.assertEqual(imported['archive_sha256'],record['archive_sha256'])

    def test_budget_and_commands_are_bounded(self):
        self.assertAlmostEqual(launch.MAXIMUM_NEW_USD,9.72)
        self.assertAlmostEqual(launch.TOTAL_RESERVED_USD,13.08)
        self.assertLessEqual(launch.TOTAL_RESERVED_USD,launch.AUTHORIZED_USD)
        for host in batch.hosts():
            cmd=launch.hf_command('b'*40,host,True)
            self.assertEqual(cmd[cmd.index('--timeout')+1],'12h')
            self.assertEqual(cmd[cmd.index('--attempts')+1],'1')
            self.assertNotIn('--secrets',cmd)

    def test_capacity_wait_resumes_without_repeating_accepted_jobs(self):
        receipt=self.root/'launch.json';calls=[];rejected=False
        def run(cmd,**kwargs):
            nonlocal rejected
            host=cmd[-1];calls.append(host)
            if len(calls)==2 and not rejected:
                rejected=True
                return SimpleNamespace(returncode=1,stdout='',stderr='HTTP 429 Too Many concurrent jobs')
            return SimpleNamespace(returncode=0,stdout=json.dumps(dict(id='id-'+host)),stderr='')
        with patch.object(launch,'RECEIPT',receipt),patch.object(launch,'verify_published_source'),\
             patch.object(launch,'command',return_value=b'[]'),patch.object(launch.subprocess,'run',side_effect=run),\
             patch.object(launch.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
            first=launch.launch('b'*40,False)
            self.assertEqual(first['state'],'waiting_for_capacity')
            second=launch.launch('b'*40,True)
        self.assertEqual(second['state'],'launched')
        self.assertEqual(len(calls),28)
        self.assertEqual(calls.count(list(batch.hosts())[0]),1)
        self.assertEqual(sum(v['state']=='accepted' for v in second['hosts'].values()),27)

    def test_ambiguous_submission_cannot_repeat(self):
        host=next(iter(batch.hosts()))
        record=dict(source_commit='b'*40,hosts={host:dict(state='submitting')})
        with self.assertRaisesRegex(RuntimeError,'Ambiguous submission'):
            launch.reconcile(record,[])
        launch.reconcile(record,[dict(id='saved',labels=dict(name=launch.label(host)),command='run '+('b'*40))])
        self.assertEqual(record['hosts'][host]['id'],'saved')
        self.assertEqual(record['hosts'][host]['state'],'accepted')

    def test_pairing_requires_same_generated_data(self):
        jobs=batch.jobs()
        row=dict(estimand='h2_prevalence_bridge',data_seed=7,truth=0.,mean=.1,width90=.4)
        results={0:dict(status=jobs[0],rows=[row]),6:dict(status=jobs[6],rows=[dict(row,mean=.2,width90=.8)])}
        pair=monitor.comparison_rows(results)[0]
        self.assertAlmostEqual(pair['mean_difference'],-.1)
        self.assertAlmostEqual(pair['width90_ratio'],.5)
        results[6]['rows'][0]['data_seed']=8
        with self.assertRaisesRegex(ValueError,'datasets differ'):monitor.comparison_rows(results)


if __name__=='__main__':unittest.main()

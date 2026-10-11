"""No live provider calls: exercise scientific job accounting and packet barriers."""
import copy
import json
from pathlib import Path
import signal
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import production_runner as runner


def packet(identifier='wnadj-01', supplemented=False):
    return {'packet_id': identifier, 'stratum': 'wordnet_adjective', 'items': [
        {'item_id': 'item-' + identifier, 'word': 'test', 'dictionary_senses': [
            {'sense_id': identifier + '-a1', 'pos': 'a', 'gloss': 'a supplied adjective interpretation'}],
         'coverage': {'wordnet': 'present', 'supplement': 'retrieved' if supplemented else 'not_supplied',
                      'supplement_required': False, 'review_complete': True, 'parser_issues': []},
         'sources': [], 'ratings': {'valence': 9}, 'source_membership': ['hidden']} ]}


def write_answer(root, family, data, requests):
    identifier = runner.job_id(family, data['packet_id'], 'initial')
    runner.atomic_json(root / 'jobs' / identifier / 'answer.json', {'requests': requests})
    return {'status': 'mechanically_valid', 'job_id': identifier, 'family': family}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.public = self.root / 'public'

    def tearDown(self):
        self.temp.cleanup()

    def test_blinding_preserves_evidence_and_hides_selection(self):
        value = packet()
        sent = runner.model_packet(value)
        self.assertNotIn('stratum', sent)
        self.assertNotIn('ratings', sent['items'][0])
        self.assertNotIn('source_membership', sent['items'][0])
        self.assertEqual(sent['items'][0]['dictionary_senses'], value['items'][0]['dictionary_senses'])

    def test_semantic_change_excludes_status_and_timestamp(self):
        value = packet()
        changed = copy.deepcopy(value)
        changed['items'][0]['coverage']['supplement'] = 'missing'
        changed['items'][0]['dictionary_senses'][0]['timestamp'] = 'later'
        self.assertEqual(runner.evidence_fingerprint(value), runner.evidence_fingerprint(changed))
        changed['items'][0]['dictionary_senses'].append({'sense_id': 'new', 'pos': 'a', 'gloss': 'new evidence'})
        self.assertNotEqual(runner.evidence_fingerprint(value), runner.evidence_fingerprint(changed))

    def test_barrier_union_and_one_augmentation(self):
        value = packet()
        value['items'].append({**copy.deepcopy(value['items'][0]), 'item_id': 'second'})
        calls = []
        def supplement(data, ids):
            calls.append(ids)
            data['items'][0]['dictionary_senses'].append({'sense_id': 's2', 'pos': 'a', 'gloss': 'new supplied evidence'})
            return {'packet': data, 'changed': True}
        initial = {family: write_answer(self.root, family, value, [identifier]) for family, identifier in
                   [('codex', value['items'][0]['item_id']), ('claude', 'second')]}
        with self.assertRaises(RuntimeError):
            runner.augment_after_barrier(value, {'codex': initial['codex']}, supplement, self.root)
        read = lambda answer, data: set(answer['requests'])
        result = runner.augment_after_barrier(value, initial, supplement, self.root, read)
        self.assertTrue(result['changed'])
        self.assertEqual(calls, [sorted([value['items'][0]['item_id'], 'second'])])
        self.assertEqual(runner.augment_after_barrier(value, initial, supplement, self.root, read), result)
        self.assertEqual(len(calls), 1)

    def test_failed_initial_still_allows_other_request_and_redundant_does_not(self):
        value = packet()
        initial = {'codex': {'status': 'failed'}, 'claude': write_answer(self.root, 'claude', value, [value['items'][0]['item_id']])}
        def supplement(data, ids):
            data['items'][0]['coverage']['supplement'] = 'missing'
            return {'packet': data, 'changed': True}  # Claimed change isn't trusted.
        result = runner.augment_after_barrier(value, initial, supplement, self.root,
                                             lambda answer, data: set(answer['requests']))
        self.assertFalse(result['changed'])
        value = packet('wnadj-02', supplemented=True)
        initial = {f: write_answer(self.root, f, value, [value['items'][0]['item_id']]) for f in runner.MODELS}
        result = runner.augment_after_barrier(value, initial,
            lambda *args: self.fail('Already supplied supplement was retrieved again'), self.root,
            lambda answer, data: set(answer['requests']))
        self.assertFalse(result['changed'])
        self.assertEqual(result['requested_item_ids'], [])

    def test_partial_claude_stream_deduplicates_message_usage(self):
        msg = {'type': 'assistant', 'request_id': 'req1', 'message': {
            'id': 'msg1', 'model': runner.MODELS['claude'], 'usage': {'input_tokens': 12, 'output_tokens': 4}}}
        init = {'type': 'system', 'subtype': 'init', 'model': runner.MODELS['claude'],
                'tools': ['StructuredOutput'], 'mcp_servers': [], 'apiKeySource': 'none'}
        stdout = '\n'.join(map(json.dumps, [init, msg, msg])) + '\n{"partial":'
        meta, answer = runner.parse_route_logs('claude', stdout, '')
        self.assertEqual(meta['assistant_message_ids'], ['msg1'])
        self.assertEqual(meta['request_ids'], ['req1'])
        self.assertEqual(meta['partial_observed_usage'], {'input_tokens': 12, 'output_tokens': 4})
        self.assertIsNone(meta['underlying_request_count'])
        self.assertIsNone(meta['schema_repairs'])
        self.assertIsNone(answer)
        self.assertEqual(meta['malformed_stream_lines'], 1)

    def test_codex_identity_uses_only_header_and_partial_token_total(self):
        stderr = 'model: gpt-6.1-sol\nreasoning effort: high\nuser\nmodel: malicious-self-report\ntokens used\n1,234\n'
        meta, _ = runner.parse_route_logs('codex', '', stderr)
        self.assertEqual(meta['returned_model'], 'gpt-6.1-sol')
        self.assertEqual(meta['usage']['reported_total_tokens'], 1234)
        self.assertIsNone(runner.route_problem({'family': 'codex'}, stderr + 'The model says rate limit.'))

    def test_commands_and_environment_are_subscription_only(self):
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'secret', 'ANTHROPIC_API_KEY': 'secret', 'HOME': '/home/test'}):
            for family in runner.MODELS:
                env = runner.scrubbed_env(family)
                self.assertNotIn('OPENAI_API_KEY', env)
                self.assertNotIn('ANTHROPIC_API_KEY', env)
        codex = runner.command_for('codex', self.root, self.root, {})
        for token in ('--ignore-user-config', '--strict-config', '--ephemeral', 'shell_tool', 'multi_agent', 'apps'):
            self.assertIn(token, codex)
        claude = runner.command_for('claude', self.root, self.root, {})
        self.assertEqual(claude[claude.index('--tools') + 1], '')
        self.assertEqual(claude[claude.index('--setting-sources') + 1], '')
        self.assertIn('--safe-mode', claude)
        self.assertIn('--strict-mcp-config', claude)

    def test_timeout_kills_whole_group_and_keeps_partial_usage(self):
        class FakeProcess:
            pid = 424242
            returncode = -9
            def __init__(self, command, **kwargs):
                self.kwargs = kwargs
                self.command = command
                kwargs['stderr'].write('model: gpt-6.1-sol\nreasoning effort: high\nuser\ntokens used\n17\n')
            def communicate(self, **kwargs):
                raise subprocess.TimeoutExpired(self.command, kwargs['timeout'])
            def wait(self, **kwargs):
                return self.returncode
        with patch.object(runner.os, 'killpg') as kill:
            meta, answer = runner.execute_once('codex', self.root / 'timeout', 'neutral', {},
                                                timeout=1, popen=FakeProcess)
        self.assertEqual(kill.call_args_list[0].args, (424242, signal.SIGTERM))
        self.assertEqual(kill.call_args_list[1].args, (424242, signal.SIGKILL))
        self.assertEqual(meta['exit_code'], 'timeout')
        self.assertEqual(meta['usage']['reported_total_tokens'], 17)
        self.assertEqual(meta['status'], 'failed')
        self.assertIsNone(answer)

    def test_run_job_slot_never_replayed_and_cap_is_80(self):
        for name in runner.LICENSES:
            (self.root / name).write_text('test licence')
        called = []
        def execute(family, directory, prompt, schema):
            called.append(family)
            runner.atomic_json(directory / 'answer.json', {'unused': True})
            return {'status': 'returned', 'elapsed_seconds': 1}, {'unused': True}
        value = packet()
        runner.run_job('codex', value, 'initial', {'source_commit': 'abc', 'packets': {value['packet_id']: runner.digest(value)}}, self.root,
                       execute=execute, validator=lambda answer, packet: [])
        with self.assertRaises(FileExistsError):
            runner.run_job('codex', value, 'initial', {'source_commit': 'abc', 'packets': {value['packet_id']: runner.digest(value)}}, self.root,
                           execute=execute, validator=lambda answer, packet: [])
        self.assertEqual(called, ['codex'])
        for n in range(79):
            (self.root / 'jobs' / f'reserved-{n}').mkdir()
        with self.assertRaises(RuntimeError):
            runner.run_job('claude', value, 'initial', {'source_commit': 'abc', 'packets': {value['packet_id']: runner.digest(value)}}, self.root,
                           execute=execute, validator=lambda answer, packet: [])

    def test_runtime_cli_version_change_is_an_instrument_error(self):
        class FakeProcess:
            pid = 424242
            returncode = 0
            def __init__(self, command, **kwargs):
                kwargs['stderr'].write('OpenAI Codex v0.999.0\nmodel: gpt-6.1-sol\nreasoning effort: high\nuser\n')
                Path(command[command.index('-o') + 1]).write_text('{"ready":true}')
            def communicate(self, **kwargs):
                return None
        meta, answer = runner.execute_once('codex', self.root / 'changed-cli', 'neutral', {}, popen=FakeProcess)
        self.assertEqual(meta['status'], 'failed')
        self.assertEqual(meta['cli_version'], '0.999.0')
        self.assertEqual(meta['route_problem']['kind'], 'instrument_mismatch')
        self.assertEqual(answer, {'ready': True})

    def test_preflight_records_published_commit_and_allows_one_attempt(self):
        def execute(family, directory, prompt, schema, timeout):
            return {'status': 'returned'}, {'ready': True}
        with patch.object(runner, 'published_source', return_value='published-commit') as published, \
             patch.object(runner.subprocess, 'check_output', return_value='codex-cli 0.161.0'):
            result = runner.preflight('codex', self.root, execute=execute)
            self.assertEqual(result['source_commit'], 'published-commit')
            self.assertEqual(result['status'], 'passed')
            self.assertEqual(published.call_count, 1)
            with self.assertRaises(FileExistsError):
                runner.preflight('codex', self.root, execute=execute)

    def test_status_does_not_recover_active_job(self):
        value = packet()
        identifier = runner.job_id('codex', value['packet_id'], 'initial')
        runner.atomic_json(self.root / 'jobs' / identifier / 'started.json', {'pid': 424242})
        result = runner.summary([value], self.root, self.public)
        self.assertEqual(result['packets'][0]['families']['codex']['assessment_statuses']['initial'], 'running')
        self.assertFalse((self.root / 'jobs' / identifier / 'manifest.json').exists())
        group = result['workload_by_stratum_family_round']['wordnet_adjective/codex/initial']
        self.assertIsNone(group['api_equivalent_usd_observed'])
        self.assertEqual(group['priced_job_count'], 0)
        self.assertEqual(group['unpriced_job_count'], 1)
        self.assertEqual(result['terminal_scientific_jobs'], 0)
        self.assertEqual(result['running_scientific_jobs'], 1)

    def test_failed_revision_retains_initial_and_marks_incomplete_counterpart(self):
        value = packet()
        for family, round_name, status in [('codex', 'initial', 'mechanically_valid'),
                                            ('codex', 'revised', 'failed'),
                                            ('claude', 'initial', 'failed'),
                                            ('claude', 'revised', 'failed')]:
            identifier = runner.job_id(family, value['packet_id'], round_name)
            runner.atomic_json(self.root / 'jobs' / identifier / 'manifest.json', {
                'job_id': identifier, 'round': round_name, 'status': status, 'elapsed_seconds': 1})
        runner.atomic_json(self.root / 'augmentation' / (value['packet_id'] + '.json'), {'changed': True})
        result = runner.summary([value], self.root, self.public)['packets'][0]
        self.assertEqual(result['families']['codex']['retained_usable_job_id'], 'wnadj-01__initial__codex')
        self.assertFalse(result['families']['codex']['current_evidence_complete'])
        self.assertTrue(result['families']['claude']['missing_usable_assessment'])
        self.assertFalse(result['completed_both_current_assessments'])

    def test_rate_limit_has_no_job_retry_and_unknown_reset_pauses(self):
        problem = runner.route_problem({'api_error_status': 429}, 'Retry-After: 17')
        self.assertFalse(problem['stop'])
        self.assertAlmostEqual(problem['provider_delay_seconds'], 17)
        self.assertGreater(problem['resume_after_epoch'], time.time())
        self.assertIsNone(runner.route_problem({'api_error_status': 429}, '')['resume_after_epoch'])
        self.assertTrue(runner.route_problem({}, 'quota exhausted')['stop'])

    def test_scheduler_barrier_failed_first_revised_once_and_resume_no_duplicates(self):
        value = packet()
        frozen = {'source_commit': 'abc', 'routes': {f: {'status': 'passed'} for f in runner.MODELS}}
        runner.atomic_json(self.root / 'frozen-instrument.json', frozen)
        initial_finished = threading.Event()
        calls = []
        lock = threading.Lock()
        def job(family, data, round_name, frozen, root):
            if family == 'claude' and round_name == 'initial':
                time.sleep(.03)
                initial_finished.set()
            identifier = runner.job_id(family, data['packet_id'], round_name)
            status = 'failed' if family == 'codex' and round_name == 'initial' else 'mechanically_valid'
            with lock:
                calls.append((family, round_name))
            meta = {'job_id': identifier, 'round': round_name, 'family': family, 'status': status, 'elapsed_seconds': .01}
            runner.atomic_json(root / 'jobs' / identifier / 'answer.json', {'requests': [data['items'][0]['item_id']]})
            runner.atomic_json(root / 'jobs' / identifier / 'manifest.json', meta)
            return meta
        def supplement(data, ids):
            self.assertTrue(initial_finished.is_set())
            self.assertEqual(ids, [data['items'][0]['item_id']])
            data['items'][0]['dictionary_senses'].append({'sense_id': 'new', 'pos': 'a', 'gloss': 'new'})
            return {'packet': data, 'changed': True}
        with patch.object(runner, 'verify_frozen'), patch('production_schema.supplement_requests',
                lambda answer, data: set(answer['requests'])):
            result = runner.run_stage('first', [value], self.root, self.public, job_runner=job, supplement=supplement)
            self.assertEqual(result['dispatched_scientific_jobs'], 4)
            runner.run_stage('first', [value], self.root, self.public, job_runner=job, supplement=supplement)
        self.assertEqual(len(calls), 4)
        self.assertIn(('codex', 'revised'), calls)

    def test_continue_requires_substantive_review_and_hold_persists(self):
        value = packet()
        runner.atomic_json(self.root / 'frozen-instrument.json', {'source_commit': 'abc',
            'routes': {f: {'status': 'passed'} for f in runner.MODELS}})
        with patch.object(runner, 'verify_frozen'):
            result = runner.run_stage('continue', [value], self.root, self.public,
                job_runner=lambda *a: self.fail('Unreviewed route dispatched'))
            self.assertEqual(result['dispatched_scientific_jobs'], 0)
            runner.atomic_json(self.root / 'instrument-hold.json', {'active': True})
            with self.assertRaises(RuntimeError):
                runner.run_stage('continue', [value], self.root, self.public)
        note = self.root / 'review.md'
        note.write_text('Inspected the isolated defect; recorded why no systematic problem remains.')
        runner.clear_hold(note, self.root)
        self.assertFalse(runner.read_json(self.root / 'instrument-hold.json')['active'])


if __name__ == '__main__':
    unittest.main()

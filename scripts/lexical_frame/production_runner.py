"""Durable, subscription-only dispatch for the adopted 200-form lexical batch.

A job is one CLI process, not one underlying model request. Never replay a job
slot. Initial and revised assessments are successive records, not replications.
CLI stages: preflight, freeze, first, review, continue, status.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import copy
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import tempfile
import threading
import time
from typing import Callable

from import_sources import PRIVATE, ROOT, now, published_source, sha

HERE = Path(__file__).resolve().parent
RUN_ROOT = PRIVATE / 'production-20261011-v1'
PUBLIC_ROOT = ROOT / 'results/lexical-frame/production-20261011-v1'
MODELS = {'codex': 'gpt-6.1-sol', 'claude': 'claude-sonnet-5-5'}
CLI = {'codex': '/opt/homebrew/bin/codex', 'claude': '/Users/brettreynolds/.local/bin/claude'}
VERSIONS = {'codex': '0.161.0', 'claude': '2.1.296'}
JOB_SECONDS = 900
MAX_JOBS = 80
LICENSES = ('WORDNET-LICENSE.txt', 'WIKTIONARY-LICENSE.txt')
_LOCK = threading.RLock()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def read_json(path, default=None):
    return json.loads(Path(path).read_text()) if Path(path).exists() else default


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp-' + str(threading.get_ident()))
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n')
    temp.replace(path)


@contextmanager
def stage_lock(root):
    """Only one scheduler/preflight writer; model jobs run concurrently inside it."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    with (root / '.dispatch.lock').open('a') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another production dispatcher is running') from exc
        yield


def scrubbed_env(family):
    env = {'PATH': '/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin',
           'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8'}
    if family == 'claude':
        env.update({key: os.environ[key] for key in ('HOME', 'USER', 'LOGNAME', 'TMPDIR')
                    if key in os.environ})
    return env


def command_for(family, directory, neutral, schema):
    if family == 'codex':
        return [CLI[family], '--sandbox', 'read-only', '--ask-for-approval', 'never', 'exec',
                '--ignore-user-config', '--strict-config', '--ephemeral', '--skip-git-repo-check',
                '--disable', 'shell_tool', '--disable', 'apps', '--disable', 'multi_agent',
                '-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0',
                '-c', 'model_reasoning_effort="high"', '-m', MODELS[family], '--cd', str(neutral),
                '--output-schema', str(directory / 'schema.json'), '-o', str(directory / 'answer.json'), '-']
    return [CLI[family], '--safe-mode', '--tools', '', '--strict-mcp-config',
            '--mcp-config', '{"mcpServers":{}}', '--no-session-persistence', '--setting-sources', '',
            '--model', MODELS[family], '--effort', 'high', '--output-format', 'stream-json',
            '--verbose', '--json-schema', json.dumps(schema), '-p']


# Whitelist the model-facing item envelope; remove known selection variables at
# any nested level without modifying the source text inside string values.
HIDDEN_KEYS = {'stratum', 'selection_stratum', 'source_membership', 'source_row',
               'source_row_position', 'ratings', 'rating', 'valence', 'frequency',
               'commonness', 'detector', 'detector_proposals', 'hypothesis'}


def _strip(value):
    if isinstance(value, dict):
        return {key: _strip(val) for key, val in value.items() if key not in HIDDEN_KEYS}
    if isinstance(value, list):
        return [_strip(val) for val in value]
    return value


def model_packet(packet):
    allowed = {'item_id', 'word', 'dictionary_senses', 'alias_dictionary_senses',
               'coverage', 'sources', 'lookup_mappings', 'category_evidence'}
    return {'packet_id': packet['packet_id'],
            'items': [_strip({key: val for key, val in item.items() if key in allowed})
                      for item in packet['items']]}


def evidence_fingerprint(packet):
    """Only content can authorize another assessment, never retrieval bookkeeping."""
    metadata = {'timestamp', 'retrieved_at', 'access_date', 'status', 'sha256',
                'raw_sha256', 'revision_id', 'revision_timestamp', 'sense_id', 'source_id',
                'url', 'source_url', 'source', 'sources', 'source_address', 'provenance'}

    def content(value):
        if isinstance(value, dict):
            return {k: content(v) for k, v in value.items() if k not in metadata}
        if isinstance(value, list):
            return [content(v) for v in value]
        return value

    return digest([{'item_id': item['item_id'], 'word': item['word'],
                    **{field: content(item.get(field, [])) for field in
                       ('dictionary_senses', 'alias_dictionary_senses', 'category_evidence')}}
                   for item in packet['items']])


def parse_route_logs(family, stdout, stderr):
    """Read partial streams too. Repeated streaming snapshots aren't extra requests."""
    meta = {'returned_model': None, 'request_ids': [], 'assistant_message_ids': [],
            'internal_retries': None, 'schema_repairs': None, 'num_turns': None,
            'usage': None, 'api_equivalent_usd': None, 'underlying_request_count': None}
    answer = None
    if family == 'codex':
        # Restrict identity to the startup header, before the supplied prompt.
        header = stderr.split('\nuser\n', 1)[0]
        models = re.findall(r'^model:\s*(\S+)\s*$', header, re.M)
        meta['returned_model'] = models[0] if models else None
        meta['cli_version'] = next(iter(re.findall(r'^OpenAI Codex v(\S+)', header, re.M)), None)
        meta['reasoning_effort'] = next(iter(re.findall(r'^reasoning effort:\s*(\S+)', header, re.M)), None)
        meta['identity_source'] = 'CLI startup header'
        totals = re.findall(r'^tokens used\s*\n([\d,]+)\s*$', stderr, re.M)
        if totals:
            meta['usage'] = {'reported_total_tokens': int(totals[-1].replace(',', ''))}
        meta['internal_request_observability'] = 'Unknown: this CLI text route exposes no complete request or schema-repair ledger.'
        return meta, answer

    events = []
    malformed = 0
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
            if isinstance(value, dict):
                events.append(value)
        except json.JSONDecodeError:
            malformed += 1
    meta['malformed_stream_lines'] = malformed
    init = next((event for event in events if event.get('type') == 'system' and event.get('subtype') == 'init'), {})
    messages = {}
    requests = set()
    retry_events = []
    for event in events:
        message = event.get('message', {})
        if event.get('type') == 'assistant' and isinstance(message, dict) and message.get('id'):
            messages[message['id']] = {'id': message['id'], 'model': message.get('model'),
                                       'usage': message.get('usage')}
        if event.get('request_id'):
            requests.add(event['request_id'])
        if event.get('type') in ('retry', 'api_retry') or event.get('subtype') in ('retry', 'api_retry'):
            retry_events.append({key: event[key] for key in ('type', 'subtype', 'attempt', 'retry_after', 'status') if key in event})
    ends = [event for event in events if event.get('type') == 'result']
    end = ends[-1] if ends else {}
    meta.update(returned_model=init.get('model'), identity_source='CLI/provider stream metadata',
                assistant_models=sorted({m['model'] for m in messages.values() if m['model']}),
                tools=init.get('tools'), mcp_servers=init.get('mcp_servers'),
                api_key_source=init.get('apiKeySource'), cli_version=init.get('claude_code_version'),
                assistant_message_ids=list(messages), request_ids=sorted(requests),
                assistant_message_usage=list(messages.values()), num_turns=end.get('num_turns'),
                usage=end.get('usage'), model_usage=end.get('modelUsage'),
                api_equivalent_usd=end.get('total_cost_usd'), provider_error=bool(end.get('is_error')),
                api_error_status=end.get('api_error_status'), terminal_reason=end.get('terminal_reason'),
                provider_error_text=end.get('result') if end.get('is_error') else None,
                exposed_retry_events=retry_events,
                internal_request_observability='Distinct assistant message/request IDs are observed lower bounds; hidden retries and schema repairs remain unknown.')
    if retry_events:
        meta['internal_retries'] = {'observed_events': len(retry_events), 'total': None}
    # On failure retain last usage per message, without adding it to aggregate
    # result usage (which can already include those same requests).
    if meta['usage'] is None and messages:
        partial = {}
        for message in messages.values():
            for key, value in (message['usage'] or {}).items():
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    partial[key] = partial.get(key, 0) + value
        meta['partial_observed_usage'] = partial
    if end.get('structured_output') is not None:
        answer = end['structured_output']
    elif end.get('result'):
        try:
            answer = json.loads(end['result'])
        except (TypeError, json.JSONDecodeError):
            pass
    return meta, answer


def route_problem(meta, stderr):
    """Classify transport/client evidence, never dictionary words or model prose."""
    if meta.get('family') == 'codex' and '\nuser\n' in stderr:
        header, transcript = stderr.split('\nuser\n', 1)
        client_lines = [line for line in transcript.splitlines() if re.match(
            r'^(?:ERROR|Error:|WARN|Warning:|Reconnecting|Retrying|HTTP|error:|You have hit your usage limit)', line)]
        stderr = header + '\n' + '\n'.join(client_lines)
    low = (stderr + '\n' + str(meta.get('provider_error_text') or '')).lower()
    status = meta.get('api_error_status')
    if status in (401, 403) or any(x in low for x in ('authentication failed', 'not logged in', 'invalid api key')):
        return {'kind': 'authentication', 'stop': True}
    if any(x in low for x in ('model is not available', 'model not found', 'unsupported model', 'model_not_found')):
        return {'kind': 'model_unavailable', 'stop': True}
    if any(x in low for x in ('quota exceeded', 'quota exhausted', 'usage limit reached', 'insufficient_quota', 'out of extra usage')):
        return {'kind': 'quota', 'stop': True}
    if status == 429 or any(x in low for x in ('rate limit', 'rate_limit', 'too many requests', 'http 429')):
        delay = re.search(r'(?:retry[- _]after|retry in)\s*[:=]?\s*(\d+(?:\.\d+)?)\s*(ms|s|seconds|minutes|m)?', low)
        seconds = None
        if delay:
            seconds = float(delay[1]) * (60 if delay[2] in ('m', 'minutes') else .001 if delay[2] == 'ms' else 1)
        return {'kind': 'rate_limit', 'stop': False,
                'resume_after_epoch': time.time() + seconds if seconds is not None else None,
                'provider_delay_seconds': seconds}
    return None


def execute_once(family, directory, prompt, schema, timeout=JOB_SECONDS, popen=subprocess.Popen):
    """One process-group invocation; kill descendants at the elapsed-time limit."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / 'prompt.txt').write_text(prompt)
    atomic_json(directory / 'schema.json', schema)
    meta = {'started_at': now(), 'requested_model': MODELS[family], 'family': family,
            'job_definition': 'one dispatched CLI invocation; internal request count may exceed one',
            'input_sha256': sha(directory / 'prompt.txt'), 'schema_sha256': sha(directory / 'schema.json'),
            'subscription_route': True, 'timeout_seconds': timeout}
    tic = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='lexical-production-neutral-') as neutral:
        command = command_for(family, directory, neutral, schema)
        meta['command'] = command
        atomic_json(directory / 'started.json', meta)
        with (directory / 'stdout.txt').open('w') as stdout, (directory / 'stderr.txt').open('w') as stderr:
            try:
                proc = popen(command, cwd=neutral, env=scrubbed_env(family), stdin=subprocess.PIPE,
                             stdout=stdout, stderr=stderr, text=True, start_new_session=True)
                meta['pid'] = proc.pid
                atomic_json(directory / 'started.json', meta)
                try:
                    proc.communicate(input=prompt, timeout=max(.01, timeout - (time.monotonic() - tic)))
                    meta['exit_code'] = proc.returncode
                except subprocess.TimeoutExpired:
                    meta['exit_code'] = 'timeout'
                    meta['process_group_terminated'] = True
                    try:
                        os.killpg(proc.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        pass
                    # Kill the group even if its leader exited after SIGTERM.
                    try:
                        os.killpg(proc.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    proc.wait()
            except Exception as exc:
                meta['exit_code'] = 'launch_error'
                meta['error'] = repr(exc)
    meta.update(completed_at=now(), elapsed_seconds=time.monotonic() - tic)
    out = (directory / 'stdout.txt').read_text(errors='replace')
    err = (directory / 'stderr.txt').read_text(errors='replace')
    observed, answer = parse_route_logs(family, out, err)
    meta.update(observed)
    meta['route_problem'] = route_problem(meta, err)
    if family == 'codex':
        try:
            answer = read_json(directory / 'answer.json')
        except (json.JSONDecodeError, OSError):
            pass
    elif answer is not None:
        atomic_json(directory / 'answer.json', answer)
    meta['stdout_bytes'] = len(out.encode())
    meta['answer_bytes'] = (directory / 'answer.json').stat().st_size if (directory / 'answer.json').exists() else None
    meta['status'] = 'returned' if meta['exit_code'] == 0 and not meta.get('provider_error') else 'failed'
    checks = []
    if meta.get('cli_version') != VERSIONS[family]:
        checks.append('runtime CLI version absent or differs from frozen instrument')
    if meta['returned_model'] != MODELS[family]:
        checks.append('returned model identity absent or mismatched')
    if family == 'codex' and meta.get('reasoning_effort') != 'high':
        checks.append('Codex reasoning effort absent or mismatched')
    if family == 'claude':
        if meta.get('tools') is None or set(meta['tools']) - {'StructuredOutput'}:
            checks.append('Claude effective tools absent or not restricted')
        if meta.get('mcp_servers'):
            checks.append('Claude unexpectedly exposes MCP servers')
        if any(model != MODELS[family] for model in meta.get('assistant_models', [])):
            checks.append('provider message model identity mismatched')
        if meta.get('api_key_source') not in (None, 'none', 'claude.ai', 'subscription'):
            checks.append('Claude reports a non-subscription credential source')
    meta['instrument_errors'] = checks
    if checks:
        meta['status'] = 'failed'
        # Unobserved identity after a network failure is not a model substitution.
        if meta.get('exit_code') == 0:
            meta['route_problem'] = {'kind': 'instrument_mismatch', 'stop': True}
    atomic_json(directory / 'process.json', meta)
    return meta, answer


def preflight(family, root=RUN_ROOT, execute=execute_once, source_commit=None):
    commit = source_commit or published_source()
    root = Path(root)
    directory = root / 'preflight' / family
    directory.mkdir(parents=True, exist_ok=False)  # exactly one route check
    schema = {'type': 'object', 'properties': {'ready': {'type': 'boolean'}},
              'required': ['ready'], 'additionalProperties': False}
    prompt = 'Return {"ready":true} in the required structured format. No tools or outside sources. This is a neutral route-format check.'
    try:
        version = subprocess.check_output([CLI[family], '--version'], env=scrubbed_env(family),
                                          cwd=tempfile.gettempdir(), text=True, timeout=20).strip()
        if not re.search(r'(?<!\d)' + re.escape(VERSIONS[family]) + r'(?!\d)', version):
            raise RuntimeError('CLI version differs from adopted instrument: ' + version)
        meta, answer = execute(family, directory, prompt, schema, timeout=120)
        meta['cli_version_output'] = version
        meta['status'] = 'passed' if meta['status'] == 'returned' and answer == {'ready': True} else 'failed'
    except Exception as exc:
        meta = {'family': family, 'status': 'failed', 'error': repr(exc), 'completed_at': now()}
    meta['source_commit'] = commit
    meta['is_scientific_job'] = False
    atomic_json(directory / 'manifest.json', meta)
    return meta


def freeze(packets, root=RUN_ROOT, source_commit=None):
    from production_schema import PRODUCTION_SCHEMA, prompt_text
    root = Path(root)
    target = root / 'frozen-instrument.json'
    if target.exists():
        frozen = read_json(target)
        verify_frozen(frozen, packets, root)
        return frozen
    commit = source_commit or published_source()
    if len(packets) != 20 or any(len(p['items']) != 10 for p in packets):
        raise ValueError('The frozen production design requires twenty ten-form packets')
    counts = {stratum: sum(p['stratum'] == stratum for p in packets)
              for stratum in ('wordnet_adjective', 'category_gap')}
    ids = [item['item_id'] for packet in packets for item in packet['items']]
    if counts != {'wordnet_adjective': 10, 'category_gap': 10} or len(set(ids)) != 200:
        raise ValueError('Production allocation or unique item accounting differs from the adopted design')
    if len({p['packet_id'] for p in packets}) != 20:
        raise ValueError('Packet IDs must be unique')
    routes = {family: read_json(root / 'preflight' / family / 'manifest.json') for family in MODELS}
    if any(value is None for value in routes.values()):
        raise RuntimeError('Complete the two planned neutral route checks before freezing')
    code = {path.name: sha(path) for path in (HERE / 'production_runner.py', HERE / 'production_evidence.py', HERE / 'production_schema.py')}
    frozen = {'frozen_at': now(), 'source_commit': commit, 'models': MODELS, 'cli_versions': VERSIONS,
              'schema_sha256': digest(PRODUCTION_SCHEMA), 'prompt_sha256': hashlib.sha256(prompt_text().encode()).hexdigest(),
              'code_sha256': code, 'packets': {p['packet_id']: digest(p) for p in packets},
              'packet_order': [p['packet_id'] for p in packets],
              'licenses': {name: sha(root / name) for name in LICENSES}, 'routes': routes,
              'scientific_job_limit': MAX_JOBS, 'elapsed_limit_per_job_seconds': JOB_SECONDS,
              'internal_requests': 'Not bounded by the job count; exposed requests, turns, retries, and usage are recorded, otherwise unknown.',
              'python': platform.python_version(), 'platform': platform.platform(),
              'initial_assessments': 40, 'revised_evidence_rounds_max': 1}
    atomic_json(target, frozen)
    return frozen


def verify_frozen(frozen, packets, root):
    from production_schema import PRODUCTION_SCHEMA, prompt_text
    errors = []
    if frozen['packets'] != {p['packet_id']: digest(p) for p in packets}:
        errors.append('packet hashes')
    if frozen['packet_order'] != [p['packet_id'] for p in packets]:
        errors.append('packet order')
    if frozen['schema_sha256'] != digest(PRODUCTION_SCHEMA):
        errors.append('schema')
    if frozen['prompt_sha256'] != hashlib.sha256(prompt_text().encode()).hexdigest():
        errors.append('prompt')
    for name, expected in frozen['code_sha256'].items():
        if sha(HERE / name) != expected:
            errors.append(name)
    for name, expected in frozen['licenses'].items():
        if sha(Path(root) / name) != expected:
            errors.append(name)
    if errors:
        raise RuntimeError('Frozen instrument changed: ' + ', '.join(errors))


def job_id(family, packet_id, round_name):
    if family not in MODELS or round_name not in ('initial', 'revised') or not re.fullmatch(r'[A-Za-z0-9_-]+', packet_id):
        raise ValueError('Invalid job identity')
    return f'{packet_id}__{round_name}__{family}'


def run_job(family, packet, round_name, frozen, root=RUN_ROOT, execute=execute_once,
            validator=None):
    from production_schema import PRODUCTION_SCHEMA, prompt_text, validate
    root = Path(root)
    identifier = job_id(family, packet['packet_id'], round_name)
    if packet['packet_id'] not in frozen.get('packets', {}):
        raise ValueError('Packet is outside the frozen production selection')
    if round_name == 'initial' and digest(packet) != frozen['packets'][packet['packet_id']]:
        raise ValueError('Initial packet differs from its frozen evidence')
    if round_name == 'revised':
        augmented = read_json(root / 'augmentation' / (packet['packet_id'] + '.json'), {})
        if not augmented.get('changed') or digest(augmented.get('packet')) != digest(packet):
            raise ValueError('Revised job lacks the one frozen, genuinely augmented packet')
    directory = root / 'jobs' / identifier
    with _LOCK:
        if len(list((root / 'jobs').glob('*'))) >= MAX_JOBS:
            raise RuntimeError('The 80 dispatched scientific job limit is reached')
        directory.mkdir(parents=True, exist_ok=False)
        # Reservation is durable before spawning: a restart cannot replay it.
        atomic_json(directory / 'reserved.json', {'job_id': identifier, 'reserved_at': now()})
    prompt = prompt_text() + '\n\nEvidence packet:\n' + json.dumps(model_packet(packet), ensure_ascii=False, sort_keys=True)
    for name in LICENSES:
        prompt += '\n\n' + name + '\n' + (root / name).read_text()
    meta, answer = execute(family, directory, prompt, PRODUCTION_SCHEMA)
    meta.update(job_id=identifier, packet_id=packet['packet_id'], round=round_name,
                stratum=packet['stratum'], item_ids=[x['item_id'] for x in packet['items']],
                form_count=len(packet['items']), source_commit=frozen['source_commit'],
                instrument_sha256=digest(frozen), packet_sha256=digest(packet),
                evidence_sha256=evidence_fingerprint(packet), is_scientific_job=True,
                evidence_bytes=len(json.dumps(model_packet(packet), ensure_ascii=False).encode()),
                adjective_sense_count=sum(s.get('pos') in ('a', 's', 'adjective') for x in packet['items'] for s in x.get('dictionary_senses', [])),
                assessment_role='successive assessment; not an independent replication', substantive_review_complete=False)
    if meta['status'] == 'returned':
        try:
            errors = (validator or validate)(answer, packet)
        except Exception as exc:
            errors = ['validator/parse failure: ' + repr(exc)]
        meta['validation_errors'] = errors
        meta['status'] = 'mechanically_valid' if not errors else 'needs_review'
    atomic_json(directory / 'manifest.json', meta)
    return meta


def load_job(root, family, packet_id, round_name, recover=False):
    directory = Path(root) / 'jobs' / job_id(family, packet_id, round_name)
    if not directory.exists():
        return None
    meta = read_json(directory / 'manifest.json')
    if meta is not None:
        return meta
    started = read_json(directory / 'started.json', {})
    if not recover:
        return {**started, 'family': family, 'packet_id': packet_id, 'round': round_name,
                'job_id': directory.name, 'status': 'running', 'is_scientific_job': True}
    if started.get('pid'):
        try:
            os.kill(started['pid'], 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError('Previously dispatched job process is still present; inspect before resuming: ' + directory.name)
    # Preserve partial observations after an interrupted dispatcher; never replay.
    observed, _ = parse_route_logs(family,
        (directory / 'stdout.txt').read_text(errors='replace') if (directory / 'stdout.txt').exists() else '',
        (directory / 'stderr.txt').read_text(errors='replace') if (directory / 'stderr.txt').exists() else '')
    meta = {**started, **observed, 'family': family, 'packet_id': packet_id, 'round': round_name,
            'job_id': directory.name, 'status': 'interrupted', 'completed_at': now(),
            'is_scientific_job': True, 'error': 'Dispatcher ended without a terminal manifest; slot is not rerunnable.'}
    atomic_json(directory / 'manifest.json', meta)
    return meta


def augment_after_barrier(packet, initial, supplement, root=RUN_ROOT, request_reader=None):
    """Both initial attempts must be terminal before the union is retrieved once."""
    from production_schema import supplement_requests
    if set(initial) != set(MODELS) or any(meta is None for meta in initial.values()):
        raise RuntimeError('Initial-attempt barrier has not been reached')
    if any(meta['status'] in ('running', 'pending', 'reserved') for meta in initial.values()):
        raise RuntimeError('Initial-attempt barrier has not been reached')
    root = Path(root)
    record_path = root / 'augmentation' / (packet['packet_id'] + '.json')
    existing = read_json(record_path)
    if existing is not None:
        if existing.get('status') == 'retrieving':
            raise RuntimeError('Interrupted supplement retrieval requires inspection before this packet can continue')
        return existing
    requests = set()
    for meta in initial.values():
        if meta['status'] != 'mechanically_valid':
            continue
        answer = read_json(root / 'jobs' / meta['job_id'] / 'answer.json')
        requests.update((request_reader or supplement_requests)(answer, packet))
    known = {item['item_id']: item for item in packet['items']}
    # A redundant request is not a new evidence round.
    requests = {identifier for identifier in requests if identifier in known and
                known[identifier].get('coverage', {}).get('supplement') == 'not_supplied'}
    record = {'packet_id': packet['packet_id'], 'requested_item_ids': sorted(requests),
              'initial_job_ids': {family: meta.get('job_id') for family, meta in initial.items()},
              'before_evidence_sha256': evidence_fingerprint(packet), 'started_at': now(), 'status': 'retrieving'}
    atomic_json(record_path, record)
    try:
        result = supplement(copy.deepcopy(packet), sorted(requests)) if requests else {'packet': packet, 'unavailable_item_ids': []}
        augmented = result['packet']
        if [i['item_id'] for i in augmented['items']] != [i['item_id'] for i in packet['items']]:
            raise ValueError('Supplement altered packet item identities/order')
        changed = evidence_fingerprint(augmented) != evidence_fingerprint(packet)
        record.update(changed=changed, status='frozen', completed_at=now(),
                      after_evidence_sha256=evidence_fingerprint(augmented),
                      unavailable_item_ids=result.get('unavailable_item_ids', []), packet=augmented)
    except Exception as exc:
        record.update(changed=False, status='failed', error=repr(exc), completed_at=now(), packet=packet)
    atomic_json(record_path, record)
    return record


def approve_first(family, note_path, packets, root=RUN_ROOT, reviewer='Codex analyst'):
    """Root analyst records an actual source-support review, not mere parse success."""
    root = Path(root)
    packet_id = packets[0]['packet_id']
    candidates = [load_job(root, family, packet_id, name) for name in ('revised', 'initial')]
    selected = next((meta for meta in candidates if meta and meta['status'] == 'mechanically_valid'), None)
    if selected is None:
        raise RuntimeError('No mechanically valid first-packet assessment to review')
    note = Path(note_path)
    if not note.is_file() or not note.read_text().strip():
        raise ValueError('A substantive source-support review note is required')
    record = {'family': family, 'job_id': selected['job_id'], 'reviewer': reviewer,
              'reviewed_at': now(), 'note_path': str(note.resolve()), 'note_sha256': sha(note),
              'approved_for_ramp': True, 'coverage': 'all first-packet scope, grouping, and temporal assignments'}
    atomic_json(root / 'first-review' / (family + '.json'), record)
    return record


def event(root, kind, data=None, public_root=PUBLIC_ROOT, notify=False):
    record = {'at': now(), 'kind': kind, **(data or {})}
    # Only caller-selected metadata, never answer text or source evidence.
    with _LOCK:
        for path in (Path(root) / 'events.jsonl', Path(public_root) / 'dispatch-events.jsonl'):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('a') as handle:
                handle.write(json.dumps(record, sort_keys=True) + '\n')
    if notify and kind in ('stage_complete', 'route_stopped', 'instrument_hold', 'supplement_failed'):
        message = {'stage_complete': 'Lexical production stage completed. Review its dispatch status.',
                   'route_stopped': 'A lexical production route stopped. Review its dispatch status.',
                   'instrument_hold': 'Lexical production paused for an instrument review.',
                   'supplement_failed': 'Lexical supplementary evidence failed. Review the preserved failure record.'}[kind]
        subprocess.Popen(['/usr/bin/osascript', '-e', 'display dialog ' + json.dumps(message) +
                          ' with title "Lexical production" buttons {"OK"} default button "OK"'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def summary(packets, root=RUN_ROOT, public_root=PUBLIC_ROOT):
    root = Path(root)
    rows = []
    aggregates = {}
    for packet in packets:
        aug = read_json(root / 'augmentation' / (packet['packet_id'] + '.json'), {})
        final_round = 'revised' if aug.get('changed') else 'initial'
        families = {}
        for family in MODELS:
            assessments = [load_job(root, family, packet['packet_id'], name) for name in ('initial', 'revised')]
            assessments = [meta for meta in assessments if meta]
            usable = [meta for meta in assessments if meta['status'] == 'mechanically_valid']
            current = next((meta for meta in assessments if meta['round'] == final_round), None)
            families[family] = {'assessment_statuses': {m['round']: m['status'] for m in assessments},
                                'retained_usable_job_id': usable[-1]['job_id'] if usable else None,
                                'current_evidence_complete': bool(current and current['status'] == 'mechanically_valid'),
                                'missing_usable_assessment': not bool(usable)}
            for meta in assessments:
                key = packet['stratum'] + '/' + family + '/' + meta['round']
                group = aggregates.setdefault(key, {'dispatched_jobs': 0, 'forms_attempted': 0,
                    'mechanically_valid_jobs': 0, 'terminal_jobs': 0, 'running_jobs': 0,
                    'elapsed_seconds': 0, 'api_equivalent_usd_observed': None,
                    'priced_job_count': 0, 'unpriced_job_count': 0,
                    'usage_observations': [], 'substantive_review_seconds': None})
                group['dispatched_jobs'] += 1
                group['forms_attempted'] += len(packet['items'])
                group['mechanically_valid_jobs'] += meta['status'] == 'mechanically_valid'
                group['terminal_jobs'] += meta['status'] != 'running'
                group['running_jobs'] += meta['status'] == 'running'
                group['elapsed_seconds'] += meta.get('elapsed_seconds', 0)
                if meta.get('api_equivalent_usd') is not None:
                    group['api_equivalent_usd_observed'] = (group['api_equivalent_usd_observed'] or 0) + meta['api_equivalent_usd']
                    group['priced_job_count'] += 1
                else:
                    group['unpriced_job_count'] += 1
                group['usage_observations'].append({'job_id': meta['job_id'], 'usage': meta.get('usage'),
                    'partial_observed_usage': meta.get('partial_observed_usage'),
                    'evidence_bytes': meta.get('evidence_bytes'), 'stdout_bytes': meta.get('stdout_bytes'),
                    'answer_bytes': meta.get('answer_bytes'),
                    'adjective_sense_count': meta.get('adjective_sense_count')})
        rows.append({'packet_id': packet['packet_id'], 'stratum': packet['stratum'],
                     'form_count': len(packet['items']), 'final_evidence_round': final_round,
                     'supplement_requested_forms': len(aug.get('requested_item_ids', [])),
                     'augmentation_status': aug.get('status'),
                     'supplement_unavailable_forms': len(aug.get('unavailable_item_ids', [])),
                     'families': families, 'completed_both_current_assessments':
                     all(info['current_evidence_complete'] for info in families.values())})
    result = {'updated_at': now(), 'selected_forms': sum(len(p['items']) for p in packets),
              'dispatched_scientific_jobs': len(list((root / 'jobs').glob('*'))),
              'terminal_scientific_jobs': sum(g['terminal_jobs'] for g in aggregates.values()),
              'running_scientific_jobs': sum(g['running_jobs'] for g in aggregates.values()),
              'job_limit': MAX_JOBS, 'packets': rows, 'workload_by_stratum_family_round': aggregates,
              'continuation_note': 'Use stratum-specific workload and actual remaining counts after completed work is excluded; no pooled balanced-batch projection. Review and pair-stage costs remain separate.'}
    atomic_json(root / 'dispatch-status.json', result)
    atomic_json(Path(public_root) / 'dispatch-status.json', result)
    return result


def run_stage(stage, packets, root=RUN_ROOT, public_root=PUBLIC_ROOT, notify=False,
              job_runner=run_job, supplement=None):
    """Packet-local barriers; real queued jobs alone explore accepted concurrency."""
    from production_evidence import supplement_packet
    root = Path(root)
    frozen = read_json(root / 'frozen-instrument.json')
    if frozen is None:
        raise RuntimeError('Freeze the instrument before scientific dispatch')
    verify_frozen(frozen, packets, root)
    if stage not in ('first', 'continue'):
        raise ValueError(stage)
    work = packets[:1] if stage == 'first' else packets
    if read_json(root / 'instrument-hold.json', {}).get('active'):
        raise RuntimeError('A durable instrument hold requires analyst inspection and clear-hold before dispatch')
    route_state = read_json(root / 'route-state.json', {})
    capacities = {family: 1 for family in MODELS}
    available = {}
    for family in MODELS:
        state = route_state.setdefault(family, {'stopped': False, 'pause_until': None})
        available[family] = frozen['routes'][family]['status'] == 'passed' and not state['stopped']
        if stage == 'first':
            state.pop('hold', None)
        if stage == 'continue' and available[family]:
            review = read_json(root / 'first-review' / (family + '.json'))
            if not review or not review.get('approved_for_ramp'):
                available[family] = False
                state['hold'] = 'first-packet substantive review required'
            else:
                reviewed_job = load_job(root, family, packets[0]['packet_id'], review['job_id'].split('__')[1])
                if not reviewed_job or reviewed_job['job_id'] != review['job_id'] or reviewed_job['status'] != 'mechanically_valid':
                    raise RuntimeError('First review does not identify a valid first-packet assessment')
                if sha(review['note_path']) != review['note_sha256']:
                    raise RuntimeError('First-packet substantive review note changed')
                state.pop('hold', None)
                capacities[family] = 2
    pending = []
    initial = {packet['packet_id']: {} for packet in work}
    augmented = {}
    packet_by_id = {p['packet_id']: p for p in work}
    for packet in work:
        for family in MODELS:
            meta = load_job(root, family, packet['packet_id'], 'initial', recover=True)
            load_job(root, family, packet['packet_id'], 'revised', recover=True)
            if meta:
                initial[packet['packet_id']][family] = meta
            elif available[family]:
                pending.append((family, packet, 'initial'))
            elif not route_state[family].get('hold'):
                initial[packet['packet_id']][family] = {'status': 'unavailable', 'family': family,
                    'reason': 'route preflight failed or route stopped'}
    active = {}
    held = False
    # Worker count derives from the finite packet design, not account capacity.
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(work) * len(MODELS))) as pool:
        while True:
            for packet_id, attempts in initial.items():
                if set(attempts) != set(MODELS) or packet_id in augmented:
                    continue
                aug = augment_after_barrier(packet_by_id[packet_id], attempts,
                                            supplement or supplement_packet, root)
                augmented[packet_id] = aug
                if aug.get('status') == 'failed':
                    event(root, 'supplement_failed', {'packet_id': packet_id}, public_root, notify)
                elif aug.get('unavailable_item_ids'):
                    event(root, 'supplement_incomplete', {'packet_id': packet_id,
                        'unavailable_forms': len(aug['unavailable_item_ids'])}, public_root)
                if aug.get('changed'):
                    for family in MODELS:
                        if available[family] and not load_job(root, family, packet_id, 'revised'):
                            pending.append((family, aug['packet'], 'revised'))
                    event(root, 'augmented_packet_frozen', {'packet_id': packet_id,
                          'requested_forms': len(aug['requested_item_ids'])}, public_root, notify)
            launched = False
            for entry in pending[:]:
                family, packet, round_name = entry
                state = route_state[family]
                if not available[family] or held:
                    continue
                if state.get('pause_until') == 'unknown' or (state.get('pause_until') or 0) > time.time():
                    continue
                if sum(info[0] == family for info in active.values()) >= capacities[family]:
                    continue
                future = pool.submit(job_runner, family, packet, round_name, frozen, root)
                active[future] = entry
                pending.remove(entry)
                launched = True
                state['peak_concurrent_jobs'] = max(state.get('peak_concurrent_jobs', 0),
                    sum(info[0] == family for info in active.values()))
                event(root, 'job_dispatched', {'family': family, 'packet_id': packet['packet_id'],
                    'round': round_name, 'concurrent_family_jobs': sum(info[0] == family for info in active.values())}, public_root)
            if not active:
                if pending and not held:
                    resumes = [route_state[f].get('pause_until') for f, _, _ in pending if available[f]]
                    known = [value for value in resumes if isinstance(value, (int, float)) and value > time.time()]
                    if known:
                        # This is local event waiting, not LLM-based polling.
                        time.sleep(min(30, max(.01, min(known) - time.time())))
                        continue
                break
            done, _ = concurrent.futures.wait(active, timeout=30,
                                             return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                family, packet, round_name = active.pop(future)
                try:
                    meta = future.result()
                except Exception as exc:
                    meta = load_job(root, family, packet['packet_id'], round_name, recover=True)
                    if meta is None:
                        # No launch took place; stop the instrument rather than
                        # silently filling the queue or retrying the same slot.
                        meta = {'status': 'failed', 'family': family, 'error': repr(exc)}
                    held = True
                    atomic_json(root / 'instrument-hold.json', {'active': True, 'at': now(),
                        'reason': 'dispatcher exception', 'error': repr(exc)})
                if round_name == 'initial':
                    initial[packet['packet_id']][family] = meta
                problem = meta.get('route_problem')
                if problem:
                    if problem.get('stop'):
                        available[family] = False
                        route_state[family].update(stopped=True, reason=problem['kind'])
                        # Other packets may advance with an explicit unavailable
                        # counterpart, while already-dispatched jobs finish.
                        for pending_family, pending_packet, pending_round in pending[:]:
                            if pending_family == family:
                                pending.remove((pending_family, pending_packet, pending_round))
                                if pending_round == 'initial':
                                    initial[pending_packet['packet_id']][family] = {'status': 'unavailable', 'family': family, 'reason': problem['kind']}
                        event(root, 'route_stopped', {'family': family, 'reason': problem['kind']}, public_root, notify)
                    else:
                        route_state[family]['pause_until'] = problem.get('resume_after_epoch') or 'unknown'
                        capacities[family] = max(1, capacities[family] // 2)
                        event(root, 'route_paused', {'family': family, 'resume_after_epoch': problem.get('resume_after_epoch')}, public_root)
                if meta['status'] == 'needs_review':
                    # A validation defect may be systematic. Root must inspect;
                    # no automatic retry or automatic clearance is provided.
                    held = True
                    atomic_json(root / 'instrument-hold.json', {'active': True, 'at': now(),
                        'reason': 'validation defect requires assessment of systematic risk',
                        'job_id': meta.get('job_id')})
                    event(root, 'instrument_hold', {'family': family, 'packet_id': packet['packet_id']}, public_root, notify)
                elif meta['status'] == 'mechanically_valid' and stage == 'continue':
                    capacities[family] += 1
                atomic_json(root / 'route-state.json', route_state)
                event(root, 'job_terminal', {'family': family, 'packet_id': packet['packet_id'],
                    'round': round_name, 'status': meta['status']}, public_root)
                summary(packets, root, public_root)
            # On a hold finish active jobs but retain the pending-slot count.
    atomic_json(root / 'route-state.json', route_state)
    result = summary(packets, root, public_root)
    result['stage'] = stage
    result['instrument_hold'] = held
    result['pending_dispatch_slots'] = len(pending)
    atomic_json(root / (stage + '-stage.json'), result)
    event(root, 'stage_complete', {'stage': stage, 'scientific_jobs': result['dispatched_scientific_jobs'],
          'instrument_hold': held, 'pending_dispatch_slots': len(pending)}, public_root, notify)
    return result


def clear_hold(note_path, root=RUN_ROOT):
    """Analyst-only clearance after documenting why no systematic defect remains."""
    root = Path(root)
    note = Path(note_path)
    hold = read_json(root / 'instrument-hold.json', {})
    if not hold.get('active'):
        raise RuntimeError('No active instrument hold')
    if not note.is_file() or not note.read_text().strip():
        raise ValueError('A substantive defect review note is required')
    hold.update(active=False, cleared_at=now(), review_note=str(note.resolve()), note_sha256=sha(note))
    atomic_json(root / 'instrument-hold.json', hold)
    return hold


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('preflight', 'freeze', 'first', 'review', 'continue', 'status', 'clear-hold'))
    parser.add_argument('--family', choices=(*MODELS, 'both'), default='both')
    parser.add_argument('--root', type=Path, default=RUN_ROOT)
    parser.add_argument('--public-root', type=Path, default=PUBLIC_ROOT)
    parser.add_argument('--review-note', type=Path)
    parser.add_argument('--notify', action='store_true', help='Emit persistent macOS dialogs for major events')
    args = parser.parse_args()
    families = list(MODELS) if args.family == 'both' else [args.family]
    with stage_lock(args.root):
        if args.stage == 'clear-hold':
            if not args.review_note:
                parser.error('clear-hold requires --review-note with the defect assessment')
            result = clear_hold(args.review_note, args.root)
        elif args.stage == 'preflight':
            result = {family: preflight(family, args.root) for family in families}
        else:
            from production_evidence import build_packets
            packets = build_packets()
            if args.stage == 'freeze':
                result = freeze(packets, args.root)
            elif args.stage in ('first', 'continue'):
                # published_source verifies this checked-out implementation is
                # committed and published before any scientific invocation.
                commit = published_source()
                frozen = read_json(args.root / 'frozen-instrument.json', {})
                if frozen.get('source_commit') != commit:
                    raise RuntimeError('Source commit differs from frozen instrument')
                result = run_stage(args.stage, packets, args.root, args.public_root, args.notify)
            elif args.stage == 'review':
                if not args.review_note:
                    parser.error('review requires --review-note with the completed source-support review')
                result = {family: approve_first(family, args.review_note, packets, args.root) for family in families}
            else:
                result = summary(packets, args.root, args.public_root)
        print(json.dumps({'stage': args.stage, 'recorded': True,
                          'status': {f: r.get('status') for f, r in result.items() if f in MODELS} if isinstance(result, dict) else None}, sort_keys=True))


if __name__ == '__main__':
    main()

"""Attempt-preserving H2 orchestration repair; the frozen scientific worker is unchanged."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import threading
import time
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from common import ROOT, dump, sha, utc
from empirical import all_jobs, check_bundle, job_info
from remote_batch import ALLOWED, CHUNK, Registry, handler, request, verify_result, worker_command

FIRST = 'nicolas-s0-c0'
IMPORTED = 'nicolas-s0-c1'
STALE_SECONDS = 180


def timestamp(value):
    return datetime.fromisoformat(value).timestamp()


def process_evidence(row, now=None, provider_stage='RUNNING'):
    """Assignments never constitute evidence that a child is currently alive."""
    if row['state'] != 'running':
        return row['state']
    if provider_stage not in ('RUNNING', 'PENDING', 'STARTING'):
        return 'provider_terminated_unverified'
    heartbeat = row.get('heartbeat')
    if not heartbeat:
        return 'assigned_no_process_evidence'
    if heartbeat.get('returncode') is not None or not heartbeat.get('child_alive', False):
        return 'child_exited_pending_export'
    age = (time.time() if now is None else now) - timestamp(heartbeat['received_at'])
    return 'recent_process_evidence' if age <= STALE_SECONDS else 'stale_process_evidence'


class RecoveryRegistry(Registry):
    def __init__(self, path, meta, original, mode, deadline, bundle_hash):
        if mode not in ('mixed', 'hf'):
            raise ValueError('Unknown recovery mode')
        if path.exists():
            raise RuntimeError('Recovery register exists; no automatic restart or reassignment')
        old = json.loads((original / 'register.json').read_text())
        if old['jobs'][FIRST]['state'] != 'failed' or old['jobs'][IMPORTED]['state'] != 'complete':
            raise ValueError('Original attempts have not reached the authorized recovery boundary')
        if any(row['state'] == 'running' for row in old['jobs'].values()):
            raise ValueError('An original attempt is still assigned as running')
        if any(row['state'] != 'unassigned' for job, row in old['jobs'].items()
               if job not in (FIRST, IMPORTED)):
            raise ValueError('Unexpected original attempts; reconcile before recovery')
        for job in (FIRST, IMPORTED):
            folder = original / job
            fit = verify_result(folder, meta)
            if sha(folder / 'manifest.json') != old['jobs'][job]['manifest_sha256']:
                raise ValueError('Original manifest changed')
            if fit['bundle_sha256'] != bundle_hash:
                raise ValueError('Original input bundle mismatch')
        self.path, self.meta, self.lock = path, meta, threading.RLock()
        jobs = {job: dict(state='unassigned', owner=None, attempt=1) for job in all_jobs()}
        jobs[FIRST].update(attempt=2, previous_attempt=dict(attempt=1, state='failed',
            archive=str(original / FIRST), manifest_sha256=old['jobs'][FIRST]['manifest_sha256']))
        jobs[IMPORTED] = dict(old['jobs'][IMPORTED], attempt=1, imported=True,
            original_archive=str(original / IMPORTED))
        self.data = dict(started_at=utc(), phase='initial', mode=mode, jobs=jobs,
            deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat(),
            input_bundle_sha256=bundle_hash, original_register_sha256=sha(original / 'register.json'),
            automatic_retries=False, authorized_replacement=FIRST,
            orchestration_sha256=sha(Path(__file__)))
        path.parent.mkdir(parents=True, exist_ok=True)
        # Copy only verified outputs; the original archive and attempt history remain intact.
        manifest = json.loads((original / IMPORTED / 'manifest.json').read_text())
        destination = path.parent / IMPORTED
        destination.mkdir(exist_ok=False)
        for name in [*manifest['files'], 'manifest.json']:
            shutil.copy2(original / IMPORTED / name, destination / name)
        verify_result(destination, meta)
        self.save()

    def claim(self, owner):
        allowed = ('hf-1', 'hf-2', 'claude-1') if self.data['mode'] == 'mixed' else ('hf-1', 'hf-2')
        if owner not in allowed:
            raise ValueError('Worker not enabled for this recovery')
        with self.lock:
            active = [j for j, r in self.data['jobs'].items() if r['owner'] == owner and r['state'] == 'running']
            if active:
                return dict(action='already_running', job=active[0])
            if time.time() >= timestamp(self.data['deadline']):
                return dict(action='stop', reason='Approved resource boundary')
            if self.data['phase'] == 'initial':
                initial_owner = 'claude-1' if self.data['mode'] == 'mixed' else 'hf-1'
                if owner != initial_owner or self.data['jobs'][FIRST]['state'] != 'unassigned':
                    return dict(action='wait')
                job = FIRST
            elif self.data['phase'] != 'released':
                return dict(action='stop', reason='Recorded initial failure or resource boundary')
            else:
                job = next((j for j, r in self.data['jobs'].items() if r['state'] == 'unassigned'), None)
                if job is None:
                    return dict(action='stop', reason='No unassigned jobs')
            self.data['jobs'][job].update(state='running', owner=owner, started_at=utc())
            self.save()
            return dict(action='fit', job=job, attempt=self.data['jobs'][job]['attempt'],
                        deadline=self.data['deadline'])

    def heartbeat(self, job, owner, event):
        with self.lock:
            self.owner(job, owner)
            permitted = {'at', 'pid', 'child_alive', 'returncode', 'elapsed_seconds', 'sampler', 'phase', 'error'}
            if set(event) - permitted or not isinstance(event.get('child_alive'), bool):
                raise ValueError('Invalid process heartbeat')
            row = dict(event, received_at=utc())
            self.data['jobs'][job]['heartbeat'] = row
            with (self.path.parent / (job + '-heartbeats.jsonl')).open('a') as stream:
                stream.write(json.dumps(row) + '\n')
            self.save()
            return dict(recorded=True, stop=time.time() >= timestamp(self.data['deadline']))

    def finish(self, job, owner, folder):
        with self.lock:
            super().finish(job, owner, folder)
            self.data['jobs'][job]['archive_verified_at'] = utc()
            self.save()


def failure_receipt(folder, meta, job, owner, bundle_hash, error, exit_status, elapsed):
    """Retain the worker's prior receipt alongside an honest supervisor failure receipt."""
    folder.mkdir(parents=True, exist_ok=True)
    previous = None
    if (folder / 'fit.json').exists():
        previous = json.loads((folder / 'fit.json').read_text())
        dump(folder.parent / (job + '-worker-receipt-before-supervisor.json'), previous)
    if (folder / 'manifest.json').exists():
        shutil.copy2(folder / 'manifest.json', folder.parent / (job + '-worker-manifest-before-supervisor.json'))
    record = dict(job=job_info(job), owner=owner, state='failed', source_hashes=meta['source_hashes'],
        bundle_sha256=bundle_hash, started_at=previous.get('started_at') if previous else None,
        ended_at=utc() if exit_status is not None else None, reported_at=utc(),
        elapsed_seconds=elapsed, exit_status=exit_status, error=error,
        previous_worker_receipt=previous, infrastructure_failure=True)
    dump(folder / 'fit.json', record)
    dump(folder / 'manifest.json', dict(job=job, state='failed', files={
        p.name: dict(bytes=p.stat().st_size, sha256=sha(p)) for p in folder.iterdir()
        if p.is_file() and p.name in ALLOWED}))


def supervise(command, folder, callback, deadline, interval=30, stop=None):
    """Observe a real child, capture its exit, and never restart it."""
    folder.parent.mkdir(parents=True, exist_ok=True)
    lock = folder.parent / (folder.name + '-launch.lock')
    with lock.open('x') as stream:
        stream.write(utc() + '\n')
    if folder.exists():
        raise RuntimeError('Attempt output already exists')
    start = time.monotonic()
    process = None
    error = None
    record = dict(at=utc(), phase='starting', child_alive=False, pid=None, returncode=None, elapsed_seconds=0)
    receipt = folder.parent / (folder.name + '-process.json')

    def emit():
        record.update(at=utc(), elapsed_seconds=time.monotonic() - start,
                      child_alive=process.poll() is None, pid=process.pid, returncode=process.returncode)
        progress = folder / 'progress.json'
        if progress.exists():
            record['sampler'] = json.loads(progress.read_text())
        dump(receipt, record)
        response = callback(dict(record))
        return bool(response and response.get('stop'))

    try:
        with (folder.parent / (folder.name + '-stdout.txt')).open('xb') as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
            record['phase'] = 'running'
            while True:
                requested_stop = emit()
                if process.returncode is not None:
                    break
                if requested_stop or time.time() >= deadline or (stop is not None and stop.is_set()):
                    raise TimeoutError('Approved resource boundary or supervisor shutdown')
                try:
                    process.wait(timeout=min(interval, max(.01, deadline-time.time())))
                except subprocess.TimeoutExpired:
                    pass
    except BaseException as exc:
        error = repr(exc)
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        record.update(at=utc(), phase='exited', child_alive=False,
                      returncode=process.returncode if process else None,
                      elapsed_seconds=time.monotonic()-start)
        if error:
            record['error'] = error
        dump(receipt, record)
        try:
            callback(dict(record))
        except Exception as exc:
            record['final_heartbeat_error'] = repr(exc)
            dump(receipt, record)
    return record


def finalize_child(folder, record, meta, job, owner, bundle_hash):
    reason = record.get('error')
    try:
        if record['returncode'] != 0:
            raise RuntimeError('Observed child exit status: ' + str(record['returncode']))
        if reason:
            raise RuntimeError(reason)
        fit = verify_result(folder, meta)
        if fit['state'] != 'complete' or fit['owner'] != owner or fit['bundle_sha256'] != bundle_hash:
            raise ValueError('Worker result does not match the assigned attempt')
    except Exception as exc:
        failure_receipt(folder, meta, job, owner, bundle_hash, reason or repr(exc),
                        record['returncode'], record['elapsed_seconds'])
    return verify_result(folder, meta)


def local_worker(owner, reg, inputs, outputs, stop):
    while not stop.is_set():
        assignment = reg.claim(owner)
        if assignment['action'] == 'wait':
            stop.wait(10)
            continue
        if assignment['action'] != 'fit':
            return
        job = assignment['job']
        folder = outputs / job
        try:
            record = supervise(worker_command(inputs, folder, job, owner), folder,
                lambda value: reg.heartbeat(job, owner, value), timestamp(assignment['deadline']), stop=stop)
            fit = finalize_child(folder, record, reg.meta, job, owner, sha(inputs / 'bundle.json'))
            reg.finish(job, owner, folder)
            if fit['state'] == 'failed':
                return
        except BaseException as exc:
            reg.failed_before_receipt(job, owner, 'Orchestration error: ' + repr(exc))
            return


def recovery_handler(reg, inputs, outputs, tokens):
    base = handler(reg, inputs, outputs, tokens)

    class Handler(base):
        def do_POST(self):
            if not self.path.startswith('/heartbeat/'):
                return super().do_POST()
            try:
                owner = self.auth()
                match = re.fullmatch(r'/heartbeat/((?:uwa|nicolas)-s[0-3]-c[0-7])', self.path)
                if not match:
                    raise ValueError('Invalid heartbeat path')
                self.respond(200, reg.heartbeat(match.group(1), owner, json.loads(self.body(16384))))
            except PermissionError:
                self.respond(403, {'error': 'Unauthorized'})
            except Exception as exc:
                self.respond(400, {'error': str(exc)})
    return Handler


def upload(folder, url, owner, secret):
    manifest = json.loads((folder / 'manifest.json').read_text())
    job = manifest['job']
    for name in manifest['files']:
        with (folder / name).open('rb') as stream:
            part = 0
            while data := stream.read(CHUNK):
                request(url, owner, secret, f'/part/{job}/{name}/{part:05d}', data, 'PUT',
                        {'X-Content-SHA256': hashlib.sha256(data).hexdigest()})
                part += 1
    response = json.loads(request(url, owner, secret, '/finish/' + job, json.dumps(manifest).encode(), 'POST'))
    if not response['verified']:
        raise RuntimeError('Private remote archive did not verify')


def cloud_worker(url, secret_file, bundle_hash, work):
    owner = 'claude-1'
    secret = secret_file.read_text().strip()
    work.mkdir(parents=True, exist_ok=False)
    archive = work / 'inputs.tar.gz'
    archive.write_bytes(request(url, owner, secret, '/inputs'))
    inputs = work / 'inputs'
    inputs.mkdir()
    with tarfile.open(archive) as tar:
        if any(not m.isfile() or Path(m.name).name != m.name for m in tar.getmembers()):
            raise ValueError('Unsafe input archive')
        tar.extractall(inputs, filter='data')
    if sha(inputs / 'bundle.json') != bundle_hash:
        raise ValueError('Wrong frozen input bundle')
    meta = check_bundle(inputs)
    while True:
        assignment = json.loads(request(url, owner, secret, '/claim', b'{}', 'POST'))
        if assignment['action'] == 'wait':
            time.sleep(30)
            continue
        if assignment['action'] != 'fit':
            print(json.dumps(assignment), flush=True)
            return
        job = assignment['job']
        folder = work / 'outputs' / job
        print(json.dumps(dict(event='assigned', **assignment)), flush=True)
        callback = lambda event: json.loads(request(url, owner, secret, '/heartbeat/' + job,
                                                     json.dumps(event).encode(), 'POST'))
        record = supervise(worker_command(inputs, folder, job, owner), folder, callback,
                           timestamp(assignment['deadline']))
        fit = finalize_child(folder, record, meta, job, owner, bundle_hash)
        upload(folder, url, owner, secret)
        print(json.dumps(dict(event='archive_verified', job=job, state=fit['state'], at=utc())), flush=True)
        # Remove only the verified remote duplicate. Process evidence and stdout remain.
        shutil.rmtree(folder)
        if fit['state'] == 'failed':
            return


def serve(inputs, outputs, original, secrets_file, mode, deadline, port):
    meta = check_bundle(inputs)
    reg = RecoveryRegistry(outputs / 'register.json', meta, original, mode, deadline, sha(inputs / 'bundle.json'))
    tokens = json.loads(secrets_file.read_text()) if mode == 'mixed' else {}
    if mode == 'mixed' and (set(tokens) != {'claude-1'} or len(tokens['claude-1']) < 40):
        raise ValueError('Expected one restricted Claude capability')
    archive = inputs.parent / 'inputs.tar.gz'
    if not archive.exists():
        with tarfile.open(archive, 'w:gz') as tar:
            for path in sorted(inputs.iterdir()):
                tar.add(path, arcname=path.name)
    server = ThreadingHTTPServer(('0.0.0.0', port), recovery_handler(reg, inputs, outputs, tokens)) if mode == 'mixed' else None
    if server:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    stop = threading.Event()
    workers = [threading.Thread(target=local_worker, args=(owner, reg, inputs, outputs, stop), daemon=True)
               for owner in ('hf-1', 'hf-2')]
    for worker in workers:
        worker.start()
    try:
        while True:
            with reg.lock:
                counts = {state: sum(r['state'] == state for r in reg.data['jobs'].values())
                          for state in ('unassigned', 'running', 'complete', 'failed')}
                evidence = {job: process_evidence(row) for job, row in reg.data['jobs'].items() if row['state'] == 'running'}
                snapshot = dict(at=utc(), phase=reg.data['phase'], counts=counts, process_evidence=evidence,
                                orchestration_sha256=sha(Path(__file__)))
                dump(outputs / 'server.json', snapshot)
                print(json.dumps(snapshot), flush=True)
                if not counts['running'] and (not counts['unassigned'] or reg.data['phase'] == 'blocked'):
                    break
            if time.time() >= deadline:
                stop.set()
                break
            stop.wait(30)
    finally:
        stop.set()
        for worker in workers:
            worker.join(timeout=45)
        if time.time() >= deadline:
            with reg.lock:
                reg.data['phase'] = 'resource_boundary'
                for job, row in reg.data['jobs'].items():
                    if row['state'] == 'running':
                        row.update(state='failed', reported_at=utc(), ended_at=None,
                            error='Resource boundary reached without verified terminal export; process end time unknown',
                            last_process_evidence=process_evidence(row))
                reg.save()
        if server:
            server.shutdown()
            server.server_close()


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='command', required=True)
    item = sub.add_parser('serve')
    for name in ('inputs', 'outputs', 'original', 'secrets-file'):
        item.add_argument('--' + name, type=Path, required=True)
    item.add_argument('--mode', choices=['mixed', 'hf'], required=True)
    item.add_argument('--deadline', type=float, required=True)
    item.add_argument('--port', type=int, default=8000)
    item = sub.add_parser('cloud')
    item.add_argument('--url', required=True)
    item.add_argument('--secret-file', type=Path, required=True)
    item.add_argument('--bundle-hash', required=True)
    item.add_argument('--work', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'serve':
        serve(args.inputs, args.outputs, args.original, args.secrets_file, args.mode, args.deadline, args.port)
    else:
        cloud_worker(args.url, args.secret_file, args.bundle_hash, args.work)


if __name__ == '__main__':
    main()

"""Continue only the 59 unstarted H2 jobs, preserving five verified exports."""
from __future__ import annotations
import argparse
import copy
import json
import shutil
import threading
from datetime import datetime, timezone
from pathlib import Path
from common import dump, sha, utc
from empirical import all_jobs, check_bundle
from recovery import RecoveryRegistry, serve_registry
from verify_archive import verify_result

IMPORTED = {'nicolas-s0-c0', 'nicolas-s0-c1', 'uwa-s0-c0', 'uwa-s0-c1', 'uwa-s0-c2'}
RECONCILED = {'uwa-s0-c0', 'uwa-s0-c1', 'uwa-s0-c2'}


class ContinuationRegistry(RecoveryRegistry):
    def __init__(self, path, meta, original, proof_path, proof_hash, deadline, bundle_hash):
        if path.exists() or path.parent.exists():
            raise RuntimeError('Continuation destination exists; never restart or duplicate blindly')
        proof = json.loads(proof_path.read_text())
        old_path = original / 'register.json'
        old = json.loads(old_path.read_text())
        if (sha(proof_path) != proof_hash or proof['state'] != 'verified'
                or proof['original_register_sha256'] != sha(old_path)
                or proof['bundle_sha256'] != bundle_hash
                or proof['source_hashes'] != meta['source_hashes']
                or set(proof['jobs']) != RECONCILED or set(old['jobs']) != set(all_jobs())
                or old['input_bundle_sha256'] != bundle_hash
                or old['phase'] != 'released'):
            raise ValueError('Continuation proof does not bind the stopped register and inputs')
        if deadline > datetime.fromisoformat(old['deadline']).timestamp():
            raise ValueError('Continuation cannot extend the approved deadline')
        for job, row in old['jobs'].items():
            expected = 'failed' if job in RECONCILED else 'complete' if job in IMPORTED else 'unassigned'
            if row['state'] != expected or (expected == 'unassigned' and (row['owner'] is not None or row['attempt'] != 1)):
                raise ValueError('Unexpected or already-started job: ' + job)
        fits = {}
        for job in sorted(IMPORTED):
            folder = original / job
            row = old['jobs'][job]
            fit = verify_result(folder, meta)
            if (sha(folder/'manifest.json') != row['manifest_sha256'] or fit['owner'] != row['owner']
                    or fit['bundle_sha256'] != bundle_hash):
                raise ValueError('Imported archive differs from stopped register: ' + job)
            if job in RECONCILED:
                evidence = proof['jobs'][job]
                previous = fit.get('previous_worker_receipt', {})
                if (evidence['original_row'] != row
                        or evidence['original_manifest_sha256'] != row['manifest_sha256']
                        or evidence['original_failure_receipt_sha256'] != sha(folder/'fit.json')
                        or fit.get('error') != "ValueError('Wrong summary budget/source')"
                        or fit.get('exit_status') != 0 or fit.get('infrastructure_failure') is not True
                        or previous.get('state') != 'complete'
                        or previous.get('job') != fit['job'] or previous.get('owner') != fit['owner']
                        or previous.get('source_hashes') != meta['source_hashes']
                        or previous.get('bundle_sha256') != bundle_hash):
                    raise ValueError('Not the verified UWA rejection: ' + job)
                fits[job] = previous
            else:
                if fit['state'] != 'complete':
                    raise ValueError('Imported Nicolas fit is incomplete')
                fits[job] = fit
        # Copy into a new namespace. The old register and all original archives stay intact.
        path.parent.mkdir(parents=True)
        jobs = copy.deepcopy(old['jobs'])
        for job in sorted(IMPORTED):
            folder, destination = original/job, path.parent/job
            destination.mkdir()
            manifest = json.loads((folder/'manifest.json').read_text())
            for name in [*manifest['files'], 'manifest.json']:
                shutil.copy2(folder/name, destination/name)
            if job in RECONCILED:
                dump(destination/'fit.json', fits[job])
                evidence = proof['jobs'][job]
                if sha(destination/'fit.json') != evidence['restored_worker_receipt_sha256']:
                    raise ValueError('Restored worker receipt changed')
                dump(destination/'manifest.json', evidence['completed_view_manifest'])
                if sha(destination/'manifest.json') != evidence['completed_view_manifest_sha256']:
                    raise ValueError('Reconciled manifest changed')
                jobs[job].update(original_registration=copy.deepcopy(old['jobs'][job]),
                                 verification_reconciliation_sha256=proof_hash)
            verified = verify_result(destination, meta)
            if verified['state'] != 'complete':
                raise ValueError('Imported output did not pass completed-output checks')
            jobs[job].update(state='complete', manifest_sha256=sha(destination/'manifest.json'),
                             elapsed_seconds=fits[job]['elapsed_seconds'], imported=True,
                             original_archive=str(folder), archive_verified_at=utc())
        self.path, self.meta, self.lock = path, meta, threading.RLock()
        self.data = dict(started_at=utc(), phase='released', mode='mixed', jobs=jobs,
            deadline=datetime.fromtimestamp(deadline, timezone.utc).isoformat(),
            input_bundle_sha256=bundle_hash, original_register_sha256=sha(old_path),
            verification_reconciliation_sha256=proof_hash, automatic_retries=False,
            authorized_replacement=None, imported_components=sorted(IMPORTED),
            unstarted_components_to_run=59, initial_timings=old.get('initial_timings'),
            orchestration_sha256=sha(Path(__file__)), original_orchestration_sha256=old['orchestration_sha256'])
        self.save()


def main():
    parser = argparse.ArgumentParser()
    for name in ('inputs', 'outputs', 'original', 'proof', 'secrets-file'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--proof-sha', required=True)
    parser.add_argument('--deadline', type=float, required=True)
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    meta = check_bundle(args.inputs)
    reg = ContinuationRegistry(args.outputs/'register.json', meta, args.original,
                               args.proof, args.proof_sha, args.deadline, sha(args.inputs/'bundle.json'))
    serve_registry(reg, args.inputs, args.outputs, args.secrets_file, 'mixed', args.deadline, args.port)


if __name__ == '__main__':
    main()

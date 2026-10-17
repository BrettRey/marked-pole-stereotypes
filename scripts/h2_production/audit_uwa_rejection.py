"""Audit the three saved UWA exports rejected by the Nicolas-only budget check.

Reads real exports; fits nothing, changes no archive or register, and never
submits a job. Temporary views restore the preserved worker receipt solely to
exercise all completed-output checks rather than the failure-receipt checks.
"""
from __future__ import annotations
import json
import os
import tempfile
import zipfile
from pathlib import Path
from common import ROOT, dump, sha, utc
from empirical import check_bundle, job_info
from verify_archive import verify_result


def audit():
    base = ROOT / 'private/h2-recovery-20261016'
    inputs = base / 'inputs'
    meta = check_bundle(inputs)
    register_path = base / 'live-register.json'
    register = json.loads(register_path.read_text())
    rows = {}
    for job in ('uwa-s0-c0', 'uwa-s0-c1', 'uwa-s0-c2'):
        folder = base / 'collected' / job
        original = json.loads((folder / 'manifest.json').read_text())
        fit = verify_result(folder, meta)  # Includes every original file hash.
        row = register['jobs'][job]
        previous = fit.get('previous_worker_receipt', {})
        if (row['state'] != 'failed' or row['manifest_sha256'] != sha(folder / 'manifest.json')
                or fit.get('error') != "ValueError('Wrong summary budget/source')"
                or fit.get('infrastructure_failure') is not True or fit.get('exit_status') != 0
                or previous.get('state') != 'complete' or previous.get('job') != job_info(job)
                or previous.get('owner') != row['owner']
                or previous.get('source_hashes') != meta['source_hashes']
                or previous.get('bundle_sha256') != sha(inputs / 'bundle.json')):
            raise ValueError('Not the known summary-check incident: ' + job)
        with tempfile.TemporaryDirectory(prefix='h2-uwa-archive-audit-') as temporary:
            view = Path(temporary)
            for name in original['files']:
                if name != 'fit.json':
                    os.link(folder / name, view / name)
            dump(view / 'fit.json', previous)
            files = dict(original['files'])
            files['fit.json'] = dict(bytes=(view / 'fit.json').stat().st_size,
                                     sha256=sha(view / 'fit.json'))
            completed = dict(original, state='complete', files=files)
            dump(view / 'manifest.json', completed)
            verify_result(view, meta)
            receipt = json.loads((view / 'summary-receipt.json').read_text())
            predictions = json.loads((view / 'predictive-replications.json').read_text())
            if len(predictions['joint']) != 200 or predictions['conditional_history'] != []:
                raise ValueError('Wrong saved UWA predictive replications')
            with zipfile.ZipFile(view / 'posterior.npz') as archive:
                if archive.testzip() is not None:
                    raise ValueError('Posterior CRC failure')
                member_count = len(archive.namelist())
            rows[job] = dict(state='verified_completed_worker_output', original_row=row,
                original_manifest_sha256=sha(folder / 'manifest.json'),
                original_failure_receipt_sha256=sha(folder / 'fit.json'),
                restored_worker_receipt_sha256=sha(view / 'fit.json'),
                completed_view_manifest_sha256=sha(view / 'manifest.json'),
                completed_view_manifest=completed,
                all_original_file_hashes_match=True, posterior_zip_crc=True,
                posterior_array_count=member_count, posterior_shape_prefix=[4, 1000],
                contrast_draws=receipt['contrast_draws'], joint_replications=200,
                conditional_replications=0, scientific_elapsed_seconds=previous['elapsed_seconds'],
                diagnostics=json.loads((view / 'diagnostics.json').read_text()))
        if sha(folder / 'manifest.json') != row['manifest_sha256']:
            raise ValueError('Original archive changed during audit')
    result = dict(at=utc(), state='verified', jobs=rows,
        original_register_sha256=sha(register_path), source_hashes=meta['source_hashes'],
        bundle_sha256=sha(inputs / 'bundle.json'), verifier_sha256=sha(Path(__file__).with_name('verify_archive.py')),
        audit_script_sha256=sha(Path(__file__)), fits_launched=0, original_archives_modified=False,
        remote_register_modified=False,
        scope='Saved worker outputs verified; remote failure registrations remain unchanged. No complete eight-component cut exists.')
    target = ROOT / 'results/h2-recovery-20261016/uwa-summary-reconciliation.json'
    dump(target, result)
    print(json.dumps(dict(at=result['at'], state=result['state'], verified_jobs=list(rows),
                         fits_launched=0, original_archives_modified=False)))


if __name__ == '__main__':
    audit()

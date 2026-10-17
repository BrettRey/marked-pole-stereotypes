"""Operational archive checks using public NumPy APIs; no model or data changes."""
from __future__ import annotations
import json
import zipfile
import numpy as np
from common import sha
from empirical import job_info
from remote_batch import ALLOWED

VERIFIER_ERROR = "Result verification failed: module 'numpy.lib.format' has no attribute '_read_array_header'"


def reconciled_register(register_path, proof_path=None):
    """Return an audited view; never overwrite the original provider register."""
    register = json.loads(register_path.read_text())
    if proof_path is None or not proof_path.exists():
        return register
    proof = json.loads(proof_path.read_text())
    job = 'nicolas-s0-c1'
    row = register['jobs'][job]
    if (proof['state'] != 'verified' or proof['job'] != job
            or proof['original_register_sha256'] != sha(register_path)
            or proof['original_row'] != row or row.get('error') != VERIFIER_ERROR
            or row['state'] != 'failed' or row['owner'] != 'hf-1'
            or proof['all_file_hashes_match'] is not True
            or proof['posterior_zip_crc'] is not True):
        raise ValueError('Invalid original verification reconciliation')
    register['jobs'][job] = dict(row, state='complete',
        manifest_sha256=proof['manifest_sha256'], elapsed_seconds=proof['fit_elapsed_seconds'],
        ended_at=proof['fit_ended_at'], original_registration=dict(row),
        reconciliation_sha256=sha(proof_path))
    register['verification_reconciliation_sha256'] = sha(proof_path)
    return register


def posterior_header(stream):
    version = np.lib.format.read_magic(stream)
    readers = {(1, 0): np.lib.format.read_array_header_1_0,
               (2, 0): np.lib.format.read_array_header_2_0}
    if version not in readers:
        raise ValueError(f'Unsupported posterior NPY version: {version}')
    shape, fortran, dtype = readers[version](stream)
    if shape[:2] != (4, 1000) or dtype.hasobject or dtype.kind not in 'biufc':
        raise ValueError('Invalid posterior archive header')
    return shape, fortran, dtype


def verify_summary_receipt(receipt, dataset, source_hashes):
    """Conditional-history predictions apply only to the Nicolas repeat task."""
    if dataset not in ('uwa', 'nicolas'):
        raise ValueError('Unknown summary dataset')
    conditional = 200 if dataset == 'nicolas' else 0
    if (receipt['contrast_draws'] != 4000 or receipt['joint_replications'] != 200
            or receipt['conditional_replications'] != conditional
            or receipt['source_hashes'] != source_hashes):
        raise ValueError('Wrong summary budget/source')


def verify_result(folder, meta):
    manifest = json.loads((folder / 'manifest.json').read_text())
    job_info(manifest['job'])
    if 'fit.json' not in manifest['files']:
        raise ValueError('Missing fit receipt')
    for name, row in manifest['files'].items():
        if name not in ALLOWED:
            raise ValueError('Unapproved output filename')
        path = folder / name
        if path.stat().st_size != row['bytes'] or sha(path) != row['sha256']:
            raise ValueError('Output integrity mismatch: ' + name)
    fit = json.loads((folder / 'fit.json').read_text())
    if fit['job'] != job_info(manifest['job']) or fit['source_hashes'] != meta['source_hashes']:
        raise ValueError('Wrong fit/source')
    if fit['state'] != manifest['state'] or fit['state'] not in ('complete', 'failed'):
        raise ValueError('Not a terminal fit')
    if fit['state'] == 'complete':
        if ALLOWED - {'progress.json'} - set(manifest['files']):
            raise ValueError('Missing completed output')
        receipt = json.loads((folder / 'summary-receipt.json').read_text())
        verify_summary_receipt(receipt, fit['job']['dataset'], meta['source_hashes'])
        with np.load(folder / 'contrast-draws.npz', allow_pickle=False) as draws:
            for key in ('mean_log_ratio', 'probability_ratio', 'probability_difference_per_1000'):
                if draws[key].shape != (4, 1000) or not np.isfinite(draws[key]).all():
                    raise ValueError('Invalid contrast draws')
            if not np.allclose(draws['probability_ratio'], np.exp(draws['mean_log_ratio']), rtol=1e-12):
                raise ValueError('Ratio mismatch')
        with zipfile.ZipFile(folder / 'posterior.npz') as archive:
            names = archive.namelist()
            if not names or len(names) != len(set(names)) or any(not name.endswith('.npy') for name in names):
                raise ValueError('Invalid posterior archive members')
            for name in names:
                with archive.open(name) as stream:
                    posterior_header(stream)
    return fit

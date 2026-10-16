"""Shared paths, receipts and deterministic arithmetic for restricted H2."""
from __future__ import annotations
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from importlib.metadata import distributions
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PRIVATE = ROOT / 'private/h2-implementation-20261016'
OUT = ROOT / 'results/h2-implementation-20261016'
SPEC = ROOT / 'notes/h2-production-specification-2026-10-16.md'
SCRATCH = ROOT / '.cache/h2-production'
SCRATCH.mkdir(parents=True, exist_ok=True)
os.environ.setdefault('NUMBA_CACHE_DIR', str(SCRATCH / 'numba'))
os.environ.setdefault('MPLCONFIGDIR', str(SCRATCH / 'mpl'))
flags = [s for s in os.environ.get('PYTENSOR_FLAGS', '').split(',') if s and
         not s.startswith(('base_compiledir=', 'compiledir='))]
flags.append('base_compiledir=' + str(SCRATCH / 'pytensor'))
if sys.platform == 'darwin' and not any(s.startswith('cxx=') for s in flags):
    flags.append('cxx=' + str(ROOT / 'scripts/d1/bin/clang++'))
os.environ['PYTENSOR_FLAGS'] = ','.join(flags)
for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ.setdefault(key, '1')

import numpy as np


def utc(): return datetime.now(timezone.utc).isoformat()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(2**20), b''): h.update(block)
    return h.hexdigest()


def plain(x):
    if isinstance(x, np.ndarray): return plain(x.tolist())
    if isinstance(x, np.generic): return plain(x.item())
    if isinstance(x, float) and not np.isfinite(x): return None
    if isinstance(x, dict): return {str(k): plain(v) for k,v in x.items()}
    if isinstance(x, (list, tuple)): return [plain(v) for v in x]
    return x


def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(plain(value), indent=2, allow_nan=False) + '\n')
    temp.replace(path)


def environment():
    return dict(at=utc(), python=sys.version, executable=sys.executable, platform=platform.platform(),
        packages={d.metadata['Name']: d.version for d in distributions()},
        threads={k:os.environ[k] for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')},
        pytensor_flags=os.environ['PYTENSOR_FLAGS'])


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def source_receipt():
    names = [str(p.relative_to(ROOT)) for p in sorted((ROOT/'scripts/h2_production').glob('*.py'))]
    names += ['scripts/h2_production/preflight-settings.json', str(SPEC.relative_to(ROOT)),
              'scripts/d1/bin/clang++']
    return {n: sha(ROOT/n) for n in names}


def require_committed():
    hashes = source_receipt()
    for name, digest in hashes.items():
        if hashlib.sha256(git('show', 'HEAD:'+name)).hexdigest() != digest:
            raise ValueError('Uncommitted execution source: '+name)
    return dict(commit=git('rev-parse','HEAD').decode().strip(), hashes=hashes)


def summary(x):
    a=np.asarray(x, dtype=float)
    return dict(mean=a.mean(), sd=a.std(), q05=np.quantile(a,.05), q25=np.quantile(a,.25),
        median=np.median(a), q75=np.quantile(a,.75), q95=np.quantile(a,.95), p_negative=np.mean(a<0))


def centered(x, axes=None):
    x=np.asarray(x)
    if axes == 'double':
        g,w=x.shape
        return (x-x.mean(0)-x.mean(1)[:,None]+x.mean())/np.sqrt((1-1/g)*(1-1/w))
    return (x-x.mean())/np.sqrt(1-1/x.size)


def ordinal_scores(q):
    """Leading dimensions may include draw; final axes are word and category."""
    r=q.mean(axis=-2)
    lower=np.cumsum(r,axis=-1)-r
    return np.sum(q*(lower+.5*r)[...,None,:],axis=-1)

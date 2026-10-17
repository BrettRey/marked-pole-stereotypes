"""One bounded Claude process-lifetime check; no data access or model fitting."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import platform
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def run(output, duration=7500, interval=60):
    output.mkdir(parents=True, exist_ok=False)
    limits = {k: int(os.environ.get(k, '0')) for k in
              ('BASH_DEFAULT_TIMEOUT_MS', 'BASH_MAX_TIMEOUT_MS')}
    if max(limits.values()) < (duration + 60) * 1000:
        raise RuntimeError('Configured timeout does not cover the lifecycle check')
    version = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=30)
    if version.returncode:
        raise RuntimeError('Cannot record installed Claude Code version')
    record = dict(kind='process_lifetime_only', state='running', started_at=now(),
                  pid=os.getpid(), duration_seconds=duration, interval_seconds=interval,
                  timeout_environment=limits, claude_version=version.stdout.strip(),
                  python_version=platform.python_version(),
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  empirical_fits=0, research_data_access=False)
    write(output / 'receipt.json', record)
    start = time.monotonic()

    def interrupted(signum, frame):
        raise InterruptedError('Received signal ' + str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        while True:
            elapsed = time.monotonic() - start
            event = dict(at=now(), pid=os.getpid(), elapsed_seconds=elapsed, state='running')
            write(output / 'heartbeat.json', event)
            with (output / 'heartbeats.jsonl').open('a') as stream:
                stream.write(json.dumps(event) + '\n')
                stream.flush()
                os.fsync(stream.fileno())
            print(json.dumps(event), flush=True)
            if elapsed >= duration:
                break
            time.sleep(min(interval, duration - elapsed))
        record.update(state='complete', exit_status=0)
    except BaseException as exc:
        record.update(state='failed', error=repr(exc), exit_status=1)
        raise
    finally:
        record.update(ended_at=now(), elapsed_seconds=time.monotonic() - start)
        write(output / 'receipt.json', record)
        print(json.dumps(record), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)

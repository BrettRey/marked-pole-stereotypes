# Prepare one Apple Silicon Mac

This prepares an Apple Silicon Mac with at least 16 GB for one simulation worker,
including the M2 and M5 volunteer Macs. It checks
the environment only. The replicated assessment still waits for the frozen
empirical inputs and an assigned batch. Don't run the archived full-grid commands.

The setup uses the existing native macOS compiler workaround and exact scientific
package versions. It doesn't require an AI subscription, HF credentials, Docker,
remote login, or access to empirical data. It installs Python packages in this
project's `.venv-volunteer`, not the system Python.

## 1. Check Apple's command line tools

Open Terminal and run:

```sh
xcode-select -p
```

If that prints an error, run `xcode-select --install`, accept Apple's installer,
and wait for it to finish. Then continue. If it prints a directory, continue now.

## 2. Download the project and prepare Python

Copy this block into Terminal. The folder name must be unused; `git clone` stops
instead of overwriting an existing copy.

```sh
git clone --depth 1 https://github.com/BrettRey/marked-pole-stereotypes.git "$HOME/marked-pole-volunteer"
```

After the clone succeeds, copy this block:

```sh
cd "$HOME/marked-pole-volunteer" && (
  set -e
  mkdir -p .tools
  curl --fail --location --silent --show-error https://astral.sh/uv/0.13.0/install.sh -o .tools/install-uv.sh
  UV_UNMANAGED_INSTALL="$PWD/.tools" sh .tools/install-uv.sh
  .tools/uv python install 3.14.8
  .tools/uv venv --python 3.14.8 .venv-volunteer
  .tools/uv pip install --python .venv-volunteer/bin/python -r requirements-d1.txt
  .venv-volunteer/bin/python scripts/volunteer/preflight.py
)
```

The uv installer is pinned to version 0.13.0 and installed
under `.tools`, without editing shell profiles. Python is managed by uv; the
scientific packages use `requirements-d1.txt`. The readiness report records the
checked-out commit and exact installed versions. [Official uv installation](https://docs.astral.sh/uv/getting-started/installation/),
[unmanaged installation](https://docs.astral.sh/uv/configuration/installer/).

## 3. Return the readiness result

When it finishes, send Brett the PASS/FAIL lines, or the file
`marked-pole-volunteer/volunteer-readiness.json`. The report includes chip, memory,
OS/compiler/package versions and disk space; it omits the computer's hostname,
account name, network addresses and credentials. A passing result checks this
environment, not model convergence, sustained speed or production memory use.

Once a study batch is assigned, keep the Mac plugged in with the lid open.
Start with one worker; additional workers require measured memory headroom.
The assigned command will control sleep for that run and explain how to stop it.
No always-on service is installed by this setup.

## Coordinator check

Publish this setup before asking a volunteer to run it. Validate the preflight
with the coordinator's existing pinned environment first. Its scalar arithmetic
check compiles no study model and fits no observations. Keep the volunteered
computer's report separate from that local validation.

"""Execute through Colab CLI only after checking the account rate and allowance.

Requires BENCHMARK_SOURCE=<full published commit> in the remote environment.
No GPU, Drive mount, account tokens, or empirical source files are needed.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def main():
    source = os.environ.get("BENCHMARK_SOURCE", "")
    if not re.fullmatch(r"[0-9a-f]{40}", source):
        raise ValueError("Set BENCHMARK_SOURCE to the published full commit")
    if not sys.platform.startswith("linux"):
        raise RuntimeError("This bootstrap is for a Linux Colab runtime")
    if not shutil.which("g++"):
        raise RuntimeError("C++ compiler is unavailable; stop before setup or fitting")
    memory = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    if int(memory["MemAvailable"].split()[0])*1024 < 11*2**30:
        raise RuntimeError("Less than 11 GiB available; stop before fitting")
    project = Path("/content/marked-pole-compute")
    if project.exists():
        raise FileExistsError("This runtime was already prepared; inspect rather than restart")
    subprocess.run([sys.executable, "-m", "pip", "install", "uv==0.13.0"], check=True, timeout=180)
    subprocess.run(["git", "clone", "https://github.com/BrettRey/marked-pole-stereotypes.git", str(project)],
                   check=True, timeout=180)
    subprocess.run(["git", "checkout", "--quiet", source], cwd=project, check=True, timeout=60)
    subprocess.run([sys.executable, "-m", "uv", "venv", "--python", "3.14.8", ".venv-compute"],
                   cwd=project, check=True, timeout=300)
    python = str(project / ".venv-compute/bin/python")
    subprocess.run([sys.executable, "-m", "uv", "pip", "install", "--python", python,
                    "-r", "requirements-d1.txt"], cwd=project, check=True, timeout=600)
    command = [python, "-u", "scripts/compute/benchmark.py", "--source", source, "--profile", "colab-one"]
    subprocess.run(command + ["--check"], cwd=project, check=True, timeout=180)
    try:
        subprocess.run(command, cwd=project, check=True, timeout=6*3600+600)
    finally:
        artifacts = project / "results/compute/20261011/colab-one"
        if artifacts.exists():
            shutil.make_archive("/content/benchmark-artifacts", "zip", artifacts)
            print("Download /content/benchmark-artifacts.zip before stopping the runtime", flush=True)


if __name__ == "__main__":
    main()

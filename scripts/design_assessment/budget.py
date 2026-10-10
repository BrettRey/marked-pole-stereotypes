#!/usr/bin/env python3
"""Preview replication precision and compute cost; never submit or fit jobs."""
import argparse
import hashlib
import json
import math
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def replication_count(mcse, rate=.5):
    if not 0 < mcse < .5 or not 0 < rate < 1:
        raise ValueError("Use 0 < MCSE < .5 and 0 < assumed rate < 1")
    return max(2, math.ceil(rate*(1-rate)/mcse**2))


def estimate(plan, repetitions):
    if repetitions < 2 or not isinstance(repetitions, int):
        raise ValueError("At least two integer independent datasets are required")
    if plan.get("launch_authorized") is not False or not plan.get("cells"):
        raise ValueError("This calculator requires an explicit non-launch planning document")
    labels, hours, total_cost, reserved = set(), {}, 0., 0.
    rows = []
    for cell in plan["cells"]:
        if cell["id"] in labels:
            raise ValueError("Duplicate planned cell")
        labels.add(cell["id"])
        platform = cell["platform"]
        components = cell["components"]
        if not components:
            raise ValueError("Missing component timing")
        total = 0.
        for c in components:
            if (not isinstance(c["count"], int) or c["count"] < 1
                    or not math.isfinite(c["seconds"]) or c["seconds"] <= 0 or not c.get("source")):
                raise ValueError("Positive sourced component timings and integer counts required")
            total += c["count"]*c["seconds"]
        worker_hours = repetitions*total/3600
        hours[platform] = hours.get(platform, 0)+worker_hours
        rows.append(dict(cell=cell["id"], platform=platform, datasets=repetitions,
                         fits=repetitions*sum(c["count"] for c in components), worker_hours=worker_hours))
    platforms = {}
    for name, worker_hours in hours.items():
        settings = plan["platforms"][name]
        workers, machines = settings["workers_per_machine"], settings["machines"]
        price, timeout = settings["usd_per_machine_hour"], settings["timeout_hours"]
        if (any(not isinstance(x, int) or x < 1 for x in (workers, machines))
                or not math.isfinite(price) or price < 0 or not math.isfinite(timeout) or timeout <= 0):
            raise ValueError("Invalid platform capacity, hourly price or timeout")
        elapsed = worker_hours/(workers*machines)
        # Each machine would require this many sessions at the same concurrency.
        sessions = math.ceil(elapsed/timeout)
        cost = math.ceil(elapsed*60)/60*machines*price
        reserve = sessions*machines*timeout*price
        total_cost += cost
        reserved += reserve
        platforms[name] = dict(worker_hours=worker_hours,
            ideal_elapsed_hours=elapsed, serial_elapsed_hours=worker_hours,
            projected_machine_sessions=sessions*machines, estimated_compute_usd=cost,
            compute_reserved_at_session_timeouts_usd=reserve)
    remaining = plan["remaining_authorized_usd"]
    if not math.isfinite(remaining) or remaining < 0:
        raise ValueError("Remaining budget must be nonnegative")
    return dict(replicates_per_cell=repetitions, cells=rows, platforms=platforms,
        ideal_elapsed_hours=max(p["ideal_elapsed_hours"] for p in platforms.values()),
        estimated_compute_usd=total_cost, conservative_session_reservation_usd=reserved,
        remaining_authorized_usd=remaining, reservation_within_budget=reserved <= remaining,
        launch_authorized=False,
        limitations=["Ideal elapsed time assumes perfect load balancing and independent one-core work.",
                    "Setup, export overhead, dependencies, contention and failures can increase elapsed time and cost.",
                    "Session counts and reservations assume resumable work across timeout boundaries; no jobs are submitted.",
                    "Different sampler budgets, designs and hardware require new timing inputs."])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcse", type=float, required=True, help="Rate SE as a proportion, e.g. .025")
    parser.add_argument("--rate", type=float, default=.5, help=".5 gives the worst-case binomial bound")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    count = replication_count(args.mcse, args.rate)
    result = dict(observed_at=datetime.now(timezone.utc).isoformat(),
        requested_rate_mcse=args.mcse, assumed_rate=args.rate, independent_datasets=count,
        worst_case_mcse=.5/math.sqrt(count), launch_authorized=False,
        environment=dict(python=sys.version, platform=platform.platform()),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), command=sys.argv)
    if args.plan:
        result.update(compute=estimate(json.loads(args.plan.read_text()), count),
                      plan_sha256=hashlib.sha256(args.plan.read_bytes()).hexdigest())
    value = json.dumps(result, indent=2, allow_nan=False)+"\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x") as stream:
            stream.write(value)
    print(value, end="")


if __name__ == "__main__":
    main()

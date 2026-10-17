# H2 recovery: repair Claude launch and retain HF

16 October 2026. **Recommendation: correct the documented Claude Cloud timeout configuration and verify process monitoring, with HF as the fallback.** My earlier HF-only recommendation was premature. This is an execution repair; the analysis, inputs, priors, measurement components and sampler settings stay fixed. No recovery fit has been launched.

## What failed and what the documentation establishes

The Claude driver was launched inside an agent background task with a two-hour lifetime. It stopped before saving a posterior or reporting failure. The assignment register lacked independent evidence of process life, so monitoring continued to display a stale claim. I should have verified process lifetime and failure detection before describing the batch as unattended. The failed attempt and its independently verified export remain preserved in the [incident record](../results/h2-empirical-20261016/cloud-launch-failure.json).

Anthropic documents a configurable background-command maximum: `BASH_MAX_TIMEOUT_MS` above `7200000` raises the two-hour ceiling. A main-conversation background command can continue after the agent's final response. This supports a configuration repair; it does not establish that Claude Cloud is unsuitable. [Claude Code tools reference](https://code.claude.com/docs/en/tools-reference#raise-the-time-limit-for-background-commands).

Claude Cloud adds no separate command timeout. Its environment settings can supply the timeout variables before Claude starts. Idle VMs can pause and later be reclaimed, so correct command configuration alone does not prove uninterrupted multi-day execution. Use a fresh session with the configured environment, and verify actual process life externally. [Cloud environments: time limits](https://code.claude.com/docs/en/cloud-environments#time-limits), [environment variables](https://code.claude.com/docs/en/cloud-environments#set-environment-variables).

## Approved recovery

1. **Let the existing HF fit finish.** Verify its archive and summaries, preserving diagnostic qualifications. Do not rerun it. If it fails execution or output integrity, stop at that boundary; this plan does not authorize replacing it. At the latest check, one attempt has failed, one HF fit is advancing, and 62 jobs remain held.

2. **Repair orchestration while that fit runs.** Keep the scientific worker and frozen inputs unchanged. Store attempts separately and link each logical component to its attempts. The new register must distinguish assignment, recent process evidence, completed export and verified output. Import the surviving HF component by its verified manifest; preserve the failed Claude attempt unchanged.

3. **Verify the supported Claude configuration before entrusting it with another fit.** Use a dedicated recovery environment with an explicit background-command timeout bounded by the remaining batch deadline. Set it before a fresh session starts, record the installed Claude Code version and effective values, and launch from the main conversation. Run one 125-minute process-lifetime check that only emits timestamped heartbeats and exits. It fits no model and uses no research data. Require evidence beyond two hours and a captured successful exit. If the configuration cannot be applied or the check fails, preserve the evidence and use HF for the recovery.

4. **Run exactly one replacement of `nicolas-s0-c0`.** Use Claude if the lifecycle check passes; otherwise use HF. Retain the original seed, four chains, 1,000 warmup and 1,000 retained draws per chain, target acceptance .95 and depth 12. Record attempt 2 as an infrastructure replacement. There is no posterior from attempt 1 to reuse or select between. If attempt 2 fails, preserve it and stop the initial gate; do not try another provider automatically.

5. **After both initial components export and verify, release the remaining 62 fixed jobs.** Use the repaired mixed-provider queue if Claude passes the operational check; otherwise use HF only. Allow at most two concurrent HF fits and one Claude fit. Never duplicate a claim, automatically replace a failed fit, or renormalize a cut over missing components. Retain equal weights over all eight verified components for each cut.

## Monitoring and output preservation

A supervisor will publish timestamps, child-process state, sampler progress, exit status and export-verification state to the private HF archive. An independently observed process exit must produce a failure receipt even when the scientific worker cannot. Old or missing evidence is stale or unknown, not confirmed running. A stale heartbeat does not authorize reassignment. Slow warmup alone triggers neither termination nor a scientific verdict.

Keep Claude's access limited to its batch inputs, assigned outputs and heartbeats through a temporary capability; do not give it an HF account credential. Keep the existing live server untouched. Use a separately versioned recovery register and service after the original run finishes. Local collection can resume after the Mac wakes; remote process monitoring must continue without the Mac.

Test normal exit, abrupt termination, stale heartbeat, duplicate launch, changed hashes and collection restart using short non-scientific subprocesses. Commit the accepted execution amendment and repaired source before the replacement fit starts. Prefer documented CLI/API access; use the browser only where this account lacks an available configuration or session-management API.

## Resource boundary and timing

Retain the **$12 total HF cap**, including the original host and any temporary exposed-port charges, and use existing Claude credits. Recheck current prices and remaining balances at launch. Use one HF provider attempt, enforce the remaining allowance in the new timeout, and do not buy credit, enable recharge or change subscriptions. [HF Jobs guide](https://huggingface.co/docs/huggingface_hub/en/guides/jobs), [HF pricing](https://huggingface.co/docs/hub/en/jobs-pricing).

The first completed fit will support a revised timing estimate. The lifecycle check establishes survival across the observed failure boundary, not a guarantee of multi-day availability. Do not promise completion within the resource cap or restore the withdrawn batch ETA prematurely.

## Decision for this checkpoint

Approve the orchestration repair, one bounded Claude lifecycle check, and **one infrastructure replacement of `nicolas-s0-c0`**, followed by the remaining fixed jobs within the existing resource boundary. This explicitly amends the [original execution plan's no-retry rule](h2-empirical-execution-2026-10-16.md) for that attempt only. Further model changes, additional measurement components and other replacement fits remain outside this plan.

Status: approved by Brett's “proceed” on 16 October 2026. Implementation and the bounded lifecycle check are authorized. The existing HF fit continues independently; no replacement fit has started.

# Registered baseline joint/cut comparison

Updated 2026-10-11T01:36:59.801167+00:00. Batch state: **complete**.

One artificial dataset per production design. Paired fits are not independent replications; this is a computational comparison, not calibration or an empirical verdict.

| Location | Provider/controller state | Completed modules |
|---|---|---|
| hf-shard-0 | COMPLETED / complete | upstream, downstream-000, downstream-001 |
| hf-shard-1 | COMPLETED / complete | downstream-003, downstream-002 |
| hf-shard-2 | COMPLETED / complete | downstream-004, downstream-005 |
| hf-shard-3 | COMPLETED / complete | downstream-006, downstream-007 |
| hf-joint | COMPLETED / complete | joint-124 |
| local | complete / complete | joint-004 |

| Design / fit | Contrast | Mean | 50% interval | 90% interval | Diagnostic status |
|---|---|---:|---|---|---|
| uwa / cut | h2_prevalence_bridge | 0.02740 | [-0.05851, 0.11579] | [-0.18218, 0.22546] | converged |
| uwa / cut | h1_fixed_usage | -0.25169 | [-0.43902, -0.05603] | [-0.73406, 0.20497] | converged |
| uwa / cut | b_z | -0.01913 | [-0.10993, 0.07517] | [-0.24883, 0.19454] | converged |
| uwa / cut | marking | -0.02069 | [-0.03557, -0.00658] | [-0.05398, 0.01475] | converged |
| uwa / joint | h2_prevalence_bridge | 0.01971 | [-0.07549, 0.11726] | [-0.21602, 0.25012] | converged |
| uwa / joint | h1_fixed_usage | -0.29230 | [-0.48407, -0.09085] | [-0.77731, 0.17378] | converged |
| uwa / joint | b_z | -0.11119 | [-0.22325, 0.00015] | [-0.38057, 0.15782] | converged |
| uwa / joint | marking | -0.06528 | [-0.08111, -0.05095] | [-0.10010, -0.02574] | converged |
| nicolas / joint | h2_prevalence_bridge | 0.01669 | [-0.02659, 0.05907] | [-0.08594, 0.12101] | converged |
| nicolas / joint | h1_fixed_usage | -0.00914 | [-0.08721, 0.07164] | [-0.20738, 0.18330] | converged |
| nicolas / joint | b_z | -0.07768 | [-0.13124, -0.02364] | [-0.21369, 0.05576] | converged |
| nicolas / joint | marking | -0.04960 | [-0.06690, -0.03430] | [-0.08604, -0.00684] | converged |
| nicolas / cut | h2_prevalence_bridge | 0.01051 | [-0.02746, 0.04824] | [-0.08002, 0.10154] | converged |
| nicolas / cut | h1_fixed_usage | 0.02200 | [-0.05489, 0.09993] | [-0.16852, 0.20992] | converged |
| nicolas / cut | b_z | -0.02130 | [-0.06294, 0.02076] | [-0.12529, 0.08072] | converged |
| nicolas / cut | marking | -0.01673 | [-0.03003, -0.00431] | [-0.04670, 0.01610] | converged |

| Design | Contrast | Joint mean minus cut mean | Joint/cut 90% interval width |
|---|---|---:|---:|
| uwa | h2_prevalence_bridge | -0.00769 | 1.1435 |
| uwa | h1_fixed_usage | -0.04062 | 1.0128 |
| uwa | b_z | -0.09206 | 1.2143 |
| uwa | marking | -0.04459 | 1.0820 |
| nicolas | h2_prevalence_bridge | 0.00618 | 1.1399 |
| nicolas | h1_fixed_usage | -0.03114 | 1.0323 |
| nicolas | b_z | -0.05638 | 1.3080 |
| nicolas | marking | -0.03287 | 1.2610 |

Cuts retain eight equally weighted upstream draws; inner-chain diagnostics do not establish the accuracy of that outer approximation. Failed diagnostics remain visible. Mean differences and width ratios describe the two posterior summaries; no posterior interval for their difference is implied. The 240-cell sweep remains stopped.

HF compute estimate from provider durations: USD 0.3210; not an invoice.

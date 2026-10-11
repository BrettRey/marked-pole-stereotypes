# Parallel baseline engineering batch

Updated 2026-10-11T02:28:18.251302+00:00. State: **incomplete_terminal**. Completed configurations: **14/16**.

Fixed scope: both designs, targets 0/−.1, joint/cut and register reliability 0/.8, prior scale 1, replicate 0. Completed and running fits from the earlier batch are reused.

| Host | Provider state | Active modules | Completed modules |
|---|---|---:|---:|
| cut-006-0 | COMPLETED | 0 | 3 |
| cut-006-1 | COMPLETED | 0 | 2 |
| cut-006-2 | COMPLETED | 0 | 2 |
| cut-006-3 | COMPLETED | 0 | 2 |
| cut-018-0 | COMPLETED | 0 | 3 |
| cut-018-1 | COMPLETED | 0 | 2 |
| cut-018-2 | COMPLETED | 0 | 2 |
| cut-018-3 | COMPLETED | 0 | 2 |
| cut-022-0 | COMPLETED | 0 | 3 |
| cut-022-1 | COMPLETED | 0 | 2 |
| cut-022-2 | COMPLETED | 0 | 2 |
| cut-022-3 | COMPLETED | 0 | 2 |
| cut-126-0 | COMPLETED | 0 | 3 |
| cut-126-1 | COMPLETED | 0 | 2 |
| cut-126-2 | COMPLETED | 0 | 2 |
| cut-126-3 | COMPLETED | 0 | 2 |
| cut-138-0 | COMPLETED | 0 | 3 |
| cut-138-1 | COMPLETED | 0 | 2 |
| cut-138-2 | COMPLETED | 0 | 2 |
| cut-138-3 | COMPLETED | 0 | 2 |
| cut-142-0 | COMPLETED | 0 | 3 |
| cut-142-1 | COMPLETED | 0 | 2 |
| cut-142-2 | COMPLETED | 0 | 2 |
| cut-142-3 | COMPLETED | 0 | 2 |
| joint-0 | ERROR | 2 | 0 |
| joint-1 | COMPLETED | 0 | 2 |
| joint-2 | COMPLETED | 0 | 2 |

| Cell | Design | Target | Register reliability | Fit | Diagnostic status |
|---|---|---:|---:|---|---|
| 0 | uwa | 0.0 | 0.0 | joint | pending |
| 4 | uwa | 0.0 | 0.8 | joint | converged |
| 6 | uwa | 0.0 | 0.0 | cut | converged |
| 10 | uwa | 0.0 | 0.8 | cut | converged |
| 12 | uwa | -0.1 | 0.0 | joint | pending |
| 16 | uwa | -0.1 | 0.8 | joint | converged |
| 18 | uwa | -0.1 | 0.0 | cut | converged |
| 22 | uwa | -0.1 | 0.8 | cut | converged |
| 120 | nicolas | 0.0 | 0.0 | joint | converged |
| 124 | nicolas | 0.0 | 0.8 | joint | converged |
| 126 | nicolas | 0.0 | 0.0 | cut | converged |
| 130 | nicolas | 0.0 | 0.8 | cut | converged |
| 132 | nicolas | -0.1 | 0.0 | joint | converged |
| 136 | nicolas | -0.1 | 0.8 | joint | converged |
| 138 | nicolas | -0.1 | 0.0 | cut | converged |
| 142 | nicolas | -0.1 | 0.8 | cut | converged |

| Cell | Contrast | Generated truth | Mean | 50% interval | 90% interval |
|---|---|---:|---:|---|---|
| 4 | h2_prevalence_bridge | 0.00000 | 0.01971 | [-0.07549, 0.11726] | [-0.21602, 0.25012] |
| 4 | h1_fixed_usage | -0.01301 | -0.29230 | [-0.48407, -0.09085] | [-0.77731, 0.17378] |
| 4 | b_z | -0.10868 | -0.11119 | [-0.22325, 0.00015] | [-0.38057, 0.15782] |
| 4 | marking | -0.04910 | -0.06528 | [-0.08111, -0.05095] | [-0.10010, -0.02574] |
| 6 | h2_prevalence_bridge | 0.00000 | -0.03727 | [-0.12397, 0.05305] | [-0.25662, 0.17208] |
| 6 | h1_fixed_usage | -0.01301 | -0.30799 | [-0.49342, -0.11415] | [-0.78291, 0.14289] |
| 6 | b_z | -0.10868 | -0.08258 | [-0.17582, 0.01476] | [-0.32448, 0.14567] |
| 6 | marking | -0.04910 | -0.02500 | [-0.03861, -0.01207] | [-0.05613, 0.00817] |
| 10 | h2_prevalence_bridge | 0.00000 | 0.02740 | [-0.05851, 0.11579] | [-0.18218, 0.22546] |
| 10 | h1_fixed_usage | -0.01301 | -0.25169 | [-0.43902, -0.05603] | [-0.73406, 0.20497] |
| 10 | b_z | -0.10868 | -0.01913 | [-0.10993, 0.07517] | [-0.24883, 0.19454] |
| 10 | marking | -0.04910 | -0.02069 | [-0.03557, -0.00658] | [-0.05398, 0.01475] |
| 16 | h2_prevalence_bridge | -0.10000 | -0.14673 | [-0.23588, -0.05381] | [-0.37197, 0.06801] |
| 16 | h1_fixed_usage | 0.01042 | -0.42637 | [-0.63090, -0.21166] | [-0.95468, 0.07428] |
| 16 | b_z | -0.23293 | -0.29540 | [-0.40278, -0.18520] | [-0.56622, -0.02913] |
| 16 | marking | -0.04601 | -0.06284 | [-0.07821, -0.04916] | [-0.09564, -0.02456] |
| 18 | h2_prevalence_bridge | -0.10000 | -0.11673 | [-0.19338, -0.03807] | [-0.31022, 0.06983] |
| 18 | h1_fixed_usage | 0.01042 | -0.34701 | [-0.53933, -0.14746] | [-0.83745, 0.12029] |
| 18 | b_z | -0.23293 | -0.16231 | [-0.25008, -0.07453] | [-0.38080, 0.05431] |
| 18 | marking | -0.04601 | -0.01001 | [-0.02491, 0.00415] | [-0.04336, 0.02586] |
| 22 | h2_prevalence_bridge | -0.10000 | -0.08539 | [-0.16343, -0.00829] | [-0.27128, 0.10326] |
| 22 | h1_fixed_usage | 0.01042 | -0.35295 | [-0.54699, -0.15165] | [-0.84614, 0.11833] |
| 22 | b_z | -0.23293 | -0.12360 | [-0.20765, -0.03943] | [-0.33019, 0.08255] |
| 22 | marking | -0.04601 | -0.01242 | [-0.02774, 0.00205] | [-0.04693, 0.02494] |
| 120 | h2_prevalence_bridge | 0.00000 | 0.00622 | [-0.03518, 0.04779] | [-0.09682, 0.10726] |
| 120 | h1_fixed_usage | 0.01638 | -0.00017 | [-0.07990, 0.07903] | [-0.19546, 0.19066] |
| 120 | b_z | -0.13726 | -0.08352 | [-0.13584, -0.03059] | [-0.21756, 0.04898] |
| 120 | marking | -0.04463 | -0.04276 | [-0.05998, -0.02737] | [-0.07984, -0.00056] |
| 124 | h2_prevalence_bridge | 0.00000 | 0.01669 | [-0.02659, 0.05907] | [-0.08594, 0.12101] |
| 124 | h1_fixed_usage | 0.01638 | -0.00914 | [-0.08721, 0.07164] | [-0.20738, 0.18330] |
| 124 | b_z | -0.13726 | -0.07768 | [-0.13124, -0.02364] | [-0.21369, 0.05576] |
| 124 | marking | -0.04463 | -0.04960 | [-0.06690, -0.03430] | [-0.08604, -0.00684] |
| 126 | h2_prevalence_bridge | 0.00000 | 0.01423 | [-0.02143, 0.04999] | [-0.07272, 0.10053] |
| 126 | h1_fixed_usage | 0.01638 | 0.02879 | [-0.04782, 0.10616] | [-0.16198, 0.21628] |
| 126 | b_z | -0.13726 | -0.02008 | [-0.05748, 0.01737] | [-0.11243, 0.07303] |
| 126 | marking | -0.04463 | -0.01292 | [-0.02883, 0.00142] | [-0.04650, 0.02654] |
| 130 | h2_prevalence_bridge | 0.00000 | 0.01051 | [-0.02746, 0.04824] | [-0.08002, 0.10154] |
| 130 | h1_fixed_usage | 0.01638 | 0.02200 | [-0.05489, 0.09993] | [-0.16852, 0.20992] |
| 130 | b_z | -0.13726 | -0.02130 | [-0.06294, 0.02076] | [-0.12529, 0.08072] |
| 130 | marking | -0.04463 | -0.01673 | [-0.03003, -0.00431] | [-0.04670, 0.01610] |
| 132 | h2_prevalence_bridge | -0.10000 | -0.20276 | [-0.24769, -0.15828] | [-0.31129, -0.09467] |
| 132 | h1_fixed_usage | 0.01050 | -0.21599 | [-0.31662, -0.11410] | [-0.46460, 0.02788] |
| 132 | b_z | -0.24009 | -0.29735 | [-0.35663, -0.23956] | [-0.44201, -0.14719] |
| 132 | marking | -0.04494 | -0.05109 | [-0.06397, -0.03949] | [-0.07971, -0.01799] |
| 136 | h2_prevalence_bridge | -0.10000 | -0.20753 | [-0.25265, -0.16137] | [-0.31876, -0.09852] |
| 136 | h1_fixed_usage | 0.01050 | -0.23695 | [-0.33845, -0.13189] | [-0.49216, 0.00819] |
| 136 | b_z | -0.24009 | -0.30714 | [-0.36561, -0.24947] | [-0.45173, -0.16114] |
| 136 | marking | -0.04494 | -0.05192 | [-0.06493, -0.04028] | [-0.08018, -0.01975] |
| 138 | h2_prevalence_bridge | -0.10000 | -0.07157 | [-0.10780, -0.03698] | [-0.15681, 0.01917] |
| 138 | h1_fixed_usage | 0.01050 | -0.05984 | [-0.14930, 0.03107] | [-0.28348, 0.15786] |
| 138 | b_z | -0.24009 | -0.09632 | [-0.13776, -0.05639] | [-0.19521, 0.00783] |
| 138 | marking | -0.04494 | -0.01508 | [-0.02995, -0.00119] | [-0.04758, 0.02033] |
| 142 | h2_prevalence_bridge | -0.10000 | -0.09348 | [-0.13039, -0.05599] | [-0.18369, -0.00586] |
| 142 | h1_fixed_usage | 0.01050 | -0.07351 | [-0.16301, 0.01797] | [-0.29729, 0.14537] |
| 142 | b_z | -0.24009 | -0.11516 | [-0.15805, -0.07243] | [-0.21981, -0.00958] |
| 142 | marking | -0.04494 | -0.02055 | [-0.03269, -0.00977] | [-0.04693, 0.01011] |

| Joint / cut cells | Contrast | Joint mean minus cut mean | Joint/cut 90% width |
|---|---|---:|---:|
| 4 / 10 | h2_prevalence_bridge | -0.00769 | 1.1435 |
| 4 / 10 | h1_fixed_usage | -0.04062 | 1.0128 |
| 4 / 10 | b_z | -0.09206 | 1.2143 |
| 4 / 10 | marking | -0.04459 | 1.0820 |
| 16 / 22 | h2_prevalence_bridge | -0.06135 | 1.1747 |
| 16 / 22 | h1_fixed_usage | -0.07343 | 1.0669 |
| 16 / 22 | b_z | -0.17180 | 1.3013 |
| 16 / 22 | marking | -0.05042 | 0.9890 |
| 120 / 126 | h2_prevalence_bridge | -0.00801 | 1.1780 |
| 120 / 126 | h1_fixed_usage | -0.02896 | 1.0208 |
| 120 / 126 | b_z | -0.06344 | 1.4372 |
| 120 / 126 | marking | -0.02984 | 1.0855 |
| 124 / 130 | h2_prevalence_bridge | 0.00618 | 1.1399 |
| 124 / 130 | h1_fixed_usage | -0.03114 | 1.0323 |
| 124 / 130 | b_z | -0.05638 | 1.3080 |
| 124 / 130 | marking | -0.03287 | 1.2610 |
| 132 / 138 | h2_prevalence_bridge | -0.13119 | 1.2309 |
| 132 / 138 | h1_fixed_usage | -0.15614 | 1.1159 |
| 132 / 138 | b_z | -0.20103 | 1.4520 |
| 132 / 138 | marking | -0.03601 | 0.9088 |
| 136 / 142 | h2_prevalence_bridge | -0.11405 | 1.2385 |
| 136 / 142 | h1_fixed_usage | -0.16344 | 1.1303 |
| 136 / 142 | b_z | -0.19199 | 1.3823 |
| 136 / 142 | marking | -0.03137 | 1.0595 |

One artificial dataset per design/target, with paired specifications; this is not replicated calibration. Eight outer draws do not establish cut-integration accuracy. Inner-chain diagnostic failures remain visible. The provisional empirical-design inputs remain unresolved. Summary differences are not posterior intervals for differences.

New extension compute ceiling: USD 9.72. Conservative total reservation: USD 13.08 of USD 15. Observed extension compute estimate: USD 1.7975, not an invoice.

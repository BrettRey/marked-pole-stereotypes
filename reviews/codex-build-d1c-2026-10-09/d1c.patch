diff --git a/scripts/d1c/README.md b/scripts/d1c/README.md
new file mode 100644
--- /dev/null
+++ b/scripts/d1c/README.md
@@ -0,0 +1,125 @@
+# D1c: categorical production design simulation
+
+This is a prospective specification. No D1c results are assumed here. Commit
+the specification and code before running; results inform the plan before it
+is FIXED. Simulated data evaluates a design, never supplies research evidence
+or replaces unavailable source data. All numerical design choices below are
+placeholders **[ours]**; none estimates a property of the actual datasets.
+
+## Design and reporting order
+
+Fit UWA-like and Nicolas-like designs separately: respectively 40 **[ours]**
+and 43 **[ours]** groups, with 12 **[ours]** participants answering every group,
+giving one and six responses per participant-group. Those response budgets
+match the task descriptions; group counts and the complete crossing remain
+placeholder designs. The vocabulary has 400 **[ours]** eligible words plus
+one explicit outside category. Independent commonness measurements cover
+40% **[ours]** of words, chosen at random, with reliability .8 **[ours]**.
+Eligibility and measurement coverage are different: uncovered words remain
+in the competing vocabulary.
+
+The fixed scenario order is baseline, indicator valence bias, register,
+display divergence, and differential register error. Each is crossed with
+null and threshold-sized *predictive* H2 truths, both datasets, joint and cut
+feedback, omitted register and measured register at reliabilities .5 and
+.8 **[ours]**, and coefficient prior SDs 1 and 2.5 **[ours]**. This is a
+first-version restricted multiverse, not coverage of every plan dimension.
+Both control reliabilities are fitted even in scenarios without confounding.
+Specifications share generated data and proxy noise within a replicate.
+Datasets, estimands, assumptions and priors stay separate in summaries.
+
+## Generating model
+
+All continuous predictors use fixed population scales. Higher z means greater
+within-valence prevalence. Valence v, prevalence residual z and stakes s are
+independent standard normals **[ours]**. Observed valence is v plus normal
+error of SD .1 **[ours]**, and arousal is s plus error of SD 1 **[ours]**.
+The fitted measurement model retains those known sampling errors.
+
+Three distinct register dimensions h are generated, representing origin,
+formality and familiarity. In register scenarios, each has mean
+−.3z + .2v + .2s and independent residual SD sqrt(.83) **[ours]**.
+Otherwise their mean is zero and residual SD is 1 **[ours]**. Origin is a
+continuous propensity here, not an observed Latinate/native classification.
+Register proxies are h plus paired normal errors of SD sqrt((1−r)/r)
+**[ours]**. Differential-error stress additionally shifts every proxy by
+.3m + .2v **[ours]**, which the fitted model deliberately does not know.
+
+Marking is binary, with logit probability
+−2 − .45z − v − .3s + .4 sum(h) in register scenarios **[ours]**.
+The h loading is zero otherwise. This approximates pooled formal negation;
+affix-specific H1 models and uncertain act-type coding are outside this
+first-version design. Stakes supplies a correlated semantic control, not a
+substitute for act type.
+
+Latent log usage ell has mean
+−4 + .4z + .3s + .3v − .3m − .25 sum(h), with the register term active only
+in register scenarios, and its own residual SD .7 **[ours]**. Corpus counts
+are Poisson(exp(ell) × 1,000) **[ours]**. Production uses latent ell,
+never log observed counts. There is no extra negative-binomial dispersion.
+
+The commonness indicator measures d + bias*v with known normal error;
+bias is .2 normally and .8 in the valence-bias scenario **[ours]**.
+Ordinarily d=z. In display divergence,
+d=.5z+sqrt(.75)*q **[ours]**, representing frequent minority display versus
+occasional majority display. This is a failed construct bridge, not a second
+indicator of prevalence. The fitted model implicitly assumes the identity
+bridge; results show its failure against both construct-specific truths.
+
+Eligible-word utilities contain z, marking, ell, valence and stakes, plus
+register in confounded scenarios. Accessibility is .3, valence −.5, stakes
+.1 and direct marking zero **[ours]**. Register production loadings are
+.25 each **[ours]**. Shared item effects have SD .2; group-by-word content
+has SD .35; group and participant rarity and marking slopes have SD .1
+**[ours]**. The outside utility is log(400 × 1.5) **[ours]**.
+
+Conditional on those slopes, each participant-group gives multinomial
+counts across the full vocabulary. This is exactly equivalent to independent
+categorical draws with that response budget: no group aggregation removes
+participant slopes. Nicolas-like responses can repeat a word. Conditional
+independence and sampling with replacement are approximations; sequential
+depletion, order and participant-group-specific dependence are not modelled.
+
+## Estimands and truth
+
+H2 is the mean log ratio of focal-word choice probabilities under z versus
+z+1, averaging over the model's marking and usage distributions, over all
+words, groups and the design's participants. Shift one focal word at a time;
+hold its competitors, outside option, content effects, valence, stakes and
+register fixed. This specifies competition and the target population.
+It is a predictive association, not a causal effect.
+
+Marking is integrated exactly over its two states; usage residuals use
+five-point Gauss–Hermite quadrature **[ours]**. Each branch changes the focal
+word's contribution to the denominator. This is not b_z or a sum of path
+coefficients. A deterministic root solve sets generating b_z so prevalence
+H2 equals 0 or −.10 **[ours]**, conditional on the generated design.
+The latter is a design magnitude, not a justified substantive benchmark.
+
+Also report H1's mean log probability ratio for m=1 versus m=0, with usage
+held fixed; conditional b_z; and the marking probability difference for z+1.
+Display truth shifts prevalence by .5 **[ours]**, preserving the residual
+in the Gaussian prevalence-given-display bridge and holding other controls
+fixed. Display and prevalence truths are reported separately, never pooled.
+Fitted H2 against prevalence truth explicitly evaluates its identity bridge.
+
+## Feedback, fitting and checks
+
+Let L=(z,s,v,h), E denote commonness/arousal/valence/register measurements,
+C corpus counts, M marking and Y production. The joint fit is proportional
+to p(L,theta) p(E|L,theta) p(C,M,Y|L,theta).
+The cut fit is
+q(L,theta_E,theta_D)=p(L,theta_E|E)
+×p(theta_D|C,M,Y,L).
+Each downstream factor is normalized separately for its upstream draw.
+Neither frequency, marking nor production updates L in the cut.
+Merely stopping a gradient or inserting a plug-in mean is not this cut.
+Omitted-register fits also omit register measurements from E.
+
+Use eight upstream posterior draws **[ours]**, each followed by a conditional
+downstream fit, and equally mix their contrasts. This is finite Monte Carlo
+integration of the cut; increase it before relying on small uncertainty
+differences. Compile once per shape/variant within each worker, with pm.Data,
+freeze_model=False and with_data. Use four chains, 500 retained draws,
+1,000 tuning steps, target acceptance .95 **[ours]**, with one sampler core
+per job. Flag any divergence, R-hat above 1.01, bulk or tail ESS below 100,
+or nonfinite diagnostics **[ours]**. Check every sampled variable and the
+derived contrasts. All cut components must pass. No automatic retries.
+
+CSV summaries report 50% and 90% coverage with binomial Monte Carlo SEs,
+bias and its SE, width, unconditional and 90%-selected sign errors,
+selected exaggeration ratios for nonzero truths, selected absolute bias,
+and false meaningful support. Selection means the 90% interval excludes zero.
+Benchmarks are −.10 for H2 and b_z, +.10 for H1, and −.02 for marking
+**[ours]**. False support is conditional on a truth not beyond its benchmark.
+Undefined quantities remain missing. Convergence failures and exceptions
+have separate rows; bias summaries use converged fits and state that selection.
+
+Run `python scripts/d1c/d1c.py pilot` for two replicates of one baseline
+cell and timing, or `python scripts/d1c/d1c.py run --reps R --workers W`.
+Outputs are timestamped CSVs under results/d1c and a JSON log under logs,
+including seeds, configuration, package versions, git state and timing.
+Pilot timing determines practical replication; two replicates cannot assess
+coverage. Re-run at frozen sizes and coverage before treating D1c as complete.
diff --git a/scripts/d1c/d1c.py b/scripts/d1c/d1c.py
new file mode 100644
--- /dev/null
+++ b/scripts/d1c/d1c.py
@@ -0,0 +1,471 @@
+#!/usr/bin/env python3
+"""D1c prospective design check; artificial data only. See README.md."""
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parents[2]
+if sys.platform == "darwin":
+    os.environ.setdefault(
+        "PYTENSOR_FLAGS", f"cxx={ROOT / 'scripts/d1/bin/clang++'}"
+    )
+# Avoid nested BLAS parallelism inside the process pool.
+for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
+    os.environ.setdefault(name, "1")
+
+import argparse
+import itertools
+import json
+import platform
+import subprocess
+import time
+from concurrent.futures import ProcessPoolExecutor, as_completed
+from datetime import datetime, timezone
+from importlib.metadata import PackageNotFoundError, version
+
+import numpy as np
+import pandas as pd
+from numpy.polynomial.hermite import hermgauss
+from scipy.optimize import brentq
+from scipy.special import expit, logsumexp
+
+# All numerical simulation/sampler choices are [ours]; see prospective spec.
+SEED = 20261009
+I, P, COVERAGE = 400, 12, .4
+DESIGNS = {"uwa": (40, 1), "nicolas": (43, 6)}
+SCENARIOS = ("baseline", "valence_bias", "register", "display", "differential")
+PRIORS = (1., 2.5)
+RELIABILITIES = (0., .5, .8)
+DRAWS, TUNE, CHAINS, CUT_DRAWS = 500, 1000, 4, 8
+POST_DRAWS = 100
+OUTSIDE = np.log(I * 1.5)
+NODES, WEIGHTS = hermgauss(5)
+NODES, WEIGHTS = NODES * np.sqrt(2), WEIGHTS / np.sqrt(np.pi)
+BENCHMARKS = {"h2_prevalence_bridge": -.1, "h2_display": -.1,
+              "h1_fixed_usage": .1, "b_z": -.1, "marking": -.02}
+COMPILED = {}
+
+
+def seed(*keys):
+    return int(np.random.SeedSequence(SEED, spawn_key=keys).generate_state(1)[0])
+
+
+def cells():
+    for index, values in enumerate(itertools.product(
+            DESIGNS, SCENARIOS, (0., -.1), ("joint", "cut"),
+            RELIABILITIES, PRIORS)):
+        yield dict(zip(("design", "scenario", "target", "feedback", "reliability",
+                        "prior"), values), cell=index)
+
+
+def utilities(t, z=None, marking=None, ell=None):
+    z = t["z"] if z is None else z
+    marking = t["m"] if marking is None else marking
+    ell = t["ell"] if ell is None else ell
+    return (t["base"] + t["bz"][:, None] * z
+            + t["bm"][:, None] * marking + t["bf"] * ell
+            + t["bv"] * t["v"] + t["bs"] * t["s"] + t["h"] @ t["bh"])
+
+
+def contrasts(t, delta=1.):
+    """All focal words, fixed competitors; branch-specific choice denominators."""
+    eta = utilities(t)
+    denominator = np.exp(eta).sum(axis=1) + np.exp(OUTSIDE)
+    competitors = denominator[:, None] - np.exp(eta)
+
+    def averaged_probability(z):
+        pm = expit(t["g0"] + t["gz"] * z + t["gv"] * t["v"]
+                   + t["gs"] * t["s"] + t["h"] @ t["gh"])
+        probability = np.zeros_like(eta)
+        for marking in (0., 1.):
+            mean = (t["f0"] + t["lz"] * z + t["ls"] * t["s"]
+                    + t["lv"] * t["v"] + t["lm"] * marking
+                    + t["h"] @ t["lh"])
+            mass = pm if marking else 1 - pm
+            for node, weight in zip(NODES, WEIGHTS):
+                focal = utilities(t, z, marking, mean + node * t["sig_f"])
+                # Stable logistic focal/(focal + competitors).
+                probability += weight * mass * expit(focal - np.log(competitors))
+        return probability
+
+    p0 = averaged_probability(t["z"])
+    p1 = averaged_probability(t["z"] + delta)
+    h2 = np.mean(np.log(p1) - np.log(p0))
+    # Marking held at each level, usage held at its current latent value.
+    a = expit(utilities(t, marking=0.) - np.log(competitors))
+    b = expit(utilities(t, marking=1.) - np.log(competitors))
+    h1 = np.mean(np.log(b) - np.log(a))
+    mark0 = (t["g0"] + t["gz"] * t["z"] + t["gv"] * t["v"]
+             + t["gs"] * t["s"] + t["h"] @ t["gh"])
+    return dict(h2=h2, h1_fixed_usage=h1,
+                marking=np.mean(expit(mark0 + t["gz"] * delta) - expit(mark0)))
+
+
+def generate(job):
+    design_index = list(DESIGNS).index(job["design"])
+    scenario_index = SCENARIOS.index(job["scenario"])
+    target_index = int(job["target"] != 0)
+    data_seed = seed(1, design_index, scenario_index, target_index, job["rep"])
+    rng = np.random.default_rng(data_seed)
+    G, budget = DESIGNS[job["design"]]
+    z, v, s = rng.normal(size=(3, I))
+    confounded = job["scenario"] in ("register", "differential")
+    h = rng.normal(size=(I, 3))
+    if confounded:
+        h = (-.3 * z + .2 * v + .2 * s)[:, None] + np.sqrt(.83) * h
+    gh = np.full(3, .4 if confounded else 0.)
+    lh = np.full(3, -.25 if confounded else 0.)
+    bh = np.full(3, .25 if confounded else 0.)
+    m = rng.binomial(1, expit(-2 - .45*z - v - .3*s + h @ gh))
+    ell = -4 + .4*z + .3*s + .3*v - .3*m + h @ lh + .7*rng.normal(size=I)
+    counts = rng.poisson(1000*np.exp(ell))
+    display = .5*z + np.sqrt(.75)*rng.normal(size=I)
+    d = display if job["scenario"] == "display" else z
+    idx = np.sort(rng.choice(I, int(I*COVERAGE), replace=False))
+    bias = .8 if job["scenario"] == "valence_bias" else .2
+    e = d[idx] + bias*v[idx] + .5*rng.normal(size=len(idx))
+    vo = v + .1*rng.normal(size=I)
+    arousal = s + rng.normal(size=I)
+    proxy_noise = rng.normal(size=(I, 3))
+    # Fixed random-effects draws across fitted specifications.
+    group = .1*rng.normal(size=(G, 2))
+    participant = .1*rng.normal(size=(P, 2))
+    slopes = (group[:, None, :] + participant[None, :, :]).reshape(G*P, 2)
+    item = .2*rng.normal(size=I)
+    content = .35*rng.normal(size=(G, I))
+    base = np.repeat(content + item, P, axis=0)
+    t = dict(z=z, v=v, s=s, h=h, m=m, ell=ell, base=base,
+             bz=slopes[:, 0].copy(), bm=slopes[:, 1], bf=.3, bv=-.5, bs=.1,
+             bh=bh, g0=-2., gz=-.45, gv=-1., gs=-.3, gh=gh,
+             f0=-4., lz=.4, ls=.3, lv=.3, lm=-.3, lh=lh, sig_f=.7)
+
+    def objective(bz):
+        t["bz"] = bz + slopes[:, 0]
+        return contrasts(t)["h2"] - job["target"]
+
+    direct = brentq(objective, -4, 4, xtol=1e-9)
+    t["bz"] = direct + slopes[:, 0]
+    truth = contrasts(t)
+    truths = dict(h2_prevalence_bridge=truth["h2"],
+                  h1_fixed_usage=truth["h1_fixed_usage"], b_z=direct,
+                  marking=truth["marking"])
+    if job["scenario"] == "display":
+        truths["h2_display"] = contrasts(t, delta=.5)["h2"]
+    eta = utilities(t)
+    logits = np.column_stack([eta, np.full(G*P, OUTSIDE)])
+    probabilities = np.exp(logits - logsumexp(logits, axis=1, keepdims=True))
+    y = np.stack([rng.multinomial(budget, p) for p in probabilities])
+    observed = dict(vo=vo, arousal=arousal, e=e, idx=idx.astype("int64"),
+                    m=m.astype("int64"), corpus=counts.astype("int64"),
+                    y=y.astype("int64"))
+    r = job["reliability"]
+    if r:
+        shift = (.3*m + .2*v)[:, None] if job["scenario"] == "differential" else 0.
+        observed["proxy"] = h + np.sqrt((1-r)/r)*proxy_noise + shift
+    return observed, truths, data_seed
+
+
+def build(G, budget, register, prior, mode):
+    """Three reusable graphs: joint, upstream E-only, downstream given L."""
+    import pymc as pm
+    import pytensor.tensor as pt
+
+    downstream = mode == "downstream"
+    upstream = mode == "upstream"
+    with pm.Model() as model:
+        if downstream:
+            z = pm.Data("z_fixed", np.zeros(I))
+            s = pm.Data("s_fixed", np.zeros(I))
+            v = pm.Data("v_fixed", np.zeros(I))
+            h = pm.Data("h_fixed", np.zeros((I, 3))) if register else pt.zeros((I, 3))
+        else:
+            z = pm.Normal("z", 0, 1, shape=I)
+            s = pm.Normal("s", 0, 1, shape=I)
+            v = pm.Normal("v", 0, 1, shape=I)
+            pm.Normal("valence_obs", v, .1, observed=pm.Data("vo", np.zeros(I)))
+            pm.Normal("arousal_obs", s, 1, observed=pm.Data("arousal", np.zeros(I)))
+            idx = pm.Data("idx", np.arange(int(I*COVERAGE), dtype="int64"))
+            pm.Normal("indicator_obs", z[idx] + pm.Normal("e_v", 0, prior)*v[idx],
+                      .5, observed=pm.Data("e", np.zeros(int(I*COVERAGE))))
+            if register:
+                coefficients = pm.Normal("h_coef", 0, prior, shape=(3, 3))
+                predictors = pt.stack([z, v, s], axis=1)
+                hs = pm.HalfNormal("h_sd", 1, shape=3)
+                h = pm.Deterministic(
+                    "h", predictors @ coefficients + hs*pm.Normal("h_raw", 0, 1, shape=(I, 3))
+                )
+                proxy = pm.Data("proxy", np.zeros((I, 3)))
+                error = pm.Data("proxy_error", np.array(1.))
+                pm.Normal("register_obs", h, error, observed=proxy)
+            else:
+                h = pt.zeros((I, 3))
+        if upstream:
+            return model
+
+        def coefficient(name):
+            return pm.Normal(name, 0, prior)
+
+        def register_coefficient(name):
+            return pm.Normal(name, 0, prior, shape=3) if register else pt.zeros(3)
+
+        g0, gz, gv, gs = [coefficient(k) for k in ("g0", "gz", "gv", "gs")]
+        gh = register_coefficient("gh")
+        m = pm.Data("m", np.zeros(I, dtype="int64"))
+        pm.Bernoulli("mark_obs", logit_p=g0 + gz*z + gv*v + gs*s + h @ gh, observed=m)
+        f0 = pm.Normal("f0", -4, 2)
+        lz, ls, lv, lm = [coefficient(k) for k in ("lz", "ls", "lv", "lm")]
+        lh = register_coefficient("lh")
+        sig_f = pm.HalfNormal("sig_f", 1)
+        ell = pm.Deterministic(
+            "ell", f0 + lz*z + ls*s + lv*v + lm*m + h @ lh
+            + sig_f*pm.Normal("ell_raw", 0, 1, shape=I)
+        )
+        pm.Poisson("corpus_obs", mu=1000*pt.exp(ell),
+                   observed=pm.Data("corpus", np.ones(I, dtype="int64")))
+        b_z, b_m, bf, bv, bs = [coefficient(k) for k in ("b_z", "b_m", "bf", "bv", "bs")]
+        bh = register_coefficient("bh")
+        group = pm.Deterministic(
+            "group", pm.HalfNormal("group_sd", .5, shape=2)
+            * pm.Normal("group_raw", 0, 1, shape=(G, 2))
+        )
+        participant = pm.Deterministic(
+            "participant", pm.HalfNormal("participant_sd", .5, shape=2)
+            * pm.Normal("participant_raw", 0, 1, shape=(P, 2))
+        )
+        slopes = (group[:, None, :] + participant[None, :, :]).reshape((G*P, 2))
+        bz = pm.Deterministic("bz", b_z + slopes[:, 0])
+        bm = pm.Deterministic("bm", b_m + slopes[:, 1])
+        item = pm.HalfNormal("item_sd", .5)*pm.Normal("item_raw", 0, 1, shape=I)
+        content = (pm.HalfNormal("content_sd", .5)
+                   * pm.Normal("content_raw", 0, 1, shape=(G, I)))
+        base = pm.Deterministic("base", pt.repeat(content + item, P, axis=0))
+        eta = base + bz[:, None]*z + bm[:, None]*m + bf*ell + bv*v + bs*s + h @ bh
+        logits = pt.concatenate([eta, pt.full((G*P, 1), OUTSIDE)], axis=1)
+        pm.Multinomial("production_obs", n=budget, p=pm.math.softmax(logits, axis=1),
+                       observed=pm.Data("y", np.zeros((G*P, I+1), dtype="int64")))
+    return model
+
+
+def sample(job, mode, data, sampling_seed):
+    import arviz as az
+    import nutpie
+
+    G, budget = DESIGNS[job["design"]]
+    register = bool(job["reliability"])
+    key = (G, budget, register, job["prior"], mode)
+    if key not in COMPILED:
+        model = build(G, budget, register, job["prior"], mode)
+        free_names = [rv.name for rv in model.free_RVs]
+        COMPILED[key] = (nutpie.compile_pymc_model(model, freeze_model=False), free_names)
+    compiled, free_names = COMPILED[key]
+    tr = nutpie.sample(compiled.with_data(**data), draws=DRAWS, tune=TUNE,
+                       chains=CHAINS, cores=1, seed=sampling_seed,
+                       target_accept=.95, progress_bar=False)
+    rh = az.rhat(tr, var_names=free_names)
+    bulk = az.ess(tr, var_names=free_names, method="bulk")
+    tail = az.ess(tr, var_names=free_names, method="tail")
+    rhat = max(float(np.max(rh[n])) for n in free_names)
+    ess = min(float(np.min(x[n])) for x in (bulk, tail) for n in free_names)
+    divergences = int(np.asarray(tr.sample_stats["diverging"]).sum())
+    finite = all(np.isfinite(np.asarray(x[n])).all()
+                 for x in (rh, bulk, tail) for n in free_names)
+    good = finite and rhat <= 1.01 and ess >= 100 and divergences == 0
+    return tr, dict(good=good, rhat=rhat, ess=ess, divergences=divergences,
+                    seed=sampling_seed, mode=mode)
+
+
+def flattened(tr, name):
+    x = np.asarray(tr.posterior[name])
+    return x.reshape((-1,) + x.shape[2:])
+
+
+def downstream_data(observed):
+    return {k: observed[k] for k in ("m", "corpus", "y")}
+
+
+def upstream_data(observed, r):
+    data = {k: observed[k] for k in ("vo", "arousal", "e", "idx")}
+    if r:
+        data.update(proxy=observed["proxy"], proxy_error=np.array(np.sqrt((1-r)/r)))
+    return data
+
+
+def posterior_contrasts(tr, observed, fixed, rng):
+    """Balanced subsampling across chains; preserve posterior dependence."""
+    names = ("bz", "bm", "bf", "bv", "bs", "base", "ell", "g0", "gz", "gv",
+             "gs", "f0", "lz", "ls", "lv", "lm", "sig_f", "b_z")
+    available = {name: flattened(tr, name) for name in names}
+    for name in ("bh", "gh", "lh", "z", "v", "s", "h"):
+        if name in tr.posterior:
+            available[name] = flattened(tr, name)
+    per_chain = tr.posterior.sizes["draw"]
+    picks = np.concatenate([
+        chain*per_chain + rng.choice(per_chain, POST_DRAWS//CHAINS, replace=False)
+        for chain in range(CHAINS)
+    ])
+    rows = []
+    for pick in picks:
+        t = {name: values[pick] for name, values in available.items()}
+        t.update(m=observed["m"])
+        if fixed is not None:
+            t.update({name.removesuffix("_fixed"): value for name, value in fixed.items()})
+        t.setdefault("h", np.zeros((I, 3)))
+        for name in ("bh", "gh", "lh"):
+            t.setdefault(name, np.zeros(3))
+        values = contrasts(t)
+        rows.append(dict(h2=values["h2"], h1_fixed_usage=values["h1_fixed_usage"],
+                         marking=values["marking"], b_z=float(t["b_z"])))
+    # Derived contrasts also require within-component chain diagnostics.
+    import arviz as az
+    diagnostic = az.from_dict(posterior={
+        name: np.array([row[name] for row in rows]).reshape(CHAINS, -1)
+        for name in rows[0]
+    })
+    # ESS at this small retained size is reported, not thresholded at 100.
+    rh = az.rhat(diagnostic)
+    finite = all(np.isfinite(np.asarray(rh[name])).all() for name in rows[0])
+    contrast_rhat = max(float(np.max(rh[name])) for name in rows[0])
+    return rows, finite and contrast_rhat <= 1.05, contrast_rhat
+
+
+def fit(job):
+    started = time.time()
+    observed, truths, data_seed = generate(job)
+    fit_seed = seed(2, job["cell"], job["rep"])
+    rng = np.random.default_rng(seed(3, job["cell"], job["rep"]))
+    upstream = upstream_data(observed, job["reliability"])
+    downstream = downstream_data(observed)
+    diagnostics, posterior = [], []
+    if job["feedback"] == "joint":
+        tr, diag = sample(job, "joint", dict(upstream, **downstream), fit_seed)
+        values, good, crhat = posterior_contrasts(tr, observed, None, rng)
+        diag.update(contrast_good=good, contrast_rhat=crhat)
+        diagnostics.append(diag)
+        posterior.extend(values)
+    else:
+        tr, diag = sample(job, "upstream", upstream, fit_seed)
+        diag.update(contrast_good=True, contrast_rhat=None)
+        diagnostics.append(diag)
+        latents = {k: flattened(tr, k) for k in ("z", "v", "s")}
+        if job["reliability"]:
+            latents["h"] = flattened(tr, "h")
+        # Independent uniform draws from the empirical upstream posterior.
+        # Draws are not weighted by downstream marginal likelihood.
+        picks = rng.integers(len(latents["z"]), size=CUT_DRAWS)
+        for component, pick in enumerate(picks):
+            fixed = {f"{k}_fixed": x[pick] for k, x in latents.items()}
+            component_seed = seed(4, job["cell"], job["rep"], component)
+            conditional, diag = sample(job, "downstream", dict(downstream, **fixed),
+                                       component_seed)
+            values, good, crhat = posterior_contrasts(conditional, observed, fixed, rng)
+            diag.update(contrast_good=good, contrast_rhat=crhat)
+            diagnostics.append(diag)
+            posterior.extend(values)
+    converged = all(d["good"] and d["contrast_good"] for d in diagnostics)
+    rows = []
+    for estimand, truth in truths.items():
+        source = "h2" if estimand.startswith("h2_") else estimand
+        x = np.array([row[source] for row in posterior])
+        lo50, hi50 = np.quantile(x, [.25, .75])
+        lo90, hi90 = np.quantile(x, [.05, .95])
+        threshold = BENCHMARKS[estimand]
+        direction = 1 if estimand == "h1_fixed_usage" else -1
+        support = lo90 > threshold if direction == 1 else hi90 < threshold
+        against = hi90 < threshold if direction == 1 else lo90 > threshold
+        meaningful_truth = direction*truth > direction*threshold
+        rows.append(dict(
+            **job, estimand=estimand, truth=truth, mean=x.mean(),
+            lo50=lo50, hi50=hi50, lo90=lo90, hi90=hi90,
+            coverage50=lo50 <= truth <= hi50, coverage90=lo90 <= truth <= hi90,
+            width50=hi50-lo50, width90=hi90-lo90, error=x.mean()-truth,
+            selected=(lo90 > 0 or hi90 < 0), meaningful_truth=meaningful_truth,
+            support=support, against=against, threshold=threshold,
+            p_direction=np.mean(direction*x > 0),
+            p_beyond=np.mean(direction*x > direction*threshold),
+            good=converged, data_seed=data_seed, fit_seed=fit_seed,
+            seconds=time.time()-started,
+        ))
+    return rows, dict(**job, status="converged" if converged else "diagnostic_failure",
+                      data_seed=data_seed, fit_seed=fit_seed,
+                      diagnostics=diagnostics, seconds=time.time()-started)
+
+
+def summarize(frame, failures):
+    records = []
+    keys = ["cell", "design", "scenario", "target", "feedback", "reliability",
+            "prior", "estimand"]
+
+    def statistic(record, name, values, binary=False):
+        values = np.asarray(values, dtype=float)
+        n = len(values)
+        mean = float(values.mean()) if n else np.nan
+        se = (np.sqrt(mean*(1-mean)/n) if n and binary else
+              values.std(ddof=1)/np.sqrt(n) if n > 1 else np.nan)
+        record.update({name: mean, name+"_mcse": se, name+"_n": n})
+
+    for key, group in frame.groupby(keys, sort=True):
+        record = dict(zip(keys, key))
+        x = group[group.good]
+        record.update(attempted=len(group), converged=len(x),
+                      diagnostic_failures=len(group)-len(x))
+        for name in ("coverage50", "coverage90"):
+            statistic(record, name, x[name], binary=True)
+        for name in ("width50", "width90"):
+            statistic(record, name, x[name])
+        statistic(record, "bias", x.error)
+        nonnull = x[np.abs(x.truth) > 1e-8]
+        selected = x[x.selected]
+        selected_nonnull = nonnull[nonnull.selected]
+        statistic(record, "sign_error", nonnull["mean"]*nonnull.truth < 0, True)
+        statistic(record, "selected_sign_error",
+                  selected_nonnull["mean"]*selected_nonnull.truth < 0, True)
+        statistic(record, "selected_exaggeration",
+                  np.abs(selected_nonnull["mean"]/selected_nonnull.truth))
+        statistic(record, "conditional_absolute_bias", np.abs(selected.error))
+        false_population = x[~x.meaningful_truth]
+        statistic(record, "false_meaningful_support", false_population.support, True)
+        records.append(record)
+    # Exceptions and convergence failures remain visible even in empty cells.
+    return pd.DataFrame(records), pd.DataFrame(failures)
+
+
+def main():
+    parser = argparse.ArgumentParser(description=__doc__)
+    commands = parser.add_subparsers(dest="command", required=True)
+    commands.add_parser("pilot", help="two replicates of one baseline joint cell")
+    run = commands.add_parser("run")
+    run.add_argument("--reps", type=int, required=True)
+    run.add_argument("--workers", type=int, default=1)
+    args = parser.parse_args()
+    reps = 2 if args.command == "pilot" else args.reps
+    workers = 1 if args.command == "pilot" else args.workers
+    if reps < 1 or workers < 1:
+        parser.error("reps and workers must be positive")
+    selected_cells = list(cells())
+    if args.command == "pilot":
+        selected_cells = selected_cells[:1]
+    jobs = [dict(c, rep=rep) for c in selected_cells for rep in range(reps)]
+    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
+    output = ROOT / "results" / "d1c"
+    output.mkdir(parents=True, exist_ok=True)
+    (ROOT / "logs").mkdir(exist_ok=True)
+    raw_path = output / f"{args.command}-{stamp}-fits.csv"
+    summary_path = output / f"{args.command}-{stamp}-summary.csv"
+    failure_path = output / f"{args.command}-{stamp}-failures.csv"
+    started = time.time()
+    rows, failures = [], []
+    with ProcessPoolExecutor(max_workers=workers) as pool:
+        pending = {pool.submit(fit, job): job for job in jobs}
+        for future in as_completed(pending):
+            job = pending[future]
+            try:
+                result, status = future.result()
+                rows.extend(result)
+                failures.append(status)
+                pd.DataFrame(result).to_csv(raw_path, mode="a",
+                                            header=not raw_path.exists(), index=False)
+                print(job["cell"], job["rep"], status["status"],
+                      round(status["seconds"], 1), "seconds", flush=True)
+            except Exception as exc:
+                failures.append(dict(**job, status="exception", error=repr(exc),
+                                     fit_seed=seed(2, job["cell"], job["rep"])))
+                print(job, repr(exc), flush=True)
+    if rows:
+        summary, failed = summarize(pd.DataFrame(rows), failures)
+        summary.to_csv(summary_path, index=False)
+    else:
+        failed = pd.DataFrame(failures)
+    # Diagnostic detail is retained in JSON; flatten failure CSV for inspection.
+    failed.drop(columns=["diagnostics"], errors="ignore").to_csv(failure_path, index=False)
+    packages = {}
+    for package in ("numpy", "pandas", "scipy", "pymc", "pytensor", "nutpie", "arviz"):
+        try:
+            packages[package] = version(package)
+        except PackageNotFoundError:
+            packages[package] = None
+
+    def git(*arguments):
+        return subprocess.run(["git", *arguments], cwd=ROOT, capture_output=True,
+                              text=True, check=False).stdout.strip()
+
+    log = dict(timestamp=stamp, script="scripts/d1c/d1c.py", args=vars(args),
+               root_seed=SEED, python=sys.version, platform=platform.platform(),
+               packages=packages, git_sha=git("rev-parse", "HEAD"),
+               git_dirty=bool(git("status", "--porcelain")),
+               sampler=dict(draws=DRAWS, tune=TUNE, chains=CHAINS, cores=1,
+                            cut_draws=CUT_DRAWS, contrast_draws=POST_DRAWS),
+               pytensor_flags=os.environ.get("PYTENSOR_FLAGS"),
+               cells=selected_cells, statuses=failures,
+               outputs=[str(p.relative_to(ROOT)) for p in
+                        (raw_path, summary_path, failure_path) if p.exists()],
+               elapsed_seconds=time.time()-started)
+    path = ROOT / "logs" / f"d1c-{stamp}.json"
+    path.write_text(json.dumps(log, indent=2, default=str))
+    print("log:", path.relative_to(ROOT))
+
+
+if __name__ == "__main__":
+    main()

Not run or runtime-validated. This first version omits act-type measurement, affix-specific effects, transport scenarios beyond construct divergence, and production posterior predictive checks. Origin uses a continuous approximation; cut integration and predictive quadrature require accuracy checks.

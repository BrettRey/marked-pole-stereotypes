# D1 engine check: can brms express the strand B joint model?
# Spec: scripts/d1/README.md, "Engine check (brms)". Time-boxed to one hour.
# Data: one scenario-1 dataset (small, rep 0, prevalence indicator r = .8),
# written by `d1.py export-brms` to results/d1/brms_check/.
#
# Differences from the PyMC model, accepted for a feasibility check:
# latent residual SDs are fixed at 1 (PyMC fixes the latent's total variance
# at 1), and group intercepts are random rather than fixed.

suppressPackageStartupMessages(library(brms))

dir <- "results/d1/brms_check"
items <- read.csv(file.path(dir, "items.csv"))
counts <- read.csv(file.path(dir, "counts_long.csv"))
n_items <- nrow(items)

item_rows <- data.frame(
  sub_item = TRUE, sub_count = FALSE,
  item = items$item, group = NA, n = NA,
  v = items$v, m = items$m, f = items$f, a = items$a, e = items$e,
  rho = NA_real_, s = NA_real_
)
count_rows <- data.frame(
  sub_item = FALSE, sub_count = TRUE,
  item = counts$item, group = counts$group, n = counts$n,
  v = items$v[counts$item], m = items$m[counts$item], f = items$f[counts$item],
  a = NA_real_, e = NA_real_, rho = NA_real_, s = NA_real_
)
dat <- rbind(item_rows, count_rows)

forms <-
  bf(rho | mi() + subset(sub_item) ~ 0 + v) +
  bf(s | mi() + subset(sub_item) ~ 0 + v) +
  bf(f | subset(sub_item) ~ 1 + mi(rho) + mi(s) + v + m) +
  bf(a | subset(sub_item) ~ 1 + mi(s)) +
  bf(e | subset(sub_item) ~ 1 + mi(rho) + v) +
  bf(m | subset(sub_item) ~ 1 + mi(rho) + v + mi(s), family = bernoulli()) +
  bf(n | subset(sub_count) ~ 1 + mi(rho, idx = item) + m + f + v + (1 | item) + (1 | group),
     family = negbinomial()) +
  set_rescor(FALSE)

pri <- c(
  prior(normal(0, 1), class = "b", resp = "rho"),
  prior(normal(0, 1), class = "b", resp = "s"),
  prior(constant(1), class = "sigma", resp = "rho"),
  prior(constant(1), class = "sigma", resp = "s"),
  prior(normal(0, 1), class = "b", resp = "f"),
  prior(normal(0, 1), class = "bsp", resp = "f"),
  prior(normal(0, 1), class = "bsp", coef = "mirho", resp = "f", lb = 0),
  prior(constant(1), class = "bsp", coef = "mis", resp = "a"),
  prior(constant(1), class = "bsp", coef = "mirho", resp = "e"),
  prior(normal(0, 1), class = "b", resp = "e"),
  prior(normal(0, 1), class = "b", resp = "m"),
  prior(normal(0, 1), class = "bsp", resp = "m"),
  prior(normal(0, 1), class = "b", resp = "n"),
  prior(normal(0, 1), class = "bsp", resp = "n")
)

out <- character()
say <- function(...) { line <- paste0(...); cat(line, "\n"); out <<- c(out, line) }
say("brms ", as.character(packageVersion("brms")), "; rstan ", as.character(packageVersion("rstan")),
    "; R ", R.version$major, ".", R.version$minor)

t0 <- Sys.time()
fit <- tryCatch(
  brm(forms, data = dat, prior = pri, chains = 4, cores = 4, iter = 2000, warmup = 1000,
      control = list(adapt_delta = 0.9), seed = 20261008, backend = "rstan", refresh = 0),
  error = function(e) e
)
secs <- as.numeric(difftime(Sys.time(), t0, units = "secs"))

if (inherits(fit, "error")) {
  say("RESULT: brms could not fit the model after ", round(secs), " s.")
  say("ERROR: ", conditionMessage(fit))
} else {
  s <- summary(fit)
  fx <- as.data.frame(fixef(fit))
  rh <- rhat(fit)
  np <- nuts_params(fit)
  div <- sum(subset(np, Parameter == "divergent__")$Value)
  ess <- neff_ratio(fit)
  say("RESULT: fitted in ", round(secs), " s (compile + sample).")
  say("max R-hat: ", round(max(rh, na.rm = TRUE), 3), "; divergences: ", div,
      "; min ESS ratio: ", round(min(ess, na.rm = TRUE), 3))
  keep <- grepl("^(n_|m_)", rownames(fx)) | grepl("mirho|mis", rownames(fx))
  write.csv(fx, file.path(dir, "brms_fixef.csv"))
  say("Fixed effects of interest:")
  out <- c(out, capture.output(print(round(fx[keep, ], 3))))
  sp <- as.data.frame(posterior_summary(fit, variable = "^bsp_", regex = TRUE))
  write.csv(sp, file.path(dir, "brms_bsp.csv"))
  out <- c(out, "Special (mi) effects:", capture.output(print(round(sp, 3))))
}
writeLines(out, file.path(dir, "brms_check_result.txt"))
writeLines(capture.output(sessionInfo()), file.path(dir, "brms_sessionInfo.txt"))

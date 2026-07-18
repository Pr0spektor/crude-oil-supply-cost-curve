# Crude-oil supply cost curve — R port of the core engine.
# Mirrors src/costcurve.py and js/costcurve.js so results reconcile across languages.
# Run the self-test:  Rscript r/costcurve.R
#
# A segment data.frame has columns: name, production_mmbd, breakeven_full, cash_cost.

build_curve <- function(df, cost = "full") {
  key <- if (cost == "full") "breakeven_full" else "cash_cost"
  d <- df[order(df[[key]]), , drop = FALSE]
  d$cost <- d[[key]]
  d$cum_end <- cumsum(d$production_mmbd)
  d$cum_start <- d$cum_end - d$production_mmbd
  rownames(d) <- NULL
  d
}

total_supply <- function(df) sum(df$production_mmbd)

marginal_barrel <- function(curve, demand_mmbd) {
  hit <- which(demand_mmbd <= curve$cum_end + 1e-12)
  if (length(hit) > 0) {
    i <- hit[1]
    list(marginal_cost = curve$cost[i], marginal_segment = curve$name[i], supplied = TRUE)
  } else {
    n <- nrow(curve)
    list(marginal_cost = curve$cost[n], marginal_segment = curve$name[n], supplied = FALSE)
  }
}

uneconomic_volume <- function(df, price, cost = "full") {
  key <- if (cost == "full") "breakeven_full" else "cash_cost"
  at_risk  <- sum(df$production_mmbd[df[[key]] >  price])
  economic <- sum(df$production_mmbd[df[[key]] <= price])
  tot <- at_risk + economic
  list(price = price, at_risk_mmbd = at_risk, economic_mmbd = economic,
       at_risk_share = if (tot > 0) at_risk / tot else 0)
}

# ---- self-test (same fixture as the Python and JS suites) ----
if (sys.nframe() == 0) {
  fix <- data.frame(
    name = c("A", "B", "C"),
    production_mmbd = c(10, 5, 5),
    breakeven_full = c(20, 50, 35),
    cash_cost = c(10, 30, 25),
    stringsAsFactors = FALSE
  )
  c1 <- build_curve(fix, "full")
  stopifnot(identical(c1$name, c("A", "C", "B")))          # cheapest-first
  stopifnot(isTRUE(all.equal(c1$cum_end[3], 20)))          # cumulative closes at total
  stopifnot(total_supply(fix) == 20)
  mb <- marginal_barrel(c1, 12)
  stopifnot(mb$marginal_segment == "C", mb$marginal_cost == 35, mb$supplied)
  stopifnot(!marginal_barrel(c1, 25)$supplied)
  u <- uneconomic_volume(fix, 40, "full")
  stopifnot(u$at_risk_mmbd + u$economic_mmbd == 20)
  stopifnot(uneconomic_volume(fix, 15)$at_risk_mmbd == 20)
  stopifnot(uneconomic_volume(fix, 60)$at_risk_mmbd == 0)
  cat("R self-test: all checks passed.\n")
}

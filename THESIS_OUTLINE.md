# Thesis Outline — Multi-Echelon Inventory Optimisation via Digital-Twin Simulation

**Working title:** *A Digital-Twin Simulation Framework for Joint Inventory and Transport Optimisation in Multi-Echelon Supply Chains*

**Author:** Sakthe Balan
**Programme:** Dual Degree Project (DDP)
**Status:** Draft outline — work-to-date is implemented in this repository; chapters are mapped to the supporting code/output artefacts.

---

## Abstract (to be written last)

Two-paragraph summary covering: (i) the gap between closed-form MEIO models and real-world supply chains with capacity-constrained transport, supply disruptions, and stochastic dynamics; (ii) the digital-twin framework built in this DDP, the experiments executed (E0–E4), and the headline result that joint inventory + transport optimisation outperforms either silo alone.

---

## Chapter 1 — Introduction

**1.1  Multi-Echelon Inventory Optimisation: the problem.** Why holding inventory at multiple stages (supplier → DC → retailer) is harder than single-echelon — coupling of stockouts, lead-time amplification, and bullwhip.

**1.2  Why a digital twin?** Closed-form analytical models (newsvendor, Clark-Scarf) require restrictive assumptions: backlog symmetry, infinite supply upstream, deterministic lead times, no transport capacity. Real supply chains violate all four. A digital-twin simulator lets us evaluate any policy under realistic conditions.

**1.3  Research questions.**
- **RQ1.** Does *joint* inventory + transport optimisation outperform siloed inventory-only or transport-only optimisation in cost and service level?
- **RQ2.** How sensitive are optimal policies to supply-side disruption (a node down for *N* days)?
- **RQ3.** Does the bullwhip effect persist under optimised policies, or does optimisation suppress it?

**1.4  Contributions.** (a) A modular, testable digital-twin framework with 7 inventory policies; (b) Optuna-TPE-based joint optimiser with hard fill-rate constraints; (c) Pareto-frontier analysis of cost vs service trade-off; (d) supply-disruption and weight-capacity modelling absent from prior open simulators.

**1.5  Thesis structure.** Brief tour of the remaining chapters.

---

## Chapter 2 — Literature Review

**2.1  Single-echelon foundations.** Newsvendor, base-stock, (s,S), economic order quantity (EOQ).

**2.2  Multi-echelon optimality — Clark & Scarf (1960).** Echelon-base-stock policies, sufficient conditions, why optimality breaks under capacity constraints.

**2.3  Periodic-review and cyclic policies.** (R,S), (R,Q), (k,m)-cycle scheduling.

**2.4  The bullwhip effect.** Lee, Padmanabhan, Whang (1997) — four causes; metric: order CV² / demand CV².

**2.5  Transport consolidation in inventory models.** Why classic MEIO ignores it, and when it dominates the cost function.

**2.6  Simulation-optimisation methods.** Genetic algorithms, Bayesian optimisation, TPE (Bergstra et al.), why TPE is a good fit for ~10–50 dimensional mixed-integer search spaces.

**2.7  Existing software.** SimPy (general DES — no MEIO domain primitives), AnyLogic (commercial, closed-source), `simopt` library, Optuna. Identifies the gap this DDP fills: an open, MEIO-specific, batteries-included simulation + optimisation framework.

---

## Chapter 3 — Digital-Twin Architecture

**3.1  Network topology.** 1-supplier → 1-warehouse → 3-retailers ("1N3"). Generalisable to arbitrary DAGs.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/network.py`, `config/1n3_5sku.json`

**3.2  Discrete-event simulation loop.** Daily tick driving: receive shipments → demand realisation → backlog clearing → policy decision → order placement → dispatch planning.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/simulator.py` (`Simulator.run`)

**3.3  Node state model.** On-hand, in-pipeline, external/internal backlog, placed-but-unfulfilled orders.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/node.py`

**3.4  Transport layer.** Lanes, transport options (mode, capacity, lead time, cost tiers), pluggable load planner. The default `GreedyLoadPlanner` enforces simultaneous **volume** and **weight** caps and supports a `min_dispatch_utilization` threshold with `max_dispatch_wait` timeout.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/transport.py`

**3.5  Cost model.** Total cost = holding + transport + ordering + shortage. Per-tick accumulation; reported with warm-up exclusion.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/simulator.py`

**3.6  Configuration schema.** JSON-driven scenarios. Validator catches malformed inputs early.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/config_validator.py`, `config/1n3_5sku.json`

**3.7  Supply disruption modelling.** Configurable node downtime; orders accumulate as backlog and clear when the node recovers.
&nbsp;&nbsp;&nbsp;&nbsp;→ `engine/simulator.py` (`disruptions` field)

---

## Chapter 4 — Inventory Policies

A common API across all policies:
`order_qty(on_hand, backlog_external, backlog_children, pipeline_in, t=None) -> int`.

**4.1  Analytical baseline — newsvendor base-stock.** S = μ·(L+1) + z·σ·√(L+1).
&nbsp;&nbsp;&nbsp;&nbsp;→ `policies/base_stock.py`

**4.2  Reorder-point family — (s,S) and (R,Q).** Continuous-review fixed-quantity and order-up-to-S variants.
&nbsp;&nbsp;&nbsp;&nbsp;→ `policies/ss_policy.py`, `policies/rq_policy.py`

**4.3  Periodic-review — (R,S) and order-up-to with phase offset.** Aligned vs staggered review schedules.
&nbsp;&nbsp;&nbsp;&nbsp;→ `policies/order_up_to.py`, `policies/periodic_review.py`

**4.4  Cyclic policies — (k,m).** k orders per m-day cycle; explores consolidation-friendly review timing.
&nbsp;&nbsp;&nbsp;&nbsp;→ `policies/km_cycle.py`

**4.5  Echelon base-stock (Clark & Scarf).** Echelon inventory position computed by DFS over downstream nodes; the simulator passes the EIP to the policy as `pipeline_in`.
&nbsp;&nbsp;&nbsp;&nbsp;→ `policies/echelon_stock.py`, `engine/simulator.py` (`_echelon_pipeline`)

**4.6  Discussion.** Trade-offs across the policy zoo: ease of analysis vs realism vs optimisation amenability.

---

## Chapter 5 — Optimisation Framework

**5.1  Why Optuna TPE.** Sample-efficient on mixed-integer spaces, supports pruning and multi-objective extensions.

**5.2  Search-space encoding — inventory.** Per-(node, SKU) integer base-stock levels in [0.3·S_analytical, 3·S_analytical] with a 10-unit floor.

**5.3  Search-space encoding — transport.** Per-lane `min_dispatch_utilization` ∈ [0.0, 0.9].

**5.4  Joint search.** Single Optuna study over the union of the two spaces.
&nbsp;&nbsp;&nbsp;&nbsp;→ `optimizer/optimize.py`

**5.5  Constrained optimisation — minimum fill rate.** Soft constraint: penalty of 1M per percentage-point shortfall under target. Best feasible trial selected; falls back to best-overall if none feasible.

**5.6  Pareto exploration.** Re-run joint optimisation at fill-rate targets 80%, 85%, 88%, 90%, 92%, 94%, 96%, 98%; plot non-dominated frontier.
&nbsp;&nbsp;&nbsp;&nbsp;→ `scripts/run_experiments.py` (`exp_E4`)

**5.7  Re-evaluation discipline.** Best params are saved to JSON and re-evaluated in a fresh simulator run before reporting — guards against optimiser overfitting / metric drift.

---

## Chapter 6 — Experimental Methodology

**6.1  Dataset.** 5 SKUs, 365-day horizon, demand profile from `inputs/`.
&nbsp;&nbsp;&nbsp;&nbsp;→ `config/1n3_5sku.json`, `inputs/`

**6.2  Warm-up exclusion.** First *N* days dropped from KPI computation to avoid initial-inventory bias.

**6.3  Multi-seed statistical validation.** 95% confidence intervals across multiple seeds; side-by-side comparison of two configurations with CI overlap test (Welch's t).
&nbsp;&nbsp;&nbsp;&nbsp;→ `scripts/multi_seed_validation.py`

**6.4  Bullwhip metric.** Order CV² / demand CV² per (node, SKU), warm-up–excluded.

**6.5  Experiments E0–E4.**
| ID  | Title | Hypothesis |
|-----|-------|------------|
| E0  | Analytical baseline | High transport cost, acceptable fill |
| E1a | Fixed 25% dispatch threshold | Cuts transport, hurts fill |
| E1b | Transport-only optimisation | Beats E1a, limited by fixed inventory |
| E2  | Inventory-only optimisation | Improves fill, marginal cost gain |
| E3  | **Joint optimisation (main)** | Lowest cost at target fill |
| E4  | Pareto frontier | Diminishing returns near 100% fill |

&nbsp;&nbsp;&nbsp;&nbsp;→ `scripts/run_experiments.py` (`EXPERIMENT_META`)

**6.6  Reproducibility.** Each run writes a self-contained `outputs/experiments_<ts>/` directory with `params.json`, `summary.md`, raw CSV logs, and plots.

---

## Chapter 7 — Results and Discussion

**7.1  E0 — Analytical baseline.** Cost decomposition; identification of transport as the dominant cost component.

**7.2  E1a — Fixed-threshold dispatch.** Demonstrates that naive consolidation without inventory adjustment is counter-productive (fills drop below 92%).

**7.3  E1b — Transport-only optimisation.** Shows the limit of single-axis optimisation.

**7.4  E2 — Inventory-only optimisation.** Improves service at modest holding-cost increase.

**7.5  E3 — Joint optimisation (the headline result).** Cost reduction vs E0 at ≥92% fill; explains the trade-off mechanism (slightly elevated S enables higher consolidation thresholds).
&nbsp;&nbsp;&nbsp;&nbsp;→ `outputs/experiments_*/E3/summary.md`

**7.6  E4 — Pareto frontier.** Cost-vs-fill trade-off curve; quantifies the marginal cost of each percentage point of service.
&nbsp;&nbsp;&nbsp;&nbsp;→ `outputs/experiments_*/plots/pareto_frontier.png`

**7.7  Bullwhip analysis.** Per-experiment bullwhip-ratio table; whether joint optimisation suppresses amplification.
&nbsp;&nbsp;&nbsp;&nbsp;→ `outputs/experiments_*/plots/bullwhip.png`

**7.8  Statistical robustness.** Multi-seed CIs for E0 and E3; CI-overlap test for whether the E3 improvement is statistically significant.
&nbsp;&nbsp;&nbsp;&nbsp;→ `scripts/multi_seed_validation.py`

**7.9  Sensitivity to supply disruption (planned extension).** Re-run E0 and E3 with a 14-day supplier outage; report degradation in fill rate and cost.

---

## Chapter 8 — Discussion

**8.1  Answering the research questions.**
- **RQ1** — Joint optimisation outperforms either silo: see §7.5.
- **RQ2** — Supply disruption degrades both configurations, but the optimised configuration buffers better through elevated DC inventory: see §7.9.
- **RQ3** — Bullwhip is partially suppressed but not eliminated under joint optimisation: see §7.7.

**8.2  Practical recommendations.** When transport cost dominates, (i) co-optimise inventory and dispatch; (ii) accept small holding-cost increases to unlock consolidation; (iii) use the Pareto frontier to negotiate service-level agreements.

**8.3  Limitations.** Deterministic lead times; single-echelon DC layer; demand is read from a CSV rather than forecast online; no transshipment between retailers.

---

## Chapter 9 — Conclusion and Future Work

**9.1  Summary of contributions.** Reiterates §1.4 with quantitative results from Chapter 7.

**9.2  Open-source framework vision.** Forward-reference to `ROADMAP.md`: stochastic lead times, demand forecasting layer, capacity-constrained nodes, lateral transshipment, RL-based policies, multi-objective optimisation, web dashboard, industry-specific config templates.

**9.3  Closing remarks.**

---

## Appendices

- **Appendix A — Configuration schema reference** (full JSON spec).
- **Appendix B — Per-experiment policy parameters** (params.json contents).
- **Appendix C — Test suite summary** (~80 pytest invariants and behaviours).
- **Appendix D — Reproducing the results** (CLI commands).

---

## Code → Chapter Map (quick index)

| Chapter | Primary code |
|---------|--------------|
| 3 | `engine/simulator.py`, `engine/node.py`, `engine/transport.py`, `engine/network.py`, `engine/config_validator.py` |
| 4 | `policies/base_stock.py`, `policies/ss_policy.py`, `policies/rq_policy.py`, `policies/order_up_to.py`, `policies/km_cycle.py`, `policies/periodic_review.py`, `policies/echelon_stock.py` |
| 5 | `optimizer/optimize.py` |
| 6 | `scripts/run_experiments.py`, `scripts/multi_seed_validation.py` |
| 7 | `outputs/experiments_<ts>/` artefacts and `scripts/plot_results.py` |

# DDP — Open-Source MEIO Framework Roadmap

**Vision.** Make this repo the *batteries-included* open-source framework that any organisation — from a 5-store retailer to a multi-echelon FMCG distributor — can clone, configure, and use to simulate, stress-test, and optimise their own supply chain.

The current codebase already provides: a discrete-event simulator, 7 inventory policies, transport consolidation with weight + volume capacity, supply-disruption modelling, an Optuna-based optimiser (inventory / transport / joint modes), Pareto exploration, multi-seed statistical validation, and report-grade plots. The roadmap below is what would turn that solid prototype into a production-quality framework.

Each item lists **what** it is, **why** industry needs it, **where** it slots into the existing module structure, and a rough **effort** estimate (S = ≤1 day, M = 2–5 days, L = 1–2 weeks, XL = a month+).

---

## Tier A — Realism / generality (highest leverage)

### A1. Stochastic lead times — **M**
Sample lead time per shipment from a configurable distribution (lognormal / triangular / empirical) instead of a deterministic constant.
- *Why:* Real lead times are the single biggest source of variance in supply chains; deterministic lead times make optimised policies look better than they are.
- *Slot:* extend `TransportOption` in `engine/transport.py` to accept `lead_time_dist`; sample at dispatch time.

### A2. Generic N-echelon topology — **M**
Configs currently assume 1N3. Make `Network` accept arbitrary DAGs (factory → DC → hub → retailer; multi-supplier; cross-dock).
- *Why:* Industry topologies are never 1-1-3.
- *Slot:* `engine/network.py` is already graph-based — add validators in `config_validator.py` and ship example configs (`config/2n2n9.json`, `config/serial_4echelon.json`).

### A3. Demand forecasting layer — **L**
Today demand is read from a CSV (perfect foresight). Add a `forecasters/` module: moving average, exponential smoothing, Holt-Winters, ARIMA, optional ML backend (Prophet, LightGBM). Policies query the forecaster instead of using a global mean.
- *Why:* Real policies operate on forecasts, not realised demand; forecast error is a first-class driver of safety stock.
- *Slot:* new `forecasters/` package; pass a `Forecaster` instance into the policy builder in `scripts/run_simulation.py::build_from_config`.

### A4. Stochastic demand generators — **M**
Pluggable demand processes when no real data is available: Poisson, Negative Binomial, intermittent (Croston), seasonal sine + trend, promotional spikes, weekday-of-week effects.
- *Why:* Lets users without their own data start simulating immediately.
- *Slot:* extend `engine/simulator.py`'s demand path; add a `demand_generators/` module.

### A5. Order-cancellation and customer-patience model — **S**
Currently unfulfilled demand backlogs forever (or is fully lost — config-dependent). Add a "customer patience" parameter: backlog ages and is cancelled after *k* days.
- *Why:* Real customers walk away.
- *Slot:* `engine/node.py::backlog_external` becomes a deque of (qty, day_arrived).

---

## Tier B — Industry-grade features

### B1. Node capacity constraints — **M**
Warehouse storage caps (max units on hand), throughput caps (max units shipped/day), dock door limits.
- *Why:* Optimisers love to set base-stock to infinity; physical warehouses don't.
- *Slot:* extend `Node` with `storage_capacity`, `throughput_capacity` fields; enforce in `Simulator`.

### B2. Multi-mode transport with switching cost — **M**
Truck vs rail vs air per lane, with mode-selection driven by urgency / lead time / cost.
- *Why:* Mode switching is a real lever — express air for emergency replenishment, rail for steady-state.
- *Slot:* `engine/transport.py::ModeSelector` protocol already exists — implement `UrgencyAwareModeSelector` and similar.

### B3. Lateral transshipment between retailers — **L**
Retailer-to-retailer rebalancing when one is short and a sibling has excess.
- *Why:* Major lever in retail and parts distribution.
- *Slot:* new `engine/lateral_transshipment.py`; new edges in `Network`; new policy hook.

### B4. Per-tier service-level constraints — **S**
A-class SKUs at 98%, B-class at 95%, C-class at 90%, instead of a single network-wide target.
- *Why:* All real SLAs are tiered.
- *Slot:* extend `min_fill_rate` arg in `optimizer/optimize.py` to accept a `dict[sku, float]`.

### B5. Inventory carrying cost as % of value — **S**
Replace flat `holding_cost` with `holding_rate * unit_value * on_hand`.
- *Why:* Standard finance practice; lets cost-of-money sensitivities be analysed.
- *Slot:* `Node.holding_cost` becomes a function; cost ledger updates in `engine/simulator.py`.

### B6. Disruption library — **M**
Beyond node downtime: lane disruption (port closure), capacity reduction (factory at 50%), demand spike (promo / pandemic), supplier price change. Schedulable or sampled.
- *Why:* Resilience analysis is a core ask post-COVID.
- *Slot:* extend the `disruptions: List[Dict]` schema; add a `disruption_types` registry.

### B7. Procurement contracts — **L**
Volume commitments, take-or-pay clauses, quantity discounts (price breaks at thresholds).
- *Why:* Real procurement is contractual, not spot.
- *Slot:* new `engine/contracts.py`; integrated into ordering cost path.

### B8. Returns / reverse logistics — **L**
Configurable return rate per SKU, refurbishment lead time, parallel reverse-flow inventory.
- *Why:* Critical in e-commerce, electronics, automotive.

---

## Tier C — Optimisation depth

### C1. Reinforcement learning policy — **L**
Wrap `Simulator` as a Gym environment; train PPO / DQN / SAC agents and benchmark against analytical policies.
- *Why:* RL is increasingly the published state-of-the-art on MEIO benchmarks.
- *Slot:* new `policies/rl_policy.py` (loads a trained model) and `envs/gym_wrapper.py`.

### C2. Bayesian / GP surrogate optimiser — **M**
Alternative to Optuna TPE for cases where each evaluation is expensive (e.g. multi-seed averaging).
- *Slot:* extend `optimizer/optimize.py` with a `sampler` arg.

### C3. Multi-objective optimisation (NSGA-II) — **M**
Today's E4 Pareto exploration runs N constrained single-objective searches. Switching to NSGA-II / MOTPE produces the entire frontier in one study.
- *Slot:* `optimizer/optimize.py` — add `multi_objective` mode using `optuna.create_study(directions=...)`.

### C4. Robust / chance-constrained optimisation — **L**
Optimise the worst-case (or 95th-percentile) cost across disruption scenarios, not the expected case.
- *Why:* Real planners care about tail risk.
- *Slot:* extend the optimiser objective to evaluate over a *set* of scenarios.

### C5. Online / adaptive policies — **L**
Policies that update parameters during the simulation based on observed forecast error.
- *Slot:* new `policies/adaptive_*.py`; add a `policy.update(observed_demand)` hook in the simulator loop.

---

## Tier D — Framework & UX (open-source readiness)

### D1. Python package layout — **S**
Convert to installable `pip install ddp-meio`. Move scripts to entry points.
- *Slot:* add `pyproject.toml`, `setup.cfg`; restructure imports; entry points like `ddp-run`, `ddp-experiments`, `ddp-plot`.

### D2. Web dashboard — **L**
Streamlit / Dash UI: upload a config, run experiments, view live KPIs and plots, download a report.
- *Why:* Non-technical supply-chain managers can't `python scripts/run_simulation.py ...`.
- *Slot:* new `dashboard/` package; reuse existing CSV outputs and plot functions.

### D3. Interactive Plotly plots — **S**
Alongside the static matplotlib plots in `plot_results.py`, emit interactive HTML versions (zoom, hover, toggle traces).
- *Slot:* extend `scripts/plot_results.py` with a `--interactive` flag.

### D4. Config wizard / JSON-Schema validation — **M**
JSON-Schema for all config files (auto-generated docs + IDE autocomplete) plus a CLI wizard that walks a new user through generating a config interactively.
- *Slot:* extend `engine/config_validator.py`; new `scripts/config_wizard.py`.

### D5. Industry config templates — **M**
Prebuilt configs for retail (high SKU count, daily review), automotive (low SKU count, weekly review, long lead times), pharma (regulatory holding constraints), FMCG cold-chain (weight-dominated transport).
- *Slot:* `config/templates/<industry>/`.

### D6. Public README + landing page — **S**
Quickstart, badges (CI, coverage, PyPI), screenshot, citation. Separate from `CLAUDE.md` (which is for AI agents).

### D7. Documentation site (MkDocs / Sphinx) — **M**
Module reference, tutorials ("your first MEIO simulation in 10 minutes"), how-to guides, API docs.

---

## Tier E — Validation, rigour, governance

### E1. Benchmark against closed-form Clark-Scarf — **M**
Build a serial-line scenario where the analytical optimum is known; verify the simulator + optimiser converge to it. Proves correctness.
- *Slot:* new `tests/test_clark_scarf_benchmark.py` and `config/serial_clark_scarf.json`.

### E2. Real-data case study — **L**
Wire a public dataset (M5 Walmart, Corporación Favorita Grocery) into a `config/` template and reproduce results.
- *Why:* Strongest possible credibility signal for an open-source framework.

### E3. CI pipeline (GitHub Actions) — **S**
On every push: pytest, lint (ruff), type-check (mypy), one smoke experiment run.

### E4. Property-based tests (Hypothesis) — **S**
Invariants: inventory ≥ 0, no negative orders, mass balance (orders out = arrivals in over horizon ± in-flight), monotonicity (raising S can never reduce service).
- *Slot:* new `tests/test_invariants_hypothesis.py`.

### E5. Performance benchmarks — **S**
Measure simulator wall-clock vs horizon length; fail CI if >2× regression.

### E6. Citation file (`CITATION.cff`) and DOI — **S**
Make the framework academically citable.

### E7. Contributor guide and code of conduct — **S**
Standard open-source onboarding.

---

## Suggested execution order

For a 6-month push toward "publishable open-source release":

1. **Months 1–2** — A1 (stochastic lead times), A2 (generic topology), A3 (forecasting), B1 (node capacity), E1 (Clark-Scarf benchmark) → unlocks RQ-relevant experimentation.
2. **Months 3–4** — B2 (multi-mode transport), B6 (disruption library), C3 (NSGA-II), E2 (real-data case study) → strengthens the empirical chapter and resilience analysis.
3. **Months 5–6** — D1 (pip package), D6 (README), D7 (docs site), E3 (CI), E6 (DOI), C1 (RL benchmark as a stretch goal) → makes the project externally usable and citable.

Items not on the critical path (B3 transshipment, B7 contracts, B8 returns, C5 adaptive policies, D2 dashboard) are good "v2" work after the first public release.

---

## How this maps to the thesis

- Tier A items extend Chapter 3 (Architecture) and add new sections to Chapter 7 (Results).
- Tier B items add resilience and capacity sub-sections to Chapter 7; Item B6 + a planned disruption sweep answers RQ2.
- Tier C items add a new chapter or extended Chapter 5 — *Advanced Optimisation*.
- Tier D items belong in Chapter 9 (Future Work) as the "open-source framework" deliverable.
- Tier E items support Chapter 8's "Limitations" and Chapter 9's "Reproducibility / Validity" subsection.

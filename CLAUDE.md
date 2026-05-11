# DDP — MEIO Digital-Twin Framework

A discrete-event simulation framework for **Multi-Echelon Inventory Optimization** (MEIO) with joint inventory + transport co-optimization.

**Canonical scenario (`config/1n3_5sku.json`):** `1N3` ≡ **1 supplier → N warehouses → 3 retailers**. The default config has **N=2 warehouses** (W1 serves R1+R2; W2 serves R3) — i.e. a **1-2-3 topology**, *not* 1-1-3. Network: `Supplier → {W1, W2}; W1 → {R1, R2}; W2 → R3`. 5 SKUs, **365-day horizon** using the last 365 days of the M5 Walmart series (`start_index=1548`, `strategy=clip`). Every experiment run prints a topology sanity line so a misreading is caught immediately.

---

## Repo map

| Path | Purpose |
|------|---------|
| `engine/` | Core simulation: simulator loop, nodes, transport, network graph, config validator |
| `policies/` | Inventory control policies (7 implementations) |
| `optimizer/` | TPE joint optimizer (`optimize.py`); NSGA-II Pareto frontier (`pareto.py`); per-policy search (`policy_search.py`); bullwhip-aware objective (`bullwhip_aware.py`) |
| `scripts/` | CLI entry points: single run, experiment suite, plots, multi-seed validation |
| `config/` | JSON scenario files (network, SKUs, policies, edges, optional disruptions) |
| `tests/` | pytest suite (~80 tests) covering invariants, policy behaviour, transport |
| `inputs/` | CSV-based config pipeline + per-retailer demand CSVs (M5 Walmart) |
| `dataset/` | Reference datasets |
| `outputs/` | Auto-generated run artefacts (`outputs/<run_type>_<timestamp>/`) |
| `research papers/` | Literature reference PDFs |

Generated/ignored: `outputs/`, `__pycache__/`, `venv/`, `dump/`.

---

## Core abstractions

- **`Simulator`** — `engine/simulator.py`. Daily-tick driver. Fields: `network`, `demand_by_node`, `T`, `volume_per_unit`, `weight_per_unit`, `disruptions`, `metrics`, `pending_dispatch`. Entry point: `Simulator.run(...)`.
- **`Node`** — `engine/node.py`. Per-SKU state: `on_hand`, `pipeline_in`, `backlog_external`, `backlog_children`, `inbound_orders_queue`, `placed_orders`. Helpers: `Shipment`, `IncomingOrder`.
- **Transport** — `engine/transport.py`. `TransportOption` (lane spec), `VehicleLoad`, `GreedyLoadPlanner` (default planner — respects volume **and** weight capacity), pluggable `LoadPlanner` / `ModeSelector` / `CostAllocator` protocols.
- **`Network`** — `engine/network.py`. Graph of nodes + `Edge`s. Supports arbitrary DAG topology.
- **Policies** (`policies/*.py`, all expose `order_qty(on_hand, backlog_external, backlog_children, pipeline_in, t=None)`):
  - `BaseStockPolicy(base_stock_level)`
  - `SsPolicy(s, S)`
  - `RQPolicy(reorder_point, order_quantity)`
  - `OrderUpToPolicy(R, S, phase_offset=0, k=None, m=None)`
  - `KmCyclePolicy(k, m, S, review_offsets)`
  - `PeriodicReviewPolicy(review_period, order_up_to)`
  - `EchelonStockPolicy(echelon_base_stock_level)` — Clark & Scarf; simulator computes echelon inventory position via DFS over downstream nodes.
- **Optimizer** — `optimizer/optimize.py`. `run_optimizer(config_path, mode, n_trials, min_fill_rate, seed, per_sku_constraint=False, ...)`. Modes: `"inventory"`, `"transport"`, `"joint"`. `evaluate(cfg, vpu) -> (cost, fill)`; `evaluate_with_sku_fills(cfg, vpu) -> (cost, fill, {sku: fill})`. `_apply_params(cfg, params)` injects candidate values. With `per_sku_constraint=True` the penalty becomes `Σ_sku max(0, target − fill_sku) × 1e6` so every SKU must hit the target individually.
- **Pareto** — `optimizer/pareto.py`. `run_nsga2_pareto(...)` runs Optuna's `NSGAIISampler` on `(total_cost, -fill_rate)` and returns the non-dominated set. Used by E4.
- **Policy search (E6)** — `optimizer/policy_search.py`. Wraps Optuna with a per-policy parameter registry so non-`base_stock` policies (`ss`, `periodic_review`, `echelon_stock`) can be optimized in their native shape.
- **Bullwhip-aware (E8)** — `optimizer/bullwhip_aware.py`. Joint search with augmented objective `total_cost + λ × mean_bullwhip`.

---

## Standard workflows

```bash
# Single run
python scripts/run_simulation.py --config config/1n3_5sku.json

# Default experiment suite (E0–E4) → outputs/experiments_<ts>/
python scripts/run_experiments.py --config config/1n3_5sku.json

# Full Phase A + Phase B suite (everything)
python scripts/run_experiments.py --config config/1n3_5sku.json \
    --experiments E0 E1a E1b E2 E3 E3_per_sku E4 E5 E6 E7 E8 E9 \
    --trials 100 --validate_seeds 10

# Subset
python scripts/run_experiments.py --config config/1n3_5sku.json \
    --experiments E0 E3 --trials 50

# Plots (cost_breakdown, fill_rate, inventory_ts, orders_ts, bullwhip, pareto)
python scripts/plot_results.py --expdir outputs/experiments_<ts>/

# Multi-seed via flag (re-runs E3 best params under N seeds, mean ± std)
python scripts/run_experiments.py --config ... --validate_seeds 10

# Tests
python -m pytest tests/ -q     # 84 tests
```

### Warm-up convention

`--warmup` defaults to **None**: each experiment in `EXPERIMENT_META` ships its own `recommended_warmup` (currently 30 days for the 365-day M5 scenario). Pass `--warmup N` to override globally. Synthetic / disruption configs that *measure* the transient should pass `--warmup 0` explicitly. The runner prints a warning if `warmup=0` and `T >= 200` and the experiment didn't opt in.

### Experiment catalogue

| ID | Purpose |
|----|---------|
| `E0` | Analytical newsvendor baseline (computed at runtime from the realised demand series, not hardcoded). |
| `E1a` | Fixed 25% dispatch threshold on every lane, inventory unchanged from E0. |
| `E1b` | Transport-only Optuna search (inventory locked at E0). |
| `E2` | Inventory-only Optuna search. |
| `E3` | Joint inventory + transport optimisation — main result. |
| `E3_per_sku` | E3 with per-SKU fill constraint (every SKU ≥ target, not just aggregate). |
| `E4` | Pareto: NSGA-II two-objective `(cost, -fill)` *plus* trimmed constraint sweep at 92–99% as a sanity check. |
| `E5` | Disruption robustness — 14-day W1 outage, run with both E0 and E3 params. |
| `E6` | Policy comparison — `base_stock`, `ss`, `periodic_review`, `echelon_stock` each individually optimized. |
| `E7` | Forecast sensitivity — sweep σ_f ∈ {0,5,10,20,30}% applied to base-stock levels via noisy oracle. |
| `E8` | Bullwhip-aware joint optimisation — sweep λ ∈ {0, 1e3, 1e4, 1e5, 1e6}, objective = cost + λ·mean_bullwhip. |
| `E9` | Stochastic demand robustness — E3 params evaluated across 10 independently seeded Poisson realisations (λ = M5 mean per retailer/SKU); confirms parameter transferability without re-optimisation. |

---

## CSV input pipeline (`inputs/`)

An alternative to writing JSON configs by hand. Fill the 6 CSV files, run the builder, and the JSON is generated automatically.

```bash
python inputs/scripts/build_config_from_csv.py
# → writes inputs/config/generated_from_csv.json
# then pass that to any script:
python scripts/run_simulation.py --config inputs/config/generated_from_csv.json
```

### Input files

| File | Columns | Purpose |
|------|---------|---------|
| `inputs/sim_config.csv` | `parameter, value` | Global params: `seed`, `time_horizon`, `tail_days`, `strategy`, `warmup_days` |
| `inputs/products.csv` | `sku, unit_volume, unit_cost` | SKU physical properties |
| `inputs/nodes.csv` | `node_id, node_type, initial_inventory, holding_cost, shortage_cost, order_cost_fixed, order_cost_per_unit, infinite_supply` | One row per node |
| `inputs/policies.csv` | `node_id, policy_type, param_name, param_value` | Long-format — one row per policy parameter; `policy_type` must match a key in `POLICY_REQUIRED_PARAMS` inside the builder |
| `inputs/routes.csv` | `from_node, to_node, route_id, mode, capacity, cost_full, cost_half, cost_quarter, lead_time` | Transport lanes (deterministic lead times) |
| `inputs/demand_config.csv` | `node_id, source_type, source_path, time_col, quantity_col, fill_strategy` | Points each retailer to its demand CSV; `source_type` must be `"csv"`; `fill_strategy`: `wrap` loops the series |

### Demand data

- `inputs/demand_data/R1.csv`, `R2.csv`, `R3.csv` — per-retailer daily demand derived from the **M5 Walmart Forecasting dataset** (columns: `date`, `quantity`).
- `inputs/demand_shock.csv` — synthetic constant-demand series with a single spike at day 20 (used for the EV2 demand-shock validation experiment).

### Policy types recognised by the builder

| `policy_type` | Required `param_name` values |
|---------------|------------------------------|
| `base_stock` | `base_stock_level` |
| `ss` | `s`, `S` |
| `order_up_to` | `level` |
| `periodic_review` | `review_period`, `target_level` |
| `km_cycle` | `K`, `M` |

> Supplier nodes do not require a policy entry. Every other node must have one.

---

## Config schema (top-level keys of `config/*.json`)

- `seed`, `time_horizon`
- `skus` — list of SKU IDs
- `sku_properties` — `{ sku: { item_id, volume_per_unit, weight_per_unit } }`
- `nodes` — `[{ id, type, infinite_supply, policy: { sku: {...} }, holding_cost, shortage_cost, order_cost_*, initial_inventory }]`
- `edges` — `[{ from, to, transport_options: [{ mode, capacity, cost_*, lead_time, weight_capacity, min_dispatch_utilization }], max_dispatch_wait, ... }]`
- `disruptions` — *(optional)* `[{ node_id, start_day, duration }]`

`engine/config_validator.py` validates incoming configs.

---

## Conventions

- **Warm-up exclusion**: each experiment in `EXPERIMENT_META` has its own `recommended_warmup`. Default 30 days for the M5 365-day scenario. CLI `--warmup` overrides globally.
- **Bullwhip ratio** is computed *per echelon* (Lee/Padmanabhan/Whang 1997): `CV²(orders out) / CV²(orders in)` where the warehouse's "orders in" is the daily sum of orders from its children, *not* raw retailer demand. Reported per (node, SKU) in `bullwhip.csv` together with `cv2_in` and `cv2_out`.
- **Default fill-rate target** = 92% (overridable via `--min_fill_rate`). Aggregate by default; pass `--experiments E3_per_sku` (or use `optimizer.run_optimizer(per_sku_constraint=True)`) for per-SKU.
- **Newsvendor levels (E0)** are computed at runtime from the realised demand series via `_compute_newsvendor_levels`; the JSON's hardcoded `base_stock_level` values are *overwritten*. Saved to `E0/params.json`.
- **Outputs** land in `outputs/experiments_<timestamp>/` — never check them in.
- **Policies must accept `t=None`** in `order_qty(...)`; periodic policies handle `None` by acting as if `t==review tick`.
- **Topology print**: every experiment run prints `Topology : 1 supplier, 2 warehouses, 3 retailers [Supplier → W1,W2 → R1,R2,R3]` so misreadings are caught at the start.

---

## Adding a new policy

1. Create `policies/<name>.py` with an `@dataclass` extending `BasePolicy` from `policies/base_stock.py`.
2. Implement `order_qty(self, on_hand, backlog_external, backlog_children, pipeline_in, t=None) -> int`.
3. Register the new `"type"` string in `scripts/run_simulation.py::build_from_config(...)` policy dispatch.
4. Add a unit test under `tests/test_<name>.py`.

If the policy needs network-wide state (like `EchelonStockPolicy` needing downstream inventory), extend `Simulator._echelon_pipeline` or add a similar helper and gate the call with an `isinstance(policy, ...)` branch.

---

## Adding a new experiment

1. Add an entry to `EXPERIMENT_META` in `scripts/run_experiments.py` with `id`, `title`, `purpose`, `methodology`, `hypothesis`, `report_section`.
2. Write `exp_E<n>(base_cfg, args, ...)` returning the same result dict shape as the others.
3. Wire it into `main()`'s experiment dispatch and pass `baseline=r` (the E0 result) for vs-baseline comparisons.
4. `save_experiment(...)` will auto-render `summary.md` and update `REPORT_SUMMARY.md`.

---

## Don't-touch list

- `outputs/`, `dump/`, `synthetic_validation_*/` — generated artefacts.
- `__pycache__/`, `venv/`, `.pytest_cache/`.
- `research papers/` — read-only reference PDFs.

# DDP Experiment Report Summary

*Generated: 2026-05-10 16:18*  
*Config: `config/1n3_5sku_0.5x_transport.json`*  
*Runtime: 0.3 minutes*

---

## 1. Network Configuration

| Parameter | Value |
|-----------|-------|
| Network topology | 1S–2W–3R (1 supplier, 2 warehouse, 3 retailers) |
| SKUs | 5: SKU_A, SKU_B, SKU_C, SKU_D, SKU_E |
| Transport lanes | 5 |
| Simulation horizon | 365 days |
| Warm-up excluded | per-experiment days |
| Optimizer trials | 100 per experiment |
| Min fill rate target | 92% |

### Node Summary

| Node | Type | Policy (SKU_A) |
|------|------|----------------|
| Supplier | supplier | base_stock |
| W1 | warehouse | base_stock |
| W2 | warehouse | base_stock |
| R1 | retailer | base_stock |
| R2 | retailer | base_stock |
| R3 | retailer | base_stock |

### Transport Lanes

| From | To | Lead Time | Capacity | Min Dispatch |
|------|----|----------:|---------:|-------------:|
| Supplier | W1 | 5 days (deterministic) | 20.0 | 0% |
| Supplier | W2 | 6 days (deterministic) | 15.0 | 0% |
| W1 | R1 | 2 days (deterministic) | 11.0 | 0% |
| W1 | R2 | 3 days (deterministic) | 8.0 | 0% |
| W2 | R3 | 4 days (deterministic) | 15.0 | 0% |

---

## 2. Experiment Results

### E0 — Analytical Baseline

**Purpose:** Establish a reference point using analytically derived base-stock levels (newsvendor formula) with no transport consolidation constraint. This represents the standard textbook multi-echelon policy without any joint optimization.

| KPI | Value |
|-----|------:|
| Total cost | 251,127 |
| Fill rate | 91.59% |
| Transport share | 66.0% |
| Holding share | 8.3% |
| Shortage share | 10.2% |

**Key findings:**

- Baseline total cost is **251,127**, dominated by transport (66.0%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **91.59%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 8.3% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (86.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 86.1% (SKU_B) to 96.7% (SKU_E) — a 10.6 pp range.

### E3 — Joint Inventory + Transport Optimization (Main Result)

**Purpose:** Simultaneously optimize both base-stock levels and dispatch thresholds. This is the core research contribution: demonstrating that joint optimization achieves cost savings that neither inventory-only nor transport-only optimization can achieve independently.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 192,696 | +23.3% |
| Fill rate | 96.29% | +4.71 pp |
| Transport share | 37.0% | -29.0 pp |
| Holding share | 35.6% | +27.3 pp |
| Shortage share | 7.3% | -2.9 pp |

**Key findings:**

- **23.3% total cost reduction** vs E0 baseline (from 251,127 to 192,696).
- Fill rate improved by **4.71 percentage points** over baseline.
- Transport cost share decreased by **29.0 pp** (from 66.0% to 37.0%), reflecting effective vehicle consolidation.
- Holding cost share is **27.3 pp higher** (35.6% vs 8.3% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.9 pp** (7.3% vs 10.2% in E0).
- **SKU_B** has the lowest fill rate (84.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 84.2% (SKU_B) to 99.7% (SKU_C) — a 15.5 pp range.

---

## 3. Comparison Table

Exp | Description              | Total Cost | vs E0  | Holding % | Transport % | Ordering % | Shortage % | Fill Rate %
----+--------------------------+------------+--------+-----------+-------------+------------+------------+------------
E0  | E0 — Analytical Baseline | 251,127    | +0.0%  | 8.3       | 66.0        | 15.5       | 10.2       | 91.59      
E3  | E3 — Joint Opt (≥92%)    | 192,696    | +23.3% | 35.6      | 37.0        | 20.2       | 7.3        | 96.29      

---

## 5. Key Findings for Dissertation

---

## 6. Files Reference

| File | Contents |
|------|----------|
| `summary_table.csv` | One-row-per-experiment KPI comparison |
| `E*/summary.md` | Rich per-experiment report with purpose, methodology, results |
| `E*/summary.txt` | Quick plain-text reference |
| `E*/costs_by_node_sku.csv` | Cost breakdown at node × SKU granularity |
| `E*/kpis_by_sku.csv` | Fill rate per SKU |
| `E*/kpis_by_node_sku.csv` | Fill rate per retailer × SKU |
| `E*/bullwhip.csv` | Bullwhip effect ratio per node × SKU |
| `E*/inventory_log.csv` | Daily on-hand, pipeline, backlog time series |
| `E*/orders_log.csv` | Daily order quantities (shows bullwhip visually) |
| `E*/params.json` | Exact policy parameters used |
| `E4_pareto/pareto_frontier.csv` | Cost vs fill rate Pareto data |
| `plots/` | All matplotlib figures (run `plot_results.py`) |

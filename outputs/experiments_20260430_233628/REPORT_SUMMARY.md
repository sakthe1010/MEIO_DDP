# DDP Experiment Report Summary

*Generated: 2026-04-30 23:36*  
*Config: `config/1n3_5sku.json`*  
*Runtime: 0.4 minutes*

---

## 1. Network Configuration

| Parameter | Value |
|-----------|-------|
| Network topology | 1S–2W–3R (1 supplier, 2 warehouse, 3 retailers) |
| SKUs | 5: SKU_A, SKU_B, SKU_C, SKU_D, SKU_E |
| Transport lanes | 5 |
| Simulation horizon | 365 days |
| Warm-up excluded | per-experiment days |
| Optimizer trials | 40 per experiment |
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
| Total cost | 416,952 |
| Fill rate | 91.59% |
| Transport share | 79.5% |
| Holding share | 5.0% |
| Shortage share | 6.1% |

**Key findings:**

- Baseline total cost is **416,952**, dominated by transport (79.5%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **91.59%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 5.0% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (86.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 86.1% (SKU_B) to 96.7% (SKU_E) — a 10.6 pp range.

### E1a — Fixed Financial Dispatch Threshold (25%)

**Purpose:** Assess the cost impact of imposing a minimum vehicle utilization threshold of 25% on all transport lanes, using the same inventory policy as E0. This isolates the effect of transport consolidation alone, without re-optimizing inventory to compensate.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 282,935 | +32.1% |
| Fill rate | 75.09% | -16.50 pp |
| Transport share | 55.4% | -24.1 pp |
| Holding share | 4.8% | -0.2 pp |
| Shortage share | 26.1% | +19.9 pp |

**Key findings:**

- **32.1% total cost reduction** vs E0 baseline (from 416,952 to 282,935).
- Fill rate **dropped 16.50 pp** vs baseline (75.09%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **24.1 pp** (from 79.5% to 55.4%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 19.9 pp** (26.1% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (73.0%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 73.0% (SKU_B) to 77.7% (SKU_D) — a 4.7 pp range.

### E1b — Transport-Only Optimization

**Purpose:** Optimize dispatch thresholds per lane using Optuna (TPE sampler) while keeping inventory base-stock levels fixed at their analytical values. This answers: how much can transport cost be reduced through smart threshold selection alone?

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 298,901 | +28.3% |
| Fill rate | 79.10% | -12.49 pp |
| Transport share | 59.6% | -20.0 pp |
| Holding share | 5.1% | +0.0 pp |
| Shortage share | 22.4% | +16.3 pp |

**Key findings:**

- **28.3% total cost reduction** vs E0 baseline (from 416,952 to 298,901).
- Fill rate **dropped 12.49 pp** vs baseline (79.10%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **20.0 pp** (from 79.5% to 59.6%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 16.3 pp** (22.4% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (75.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 75.7% (SKU_B) to 82.3% (SKU_D) — a 6.6 pp range.

### E2 — Inventory-Only Optimization

**Purpose:** Optimize base-stock levels per node and SKU while keeping dispatch thresholds at zero (immediate dispatch). This answers: how much cost can be saved by right-sizing inventory alone, without touching transport policy?

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 488,965 | -17.3% |
| Fill rate | 93.51% | +1.92 pp |
| Transport share | 67.8% | -11.7 pp |
| Holding share | 20.4% | +15.4 pp |
| Shortage share | 3.8% | -2.3 pp |

**Key findings:**

- Total cost is **17.3% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **1.92 percentage points** over baseline.
- Transport cost share decreased by **11.7 pp** (from 79.5% to 67.8%), reflecting effective vehicle consolidation.
- Holding cost share is **15.4 pp higher** (20.4% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.3 pp** (3.8% vs 6.1% in E0).
- **SKU_E** has the lowest fill rate (83.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.1% (SKU_E) to 100.0% (SKU_D) — a 16.9 pp range.

### E3 — Joint Inventory + Transport Optimization (Main Result)

**Purpose:** Simultaneously optimize both base-stock levels and dispatch thresholds. This is the core research contribution: demonstrating that joint optimization achieves cost savings that neither inventory-only nor transport-only optimization can achieve independently.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 263,804 | +36.7% |
| Fill rate | 96.29% | +4.71 pp |
| Transport share | 54.0% | -25.6 pp |
| Holding share | 26.0% | +21.0 pp |
| Shortage share | 5.3% | -0.8 pp |

**Key findings:**

- **36.7% total cost reduction** vs E0 baseline (from 416,952 to 263,804).
- Fill rate improved by **4.71 percentage points** over baseline.
- Transport cost share decreased by **25.6 pp** (from 79.5% to 54.0%), reflecting effective vehicle consolidation.
- Holding cost share is **21.0 pp higher** (26.0% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- **SKU_B** has the lowest fill rate (84.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 84.2% (SKU_B) to 99.7% (SKU_C) — a 15.5 pp range.

### E3_per_sku — Joint Optimization with per-SKU fill constraint

**Purpose:** Re-run E3 but apply the fill rate constraint per-SKU rather than aggregated. Every SKU must individually meet the target. This eliminates the loophole where popular SKUs over-serve and compensate for under-served ones.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 277,693 | +33.4% |
| Fill rate | 98.83% | +7.24 pp |
| Transport share | 50.8% | -28.7 pp |
| Holding share | 34.0% | +29.0 pp |
| Shortage share | 1.2% | -4.9 pp |

**Key findings:**

- **33.4% total cost reduction** vs E0 baseline (from 416,952 to 277,693).
- Fill rate improved by **7.24 percentage points** over baseline.
- Transport cost share decreased by **28.7 pp** (from 79.5% to 50.8%), reflecting effective vehicle consolidation.
- Holding cost share is **29.0 pp higher** (34.0% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.9 pp** (1.2% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.3% (SKU_C) to 100.0% (SKU_E) — a 3.7 pp range.

---

## 3. Comparison Table

Exp        | Description                            | Total Cost | vs E0  | Holding % | Transport % | Ordering % | Shortage % | Fill Rate %
-----------+----------------------------------------+------------+--------+-----------+-------------+------------+------------+------------
E0         | E0 — Analytical Baseline               | 416,952    | +0.0%  | 5.0       | 79.5        | 9.3        | 6.1        | 91.59      
E1a        | E1a — Financial Dispatch (25%)         | 282,935    | +32.1% | 4.8       | 55.4        | 13.7       | 26.1       | 75.09      
E1b        | E1b — Transport-Only Optimization      | 298,901    | +28.3% | 5.1       | 59.6        | 13.0       | 22.4       | 79.10      
E2         | E2 — Inventory-Only Opt (≥92%)         | 488,965    | -17.3% | 20.4      | 67.8        | 7.9        | 3.8        | 93.51      
E3         | E3 — Joint Opt (≥92%)                  | 263,804    | +36.7% | 26.0      | 54.0        | 14.7       | 5.3        | 96.29      
E3_per_sku | E3_per_sku — Joint Opt (per-SKU ≥ 92%) | 277,693    | +33.4% | 34.0      | 50.8        | 14.0       | 1.2        | 98.83      

---

## 5. Key Findings for Dissertation

1. **Joint optimization (E3) achieves a 36.7% total cost reduction** over the analytical baseline while meeting the 92% fill rate target (achieved: 96.29%). This is the primary result of the dissertation.

2. **Inventory-only optimization (E2) increases cost by 17.3%**, confirming that optimizing inventory alone is insufficient compared to joint optimization.

3. **Transport-only optimization (E1b) achieves 28.3% cost reduction**, showing that threshold selection matters but is limited without inventory co-optimization.

4. **Transport cost dominates** the baseline cost structure (79.5% of total), making it the primary lever for cost reduction. Joint optimization reduces this share through vehicle consolidation.

5. **The bullwhip effect** is observable in the orders time series — order variability increases upstream from retailers to warehouses to the supplier. Joint optimization reduces bullwhip by smoothing replenishment patterns.

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

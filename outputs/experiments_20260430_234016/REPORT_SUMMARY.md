# DDP Experiment Report Summary

*Generated: 2026-04-30 23:42*  
*Config: `config/1n3_5sku.json`*  
*Runtime: 2.1 minutes*

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
| Total cost | 371,847 | +10.8% |
| Fill rate | 88.68% | -2.91 pp |
| Transport share | 75.4% | -4.1 pp |
| Holding share | 5.2% | +0.2 pp |
| Shortage share | 9.0% | +2.8 pp |

**Key findings:**

- **10.8% total cost reduction** vs E0 baseline (from 416,952 to 371,847).
- Fill rate **dropped 2.91 pp** vs baseline (88.68%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **4.1 pp** (from 79.5% to 75.4%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 2.8 pp** (9.0% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (83.5%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.5% (SKU_B) to 93.2% (SKU_E) — a 9.6 pp range.

### E2 — Inventory-Only Optimization

**Purpose:** Optimize base-stock levels per node and SKU while keeping dispatch thresholds at zero (immediate dispatch). This answers: how much cost can be saved by right-sizing inventory alone, without touching transport policy?

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 458,890 | -10.1% |
| Fill rate | 99.23% | +7.64 pp |
| Transport share | 72.3% | -7.3 pp |
| Holding share | 18.8% | +13.7 pp |
| Shortage share | 0.5% | -5.6 pp |

**Key findings:**

- Total cost is **10.1% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **7.64 percentage points** over baseline.
- Transport cost share decreased by **7.3 pp** (from 79.5% to 72.3%), reflecting effective vehicle consolidation.
- Holding cost share is **13.7 pp higher** (18.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 5.6 pp** (0.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 98.1% (SKU_C) to 100.0% (SKU_E) — a 1.9 pp range.

### E3 — Joint Inventory + Transport Optimization (Main Result)

**Purpose:** Simultaneously optimize both base-stock levels and dispatch thresholds. This is the core research contribution: demonstrating that joint optimization achieves cost savings that neither inventory-only nor transport-only optimization can achieve independently.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 261,088 | +37.4% |
| Fill rate | 98.72% | +7.13 pp |
| Transport share | 52.7% | -26.9 pp |
| Holding share | 31.1% | +26.1 pp |
| Shortage share | 1.3% | -4.8 pp |

**Key findings:**

- **37.4% total cost reduction** vs E0 baseline (from 416,952 to 261,088).
- Fill rate improved by **7.13 percentage points** over baseline.
- Transport cost share decreased by **26.9 pp** (from 79.5% to 52.7%), reflecting effective vehicle consolidation.
- Holding cost share is **26.1 pp higher** (31.1% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.8 pp** (1.3% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.7% (SKU_D) to 99.9% (SKU_B) — a 3.3 pp range.

### E3_per_sku — Joint Optimization with per-SKU fill constraint

**Purpose:** Re-run E3 but apply the fill rate constraint per-SKU rather than aggregated. Every SKU must individually meet the target. This eliminates the loophole where popular SKUs over-serve and compensate for under-served ones.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 258,085 | +38.1% |
| Fill rate | 97.41% | +5.82 pp |
| Transport share | 54.0% | -25.6 pp |
| Holding share | 28.5% | +23.5 pp |
| Shortage share | 2.5% | -3.6 pp |

**Key findings:**

- **38.1% total cost reduction** vs E0 baseline (from 416,952 to 258,085).
- Fill rate improved by **5.82 percentage points** over baseline.
- Transport cost share decreased by **25.6 pp** (from 79.5% to 54.0%), reflecting effective vehicle consolidation.
- Holding cost share is **23.5 pp higher** (28.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 3.6 pp** (2.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 92.1% (SKU_E) to 99.5% (SKU_A) — a 7.5 pp range.

---

## 3. Comparison Table

Exp        | Description                            | Total Cost | vs E0  | Holding % | Transport % | Ordering % | Shortage % | Fill Rate %
-----------+----------------------------------------+------------+--------+-----------+-------------+------------+------------+------------
E0         | E0 — Analytical Baseline               | 416,952    | +0.0%  | 5.0       | 79.5        | 9.3        | 6.1        | 91.59      
E1a        | E1a — Financial Dispatch (25%)         | 282,935    | +32.1% | 4.8       | 55.4        | 13.7       | 26.1       | 75.09      
E1b        | E1b — Transport-Only Optimization      | 371,847    | +10.8% | 5.2       | 75.4        | 10.4       | 9.0        | 88.68      
E2         | E2 — Inventory-Only Opt (≥92%)         | 458,890    | -10.1% | 18.8      | 72.3        | 8.5        | 0.5        | 99.23      
E3         | E3 — Joint Opt (≥92%)                  | 261,088    | +37.4% | 31.1      | 52.7        | 14.9       | 1.3        | 98.72      
E3_per_sku | E3_per_sku — Joint Opt (per-SKU ≥ 92%) | 258,085    | +38.1% | 28.5      | 54.0        | 15.0       | 2.5        | 97.41      

---

## 4. Pareto Frontier (E4)

The table below shows the trade-off between fill rate and total cost under joint optimization. Each row is an independent optimizer run with a different fill rate target.

target_fill_pct | achieved_fill_pct | total_cost | feasible_trials | best_trial
----------------+-------------------+------------+-----------------+-----------
92.0            | 96.38             | 288221.3   | 18.0            | 27.0      
93.0            | 97.2              | 315342.09  | 10.0            | 46.0      
94.0            | 96.51             | 315889.82  | 11.0            | 12.0      
95.0            | 96.12             | 342736.55  | 11.0            | 28.0      
96.0            | 98.69             | 303618.39  | 10.0            | 40.0      
97.0            | 96.23             | 349844.05  | 0.0             | 39.0      
98.0            | 98.6              | 304663.63  | 4.0             | 41.0      
99.0            | 98.93             | 355286.43  | 0.0             | 46.0      

**Marginal cost of fill rate improvement:**

| At fill rate | Marginal cost per +1pp |
|-------------:|-----------------------:|
| 97.2% | 33,074 |
| 98.7% | -15,221 |
| 98.6% | -19,063 |
| 98.9% | 153,402 |

---

## 5. Key Findings for Dissertation

1. **Joint optimization (E3) achieves a 37.4% total cost reduction** over the analytical baseline while meeting the 92% fill rate target (achieved: 98.72%). This is the primary result of the dissertation.

2. **Inventory-only optimization (E2) increases cost by 10.1%**, confirming that optimizing inventory alone is insufficient compared to joint optimization.

3. **Transport-only optimization (E1b) achieves 10.8% cost reduction**, showing that threshold selection matters but is limited without inventory co-optimization.

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

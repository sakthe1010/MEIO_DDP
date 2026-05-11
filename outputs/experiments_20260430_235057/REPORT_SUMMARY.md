# DDP Experiment Report Summary

*Generated: 2026-04-30 23:54*  
*Config: `config/1n3_5sku.json`*  
*Runtime: 3.9 minutes*

---

## 1. Network Configuration

| Parameter | Value |
|-----------|-------|
| Network topology | 1S–2W–3R (1 supplier, 2 warehouse, 3 retailers) |
| SKUs | 5: SKU_A, SKU_B, SKU_C, SKU_D, SKU_E |
| Transport lanes | 5 |
| Simulation horizon | 365 days |
| Warm-up excluded | per-experiment days |
| Optimizer trials | 80 per experiment |
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
| Total cost | 370,370 | +11.2% |
| Fill rate | 87.44% | -4.14 pp |
| Transport share | 74.3% | -5.3 pp |
| Holding share | 5.2% | +0.2 pp |
| Shortage share | 10.0% | +3.9 pp |

**Key findings:**

- **11.2% total cost reduction** vs E0 baseline (from 416,952 to 370,370).
- Fill rate **dropped 4.14 pp** vs baseline (87.44%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **5.3 pp** (from 79.5% to 74.3%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 3.9 pp** (10.0% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (82.8%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 82.8% (SKU_B) to 91.3% (SKU_D) — a 8.5 pp range.

### E2 — Inventory-Only Optimization

**Purpose:** Optimize base-stock levels per node and SKU while keeping dispatch thresholds at zero (immediate dispatch). This answers: how much cost can be saved by right-sizing inventory alone, without touching transport policy?

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 470,742 | -12.9% |
| Fill rate | 94.62% | +3.03 pp |
| Transport share | 70.5% | -9.1 pp |
| Holding share | 18.0% | +13.0 pp |
| Shortage share | 3.3% | -2.9 pp |

**Key findings:**

- Total cost is **12.9% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **3.03 percentage points** over baseline.
- Transport cost share decreased by **9.1 pp** (from 79.5% to 70.5%), reflecting effective vehicle consolidation.
- Holding cost share is **13.0 pp higher** (18.0% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.9 pp** (3.3% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (81.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 81.7% (SKU_B) to 99.9% (SKU_A) — a 18.2 pp range.

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
| Total cost | 267,706 | +35.8% |
| Fill rate | 99.40% | +7.82 pp |
| Transport share | 52.2% | -27.4 pp |
| Holding share | 32.8% | +27.8 pp |
| Shortage share | 0.5% | -5.6 pp |

**Key findings:**

- **35.8% total cost reduction** vs E0 baseline (from 416,952 to 267,706).
- Fill rate improved by **7.82 percentage points** over baseline.
- Transport cost share decreased by **27.4 pp** (from 79.5% to 52.2%), reflecting effective vehicle consolidation.
- Holding cost share is **27.8 pp higher** (32.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 5.6 pp** (0.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 98.6% (SKU_C) to 100.0% (SKU_A) — a 1.4 pp range.

### E5 — Disruption Robustness

**Purpose:** Inject a supply-side disruption at warehouse W1 and compare how E0 (analytical) and E3 (joint-optimized) parameters cope. Measures cost overhead, service degradation, and recovery time — the stress test the analytical baseline can't anticipate.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 2,577,516 | -518.2% |
| Fill rate | 73.83% | -17.76 pp |
| Transport share | 11.5% | -68.0 pp |
| Holding share | 6.9% | +1.9 pp |
| Shortage share | 80.3% | +74.2 pp |

**Key findings:**

- Total cost is **518.2% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate **dropped 17.76 pp** vs baseline (73.83%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **68.0 pp** (from 79.5% to 11.5%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 74.2 pp** (80.3% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (66.6%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 66.6% (SKU_B) to 79.3% (SKU_E) — a 12.8 pp range.

### E5 — Disruption Robustness

**Purpose:** Inject a supply-side disruption at warehouse W1 and compare how E0 (analytical) and E3 (joint-optimized) parameters cope. Measures cost overhead, service degradation, and recovery time — the stress test the analytical baseline can't anticipate.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 2,222,086 | -432.9% |
| Fill rate | 81.86% | -9.73 pp |
| Transport share | 6.4% | -73.1 pp |
| Holding share | 10.3% | +5.3 pp |
| Shortage share | 81.8% | +75.6 pp |

**Key findings:**

- Total cost is **432.9% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate **dropped 9.73 pp** vs baseline (81.86%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **73.1 pp** (from 79.5% to 6.4%), reflecting effective vehicle consolidation.
- Holding cost share is **5.3 pp higher** (10.3% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **increased by 75.6 pp** (81.8% vs 6.1% in E0).
- **SKU_D** has the lowest fill rate (79.4%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 79.4% (SKU_D) to 84.2% (SKU_C) — a 4.8 pp range.

### E6 — Policy Comparison (Core 4)

**Purpose:** Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 458,021 | -9.8% |
| Fill rate | 96.29% | +4.71 pp |
| Transport share | 72.4% | -7.1 pp |
| Holding share | 16.8% | +11.8 pp |
| Shortage share | 2.3% | -3.8 pp |

**Key findings:**

- Total cost is **9.8% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **4.71 percentage points** over baseline.
- Transport cost share decreased by **7.1 pp** (from 79.5% to 72.4%), reflecting effective vehicle consolidation.
- Holding cost share is **11.8 pp higher** (16.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 3.8 pp** (2.3% vs 6.1% in E0).
- **SKU_C** has the lowest fill rate (90.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 90.1% (SKU_C) to 100.0% (SKU_B) — a 9.9 pp range.

### E6 — Policy Comparison (Core 4)

**Purpose:** Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 369,257 | +11.4% |
| Fill rate | 92.03% | +0.44 pp |
| Transport share | 59.3% | -20.3 pp |
| Holding share | 32.1% | +27.1 pp |
| Shortage share | 5.8% | -0.3 pp |

**Key findings:**

- **11.4% total cost reduction** vs E0 baseline (from 416,952 to 369,257).
- Fill rate improved by **0.44 percentage points** over baseline.
- Transport cost share decreased by **20.3 pp** (from 79.5% to 59.3%), reflecting effective vehicle consolidation.
- Holding cost share is **27.1 pp higher** (32.1% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- **SKU_B** has the lowest fill rate (83.9%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.9% (SKU_B) to 99.5% (SKU_D) — a 15.6 pp range.

### E6 — Policy Comparison (Core 4)

**Purpose:** Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 407,719 | +2.2% |
| Fill rate | 88.48% | -3.11 pp |
| Transport share | 53.5% | -26.0 pp |
| Holding share | 24.5% | +19.5 pp |
| Shortage share | 19.4% | +13.3 pp |

**Key findings:**

- **2.2% total cost reduction** vs E0 baseline (from 416,952 to 407,719).
- Fill rate **dropped 3.11 pp** vs baseline (88.48%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **26.0 pp** (from 79.5% to 53.5%), reflecting effective vehicle consolidation.
- Holding cost share is **19.5 pp higher** (24.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **increased by 13.3 pp** (19.4% vs 6.1% in E0).
- **SKU_C** has the lowest fill rate (66.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 66.2% (SKU_C) to 99.6% (SKU_A) — a 33.4 pp range.

### E6 — Policy Comparison (Core 4)

**Purpose:** Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 495,132 | -18.8% |
| Fill rate | 98.97% | +7.39 pp |
| Transport share | 67.1% | -12.5 pp |
| Holding share | 25.9% | +20.9 pp |
| Shortage share | 0.6% | -5.6 pp |

**Key findings:**

- Total cost is **18.8% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **7.39 percentage points** over baseline.
- Transport cost share decreased by **12.5 pp** (from 79.5% to 67.1%), reflecting effective vehicle consolidation.
- Holding cost share is **20.9 pp higher** (25.9% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 5.6 pp** (0.6% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.1% (SKU_B) to 100.0% (SKU_D) — a 3.9 pp range.

### E7 — Demand Forecasting Sensitivity

**Purpose:** Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 261,917 | +37.2% |
| Fill rate | 98.65% | +7.06 pp |
| Transport share | 52.7% | -26.9 pp |
| Holding share | 31.1% | +26.1 pp |
| Shortage share | 1.4% | -4.7 pp |

**Key findings:**

- **37.2% total cost reduction** vs E0 baseline (from 416,952 to 261,917).
- Fill rate improved by **7.06 percentage points** over baseline.
- Transport cost share decreased by **26.9 pp** (from 79.5% to 52.7%), reflecting effective vehicle consolidation.
- Holding cost share is **26.1 pp higher** (31.1% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.7 pp** (1.4% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.6% (SKU_D) to 99.9% (SKU_B) — a 3.4 pp range.

### E7 — Demand Forecasting Sensitivity

**Purpose:** Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 265,638 | +36.3% |
| Fill rate | 98.08% | +6.49 pp |
| Transport share | 51.9% | -27.6 pp |
| Holding share | 31.2% | +26.2 pp |
| Shortage share | 2.2% | -3.9 pp |

**Key findings:**

- **36.3% total cost reduction** vs E0 baseline (from 416,952 to 265,638).
- Fill rate improved by **6.49 percentage points** over baseline.
- Transport cost share decreased by **27.6 pp** (from 79.5% to 51.9%), reflecting effective vehicle consolidation.
- Holding cost share is **26.2 pp higher** (31.2% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 3.9 pp** (2.2% vs 6.1% in E0).
- Fill rate spread across SKUs: 93.9% (SKU_D) to 99.9% (SKU_B) — a 6.0 pp range.

### E7 — Demand Forecasting Sensitivity

**Purpose:** Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 272,812 | +34.6% |
| Fill rate | 96.71% | +5.12 pp |
| Transport share | 50.8% | -28.7 pp |
| Holding share | 30.8% | +25.8 pp |
| Shortage share | 4.1% | -2.0 pp |

**Key findings:**

- **34.6% total cost reduction** vs E0 baseline (from 416,952 to 272,812).
- Fill rate improved by **5.12 percentage points** over baseline.
- Transport cost share decreased by **28.7 pp** (from 79.5% to 50.8%), reflecting effective vehicle consolidation.
- Holding cost share is **25.8 pp higher** (30.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- **SKU_D** has the lowest fill rate (90.0%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 90.0% (SKU_D) to 99.9% (SKU_B) — a 9.9 pp range.

### E7 — Demand Forecasting Sensitivity

**Purpose:** Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 295,571 | +29.1% |
| Fill rate | 93.19% | +1.60 pp |
| Transport share | 47.0% | -32.6 pp |
| Holding share | 29.5% | +24.5 pp |
| Shortage share | 10.4% | +4.2 pp |

**Key findings:**

- **29.1% total cost reduction** vs E0 baseline (from 416,952 to 295,571).
- Fill rate improved by **1.60 percentage points** over baseline.
- Transport cost share decreased by **32.6 pp** (from 79.5% to 47.0%), reflecting effective vehicle consolidation.
- Holding cost share is **24.5 pp higher** (29.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **increased by 4.2 pp** (10.4% vs 6.1% in E0).
- **SKU_D** has the lowest fill rate (80.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 80.2% (SKU_D) to 99.5% (SKU_B) — a 19.4 pp range.

### E7 — Demand Forecasting Sensitivity

**Purpose:** Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 337,255 | +19.1% |
| Fill rate | 86.54% | -5.05 pp |
| Transport share | 41.2% | -38.3 pp |
| Holding share | 26.7% | +21.7 pp |
| Shortage share | 20.6% | +14.5 pp |

**Key findings:**

- **19.1% total cost reduction** vs E0 baseline (from 416,952 to 337,255).
- Fill rate **dropped 5.05 pp** vs baseline (86.54%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **38.3 pp** (from 79.5% to 41.2%), reflecting effective vehicle consolidation.
- Holding cost share is **21.7 pp higher** (26.7% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **increased by 14.5 pp** (20.6% vs 6.1% in E0).
- **SKU_D** has the lowest fill rate (65.8%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 65.8% (SKU_D) to 98.6% (SKU_B) — a 32.8 pp range.

### E8 — Bullwhip-Aware Joint Optimization

**Purpose:** Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 290,180 | +30.4% |
| Fill rate | 95.51% | +3.93 pp |
| Transport share | 48.9% | -30.7 pp |
| Holding share | 32.5% | +27.5 pp |
| Shortage share | 5.2% | -0.9 pp |

**Key findings:**

- **30.4% total cost reduction** vs E0 baseline (from 416,952 to 290,180).
- Fill rate improved by **3.93 percentage points** over baseline.
- Transport cost share decreased by **30.7 pp** (from 79.5% to 48.9%), reflecting effective vehicle consolidation.
- Holding cost share is **27.5 pp higher** (32.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Fill rate spread across SKUs: 93.0% (SKU_A) to 99.9% (SKU_B) — a 6.9 pp range.

### E8 — Bullwhip-Aware Joint Optimization

**Purpose:** Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 290,180 | +30.4% |
| Fill rate | 95.51% | +3.93 pp |
| Transport share | 48.9% | -30.7 pp |
| Holding share | 32.5% | +27.5 pp |
| Shortage share | 5.2% | -0.9 pp |

**Key findings:**

- **30.4% total cost reduction** vs E0 baseline (from 416,952 to 290,180).
- Fill rate improved by **3.93 percentage points** over baseline.
- Transport cost share decreased by **30.7 pp** (from 79.5% to 48.9%), reflecting effective vehicle consolidation.
- Holding cost share is **27.5 pp higher** (32.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Fill rate spread across SKUs: 93.0% (SKU_A) to 99.9% (SKU_B) — a 6.9 pp range.

### E8 — Bullwhip-Aware Joint Optimization

**Purpose:** Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 282,938 | +32.1% |
| Fill rate | 93.10% | +1.51 pp |
| Transport share | 49.4% | -30.1 pp |
| Holding share | 28.9% | +23.9 pp |
| Shortage share | 7.9% | +1.8 pp |

**Key findings:**

- **32.1% total cost reduction** vs E0 baseline (from 416,952 to 282,938).
- Fill rate improved by **1.51 percentage points** over baseline.
- Transport cost share decreased by **30.1 pp** (from 79.5% to 49.4%), reflecting effective vehicle consolidation.
- Holding cost share is **23.9 pp higher** (28.9% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- **SKU_E** has the lowest fill rate (74.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 74.7% (SKU_E) to 99.6% (SKU_D) — a 24.9 pp range.

### E8 — Bullwhip-Aware Joint Optimization

**Purpose:** Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 287,111 | +31.1% |
| Fill rate | 97.13% | +5.54 pp |
| Transport share | 49.7% | -29.8 pp |
| Holding share | 32.3% | +27.2 pp |
| Shortage share | 4.5% | -1.7 pp |

**Key findings:**

- **31.1% total cost reduction** vs E0 baseline (from 416,952 to 287,111).
- Fill rate improved by **5.54 percentage points** over baseline.
- Transport cost share decreased by **29.8 pp** (from 79.5% to 49.7%), reflecting effective vehicle consolidation.
- Holding cost share is **27.2 pp higher** (32.3% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Fill rate spread across SKUs: 93.3% (SKU_C) to 100.0% (SKU_A) — a 6.7 pp range.

### E8 — Bullwhip-Aware Joint Optimization

**Purpose:** Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

| KPI | Value | vs E0 |
|-----|------:|------:|
| Total cost | 271,535 | +34.9% |
| Fill rate | 96.75% | +5.16 pp |
| Transport share | 51.7% | -27.8 pp |
| Holding share | 30.7% | +25.7 pp |
| Shortage share | 3.3% | -2.9 pp |

**Key findings:**

- **34.9% total cost reduction** vs E0 baseline (from 416,952 to 271,535).
- Fill rate improved by **5.16 percentage points** over baseline.
- Transport cost share decreased by **27.8 pp** (from 79.5% to 51.7%), reflecting effective vehicle consolidation.
- Holding cost share is **25.7 pp higher** (30.7% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.9 pp** (3.3% vs 6.1% in E0).
- Fill rate spread across SKUs: 92.4% (SKU_C) to 99.7% (SKU_B) — a 7.3 pp range.

---

## 3. Comparison Table

Exp        | Description                            | Total Cost | vs E0   | Holding % | Transport % | Ordering % | Shortage % | Fill Rate %
-----------+----------------------------------------+------------+---------+-----------+-------------+------------+------------+------------
E0         | E0 — Analytical Baseline               | 416,952    | +0.0%   | 5.0       | 79.5        | 9.3        | 6.1        | 91.59      
E1a        | E1a — Financial Dispatch (25%)         | 282,935    | +32.1%  | 4.8       | 55.4        | 13.7       | 26.1       | 75.09      
E1b        | E1b — Transport-Only Optimization      | 370,370    | +11.2%  | 5.2       | 74.3        | 10.5       | 10.0       | 87.44      
E2         | E2 — Inventory-Only Opt (≥92%)         | 470,742    | -12.9%  | 18.0      | 70.5        | 8.2        | 3.3        | 94.62      
E3         | E3 — Joint Opt (≥92%)                  | 261,088    | +37.4%  | 31.1      | 52.7        | 14.9       | 1.3        | 98.72      
E3_per_sku | E3_per_sku — Joint Opt (per-SKU ≥ 92%) | 267,706    | +35.8%  | 32.8      | 52.2        | 14.5       | 0.5        | 99.40      
E5         | E5 — E0 under W1 outage                | 2,577,516  | -518.2% | 6.9       | 11.5        | 1.3        | 80.3       | 73.83      
E5         | E5 — E3 under W1 outage                | 2,222,086  | -432.9% | 10.3      | 6.4         | 1.5        | 81.8       | 81.86      
E6         | E6 — base_stock                        | 458,021    | -9.8%   | 16.8      | 72.4        | 8.5        | 2.3        | 96.29      
E6         | E6 — ss                                | 369,257    | +11.4%  | 32.1      | 59.3        | 2.8        | 5.8        | 92.03      
E6         | E6 — periodic_review                   | 407,719    | +2.2%   | 24.5      | 53.5        | 2.5        | 19.4       | 88.48      
E6         | E6 — echelon_stock                     | 495,132    | -18.8%  | 25.9      | 67.1        | 6.5        | 0.6        | 98.97      
E7         | E7 — σ_f = 0%                          | 261,917    | +37.2%  | 31.1      | 52.7        | 14.8       | 1.4        | 98.65      
E7         | E7 — σ_f = 5%                          | 265,638    | +36.3%  | 31.2      | 51.9        | 14.6       | 2.2        | 98.08      
E7         | E7 — σ_f = 10%                         | 272,812    | +34.6%  | 30.8      | 50.8        | 14.2       | 4.1        | 96.71      
E7         | E7 — σ_f = 20%                         | 295,571    | +29.1%  | 29.5      | 47.0        | 13.1       | 10.4       | 93.19      
E7         | E7 — σ_f = 30%                         | 337,255    | +19.1%  | 26.7      | 41.2        | 11.5       | 20.6       | 86.54      
E8         | E8 — λ=0e+00                           | 290,180    | +30.4%  | 32.5      | 48.9        | 13.4       | 5.2        | 95.51      
E8         | E8 — λ=1e+03                           | 290,180    | +30.4%  | 32.5      | 48.9        | 13.4       | 5.2        | 95.51      
E8         | E8 — λ=1e+04                           | 282,938    | +32.1%  | 28.9      | 49.4        | 13.7       | 7.9        | 93.10      
E8         | E8 — λ=1e+05                           | 287,111    | +31.1%  | 32.3      | 49.7        | 13.5       | 4.5        | 97.13      
E8         | E8 — λ=1e+06                           | 271,535    | +34.9%  | 30.7      | 51.7        | 14.3       | 3.3        | 96.75      

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

2. **Inventory-only optimization (E2) increases cost by 12.9%**, confirming that optimizing inventory alone is insufficient compared to joint optimization.

3. **Transport-only optimization (E1b) achieves 11.2% cost reduction**, showing that threshold selection matters but is limited without inventory co-optimization.

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

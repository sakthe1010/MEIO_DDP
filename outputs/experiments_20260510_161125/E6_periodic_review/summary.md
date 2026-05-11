# E6_periodic_review — Policy = periodic_review

*Section 4.8 — Policy Comparison*

---

## Purpose

Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

## Methodology

Each policy gets its own 100-trial Optuna search over its native parameter space (mode=inventory, dispatch fixed at 0.0, fill ≥ 92%). Headline metrics: total cost, fill rate, holding/transport mix, bullwhip per echelon.

## Hypothesis

*echelon_stock ≤ base_stock ≈ ss < periodic_review on cost. Echelon wins because warehouses see downstream pipeline; periodic loses to review delay.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | — |
| Trials run | 100 |
| Feasible trials | 0 |
| Best trial # | 95 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 3628 |
| `S_W1__SKU_B` | 1825 |
| `S_W1__SKU_C` | 2362 |
| `S_W1__SKU_D` | 1801 |
| `S_W1__SKU_E` | 1049 |
| `S_W2__SKU_A` | 5129 |
| `S_W2__SKU_B` | 583 |
| `S_W2__SKU_C` | 1665 |
| `S_W2__SKU_D` | 3109 |
| `S_W2__SKU_E` | 1942 |
| `S_R1__SKU_A` | 1098 |
| `S_R1__SKU_B` | 624 |
| `S_R1__SKU_C` | 818 |
| `S_R1__SKU_D` | 540 |
| `S_R1__SKU_E` | 613 |
| `S_R2__SKU_A` | 1236 |
| `S_R2__SKU_B` | 813 |
| `S_R2__SKU_C` | 599 |
| `S_R2__SKU_D` | 431 |
| `S_R2__SKU_E` | 627 |
| `S_R3__SKU_A` | 2952 |
| `S_R3__SKU_B` | 1064 |
| `S_R3__SKU_C` | 1679 |
| `S_R3__SKU_D` | 1423 |
| `S_R3__SKU_E` | 1170 |
| `R_W1__SKU_A` | 9 |
| `R_W1__SKU_B` | 13 |
| `R_W1__SKU_C` | 14 |
| `R_W1__SKU_D` | 3 |
| `R_W1__SKU_E` | 9 |
| `R_W2__SKU_A` | 4 |
| `R_W2__SKU_B` | 9 |
| `R_W2__SKU_C` | 7 |
| `R_W2__SKU_D` | 7 |
| `R_W2__SKU_E` | 2 |
| `R_R1__SKU_A` | 1 |
| `R_R1__SKU_B` | 9 |
| `R_R1__SKU_C` | 5 |
| `R_R1__SKU_D` | 3 |
| `R_R1__SKU_E` | 12 |
| `R_R2__SKU_A` | 12 |
| `R_R2__SKU_B` | 10 |
| `R_R2__SKU_C` | 7 |
| `R_R2__SKU_D` | 3 |
| `R_R2__SKU_E` | 7 |
| `R_R3__SKU_A` | 10 |
| `R_R3__SKU_B` | 8 |
| `R_R3__SKU_C` | 11 |
| `R_R3__SKU_D` | 6 |
| `R_R3__SKU_E` | 4 |
| `D_Supplier_W1` | 0.30383955832429643 |
| `D_Supplier_W2` | 0.789188523960806 |
| `D_W1_R1` | 0.42359206853684045 |
| `D_W1_R2` | 0.1380574096906839 |
| `D_W2_R3` | 0.6342473791481672 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **373,008** | 100% |
| Holding | 96,036 | 25.7% |
| Transport | 161,550 | 43.3% |
| Ordering | 8,835 | 2.4% |
| Shortage (backlog) | 106,588 | 28.6% |

**Overall fill rate: 84.25%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 90.32% ✗ |
| SKU_B | 73.18% ✗ |
| SKU_C | 64.51% ✗ |
| SKU_D | 99.84% ✓ |
| SKU_E | 94.04% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.5% | 59.8% | 58.0% | 99.7% | 82.3% |
| R2 | 72.7% | 82.4% | 70.9% | 99.6% | 95.1% |
| R3 | 92.3% | 79.6% | 67.6% | 100.0% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 1.000 |
| R1 | SKU_B | 63.848 ⚠ |
| R1 | SKU_C | 30.555 ⚠ |
| R1 | SKU_D | 27.285 ⚠ |
| R1 | SKU_E | 137.934 ⚠ |
| R2 | SKU_A | 237.536 ⚠ |
| R2 | SKU_B | 88.062 ⚠ |
| R2 | SKU_C | 47.096 ⚠ |
| R2 | SKU_D | 33.414 ⚠ |
| R2 | SKU_E | 105.944 ⚠ |
| R3 | SKU_A | 142.424 ⚠ |
| R3 | SKU_B | 79.523 ⚠ |
| R3 | SKU_C | 71.179 ⚠ |
| R3 | SKU_D | 74.893 ⚠ |
| R3 | SKU_E | 61.077 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 4.814 ⚠ |
| W1 | SKU_B | 2.898 ⚠ |
| W1 | SKU_C | 5.108 ⚠ |
| W1 | SKU_D | 1.001 |
| W1 | SKU_E | 2.130 ⚠ |
| W2 | SKU_A | 1.000 |
| W2 | SKU_B | 1.240 |
| W2 | SKU_C | 1.000 |
| W2 | SKU_D | 1.347 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **373,008**, dominated by transport (43.3%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **84.25%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 25.7% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_C** has the lowest fill rate (64.5%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 64.5% (SKU_C) to 99.8% (SKU_D) — a 35.3 pp range.

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
| Trials run | 80 |
| Feasible trials | 0 |
| Best trial # | 74 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2090 |
| `S_W1__SKU_B` | 1432 |
| `S_W1__SKU_C` | 3165 |
| `S_W1__SKU_D` | 1557 |
| `S_W1__SKU_E` | 2121 |
| `S_W2__SKU_A` | 2227 |
| `S_W2__SKU_B` | 877 |
| `S_W2__SKU_C` | 2281 |
| `S_W2__SKU_D` | 1028 |
| `S_W2__SKU_E` | 1754 |
| `S_R1__SKU_A` | 730 |
| `S_R1__SKU_B` | 727 |
| `S_R1__SKU_C` | 813 |
| `S_R1__SKU_D` | 811 |
| `S_R1__SKU_E` | 446 |
| `S_R2__SKU_A` | 1293 |
| `S_R2__SKU_B` | 752 |
| `S_R2__SKU_C` | 643 |
| `S_R2__SKU_D` | 433 |
| `S_R2__SKU_E` | 760 |
| `S_R3__SKU_A` | 3850 |
| `S_R3__SKU_B` | 510 |
| `S_R3__SKU_C` | 1672 |
| `S_R3__SKU_D` | 2039 |
| `S_R3__SKU_E` | 1176 |
| `R_W1__SKU_A` | 2 |
| `R_W1__SKU_B` | 7 |
| `R_W1__SKU_C` | 11 |
| `R_W1__SKU_D` | 9 |
| `R_W1__SKU_E` | 2 |
| `R_W2__SKU_A` | 7 |
| `R_W2__SKU_B` | 11 |
| `R_W2__SKU_C` | 5 |
| `R_W2__SKU_D` | 3 |
| `R_W2__SKU_E` | 10 |
| `R_R1__SKU_A` | 1 |
| `R_R1__SKU_B` | 6 |
| `R_R1__SKU_C` | 11 |
| `R_R1__SKU_D` | 2 |
| `R_R1__SKU_E` | 4 |
| `R_R2__SKU_A` | 8 |
| `R_R2__SKU_B` | 6 |
| `R_R2__SKU_C` | 5 |
| `R_R2__SKU_D` | 5 |
| `R_R2__SKU_E` | 11 |
| `R_R3__SKU_A` | 5 |
| `R_R3__SKU_B` | 4 |
| `R_R3__SKU_C` | 10 |
| `R_R3__SKU_D` | 5 |
| `R_R3__SKU_E` | 12 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **409,051** | 100% |
| Holding | 100,076 | 24.5% |
| Transport | 219,459 | 53.7% |
| Ordering | 10,330 | 2.5% |
| Shortage (backlog) | 79,185 | 19.4% |

**Overall fill rate: 88.48%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.57% ✓ |
| SKU_B | 81.32% ✗ |
| SKU_C | 66.17% ✗ |
| SKU_D | 99.32% ✓ |
| SKU_E | 91.32% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.1% | 97.1% | 36.5% | 100.0% | 100.0% |
| R2 | 99.5% | 86.1% | 94.7% | 97.0% | 99.0% |
| R3 | 100.0% | 59.6% | 80.4% | 100.0% | 82.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 1.000 |
| R1 | SKU_B | 39.636 ⚠ |
| R1 | SKU_C | 73.392 ⚠ |
| R1 | SKU_D | 14.246 ⚠ |
| R1 | SKU_E | 38.586 ⚠ |
| R2 | SKU_A | 151.748 ⚠ |
| R2 | SKU_B | 50.061 ⚠ |
| R2 | SKU_C | 31.943 ⚠ |
| R2 | SKU_D | 65.673 ⚠ |
| R2 | SKU_E | 173.422 ⚠ |
| R3 | SKU_A | 64.987 ⚠ |
| R3 | SKU_B | 34.906 ⚠ |
| R3 | SKU_C | 64.339 ⚠ |
| R3 | SKU_D | 60.387 ⚠ |
| R3 | SKU_E | 220.632 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.723 |
| W1 | SKU_B | 1.339 |
| W1 | SKU_C | 2.014 ⚠ |
| W1 | SKU_D | 7.534 ⚠ |
| W1 | SKU_E | 1.143 |
| W2 | SKU_A | 1.704 |
| W2 | SKU_B | 3.242 ⚠ |
| W2 | SKU_C | 1.033 |
| W2 | SKU_D | 1.000 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **409,051**, dominated by transport (53.7%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **88.48%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 24.5% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_C** has the lowest fill rate (66.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 66.2% (SKU_C) to 99.6% (SKU_A) — a 33.4 pp range.

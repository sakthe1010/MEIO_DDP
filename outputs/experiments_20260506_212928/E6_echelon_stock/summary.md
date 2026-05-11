# E6_echelon_stock — Policy = echelon_stock

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
| Feasible trials | 49 |
| Best trial # | 78 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 4283 |
| `S_W1__SKU_B` | 2566 |
| `S_W1__SKU_C` | 1765 |
| `S_W1__SKU_D` | 2392 |
| `S_W1__SKU_E` | 366 |
| `S_W2__SKU_A` | 5431 |
| `S_W2__SKU_B` | 1364 |
| `S_W2__SKU_C` | 2440 |
| `S_W2__SKU_D` | 2298 |
| `S_W2__SKU_E` | 1366 |
| `S_R1__SKU_A` | 1185 |
| `S_R1__SKU_B` | 385 |
| `S_R1__SKU_C` | 598 |
| `S_R1__SKU_D` | 248 |
| `S_R1__SKU_E` | 618 |
| `S_R2__SKU_A` | 1281 |
| `S_R2__SKU_B` | 822 |
| `S_R2__SKU_C` | 274 |
| `S_R2__SKU_D` | 323 |
| `S_R2__SKU_E` | 640 |
| `S_R3__SKU_A` | 3113 |
| `S_R3__SKU_B` | 1124 |
| `S_R3__SKU_C` | 919 |
| `S_R3__SKU_D` | 1389 |
| `S_R3__SKU_E` | 843 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **486,394** | 100% |
| Holding | 114,282 | 23.5% |
| Transport | 332,426 | 68.3% |
| Ordering | 35,220 | 7.2% |
| Shortage (backlog) | 4,465 | 0.9% |

**Overall fill rate: 98.46%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 100.00% ✓ |
| SKU_B | 99.86% ✓ |
| SKU_C | 94.30% ✓ |
| SKU_D | 98.54% ✓ |
| SKU_E | 99.68% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 99.6% | 97.2% | 95.3% | 99.8% |
| R2 | 100.0% | 100.0% | 84.6% | 100.0% | 99.0% |
| R3 | 100.0% | 100.0% | 96.0% | 100.0% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 1.000 |
| R1 | SKU_B | 1.000 |
| R1 | SKU_C | 3.848 ⚠ |
| R1 | SKU_D | 1.000 |
| R1 | SKU_E | 54.529 ⚠ |
| R2 | SKU_A | 1.000 |
| R2 | SKU_B | 1.000 |
| R2 | SKU_C | 9.185 ⚠ |
| R2 | SKU_D | 1.000 |
| R2 | SKU_E | 123.638 ⚠ |
| R3 | SKU_A | 1.000 |
| R3 | SKU_B | 20.167 ⚠ |
| R3 | SKU_C | 1.000 |
| R3 | SKU_D | 1.000 |
| R3 | SKU_E | 4.622 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.000 |
| W1 | SKU_B | 0.984 |
| W1 | SKU_C | 1.133 |
| W1 | SKU_D | 0.860 |
| W1 | SKU_E | 0.972 |
| W2 | SKU_A | 1.000 |
| W2 | SKU_B | 1.000 |
| W2 | SKU_C | 0.952 |
| W2 | SKU_D | 1.000 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **486,394**, dominated by transport (68.3%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **98.46%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 23.5% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 94.3% (SKU_C) to 100.0% (SKU_A) — a 5.7 pp range.

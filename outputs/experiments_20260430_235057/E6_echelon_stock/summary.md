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
| Feasible trials | 52 |
| Best trial # | 64 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 3758 |
| `S_W1__SKU_B` | 2136 |
| `S_W1__SKU_C` | 3185 |
| `S_W1__SKU_D` | 2115 |
| `S_W1__SKU_E` | 1160 |
| `S_W2__SKU_A` | 1443 |
| `S_W2__SKU_B` | 1371 |
| `S_W2__SKU_C` | 2838 |
| `S_W2__SKU_D` | 2226 |
| `S_W2__SKU_E` | 1882 |
| `S_R1__SKU_A` | 953 |
| `S_R1__SKU_B` | 263 |
| `S_R1__SKU_C` | 911 |
| `S_R1__SKU_D` | 321 |
| `S_R1__SKU_E` | 656 |
| `S_R2__SKU_A` | 1400 |
| `S_R2__SKU_B` | 489 |
| `S_R2__SKU_C` | 417 |
| `S_R2__SKU_D` | 348 |
| `S_R2__SKU_E` | 591 |
| `S_R3__SKU_A` | 2324 |
| `S_R3__SKU_B` | 982 |
| `S_R3__SKU_C` | 1073 |
| `S_R3__SKU_D` | 1757 |
| `S_R3__SKU_E` | 1090 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **495,132** | 100% |
| Holding | 128,144 | 25.9% |
| Transport | 332,050 | 67.1% |
| Ordering | 32,113 | 6.5% |
| Shortage (backlog) | 2,825 | 0.6% |

**Overall fill rate: 98.97%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.85% ✓ |
| SKU_B | 96.09% ✓ |
| SKU_C | 99.94% ✓ |
| SKU_D | 100.00% ✓ |
| SKU_E | 99.61% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 89.3% | 100.0% | 100.0% | 100.0% |
| R2 | 100.0% | 100.0% | 100.0% | 100.0% | 98.6% |
| R3 | 97.4% | 100.0% | 99.9% | 100.0% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 1.177 |
| R1 | SKU_B | 1.000 |
| R1 | SKU_C | 1.000 |
| R1 | SKU_D | 1.000 |
| R1 | SKU_E | 58.163 ⚠ |
| R2 | SKU_A | 7.836 ⚠ |
| R2 | SKU_B | 1.000 |
| R2 | SKU_C | 1.000 |
| R2 | SKU_D | 1.000 |
| R2 | SKU_E | 101.800 ⚠ |
| R3 | SKU_A | 72.689 ⚠ |
| R3 | SKU_B | 6.638 ⚠ |
| R3 | SKU_C | 1.000 |
| R3 | SKU_D | 17.799 ⚠ |
| R3 | SKU_E | 1.000 |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.221 |
| W1 | SKU_B | 0.820 |
| W1 | SKU_C | 1.000 |
| W1 | SKU_D | 1.000 |
| W1 | SKU_E | 1.113 |
| W2 | SKU_A | 0.987 |
| W2 | SKU_B | 1.000 |
| W2 | SKU_C | 0.989 |
| W2 | SKU_D | 1.000 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **495,132**, dominated by transport (67.1%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **98.97%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 25.9% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 96.1% (SKU_B) to 100.0% (SKU_D) — a 3.9 pp range.

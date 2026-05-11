# E6_ss — Policy = ss

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
| Feasible trials | 19 |
| Best trial # | 75 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2021 |
| `S_W1__SKU_B` | 2346 |
| `S_W1__SKU_C` | 2703 |
| `S_W1__SKU_D` | 1096 |
| `S_W1__SKU_E` | 1584 |
| `S_W2__SKU_A` | 3958 |
| `S_W2__SKU_B` | 1866 |
| `S_W2__SKU_C` | 2746 |
| `S_W2__SKU_D` | 2889 |
| `S_W2__SKU_E` | 1594 |
| `S_R1__SKU_A` | 886 |
| `S_R1__SKU_B` | 837 |
| `S_R1__SKU_C` | 502 |
| `S_R1__SKU_D` | 764 |
| `S_R1__SKU_E` | 407 |
| `S_R2__SKU_A` | 1140 |
| `S_R2__SKU_B` | 503 |
| `S_R2__SKU_C` | 711 |
| `S_R2__SKU_D` | 232 |
| `S_R2__SKU_E` | 752 |
| `S_R3__SKU_A` | 2769 |
| `S_R3__SKU_B` | 525 |
| `S_R3__SKU_C` | 1737 |
| `S_R3__SKU_D` | 2144 |
| `S_R3__SKU_E` | 1284 |
| `alpha_W1__SKU_A` | 0.7986772868384685 |
| `alpha_W1__SKU_B` | 0.506002050927549 |
| `alpha_W1__SKU_C` | 0.7130316787042164 |
| `alpha_W1__SKU_D` | 0.8512112771714075 |
| `alpha_W1__SKU_E` | 0.5445158338525877 |
| `alpha_W2__SKU_A` | 0.3942859277005339 |
| `alpha_W2__SKU_B` | 0.3008537072502877 |
| `alpha_W2__SKU_C` | 0.4321347296984812 |
| `alpha_W2__SKU_D` | 0.5742729153285345 |
| `alpha_W2__SKU_E` | 0.4036622185851749 |
| `alpha_R1__SKU_A` | 0.3379487543334862 |
| `alpha_R1__SKU_B` | 0.7890913871189282 |
| `alpha_R1__SKU_C` | 0.4618072837100836 |
| `alpha_R1__SKU_D` | 0.32807879040988774 |
| `alpha_R1__SKU_E` | 0.5955079249295052 |
| `alpha_R2__SKU_A` | 0.4783656545538503 |
| `alpha_R2__SKU_B` | 0.31442864305319496 |
| `alpha_R2__SKU_C` | 0.5244332330124533 |
| `alpha_R2__SKU_D` | 0.806372934435694 |
| `alpha_R2__SKU_E` | 0.4033766999262082 |
| `alpha_R3__SKU_A` | 0.4908236079128822 |
| `alpha_R3__SKU_B` | 0.48982571863268554 |
| `alpha_R3__SKU_C` | 0.40583287504835597 |
| `alpha_R3__SKU_D` | 0.5936279278882141 |
| `alpha_R3__SKU_E` | 0.7508829312647949 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **352,015** | 100% |
| Holding | 115,149 | 32.7% |
| Transport | 212,961 | 60.5% |
| Ordering | 8,686 | 2.5% |
| Shortage (backlog) | 15,219 | 4.3% |

**Overall fill rate: 94.33%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 95.04% ✓ |
| SKU_B | 89.45% ✗ |
| SKU_C | 90.16% ✗ |
| SKU_D | 98.13% ✓ |
| SKU_E | 100.00% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 85.5% | 100.0% | 76.8% | 99.7% | 100.0% |
| R2 | 99.7% | 84.7% | 100.0% | 92.3% | 100.0% |
| R3 | 100.0% | 82.1% | 97.9% | 100.0% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 51.213 ⚠ |
| R1 | SKU_B | 15.812 ⚠ |
| R1 | SKU_C | 14.223 ⚠ |
| R1 | SKU_D | 92.468 ⚠ |
| R1 | SKU_E | 37.391 ⚠ |
| R2 | SKU_A | 114.092 ⚠ |
| R2 | SKU_B | 51.485 ⚠ |
| R2 | SKU_C | 42.464 ⚠ |
| R2 | SKU_D | 6.454 ⚠ |
| R2 | SKU_E | 148.665 ⚠ |
| R3 | SKU_A | 101.759 ⚠ |
| R3 | SKU_B | 40.851 ⚠ |
| R3 | SKU_C | 55.290 ⚠ |
| R3 | SKU_D | 122.590 ⚠ |
| R3 | SKU_E | 67.050 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.000 |
| W1 | SKU_B | 5.950 ⚠ |
| W1 | SKU_C | 3.496 ⚠ |
| W1 | SKU_D | 1.478 |
| W1 | SKU_E | 3.097 ⚠ |
| W2 | SKU_A | 2.103 ⚠ |
| W2 | SKU_B | 6.129 ⚠ |
| W2 | SKU_C | 2.186 ⚠ |
| W2 | SKU_D | 2.118 ⚠ |
| W2 | SKU_E | 3.526 ⚠ |

## Key Observations for Report

- Baseline total cost is **352,015**, dominated by transport (60.5%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **94.33%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 32.7% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (89.5%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 89.5% (SKU_B) to 100.0% (SKU_E) — a 10.5 pp range.

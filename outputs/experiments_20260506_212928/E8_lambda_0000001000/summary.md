# E8_lambda_1e+03 — Bullwhip-aware (λ=1e+03)

*Section 4.10 — Bullwhip-Aware Optimization*

---

## Purpose

Add bullwhip ratio as a secondary optimization objective. Tests whether a small cost increase can buy a meaningful bullwhip reduction — directly addressing the supply-chain literature's main motivation for measuring bullwhip.

## Methodology

Joint-mode optimizer with augmented objective: total_cost + λ × Σ_node bullwhip_ratio. Sweep λ ∈ {0, 1e3, 1e4, 1e5, 1e6} and plot the (cost, bullwhip) Pareto. Bullwhip is the corrected per-echelon metric from A2.

## Hypothesis

*There exists a small λ such that cost rises < 5% while total bullwhip drops >20% — i.e., the cost-optimal solution from E3 is bullwhip-suboptimal and a modest tradeoff is worthwhile.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | — |
| Trials run | 80 |
| Feasible trials | 30 |
| Best trial # | 52 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1260 |
| `S_W1__SKU_B` | 1396 |
| `S_W1__SKU_C` | 795 |
| `S_W1__SKU_D` | 491 |
| `S_W1__SKU_E` | 1048 |
| `S_W2__SKU_A` | 3598 |
| `S_W2__SKU_B` | 1563 |
| `S_W2__SKU_C` | 2518 |
| `S_W2__SKU_D` | 811 |
| `S_W2__SKU_E` | 976 |
| `S_R1__SKU_A` | 763 |
| `S_R1__SKU_B` | 751 |
| `S_R1__SKU_C` | 1056 |
| `S_R1__SKU_D` | 561 |
| `S_R1__SKU_E` | 193 |
| `S_R2__SKU_A` | 1025 |
| `S_R2__SKU_B` | 534 |
| `S_R2__SKU_C` | 672 |
| `S_R2__SKU_D` | 582 |
| `S_R2__SKU_E` | 717 |
| `S_R3__SKU_A` | 1688 |
| `S_R3__SKU_B` | 1347 |
| `S_R3__SKU_C` | 1895 |
| `S_R3__SKU_D` | 1610 |
| `S_R3__SKU_E` | 737 |
| `D_Supplier_W1` | 0.8049585039372876 |
| `D_Supplier_W2` | 0.31375454101137384 |
| `D_W1_R1` | 0.16754430655289929 |
| `D_W1_R2` | 0.7740196423971965 |
| `D_W2_R3` | 0.5125792981660319 |
| `lambda` | 1000.0 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **290,180** | 100% |
| Holding | 94,300 | 32.5% |
| Transport | 141,850 | 48.9% |
| Ordering | 38,832 | 13.4% |
| Shortage (backlog) | 15,198 | 5.2% |

**Overall fill rate: 95.51%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 93.00% ✓ |
| SKU_B | 99.94% ✓ |
| SKU_C | 95.08% ✓ |
| SKU_D | 98.67% ✓ |
| SKU_E | 94.02% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 89.2% | 100.0% | 100.0% | 100.0% | 77.4% |
| R2 | 87.0% | 99.8% | 74.1% | 94.2% | 100.0% |
| R3 | 99.0% | 100.0% | 100.0% | 100.0% | 99.8% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 1.000 |
| R1 | SKU_B | 1.000 |
| R1 | SKU_C | 1.000 |
| R1 | SKU_D | 1.000 |
| R1 | SKU_E | 1.000 |
| R2 | SKU_A | 1.000 |
| R2 | SKU_B | 1.000 |
| R2 | SKU_C | 1.000 |
| R2 | SKU_D | 1.000 |
| R2 | SKU_E | 1.000 |
| R3 | SKU_A | 1.000 |
| R3 | SKU_B | 1.000 |
| R3 | SKU_C | 1.000 |
| R3 | SKU_D | 1.000 |
| R3 | SKU_E | 1.000 |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.001 |
| W1 | SKU_B | 1.003 |
| W1 | SKU_C | 1.001 |
| W1 | SKU_D | 1.004 |
| W1 | SKU_E | 0.999 |
| W2 | SKU_A | 0.998 |
| W2 | SKU_B | 0.998 |
| W2 | SKU_C | 1.000 |
| W2 | SKU_D | 1.002 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **290,180**, dominated by transport (48.9%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **95.51%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 32.5% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 93.0% (SKU_A) to 99.9% (SKU_B) — a 6.9 pp range.

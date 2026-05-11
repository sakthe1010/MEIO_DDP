# E8_lambda_1e+05 — Bullwhip-aware (λ=1e+05)

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
| Feasible trials | 34 |
| Best trial # | 74 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2293 |
| `S_W1__SKU_B` | 1051 |
| `S_W1__SKU_C` | 2908 |
| `S_W1__SKU_D` | 948 |
| `S_W1__SKU_E` | 1733 |
| `S_W2__SKU_A` | 1682 |
| `S_W2__SKU_B` | 1072 |
| `S_W2__SKU_C` | 1538 |
| `S_W2__SKU_D` | 454 |
| `S_W2__SKU_E` | 1376 |
| `S_R1__SKU_A` | 924 |
| `S_R1__SKU_B` | 666 |
| `S_R1__SKU_C` | 1038 |
| `S_R1__SKU_D` | 773 |
| `S_R1__SKU_E` | 361 |
| `S_R2__SKU_A` | 712 |
| `S_R2__SKU_B` | 462 |
| `S_R2__SKU_C` | 408 |
| `S_R2__SKU_D` | 348 |
| `S_R2__SKU_E` | 599 |
| `S_R3__SKU_A` | 1792 |
| `S_R3__SKU_B` | 744 |
| `S_R3__SKU_C` | 1725 |
| `S_R3__SKU_D` | 1165 |
| `S_R3__SKU_E` | 513 |
| `D_Supplier_W1` | 0.7315821155023298 |
| `D_Supplier_W2` | 0.36284323106261374 |
| `D_W1_R1` | 0.8797377746827182 |
| `D_W1_R2` | 0.690758573468549 |
| `D_W2_R3` | 0.4024863272237077 |
| `lambda` | 100000.0 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **260,690** | 100% |
| Holding | 77,247 | 29.6% |
| Transport | 136,930 | 52.5% |
| Ordering | 38,832 | 14.9% |
| Shortage (backlog) | 7,682 | 2.9% |

**Overall fill rate: 96.83%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.47% ✓ |
| SKU_B | 99.06% ✓ |
| SKU_C | 99.36% ✓ |
| SKU_D | 97.22% ✓ |
| SKU_E | 85.76% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.0% | 100.0% | 100.0% | 100.0% | 99.9% |
| R2 | 98.9% | 96.9% | 96.6% | 99.5% | 100.0% |
| R3 | 97.8% | 100.0% | 100.0% | 94.3% | 69.5% |

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

- Baseline total cost is **260,690**, dominated by transport (52.5%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.83%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 29.6% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_E** has the lowest fill rate (85.8%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 85.8% (SKU_E) to 99.4% (SKU_C) — a 13.6 pp range.

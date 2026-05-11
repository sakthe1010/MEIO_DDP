# E8_lambda_1e+04 — Bullwhip-aware (λ=1e+04)

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
| Feasible trials | 33 |
| Best trial # | 47 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2983 |
| `S_W1__SKU_B` | 1593 |
| `S_W1__SKU_C` | 972 |
| `S_W1__SKU_D` | 741 |
| `S_W1__SKU_E` | 722 |
| `S_W2__SKU_A` | 1448 |
| `S_W2__SKU_B` | 1420 |
| `S_W2__SKU_C` | 2552 |
| `S_W2__SKU_D` | 441 |
| `S_W2__SKU_E` | 836 |
| `S_R1__SKU_A` | 782 |
| `S_R1__SKU_B` | 264 |
| `S_R1__SKU_C` | 1136 |
| `S_R1__SKU_D` | 406 |
| `S_R1__SKU_E` | 113 |
| `S_R2__SKU_A` | 777 |
| `S_R2__SKU_B` | 651 |
| `S_R2__SKU_C` | 742 |
| `S_R2__SKU_D` | 602 |
| `S_R2__SKU_E` | 654 |
| `S_R3__SKU_A` | 2750 |
| `S_R3__SKU_B` | 836 |
| `S_R3__SKU_C` | 1723 |
| `S_R3__SKU_D` | 1517 |
| `S_R3__SKU_E` | 610 |
| `D_Supplier_W1` | 0.43546059506397977 |
| `D_Supplier_W2` | 0.39808769056639093 |
| `D_W1_R1` | 0.31453825571078264 |
| `D_W1_R2` | 0.8982996967414519 |
| `D_W2_R3` | 0.6629316762429349 |
| `lambda` | 10000.0 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **282,938** | 100% |
| Holding | 81,785 | 28.9% |
| Transport | 139,871 | 49.4% |
| Ordering | 38,832 | 13.7% |
| Shortage (backlog) | 22,451 | 7.9% |

**Overall fill rate: 93.10%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 97.56% ✓ |
| SKU_B | 84.78% ✗ |
| SKU_C | 98.29% ✓ |
| SKU_D | 99.59% ✓ |
| SKU_E | 74.67% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 92.9% | 58.5% | 100.0% | 98.7% | 16.2% |
| R2 | 99.7% | 100.0% | 91.0% | 100.0% | 100.0% |
| R3 | 100.0% | 100.0% | 100.0% | 100.0% | 92.7% |

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

- Baseline total cost is **282,938**, dominated by transport (49.4%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **93.10%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 28.9% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_E** has the lowest fill rate (74.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 74.7% (SKU_E) to 99.6% (SKU_D) — a 24.9 pp range.

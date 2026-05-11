# E8_lambda_1e+06 — Bullwhip-aware (λ=1e+06)

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
| Feasible trials | 24 |
| Best trial # | 24 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1655 |
| `S_W1__SKU_B` | 1025 |
| `S_W1__SKU_C` | 1753 |
| `S_W1__SKU_D` | 1708 |
| `S_W1__SKU_E` | 1474 |
| `S_W2__SKU_A` | 3418 |
| `S_W2__SKU_B` | 1689 |
| `S_W2__SKU_C` | 1022 |
| `S_W2__SKU_D` | 697 |
| `S_W2__SKU_E` | 559 |
| `S_R1__SKU_A` | 767 |
| `S_R1__SKU_B` | 672 |
| `S_R1__SKU_C` | 912 |
| `S_R1__SKU_D` | 675 |
| `S_R1__SKU_E` | 545 |
| `S_R2__SKU_A` | 922 |
| `S_R2__SKU_B` | 541 |
| `S_R2__SKU_C` | 281 |
| `S_R2__SKU_D` | 562 |
| `S_R2__SKU_E` | 562 |
| `S_R3__SKU_A` | 1633 |
| `S_R3__SKU_B` | 993 |
| `S_R3__SKU_C` | 1502 |
| `S_R3__SKU_D` | 1019 |
| `S_R3__SKU_E` | 846 |
| `D_Supplier_W1` | 0.8146945782154565 |
| `D_Supplier_W2` | 0.3432400448681172 |
| `D_W1_R1` | 0.21562718221558336 |
| `D_W1_R2` | 0.8815066168728382 |
| `D_W2_R3` | 0.3573266002694736 |
| `lambda` | 1000000.0 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **271,535** | 100% |
| Holding | 83,330 | 30.7% |
| Transport | 140,501 | 51.7% |
| Ordering | 38,832 | 14.3% |
| Shortage (backlog) | 8,872 | 3.3% |

**Overall fill rate: 96.75%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 95.97% ✓ |
| SKU_B | 99.72% ✓ |
| SKU_C | 92.41% ✓ |
| SKU_D | 99.37% ✓ |
| SKU_E | 99.42% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 90.3% | 100.0% | 99.8% | 100.0% | 100.0% |
| R2 | 98.7% | 99.1% | 61.6% | 100.0% | 100.0% |
| R3 | 98.9% | 100.0% | 99.5% | 98.6% | 98.8% |

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

- Baseline total cost is **271,535**, dominated by transport (51.7%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.75%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 30.7% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 92.4% (SKU_C) to 99.7% (SKU_B) — a 7.3 pp range.

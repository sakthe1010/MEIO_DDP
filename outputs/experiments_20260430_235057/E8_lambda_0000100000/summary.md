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
| Feasible trials | 31 |
| Best trial # | 66 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2562 |
| `S_W1__SKU_B` | 1048 |
| `S_W1__SKU_C` | 908 |
| `S_W1__SKU_D` | 1324 |
| `S_W1__SKU_E` | 1543 |
| `S_W2__SKU_A` | 2515 |
| `S_W2__SKU_B` | 241 |
| `S_W2__SKU_C` | 1313 |
| `S_W2__SKU_D` | 2786 |
| `S_W2__SKU_E` | 1353 |
| `S_R1__SKU_A` | 1186 |
| `S_R1__SKU_B` | 609 |
| `S_R1__SKU_C` | 977 |
| `S_R1__SKU_D` | 782 |
| `S_R1__SKU_E` | 254 |
| `S_R2__SKU_A` | 1199 |
| `S_R2__SKU_B` | 458 |
| `S_R2__SKU_C` | 490 |
| `S_R2__SKU_D` | 267 |
| `S_R2__SKU_E` | 535 |
| `S_R3__SKU_A` | 2255 |
| `S_R3__SKU_B` | 920 |
| `S_R3__SKU_C` | 1777 |
| `S_R3__SKU_D` | 1209 |
| `S_R3__SKU_E` | 635 |
| `D_Supplier_W1` | 0.5532952590535039 |
| `D_Supplier_W2` | 0.27964693420357484 |
| `D_W1_R1` | 0.6203314882324686 |
| `D_W1_R2` | 0.3294638917272125 |
| `D_W2_R3` | 0.7236272637786865 |
| `lambda` | 100000.0 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **287,111** | 100% |
| Holding | 92,636 | 32.3% |
| Transport | 142,820 | 49.7% |
| Ordering | 38,832 | 13.5% |
| Shortage (backlog) | 12,823 | 4.5% |

**Overall fill rate: 97.13%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 100.00% ✓ |
| SKU_B | 97.51% ✓ |
| SKU_C | 93.29% ✓ |
| SKU_D | 95.93% ✓ |
| SKU_E | 97.12% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 94.6% |
| R2 | 100.0% | 96.5% | 64.7% | 82.2% | 100.0% |
| R3 | 100.0% | 95.7% | 100.0% | 100.0% | 96.8% |

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

- Baseline total cost is **287,111**, dominated by transport (49.7%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **97.13%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 32.3% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 93.3% (SKU_C) to 100.0% (SKU_A) — a 6.7 pp range.

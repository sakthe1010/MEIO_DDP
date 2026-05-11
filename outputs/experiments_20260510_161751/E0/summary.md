# E0 — Analytical Baseline

*Section 4.1 — Baseline Performance*

---

## Purpose

Establish a reference point using analytically derived base-stock levels (newsvendor formula) with no transport consolidation constraint. This represents the standard textbook multi-echelon policy without any joint optimization.

## Methodology

Base-stock levels are computed at runtime from the realised demand series: S = μ·(L+1) + z·σ·√(L+1), where L is the lane lead time, μ and σ are the post-warmup mean and standard deviation of demand, and z is the service-level z-score. Warehouse levels are sized for aggregated downstream demand. No minimum dispatch utilization is enforced — every order is shipped immediately regardless of vehicle fill level.

## Hypothesis

*The analytical baseline will provide acceptable fill rates but high transport costs due to frequent small shipments, and will serve as the upper-bound cost reference for optimization experiments.*

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1766 |
| `S_W1__SKU_B` | 943 |
| `S_W1__SKU_C` | 1245 |
| `S_W1__SKU_D` | 805 |
| `S_W1__SKU_E` | 668 |
| `S_W2__SKU_A` | 1610 |
| `S_W2__SKU_B` | 535 |
| `S_W2__SKU_C` | 1069 |
| `S_W2__SKU_D` | 813 |
| `S_W2__SKU_E` | 672 |
| `S_R1__SKU_A` | 573 |
| `S_R1__SKU_B` | 287 |
| `S_R1__SKU_C` | 459 |
| `S_R1__SKU_D` | 253 |
| `S_R1__SKU_E` | 181 |
| `S_R2__SKU_A` | 482 |
| `S_R2__SKU_B` | 297 |
| `S_R2__SKU_C` | 289 |
| `S_R2__SKU_D` | 239 |
| `S_R2__SKU_E` | 237 |
| `S_R3__SKU_A` | 1178 |
| `S_R3__SKU_B` | 393 |
| `S_R3__SKU_C` | 791 |
| `S_R3__SKU_D` | 596 |
| `S_R3__SKU_E` | 491 |
| `_note` | Newsvendor S = μ(L+1) + z·σ·√(L+1), z=1.64 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **251,127** | 100% |
| Holding | 20,931 | 8.3% |
| Transport | 165,825 | 66.0% |
| Ordering | 38,832 | 15.5% |
| Shortage (backlog) | 25,539 | 10.2% |

**Overall fill rate: 91.59%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 92.94% ✓ |
| SKU_B | 86.12% ✗ |
| SKU_C | 86.91% ✗ |
| SKU_D | 95.64% ✓ |
| SKU_E | 96.75% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 96.3% | 94.3% | 93.2% | 96.2% | 96.8% |
| R2 | 93.6% | 79.9% | 85.2% | 96.1% | 96.3% |
| R3 | 90.0% | 82.7% | 81.9% | 95.1% | 97.0% |

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

- Baseline total cost is **251,127**, dominated by transport (66.0%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **91.59%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 8.3% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (86.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 86.1% (SKU_B) to 96.7% (SKU_E) — a 10.6 pp range.

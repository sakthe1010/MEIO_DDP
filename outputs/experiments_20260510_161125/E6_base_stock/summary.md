# E6_base_stock — Policy = base_stock

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
| Trials run | 100 |
| Feasible trials | 52 |
| Best trial # | 93 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 3276 |
| `S_W1__SKU_B` | 1809 |
| `S_W1__SKU_C` | 1902 |
| `S_W1__SKU_D` | 1069 |
| `S_W1__SKU_E` | 604 |
| `S_W2__SKU_A` | 3527 |
| `S_W2__SKU_B` | 1881 |
| `S_W2__SKU_C` | 2664 |
| `S_W2__SKU_D` | 343 |
| `S_W2__SKU_E` | 1020 |
| `S_R1__SKU_A` | 1484 |
| `S_R1__SKU_B` | 688 |
| `S_R1__SKU_C` | 965 |
| `S_R1__SKU_D` | 510 |
| `S_R1__SKU_E` | 441 |
| `S_R2__SKU_A` | 666 |
| `S_R2__SKU_B` | 566 |
| `S_R2__SKU_C` | 572 |
| `S_R2__SKU_D` | 665 |
| `S_R2__SKU_E` | 743 |
| `S_R3__SKU_A` | 1613 |
| `S_R3__SKU_B` | 1066 |
| `S_R3__SKU_C` | 1256 |
| `S_R3__SKU_D` | 1507 |
| `S_R3__SKU_E` | 943 |
| `D_Supplier_W1` | 0.8006481473078624 |
| `D_Supplier_W2` | 0.29964088017351254 |
| `D_W1_R1` | 0.5601228365036266 |
| `D_W1_R2` | 0.42737315182569163 |
| `D_W2_R3` | 0.4028256711182447 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **288,490** | 100% |
| Holding | 106,771 | 37.0% |
| Transport | 141,288 | 49.0% |
| Ordering | 38,832 | 13.5% |
| Shortage (backlog) | 1,599 | 0.6% |

**Overall fill rate: 99.29%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.21% ✓ |
| SKU_B | 99.99% ✓ |
| SKU_C | 99.54% ✓ |
| SKU_D | 100.00% ✓ |
| SKU_E | 100.00% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| R2 | 96.7% | 100.0% | 100.0% | 100.0% | 100.0% |
| R3 | 97.6% | 100.0% | 98.9% | 100.0% | 100.0% |

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

- Baseline total cost is **288,490**, dominated by transport (49.0%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **99.29%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 37.0% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 98.2% (SKU_A) to 100.0% (SKU_D) — a 1.8 pp range.

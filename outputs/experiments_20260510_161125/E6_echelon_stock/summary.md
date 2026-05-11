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
| Trials run | 100 |
| Feasible trials | 62 |
| Best trial # | 73 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 4807 |
| `S_W1__SKU_B` | 1812 |
| `S_W1__SKU_C` | 2145 |
| `S_W1__SKU_D` | 1711 |
| `S_W1__SKU_E` | 1611 |
| `S_W2__SKU_A` | 4394 |
| `S_W2__SKU_B` | 1322 |
| `S_W2__SKU_C` | 2863 |
| `S_W2__SKU_D` | 1237 |
| `S_W2__SKU_E` | 1352 |
| `S_R1__SKU_A` | 879 |
| `S_R1__SKU_B` | 603 |
| `S_R1__SKU_C` | 727 |
| `S_R1__SKU_D` | 813 |
| `S_R1__SKU_E` | 293 |
| `S_R2__SKU_A` | 872 |
| `S_R2__SKU_B` | 334 |
| `S_R2__SKU_C` | 198 |
| `S_R2__SKU_D` | 332 |
| `S_R2__SKU_E` | 546 |
| `S_R3__SKU_A` | 2398 |
| `S_R3__SKU_B` | 493 |
| `S_R3__SKU_C` | 1229 |
| `S_R3__SKU_D` | 671 |
| `S_R3__SKU_E` | 1049 |
| `D_Supplier_W1` | 0.4466225160944559 |
| `D_Supplier_W2` | 0.3777309225163263 |
| `D_W1_R1` | 0.7440719660815869 |
| `D_W1_R2` | 0.21837033580134227 |
| `D_W2_R3` | 0.46277674044097833 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **306,613** | 100% |
| Holding | 110,407 | 36.0% |
| Transport | 155,827 | 50.8% |
| Ordering | 24,204 | 7.9% |
| Shortage (backlog) | 16,175 | 5.3% |

**Overall fill rate: 96.36%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.91% ✓ |
| SKU_B | 95.98% ✓ |
| SKU_C | 91.73% ✗ |
| SKU_D | 92.45% ✓ |
| SKU_E | 99.98% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.7% | 99.6% | 98.6% | 99.3% | 99.9% |
| R2 | 100.0% | 91.1% | 59.7% | 89.4% | 100.0% |
| R3 | 100.0% | 96.4% | 99.8% | 89.4% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 16.914 ⚠ |
| R1 | SKU_B | 11.441 ⚠ |
| R1 | SKU_C | 10.188 ⚠ |
| R1 | SKU_D | 74.732 ⚠ |
| R1 | SKU_E | 12.857 ⚠ |
| R2 | SKU_A | 20.503 ⚠ |
| R2 | SKU_B | 16.824 ⚠ |
| R2 | SKU_C | 10.908 ⚠ |
| R2 | SKU_D | 94.894 ⚠ |
| R2 | SKU_E | 14.966 ⚠ |
| R3 | SKU_A | 15.864 ⚠ |
| R3 | SKU_B | 13.090 ⚠ |
| R3 | SKU_C | 9.005 ⚠ |
| R3 | SKU_D | 22.749 ⚠ |
| R3 | SKU_E | 64.257 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.839 |
| W1 | SKU_B | 2.040 ⚠ |
| W1 | SKU_C | 2.129 ⚠ |
| W1 | SKU_D | 2.113 ⚠ |
| W1 | SKU_E | 2.246 ⚠ |
| W2 | SKU_A | 1.044 |
| W2 | SKU_B | 0.845 |
| W2 | SKU_C | 0.839 |
| W2 | SKU_D | 1.805 |
| W2 | SKU_E | 1.488 |

## Key Observations for Report

- Baseline total cost is **306,613**, dominated by transport (50.8%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.36%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 36.0% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_C** has the lowest fill rate (91.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 91.7% (SKU_C) to 100.0% (SKU_E) — a 8.3 pp range.

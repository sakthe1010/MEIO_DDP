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
| Trials run | 80 |
| Feasible trials | 30 |
| Best trial # | 43 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 943 |
| `S_W1__SKU_B` | 1186 |
| `S_W1__SKU_C` | 1181 |
| `S_W1__SKU_D` | 1509 |
| `S_W1__SKU_E` | 373 |
| `S_W2__SKU_A` | 1676 |
| `S_W2__SKU_B` | 205 |
| `S_W2__SKU_C` | 2746 |
| `S_W2__SKU_D` | 1776 |
| `S_W2__SKU_E` | 341 |
| `S_R1__SKU_A` | 999 |
| `S_R1__SKU_B` | 735 |
| `S_R1__SKU_C` | 430 |
| `S_R1__SKU_D` | 271 |
| `S_R1__SKU_E` | 182 |
| `S_R2__SKU_A` | 1437 |
| `S_R2__SKU_B` | 447 |
| `S_R2__SKU_C` | 254 |
| `S_R2__SKU_D` | 235 |
| `S_R2__SKU_E` | 513 |
| `S_R3__SKU_A` | 1207 |
| `S_R3__SKU_B` | 885 |
| `S_R3__SKU_C` | 1989 |
| `S_R3__SKU_D` | 1749 |
| `S_R3__SKU_E` | 961 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **458,021** | 100% |
| Holding | 76,892 | 16.8% |
| Transport | 331,650 | 72.4% |
| Ordering | 38,832 | 8.5% |
| Shortage (backlog) | 10,646 | 2.3% |

**Overall fill rate: 96.29%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 96.70% ✓ |
| SKU_B | 100.00% ✓ |
| SKU_C | 90.11% ✗ |
| SKU_D | 98.98% ✓ |
| SKU_E | 98.07% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 89.7% | 98.5% | 97.0% |
| R2 | 97.5% | 100.0% | 69.0% | 97.6% | 95.8% |
| R3 | 93.7% | 100.0% | 100.0% | 100.0% | 100.0% |

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

- Baseline total cost is **458,021**, dominated by transport (72.4%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.29%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 16.8% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_C** has the lowest fill rate (90.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 90.1% (SKU_C) to 100.0% (SKU_B) — a 9.9 pp range.

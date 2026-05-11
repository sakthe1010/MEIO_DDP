# E2 — Inventory-Only Optimization

*Section 4.4 — Inventory-Only Optimization*

---

## Purpose

Optimize base-stock levels per node and SKU while keeping dispatch thresholds at zero (immediate dispatch). This answers: how much cost can be saved by right-sizing inventory alone, without touching transport policy?

## Methodology

Optuna TPE sampler searches base-stock levels in [30%, 300%] of analytical S, with a floor of 10 units. Dispatch thresholds remain at 0.0 (no consolidation). Same fill rate constraint (≥ 92%) and penalty structure as E1b.

## Hypothesis

*Inventory optimization will improve fill rates at a cost of higher holding expenditure. Total cost may not decrease significantly because transport costs (the largest component) are untouched.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | inventory |
| Trials run | 40 |
| Feasible trials | 9 |
| Best trial # | 26 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1944 |
| `S_W1__SKU_B` | 1715 |
| `S_W1__SKU_C` | 1154 |
| `S_W1__SKU_D` | 1397 |
| `S_W1__SKU_E` | 211 |
| `S_W2__SKU_A` | 3076 |
| `S_W2__SKU_B` | 966 |
| `S_W2__SKU_C` | 2501 |
| `S_W2__SKU_D` | 2093 |
| `S_W2__SKU_E` | 1735 |
| `S_R1__SKU_A` | 493 |
| `S_R1__SKU_B` | 352 |
| `S_R1__SKU_C` | 454 |
| `S_R1__SKU_D` | 385 |
| `S_R1__SKU_E` | 313 |
| `S_R2__SKU_A` | 776 |
| `S_R2__SKU_B` | 236 |
| `S_R2__SKU_C` | 411 |
| `S_R2__SKU_D` | 313 |
| `S_R2__SKU_E` | 535 |
| `S_R3__SKU_A` | 1551 |
| `S_R3__SKU_B` | 811 |
| `S_R3__SKU_C` | 2185 |
| `S_R3__SKU_D` | 1435 |
| `S_R3__SKU_E` | 1318 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **488,965** | 100% |
| Holding | 99,833 | 20.4% |
| Transport | 331,650 | 67.8% |
| Ordering | 38,832 | 7.9% |
| Shortage (backlog) | 18,650 | 3.8% |

**Overall fill rate: 93.51%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E2 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 488,965 | -17.3% increase |
| Fill rate | 91.59% | 93.51% | +1.92 pp |
| Transport % | 79.5% | 67.8% | -11.7 pp |
| Holding % | 5.0% | 20.4% | +15.4 pp |
| Shortage % | 6.1% | 3.8% | -2.3 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 95.02% ✓ |
| SKU_B | 89.25% ✗ |
| SKU_C | 95.63% ✓ |
| SKU_D | 100.00% ✓ |
| SKU_E | 83.13% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 85.2% | 99.3% | 92.6% | 100.0% | 100.0% |
| R2 | 100.0% | 65.2% | 92.1% | 100.0% | 38.2% |
| R3 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |

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

- Total cost is **17.3% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **1.92 percentage points** over baseline.
- Transport cost share decreased by **11.7 pp** (from 79.5% to 67.8%), reflecting effective vehicle consolidation.
- Holding cost share is **15.4 pp higher** (20.4% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.3 pp** (3.8% vs 6.1% in E0).
- **SKU_E** has the lowest fill rate (83.1%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.1% (SKU_E) to 100.0% (SKU_D) — a 16.9 pp range.

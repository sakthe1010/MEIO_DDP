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
| Trials run | 100 |
| Feasible trials | 51 |
| Best trial # | 94 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2042 |
| `S_W1__SKU_B` | 2074 |
| `S_W1__SKU_C` | 1348 |
| `S_W1__SKU_D` | 1465 |
| `S_W1__SKU_E` | 710 |
| `S_W2__SKU_A` | 1699 |
| `S_W2__SKU_B` | 356 |
| `S_W2__SKU_C` | 717 |
| `S_W2__SKU_D` | 2139 |
| `S_W2__SKU_E` | 1356 |
| `S_R1__SKU_A` | 1252 |
| `S_R1__SKU_B` | 733 |
| `S_R1__SKU_C` | 819 |
| `S_R1__SKU_D` | 396 |
| `S_R1__SKU_E` | 272 |
| `S_R2__SKU_A` | 625 |
| `S_R2__SKU_B` | 326 |
| `S_R2__SKU_C` | 290 |
| `S_R2__SKU_D` | 437 |
| `S_R2__SKU_E` | 370 |
| `S_R3__SKU_A` | 1391 |
| `S_R3__SKU_B` | 964 |
| `S_R3__SKU_C` | 1875 |
| `S_R3__SKU_D` | 615 |
| `S_R3__SKU_E` | 1418 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **458,890** | 100% |
| Holding | 86,076 | 18.8% |
| Transport | 331,650 | 72.3% |
| Ordering | 38,832 | 8.5% |
| Shortage (backlog) | 2,333 | 0.5% |

**Overall fill rate: 99.23%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E2 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 458,890 | -10.1% increase |
| Fill rate | 91.59% | 99.23% | +7.64 pp |
| Transport % | 79.5% | 72.3% | -7.3 pp |
| Holding % | 5.0% | 18.8% | +13.7 pp |
| Shortage % | 6.1% | 0.5% | -5.6 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.79% ✓ |
| SKU_B | 99.07% ✓ |
| SKU_C | 98.11% ✓ |
| SKU_D | 99.07% ✓ |
| SKU_E | 100.00% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| R2 | 100.0% | 96.9% | 90.1% | 100.0% | 100.0% |
| R3 | 99.5% | 100.0% | 100.0% | 98.0% | 100.0% |

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

- Total cost is **10.1% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **7.64 percentage points** over baseline.
- Transport cost share decreased by **7.3 pp** (from 79.5% to 72.3%), reflecting effective vehicle consolidation.
- Holding cost share is **13.7 pp higher** (18.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 5.6 pp** (0.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 98.1% (SKU_C) to 100.0% (SKU_E) — a 1.9 pp range.

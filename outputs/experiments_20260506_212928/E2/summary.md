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
| Trials run | 80 |
| Feasible trials | 33 |
| Best trial # | 43 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 3346 |
| `S_W1__SKU_B` | 2226 |
| `S_W1__SKU_C` | 1565 |
| `S_W1__SKU_D` | 1730 |
| `S_W1__SKU_E` | 1207 |
| `S_W2__SKU_A` | 2415 |
| `S_W2__SKU_B` | 172 |
| `S_W2__SKU_C` | 1106 |
| `S_W2__SKU_D` | 2093 |
| `S_W2__SKU_E` | 704 |
| `S_R1__SKU_A` | 1233 |
| `S_R1__SKU_B` | 513 |
| `S_R1__SKU_C` | 874 |
| `S_R1__SKU_D` | 507 |
| `S_R1__SKU_E` | 294 |
| `S_R2__SKU_A` | 877 |
| `S_R2__SKU_B` | 316 |
| `S_R2__SKU_C` | 314 |
| `S_R2__SKU_D` | 271 |
| `S_R2__SKU_E` | 491 |
| `S_R3__SKU_A` | 1471 |
| `S_R3__SKU_B` | 740 |
| `S_R3__SKU_C` | 1970 |
| `S_R3__SKU_D` | 533 |
| `S_R3__SKU_E` | 1080 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **473,470** | 100% |
| Holding | 96,428 | 20.4% |
| Transport | 331,650 | 70.0% |
| Ordering | 38,832 | 8.2% |
| Shortage (backlog) | 6,560 | 1.4% |

**Overall fill rate: 97.73%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E2 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 473,470 | -13.6% increase |
| Fill rate | 91.59% | 97.73% | +6.14 pp |
| Transport % | 79.5% | 70.0% | -9.5 pp |
| Holding % | 5.0% | 20.4% | +15.3 pp |
| Shortage % | 6.1% | 1.4% | -4.7 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 100.00% ✓ |
| SKU_B | 92.77% ✓ |
| SKU_C | 99.40% ✓ |
| SKU_D | 93.27% ✓ |
| SKU_E | 100.00% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| R2 | 100.0% | 95.6% | 96.8% | 100.0% | 100.0% |
| R3 | 100.0% | 82.2% | 100.0% | 85.5% | 100.0% |

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

- Total cost is **13.6% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **6.14 percentage points** over baseline.
- Transport cost share decreased by **9.5 pp** (from 79.5% to 70.0%), reflecting effective vehicle consolidation.
- Holding cost share is **15.3 pp higher** (20.4% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.7 pp** (1.4% vs 6.1% in E0).
- Fill rate spread across SKUs: 92.8% (SKU_B) to 100.0% (SKU_A) — a 7.2 pp range.

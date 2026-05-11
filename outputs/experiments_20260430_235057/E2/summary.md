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
| Feasible trials | 35 |
| Best trial # | 58 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1876 |
| `S_W1__SKU_B` | 2043 |
| `S_W1__SKU_C` | 1405 |
| `S_W1__SKU_D` | 1638 |
| `S_W1__SKU_E` | 1082 |
| `S_W2__SKU_A` | 2203 |
| `S_W2__SKU_B` | 1494 |
| `S_W2__SKU_C` | 686 |
| `S_W2__SKU_D` | 2002 |
| `S_W2__SKU_E` | 1095 |
| `S_R1__SKU_A` | 1242 |
| `S_R1__SKU_B` | 574 |
| `S_R1__SKU_C` | 784 |
| `S_R1__SKU_D` | 487 |
| `S_R1__SKU_E` | 177 |
| `S_R2__SKU_A` | 643 |
| `S_R2__SKU_B` | 194 |
| `S_R2__SKU_C` | 344 |
| `S_R2__SKU_D` | 312 |
| `S_R2__SKU_E` | 187 |
| `S_R3__SKU_A` | 1386 |
| `S_R3__SKU_B` | 933 |
| `S_R3__SKU_C` | 1667 |
| `S_R3__SKU_D` | 539 |
| `S_R3__SKU_E` | 1058 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **470,742** | 100% |
| Holding | 84,905 | 18.0% |
| Transport | 331,650 | 70.5% |
| Ordering | 38,832 | 8.2% |
| Shortage (backlog) | 15,355 | 3.3% |

**Overall fill rate: 94.62%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E2 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 470,742 | -12.9% increase |
| Fill rate | 91.59% | 94.62% | +3.03 pp |
| Transport % | 79.5% | 70.5% | -9.1 pp |
| Holding % | 5.0% | 18.0% | +13.0 pp |
| Shortage % | 6.1% | 3.3% | -2.9 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.91% ✓ |
| SKU_B | 81.73% ✗ |
| SKU_C | 99.12% ✓ |
| SKU_D | 94.00% ✓ |
| SKU_E | 88.62% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 95.9% |
| R2 | 99.8% | 39.4% | 96.4% | 100.0% | 62.2% |
| R3 | 99.9% | 100.0% | 99.5% | 87.0% | 100.0% |

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

- Total cost is **12.9% higher** than E0 baseline — this experiment trades cost for service quality.
- Fill rate improved by **3.03 percentage points** over baseline.
- Transport cost share decreased by **9.1 pp** (from 79.5% to 70.5%), reflecting effective vehicle consolidation.
- Holding cost share is **13.0 pp higher** (18.0% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 2.9 pp** (3.3% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (81.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 81.7% (SKU_B) to 99.9% (SKU_A) — a 18.2 pp range.

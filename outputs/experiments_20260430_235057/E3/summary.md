# E3 — Joint Inventory + Transport Optimization (Main Result)

*Section 4.5 — Joint Optimization (Main Result)*

---

## Purpose

Simultaneously optimize both base-stock levels and dispatch thresholds. This is the core research contribution: demonstrating that joint optimization achieves cost savings that neither inventory-only nor transport-only optimization can achieve independently.

## Methodology

Optuna TPE sampler jointly searches the full parameter space: base-stock levels per (node, SKU) and dispatch thresholds per lane. Same fill constraint (≥ 92%) and penalty as E1b/E2. The optimizer can trade off higher holding cost (larger S) against lower transport cost (higher threshold) in a single search.

## Hypothesis

*Joint optimization will find configurations where slightly elevated inventory levels enable vehicle consolidation, reducing transport costs enough to more than offset the additional holding cost — yielding the lowest total cost while maintaining service level targets.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | joint |
| Trials run | 80 |
| Feasible trials | 39 |
| Best trial # | 62 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1639 |
| `S_W1__SKU_B` | 1022 |
| `S_W1__SKU_C` | 1172 |
| `S_W1__SKU_D` | 595 |
| `S_W1__SKU_E` | 1563 |
| `S_W2__SKU_A` | 3703 |
| `S_W2__SKU_B` | 769 |
| `S_W2__SKU_C` | 2005 |
| `S_W2__SKU_D` | 832 |
| `S_W2__SKU_E` | 1279 |
| `S_R1__SKU_A` | 929 |
| `S_R1__SKU_B` | 567 |
| `S_R1__SKU_C` | 1028 |
| `S_R1__SKU_D` | 504 |
| `S_R1__SKU_E` | 249 |
| `S_R2__SKU_A` | 1226 |
| `S_R2__SKU_B` | 781 |
| `S_R2__SKU_C` | 757 |
| `S_R2__SKU_D` | 442 |
| `S_R2__SKU_E` | 584 |
| `S_R3__SKU_A` | 1620 |
| `S_R3__SKU_B` | 653 |
| `S_R3__SKU_C` | 1607 |
| `S_R3__SKU_D` | 939 |
| `S_R3__SKU_E` | 979 |
| `D_Supplier_W1` | 0.7920524122295123 |
| `D_Supplier_W2` | 0.3609568704410574 |
| `D_W1_R1` | 0.6345156884849313 |
| `D_W1_R2` | 0.4696112413513688 |
| `D_W2_R3` | 0.8179755086241148 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **261,088** | 100% |
| Holding | 81,245 | 31.1% |
| Transport | 137,552 | 52.7% |
| Ordering | 38,832 | 14.9% |
| Shortage (backlog) | 3,459 | 1.3% |

**Overall fill rate: 98.72%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E3 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 261,088 | +37.4% saving |
| Fill rate | 91.59% | 98.72% | +7.13 pp |
| Transport % | 79.5% | 52.7% | -26.9 pp |
| Holding % | 5.0% | 31.1% | +26.1 pp |
| Shortage % | 6.1% | 1.3% | -4.8 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.66% ✓ |
| SKU_B | 99.93% ✓ |
| SKU_C | 99.78% ✓ |
| SKU_D | 96.65% ✓ |
| SKU_E | 98.30% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.2% | 99.8% | 100.0% | 100.0% | 93.5% |
| R2 | 100.0% | 100.0% | 98.8% | 88.4% | 100.0% |
| R3 | 97.6% | 100.0% | 100.0% | 98.5% | 100.0% |

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

- **37.4% total cost reduction** vs E0 baseline (from 416,952 to 261,088).
- Fill rate improved by **7.13 percentage points** over baseline.
- Transport cost share decreased by **26.9 pp** (from 79.5% to 52.7%), reflecting effective vehicle consolidation.
- Holding cost share is **26.1 pp higher** (31.1% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.8 pp** (1.3% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.7% (SKU_D) to 99.9% (SKU_B) — a 3.3 pp range.

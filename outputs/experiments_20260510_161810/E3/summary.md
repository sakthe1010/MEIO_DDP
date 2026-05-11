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
| Trials run | 100 |
| Feasible trials | 44 |
| Best trial # | 27 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1197 |
| `S_W1__SKU_B` | 1142 |
| `S_W1__SKU_C` | 1371 |
| `S_W1__SKU_D` | 634 |
| `S_W1__SKU_E` | 830 |
| `S_W2__SKU_A` | 2427 |
| `S_W2__SKU_B` | 1010 |
| `S_W2__SKU_C` | 2330 |
| `S_W2__SKU_D` | 831 |
| `S_W2__SKU_E` | 900 |
| `S_R1__SKU_A` | 1285 |
| `S_R1__SKU_B` | 585 |
| `S_R1__SKU_C` | 822 |
| `S_R1__SKU_D` | 377 |
| `S_R1__SKU_E` | 247 |
| `S_R2__SKU_A` | 1210 |
| `S_R2__SKU_B` | 497 |
| `S_R2__SKU_C` | 765 |
| `S_R2__SKU_D` | 384 |
| `S_R2__SKU_E` | 615 |
| `S_R3__SKU_A` | 1907 |
| `S_R3__SKU_B` | 368 |
| `S_R3__SKU_C` | 1579 |
| `S_R3__SKU_D` | 1061 |
| `S_R3__SKU_E` | 855 |
| `D_Supplier_W1` | 0.7998707929851543 |
| `D_Supplier_W2` | 0.7866158970742931 |
| `D_W1_R1` | 0.23056641585772286 |
| `D_W1_R2` | 0.22703317637190595 |
| `D_W2_R3` | 0.3891917623408493 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **406,500** | 100% |
| Holding | 68,617 | 16.9% |
| Transport | 285,072 | 70.1% |
| Ordering | 38,832 | 9.6% |
| Shortage (backlog) | 13,979 | 3.4% |

**Overall fill rate: 96.29%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E3 | Change |
|-----|------------:|--------:|-------:|
| Total cost | 748,602 | 406,500 | +45.7% saving |
| Fill rate | 91.59% | 96.29% | +4.71 pp |
| Transport % | 88.6% | 70.1% | -18.5 pp |
| Holding % | 2.8% | 16.9% | +14.1 pp |
| Shortage % | 3.4% | 3.4% | +0.0 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.82% ✓ |
| SKU_B | 84.24% ✗ |
| SKU_C | 99.70% ✓ |
| SKU_D | 95.16% ✓ |
| SKU_E | 98.74% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 99.9% | 99.2% | 96.6% | 95.2% |
| R2 | 94.8% | 99.2% | 100.0% | 83.4% | 100.0% |
| R3 | 100.0% | 53.4% | 100.0% | 100.0% | 100.0% |

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

- **45.7% total cost reduction** vs E0 baseline (from 748,602 to 406,500).
- Fill rate improved by **4.71 percentage points** over baseline.
- Transport cost share decreased by **18.5 pp** (from 88.6% to 70.1%), reflecting effective vehicle consolidation.
- Holding cost share is **14.1 pp higher** (16.9% vs 2.8% in E0), reflecting elevated base-stock levels to enable consolidation.
- **SKU_B** has the lowest fill rate (84.2%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 84.2% (SKU_B) to 99.7% (SKU_C) — a 15.5 pp range.

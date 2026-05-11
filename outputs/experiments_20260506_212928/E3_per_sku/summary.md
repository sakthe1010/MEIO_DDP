# E3_per_sku — Joint Optimization with per-SKU fill constraint

*Section 4.5b — Per-SKU Joint Optimization*

---

## Purpose

Re-run E3 but apply the fill rate constraint per-SKU rather than aggregated. Every SKU must individually meet the target. This eliminates the loophole where popular SKUs over-serve and compensate for under-served ones.

## Methodology

Same Optuna joint search as E3, but the objective penalty is Σ_sku max(0, target − fill_sku) × PENALTY_PER_PCT. Best feasible trial is the one where every SKU's fill rate meets the target.

## Hypothesis

*Per-SKU constraint will raise total cost slightly compared to E3 (the weakly-served SKUs need more inventory) but will eliminate the SKU-level service-level shortfall observed in E3.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | joint |
| Trials run | 80 |
| Feasible trials | 21 |
| Best trial # | 78 |
| Min fill rate target | 92% per-SKU |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1903 |
| `S_W1__SKU_B` | 1382 |
| `S_W1__SKU_C` | 2151 |
| `S_W1__SKU_D` | 870 |
| `S_W1__SKU_E` | 1809 |
| `S_W2__SKU_A` | 2507 |
| `S_W2__SKU_B` | 922 |
| `S_W2__SKU_C` | 566 |
| `S_W2__SKU_D` | 1931 |
| `S_W2__SKU_E` | 437 |
| `S_R1__SKU_A` | 1233 |
| `S_R1__SKU_B` | 436 |
| `S_R1__SKU_C` | 996 |
| `S_R1__SKU_D` | 607 |
| `S_R1__SKU_E` | 294 |
| `S_R2__SKU_A` | 1389 |
| `S_R2__SKU_B` | 548 |
| `S_R2__SKU_C` | 386 |
| `S_R2__SKU_D` | 400 |
| `S_R2__SKU_E` | 319 |
| `S_R3__SKU_A` | 1895 |
| `S_R3__SKU_B` | 943 |
| `S_R3__SKU_C` | 1996 |
| `S_R3__SKU_D` | 942 |
| `S_R3__SKU_E` | 1337 |
| `D_Supplier_W1` | 0.7182678621716968 |
| `D_Supplier_W2` | 0.7644967748111341 |
| `D_W1_R1` | 0.32504285865506566 |
| `D_W1_R2` | 0.44207053448802275 |
| `D_W2_R3` | 0.563658051946556 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **267,706** | 100% |
| Holding | 87,923 | 32.8% |
| Transport | 139,616 | 52.2% |
| Ordering | 38,832 | 14.5% |
| Shortage (backlog) | 1,336 | 0.5% |

**Overall fill rate: 99.40%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E3_per_sku | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 267,706 | +35.8% saving |
| Fill rate | 91.59% | 99.40% | +7.82 pp |
| Transport % | 79.5% | 52.2% | -27.4 pp |
| Holding % | 5.0% | 32.8% | +27.8 pp |
| Shortage % | 6.1% | 0.5% | -5.6 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.98% ✓ |
| SKU_B | 99.49% ✓ |
| SKU_C | 98.56% ✓ |
| SKU_D | 99.91% ✓ |
| SKU_E | 98.62% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 98.7% | 100.0% | 100.0% | 99.8% |
| R2 | 100.0% | 99.9% | 93.5% | 100.0% | 95.2% |
| R3 | 100.0% | 100.0% | 99.5% | 99.8% | 100.0% |

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

- **35.8% total cost reduction** vs E0 baseline (from 416,952 to 267,706).
- Fill rate improved by **7.82 percentage points** over baseline.
- Transport cost share decreased by **27.4 pp** (from 79.5% to 52.2%), reflecting effective vehicle consolidation.
- Holding cost share is **27.8 pp higher** (32.8% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 5.6 pp** (0.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 98.6% (SKU_C) to 100.0% (SKU_A) — a 1.4 pp range.

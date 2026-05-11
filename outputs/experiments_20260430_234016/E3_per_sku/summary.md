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
| Trials run | 100 |
| Feasible trials | 29 |
| Best trial # | 95 |
| Min fill rate target | 92% per-SKU |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1886 |
| `S_W1__SKU_B` | 806 |
| `S_W1__SKU_C` | 1865 |
| `S_W1__SKU_D` | 545 |
| `S_W1__SKU_E` | 1792 |
| `S_W2__SKU_A` | 2131 |
| `S_W2__SKU_B` | 339 |
| `S_W2__SKU_C` | 818 |
| `S_W2__SKU_D` | 1653 |
| `S_W2__SKU_E` | 474 |
| `S_R1__SKU_A` | 967 |
| `S_R1__SKU_B` | 440 |
| `S_R1__SKU_C` | 808 |
| `S_R1__SKU_D` | 649 |
| `S_R1__SKU_E` | 354 |
| `S_R2__SKU_A` | 712 |
| `S_R2__SKU_B` | 805 |
| `S_R2__SKU_C` | 343 |
| `S_R2__SKU_D` | 504 |
| `S_R2__SKU_E` | 258 |
| `S_R3__SKU_A` | 2626 |
| `S_R3__SKU_B` | 872 |
| `S_R3__SKU_C` | 1785 |
| `S_R3__SKU_D` | 953 |
| `S_R3__SKU_E` | 1327 |
| `D_Supplier_W1` | 0.5404342521852896 |
| `D_Supplier_W2` | 0.897098655362706 |
| `D_W1_R1` | 0.30746244640015297 |
| `D_W1_R2` | 0.38332117070223476 |
| `D_W2_R3` | 0.5613597315393015 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **258,085** | 100% |
| Holding | 73,498 | 28.5% |
| Transport | 139,260 | 54.0% |
| Ordering | 38,832 | 15.0% |
| Shortage (backlog) | 6,495 | 2.5% |

**Overall fill rate: 97.41%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E3_per_sku | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 258,085 | +38.1% saving |
| Fill rate | 91.59% | 97.41% | +5.82 pp |
| Transport % | 79.5% | 54.0% | -25.6 pp |
| Holding % | 5.0% | 28.5% | +23.5 pp |
| Shortage % | 6.1% | 2.5% | -3.6 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.51% ✓ |
| SKU_B | 98.61% ✓ |
| SKU_C | 96.40% ✓ |
| SKU_D | 97.78% ✓ |
| SKU_E | 92.05% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 99.6% | 96.8% | 99.1% | 100.0% | 99.9% |
| R2 | 98.4% | 99.5% | 83.4% | 90.6% | 71.0% |
| R3 | 100.0% | 99.8% | 99.8% | 99.8% | 100.0% |

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

- **38.1% total cost reduction** vs E0 baseline (from 416,952 to 258,085).
- Fill rate improved by **5.82 percentage points** over baseline.
- Transport cost share decreased by **25.6 pp** (from 79.5% to 54.0%), reflecting effective vehicle consolidation.
- Holding cost share is **23.5 pp higher** (28.5% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 3.6 pp** (2.5% vs 6.1% in E0).
- Fill rate spread across SKUs: 92.1% (SKU_E) to 99.5% (SKU_A) — a 7.5 pp range.

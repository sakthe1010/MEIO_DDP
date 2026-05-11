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
| Trials run | 40 |
| Feasible trials | 6 |
| Best trial # | 23 |
| Min fill rate target | 92% per-SKU |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 1876 |
| `S_W1__SKU_B` | 1910 |
| `S_W1__SKU_C` | 2408 |
| `S_W1__SKU_D` | 941 |
| `S_W1__SKU_E` | 1189 |
| `S_W2__SKU_A` | 2128 |
| `S_W2__SKU_B` | 1050 |
| `S_W2__SKU_C` | 422 |
| `S_W2__SKU_D` | 1923 |
| `S_W2__SKU_E` | 915 |
| `S_R1__SKU_A` | 1481 |
| `S_R1__SKU_B` | 540 |
| `S_R1__SKU_C` | 1342 |
| `S_R1__SKU_D` | 572 |
| `S_R1__SKU_E` | 355 |
| `S_R2__SKU_A` | 1378 |
| `S_R2__SKU_B` | 506 |
| `S_R2__SKU_C` | 443 |
| `S_R2__SKU_D` | 417 |
| `S_R2__SKU_E` | 410 |
| `S_R3__SKU_A` | 1653 |
| `S_R3__SKU_B` | 1004 |
| `S_R3__SKU_C` | 1811 |
| `S_R3__SKU_D` | 830 |
| `S_R3__SKU_E` | 1432 |
| `D_Supplier_W1` | 0.8965662630584036 |
| `D_Supplier_W2` | 0.7831660504952584 |
| `D_W1_R1` | 0.26097308627980736 |
| `D_W1_R2` | 0.4811425099412361 |
| `D_W2_R3` | 0.37165825689454735 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **277,693** | 100% |
| Holding | 94,408 | 34.0% |
| Transport | 141,129 | 50.8% |
| Ordering | 38,832 | 14.0% |
| Shortage (backlog) | 3,323 | 1.2% |

**Overall fill rate: 98.83%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E3_per_sku | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 277,693 | +33.4% saving |
| Fill rate | 91.59% | 98.83% | +7.24 pp |
| Transport % | 79.5% | 50.8% | -28.7 pp |
| Holding % | 5.0% | 34.0% | +29.0 pp |
| Shortage % | 6.1% | 1.2% | -4.9 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 99.19% ✓ |
| SKU_B | 99.89% ✓ |
| SKU_C | 96.33% ✓ |
| SKU_D | 99.51% ✓ |
| SKU_E | 100.00% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 100.0% | 100.0% | 100.0% |
| R2 | 100.0% | 99.6% | 99.0% | 100.0% | 100.0% |
| R3 | 98.2% | 100.0% | 91.8% | 98.9% | 100.0% |

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

- **33.4% total cost reduction** vs E0 baseline (from 416,952 to 277,693).
- Fill rate improved by **7.24 percentage points** over baseline.
- Transport cost share decreased by **28.7 pp** (from 79.5% to 50.8%), reflecting effective vehicle consolidation.
- Holding cost share is **29.0 pp higher** (34.0% vs 5.0% in E0), reflecting elevated base-stock levels to enable consolidation.
- Shortage cost share **reduced by 4.9 pp** (1.2% vs 6.1% in E0).
- Fill rate spread across SKUs: 96.3% (SKU_C) to 100.0% (SKU_E) — a 3.7 pp range.

# E1b — Transport-Only Optimization

*Section 4.3 — Transport-Only Optimization*

---

## Purpose

Optimize dispatch thresholds per lane using Optuna (TPE sampler) while keeping inventory base-stock levels fixed at their analytical values. This answers: how much can transport cost be reduced through smart threshold selection alone?

## Methodology

Optuna TPE sampler searches dispatch thresholds in [0.0, 0.9] per lane. Inventory levels are held fixed at E0 analytical values. Soft constraint: fill rate ≥ 92% (penalty of 1M per 1% shortfall). Best feasible trial (fill ≥ 92%) is selected; falls back to best overall if no feasible trial found.

## Hypothesis

*Per-lane threshold optimization will outperform the fixed 25% threshold of E1a while maintaining fill rates, but will be limited by the fixed inventory levels which were not designed for consolidation.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | transport |
| Trials run | 100 |
| Feasible trials | 0 |
| Best trial # | 99 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `D_Supplier_W1` | 0.18246871412227147 |
| `D_Supplier_W2` | 0.10350131365441567 |
| `D_W1_R1` | 0.08798911485639409 |
| `D_W1_R2` | 0.0799872793267635 |
| `D_W2_R3` | 0.02214105346018791 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **371,847** | 100% |
| Holding | 19,341 | 5.2% |
| Transport | 280,348 | 75.4% |
| Ordering | 38,832 | 10.4% |
| Shortage (backlog) | 33,325 | 9.0% |

**Overall fill rate: 88.68%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E1b | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 371,847 | +10.8% saving |
| Fill rate | 91.59% | 88.68% | -2.91 pp |
| Transport % | 79.5% | 75.4% | -4.1 pp |
| Holding % | 5.0% | 5.2% | +0.2 pp |
| Shortage % | 6.1% | 9.0% | +2.8 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 89.60% ✗ |
| SKU_B | 83.51% ✗ |
| SKU_C | 84.59% ✗ |
| SKU_D | 93.13% ✓ |
| SKU_E | 93.16% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 92.1% | 90.5% | 89.2% | 92.5% | 93.6% |
| R2 | 85.5% | 75.9% | 81.6% | 90.1% | 86.2% |
| R3 | 89.8% | 82.7% | 81.7% | 95.1% | 97.0% |

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

- **10.8% total cost reduction** vs E0 baseline (from 416,952 to 371,847).
- Fill rate **dropped 2.91 pp** vs baseline (88.68%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **4.1 pp** (from 79.5% to 75.4%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 2.8 pp** (9.0% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (83.5%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.5% (SKU_B) to 93.2% (SKU_E) — a 9.6 pp range.

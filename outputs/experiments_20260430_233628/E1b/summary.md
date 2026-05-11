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
| Trials run | 40 |
| Feasible trials | 0 |
| Best trial # | 15 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `D_Supplier_W1` | 0.196537118722967 |
| `D_Supplier_W2` | 0.3836552006281504 |
| `D_W1_R1` | 0.13937397837896587 |
| `D_W1_R2` | 0.22945411727994855 |
| `D_W2_R3` | 0.10052146257503494 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **298,901** | 100% |
| Holding | 15,125 | 5.1% |
| Transport | 178,061 | 59.6% |
| Ordering | 38,832 | 13.0% |
| Shortage (backlog) | 66,882 | 22.4% |

**Overall fill rate: 79.10%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E1b | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 298,901 | +28.3% saving |
| Fill rate | 91.59% | 79.10% | -12.49 pp |
| Transport % | 79.5% | 59.6% | -20.0 pp |
| Holding % | 5.0% | 5.1% | +0.0 pp |
| Shortage % | 6.1% | 22.4% | +16.3 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 79.60% ✗ |
| SKU_B | 75.71% ✗ |
| SKU_C | 78.57% ✗ |
| SKU_D | 82.34% ✗ |
| SKU_E | 78.44% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 88.4% | 87.3% | 87.1% | 89.2% | 90.1% |
| R2 | 74.7% | 69.6% | 73.7% | 79.0% | 76.6% |
| R3 | 75.3% | 68.5% | 73.0% | 79.4% | 73.0% |

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

- **28.3% total cost reduction** vs E0 baseline (from 416,952 to 298,901).
- Fill rate **dropped 12.49 pp** vs baseline (79.10%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **20.0 pp** (from 79.5% to 59.6%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 16.3 pp** (22.4% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (75.7%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 75.7% (SKU_B) to 82.3% (SKU_D) — a 6.6 pp range.

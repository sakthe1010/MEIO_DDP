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
| Trials run | 80 |
| Feasible trials | 0 |
| Best trial # | 75 |
| Min fill rate target | 92% |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `D_Supplier_W1` | 0.12633090322411974 |
| `D_Supplier_W2` | 0.13541707909978973 |
| `D_W1_R1` | 0.014054157824322332 |
| `D_W1_R2` | 0.23996017644875087 |
| `D_W2_R3` | 0.04099761458465326 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **370,370** | 100% |
| Holding | 19,247 | 5.2% |
| Transport | 275,103 | 74.3% |
| Ordering | 38,832 | 10.5% |
| Shortage (backlog) | 37,188 | 10.0% |

**Overall fill rate: 87.44%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E1b | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 370,370 | +11.2% saving |
| Fill rate | 91.59% | 87.44% | -4.14 pp |
| Transport % | 79.5% | 74.3% | -5.3 pp |
| Holding % | 5.0% | 5.2% | +0.2 pp |
| Shortage % | 6.1% | 10.0% | +3.9 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 88.10% ✗ |
| SKU_B | 82.83% ✗ |
| SKU_C | 84.62% ✗ |
| SKU_D | 91.30% ✗ |
| SKU_E | 90.69% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 96.3% | 94.3% | 93.2% | 96.2% | 96.8% |
| R2 | 74.2% | 69.8% | 74.4% | 78.9% | 77.2% |
| R3 | 88.9% | 82.0% | 81.3% | 94.2% | 95.2% |

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

- **11.2% total cost reduction** vs E0 baseline (from 416,952 to 370,370).
- Fill rate **dropped 4.14 pp** vs baseline (87.44%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **5.3 pp** (from 79.5% to 74.3%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 3.9 pp** (10.0% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (82.8%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 82.8% (SKU_B) to 91.3% (SKU_D) — a 8.5 pp range.

# E1a — Fixed Financial Dispatch Threshold (25%)

*Section 4.2 — Isolated Transport Consolidation*

---

## Purpose

Assess the cost impact of imposing a minimum vehicle utilization threshold of 25% on all transport lanes, using the same inventory policy as E0. This isolates the effect of transport consolidation alone, without re-optimizing inventory to compensate.

## Methodology

All edges have min_dispatch_utilization set to 0.25. Goods accumulate in a pending-dispatch buffer until 25% vehicle fill is reached, or until the max_dispatch_wait timeout (3 days) forces a dispatch. Inventory policy is unchanged from E0.

## Hypothesis

*Transport consolidation will reduce transport cost significantly but increase shortage cost because delayed shipments reduce service levels. This demonstrates that naive consolidation without inventory adjustment is counter-productive.*

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `D_Supplier_W1` | 0.25 |
| `D_Supplier_W2` | 0.25 |
| `D_W1_R1` | 0.25 |
| `D_W1_R2` | 0.25 |
| `D_W2_R3` | 0.25 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **282,935** | 100% |
| Holding | 13,623 | 4.8% |
| Transport | 156,753 | 55.4% |
| Ordering | 38,832 | 13.7% |
| Shortage (backlog) | 73,727 | 26.1% |

**Overall fill rate: 75.09%**

### Comparison to E0 Baseline

| KPI | E0 Baseline | E1a | Change |
|-----|------------:|--------:|-------:|
| Total cost | 416,952 | 282,935 | +32.1% saving |
| Fill rate | 91.59% | 75.09% | -16.50 pp |
| Transport % | 79.5% | 55.4% | -24.1 pp |
| Holding % | 5.0% | 4.8% | -0.2 pp |
| Shortage % | 6.1% | 26.1% | +19.9 pp |

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 74.50% ✗ |
| SKU_B | 73.00% ✗ |
| SKU_C | 76.40% ✗ |
| SKU_D | 77.71% ✗ |
| SKU_E | 73.55% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 76.4% | 80.2% | 81.2% | 78.0% | 75.2% |
| R2 | 72.0% | 68.5% | 72.5% | 76.8% | 74.5% |
| R3 | 74.3% | 69.1% | 73.8% | 78.0% | 72.1% |

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

- **32.1% total cost reduction** vs E0 baseline (from 416,952 to 282,935).
- Fill rate **dropped 16.50 pp** vs baseline (75.09%). Below 92% target — the consolidation constraint is harming service.
- Transport cost share decreased by **24.1 pp** (from 79.5% to 55.4%), reflecting effective vehicle consolidation.
- Shortage cost share **increased by 19.9 pp** (26.1% vs 6.1% in E0).
- **SKU_B** has the lowest fill rate (73.0%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 73.0% (SKU_B) to 77.7% (SKU_D) — a 4.7 pp range.

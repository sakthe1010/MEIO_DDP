# E5_E3params — Disruption — E3 params

*Section 4.7 — Disruption Robustness*

---

## Purpose

Inject a supply-side disruption at warehouse W1 and compare how E0 (analytical) and E3 (joint-optimized) parameters cope. Measures cost overhead, service degradation, and recovery time — the stress test the analytical baseline can't anticipate.

## Methodology

Run the same 1n3_5sku scenario with a 14-day W1 outage centred at 60% through the post-warmup horizon. Two configurations: E0 params and E3 params. Time-to-recover = days for fill rate to return within 1pp of the pre-disruption value.

## Hypothesis

*E3's elevated buffer stocks (driven by transport consolidation) will absorb the shock better, recovering faster than E0 even though the disruption was not in the optimization objective.*

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
| `disruption` | {'node': 'W1', 'start': 231, 'end': 245} |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **2,222,086** | 100% |
| Holding | 229,746 | 10.3% |
| Transport | 142,947 | 6.4% |
| Ordering | 32,438 | 1.5% |
| Shortage (backlog) | 1,816,955 | 81.8% |

**Overall fill rate: 81.86%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 81.34% ✗ |
| SKU_B | 81.80% ✗ |
| SKU_C | 84.16% ✗ |
| SKU_D | 79.39% ✗ |
| SKU_E | 82.44% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 68.2% | 72.3% | 72.5% | 67.9% | 67.7% |
| R2 | 70.0% | 73.3% | 72.6% | 56.6% | 66.6% |
| R3 | 97.3% | 100.0% | 100.0% | 98.3% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 60.424 ⚠ |
| R1 | SKU_B | 29.017 ⚠ |
| R1 | SKU_C | 26.479 ⚠ |
| R1 | SKU_D | 55.059 ⚠ |
| R1 | SKU_E | 57.654 ⚠ |
| R2 | SKU_A | 82.759 ⚠ |
| R2 | SKU_B | 22.082 ⚠ |
| R2 | SKU_C | 20.727 ⚠ |
| R2 | SKU_D | 58.004 ⚠ |
| R2 | SKU_E | 57.498 ⚠ |
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
| W1 | SKU_A | 12.646 ⚠ |
| W1 | SKU_B | 12.285 ⚠ |
| W1 | SKU_C | 12.533 ⚠ |
| W1 | SKU_D | 12.761 ⚠ |
| W1 | SKU_E | 12.486 ⚠ |
| W2 | SKU_A | 0.998 |
| W2 | SKU_B | 0.998 |
| W2 | SKU_C | 1.000 |
| W2 | SKU_D | 1.002 |
| W2 | SKU_E | 1.000 |

## Key Observations for Report

- Baseline total cost is **2,222,086**, dominated by transport (6.4%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **81.86%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 10.3% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_D** has the lowest fill rate (79.4%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 79.4% (SKU_D) to 84.2% (SKU_C) — a 4.8 pp range.

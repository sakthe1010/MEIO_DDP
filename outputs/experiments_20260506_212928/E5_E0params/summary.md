# E5_E0params — Disruption — E0 params

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
| `S_W1__SKU_A` | 1766 |
| `S_W1__SKU_B` | 943 |
| `S_W1__SKU_C` | 1245 |
| `S_W1__SKU_D` | 805 |
| `S_W1__SKU_E` | 668 |
| `S_W2__SKU_A` | 1610 |
| `S_W2__SKU_B` | 535 |
| `S_W2__SKU_C` | 1069 |
| `S_W2__SKU_D` | 813 |
| `S_W2__SKU_E` | 672 |
| `S_R1__SKU_A` | 573 |
| `S_R1__SKU_B` | 287 |
| `S_R1__SKU_C` | 459 |
| `S_R1__SKU_D` | 253 |
| `S_R1__SKU_E` | 181 |
| `S_R2__SKU_A` | 482 |
| `S_R2__SKU_B` | 297 |
| `S_R2__SKU_C` | 289 |
| `S_R2__SKU_D` | 239 |
| `S_R2__SKU_E` | 237 |
| `S_R3__SKU_A` | 1178 |
| `S_R3__SKU_B` | 393 |
| `S_R3__SKU_C` | 791 |
| `S_R3__SKU_D` | 596 |
| `S_R3__SKU_E` | 491 |
| `disruption` | {'node': 'W1', 'start': 231, 'end': 245} |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **2,577,516** | 100% |
| Holding | 178,211 | 6.9% |
| Transport | 297,246 | 11.5% |
| Ordering | 32,438 | 1.3% |
| Shortage (backlog) | 2,069,621 | 80.3% |

**Overall fill rate: 73.83%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 75.27% ✗ |
| SKU_B | 66.57% ✗ |
| SKU_C | 70.10% ✗ |
| SKU_D | 77.74% ✗ |
| SKU_E | 79.34% ✗ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 65.1% | 64.9% | 63.6% | 63.4% | 63.7% |
| R2 | 61.8% | 50.8% | 57.0% | 62.1% | 64.2% |
| R3 | 90.0% | 82.7% | 81.9% | 95.1% | 97.0% |

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

- Baseline total cost is **2,577,516**, dominated by transport (11.5%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **73.83%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 6.9% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (66.6%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 66.6% (SKU_B) to 79.3% (SKU_E) — a 12.8 pp range.

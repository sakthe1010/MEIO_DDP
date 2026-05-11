# E7_sigma_10 — Forecast σ=10%

*Section 4.9 — Forecast Uncertainty*

---

## Purpose

Replace the perfect-information assumption with noisy forecasts and measure how cost, fill rate, and bullwhip degrade as forecast error grows.

## Methodology

Wrap the demand series with a noisy-oracle: forecast(t+L) = true(t+L) × (1 + N(0, σ_f)). Run E3 params with σ_f ∈ {0%, 5%, 10%, 20%, 30%}. Policies consume the forecast for sizing decisions; the simulator still receives the true demand.

## Hypothesis

*Cost and bullwhip rise monotonically with σ_f; fill rate drops because under-forecasting causes stock-outs. This quantifies the value of forecast accuracy.*

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
| `forecast_sigma` | 0.1 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **272,812** | 100% |
| Holding | 84,111 | 30.8% |
| Transport | 138,578 | 50.8% |
| Ordering | 38,832 | 14.2% |
| Shortage (backlog) | 11,291 | 4.1% |

**Overall fill rate: 96.71%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 96.36% ✓ |
| SKU_B | 99.86% ✓ |
| SKU_C | 99.75% ✓ |
| SKU_D | 89.96% ✗ |
| SKU_E | 97.35% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 91.4% | 99.6% | 100.0% | 99.2% | 89.9% |
| R2 | 100.0% | 100.0% | 98.7% | 58.3% | 100.0% |
| R3 | 98.3% | 100.0% | 100.0% | 99.4% | 100.0% |

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

- Baseline total cost is **272,812**, dominated by transport (50.8%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.71%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 30.8% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_D** has the lowest fill rate (90.0%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 90.0% (SKU_D) to 99.9% (SKU_B) — a 9.9 pp range.

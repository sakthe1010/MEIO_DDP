# E7_sigma_05 — Forecast σ=5%

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
| `forecast_sigma` | 0.05 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **265,638** | 100% |
| Holding | 82,955 | 31.2% |
| Transport | 137,889 | 51.9% |
| Ordering | 38,832 | 14.6% |
| Shortage (backlog) | 5,962 | 2.2% |

**Overall fill rate: 98.08%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 98.33% ✓ |
| SKU_B | 99.90% ✓ |
| SKU_C | 99.76% ✓ |
| SKU_D | 93.85% ✓ |
| SKU_E | 97.86% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 98.0% | 99.7% | 100.0% | 99.9% | 91.8% |
| R2 | 100.0% | 100.0% | 98.7% | 76.5% | 100.0% |
| R3 | 97.7% | 100.0% | 100.0% | 98.4% | 100.0% |

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

- Baseline total cost is **265,638**, dominated by transport (51.9%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **98.08%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 31.2% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- Fill rate spread across SKUs: 93.9% (SKU_D) to 99.9% (SKU_B) — a 6.0 pp range.

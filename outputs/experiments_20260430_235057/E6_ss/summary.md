# E6_ss — Policy = ss

*Section 4.8 — Policy Comparison*

---

## Purpose

Compare four inventory policies — base_stock, ss, periodic_review, echelon_stock — on the same scenario after individual Optuna tuning. Tests the core thesis claim that network-wide coordination (echelon) beats local policies.

## Methodology

Each policy gets its own 100-trial Optuna search over its native parameter space (mode=inventory, dispatch fixed at 0.0, fill ≥ 92%). Headline metrics: total cost, fill rate, holding/transport mix, bullwhip per echelon.

## Hypothesis

*echelon_stock ≤ base_stock ≈ ss < periodic_review on cost. Echelon wins because warehouses see downstream pipeline; periodic loses to review delay.*

## Optimization Details

| Parameter | Value |
|-----------|-------|
| Mode | — |
| Trials run | 80 |
| Feasible trials | 18 |
| Best trial # | 75 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 2628 |
| `S_W1__SKU_B` | 2057 |
| `S_W1__SKU_C` | 3089 |
| `S_W1__SKU_D` | 804 |
| `S_W1__SKU_E` | 1842 |
| `S_W2__SKU_A` | 3244 |
| `S_W2__SKU_B` | 1672 |
| `S_W2__SKU_C` | 2904 |
| `S_W2__SKU_D` | 2529 |
| `S_W2__SKU_E` | 1433 |
| `S_R1__SKU_A` | 951 |
| `S_R1__SKU_B` | 781 |
| `S_R1__SKU_C` | 446 |
| `S_R1__SKU_D` | 763 |
| `S_R1__SKU_E` | 169 |
| `S_R2__SKU_A` | 1420 |
| `S_R2__SKU_B` | 458 |
| `S_R2__SKU_C` | 813 |
| `S_R2__SKU_D` | 402 |
| `S_R2__SKU_E` | 737 |
| `S_R3__SKU_A` | 3157 |
| `S_R3__SKU_B` | 397 |
| `S_R3__SKU_C` | 1737 |
| `S_R3__SKU_D` | 2308 |
| `S_R3__SKU_E` | 1080 |
| `alpha_W1__SKU_A` | 0.8515214870769079 |
| `alpha_W1__SKU_B` | 0.4611092070516204 |
| `alpha_W1__SKU_C` | 0.9385999893649419 |
| `alpha_W1__SKU_D` | 0.9269359333544619 |
| `alpha_W1__SKU_E` | 0.5445158338525877 |
| `alpha_W2__SKU_A` | 0.45274713806678185 |
| `alpha_W2__SKU_B` | 0.3002829393570563 |
| `alpha_W2__SKU_C` | 0.32643545143850616 |
| `alpha_W2__SKU_D` | 0.5319710351493737 |
| `alpha_W2__SKU_E` | 0.3385582065563904 |
| `alpha_R1__SKU_A` | 0.30135469121552816 |
| `alpha_R1__SKU_B` | 0.7870718007535984 |
| `alpha_R1__SKU_C` | 0.42958900180497367 |
| `alpha_R1__SKU_D` | 0.6279990011461566 |
| `alpha_R1__SKU_E` | 0.5741273836405104 |
| `alpha_R2__SKU_A` | 0.4783656545538503 |
| `alpha_R2__SKU_B` | 0.4199435418713601 |
| `alpha_R2__SKU_C` | 0.6522014306763115 |
| `alpha_R2__SKU_D` | 0.6192906352840314 |
| `alpha_R2__SKU_E` | 0.3448470111609514 |
| `alpha_R3__SKU_A` | 0.49739411120572125 |
| `alpha_R3__SKU_B` | 0.598493315856808 |
| `alpha_R3__SKU_C` | 0.43671506477590105 |
| `alpha_R3__SKU_D` | 0.680089971547276 |
| `alpha_R3__SKU_E` | 0.6716032997688341 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **369,257** | 100% |
| Holding | 118,664 | 32.1% |
| Transport | 218,881 | 59.3% |
| Ordering | 10,184 | 2.8% |
| Shortage (backlog) | 21,527 | 5.8% |

**Overall fill rate: 92.03%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 95.19% ✓ |
| SKU_B | 83.94% ✗ |
| SKU_C | 86.56% ✗ |
| SKU_D | 99.50% ✓ |
| SKU_E | 92.65% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 85.8% | 100.0% | 66.3% | 100.0% | 71.9% |
| R2 | 100.0% | 86.8% | 100.0% | 97.8% | 100.0% |
| R3 | 100.0% | 63.6% | 99.0% | 100.0% | 100.0% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 57.642 ⚠ |
| R1 | SKU_B | 14.403 ⚠ |
| R1 | SKU_C | 13.271 ⚠ |
| R1 | SKU_D | 49.052 ⚠ |
| R1 | SKU_E | 14.423 ⚠ |
| R2 | SKU_A | 141.642 ⚠ |
| R2 | SKU_B | 39.386 ⚠ |
| R2 | SKU_C | 34.852 ⚠ |
| R2 | SKU_D | 42.225 ⚠ |
| R2 | SKU_E | 158.729 ⚠ |
| R3 | SKU_A | 119.793 ⚠ |
| R3 | SKU_B | 22.148 ⚠ |
| R3 | SKU_C | 52.066 ⚠ |
| R3 | SKU_D | 103.026 ⚠ |
| R3 | SKU_E | 74.303 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 1.014 |
| W1 | SKU_B | 6.132 ⚠ |
| W1 | SKU_C | 0.988 |
| W1 | SKU_D | 1.000 |
| W1 | SKU_E | 3.536 ⚠ |
| W2 | SKU_A | 1.946 |
| W2 | SKU_B | 9.234 ⚠ |
| W2 | SKU_C | 2.073 ⚠ |
| W2 | SKU_D | 2.141 ⚠ |
| W2 | SKU_E | 3.469 ⚠ |

## Key Observations for Report

- Baseline total cost is **369,257**, dominated by transport (59.3%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **92.03%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 32.1% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (83.9%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 83.9% (SKU_B) to 99.5% (SKU_D) — a 15.6 pp range.

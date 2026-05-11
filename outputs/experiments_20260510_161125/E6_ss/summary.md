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
| Trials run | 100 |
| Feasible trials | 32 |
| Best trial # | 86 |
| Min fill rate target | — |

## Policy Parameters

| Parameter | Value |
|-----------|------:|
| `S_W1__SKU_A` | 3861 |
| `S_W1__SKU_B` | 1163 |
| `S_W1__SKU_C` | 3126 |
| `S_W1__SKU_D` | 2121 |
| `S_W1__SKU_E` | 1606 |
| `S_W2__SKU_A` | 3171 |
| `S_W2__SKU_B` | 1066 |
| `S_W2__SKU_C` | 2857 |
| `S_W2__SKU_D` | 836 |
| `S_W2__SKU_E` | 1614 |
| `S_R1__SKU_A` | 1716 |
| `S_R1__SKU_B` | 653 |
| `S_R1__SKU_C` | 890 |
| `S_R1__SKU_D` | 759 |
| `S_R1__SKU_E` | 470 |
| `S_R2__SKU_A` | 1339 |
| `S_R2__SKU_B` | 325 |
| `S_R2__SKU_C` | 813 |
| `S_R2__SKU_D` | 447 |
| `S_R2__SKU_E` | 600 |
| `S_R3__SKU_A` | 3759 |
| `S_R3__SKU_B` | 640 |
| `S_R3__SKU_C` | 2264 |
| `S_R3__SKU_D` | 2148 |
| `S_R3__SKU_E` | 1034 |
| `alpha_W1__SKU_A` | 0.49451453132817796 |
| `alpha_W1__SKU_B` | 0.8369095235355501 |
| `alpha_W1__SKU_C` | 0.8165862624317403 |
| `alpha_W1__SKU_D` | 0.35027515664574976 |
| `alpha_W1__SKU_E` | 0.7261110904410826 |
| `alpha_W2__SKU_A` | 0.6257765461507493 |
| `alpha_W2__SKU_B` | 0.3336450938253794 |
| `alpha_W2__SKU_C` | 0.3222646252682997 |
| `alpha_W2__SKU_D` | 0.3899885178107255 |
| `alpha_W2__SKU_E` | 0.8450807783687682 |
| `alpha_R1__SKU_A` | 0.4753066396727152 |
| `alpha_R1__SKU_B` | 0.8621732879547991 |
| `alpha_R1__SKU_C` | 0.5210811388961886 |
| `alpha_R1__SKU_D` | 0.4693551258122727 |
| `alpha_R1__SKU_E` | 0.8346833379560492 |
| `alpha_R2__SKU_A` | 0.6621618814476734 |
| `alpha_R2__SKU_B` | 0.4468149697324867 |
| `alpha_R2__SKU_C` | 0.5824746942571766 |
| `alpha_R2__SKU_D` | 0.5755392447439297 |
| `alpha_R2__SKU_E` | 0.7818306992801557 |
| `alpha_R3__SKU_A` | 0.8154699008963443 |
| `alpha_R3__SKU_B` | 0.8685382691135438 |
| `alpha_R3__SKU_C` | 0.859525666452433 |
| `alpha_R3__SKU_D` | 0.4000754516371629 |
| `alpha_R3__SKU_E` | 0.3698455097544493 |
| `D_Supplier_W1` | 0.4170516610277847 |
| `D_Supplier_W2` | 0.09417652690189586 |
| `D_W1_R1` | 0.28307752232721356 |
| `D_W1_R2` | 0.7844689356590846 |
| `D_W2_R3` | 0.27124968101528546 |

## Results

### Cost Breakdown

| Cost Component | Amount | Share |
|----------------|-------:|------:|
| **Total cost** | **301,687** | 100% |
| Holding | 125,770 | 41.7% |
| Transport | 147,611 | 48.9% |
| Ordering | 8,903 | 3.0% |
| Shortage (backlog) | 19,404 | 6.4% |

**Overall fill rate: 96.37%**

### Fill Rate by SKU

| SKU | Fill Rate |
|-----|----------:|
| SKU_A | 100.00% ✓ |
| SKU_B | 79.61% ✗ |
| SKU_C | 98.37% ✓ |
| SKU_D | 99.11% ✓ |
| SKU_E | 98.73% ✓ |

### Fill Rate by Node and SKU

| Node | SKU_A | SKU_B | SKU_C | SKU_D | SKU_E |
|------|------:|------:|------:|------:|------:|
| R1 | 100.0% | 100.0% | 95.8% | 100.0% | 100.0% |
| R2 | 100.0% | 35.2% | 100.0% | 96.1% | 100.0% |
| R3 | 100.0% | 97.5% | 100.0% | 100.0% | 97.3% |

### Bullwhip Effect

> BWE = Order CV² / Demand CV². Values > 1 indicate demand variance amplification upstream — the classic bullwhip effect.

| Node | SKU | Bullwhip Ratio |
|------|-----|---------------:|
| R1 | SKU_A | 80.832 ⚠ |
| R1 | SKU_B | 6.224 ⚠ |
| R1 | SKU_C | 24.612 ⚠ |
| R1 | SKU_D | 71.822 ⚠ |
| R1 | SKU_E | 15.201 ⚠ |
| R2 | SKU_A | 86.129 ⚠ |
| R2 | SKU_B | 25.649 ⚠ |
| R2 | SKU_C | 42.464 ⚠ |
| R2 | SKU_D | 54.998 ⚠ |
| R2 | SKU_E | 38.634 ⚠ |
| R3 | SKU_A | 47.545 ⚠ |
| R3 | SKU_B | 10.802 ⚠ |
| R3 | SKU_C | 15.125 ⚠ |
| R3 | SKU_D | 182.862 ⚠ |
| R3 | SKU_E | 142.626 ⚠ |
| Supplier | SKU_A | nan |
| Supplier | SKU_B | nan |
| Supplier | SKU_C | nan |
| Supplier | SKU_D | nan |
| Supplier | SKU_E | nan |
| W1 | SKU_A | 3.114 ⚠ |
| W1 | SKU_B | 2.151 ⚠ |
| W1 | SKU_C | 2.084 ⚠ |
| W1 | SKU_D | 4.518 ⚠ |
| W1 | SKU_E | 5.282 ⚠ |
| W2 | SKU_A | 2.321 ⚠ |
| W2 | SKU_B | 11.088 ⚠ |
| W2 | SKU_C | 7.551 ⚠ |
| W2 | SKU_D | 1.000 |
| W2 | SKU_E | 1.028 |

## Key Observations for Report

- Baseline total cost is **301,687**, dominated by transport (48.9%) — this is the primary optimisation target for subsequent experiments.
- Baseline fill rate of **96.37%** is below the 92% target, indicating the analytical newsvendor levels alone are insufficient for the target service level.
- With only 41.7% of cost in holding, there is room to increase inventory levels (raise S) to buffer against transport delays introduced by consolidation in later experiments.
- **SKU_B** has the lowest fill rate (79.6%) and may need a higher base-stock level or priority attention.
- Fill rate spread across SKUs: 79.6% (SKU_B) to 100.0% (SKU_A) — a 20.4 pp range.

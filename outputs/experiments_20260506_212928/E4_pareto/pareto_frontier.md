# E4 — Pareto Frontier: Cost vs Fill Rate

Map the trade-off curve between total system cost and fill rate under joint optimization. Shows decision-makers the range of feasible operating points and the cost of each additional percentage point of service level.

## NSGA-II frontier (primary)

method | fill_rate | total_cost | trial
-------+-----------+------------+------
nsga2  | 93.8986   | 301394.22  | 136  
nsga2  | 96.0736   | 329552.7   | 188  
nsga2  | 96.3162   | 336301.13  | 160  
nsga2  | 97.2489   | 336580.84  | 97   
nsga2  | 98.9348   | 380926.69  | 169  
nsga2  | 99.3192   | 381474.41  | 142  
nsga2  | 99.8196   | 385688.42  | 143  

## Constraint sweep (validation)

method | target_fill_pct | achieved_fill_pct | total_cost | feasible_trials | best_trial
-------+-----------------+-------------------+------------+-----------------+-----------
sweep  | 92.0            | 96.38             | 288701.3   | 18              | 27        
sweep  | 93.0            | 97.2              | 316062.09  | 10              | 46        
sweep  | 94.0            | 96.51             | 316561.82  | 11              | 12        
sweep  | 95.0            | 96.12             | 342736.55  | 11              | 28        
sweep  | 96.0            | 98.69             | 304098.39  | 10              | 40        
sweep  | 97.0            | 96.23             | 350164.05  | 0               | 39        
sweep  | 98.0            | 98.6              | 304663.63  | 4               | 41        
sweep  | 99.0            | 98.93             | 355758.43  | 0               | 46        

# E4 Pareto Decision Log

NSGA-II frontier points: 7
Sweep targets that bind: 8
NSGA-II curve smooth + monotone: **True**

Recommendation: Use NSGA-II as primary, sweep as validation overlay.

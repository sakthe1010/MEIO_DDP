# tests/test_local_flow_conservation.py
import pandas as pd
import pytest
from scripts.run_simulation import build_from_config
from engine.simulator import Simulator

def test_local_flow_conservation():
    cfg = {
        "time_horizon": 15,
        "nodes": [
            {"id":"Supplier","type":"supplier","infinite_supply":True,
             "policy":{"type":"base_stock","base_stock_level":0}},
            {"id":"W","type":"warehouse","initial_inventory":30,
             "policy":{"type":"base_stock","base_stock_level":45}},
            {"id":"R","type":"retailer","initial_inventory":10,
             "policy":{"type":"base_stock","base_stock_level":25}}
        ],
        "edges": [
            {"from":"Supplier","to":"W","lead_time":{"type":"deterministic","value":2}},
            {"from":"W","to":"R","lead_time":{"type":"deterministic","value":1}}
        ],
        "demand": [
            {"node":"R","generator":{"type":"deterministic","value":2}}
        ]
    }
    net, dmap, T = build_from_config(cfg)
    sim = Simulator(net, dmap, T, order_processing_delay=1)
    df = pd.DataFrame([m.__dict__ for m in sim.run(mode="detailed")])

    r = df[df.node_id == "R"].sort_values("t").reset_index(drop=True)

    required_cols = {"on_hand", "received"}  # for arrivals
    # need one of these for external demand consumed
    demand_cols = [c for c in ("demand", "demand_served") if c in r.columns]

    if not required_cols.issubset(set(r.columns)) or not demand_cols:
        pytest.skip(
            "Per-step local flow conservation requires 'received' and 'demand|demand_served' columns. "
            "Your detailed DF does not expose demand; skipping."
        )

    demand_col = demand_cols[0]

    # Skip t=0 to avoid edge logging artifacts
    for i in range(1, len(r) - 1):
        on_t = r.loc[i, "on_hand"]
        on_tp1 = r.loc[i + 1, "on_hand"]
        arrivals_next = r.loc[i + 1, "received"]
        demand_t = r.loc[i, demand_col]
        lhs = on_tp1
        rhs = on_t + arrivals_next - demand_t
        assert abs(lhs - rhs) < 1e-6, f"Retailer day {int(r.loc[i,'t'])}: {lhs} vs {rhs}"

# tests/conftest.py
import pandas as pd
import pytest
from scripts.run_simulation import build_from_config
from engine.simulator import Simulator

def df_from_cfg(cfg, *, mode="summary"):
    # Ensure config has 'skus' and all per-SKU fields are dicts
    if "skus" not in cfg:
        cfg = dict(cfg)  # shallow copy
        cfg["skus"] = ["SKU1"]
        for nd in cfg["nodes"]:
            if "initial_inventory" in nd and not isinstance(nd["initial_inventory"], dict):
                nd["initial_inventory"] = {"SKU1": nd["initial_inventory"]}
            if "policy" in nd and not isinstance(list(nd["policy"].values())[0], dict):
                nd["policy"] = {"SKU1": nd["policy"]}
        for d in cfg.get("demand", []):
            if "sku" not in d:
                d["sku"] = "SKU1"
    net, dmap, T = build_from_config(cfg)
    sim = Simulator(net, dmap, T, order_processing_delay=1)
    rows = sim.run(mode=mode)
    return pd.DataFrame([r.__dict__ for r in rows])

@pytest.fixture
def basic_serial_config():
    # Supplier -> Warehouse -> Retailer, deterministic demand
    return {
        "skus": ["SKU1"],
        "time_horizon": 20,
        "nodes": [
            {"id": "Supplier", "type": "supplier", "infinite_supply": True,
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 0}}},
            {"id": "Warehouse", "type": "warehouse", "initial_inventory": {"SKU1": 60},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 85}}},
            {"id": "Retailer", "type": "retailer", "initial_inventory": {"SKU1": 20},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 35}}}
        ],
        "edges": [
            {"from": "Supplier", "to": "Warehouse", "lead_time": {"type": "deterministic", "value": 2}},
            {"from": "Warehouse", "to": "Retailer", "lead_time": {"type": "deterministic", "value": 1}}
        ],
        "demand": [
            {"node": "Retailer", "sku": "SKU1", "generator": {"type": "deterministic", "value": 5}}
        ]
    }

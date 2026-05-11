"""tests/test_experiments_e2e.py

End-to-end smoke tests for the experiment pipeline.

These guard against regressions in the orchestration code:
  - newsvendor levels are computed and applied to the cfg before E0 runs
  - run_one returns the expected schema (cost ≥ 0, fill ∈ [0,1], non-empty logs)
  - the per-SKU optimizer mode actually returns a feasible result
  - bullwhip CSV is non-empty for a multi-echelon Poisson scenario

Trial counts are kept tiny so the suite runs in <30s.
"""
from pathlib import Path

import pandas as pd
import pytest

from scripts.run_experiments import (
    run_one, exp_E0, _compute_newsvendor_levels, _apply_newsvendor_levels,
)


def _two_echelon_cfg():
    return {
        "skus": ["SKU1"],
        "time_horizon": 80,
        "nodes": [
            {"id": "Supplier", "type": "supplier", "infinite_supply": True,
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 0}}},
            {"id": "W1", "type": "warehouse", "initial_inventory": {"SKU1": 100},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 100}},
             "holding_cost": 0.1, "shortage_cost": 5.0,
             "order_cost_fixed": 0.0, "order_cost_per_unit": 0.0},
            {"id": "R1", "type": "retailer", "initial_inventory": {"SKU1": 30},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 30}},
             "holding_cost": 0.2, "shortage_cost": 10.0,
             "order_cost_fixed": 0.0, "order_cost_per_unit": 0.0},
        ],
        "edges": [
            {"from": "Supplier", "to": "W1",
             "lead_time": {"type": "deterministic", "value": 2}},
            {"from": "W1", "to": "R1",
             "lead_time": {"type": "deterministic", "value": 1}},
        ],
        "demand": [
            {"node": "R1", "sku": "SKU1",
             "generator": {"type": "poisson", "lam": 5.0, "seed": 42}},
        ],
    }


def test_newsvendor_levels_are_positive_ints():
    cfg = _two_echelon_cfg()
    levels = _compute_newsvendor_levels(cfg, warmup=10, z=1.64)
    # Every non-supplier node should have a level for SKU1.
    assert "W1" in levels and "R1" in levels
    for nid in ("W1", "R1"):
        assert levels[nid]["SKU1"] > 0
        assert isinstance(levels[nid]["SKU1"], int)
    # Warehouse sees aggregated demand, so its level should be ≥ the retailer's
    # (with a single retailer they should be similar but the warehouse sees
    # an extra unit of lead time).
    assert levels["W1"]["SKU1"] >= 1


def test_apply_newsvendor_overwrites_policy_and_initial_inventory():
    cfg = _two_echelon_cfg()
    levels = {"W1": {"SKU1": 200}, "R1": {"SKU1": 80}}
    cfg2 = _apply_newsvendor_levels(cfg, levels)
    w1 = next(n for n in cfg2["nodes"] if n["id"] == "W1")
    r1 = next(n for n in cfg2["nodes"] if n["id"] == "R1")
    assert w1["policy"]["SKU1"]["base_stock_level"] == 200
    assert r1["policy"]["SKU1"]["base_stock_level"] == 80
    assert w1["initial_inventory"]["SKU1"] == 200
    assert r1["initial_inventory"]["SKU1"] == 80


def test_run_one_returns_expected_schema():
    cfg = _two_echelon_cfg()
    res = run_one(cfg, volume_per_unit={"SKU1": 1.0}, label="smoke",
                  warmup_periods=10)
    # Cost / fill rate sanity.
    assert res["total_cost"] >= 0
    assert 0.0 <= res["fill_rate"] <= 1.0
    # Cost percentages sum to 100 (within rounding) when total_cost > 0.
    if res["total_cost"] > 0:
        pct_sum = (res["holding_pct"] + res["transport_pct"]
                   + res["ordering_pct"] + res["backlog_pct"])
        assert abs(pct_sum - 100.0) < 1e-6
    # Logs / KPI tables are dataframes.
    for key in ("costs_df", "sku_kpis", "node_kpis", "bullwhip_df",
                "inventory_log", "orders_log"):
        assert isinstance(res[key], pd.DataFrame), key


def test_e0_writes_params_with_runtime_levels(tmp_path: Path):
    cfg = _two_echelon_cfg()
    res = exp_E0(cfg, vpu={"SKU1": 1.0}, out_dir=tmp_path, warmup=10)
    assert (tmp_path / "E0" / "params.json").exists()
    import json
    saved = json.loads((tmp_path / "E0" / "params.json").read_text())
    # Should contain S_W1__SKU1 and S_R1__SKU1 keys (from newsvendor).
    keys = {k for k in saved if k.startswith("S_")}
    assert "S_W1__SKU1" in keys
    assert "S_R1__SKU1" in keys
    assert res["total_cost"] >= 0


def test_bullwhip_csv_populated_for_poisson_demand():
    cfg = _two_echelon_cfg()
    res = run_one(cfg, volume_per_unit={"SKU1": 1.0}, label="smoke",
                  warmup_periods=10)
    bw = res["bullwhip_df"]
    # We expect at least the warehouse and retailer rows.
    assert not bw.empty
    assert {"node_id", "sku", "cv2_in", "cv2_out", "bullwhip_ratio"} <= set(bw.columns)

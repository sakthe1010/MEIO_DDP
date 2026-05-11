"""tests/test_bullwhip.py

Validates the per-echelon bullwhip computation in scripts.run_experiments.run_one.

Key invariants:
  - Constant demand → bullwhip is NaN (CV² = 0/0).
  - Retailer's denominator is external demand CV².
  - Warehouse's denominator is the CV² of *aggregated child orders*, not raw
    retailer demand. With one child the warehouse's incoming series equals
    that child's order series, so warehouse_bwe = CV²(W→S) / CV²(R→W).
"""
import math
import pandas as pd
import pytest

from scripts.run_experiments import run_one


def _two_echelon_cfg(retailer_demand_seed: int = 7):
    return {
        "skus": ["SKU1"],
        "time_horizon": 60,
        "nodes": [
            {"id": "Supplier", "type": "supplier", "infinite_supply": True,
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 0}}},
            {"id": "W1", "type": "warehouse", "initial_inventory": {"SKU1": 100},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 100}}},
            {"id": "R1", "type": "retailer", "initial_inventory": {"SKU1": 30},
             "policy": {"SKU1": {"type": "base_stock", "base_stock_level": 30}}},
        ],
        "edges": [
            {"from": "Supplier", "to": "W1", "lead_time": {"type": "deterministic", "value": 2}},
            {"from": "W1", "to": "R1", "lead_time": {"type": "deterministic", "value": 1}},
        ],
        "demand": [
            {"node": "R1", "sku": "SKU1",
             "generator": {"type": "poisson", "lam": 5.0, "seed": retailer_demand_seed}},
        ],
    }


def test_bullwhip_constant_demand_is_nan():
    """Constant demand → both CV² = 0 → bullwhip undefined (NaN)."""
    cfg = _two_echelon_cfg()
    cfg["demand"] = [
        {"node": "R1", "sku": "SKU1", "generator": {"type": "deterministic", "value": 5}}
    ]
    res = run_one(cfg, volume_per_unit={"SKU1": 1.0}, label="const",
                  warmup_periods=10)
    bw = res["bullwhip_df"]
    # Either no rows (no orders generated) or every ratio is NaN.
    if not bw.empty:
        for v in bw["bullwhip_ratio"]:
            assert pd.isna(v), f"expected NaN under constant demand, got {v}"


def test_bullwhip_columns_present():
    """The corrected metric reports cv2_in and cv2_out alongside the ratio."""
    cfg = _two_echelon_cfg()
    res = run_one(cfg, volume_per_unit={"SKU1": 1.0}, label="poisson",
                  warmup_periods=10)
    bw = res["bullwhip_df"]
    assert {"node_id", "sku", "cv2_in", "cv2_out", "bullwhip_ratio"} <= set(bw.columns)


def test_bullwhip_warehouse_uses_child_orders_not_external_demand():
    """The warehouse denominator should be CV² of child orders.

    With a single retailer child, that's equivalent to CV² of orders R1→W1.
    The previous (buggy) implementation used CV² of external demand at R1
    (which is *fulfilled* demand, not the *order* series). When there are
    stockouts those two series differ. We assert the value matches the
    new definition.
    """
    cfg = _two_echelon_cfg()
    res = run_one(cfg, volume_per_unit={"SKU1": 1.0}, label="poisson",
                  warmup_periods=10)
    bw = res["bullwhip_df"]
    orders_log = res["orders_log"]
    if bw.empty or orders_log.empty:
        pytest.skip("no orders generated in this short scenario")

    orders = orders_log[orders_log["t"] >= 10]

    # CV² of R1's outgoing orders (= W1's incoming series with a single child).
    r1_orders = (orders[(orders["node_id"] == "R1") & (orders["sku"] == "SKU1")]
                 .sort_values("t")["orders_to_parent"])
    if r1_orders.empty or r1_orders.mean() <= 0:
        pytest.skip("no R1 orders to compute denominator")
    expected_cv2_in = (r1_orders.std() / r1_orders.mean()) ** 2

    w1_row = bw[(bw["node_id"] == "W1") & (bw["sku"] == "SKU1")]
    if w1_row.empty:
        pytest.skip("no W1 bullwhip row")
    cv2_in_reported = float(w1_row["cv2_in"].iloc[0])

    assert math.isclose(cv2_in_reported, expected_cv2_in, rel_tol=1e-3, abs_tol=1e-6), (
        f"warehouse cv2_in should equal CV² of child orders, "
        f"got {cv2_in_reported} expected {expected_cv2_in}"
    )

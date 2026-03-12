"""
engine/config_validator.py
==========================
Validates a DDP simulator config dict before any simulation objects are built.
Called automatically by build_from_config() in run_simulation.py.

Raises ConfigValidationError with a clear, human-readable message describing
exactly what is wrong and where. No more cryptic Python tracebacks for users.

Usage (automatic)
-----------------
  # Already called inside build_from_config():
  from engine.config_validator import validate_config
  validate_config(cfg)

Usage (manual / CLI)
--------------------
  python engine/config_validator.py config/1n3_5sku.json
"""

from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# Exception
# ============================================================

class ConfigValidationError(Exception):
    """Raised when a config fails validation. Message is human-readable."""
    pass


# ============================================================
# Internal helpers
# ============================================================

def _err(msg: str) -> None:
    raise ConfigValidationError(msg)


def _check_required(obj: dict, keys: List[str], context: str) -> None:
    for k in keys:
        if k not in obj:
            _err(f"[{context}] Missing required field: '{k}'")


def _check_positive(value: Any, name: str, context: str) -> None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        _err(f"[{context}] '{name}' must be a number, got: {value!r}")
    if v <= 0:
        _err(f"[{context}] '{name}' must be > 0, got: {v}")


def _check_non_negative(value: Any, name: str, context: str) -> None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        _err(f"[{context}] '{name}' must be a number, got: {value!r}")
    if v < 0:
        _err(f"[{context}] '{name}' must be >= 0, got: {v}")


VALID_POLICY_TYPES = {"base_stock", "sS", "order_up_to", "km_cycle", "periodic_review"}
VALID_NODE_TYPES   = {"supplier", "warehouse", "retailer"}
VALID_DEMAND_TYPES = {"deterministic", "poisson", "csv"}
VALID_LT_TYPES     = {"deterministic", "normal_int"}


# ============================================================
# Section validators
# ============================================================

def _validate_top_level(cfg: dict) -> None:
    _check_required(cfg, ["nodes", "edges", "time_horizon"], "config root")

    try:
        T = int(cfg["time_horizon"])
    except (TypeError, ValueError):
        _err(f"[config root] 'time_horizon' must be an integer, got: {cfg['time_horizon']!r}")
    if T <= 0:
        _err(f"[config root] 'time_horizon' must be > 0, got: {T}")


def _validate_skus(cfg: dict) -> List[str]:
    skus = cfg.get("skus", ["SKU1"])
    if not isinstance(skus, list) or len(skus) == 0:
        _err("[config root] 'skus' must be a non-empty list of strings")
    for s in skus:
        if not isinstance(s, str) or not s.strip():
            _err(f"[config root] Each entry in 'skus' must be a non-empty string, got: {s!r}")
    if len(skus) != len(set(skus)):
        _err(f"[config root] 'skus' contains duplicates: {skus}")
    return skus


def _validate_sku_properties(cfg: dict, skus: List[str]) -> None:
    props = cfg.get("sku_properties", {})
    for sku in skus:
        sp = props.get(sku, {})
        vpu = sp.get("volume_per_unit", 1.0)
        _check_positive(vpu, "volume_per_unit", f"sku_properties/{sku}")
        wpu = sp.get("weight_per_unit", None)
        if wpu is not None:
            _check_positive(wpu, "weight_per_unit", f"sku_properties/{sku}")


def _validate_policy_block(policy_block: dict, skus: List[str], node_id: str) -> None:
    """Validate the nested {sku: {type: ..., params}} policy dict."""
    if not isinstance(policy_block, dict):
        _err(f"[node {node_id}] 'policy' must be a dict, got: {type(policy_block).__name__}")

    for sku in skus:
        if sku not in policy_block:
            _err(f"[node {node_id}] Missing policy for SKU '{sku}'")

        pol = policy_block[sku]
        ctx = f"node {node_id} / policy / {sku}"

        if not isinstance(pol, dict):
            _err(f"[{ctx}] Policy must be a dict, got: {type(pol).__name__}")

        _check_required(pol, ["type"], ctx)
        ptype = pol["type"]

        if ptype not in VALID_POLICY_TYPES:
            _err(f"[{ctx}] Unknown policy type '{ptype}'. Valid: {sorted(VALID_POLICY_TYPES)}")

        if ptype == "base_stock":
            _check_required(pol, ["base_stock_level"], ctx)
            _check_non_negative(pol["base_stock_level"], "base_stock_level", ctx)

        elif ptype == "sS":
            _check_required(pol, ["s", "S"], ctx)
            s, S = pol["s"], pol["S"]
            _check_non_negative(s, "s", ctx)
            _check_non_negative(S, "S", ctx)
            if float(s) >= float(S):
                _err(f"[{ctx}] (s,S) policy requires s < S, got s={s}, S={S}")

        elif ptype == "order_up_to":
            _check_required(pol, ["R", "S"], ctx)
            _check_positive(pol["R"], "R", ctx)
            _check_non_negative(pol["S"], "S", ctx)

        elif ptype == "km_cycle":
            _check_required(pol, ["k", "m", "S"], ctx)
            _check_positive(pol["k"], "k", ctx)
            _check_positive(pol["m"], "m", ctx)
            _check_non_negative(pol["S"], "S", ctx)

        elif ptype == "periodic_review":
            _check_required(pol, ["review_period", "order_up_to"], ctx)
            _check_positive(pol["review_period"], "review_period", ctx)
            _check_non_negative(pol["order_up_to"], "order_up_to", ctx)


def _validate_cost_field(value: Any, field: str, node_id: str, skus: List[str]) -> None:
    """
    A cost field can be:
      - a single float (applied to all SKUs)
      - a dict {sku: float} with at least all SKUs covered
    """
    ctx = f"node {node_id} / {field}"
    if isinstance(value, dict):
        for sku in skus:
            if sku not in value:
                _err(f"[{ctx}] Per-SKU dict missing entry for SKU '{sku}'")
            _check_non_negative(value[sku], f"{field}[{sku}]", ctx)
    else:
        _check_non_negative(value, field, ctx)


def _validate_nodes(cfg: dict, skus: List[str]) -> Dict[str, str]:
    """Returns {node_id: node_type}."""
    nodes = cfg["nodes"]
    if not isinstance(nodes, list) or len(nodes) == 0:
        _err("[config root] 'nodes' must be a non-empty list")

    node_ids: Dict[str, str] = {}

    for nd in nodes:
        if not isinstance(nd, dict):
            _err(f"[nodes] Each node must be a dict, got: {type(nd).__name__}")

        _check_required(nd, ["id", "type"], "node entry")
        nid   = nd["id"]
        ntype = nd["type"]
        ctx   = f"node {nid}"

        if nid in node_ids:
            _err(f"[{ctx}] Duplicate node id '{nid}'")

        if ntype not in VALID_NODE_TYPES:
            _err(f"[{ctx}] Unknown node type '{ntype}'. Valid: {sorted(VALID_NODE_TYPES)}")

        node_ids[nid] = ntype

        # Policy — required for all non-supplier nodes (supplier needs it too but base_stock 0)
        if "policy" not in nd:
            _err(f"[{ctx}] Missing 'policy' block")
        _validate_policy_block(nd["policy"], skus, nid)

        # Cost fields
        for field in ("holding_cost", "shortage_cost", "order_cost_fixed", "order_cost_per_unit"):
            if field in nd:
                _validate_cost_field(nd[field], field, nid, skus)

        # Initial inventory
        inv = nd.get("initial_inventory", {})
        if isinstance(inv, dict):
            for sku, qty in inv.items():
                if sku not in skus:
                    _err(f"[{ctx}] initial_inventory has unknown SKU '{sku}'. Known: {skus}")
                try:
                    q = int(qty)
                except (TypeError, ValueError):
                    _err(f"[{ctx}] initial_inventory[{sku}] must be an integer, got: {qty!r}")
                if q < 0:
                    _err(f"[{ctx}] initial_inventory[{sku}] must be >= 0, got: {q}")
        elif inv is not None:
            try:
                q = int(inv)
                if q < 0:
                    _err(f"[{ctx}] initial_inventory must be >= 0, got: {q}")
            except (TypeError, ValueError):
                _err(f"[{ctx}] initial_inventory must be int or dict, got: {inv!r}")

    return node_ids


def _validate_edges(cfg: dict, node_ids: Dict[str, str]) -> None:
    edges = cfg["edges"]
    if not isinstance(edges, list):
        _err("[config root] 'edges' must be a list")

    seen_pairs = set()

    for e in edges:
        if not isinstance(e, dict):
            _err(f"[edges] Each edge must be a dict, got: {type(e).__name__}")
        _check_required(e, ["from", "to", "lead_time"], "edge entry")

        src, dst = e["from"], e["to"]
        ctx = f"edge {src}->{dst}"

        if src not in node_ids:
            _err(f"[{ctx}] Unknown source node '{src}'. Known nodes: {list(node_ids.keys())}")
        if dst not in node_ids:
            _err(f"[{ctx}] Unknown destination node '{dst}'. Known nodes: {list(node_ids.keys())}")
        if src == dst:
            _err(f"[{ctx}] Self-loop not allowed")

        # Transport fields
        for field in ("capacity", "cost_full", "cost_half", "cost_quarter"):
            if field in e:
                _check_positive(e[field], field, ctx)

        # Lead time
        lt = e["lead_time"]
        if not isinstance(lt, dict):
            _err(f"[{ctx}] 'lead_time' must be a dict, got: {type(lt).__name__}")
        _check_required(lt, ["type"], f"{ctx} / lead_time")
        if lt["type"] not in VALID_LT_TYPES:
            _err(f"[{ctx}] Unknown lead_time type '{lt['type']}'. Valid: {sorted(VALID_LT_TYPES)}")
        if lt["type"] == "deterministic":
            _check_required(lt, ["value"], f"{ctx} / lead_time")
            _check_non_negative(lt["value"], "value", f"{ctx} / lead_time")
        elif lt["type"] == "normal_int":
            _check_required(lt, ["mean", "std"], f"{ctx} / lead_time")
            _check_non_negative(lt["mean"], "mean", f"{ctx} / lead_time")
            _check_non_negative(lt["std"],  "std",  f"{ctx} / lead_time")


def _validate_demand(cfg: dict, node_ids: Dict[str, str], skus: List[str]) -> None:
    demand = cfg.get("demand", [])
    if not isinstance(demand, list):
        _err("[config root] 'demand' must be a list")

    for d in demand:
        if not isinstance(d, dict):
            _err(f"[demand] Each entry must be a dict, got: {type(d).__name__}")

        _check_required(d, ["node", "generator"], "demand entry")
        node  = d["node"]
        sku   = d.get("sku", "SKU1")
        ctx   = f"demand / {node} / {sku}"

        if node not in node_ids:
            _err(f"[{ctx}] Unknown node '{node}'. Known nodes: {list(node_ids.keys())}")
        if sku not in skus:
            _err(f"[{ctx}] Unknown SKU '{sku}'. Known SKUs: {skus}")
        if node_ids[node] != "retailer":
            # Warning only — suppliers/warehouses can have demand in some scenarios
            pass

        g = d["generator"]
        if not isinstance(g, dict):
            _err(f"[{ctx}] 'generator' must be a dict")
        _check_required(g, ["type"], ctx + " / generator")

        gtype = g["type"]
        if gtype not in VALID_DEMAND_TYPES:
            _err(f"[{ctx}] Unknown demand generator type '{gtype}'. Valid: {sorted(VALID_DEMAND_TYPES)}")

        if gtype == "deterministic":
            _check_required(g, ["value"], ctx + " / generator")
            _check_non_negative(g["value"], "value", ctx + " / generator")

        elif gtype == "poisson":
            _check_required(g, ["lam"], ctx + " / generator")
            _check_positive(g["lam"], "lam", ctx + " / generator")

        elif gtype == "csv":
            if "path" not in g and not ("manifest" in g and "store_id" in g):
                _err(
                    f"[{ctx}] CSV generator requires either 'path' or both 'manifest' + 'store_id'"
                )


# ============================================================
# Public entry point
# ============================================================

def validate_config(cfg: dict, repo_root: Optional[Path] = None) -> None:
    """
    Validate a config dict. Raises ConfigValidationError with a clear message
    if anything is wrong. Silent on success.

    Parameters
    ----------
    cfg       : parsed config dict
    repo_root : if provided, checks that CSV demand file paths actually exist
    """
    _validate_top_level(cfg)
    skus     = _validate_skus(cfg)
    _validate_sku_properties(cfg, skus)
    node_ids = _validate_nodes(cfg, skus)
    _validate_edges(cfg, node_ids)
    _validate_demand(cfg, node_ids, skus)

    # Optional: check CSV paths exist
    if repo_root is not None:
        for d in cfg.get("demand", []):
            g = d.get("generator", {})
            if g.get("type") == "csv" and "path" in g:
                p = (repo_root / g["path"]).resolve()
                if not p.exists():
                    _err(
                        f"[demand / {d.get('node')} / {d.get('sku', 'SKU1')}] "
                        f"CSV file not found: {p}\n"
                        f"  Check the 'path' field in your config or run the build script first."
                    )


# ============================================================
# CLI usage: python engine/config_validator.py config/1n3_5sku.json
# ============================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python engine/config_validator.py <config.json>")
        sys.exit(1)

    cfg_path = Path(sys.argv[1])
    if not cfg_path.exists():
        print(f"ERROR: File not found: {cfg_path}")
        sys.exit(1)

    with open(cfg_path) as f:
        cfg = json.load(f)

    # Determine repo root for CSV path checking
    here = Path(__file__).resolve()
    root = here.parent
    while root.parent != root:
        if (root / "engine").exists():
            break
        root = root.parent

    try:
        validate_config(cfg, repo_root=root)
        print(f"✓ Config is valid: {cfg_path}")
    except ConfigValidationError as e:
        print(f"\n✗ Config validation failed:\n\n  {e}\n")
        sys.exit(1)
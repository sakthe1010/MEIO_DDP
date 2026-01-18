import os
import json
import pandas as pd
from collections import defaultdict

# =========================
# Errors
# =========================

class ConfigBuildError(Exception):
    pass


def error(msg):
    raise ConfigBuildError(f"[CONFIG BUILD ERROR] {msg}")


# =========================
# Helpers
# =========================

def read_csv(path, required_cols):
    if not os.path.exists(path):
        error(f"Missing required file: {path}")

    df = pd.read_csv(path)

    missing = set(required_cols) - set(df.columns)
    if missing:
        error(f"{path} is missing columns: {sorted(missing)}")

    return df


def ensure_unique(df, col, name):
    if df[col].duplicated().any():
        error(f"Duplicate {name} detected in column '{col}'")


# =========================
# SIM CONFIG
# =========================

def load_sim_config(path):
    df = read_csv(path, ["parameter", "value"])
    config = {}

    for _, row in df.iterrows():
        config[row["parameter"]] = row["value"]

    required = ["seed", "time_horizon"]
    for r in required:
        if r not in config:
            error(f"sim_config.csv missing required parameter '{r}'")

    config["seed"] = int(config["seed"])
    config["time_horizon"] = int(config["time_horizon"])

    return config


# =========================
# NODES
# =========================

def load_nodes(path):
    df = read_csv(
        path,
        [
            "node_id",
            "node_type",
            "initial_inventory",
            "holding_cost",
            "shortage_cost",
            "order_cost_fixed",
            "order_cost_per_unit",
            "infinite_supply",
        ],
    )

    ensure_unique(df, "node_id", "node_id")

    nodes = {}
    for _, r in df.iterrows():
        if r["initial_inventory"] < 0:
            error(f"Node {r['node_id']} has negative initial_inventory")

        if r["holding_cost"] < 0 or r["shortage_cost"] < 0:
            error(f"Node {r['node_id']} has negative cost values")

        if r["infinite_supply"] not in (0, 1):
            error(f"Node {r['node_id']} infinite_supply must be 0 or 1")

        nodes[r["node_id"]] = {
            "id": r["node_id"],
            "type": r["node_type"],
            "initial_inventory": int(r["initial_inventory"]),
            "holding_cost": float(r["holding_cost"]),
            "shortage_cost": float(r["shortage_cost"]),
            "order_cost_fixed": float(r["order_cost_fixed"]),
            "order_cost_per_unit": float(r["order_cost_per_unit"]),
            "infinite_supply": bool(r["infinite_supply"]),
        }

    return nodes


# =========================
# POLICIES
# =========================

POLICY_REQUIRED_PARAMS = {
    "base_stock": {"base_stock_level"},
    "ss": {"s", "S"},
    "order_up_to": {"level"},
    "periodic_review": {"review_period", "target_level"},
    "km_cycle": {"K", "M"},
}


def load_policies(path, nodes):
    df = read_csv(path, ["node_id", "policy_type", "param_name", "param_value"])

    grouped = defaultdict(list)
    for _, r in df.iterrows():
        grouped[r["node_id"]].append(r)

    for node_id in grouped:
        if node_id not in nodes:
            error(f"Policy assigned to unknown node '{node_id}'")

    for node_id, rows in grouped.items():
        policy_types = {r["policy_type"] for r in rows}
        if len(policy_types) != 1:
            error(f"Node '{node_id}' has multiple policy types: {policy_types}")

        policy_type = policy_types.pop()
        if policy_type not in POLICY_REQUIRED_PARAMS:
            error(f"Unknown policy_type '{policy_type}' for node '{node_id}'")

        params = {}
        for r in rows:
            if r["param_name"] in params:
                error(f"Duplicate param '{r['param_name']}' for node '{node_id}'")
            params[r["param_name"]] = float(r["param_value"])

        missing = POLICY_REQUIRED_PARAMS[policy_type] - set(params)
        if missing:
            error(
                f"Policy '{policy_type}' for node '{node_id}' missing params {missing}"
            )

        nodes[node_id]["policy"] = {
            "type": policy_type,
            **params,
        }

    # Ensure every non-supplier node has a policy
    for node_id, node in nodes.items():
        if node["type"] != "supplier" and "policy" not in node:
            error(f"Node '{node_id}' has no policy assigned")

    return nodes


# =========================
# ROUTES
# =========================

def load_routes(path, nodes):
    df = read_csv(path, ["from_node", "to_node", "lead_time", "transport_cost_per_unit"])

    edges = []
    for _, r in df.iterrows():
        if r["from_node"] not in nodes:
            error(f"Route from unknown node '{r['from_node']}'")
        if r["to_node"] not in nodes:
            error(f"Route to unknown node '{r['to_node']}'")
        if r["lead_time"] < 0:
            error(f"Negative lead_time on route {r['from_node']} → {r['to_node']}")
        if r["transport_cost_per_unit"] < 0:
            error(
                f"Negative transport cost on route {r['from_node']} → {r['to_node']}"
            )

        edges.append(
            {
                "from": r["from_node"],
                "to": r["to_node"],
                "lead_time": {
                    "type": "deterministic",
                    "value": int(r["lead_time"]),
                },
                "transport_cost_per_unit": float(r["transport_cost_per_unit"]),
            }
        )

    return edges


# =========================
# DEMAND
# =========================

def load_demand(path, nodes):
    df = read_csv(
        path,
        ["node_id", "source_type", "source_path", "time_col", "quantity_col", "fill_strategy"],
    )

    demand = []
    for _, r in df.iterrows():
        if r["node_id"] not in nodes:
            error(f"Demand assigned to unknown node '{r['node_id']}'")

        if r["source_type"] != "csv":
            error(f"Unsupported demand source_type '{r['source_type']}'")

        if not os.path.exists(r["source_path"]):
            error(f"Demand file not found: {r['source_path']}")

        demand.append(
            {
                "node": r["node_id"],
                "generator": {
                    "type": "csv",
                    "path": r["source_path"],
                    "date_col": r["time_col"],
                    "qty_col": r["quantity_col"],
                    "strategy": r["fill_strategy"],
                },
            }
        )

    return demand


# =========================
# MAIN
# =========================

def build_config(inputs_dir, output_path):
    sim = load_sim_config(f"{inputs_dir}/sim_config.csv")
    nodes = load_nodes(f"{inputs_dir}/nodes.csv")
    nodes = load_policies(f"{inputs_dir}/policies.csv", nodes)
    edges = load_routes(f"{inputs_dir}/routes.csv", nodes)
    demand = load_demand(f"{inputs_dir}/demand_config.csv", nodes)

    config = {
        **sim,
        "nodes": list(nodes.values()),
        "edges": edges,
        "demand": demand,
    }

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"[SUCCESS] Config written to {output_path}")


if __name__ == "__main__":
    build_config(
        inputs_dir="inputs",
        output_path="inputs/config/generated_from_csv.json",
    )

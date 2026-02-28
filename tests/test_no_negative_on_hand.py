import pandas as pd
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy


def test_no_negative_on_hand_over_horizon():
    net = Network()

    r = Node(
        node_id="R",
        node_type="retailer",
        policies={"SKU1": BaseStockPolicy(base_stock_level=0)},
        skus=["SKU1"],
        initial_inventory={"SKU1": 0},
    )

    net.add_node(r)

    demand_by_node = {"R": {"SKU1": lambda t: 10}}

    sim = Simulator(net, demand_by_node, T=10)
    df = pd.DataFrame([m.__dict__ for m in sim.run()])

    df = df[df["sku"] == "SKU1"]

    assert (df["on_hand"] >= 0).all()

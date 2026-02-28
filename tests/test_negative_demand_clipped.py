import pandas as pd
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy


def test_negative_demand_is_clipped():
    net = Network()

    r = Node(
        node_id="R",
        node_type="retailer",
        policies={"SKU1": BaseStockPolicy(base_stock_level=10)},
        skus=["SKU1"],
        initial_inventory={"SKU1": 5},
    )

    net.add_node(r)

    demand_by_node = {"R": {"SKU1": lambda t: -5}}

    sim = Simulator(net, demand_by_node, T=5)
    df = pd.DataFrame([m.__dict__ for m in sim.run()])

    df = df[df["sku"] == "SKU1"]

    assert (df["on_hand"] >= 0).all()

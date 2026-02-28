import pandas as pd
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BaseStockPolicy


def test_zero_lead_time_not_lost():
    net = Network()

    w = Node(
        node_id="W",
        node_type="warehouse",
        policies={"SKU1": BaseStockPolicy(base_stock_level=0)},
        skus=["SKU1"],
        initial_inventory={"SKU1": 100},
    )

    r = Node(
        node_id="R",
        node_type="retailer",
        policies={"SKU1": BaseStockPolicy(base_stock_level=20)},
        skus=["SKU1"],
        initial_inventory={"SKU1": 0},
    )

    net.add_node(w)
    net.add_node(r)

    net.add_edge("W", "R", lead_time_sampler=lambda: 0)

    demand_by_node = {"R": {"SKU1": lambda t: 0}}

    sim = Simulator(net, demand_by_node, T=4, order_processing_delay=1)
    df = pd.DataFrame([m.__dict__ for m in sim.run(mode="summary")])

    df = df[df["sku"] == "SKU1"]

    r_eod = df[(df.node_id == "R") & (df.phase == "EOD")]
    assert (r_eod["on_hand"] > 0).any()

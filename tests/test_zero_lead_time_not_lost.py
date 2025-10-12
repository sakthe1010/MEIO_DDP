import pytest
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BasePolicy


def deterministic_zero():
    return 0


def test_zero_lead_time_not_lost():
    # Simple 1->1 network (parent=warehouse, child=retailer)
    net = Network()
    w = Node("W", "warehouse", on_hand=100)
    r = Node("R", "retailer", on_hand=0)
    net.add_node(w); net.add_node(r)
    net.add_edge("W","R")

    demand_by_node = {"R": [0, 0, 0, 0]}
    policies = {"R": BasePolicy(S=20), "W": BasePolicy(S=0)}  # W doesn't order upstream

    lead_samplers = {("W","R"): deterministic_zero}  # L=0

    sim = Simulator(
        network=net,
        demand_by_node=demand_by_node,
        policy_by_node=policies,
        lead_time_sampler_by_edge=lead_samplers,
        order_processing_delay=1,
        infinite_supply_roots=False,
        mode="summary"
    )

    res = sim.run()
    # R should receive shipments (with our fix they arrive at earliest next day)
    # After first EOD, R will have placed an order (20), W ships at t=0 against that need
    # Shipment arrives at t=1 (not lost at t=0)
    # By t=2 snapshot, R must have strictly positive on_hand
    oh_t2 = [row.on_hand for row in res.timeline if row.t == 2 and row.node_id == "R"][0]
    assert oh_t2 > 0

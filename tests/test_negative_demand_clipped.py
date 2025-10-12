import pytest
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BasePolicy


def deterministic_one():
    return 1


def test_negative_demand_is_clipped():
    net = Network()
    r = Node("R", "retailer", on_hand=10)
    net.add_node(r)
    demand_by_node = {"R": [5, -7, 3]}  # negative will be clipped to 0
    policies = {"R": BasePolicy(S=10)}
    lead_samplers = {}

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

    # After day 0: 10-5=5
    oh_t0 = [row.on_hand for row in res.timeline if row.t == 0 and row.node_id == "R"][0]
    # After day 1: demand is -7 -> clipped to 0 -> on_hand unchanged (except any arrivals, which we don't have here)
    oh_t1 = [row.on_hand for row in res.timeline if row.t == 1 and row.node_id == "R"][0]
    assert oh_t0 == 5
    assert oh_t1 == 5

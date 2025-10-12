import pytest
from engine.network import Network
from engine.node import Node
from engine.simulator import Simulator
from policies.base_stock import BasePolicy


def deterministic_one():
    return 1


def test_no_negative_on_hand_over_horizon():
    net = Network()
    s = Node("S", "supplier", on_hand=0)   # Infinite supply not needed here
    w = Node("W", "warehouse", on_hand=50)
    r = Node("R", "retailer", on_hand=20)
    net.add_node(s); net.add_node(w); net.add_node(r)
    net.add_edge("W","R")  # simple W->R chain

    demand = [5]*50
    demand_by_node = {"R": demand}
    policies = {
        "R": BasePolicy(S=25),  # generous S so it won't starve
        "W": BasePolicy(S=70),
        "S": BasePolicy(S=0)
    }
    lead_samplers = {("W","R"): deterministic_one}

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

    for row in res.timeline:
        assert row.on_hand >= 0, f"Negative on_hand at t={row.t} node={row.node_id}"
        assert row.backlog_external >= 0
        assert row.backlog_children >= 0
        assert row.pipeline_in >= 0

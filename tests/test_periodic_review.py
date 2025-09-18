import pytest
import pandas as pd
from engine.node import Node
from engine.network import Network, Edge
from engine.simulator import Simulator
from policies.periodic_review import PeriodicReviewPolicy
from scripts.run_simulation import build_from_config
import json

def test_periodic_review_basic():
    """Test basic functionality of periodic review policy"""
    # Setup a simple network with periodic review
    cfg = {
        "time_horizon": 10,
        "nodes": [
            {"id": "Supplier", "type": "supplier", "infinite_supply": True,
             "policy": {"type": "periodic_review", "review_period": 3, "order_up_to": 50}},
            {"id": "Retailer", "type": "retailer", "initial_inventory": 20,
             "policy": {"type": "periodic_review", "review_period": 2, "order_up_to": 30}}
        ],
        "edges": [
            {"from": "Supplier", "to": "Retailer", 
             "lead_time": {"type": "deterministic", "value": 1}}
        ],
        "demand": [
            {"node": "Retailer", "generator": {"type": "deterministic", "value": 5}}
        ]
    }
    
    net, dmap, T = build_from_config(cfg)
    sim = Simulator(net, dmap, T)
    results = sim.run()
    df = pd.DataFrame([r.__dict__ for r in results])
    
    # Check that orders only happen on review periods
    retailer_orders = df[df.node_id == "Retailer"]["orders_to_parent"]
    for t in range(T):
        if t % 2 != 0:  # Non-review periods
            assert retailer_orders.iloc[t] == 0

def test_periodic_review_order_quantity():
    """Test that order quantities are correct"""
    policy = PeriodicReviewPolicy(review_period=2, order_up_to=100)
    
    # Should order on review period
    qty = policy.order_qty(
        on_hand=60,
        backlog_external=10,
        backlog_children=0,
        pipeline_in=20,
        t=2
    )
    # Inventory position = 60 - 10 + 20 = 70
    # Should order up to 100
    assert qty == 30
    
    # Should not order between reviews
    qty = policy.order_qty(
        on_hand=60,
        backlog_external=10,
        backlog_children=0,
        pipeline_in=20,
        t=3
    )
    assert qty == 0

def test_periodic_review_integration():
    """Test periodic review in a more complex network"""
    cfg = {
        "time_horizon": 20,
        "nodes": [
            {"id": "Supplier", "type": "supplier", "infinite_supply": True,
             "policy": {"type": "periodic_review", "review_period": 4, "order_up_to": 200}},
            {"id": "DC", "type": "warehouse", "initial_inventory": 100,
             "policy": {"type": "periodic_review", "review_period": 3, "order_up_to": 150}},
            {"id": "R1", "type": "retailer", "initial_inventory": 30,
             "policy": {"type": "periodic_review", "review_period": 2, "order_up_to": 50}},
            {"id": "R2", "type": "retailer", "initial_inventory": 30,
             "policy": {"type": "periodic_review", "review_period": 2, "order_up_to": 50}}
        ],
        "edges": [
            {"from": "Supplier", "to": "DC", 
             "lead_time": {"type": "deterministic", "value": 2}},
            {"from": "DC", "to": "R1", 
             "lead_time": {"type": "deterministic", "value": 1}},
            {"from": "DC", "to": "R2", 
             "lead_time": {"type": "deterministic", "value": 1}}
        ],
        "demand": [
            {"node": "R1", "generator": {"type": "deterministic", "value": 8}},
            {"node": "R2", "generator": {"type": "deterministic", "value": 7}}
        ]
    }
    
    net, dmap, T = build_from_config(cfg)
    sim = Simulator(net, dmap, T)
    results = sim.run()
    df = pd.DataFrame([r.__dict__ for r in results])
    
    # Verify review period adherence
    for node_id in ["R1", "R2"]:
        orders = df[df.node_id == node_id]["orders_to_parent"]
        for t in range(T):
            if t % 2 != 0:  # Non-review periods for retailers
                assert orders.iloc[t] == 0
    
    # Verify DC review period
    dc_orders = df[df.node_id == "DC"]["orders_to_parent"]
    for t in range(T):
        if t % 3 != 0:  # Non-review periods for DC
            assert dc_orders.iloc[t] == 0

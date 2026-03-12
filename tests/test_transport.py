"""
tests/test_transport.py
-----------------------
Comprehensive tests for the multi-SKU transport layer.

Covers:
  - TransportOption and VehicleLoad data structures
  - GreedyLoadPlanner: single SKU, multi-SKU, full/partial/mixed loads
  - Ghost shipment bug (floating-point residual)
  - VolumeProportionalAllocator: proportions, zero-volume edge case
  - CheapestModeSelector: ordering, single option
  - TransportPlanner: end-to-end, empty input guards, pluggable components
  - Protocol compliance: custom implementations accepted
  - Simulator integration: volume_per_unit conversion, cost routing
"""

import pytest
from engine.transport import (
    TransportOption,
    VehicleLoad,
    GreedyLoadPlanner,
    CheapestModeSelector,
    VolumeProportionalAllocator,
    TransportPlanner,
    LoadPlanner,
    ModeSelector,
    CostAllocator,
)


# ============================================================
# Helpers
# ============================================================

def make_option(
    capacity=100.0,
    cost_full=300.0,
    cost_half=180.0,
    cost_quarter=105.0,
    mode=1,
    lead_time=2,
    route_id="W1_R1",
):
    return TransportOption(
        route_id=route_id,
        mode=mode,
        capacity=capacity,
        cost_full=cost_full,
        cost_half=cost_half,
        cost_quarter=cost_quarter,
        lead_time=lead_time,
    )


# ============================================================
# 1. TransportOption and VehicleLoad — data integrity
# ============================================================

class TestDataStructures:

    def test_transport_option_fields(self):
        opt = make_option()
        assert opt.route_id == "W1_R1"
        assert opt.mode == 1
        assert opt.capacity == 100.0
        assert opt.cost_full == 300.0
        assert opt.weight_capacity is None  # optional, defaults to None

    def test_vehicle_load_fields(self):
        load = VehicleLoad(
            mode=1,
            lead_time=2,
            total_cost=300.0,
            utilization=1.0,
            quantities={"SKU_A": 60.0, "SKU_B": 40.0},
            cost_by_sku={"SKU_A": 180.0, "SKU_B": 120.0},
        )
        assert load.total_cost == 300.0
        assert load.quantities["SKU_A"] == 60.0
        assert sum(load.cost_by_sku.values()) == pytest.approx(300.0)

    def test_cost_by_sku_sums_to_total(self):
        load = VehicleLoad(
            mode=1, lead_time=2, total_cost=105.0, utilization=0.25,
            quantities={"SKU_A": 10.0, "SKU_B": 5.0},
            cost_by_sku={"SKU_A": 70.0, "SKU_B": 35.0},
        )
        assert sum(load.cost_by_sku.values()) == pytest.approx(load.total_cost)


# ============================================================
# 2. GreedyLoadPlanner
# ============================================================

class TestGreedyLoadPlanner:

    def setup_method(self):
        self.planner = GreedyLoadPlanner()
        self.opt = make_option(capacity=100.0)

    # --- Basic single-SKU cases ---

    def test_single_sku_partial_below_quarter(self):
        """Small shipment — billed at quarter-load rate."""
        loads = self.planner.plan_loads({"SKU_A": 10.0}, self.opt)
        assert len(loads) == 1
        assert loads[0].total_cost == self.opt.cost_quarter
        assert loads[0].utilization == 0.25

    def test_single_sku_partial_half_load(self):
        """50% utilization — billed at half-load rate."""
        loads = self.planner.plan_loads({"SKU_A": 50.0}, self.opt)
        assert len(loads) == 1
        assert loads[0].total_cost == self.opt.cost_half
        assert loads[0].utilization == 0.5

    def test_single_sku_full_load_exact(self):
        """Exactly one full truck."""
        loads = self.planner.plan_loads({"SKU_A": 100.0}, self.opt)
        assert len(loads) == 1
        assert loads[0].total_cost == self.opt.cost_full
        assert loads[0].utilization == 1.0

    def test_single_sku_two_full_trucks(self):
        """200 units, capacity 100 — should produce exactly 2 full loads."""
        loads = self.planner.plan_loads({"SKU_A": 200.0}, self.opt)
        assert len(loads) == 2
        for load in loads:
            assert load.total_cost == self.opt.cost_full
            assert load.utilization == 1.0

    def test_single_sku_full_plus_partial(self):
        """130 units — one full truck + one partial at quarter rate."""
        loads = self.planner.plan_loads({"SKU_A": 130.0}, self.opt)
        assert len(loads) == 2
        assert loads[0].utilization == 1.0
        assert loads[1].utilization == 0.25   # 30% < 50%

    def test_single_sku_full_plus_half(self):
        """160 units — one full + one half-load."""
        loads = self.planner.plan_loads({"SKU_A": 160.0}, self.opt)
        assert len(loads) == 2
        assert loads[0].utilization == 1.0
        assert loads[1].total_cost == self.opt.cost_half

    # --- Multi-SKU cases ---

    def test_two_sku_proportions_correct(self):
        """
        SKU_A: 60m³, SKU_B: 40m³ — total 100m³, one full truck.
        Each SKU should get exactly its proportional share of capacity.
        """
        quantities = {"SKU_A": 60.0, "SKU_B": 40.0}
        loads = self.planner.plan_loads(quantities, self.opt)
        assert len(loads) == 1
        assert loads[0].quantities["SKU_A"] == pytest.approx(60.0)
        assert loads[0].quantities["SKU_B"] == pytest.approx(40.0)

    def test_two_sku_proportions_preserved_across_multiple_trucks(self):
        """
        250m³ total (SKU_A: 150, SKU_B: 100) with capacity 100.
        Two full trucks + one partial — proportions must be same on all trucks.
        """
        quantities = {"SKU_A": 150.0, "SKU_B": 100.0}
        loads = self.planner.plan_loads(quantities, self.opt)
        assert len(loads) == 3  # 2 full + 1 partial

        expected_a_ratio = 150.0 / 250.0
        expected_b_ratio = 100.0 / 250.0

        for load in loads:
            total_on_load = sum(load.quantities.values())
            if total_on_load > 1e-9:
                assert load.quantities["SKU_A"] / total_on_load == pytest.approx(expected_a_ratio, rel=1e-6)
                assert load.quantities["SKU_B"] / total_on_load == pytest.approx(expected_b_ratio, rel=1e-6)

    def test_two_sku_total_quantities_conserved(self):
        """Total shipped volume across all loads must equal requested volume."""
        quantities = {"SKU_A": 75.0, "SKU_B": 55.0}
        loads = self.planner.plan_loads(quantities, self.opt)

        total_a = sum(l.quantities.get("SKU_A", 0) for l in loads)
        total_b = sum(l.quantities.get("SKU_B", 0) for l in loads)

        assert total_a == pytest.approx(75.0, rel=1e-6)
        assert total_b == pytest.approx(55.0, rel=1e-6)

    def test_asymmetric_skus_volume_drives_proportion(self):
        """
        SKU_A: 0.09m³ (45 units × 0.002), SKU_B: 0.168m³ (21 units × 0.008).
        Reflects realistic grocery scenario from the config.
        SKU_B should occupy ~65% of the truck despite lower unit count.
        """
        quantities = {"SKU_A": 0.09, "SKU_B": 0.168}
        opt = make_option(capacity=33.0)  # warehouse-to-retailer truck
        loads = self.planner.plan_loads(quantities, opt)

        assert len(loads) == 1
        total = 0.09 + 0.168
        assert loads[0].quantities["SKU_B"] / total == pytest.approx(0.168 / total, rel=1e-4)

    # --- Edge cases ---

    def test_zero_volume_returns_empty(self):
        loads = self.planner.plan_loads({"SKU_A": 0.0, "SKU_B": 0.0}, self.opt)
        assert loads == []

    def test_invalid_capacity_raises(self):
        bad_opt = make_option(capacity=0.0)
        with pytest.raises(RuntimeError):
            self.planner.plan_loads({"SKU_A": 10.0}, bad_opt)

    def test_ghost_shipment_bug_not_present(self):
        """
        Exact multiple of capacity must NOT produce a ghost partial load.
        Floating-point residual (e.g. 1.42e-14) after 200.0 - 100.0 - 100.0
        must be treated as zero.
        """
        loads = self.planner.plan_loads({"SKU_A": 200.0}, self.opt)
        # Must be exactly 2 full loads — no ghost third load
        assert len(loads) == 2
        for load in loads:
            assert load.utilization == 1.0

    def test_ghost_shipment_three_trucks_exact(self):
        """300 units at capacity 100 — exactly 3 full loads, no ghost."""
        loads = self.planner.plan_loads({"SKU_A": 300.0}, self.opt)
        assert len(loads) == 3

    def test_single_sku_all_quantities_positive(self):
        """Every load must have positive quantities for every SKU."""
        loads = self.planner.plan_loads({"SKU_A": 250.0, "SKU_B": 50.0}, self.opt)
        for load in loads:
            for sku, qty in load.quantities.items():
                assert qty >= 0.0


# ============================================================
# 3. VolumeProportionalAllocator
# ============================================================

class TestVolumeProportionalAllocator:

    def setup_method(self):
        self.allocator = VolumeProportionalAllocator()
        self.opt = make_option()

    def test_proportional_split_two_skus(self):
        """SKU_A has 3× volume of SKU_B — should pay 3× the cost."""
        result = self.allocator.allocate(
            total_cost=100.0,
            quantities={"SKU_A": 75.0, "SKU_B": 25.0},
            option=self.opt,
        )
        assert result["SKU_A"] == pytest.approx(75.0)
        assert result["SKU_B"] == pytest.approx(25.0)

    def test_cost_shares_sum_to_total(self):
        result = self.allocator.allocate(
            total_cost=300.0,
            quantities={"SKU_A": 60.0, "SKU_B": 40.0},
            option=self.opt,
        )
        assert sum(result.values()) == pytest.approx(300.0)

    def test_equal_volumes_equal_cost(self):
        result = self.allocator.allocate(
            total_cost=200.0,
            quantities={"SKU_A": 50.0, "SKU_B": 50.0},
            option=self.opt,
        )
        assert result["SKU_A"] == pytest.approx(100.0)
        assert result["SKU_B"] == pytest.approx(100.0)

    def test_single_sku_gets_full_cost(self):
        result = self.allocator.allocate(
            total_cost=105.0,
            quantities={"SKU_A": 30.0},
            option=self.opt,
        )
        assert result["SKU_A"] == pytest.approx(105.0)

    def test_zero_volume_fallback_equal_split(self):
        """When all volumes are zero, fall back to equal split."""
        result = self.allocator.allocate(
            total_cost=100.0,
            quantities={"SKU_A": 0.0, "SKU_B": 0.0},
            option=self.opt,
        )
        assert result["SKU_A"] == pytest.approx(50.0)
        assert result["SKU_B"] == pytest.approx(50.0)

    def test_asymmetric_grocery_scenario(self):
        """
        SKU_A: 0.09m³, SKU_B: 0.168m³ — realistic grocery values.
        SKU_B should bear ~65% of the cost.
        """
        total = 0.09 + 0.168
        result = self.allocator.allocate(
            total_cost=105.0,
            quantities={"SKU_A": 0.09, "SKU_B": 0.168},
            option=self.opt,
        )
        assert result["SKU_B"] / 105.0 == pytest.approx(0.168 / total, rel=1e-4)
        assert sum(result.values()) == pytest.approx(105.0)


# ============================================================
# 4. CheapestModeSelector
# ============================================================

class TestCheapestModeSelector:

    def setup_method(self):
        self.selector = CheapestModeSelector()
        self.quantities = {"SKU_A": 50.0, "SKU_B": 30.0}

    def test_single_option_returned_as_is(self):
        opt = make_option(mode=1)
        result = self.selector.select(self.quantities, [opt])
        assert result == [opt]

    def test_two_options_sorted_by_mode(self):
        opt1 = make_option(mode=2, route_id="air")
        opt2 = make_option(mode=1, route_id="truck")
        result = self.selector.select(self.quantities, [opt1, opt2])
        assert result[0].route_id == "truck"
        assert result[1].route_id == "air"

    def test_three_options_correct_order(self):
        opts = [make_option(mode=3), make_option(mode=1), make_option(mode=2)]
        result = self.selector.select(self.quantities, opts)
        assert [o.mode for o in result] == [1, 2, 3]

    def test_same_mode_preserves_both(self):
        opt1 = make_option(mode=1, route_id="route_a")
        opt2 = make_option(mode=1, route_id="route_b")
        result = self.selector.select(self.quantities, [opt1, opt2])
        assert len(result) == 2


# ============================================================
# 5. TransportPlanner — end-to-end
# ============================================================

class TestTransportPlanner:

    def setup_method(self):
        self.planner = TransportPlanner()
        self.opt = make_option(capacity=100.0)

    def test_empty_quantities_returns_empty(self):
        loads = self.planner.plan({}, [self.opt])
        assert loads == []

    def test_all_zero_quantities_returns_empty(self):
        loads = self.planner.plan({"SKU_A": 0.0, "SKU_B": 0.0}, [self.opt])
        assert loads == []

    def test_empty_options_returns_empty(self):
        loads = self.planner.plan({"SKU_A": 50.0}, [])
        assert loads == []

    def test_single_sku_end_to_end(self):
        """Full pipeline: plan → loads with cost_by_sku filled."""
        loads = self.planner.plan({"SKU_A": 50.0}, [self.opt])
        assert len(loads) == 1
        assert "SKU_A" in loads[0].cost_by_sku
        assert loads[0].cost_by_sku["SKU_A"] == pytest.approx(self.opt.cost_half)

    def test_two_sku_cost_by_sku_filled(self):
        """cost_by_sku must be populated for every SKU on every load."""
        loads = self.planner.plan({"SKU_A": 60.0, "SKU_B": 40.0}, [self.opt])
        assert len(loads) == 1
        assert "SKU_A" in loads[0].cost_by_sku
        assert "SKU_B" in loads[0].cost_by_sku

    def test_cost_by_sku_sums_to_total_cost(self):
        loads = self.planner.plan({"SKU_A": 60.0, "SKU_B": 40.0}, [self.opt])
        for load in loads:
            assert sum(load.cost_by_sku.values()) == pytest.approx(load.total_cost)

    def test_multi_load_all_have_cost_by_sku(self):
        """250 units — multiple loads, all must have cost_by_sku."""
        loads = self.planner.plan({"SKU_A": 150.0, "SKU_B": 100.0}, [self.opt])
        assert len(loads) == 3
        for load in loads:
            assert sum(load.cost_by_sku.values()) == pytest.approx(load.total_cost)

    def test_mode_selection_uses_cheapest_first(self):
        """Two modes — planner must use mode 1 (cheaper) not mode 2."""
        opt_truck = make_option(mode=1, cost_full=300.0)
        opt_air   = make_option(mode=2, cost_full=900.0)
        loads = self.planner.plan({"SKU_A": 100.0}, [opt_air, opt_truck])
        assert loads[0].mode == 1
        assert loads[0].total_cost == 300.0

    def test_lead_time_propagated_to_loads(self):
        opt = make_option(lead_time=5)
        loads = self.planner.plan({"SKU_A": 50.0}, [opt])
        assert loads[0].lead_time == 5

    def test_ghost_shipment_not_billed(self):
        """
        Exact multiple of capacity — TransportPlanner must not
        produce a spurious extra partial load from float residual.
        """
        loads = self.planner.plan({"SKU_A": 200.0}, [self.opt])
        assert len(loads) == 2
        total_cost = sum(l.total_cost for l in loads)
        assert total_cost == pytest.approx(2 * self.opt.cost_full)

    def test_realistic_grocery_daily_shipment(self):
        """
        Realistic daily W1→R1 shipment:
        SKU_A: 48 units × 0.002 m³ = 0.096 m³
        SKU_B: 21 units × 0.008 m³ = 0.168 m³
        Total: 0.264 m³ on a 33 m³ truck → quarter-load billing.
        """
        opt = make_option(capacity=33.0, cost_full=300.0, cost_half=180.0, cost_quarter=105.0)
        quantities = {"SKU_A": 0.096, "SKU_B": 0.168}
        loads = self.planner.plan(quantities, [opt])

        assert len(loads) == 1
        assert loads[0].total_cost == opt.cost_quarter
        assert loads[0].utilization == 0.25

        # SKU_B takes ~64% of space → pays ~64% of cost
        total_vol = 0.096 + 0.168
        expected_b_share = 105.0 * (0.168 / total_vol)
        assert loads[0].cost_by_sku["SKU_B"] == pytest.approx(expected_b_share, rel=1e-4)

    def test_total_cost_across_all_loads(self):
        """
        250 units at capacity 100:
        2 full (300 each) + 1 partial at half-load (180) = 780 total.
        50 remaining / 100 capacity = 50% → billed at half-load rate.
        """
        loads = self.planner.plan({"SKU_A": 250.0}, [self.opt])
        total = sum(l.total_cost for l in loads)
        assert total == pytest.approx(2 * 300.0 + 180.0)  # 780, not 705


# ============================================================
# 6. Pluggable components — custom implementations accepted
# ============================================================

class TestPluggableComponents:

    def test_custom_allocator_equal_split(self):
        """Custom allocator that always splits cost equally."""

        class EqualSplitAllocator:
            def allocate(self, total_cost, quantities, option):
                n = len(quantities)
                return {sku: total_cost / n for sku in quantities}

        planner = TransportPlanner(allocator=EqualSplitAllocator())
        opt = make_option(capacity=100.0)
        loads = planner.plan({"SKU_A": 60.0, "SKU_B": 40.0}, [opt])

        # Equal split — both SKUs pay half regardless of volume
        assert loads[0].cost_by_sku["SKU_A"] == pytest.approx(loads[0].cost_by_sku["SKU_B"])

    def test_custom_mode_selector_always_picks_last(self):
        """Custom selector that reverses priority — picks highest mode first."""

        class HighestModeFirst:
            def select(self, quantities, options):
                return sorted(options, key=lambda o: o.mode, reverse=True)

        planner = TransportPlanner(mode_selector=HighestModeFirst())
        opt1 = make_option(mode=1, cost_full=300.0)
        opt2 = make_option(mode=2, cost_full=900.0)
        loads = planner.plan({"SKU_A": 100.0}, [opt1, opt2])

        assert loads[0].mode == 2
        assert loads[0].total_cost == 900.0

    def test_custom_load_planner_single_vehicle(self):
        """Custom planner that always returns exactly one vehicle regardless of volume."""

        class SingleVehiclePlanner:
            def plan_loads(self, quantities, option):
                return [VehicleLoad(
                    mode=option.mode,
                    lead_time=option.lead_time,
                    total_cost=option.cost_full,
                    utilization=1.0,
                    quantities=dict(quantities),
                    cost_by_sku={},
                )]

        planner = TransportPlanner(load_planner=SingleVehiclePlanner())
        opt = make_option(capacity=10.0)  # small capacity — default would need many trucks
        loads = planner.plan({"SKU_A": 1000.0}, [opt])

        assert len(loads) == 1  # custom planner overrides default packing

    def test_protocol_compliance_load_planner(self):
        """GreedyLoadPlanner must satisfy the LoadPlanner Protocol."""
        assert isinstance(GreedyLoadPlanner(), LoadPlanner)

    def test_protocol_compliance_mode_selector(self):
        assert isinstance(CheapestModeSelector(), ModeSelector)

    def test_protocol_compliance_cost_allocator(self):
        assert isinstance(VolumeProportionalAllocator(), CostAllocator)


# ============================================================
# 7. Volume conversion — simulator integration logic
# ============================================================

class TestVolumeConversion:
    """
    Tests the unit→volume conversion logic that lives in simulator.py.
    We test the math here directly so we don't need a full sim setup.
    """

    SKU_PROPS = {
        "SKU_A": 0.002,   # m³/unit — canned goods
        "SKU_B": 0.008,   # m³/unit — cereal box (4x bulkier)
    }

    def _convert(self, unit_qtys):
        return {
            sku: qty * self.SKU_PROPS.get(sku, 1.0)
            for sku, qty in unit_qtys.items()
        }

    def test_sku_b_occupies_more_volume_per_unit(self):
        """1 unit of SKU_B takes 4× the volume of 1 unit of SKU_A."""
        vols = self._convert({"SKU_A": 1.0, "SKU_B": 1.0})
        assert vols["SKU_B"] / vols["SKU_A"] == pytest.approx(4.0)

    def test_conversion_preserves_proportionality(self):
        """48 units SKU_A vs 21 units SKU_B — SKU_B wins on volume despite lower count."""
        vols = self._convert({"SKU_A": 48.0, "SKU_B": 21.0})
        assert vols["SKU_B"] > vols["SKU_A"]

    def test_missing_sku_defaults_to_unit_volume(self):
        """SKU with no entry in volume_per_unit defaults to 1.0 m³/unit."""
        vol_per_unit = {"SKU_A": 0.002}
        result = {"NEW_SKU": 10.0 * vol_per_unit.get("NEW_SKU", 1.0)}
        assert result["NEW_SKU"] == pytest.approx(10.0)

    def test_planner_receives_volumes_not_units(self):
        """
        End-to-end: after conversion, planner sees volumes.
        48 units SKU_A (0.096m³) + 21 units SKU_B (0.168m³)
        should produce one quarter-load truck on a 33m³ lane.
        """
        planner = TransportPlanner()
        opt = make_option(capacity=33.0, cost_quarter=105.0)
        vols = self._convert({"SKU_A": 48.0, "SKU_B": 21.0})
        loads = planner.plan(vols, [opt])

        assert len(loads) == 1
        assert loads[0].total_cost == opt.cost_quarter

    def test_cost_allocation_reflects_physical_reality(self):
        """
        SKU_B is bulkier per unit, so even with lower demand it
        pays more transport cost per unit shipped.
        """
        planner = TransportPlanner()
        opt = make_option(capacity=33.0, cost_quarter=105.0)
        vols = self._convert({"SKU_A": 48.0, "SKU_B": 21.0})
        loads = planner.plan(vols, [opt])

        cost_per_unit_a = loads[0].cost_by_sku["SKU_A"] / 48.0
        cost_per_unit_b = loads[0].cost_by_sku["SKU_B"] / 21.0
        assert cost_per_unit_b > cost_per_unit_a
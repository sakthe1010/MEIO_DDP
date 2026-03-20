from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, runtime_checkable


# ============================================================
# Core data structures
# ============================================================

@dataclass
class TransportOption:
    route_id: str
    mode: int
    capacity: float                      # volume capacity (m³ or generic units)
    cost_full: float
    cost_half: float
    cost_quarter: float
    lead_time: int
    weight_capacity: Optional[float] = None   # kg cap; None = no weight constraint
    min_dispatch_utilization: float = 0.0  # 0.0 = always dispatch


@dataclass
class VehicleLoad:
    """One dispatched vehicle carrying multiple SKUs."""
    mode: int
    lead_time: int
    total_cost: float
    utilization: float                        # 0.0 – 1.0, volume-based
    quantities: Dict[str, float]              # sku -> qty shipped on this vehicle
    cost_by_sku: Dict[str, float]             # sku -> allocated cost share


# ============================================================
# Pluggable interfaces (Protocols)
# ============================================================

@runtime_checkable
class LoadPlanner(Protocol):
    """
    Given a bundle of SKU quantities and one vehicle option,
    return a list of VehicleLoads that serve as much of the
    bundle as possible.

    Users can implement this to add custom packing logic
    (e.g. hazmat segregation, temperature zones, axle limits).
    """
    def plan_loads(
        self,
        quantities: Dict[str, float],       # sku -> total volume needed
        option: TransportOption,
    ) -> List[VehicleLoad]: ...


@runtime_checkable
class ModeSelector(Protocol):
    """
    Given multiple transport options for a lane, pick which
    one(s) to use. Default: cheapest feasible mode first.

    Users can override to implement: split shipments across
    modes, urgency-based air vs. truck decisions, etc.
    """
    def select(
        self,
        quantities: Dict[str, float],
        options: List[TransportOption],
    ) -> List[TransportOption]: ...          # ordered list of options to try


@runtime_checkable
class CostAllocator(Protocol):
    """
    Given a vehicle's total cost and what's on it,
    split cost back to each SKU.

    Default: proportional to volume consumed.
    Users can override: weight-proportional, equal-split, etc.
    """
    def allocate(
        self,
        total_cost: float,
        quantities: Dict[str, float],       # sku -> qty on this vehicle
        option: TransportOption,
    ) -> Dict[str, float]: ...              # sku -> cost share


# ============================================================
# Default implementations
# ============================================================

class GreedyLoadPlanner:
    """
    Default load planner.
    - Packs SKUs proportionally to their volume share.
    - Full vehicles first, then partial with tiered billing.
    - Always ships (carrier charges minimum quarter-load).
    """

    def plan_loads(
        self,
        quantities: Dict[str, float],
        option: TransportOption,
    ) -> List[VehicleLoad]:

        C = option.capacity
        if C <= 0:
            raise RuntimeError(
                f"Invalid capacity {C} for route {option.route_id}"
            )

        total_volume = sum(quantities.values())
        if total_volume <= 0:
            return []

        # SKU volume proportions — fixed for all vehicles on this lane
        proportions = {
            sku: vol / total_volume
            for sku, vol in quantities.items()
        }

        loads: List[VehicleLoad] = []
        remaining_vol = total_volume

        # --- Full vehicles ---
        while remaining_vol >= C:
            qty_this = {
                sku: proportions[sku] * C
                for sku in quantities
            }
            loads.append(
                VehicleLoad(
                    mode=option.mode,
                    lead_time=option.lead_time,
                    total_cost=option.cost_full,
                    utilization=1.0,
                    quantities=qty_this,
                    cost_by_sku={},          # filled by allocator
                )
            )
            remaining_vol -= C

        # --- Partial vehicle ---
        if remaining_vol > 1e-9:
            util = remaining_vol / C

            if util >= 0.5:
                cost = option.cost_half
                util_bucket = 0.5
            else:
                # quarter-load minimum billing
                cost = option.cost_quarter
                util_bucket = 0.25

            qty_this = {
                sku: proportions[sku] * remaining_vol
                for sku in quantities
            }
            loads.append(
                VehicleLoad(
                    mode=option.mode,
                    lead_time=option.lead_time,
                    total_cost=cost,
                    utilization=util_bucket,
                    quantities=qty_this,
                    cost_by_sku={},
                )
            )

        return loads


class CheapestModeSelector:
    """
    Default mode selector.
    Tries modes in ascending order (mode=1 preferred).
    First mode that can carry any volume is used exclusively.
    """

    def select(
        self,
        quantities: Dict[str, float],
        options: List[TransportOption],
    ) -> List[TransportOption]:
        return sorted(options, key=lambda o: o.mode)


class VolumeProportionalAllocator:
    """
    Default cost allocator.
    Each SKU pays proportional to the volume it occupies.
    """

    def allocate(
        self,
        total_cost: float,
        quantities: Dict[str, float],
        option: TransportOption,
    ) -> Dict[str, float]:

        total_vol = sum(quantities.values())
        if total_vol <= 0:
            n = len(quantities)
            return {sku: total_cost / n for sku in quantities}

        return {
            sku: total_cost * (vol / total_vol)
            for sku, vol in quantities.items()
        }


# ============================================================
# TransportPlanner — orchestrates the three components
# ============================================================

class TransportPlanner:
    """
    Orchestrates load planning, mode selection, and cost allocation.

    All three components are pluggable. Pass your own implementations
    to customize behaviour for your industry / network.

    Usage (default):
        planner = TransportPlanner()
        loads = planner.plan({"SKU_A": 120.0, "SKU_B": 60.0}, options)

    Usage (custom allocator):
        planner = TransportPlanner(allocator=WeightProportionalAllocator())
        loads = planner.plan(quantities, options)
    """

    def __init__(
        self,
        load_planner: Optional[LoadPlanner] = None,
        mode_selector: Optional[ModeSelector] = None,
        allocator: Optional[CostAllocator] = None,
    ):
        self.load_planner = load_planner or GreedyLoadPlanner()
        self.mode_selector = mode_selector or CheapestModeSelector()
        self.allocator = allocator or VolumeProportionalAllocator()

    def plan(
        self,
        quantities: Dict[str, float],      # sku -> volume needed
        options: List[TransportOption],
    ) -> List[VehicleLoad]:
        """
        Plan all vehicles needed to move `quantities` across this lane.
        Returns a list of VehicleLoad, each with cost_by_sku filled in.
        """

        if not quantities or all(v <= 0 for v in quantities.values()):
            return []

        if not options:
            return []

        ordered_options = self.mode_selector.select(quantities, options)

        for option in ordered_options:
            loads = self.load_planner.plan_loads(quantities, option)
            if loads:
                # Fill cost_by_sku for every load
                for load in loads:
                    load.cost_by_sku = self.allocator.allocate(
                        load.total_cost,
                        load.quantities,
                        option,
                    )
                return loads

        return []
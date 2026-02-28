from dataclasses import dataclass
from typing import List


@dataclass
class TransportOption:
    route_id: str
    mode: int
    capacity: float          # volume capacity
    cost_full: float
    cost_half: float
    cost_quarter: float
    lead_time: int


@dataclass
class PlannedShipment:
    qty: float
    mode: int
    cost: float
    lead_time: int
    utilization: float


class TransportPlanner:
    """
    Phase-1 transport planner:
    - deterministic
    - single SKU (volume = units)
    - minimum quarter-load
    - mode priority (lower mode preferred)
    """

    MIN_UTIL = 0.25

    def __init__(self, policy: str = "MIN_QUARTER_CONSOLIDATE"):
        self.policy = policy

    def plan(
        self,
        requested_volume: float,
        options: List[TransportOption],
    ) -> List[PlannedShipment]:

        if requested_volume <= 0:
            return []

        options = sorted(options, key=lambda x: x.mode)

        for opt in options:
            shipments = self._plan_single_option(requested_volume, opt)
            if shipments:
                return shipments

        return []

    def _plan_single_option(
        self,
        requested_volume: float,
        opt: TransportOption,
    ) -> List[PlannedShipment]:

        C = opt.capacity
        if C <= 0:
            raise RuntimeError(f"Invalid transport capacity: {C} for route {opt.route_id}")

        if requested_volume <= 0:
            return []

        shipments: List[PlannedShipment] = []
        remaining = requested_volume

        # Full vehicles first
        while remaining >= C:
            shipments.append(
                PlannedShipment(
                    qty=C,
                    mode=opt.mode,
                    cost=opt.cost_full,
                    lead_time=opt.lead_time,
                    utilization=1.0,
                )
            )
            remaining -= C

        # Partial vehicle — always ship, charge appropriate tier
        if remaining > 0:
            util = remaining / C

            if util >= 0.5:
                cost = opt.cost_half
                util_bucket = 0.5
            elif util >= 0.25:
                cost = opt.cost_quarter
                util_bucket = 0.25
            else:
                # Below quarter-load: charge quarter rate (minimum billing unit)
                # but ALWAYS ship — carrier charges minimum, doesn't refuse goods
                cost = opt.cost_quarter
                util_bucket = 0.25

            shipments.append(
                PlannedShipment(
                    qty=remaining,
                    mode=opt.mode,
                    cost=cost,
                    lead_time=opt.lead_time,
                    utilization=util_bucket,
                )
            )

        return shipments


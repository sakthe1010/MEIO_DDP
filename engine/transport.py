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
        
        # return []

        if requested_volume <= 0:
            return []

        # deterministic: lowest mode first
        options = sorted(options, key=lambda x: x.mode)

        for opt in options:
            shipments = self._plan_single_option(requested_volume, opt)
            if shipments:
                return shipments

        # no feasible transport -> delay shipment
        return []

    def _plan_single_option(
        self,
        requested_volume: float,
        opt: TransportOption,
    ) -> List[PlannedShipment]:

        C = opt.capacity
        if C <= 0:
            raise RuntimeError(f"Invalid transport capacity: {C} for route {opt.route_id}")

        shipments: List[PlannedShipment] = []

        # minimum feasible shipment
        if requested_volume < self.MIN_UTIL * C:
            return []

        remaining = requested_volume

        # full vehicles
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

        # partial vehicle
        if remaining > 0:
            util = remaining / C

            if util >= 1.0:
                cost = opt.cost_full
                util_bucket = 1.0
            elif util >= 0.5:
                cost = opt.cost_half
                util_bucket = 0.5
            elif util >= 0.25:
                cost = opt.cost_quarter
                util_bucket = 0.25
            else:
                return shipments  # consolidate remainder

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

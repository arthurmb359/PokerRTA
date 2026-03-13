from dataclasses import dataclass


@dataclass(frozen=True)
class DebugStateSnapshot:
    sb_bet: str = "-"
    bb_bet: str = "-"
    pot: str = "-"
    board: str = "-"


@dataclass(frozen=True)
class DebugUpdateSnapshot:
    state: DebugStateSnapshot
    regions: dict

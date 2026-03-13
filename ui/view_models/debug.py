from dataclasses import dataclass


@dataclass(frozen=True)
class DebugStateSnapshot:
    position_bets: dict[str, str]
    street: str = "-"
    pot: str = "-"
    board: str = "-"


@dataclass(frozen=True)
class DebugUpdateSnapshot:
    state: DebugStateSnapshot
    regions: dict

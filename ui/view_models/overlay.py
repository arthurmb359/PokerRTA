from dataclasses import dataclass


@dataclass(frozen=True)
class OverlayCategorySnapshot:
    category: str
    label_prefix: str
    regions: tuple[tuple[int, int, int, int], ...]


@dataclass(frozen=True)
class OverlayViewSnapshot:
    platform: str
    game_format: str
    table_left: int
    table_top: int
    categories: tuple[OverlayCategorySnapshot, ...]


@dataclass(frozen=True)
class OverlayUpdateSnapshot:
    category: str
    regions: tuple[tuple[int, int, int, int], ...]

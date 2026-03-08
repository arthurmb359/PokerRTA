def relative_to_absolute_region(left: int, top: int, rel_region: list[int]) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = rel_region
    width = max(1, x2 - x1)
    height = max(1, y2 - y1)
    return (
        int(left + x1),
        int(top + y1),
        int(width),
        int(height),
    )


def relative_to_absolute_corners(left: int, top: int, rel_region: list[int]) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = rel_region
    return (
        int(left + x1),
        int(top + y1),
        int(left + x2),
        int(top + y2),
    )


def absolute_corners_to_relative(left: int, top: int, corners: tuple[float, float, float, float]) -> list[int]:
    x1, y1, x2, y2 = corners
    return [
        int(round(x1 - left)),
        int(round(y1 - top)),
        int(round(x2 - left)),
        int(round(y2 - top)),
    ]

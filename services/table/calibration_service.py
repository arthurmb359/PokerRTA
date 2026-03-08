from configs.config_manager import get_regions_category, set_calibration_category


def update_calibration_region(
    platform: str,
    game_format: str,
    category: str,
    index: int,
    rel_region: list[int],
) -> list[list[int]]:
    regions = get_regions_category(platform, game_format, category)
    if index < len(regions):
        regions[index] = rel_region
        set_calibration_category(platform, game_format, category, regions)
    return regions


def apply_runtime_regions(
    category: str,
    regions: list[list[int]],
    players,
    to_absolute_region,
    pot_regions_abs: list[tuple[int, int, int, int]],
    board_regions_abs: list[tuple[int, int, int, int]],
):
    if category == "bet":
        for i, rel in enumerate(regions):
            if i >= len(players):
                break
            players[i].bet_region = to_absolute_region(rel)
        return pot_regions_abs, board_regions_abs, "bet"

    if category == "pot":
        return [to_absolute_region(r) for r in regions], board_regions_abs, "pot"

    if category == "board":
        return pot_regions_abs, [to_absolute_region(r) for r in regions], "board"

    return pot_regions_abs, board_regions_abs, None


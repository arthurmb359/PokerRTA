from dataclasses import dataclass

from configs.config_manager import (
    get_active_selection,
    get_game_tick_rate,
    get_platform_assets,
    get_regions_category,
    get_seat_centers,
    load_config,
)
from domain.player import Player
from services.runtime.game_session import GameSession
from services.table.region_mapper import relative_to_absolute_region
from services.table.table_scrapper import TableScrapper


@dataclass
class GameSessionSetup:
    config: dict
    platform: str
    game_format: str
    debug_mode: bool
    dealer_image: str
    tick_rate_sec: float
    table: TableScrapper
    players: list[Player]
    pot_regions_rel: list[list[int]]
    board_regions_rel: list[list[int]]
    pot_regions_abs: list[tuple[int, int, int, int]]
    board_regions_abs: list[tuple[int, int, int, int]]


class GameSessionBuilder:
    @staticmethod
    def _to_absolute_region(table: TableScrapper, rel_region: list[int]) -> tuple[int, int, int, int]:
        return relative_to_absolute_region(
            table.get_left_edge(),
            table.get_top_edge(),
            rel_region,
        )

    def build(self, platform=None, game_format=None, debug_mode=False) -> GameSession:
        config = load_config()
        selected_platform, selected_format = get_active_selection(config)
        platform = platform or selected_platform
        game_format = game_format or selected_format

        assets = get_platform_assets(platform)
        table = TableScrapper(platform=platform, anchor_image=assets["anchor_image"])

        seat_centers = get_seat_centers(game_format)
        bet_regions_rel = get_regions_category(platform, game_format, "bet", config)
        pot_regions_rel = get_regions_category(platform, game_format, "pot", config)
        board_regions_rel = get_regions_category(platform, game_format, "board", config)

        if len(bet_regions_rel) < len(seat_centers):
            raise ValueError(
                f"Calibration missing for {platform}/{game_format}. "
                f"Expected {len(seat_centers)} bet regions, got {len(bet_regions_rel)}."
            )

        players = []
        for i, center in enumerate(seat_centers):
            rel = bet_regions_rel[i]
            region_abs = self._to_absolute_region(table, rel)
            player = Player(
                table.get_left_edge() + center[0],
                table.get_top_edge() + center[1],
                region_abs,
            )
            players.append(player)

        pot_regions_abs = [self._to_absolute_region(table, r) for r in pot_regions_rel]
        board_regions_abs = [self._to_absolute_region(table, r) for r in board_regions_rel]

        setup = GameSessionSetup(
            config=config,
            platform=platform,
            game_format=game_format,
            debug_mode=bool(debug_mode),
            dealer_image=assets["dealer_image"],
            tick_rate_sec=get_game_tick_rate(config),
            table=table,
            players=players,
            pot_regions_rel=pot_regions_rel,
            board_regions_rel=board_regions_rel,
            pot_regions_abs=pot_regions_abs,
            board_regions_abs=board_regions_abs,
        )
        return GameSession(setup=setup)

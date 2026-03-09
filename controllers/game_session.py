import time

import pyautogui

from configs.config_manager import set_game_tick_rate
from services.table.calibration_service import apply_runtime_regions
from services.table.region_mapper import relative_to_absolute_region
from services.table.table_analyzer import TableAnalyzer
from services.table.table_scrapper import TableScrapper


class GameSession:

    def __init__(self, setup):
        self.config = setup.config
        self.platform = setup.platform
        self.game_format = setup.game_format
        self.debug_mode = setup.debug_mode
        self.running = True

        self.dealer_image = setup.dealer_image

        self.button_pos = 0
        self.btn_img_pos = 0
        self.dealer_miss_count = 0
        self.table_analyzer = TableAnalyzer()

        self.paused = False
        self.tick_rate_sec = setup.tick_rate_sec
        self.last_game_state = {
            "sb_bet": "-",
            "bb_bet": "-",
            "pot": "-",
            "board": "-",
        }
        self.latest_region_images = {}

        self.table = setup.table
        self.list = setup.players
        self.pot_regions_rel = setup.pot_regions_rel
        self.board_regions_rel = setup.board_regions_rel
        self.pot_regions_abs = setup.pot_regions_abs
        self.board_regions_abs = setup.board_regions_abs

        self.screenlist = [None] * len(self.list)
        self.last_raw_screenlist = [None] * len(self.list)

        self.overlay = None
        self.debug_window = None

        print(f"[Game] platform={self.platform} format={self.game_format} players={len(self.list)}")
        print(f"[Game] dealer_image={self.dealer_image}")

    def attach_ui(self, overlay=None, debug_window=None):
        self.overlay = overlay
        self.debug_window = debug_window

    def _set_paused(self, paused: bool):
        self.paused = bool(paused)
        print(f"[Debug] paused={self.paused}")

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        self.running = False
        self.paused = False

    def _set_tick_rate(self, value: float):
        self.tick_rate_sec = float(value)
        set_game_tick_rate(self.tick_rate_sec)
        print(f"[Debug] tick_rate_sec={self.tick_rate_sec}")

    def to_absolute_region(self, rel_region):
        return relative_to_absolute_region(
            self.table.get_left_edge(),
            self.table.get_top_edge(),
            rel_region,
        )

    def start(self) -> None:
        while self.running:
            if self.paused:
                time.sleep(0.1)
                continue

            self.get_button_pos()
            if not self.running:
                break
            self.get_table_state()
            if not self.running:
                break
            if self.debug_window is not None:
                state_snapshot = dict(self.last_game_state)
                regions_snapshot = {
                    key: (img.copy() if img is not None else None)
                    for key, img in self.latest_region_images.items()
                }
                self.debug_window.push_update(state_snapshot, regions_snapshot)
            time.sleep(self.tick_rate_sec)

    def _on_overlay_update(self, category, regions):
        self.pot_regions_abs, self.board_regions_abs, updated_category = apply_runtime_regions(
            category=category,
            regions=regions,
            players=self.list,
            to_absolute_region=self.to_absolute_region,
            pot_regions_abs=self.pot_regions_abs,
            board_regions_abs=self.board_regions_abs,
        )
        if updated_category is not None:
            print(f"[Overlay] {updated_category} regions refreshed in running game")

    def get_table_state(self):
        state, region_images = self.table_analyzer.extract_table_state(
            players=self.list,
            button_pos=self.button_pos,
            pot_regions_abs=self.pot_regions_abs,
            board_regions_abs=self.board_regions_abs,
            overlay=self.overlay,
            previous_state=self.last_game_state,
        )
        self.last_game_state = state
        self.latest_region_images = region_images

    def get_button_pos(self):
        self.button_pos, self.btn_img_pos, self.dealer_miss_count = self.table_analyzer.update_button_position(
            table=self.table,
            dealer_image=self.dealer_image,
            players=self.list,
            btn_img_pos=self.btn_img_pos,
            button_pos=self.button_pos,
            dealer_miss_count=self.dealer_miss_count,
        )

    @staticmethod
    def mouse_pos():
        table = TableScrapper()
        print(f" Table Edge Location - Left: '{table.get_left_edge()}' - Top: '{table.get_top_edge()}'")
        x, y = pyautogui.position()
        print(f" Mouse Location - {x, y}")


# Backward-compatible alias for incremental migration.
Game = GameSession

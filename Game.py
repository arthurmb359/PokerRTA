import time

import cv2
import numpy as np
import pyautogui
from PIL import Image
from paddleocr import PaddleOCR

from Player import Player
from TableScrapper import TableScrapper
from ui.overlay import CalibrationOverlay
from ui.debug_ui import DebugWindow
from configs.config_manager import (
    get_active_selection,
    get_game_tick_rate,
    get_platform_assets,
    get_regions_category,
    get_seat_centers,
    load_config,
    set_game_tick_rate,
)


class Game:

    def __init__(self, platform=None, game_format=None, debug_mode=False):
        self.config = load_config()
        selected_platform, selected_format = get_active_selection(self.config)
        self.platform = platform or selected_platform
        self.game_format = game_format or selected_format
        self.debug_mode = bool(debug_mode)
        self.running = True
        self.return_action = "exit_app"

        assets = get_platform_assets(self.platform)
        self.dealer_image = assets["dealer_image"]

        self.ocr = PaddleOCR(lang="en", use_textline_orientation=False)
        self.screenshot = None
        self.button_pos = 0
        self.btn_img_pos = 0
        self.dealer_miss_count = 0

        self.paused = False
        self.tick_rate_sec = get_game_tick_rate(self.config)
        self.last_game_state = {
            "sb_bet": "-",
            "bb_bet": "-",
            "pot": "-",
            "board": "-",
        }
        self.latest_region_images = {}

        self.table = TableScrapper(platform=self.platform, anchor_image=assets["anchor_image"])

        seat_centers = get_seat_centers(self.game_format)
        bet_regions_rel = get_regions_category(self.platform, self.game_format, "bet", self.config)
        self.pot_regions_rel = get_regions_category(self.platform, self.game_format, "pot", self.config)
        self.board_regions_rel = get_regions_category(self.platform, self.game_format, "board", self.config)

        if len(bet_regions_rel) < len(seat_centers):
            raise ValueError(
                f"Calibration missing for {self.platform}/{self.game_format}. "
                f"Expected {len(seat_centers)} bet regions, got {len(bet_regions_rel)}."
            )

        self.list = []
        for i, center in enumerate(seat_centers):
            rel = bet_regions_rel[i]
            region_abs = self.to_absolute_region(rel)
            player = Player(
                self.table.get_left_edge() + center[0],
                self.table.get_top_edge() + center[1],
                region_abs,
            )
            self.list.append(player)

        self.pot_regions_abs = [self.to_absolute_region(r) for r in self.pot_regions_rel]
        self.board_regions_abs = [self.to_absolute_region(r) for r in self.board_regions_rel]

        self.screenlist = [None] * len(self.list)
        self.last_raw_screenlist = [None] * len(self.list)

        self.overlay = CalibrationOverlay(
            self.platform,
            self.game_format,
            self.table.get_left_edge(),
            self.table.get_top_edge(),
            on_update=self._on_overlay_update,
        )
        self.overlay.start()

        self.debug_window = None
        if self.debug_mode:
            self.debug_window = DebugWindow(
                on_pause_changed=self._set_paused,
                on_tick_rate_changed=self._set_tick_rate,
                on_back_to_main=self._request_back_to_main,
                on_exit_app=self._request_exit_app,
                initial_tick_rate=self.tick_rate_sec,
            )
            self.debug_window.start()

        print(f"[Game] platform={self.platform} format={self.game_format} players={len(self.list)}")
        print(f"[Game] dealer_image={self.dealer_image}")

    def _set_paused(self, paused: bool):
        self.paused = bool(paused)
        print(f"[Debug] paused={self.paused}")

    def _set_tick_rate(self, value: float):
        self.tick_rate_sec = float(value)
        set_game_tick_rate(self.tick_rate_sec)
        print(f"[Debug] tick_rate_sec={self.tick_rate_sec}")

    def _request_back_to_main(self):
        self.return_action = "back_to_main"
        self.running = False
        print("[Debug] returning to main screen")

    def _request_exit_app(self):
        self.return_action = "exit_app"
        self.running = False
        print("[Debug] exiting application")

    def to_absolute_region(self, rel_region):
        left = self.table.get_left_edge()
        top = self.table.get_top_edge()

        x1, y1, x2, y2 = rel_region
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        return (
            int(left + x1),
            int(top + y1),
            int(width),
            int(height),
        )

    def start(self):
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
        if self.debug_window is not None:
            self.debug_window.stop()
        if self.overlay is not None:
            self.overlay.stop()
        return self.return_action

    def _on_overlay_update(self, category, regions):
        if category == "bet":
            for i, rel in enumerate(regions):
                if i >= len(self.list):
                    break
                self.list[i].bet_region = self.to_absolute_region(rel)
            print("[Overlay] bet regions refreshed in running game")
            return

        if category == "pot":
            self.pot_regions_abs = [self.to_absolute_region(r) for r in regions]
            print("[Overlay] pot regions refreshed in running game")
            return

        if category == "board":
            self.board_regions_abs = [self.to_absolute_region(r) for r in regions]
            print("[Overlay] board regions refreshed in running game")

    def get_table_state(self):
        self.latest_region_images = {}
        total_players = len(self.list)
        anybet = False

        for i in range(total_players):
            self.list[i].set_player_pos(self.button_pos, i, total_players)
            value, _ = self.read_region(self.list[i].bet_region, f"bet_{i}", expect_float=True)
            self.list[i].bet_size = value

            if isinstance(self.list[i].bet_size, float):
                print(f" Position: '{self.list[i].position}' - Bet: '{self.list[i].bet_size}'")
                anybet = True
            else:
                print(f" [OCR] no readable bet for '{self.list[i].position}' (player={i})")

        pot_value = ""
        if self.pot_regions_abs:
            pot_value, _ = self.read_region(self.pot_regions_abs[0], "pot_0", expect_float=True)

        board_text = ""
        if self.board_regions_abs:
            _, board_text = self.read_region(self.board_regions_abs[0], "board_0", expect_float=False)

        sb_bet = next((p.bet_size for p in self.list if p.position == "SB" and isinstance(p.bet_size, float)), "-")
        bb_bet = next((p.bet_size for p in self.list if p.position == "BB" and isinstance(p.bet_size, float)), "-")

        prev_state = dict(self.last_game_state)
        sb_str = self._format_value(sb_bet)
        bb_str = self._format_value(bb_bet)
        pot_str = self._format_value(pot_value)
        board_str = board_text if board_text else "-"

        # Keep previous valid values when a tick fails to parse.
        if sb_str == "-":
            sb_str = prev_state.get("sb_bet", "-")
        if bb_str == "-":
            bb_str = prev_state.get("bb_bet", "-")
        if pot_str == "-":
            pot_str = prev_state.get("pot", "-")
        if board_str == "-":
            board_str = prev_state.get("board", "-")

        self.last_game_state = {
            "sb_bet": sb_str,
            "bb_bet": bb_str,
            "pot": pot_str,
            "board": board_str,
        }

        if anybet:
            print("----------------")
        else:
            print("[State] no bet values detected in this cycle")

    def get_button_pos(self):
        location = self.table.check_on_screen(self.dealer_image, log_miss=False)
        if location is None:
            self.dealer_miss_count += 1
            if self.dealer_miss_count % 10 == 0:
                print(f"[Dealer] {self.dealer_image} not found (attempts={self.dealer_miss_count})")
            return

        if self.dealer_miss_count > 0:
            print(f"[Dealer] found after {self.dealer_miss_count} misses")
        self.dealer_miss_count = 0

        if location.left != self.btn_img_pos:
            self.btn_img_pos = location.left
            button = 0
            min_dist = 9999
            for i in range(len(self.list)):
                dist = abs(location.left - self.list[i].x) + abs(location.top - self.list[i].y)
                if dist < min_dist:
                    button = i
                    min_dist = dist

            self.button_pos = button
            print(f"[Dealer] button changed -> player={self.button_pos}")

    def read_region(self, region, region_key, expect_float=True):
        region = (int(region[0]), int(region[1]), int(region[2]), int(region[3]))
        if self.overlay is not None:
            self.overlay.set_visible(False)
        try:
            raw_pil = pyautogui.screenshot(region=region)
        finally:
            if self.overlay is not None:
                self.overlay.set_visible(True)

        raw_np = np.array(raw_pil)
        gray = cv2.cvtColor(raw_np, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)

        bin_img = Image.fromarray(binary)
        self.latest_region_images[f"{region_key}_raw"] = raw_pil
        self.latest_region_images[f"{region_key}_bin"] = bin_img

        screenshot_np = cv2.cvtColor(np.array(bin_img), cv2.COLOR_GRAY2BGR)
        result = self.ocr.predict(
            screenshot_np,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        raw_texts = []
        if result:
            if isinstance(result[0], dict):
                raw_texts = result[0].get("rec_texts", [])
            elif result[0]:
                for line in result[0]:
                    raw_texts.append(line[1][0])

        if expect_float:
            for text in raw_texts:
                parsed = text.replace(" ", "").replace("B", "").strip()
                try:
                    return float(parsed), ""
                except ValueError:
                    continue
            if raw_texts:
                print(f"[OCR] unparseable text on {region_key}, region={region}: {raw_texts}")
            else:
                print(f"[OCR] no text detected on {region_key}, region={region}")
            return "", ""

        text_out = " ".join([t.strip() for t in raw_texts if str(t).strip()])
        if not text_out:
            print(f"[OCR] no text detected on {region_key}, region={region}")
        return "", text_out

    @staticmethod
    def _format_value(value):
        if isinstance(value, float):
            return f"{value:.2f}"
        return "-"

    @staticmethod
    def mouse_pos():
        table = TableScrapper()
        print(f" Table Edge Location - Left: '{table.get_left_edge()}' - Top: '{table.get_top_edge()}'")
        x, y = pyautogui.position()
        print(f" Mouse Location - {x, y}")

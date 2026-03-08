import time
import threading

import cv2
import keyboard
import numpy as np
import pyautogui
from PIL import Image
from paddleocr import PaddleOCR

from Player import Player
from TableScrapper import TableScrapper
from config_manager import (
    get_active_selection,
    get_platform_assets,
    get_regions,
    get_seat_centers,
    load_config,
)

DEBUG_OCR_DUMP = True


class Game:

    def __init__(self, platform=None, game_format=None):
        self.config = load_config()
        selected_platform, selected_format = get_active_selection(self.config)
        self.platform = platform or selected_platform
        self.game_format = game_format or selected_format

        assets = get_platform_assets(self.platform)
        self.dealer_image = assets["dealer_image"]

        self.ocr = PaddleOCR(lang="en", use_textline_orientation=False)
        self.screenshot = None
        self.button_pos = 0
        self.btn_img_pos = 0
        self.dealer_miss_count = 0

        self.table = TableScrapper(platform=self.platform, anchor_image=assets["anchor_image"])

        seat_centers = get_seat_centers(self.game_format)
        bet_regions_rel = get_regions(self.platform, self.game_format, self.config)

        if len(bet_regions_rel) < len(seat_centers):
            raise ValueError(
                f"Calibration missing for {self.platform}/{self.game_format}. "
                f"Expected {len(seat_centers)} regions, got {len(bet_regions_rel)}."
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

        self.screenlist = [None] * len(self.list)
        self.last_raw_screenlist = [None] * len(self.list)

        print(f"[Game] platform={self.platform} format={self.game_format} players={len(self.list)}")
        print(f"[Game] dealer_image={self.dealer_image}")

    def to_absolute_region(self, rel_region):
        left = self.table.get_left_edge()
        top = self.table.get_top_edge()

        x1, y1, x2, y2 = rel_region
        width = max(1, x2 - x1)
        height = max(1, y2 - y1)
        return left + x1, top + y1, width, height

    def start(self):
        while True:
            self.get_button_pos()
            self.get_table_state()
            time.sleep(2)

    def get_table_state(self):
        total_players = len(self.list)
        anybet = False

        for i in range(total_players):
            self.list[i].set_player_pos(self.button_pos, i, total_players)
            self.list[i].bet_size = self.read_image(self.list[i].bet_region, i)

            if isinstance(self.list[i].bet_size, float):
                print(f" Position: '{self.list[i].position}' - Bet: '{self.list[i].bet_size}'")
                anybet = True
            else:
                print(f" [OCR] no readable bet for '{self.list[i].position}' (player={i})")

        if anybet:
            print("----------------")
        else:
            print("[State] no bet values detected in this cycle")

    def get_button_pos(self):
        location = None
        while location is None:
            location = self.table.check_on_screen(self.dealer_image, log_miss=False)
            if location is None:
                self.dealer_miss_count += 1
                if self.dealer_miss_count % 10 == 0:
                    print(f"[Dealer] {self.dealer_image} not found (attempts={self.dealer_miss_count})")
                time.sleep(0.1)
            else:
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

    def read_image(self, region, i):
        raw_pil = pyautogui.screenshot(region=region)
        raw_np = np.array(raw_pil)
        gray = cv2.cvtColor(raw_np, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)

        self.screenshot = Image.fromarray(binary)
        self.screenlist[i] = self.screenshot
        self.last_raw_screenlist[i] = raw_pil

        screenshot_np = cv2.cvtColor(np.array(self.screenshot), cv2.COLOR_GRAY2BGR)
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
                for text in raw_texts:
                    text = text.replace(" ", "").replace("B", "").strip()
                    try:
                        return float(text)
                    except ValueError:
                        continue
            elif result[0]:
                for line in result[0]:
                    text = line[1][0]
                    raw_texts.append(text)
                    text = text.replace(" ", "").replace("B", "").strip()
                    try:
                        return float(text)
                    except ValueError:
                        continue

        if raw_texts:
            print(f"[OCR] unparseable text on player={i}, region={region}: {raw_texts}")
        else:
            print(f"[OCR] no text detected on player={i}, region={region}")

        return ""

    @staticmethod
    def mouse_pos():
        table = TableScrapper()
        print(f" Table Edge Location - Left: '{table.get_left_edge()}' - Top: '{table.get_top_edge()}'")
        x, y = pyautogui.position()
        print(f" Mouse Location - {x, y}")

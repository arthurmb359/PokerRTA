from services.capture.screen_capture import ScreenCapture
from services.recognition.card_reader import UNKNOWN_CARD
from services.recognition.board_reader import BoardReader
from services.recognition.bet_reader import BetReader
from services.recognition.ocr_service import OCRService
from services.recognition.pot_reader import PotReader
from services.recognition.hero_action_reader import HeroActionReader


class TableAnalyzer:
    def __init__(self, platform="Suprema"):
        self.ocr_service = OCRService(lang="en")
        self.capture = ScreenCapture()
        self.bet_reader = BetReader(self.ocr_service)
        self.pot_reader = PotReader(self.ocr_service)
        self.board_reader = BoardReader(platform=platform)
        self.hero_action_reader = HeroActionReader(platform=platform)

    def update_button_position(self, table, dealer_image, players, btn_img_pos, button_pos, dealer_miss_count):
        location = table.check_on_screen(dealer_image, log_miss=False)
        if location is None:
            dealer_miss_count += 1
            if dealer_miss_count % 10 == 0:
                print(f"[Dealer] {dealer_image} not found (attempts={dealer_miss_count})")
            return button_pos, btn_img_pos, dealer_miss_count

        if dealer_miss_count > 0:
            print(f"[Dealer] found after {dealer_miss_count} misses")
        dealer_miss_count = 0

        if location.left != btn_img_pos:
            btn_img_pos = location.left
            nearest_button = 0
            min_dist = 9999
            for i, player in enumerate(players):
                dist = abs(location.left - player.x) + abs(location.top - player.y)
                if dist < min_dist:
                    nearest_button = i
                    min_dist = dist
            button_pos = nearest_button
            print(f"[Dealer] button changed -> player={button_pos}")

        return button_pos, btn_img_pos, dealer_miss_count

    def extract_table_state(
        self,
        players,
        button_pos,
        pot_regions_abs,
        board_regions_abs,
        hero_action_regions_abs,
        overlay,
        previous_state,
    ):
        latest_region_images = {}
        total_players = len(players)
        any_bet = False
        position_bets = {}

        for i in range(total_players):
            players[i].set_player_pos(button_pos, i, total_players)
            value = self._read_bet(players[i].bet_region, f"bet_{i}", overlay, latest_region_images)
            players[i].bet_size = value
            position_bets[players[i].position] = self._format_value(players[i].bet_size)

            if isinstance(players[i].bet_size, float):
                print(f" Position: '{players[i].position}' - Bet: '{players[i].bet_size}'")
                any_bet = True
            else:
                print(f" [OCR] no readable bet for '{players[i].position}' (player={i})")

        pot_value = ""
        if pot_regions_abs:
            pot_value = self._read_pot(pot_regions_abs[0], "pot_0", overlay, latest_region_images)

        board_text = ""
        if board_regions_abs:
            board_text = self._read_board(board_regions_abs[0], "board_0", overlay, latest_region_images)

        hero_action = "NO"
        if hero_action_regions_abs:
            hero_action = self._read_hero_action(
                hero_action_regions_abs[0],
                "hero_action_0",
                overlay,
                latest_region_images,
            )

        pot_str = self._format_value(pot_value)
        board_str = board_text if board_text else "-"
        street = self._infer_street(board_str)
        hero_position = players[0].position if players else "-"

        state = {
            "position_bets": position_bets,
            "hero_position": hero_position,
            "street": street,
            "hero_action": hero_action,
            "pot": pot_str,
            "board": board_str,
        }

        if any_bet:
            print("----------------")
        else:
            print("[State] no bet values detected in this cycle")

        return state, latest_region_images

    def _read_bet(self, region, key, overlay, image_store):
        raw_pil, safe_region = self.capture.screenshot_region(region, overlay=overlay)
        value, bin_img = self.bet_reader.read(raw_pil, key, safe_region)
        image_store[f"{key}_raw"] = raw_pil
        image_store[f"{key}_bin"] = bin_img
        return value

    def _read_pot(self, region, key, overlay, image_store):
        raw_pil, safe_region = self.capture.screenshot_region(region, overlay=overlay)
        value, bin_img = self.pot_reader.read(raw_pil, key, safe_region)
        image_store[f"{key}_raw"] = raw_pil
        image_store[f"{key}_bin"] = bin_img
        return value

    def _read_board(self, region, key, overlay, image_store):
        raw_pil, safe_region = self.capture.screenshot_region(region, overlay=overlay)
        text_out, bin_img = self.board_reader.read(raw_pil, key, safe_region)
        image_store[f"{key}_raw"] = raw_pil
        image_store[f"{key}_bin"] = bin_img
        return text_out

    def _read_hero_action(self, region, key, overlay, image_store):
        raw_pil, _safe_region = self.capture.screenshot_region(region, overlay=overlay)
        detected, _score = self.hero_action_reader.read(raw_pil)
        image_store[f"{key}_raw"] = raw_pil
        return "YES" if detected else "NO"

    @staticmethod
    def _format_value(value):
        if isinstance(value, float):
            return f"{value:.2f}"
        return "-"

    @staticmethod
    def _infer_street(board_text: str) -> str:
        if not board_text or board_text == "-":
            return "Pre-Flop"

        card_count = len([card for card in board_text.split() if card and card != UNKNOWN_CARD])
        if card_count == 3:
            return "Flop"
        if card_count == 4:
            return "Turn"
        if card_count >= 5:
            return "River"
        return "Pre-Flop"

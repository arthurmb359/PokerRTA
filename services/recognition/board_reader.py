import cv2
import numpy as np
from PIL import Image

from services.recognition.card_reader import CardReader, UNKNOWN_CARD


class BoardReader:
    CARD_COUNT = 5
    CARD_WIDTH_FRACTION = 0.16
    CARD_GAP_FRACTION = 0.035
    CARD_TOP_FRACTION = 0.04
    CARD_BOTTOM_FRACTION = 0.96

    def __init__(self, platform="Suprema"):
        self.platform = platform
        self.card_reader = self._build_card_reader(platform)

    def read(self, raw_pil, region_key, region):
        raw_np = np.array(raw_pil)
        gray = cv2.cvtColor(raw_np, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        bin_img = Image.fromarray(binary)

        if self.card_reader is None:
            return "", bin_img

        board_cards = []
        for card_roi in self._extract_card_rois(gray):
            result = self.card_reader.read_card(card_roi)
            if result.card_code == UNKNOWN_CARD:
                continue
            board_cards.append(result.card_code)

        board_text = " ".join(board_cards)
        if board_text:
            print(f"[Board] detected={board_text}")
        else:
            print(f"[Board] no cards detected on {region_key}, region={region}")
        return board_text, bin_img

    def _extract_card_rois(self, board_gray: np.ndarray) -> list[np.ndarray]:
        detected_rois = self._extract_detected_card_rois(board_gray)
        if detected_rois:
            return detected_rois

        return self._extract_fixed_card_rois(board_gray)

    def _extract_detected_card_rois(self, board_gray: np.ndarray) -> list[np.ndarray]:
        height, width = board_gray.shape[:2]
        _, binary = cv2.threshold(board_gray, 185, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates = []
        min_height = int(height * 0.45)
        min_width = int(width * 0.08)
        max_width = int(width * 0.28)

        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if h < min_height or w < min_width or w > max_width:
                continue
            if y > int(height * 0.35):
                continue
            candidates.append((x, y, w, h))

        candidates.sort(key=lambda item: item[0])
        if not candidates:
            return []

        rois = []
        for x, y, w, h in candidates[:self.CARD_COUNT]:
            pad_x = max(2, int(w * 0.08))
            pad_y = max(2, int(h * 0.06))
            left = max(0, x - pad_x)
            top = max(0, y - pad_y)
            right = min(width, x + w + pad_x)
            bottom = min(height, y + h + pad_y)
            rois.append(board_gray[top:bottom, left:right])

        return rois

    def _extract_fixed_card_rois(self, board_gray: np.ndarray) -> list[np.ndarray]:
        height, width = board_gray.shape[:2]
        card_width = max(1, int(width * self.CARD_WIDTH_FRACTION))
        gap_width = max(1, int(width * self.CARD_GAP_FRACTION))
        total_width = (self.CARD_COUNT * card_width) + ((self.CARD_COUNT - 1) * gap_width)
        start_x = max(0, (width - total_width) // 2)
        top = max(0, int(height * self.CARD_TOP_FRACTION))
        bottom = max(top + 1, int(height * self.CARD_BOTTOM_FRACTION))

        rois = []
        for index in range(self.CARD_COUNT):
            left = start_x + index * (card_width + gap_width)
            right = min(width, left + card_width)
            rois.append(board_gray[top:bottom, left:right])
        return rois

    @staticmethod
    def _build_card_reader(platform: str):
        try:
            return CardReader(platform=platform)
        except FileNotFoundError:
            print(f"[Board] no card templates available for platform={platform}")
            return None

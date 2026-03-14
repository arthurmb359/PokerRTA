import cv2
import numpy as np

from services.recognition.card_reader import CardReader, UNKNOWN_CARD


class HeroCardsReader:
    LEFT_CARD_ROI = (0.00, 0.00, 0.64, 1.00)
    RIGHT_CARD_ROI = (0.37, 0.00, 1.00, 1.00)

    def __init__(self, platform: str = "Suprema"):
        self.card_reader = CardReader(platform=platform)

    def read(self, raw_pil) -> tuple[str, np.ndarray]:
        hero_gray = cv2.cvtColor(np.array(raw_pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        left_card = self._crop_fraction(hero_gray, *self.LEFT_CARD_ROI)
        right_card = self._crop_fraction(hero_gray, *self.RIGHT_CARD_ROI)

        left_result = self.card_reader.read_card(left_card)
        right_result = self.card_reader.read_card(right_card)

        cards = []
        if left_result.card_code != UNKNOWN_CARD:
            cards.append(left_result.card_code)
        if right_result.card_code != UNKNOWN_CARD:
            cards.append(right_result.card_code)

        hero_cards = " ".join(cards)
        return hero_cards if hero_cards else "-", hero_gray

    @staticmethod
    def _crop_fraction(gray: np.ndarray, x1f: float, y1f: float, x2f: float, y2f: float) -> np.ndarray:
        height, width = gray.shape[:2]
        x1 = max(0, min(width - 1, int(width * x1f)))
        y1 = max(0, min(height - 1, int(height * y1f)))
        x2 = max(x1 + 1, min(width, int(width * x2f)))
        y2 = max(y1 + 1, min(height, int(height * y2f)))
        return gray[y1:y2, x1:x2]

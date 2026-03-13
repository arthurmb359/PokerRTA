from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


UNKNOWN_CARD = "unknown"
RANK_CODES = {
    "A": "A",
    "K": "K",
    "Q": "Q",
    "J": "J",
    "10": "T",
    "9": "9",
    "8": "8",
    "7": "7",
    "6": "6",
    "5": "5",
    "4": "4",
    "3": "3",
    "2": "2",
}
SUIT_CODES = {
    "spade": "s",
    "heart": "h",
    "diamond": "d",
    "club": "c",
}


@dataclass(frozen=True)
class CardMatch:
    label: str
    score: float


@dataclass(frozen=True)
class CardReadResult:
    rank: str
    suit: str
    card_code: str
    rank_confidence: float
    suit_confidence: float


class CardReader:
    DEFAULT_RANK_ROI = (0.06, 0.08, 0.37, 0.34)
    DEFAULT_SUIT_ROI = (0.10, 0.24, 0.42, 0.64)
    RANK_TEMPLATE_SCALES = (0.7, 0.8, 0.9, 1.0, 1.1, 1.2)

    def __init__(
        self,
        platform: str = "Suprema",
        rank_threshold: float = 0.66,
        suit_threshold: float = 0.38,
    ):
        self.platform = platform
        self.rank_threshold = float(rank_threshold)
        self.suit_threshold = float(suit_threshold)
        self.rank_templates = self._load_templates(platform, "ranks")
        self.rank_templates_gray = self._load_rank_templates_gray(platform)
        self.suit_templates = self._load_templates(platform, "suits")

    def read_card(self, card_roi) -> CardReadResult:
        card_gray = self._to_gray(card_roi)
        rank_roi = self.extract_rank_roi(card_gray)
        suit_roi = self.extract_suit_roi(card_gray)

        rank_match = self.match_rank(rank_roi)
        suit_match = self.match_suit(suit_roi)

        rank = rank_match.label if rank_match.score >= self.rank_threshold else UNKNOWN_CARD
        suit = suit_match.label if suit_match.score >= self.suit_threshold else UNKNOWN_CARD

        if rank == UNKNOWN_CARD or suit == UNKNOWN_CARD:
            card_code = UNKNOWN_CARD
        else:
            card_code = f"{RANK_CODES[rank]}{SUIT_CODES[suit]}"

        return CardReadResult(
            rank=rank,
            suit=suit,
            card_code=card_code,
            rank_confidence=rank_match.score,
            suit_confidence=suit_match.score,
        )

    def extract_rank_roi(self, card_gray: np.ndarray) -> np.ndarray:
        height, width = card_gray.shape[:2]
        x1f, y1f, x2f, y2f = self.DEFAULT_RANK_ROI
        x1 = int(width * x1f)
        y1 = int(height * y1f)
        x2 = max(x1 + 1, int(width * x2f))
        y2 = max(y1 + 1, int(height * y2f))
        return card_gray[y1:y2, x1:x2]

    def extract_suit_roi(self, card_gray: np.ndarray) -> np.ndarray:
        height, width = card_gray.shape[:2]
        x1f, y1f, x2f, y2f = self.DEFAULT_SUIT_ROI
        x1 = int(width * x1f)
        y1 = int(height * y1f)
        x2 = max(x1 + 1, int(width * x2f))
        y2 = max(y1 + 1, int(height * y2f))
        return card_gray[y1:y2, x1:x2]

    def match_rank(self, rank_roi: np.ndarray) -> CardMatch:
        return self._match_rank_templates(rank_roi)

    def match_suit(self, suit_roi: np.ndarray) -> CardMatch:
        return self._match_templates(
            suit_roi,
            self.suit_templates,
            min_foreground_ratio=0.005,
            preparation_mode="bottom",
        )

    def rank_matches(self, rank_roi: np.ndarray, limit: int = 3) -> list[CardMatch]:
        return self._match_rank_scores(rank_roi, limit)

    def suit_matches(self, suit_roi: np.ndarray, limit: int = 3) -> list[CardMatch]:
        return self._match_scores(suit_roi, self.suit_templates, limit, preparation_mode="bottom")

    def _match_templates(
        self,
        roi: np.ndarray,
        templates: dict[str, np.ndarray],
        min_foreground_ratio: float,
        preparation_mode: str,
    ) -> CardMatch:
        if self._foreground_ratio(roi, preparation_mode) < min_foreground_ratio:
            return CardMatch(label=UNKNOWN_CARD, score=0.0)

        matches = self._match_scores(roi, templates, limit=1, preparation_mode=preparation_mode)
        if not matches:
            return CardMatch(label=UNKNOWN_CARD, score=0.0)
        return matches[0]

    def _match_rank_templates(self, roi: np.ndarray) -> CardMatch:
        if self._foreground_ratio(roi, "generic") < 0.02:
            return CardMatch(label=UNKNOWN_CARD, score=0.0)
        matches = self._match_rank_scores(roi, limit=1)
        if not matches:
            return CardMatch(label=UNKNOWN_CARD, score=0.0)
        return matches[0]

    @staticmethod
    def _to_gray(card_roi) -> np.ndarray:
        if isinstance(card_roi, np.ndarray):
            raw = card_roi
        else:
            raw = np.array(card_roi)

        if raw.ndim == 2:
            return raw
        if raw.shape[2] == 4:
            return cv2.cvtColor(raw, cv2.COLOR_RGBA2GRAY)
        return cv2.cvtColor(raw, cv2.COLOR_RGB2GRAY)

    @staticmethod
    def _normalize_binary(image: np.ndarray) -> np.ndarray:
        if image.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)
        resized = cv2.resize(image, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        blurred = cv2.GaussianBlur(resized, (3, 3), 0)
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary

    @classmethod
    def _foreground_ratio(cls, image: np.ndarray, preparation_mode: str) -> float:
        binary = cls._prepare_match_roi(image, preparation_mode)
        dark_pixels = np.count_nonzero(binary == 0)
        return float(dark_pixels) / float(binary.size)

    def _match_scores(
        self,
        roi: np.ndarray,
        templates: dict[str, np.ndarray],
        limit: int,
        preparation_mode: str,
    ) -> list[CardMatch]:
        roi_binary = self._prepare_match_roi(roi, preparation_mode)
        scored_matches = []

        for label, template in templates.items():
            resized_roi = cv2.resize(
                roi_binary,
                (template.shape[1], template.shape[0]),
                interpolation=cv2.INTER_AREA,
            )
            score = float(cv2.matchTemplate(resized_roi, template, cv2.TM_CCOEFF_NORMED)[0][0])
            scored_matches.append(CardMatch(label=label, score=max(score, 0.0)))

        scored_matches.sort(key=lambda match: match.score, reverse=True)
        return scored_matches[:limit]

    def _match_rank_scores(self, roi: np.ndarray, limit: int) -> list[CardMatch]:
        scored_matches = []
        for label, template in self.rank_templates_gray.items():
            score = self._best_rank_template_score(roi, template)
            scored_matches.append(CardMatch(label=label, score=max(score, 0.0)))
        scored_matches.sort(key=lambda match: match.score, reverse=True)
        return scored_matches[:limit]

    def _best_rank_template_score(self, roi: np.ndarray, template: np.ndarray) -> float:
        best_score = -1.0
        roi_height, roi_width = roi.shape[:2]

        for scale in self.RANK_TEMPLATE_SCALES:
            template_height = max(1, int(template.shape[0] * scale))
            template_width = max(1, int(template.shape[1] * scale))
            resized_template = cv2.resize(
                template,
                (template_width, template_height),
                interpolation=cv2.INTER_AREA if scale < 1.0 else cv2.INTER_CUBIC,
            )
            if template_height > roi_height or template_width > roi_width:
                continue
            score = float(cv2.matchTemplate(roi, resized_template, cv2.TM_CCOEFF_NORMED).max())
            best_score = max(best_score, score)

        if best_score < 0.0:
            return 0.0
        return best_score

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_templates(platform: str, category: str) -> dict[str, np.ndarray]:
        base_dir = Path(__file__).resolve().parents[2]
        template_dir = base_dir / "assets" / platform / category
        templates = {}

        for path in sorted(template_dir.glob("*.png")):
            template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                continue
            if category == "ranks":
                template = CardReader._extract_template_rank_roi(template)
                templates[path.stem] = CardReader._prepare_match_roi(template, "generic")
            else:
                templates[path.stem] = CardReader._prepare_match_roi(template, "generic")

        if not templates:
            raise FileNotFoundError(f"No templates found in {template_dir}")

        return templates

    @staticmethod
    @lru_cache(maxsize=None)
    def _load_rank_templates_gray(platform: str) -> dict[str, np.ndarray]:
        base_dir = Path(__file__).resolve().parents[2]
        template_dir = base_dir / "assets" / platform / "ranks"
        templates = {}

        for path in sorted(template_dir.glob("*.png")):
            template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                continue
            templates[path.stem] = CardReader._extract_template_rank_roi(template)

        if not templates:
            raise FileNotFoundError(f"No rank templates found in {template_dir}")

        return templates

    @staticmethod
    def _extract_template_rank_roi(template: np.ndarray) -> np.ndarray:
        height, width = template.shape[:2]
        x1f, y1f, x2f, y2f = CardReader.DEFAULT_RANK_ROI
        x1 = int(width * x1f)
        y1 = int(height * y1f)
        x2 = max(x1 + 1, int(width * x2f))
        y2 = max(y1 + 1, int(height * y2f))
        return template[y1:y2, x1:x2]

    @classmethod
    def _prepare_match_roi(cls, image: np.ndarray, preparation_mode: str) -> np.ndarray:
        if preparation_mode == "top":
            return cls._extract_component_roi(image, pick="top")
        if preparation_mode == "bottom":
            return cls._extract_component_roi(image, pick="bottom")
        cropped = cls._crop_foreground(image)
        return cls._normalize_binary(cropped)

    @staticmethod
    def _crop_foreground(image: np.ndarray) -> np.ndarray:
        if image.size == 0:
            return np.zeros((1, 1), dtype=np.uint8)

        binary = CardReader._normalize_binary(image)
        foreground = np.column_stack(np.where(binary == 0))
        if foreground.size == 0:
            return image

        y1, x1 = foreground.min(axis=0)
        y2, x2 = foreground.max(axis=0)
        pad = 2
        y1 = max(0, y1 - pad)
        x1 = max(0, x1 - pad)
        y2 = min(binary.shape[0], y2 + pad + 1)
        x2 = min(binary.shape[1], x2 + pad + 1)
        return binary[y1:y2, x1:x2]

    @classmethod
    def _extract_component_roi(cls, image: np.ndarray, pick: str) -> np.ndarray:
        binary = cls._normalize_binary(image)
        foreground = (binary == 0).astype(np.uint8)
        num_labels, _, stats, centroids = cv2.connectedComponentsWithStats(foreground, connectivity=8)

        height = binary.shape[0]
        components = []
        for label in range(1, num_labels):
            x = stats[label, cv2.CC_STAT_LEFT]
            y = stats[label, cv2.CC_STAT_TOP]
            w = stats[label, cv2.CC_STAT_WIDTH]
            h = stats[label, cv2.CC_STAT_HEIGHT]
            area = stats[label, cv2.CC_STAT_AREA]
            if area < 10:
                continue
            center_y = centroids[label][1]
            components.append((area, center_y, x, y, w, h))

        if not components:
            return cls._prepare_match_roi(image, "generic")

        if pick == "bottom":
            bottom_components = [item for item in components if item[1] >= height * 0.35]
            chosen = max(bottom_components or components, key=lambda item: (item[0], item[1]))
        else:
            top_components = [item for item in components if item[1] <= height * 0.60]
            chosen = max(top_components or components, key=lambda item: (item[0], -item[1]))

        _, _, x, y, w, h = chosen

        pad = 2
        y1 = max(0, y - pad)
        x1 = max(0, x - pad)
        y2 = min(binary.shape[0], y + h + pad)
        x2 = min(binary.shape[1], x + w + pad)
        return binary[y1:y2, x1:x2]

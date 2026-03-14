from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

# Temporary offline hero-cards debug helper.
# Purpose:
# - inspect one saved hero-cards sample outside the game loop
# - export left/right card crops and their rank/suit sub-ROIs
# - print top rank/suit matches for both hero cards
#
# Use this when:
# - hero card recognition regresses
# - a new hero_cards sample is captured and needs visual diagnosis
# - overlap/crop assumptions need manual inspection before changing runtime code
#
# Typical workflow:
# 1. replace or update assets/<Platform>/images/hero_cards.png
# 2. run this script
# 3. inspect tools/tmp/hero_cards_debug/*
# 4. use the findings to refine the crop assumptions or matching thresholds

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.recognition.card_reader import CardReader


SAMPLE_PATH = PROJECT_ROOT / "assets" / "Suprema" / "images" / "hero_cards.png"
OUTPUT_DIR = TOOLS_DIR / "tmp" / "hero_cards_debug"

LEFT_CARD_ROI = (0.00, 0.00, 0.56, 1.00)
RIGHT_CARD_ROI = (0.28, 0.00, 1.00, 1.00)


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)


def crop_fraction(gray: np.ndarray, x1f: float, y1f: float, x2f: float, y2f: float) -> np.ndarray:
    height, width = gray.shape[:2]
    x1 = max(0, min(width - 1, int(width * x1f)))
    y1 = max(0, min(height - 1, int(height * y1f)))
    x2 = max(x1 + 1, min(width, int(width * x2f)))
    y2 = max(y1 + 1, min(height, int(height * y2f)))
    return gray[y1:y2, x1:x2]


def main() -> None:
    hero_image = Image.open(SAMPLE_PATH).convert("RGB")
    hero_gray = cv2.cvtColor(np.array(hero_image), cv2.COLOR_RGB2GRAY)
    reader = CardReader(platform="Suprema")

    save_image(OUTPUT_DIR / "hero_cards_gray.png", hero_gray)

    card_rois = {
        "left": crop_fraction(hero_gray, *LEFT_CARD_ROI),
        "right": crop_fraction(hero_gray, *RIGHT_CARD_ROI),
    }

    print(f"sample={SAMPLE_PATH}")
    for side, card_roi in card_rois.items():
        rank_roi = reader.extract_rank_roi(card_roi)
        suit_roi = reader.extract_suit_roi(card_roi)
        result = reader.read_card(card_roi)
        rank_matches = reader.rank_matches(rank_roi, limit=3)
        suit_matches = reader.suit_matches(suit_roi, limit=3)

        save_image(OUTPUT_DIR / f"{side}_card.png", card_roi)
        save_image(OUTPUT_DIR / f"{side}_rank_roi.png", rank_roi)
        save_image(OUTPUT_DIR / f"{side}_suit_roi.png", suit_roi)
        save_image(OUTPUT_DIR / f"{side}_rank_binary.png", reader._normalize_binary(rank_roi))
        save_image(OUTPUT_DIR / f"{side}_suit_binary.png", reader._normalize_binary(suit_roi))

        print(f"{side}: {result}")
        print(f"  rank_matches={rank_matches}")
        print(f"  suit_matches={suit_matches}")


if __name__ == "__main__":
    main()

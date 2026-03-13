from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

# Temporary offline board-debug helper.
# Purpose:
# - inspect one saved board sample image outside the game loop
# - export intermediate card/rank/suit crops for visual inspection
# - print top rank/suit matches for each detected board card
#
# Use this when:
# - board recognition regresses
# - a new board sample is captured and needs visual diagnosis
# - ROI assumptions need manual inspection before changing runtime code
#
# Typical workflow:
# 1. replace or update assets/<Platform>/images/board.png
# 2. run this script
# 3. inspect tools/tmp/board_debug/*
# 4. use the findings to refine card ROI extraction or template matching

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.recognition.board_reader import BoardReader
from services.recognition.card_reader import CardReader

SAMPLE_PATH = PROJECT_ROOT / "assets" / "Suprema" / "images" / "board.png"
OUTPUT_DIR = TOOLS_DIR / "tmp" / "board_debug"


def save_image(path: Path, image: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(image).save(path)


def main() -> None:
    board_image = Image.open(SAMPLE_PATH).convert("RGB")
    board_gray = cv2.cvtColor(np.array(board_image), cv2.COLOR_RGB2GRAY)

    board_reader = BoardReader(platform="Suprema")
    card_reader = CardReader(platform="Suprema")

    save_image(OUTPUT_DIR / "board_gray.png", board_gray)

    card_rois = board_reader._extract_card_rois(board_gray)
    print(f"sample={SAMPLE_PATH}")
    print(f"cards_detected={len(card_rois)}")

    for index, card_roi in enumerate(card_rois):
        rank_roi = card_reader.extract_rank_roi(card_roi)
        suit_roi = card_reader.extract_suit_roi(card_roi)
        result = card_reader.read_card(card_roi)
        rank_matches = card_reader.rank_matches(rank_roi, limit=3)
        suit_matches = card_reader.suit_matches(suit_roi, limit=3)

        save_image(OUTPUT_DIR / f"card_{index}.png", card_roi)
        save_image(OUTPUT_DIR / f"card_{index}_rank_roi.png", rank_roi)
        save_image(OUTPUT_DIR / f"card_{index}_suit_roi.png", suit_roi)
        save_image(OUTPUT_DIR / f"card_{index}_rank_binary.png", card_reader._normalize_binary(rank_roi))
        save_image(OUTPUT_DIR / f"card_{index}_suit_binary.png", card_reader._normalize_binary(suit_roi))

        print(f"card_{index}: {result}")
        print(f"  rank_matches={rank_matches}")
        print(f"  suit_matches={suit_matches}")


if __name__ == "__main__":
    main()

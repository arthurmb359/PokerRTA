from dataclasses import dataclass, replace
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

# Temporary offline hero-cards tuning helper.
# Purpose:
# - search incrementally for better left/right card crop parameters
# - evaluate them against a known hero-cards sample
# - save the best crop set found for later inspection
#
# Use this when:
# - a new platform/card style needs hero-card tuning
# - hero card recognition is close but still misclassifies one of the hole cards
# - we want to retune crop defaults before changing runtime parameters
#
# Typical workflow:
# 1. update SAMPLE_PATH and EXPECTED_CARDS if the reference sample changes
# 2. run this script
# 3. inspect the reported best_params and tools/tmp/hero_cards_tune_best/*
# 4. apply validated crop parameters only after confirming visually

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.recognition.card_reader import CardReader, RANK_CODES, SUIT_CODES, UNKNOWN_CARD


SAMPLE_PATH = PROJECT_ROOT / "assets" / "Suprema" / "images" / "hero_cards.png"
OUTPUT_DIR = TOOLS_DIR / "tmp" / "hero_cards_tune_best"
EXPECTED_CARDS = ("7d", "5s")


@dataclass(frozen=True)
class HeroTuneParams:
    left_x1: float = 0.00
    left_y1: float = 0.00
    left_x2: float = 0.56
    left_y2: float = 1.00
    right_x1: float = 0.28
    right_y1: float = 0.00
    right_x2: float = 1.00
    right_y2: float = 1.00
    rank_threshold: float = 0.66
    suit_threshold: float = 0.38


@dataclass(frozen=True)
class HeroTuneEvaluation:
    params: HeroTuneParams
    score: float
    predictions: tuple[str, str]
    rank_hits: int
    suit_hits: int
    exact_hits: int


def crop_fraction(gray: np.ndarray, x1f: float, y1f: float, x2f: float, y2f: float) -> np.ndarray:
    height, width = gray.shape[:2]
    x1 = max(0, min(width - 1, int(width * x1f)))
    y1 = max(0, min(height - 1, int(height * y1f)))
    x2 = max(x1 + 1, min(width, int(width * x2f)))
    y2 = max(y1 + 1, min(height, int(height * y2f)))
    return gray[y1:y2, x1:x2]


def inverse_rank_codes() -> dict[str, str]:
    return {value: key for key, value in RANK_CODES.items()}


def inverse_suit_codes() -> dict[str, str]:
    return {value: key for key, value in SUIT_CODES.items()}


def evaluate_card(card_gray: np.ndarray, reader: CardReader) -> tuple[str, str, float, float]:
    result = reader.read_card(card_gray)
    rank_matches = reader.rank_matches(reader.extract_rank_roi(card_gray), limit=1)
    suit_matches = reader.suit_matches(reader.extract_suit_roi(card_gray), limit=1)
    rank_label = rank_matches[0].label if rank_matches else UNKNOWN_CARD
    suit_label = suit_matches[0].label if suit_matches else UNKNOWN_CARD
    rank_score = rank_matches[0].score if rank_matches else 0.0
    suit_score = suit_matches[0].score if suit_matches else 0.0
    if result.rank != UNKNOWN_CARD:
        rank_label = result.rank
        rank_score = result.rank_confidence
    if result.suit != UNKNOWN_CARD:
        suit_label = result.suit
        suit_score = result.suit_confidence
    return rank_label, suit_label, rank_score, suit_score


def evaluate_params(hero_gray: np.ndarray, params: HeroTuneParams, reader: CardReader) -> HeroTuneEvaluation:
    rank_code_map = inverse_rank_codes()
    suit_code_map = inverse_suit_codes()

    left_card = crop_fraction(hero_gray, params.left_x1, params.left_y1, params.left_x2, params.left_y2)
    right_card = crop_fraction(hero_gray, params.right_x1, params.right_y1, params.right_x2, params.right_y2)
    cards = (left_card, right_card)

    predictions = []
    rank_hits = 0
    suit_hits = 0
    exact_hits = 0
    total_score = 0.0

    for card_gray, expected_card in zip(cards, EXPECTED_CARDS):
        rank_label, suit_label, rank_score, suit_score = evaluate_card(card_gray, reader)
        expected_rank = rank_code_map[expected_card[0]]
        expected_suit = suit_code_map[expected_card[1]]

        if rank_label == expected_rank:
            rank_hits += 1
            total_score += 2.0 + rank_score
        else:
            total_score -= 0.5

        if suit_label == expected_suit:
            suit_hits += 1
            total_score += 1.5 + suit_score
        else:
            total_score -= 0.5

        if rank_score >= params.rank_threshold and suit_score >= params.suit_threshold and rank_label == expected_rank and suit_label == expected_suit:
            predictions.append(expected_card)
            exact_hits += 1
            total_score += 3.0
        else:
            predictions.append(UNKNOWN_CARD)

    return HeroTuneEvaluation(
        params=params,
        score=total_score,
        predictions=tuple(predictions),
        rank_hits=rank_hits,
        suit_hits=suit_hits,
        exact_hits=exact_hits,
    )


def normalize_params(params: HeroTuneParams) -> HeroTuneParams | None:
    if not (0.0 <= params.left_x1 < params.left_x2 <= 0.75):
        return None
    if not (0.0 <= params.left_y1 < params.left_y2 <= 1.0):
        return None
    if not (0.15 <= params.right_x1 < params.right_x2 <= 1.0):
        return None
    if not (0.0 <= params.right_y1 < params.right_y2 <= 1.0):
        return None
    if not (0.0 <= params.rank_threshold <= 1.0):
        return None
    if not (0.0 <= params.suit_threshold <= 1.0):
        return None
    return params


def generate_neighbors(params: HeroTuneParams, step: float) -> list[HeroTuneParams]:
    fields = (
        "left_x1", "left_y1", "left_x2", "left_y2",
        "right_x1", "right_y1", "right_x2", "right_y2",
        "rank_threshold", "suit_threshold",
    )
    neighbors = []
    for field in fields:
        for direction in (-1.0, 1.0):
            delta = step if "threshold" not in field else step * 0.75
            candidate = replace(params, **{field: getattr(params, field) + (direction * delta)})
            normalized = normalize_params(candidate)
            if normalized is not None:
                neighbors.append(normalized)
    return neighbors


def hill_climb(hero_gray: np.ndarray, reader: CardReader) -> HeroTuneEvaluation:
    current = evaluate_params(hero_gray, HeroTuneParams(), reader)
    for step in (0.08, 0.04, 0.02, 0.01, 0.005):
        improved = True
        while improved:
            improved = False
            for candidate_params in generate_neighbors(current.params, step):
                candidate = evaluate_params(hero_gray, candidate_params, reader)
                if candidate.score > current.score:
                    current = candidate
                    improved = True
                    break
    return current


def save_best_debug(hero_gray: np.ndarray, params: HeroTuneParams, reader: CardReader) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    left_card = crop_fraction(hero_gray, params.left_x1, params.left_y1, params.left_x2, params.left_y2)
    right_card = crop_fraction(hero_gray, params.right_x1, params.right_y1, params.right_x2, params.right_y2)

    for side, card in (("left", left_card), ("right", right_card)):
        rank_roi = reader.extract_rank_roi(card)
        suit_roi = reader.extract_suit_roi(card)
        Image.fromarray(card).save(OUTPUT_DIR / f"{side}_card.png")
        Image.fromarray(rank_roi).save(OUTPUT_DIR / f"{side}_rank_roi.png")
        Image.fromarray(suit_roi).save(OUTPUT_DIR / f"{side}_suit_roi.png")


def main() -> None:
    hero_image = Image.open(SAMPLE_PATH).convert("RGB")
    hero_gray = cv2.cvtColor(np.array(hero_image), cv2.COLOR_RGB2GRAY)
    reader = CardReader(platform="Suprema")

    evaluation = hill_climb(hero_gray, reader)
    save_best_debug(hero_gray, evaluation.params, reader)

    print(f"sample={SAMPLE_PATH}")
    print(f"expected={EXPECTED_CARDS}")
    print(f"predictions={evaluation.predictions}")
    print(f"exact_hits={evaluation.exact_hits} rank_hits={evaluation.rank_hits} suit_hits={evaluation.suit_hits}")
    print(f"score={evaluation.score:.4f}")
    print("best_params=")
    print(f"  left_x1={evaluation.params.left_x1:.4f}")
    print(f"  left_y1={evaluation.params.left_y1:.4f}")
    print(f"  left_x2={evaluation.params.left_x2:.4f}")
    print(f"  left_y2={evaluation.params.left_y2:.4f}")
    print(f"  right_x1={evaluation.params.right_x1:.4f}")
    print(f"  right_y1={evaluation.params.right_y1:.4f}")
    print(f"  right_x2={evaluation.params.right_x2:.4f}")
    print(f"  right_y2={evaluation.params.right_y2:.4f}")
    print(f"  rank_threshold={evaluation.params.rank_threshold:.4f}")
    print(f"  suit_threshold={evaluation.params.suit_threshold:.4f}")
    print(f"debug_output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()

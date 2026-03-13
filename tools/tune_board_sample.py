from dataclasses import dataclass, replace
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image

# Temporary offline board-tuning helper.
# Purpose:
# - search incrementally for better rank/suit ROI crop parameters
# - evaluate them against a known expected board sample
# - save the best crop set found for later inspection
#
# Use this when:
# - a new platform/card style needs tuning
# - board recognition is close but still misclassifies some ranks/suits
# - we want to retune ROI defaults before changing runtime parameters
#
# Typical workflow:
# 1. update SAMPLE_PATH and EXPECTED_BOARD if the reference sample changes
# 2. run this script
# 3. inspect the reported best_params and tools/tmp/board_tune_best/*
# 4. apply validated parameters to CardReader defaults only after confirming visually

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.recognition.board_reader import BoardReader
from services.recognition.card_reader import CardMatch, CardReader, RANK_CODES, SUIT_CODES, UNKNOWN_CARD


SAMPLE_PATH = PROJECT_ROOT / "assets" / "Suprema" / "images" / "board.png"
OUTPUT_DIR = TOOLS_DIR / "tmp" / "board_tune_best"
EXPECTED_BOARD = ("Qc", "2c", "3s", "Th", "2d")


@dataclass(frozen=True)
class TuneParams:
    rank_x1: float = 0.02
    rank_y1: float = 0.01
    rank_x2: float = 0.45
    rank_y2: float = 0.34
    suit_x1: float = 0.02
    suit_y1: float = 0.16
    suit_x2: float = 0.34
    suit_y2: float = 0.60
    rank_threshold: float = 0.42
    suit_threshold: float = 0.38


@dataclass(frozen=True)
class TuneEvaluation:
    params: TuneParams
    score: float
    predictions: tuple[str, ...]
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


def match_best(
    roi: np.ndarray,
    templates: dict[str, np.ndarray],
    reader: CardReader,
    preparation_mode: str,
) -> CardMatch:
    prepared = reader._prepare_match_roi(roi, preparation_mode)
    best = CardMatch(label=UNKNOWN_CARD, score=0.0)
    for label, template in templates.items():
        resized = cv2.resize(prepared, (template.shape[1], template.shape[0]), interpolation=cv2.INTER_AREA)
        score = float(cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)[0][0])
        if score > best.score:
            best = CardMatch(label=label, score=score)
    return best


def evaluate_params(card_rois: list[np.ndarray], params: TuneParams, reader: CardReader) -> TuneEvaluation:
    rank_code_map = inverse_rank_codes()
    suit_code_map = inverse_suit_codes()

    predictions = []
    rank_hits = 0
    suit_hits = 0
    exact_hits = 0
    total_score = 0.0

    for roi, expected_card in zip(card_rois, EXPECTED_BOARD):
        rank_roi = crop_fraction(roi, params.rank_x1, params.rank_y1, params.rank_x2, params.rank_y2)
        suit_roi = crop_fraction(roi, params.suit_x1, params.suit_y1, params.suit_x2, params.suit_y2)

        rank_match = match_best(rank_roi, reader.rank_templates, reader, "top")
        suit_match = match_best(suit_roi, reader.suit_templates, reader, "bottom")

        expected_rank = rank_code_map[expected_card[0]]
        expected_suit = suit_code_map[expected_card[1]]

        total_score += rank_match.score if rank_match.label == expected_rank else 0.0
        total_score += suit_match.score if suit_match.label == expected_suit else 0.0

        rank_label = rank_match.label if rank_match.score >= params.rank_threshold else UNKNOWN_CARD
        suit_label = suit_match.label if suit_match.score >= params.suit_threshold else UNKNOWN_CARD

        if rank_match.label == expected_rank:
            rank_hits += 1
            total_score += 1.5
        if suit_match.label == expected_suit:
            suit_hits += 1
            total_score += 1.0

        if rank_label == expected_rank and suit_label == expected_suit:
            exact_hits += 1
            predictions.append(expected_card)
            total_score += 3.0
        elif rank_label == UNKNOWN_CARD or suit_label == UNKNOWN_CARD:
            predictions.append(UNKNOWN_CARD)
            total_score -= 0.2
        else:
            predictions.append(f"{RANK_CODES[rank_label]}{SUIT_CODES[suit_label]}")
            total_score -= 0.5

    return TuneEvaluation(
        params=params,
        score=total_score,
        predictions=tuple(predictions),
        rank_hits=rank_hits,
        suit_hits=suit_hits,
        exact_hits=exact_hits,
    )


def generate_neighbors(params: TuneParams, step: float) -> list[TuneParams]:
    fields = (
        "rank_x1", "rank_y1", "rank_x2", "rank_y2",
        "suit_x1", "suit_y1", "suit_x2", "suit_y2",
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


def normalize_params(params: TuneParams) -> TuneParams | None:
    if not (0.0 <= params.rank_x1 < params.rank_x2 <= 0.60):
        return None
    if not (0.0 <= params.rank_y1 < params.rank_y2 <= 0.70):
        return None
    if not (0.0 <= params.suit_x1 < params.suit_x2 <= 0.50):
        return None
    if not (0.0 <= params.suit_y1 < params.suit_y2 <= 0.80):
        return None
    if not (0.0 <= params.rank_threshold <= 1.0):
        return None
    if not (0.0 <= params.suit_threshold <= 1.0):
        return None
    return params


def hill_climb(card_rois: list[np.ndarray], reader: CardReader) -> TuneEvaluation:
    current = evaluate_params(card_rois, TuneParams(), reader)
    for step in (0.08, 0.04, 0.02, 0.01, 0.005):
        improved = True
        while improved:
            improved = False
            for candidate_params in generate_neighbors(current.params, step):
                candidate = evaluate_params(card_rois, candidate_params, reader)
                if candidate.score > current.score:
                    current = candidate
                    improved = True
                    break
    return current


def save_best_debug(card_rois: list[np.ndarray], params: TuneParams, reader: CardReader) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for index, roi in enumerate(card_rois):
        rank_roi = crop_fraction(roi, params.rank_x1, params.rank_y1, params.rank_x2, params.rank_y2)
        suit_roi = crop_fraction(roi, params.suit_x1, params.suit_y1, params.suit_x2, params.suit_y2)
        Image.fromarray(roi).save(OUTPUT_DIR / f"card_{index}.png")
        Image.fromarray(rank_roi).save(OUTPUT_DIR / f"card_{index}_rank_roi.png")
        Image.fromarray(suit_roi).save(OUTPUT_DIR / f"card_{index}_suit_roi.png")
        Image.fromarray(reader._prepare_match_roi(rank_roi, "top")).save(OUTPUT_DIR / f"card_{index}_rank_prepared.png")
        Image.fromarray(reader._prepare_match_roi(suit_roi, "bottom")).save(OUTPUT_DIR / f"card_{index}_suit_prepared.png")


def main() -> None:
    board_image = Image.open(SAMPLE_PATH).convert("RGB")
    board_gray = cv2.cvtColor(np.array(board_image), cv2.COLOR_RGB2GRAY)

    board_reader = BoardReader(platform="Suprema")
    card_reader = CardReader(platform="Suprema")
    card_rois = board_reader._extract_card_rois(board_gray)

    evaluation = hill_climb(card_rois, card_reader)
    save_best_debug(card_rois, evaluation.params, card_reader)

    print(f"sample={SAMPLE_PATH}")
    print(f"expected={EXPECTED_BOARD}")
    print(f"predictions={evaluation.predictions}")
    print(f"exact_hits={evaluation.exact_hits} rank_hits={evaluation.rank_hits} suit_hits={evaluation.suit_hits}")
    print(f"score={evaluation.score:.4f}")
    print("best_params=")
    print(f"  rank_x1={evaluation.params.rank_x1:.4f}")
    print(f"  rank_y1={evaluation.params.rank_y1:.4f}")
    print(f"  rank_x2={evaluation.params.rank_x2:.4f}")
    print(f"  rank_y2={evaluation.params.rank_y2:.4f}")
    print(f"  suit_x1={evaluation.params.suit_x1:.4f}")
    print(f"  suit_y1={evaluation.params.suit_y1:.4f}")
    print(f"  suit_x2={evaluation.params.suit_x2:.4f}")
    print(f"  suit_y2={evaluation.params.suit_y2:.4f}")
    print(f"  rank_threshold={evaluation.params.rank_threshold:.4f}")
    print(f"  suit_threshold={evaluation.params.suit_threshold:.4f}")
    print(f"debug_output={OUTPUT_DIR}")


if __name__ == "__main__":
    main()

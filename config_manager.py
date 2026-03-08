import json
from pathlib import Path
from copy import deepcopy

CONFIG_PATH = Path("config.json")

PLATFORMS = ["PPPoker", "Suprema"]
FORMATS = ["HeadsUp", "6-max"]

DEFAULT_SEAT_CENTERS = {
    "HeadsUp": [(275, 820), (275, 75)],
    "6-max": [(270, 840), (50, 610), (50, 320), (270, 160), (485, 320), (485, 610)],
}

PLATFORM_ASSETS = {
    "Suprema": {
        "anchor_image": "suprema_icon.png",
        "dealer_image": "dealer_suprema.png",
    },
    "PPPoker": {
        "anchor_image": "table_edge.png",
        "dealer_image": "dealer_pppoker.png",
    },
}

# Bet regions are stored as relative table coordinates:
# [x1, y1, x2, y2] where (x1, y1)=top-left and (x2, y2)=bottom-right.
DEFAULT_CONFIG = {
    "selected_platform": "Suprema",
    "selected_format": "HeadsUp",
    "calibrations": {
        "Suprema": {
            "HeadsUp": [
                [248, 747, 323, 770],
                [130, 660, 205, 683],
            ],
            "6-max": [
                [248, 747, 323, 770],
                [130, 660, 205, 683],
                [133, 278, 208, 301],
                [250, 248, 325, 271],
                [362, 275, 437, 298],
                [365, 660, 440, 683],
            ],
        },
        "PPPoker": {
            "HeadsUp": [
                [248, 747, 323, 770],
                [130, 660, 205, 683],
            ],
            "6-max": [
                [248, 747, 323, 770],
                [130, 660, 205, 683],
                [133, 278, 208, 301],
                [250, 248, 325, 271],
                [362, 275, 437, 298],
                [365, 660, 440, 683],
            ],
        },
    },
}


def _merge_dict(base: dict, incoming: dict) -> dict:
    merged = deepcopy(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    try:
        current = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        save_config(DEFAULT_CONFIG)
        return deepcopy(DEFAULT_CONFIG)

    merged = _merge_dict(DEFAULT_CONFIG, current)
    if merged != current:
        save_config(merged)
    return merged


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def set_active_selection(platform: str, game_format: str) -> dict:
    config = load_config()
    config["selected_platform"] = platform
    config["selected_format"] = game_format
    save_config(config)
    return config


def set_calibration(platform: str, game_format: str, regions: list[list[int]]) -> dict:
    config = load_config()
    config["calibrations"][platform][game_format] = regions
    save_config(config)
    return config


def get_active_selection(config: dict | None = None) -> tuple[str, str]:
    cfg = config or load_config()
    return cfg["selected_platform"], cfg["selected_format"]


def get_regions(platform: str, game_format: str, config: dict | None = None) -> list[list[int]]:
    cfg = config or load_config()
    return cfg["calibrations"][platform][game_format]


def get_calibration(platform: str, game_format: str, config: dict | None = None) -> list[list[int]]:
    return get_regions(platform, game_format, config)


def get_seat_centers(game_format: str) -> list[tuple[int, int]]:
    return DEFAULT_SEAT_CENTERS[game_format]


def get_platform_assets(platform: str) -> dict:
    return PLATFORM_ASSETS[platform]

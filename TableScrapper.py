import pyautogui
import time

from config_manager import get_platform_assets


class TableScrapper:

    def __init__(self, platform="Suprema", anchor_image=None):
        self.platform = platform
        assets = get_platform_assets(platform)
        self.anchor_image = anchor_image or assets["anchor_image"]

        attempts = 0
        while True:
            location = self.check_on_screen(self.anchor_image, log_miss=False)
            if location is not None:
                print(f"[Table] {self.anchor_image} found at ({location.left}, {location.top})")
                break
            attempts += 1
            if attempts % 10 == 0:
                print(f"[Table] waiting for {self.anchor_image}... attempts={attempts}")
            time.sleep(0.2)

        self.x = location.left
        self.y = location.top

    def check_on_screen(self, image_name, confidence=0.8, log_miss=True):
        image_path = "images/" + image_name

        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is None and log_miss:
                print(f"[Screen] not found: {image_name}")
            return location
        except Exception as exc:
            print(f"[Screen] error locating {image_name}: {exc}")
            return None

    def get_left_edge(self):
        return self.x

    def get_top_edge(self):
        return self.y

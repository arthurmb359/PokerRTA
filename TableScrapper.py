import pyautogui
from PIL import Image
import io
import time
import os
from Player import Player

class TableScrapper:

    def __init__(self):
        while True:
            try:
                location = self.check_on_screen("suprema_icon.png")
                #print(f"'{location.left}' - '{location.top}'")
                break
            except Exception:
                pass
        self.x = location.left
        self.y = location.top

    def check_on_screen(self, image_name):
        image_path = "images/" + image_name

        try:
            return pyautogui.locateOnScreen(image_path, confidence=0.8)
        except Exception:
            pass

        return None

    def get_left_edge(self):
        return self.x

    def get_top_edge(self):
        return self.y


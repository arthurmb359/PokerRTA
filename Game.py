import time
import threading
import re

import cv2
import keyboard
import numpy as np
import pyautogui
from PIL import Image
from paddleocr import PaddleOCR

from Player import Player
from TableScrapper import TableScrapper

#BET AREA FROM PPOKER
BET_AREA_0 = (248, 747)
BET_AREA_1 = (130, 660)
BET_AREA_2 = (133, 278)
BET_AREA_3 = (250, 248)
BET_AREA_4 = (362, 275)
BET_AREA_5 = (365, 660)
BET_WIDTH_HEIGHT = (75, 23)

#BET AREA HU SUPREMA


class Game:

    def __init__(self):
        self.ocr = PaddleOCR(lang="en", use_textline_orientation=False)
        self.screenshot = None
        self.button_pos = 0
        self.btn_img_pos = 0
        self.table = TableScrapper()
        self.screenlist = [None] * 6
        player1 = Player(self.table.get_left_edge() + 270, self.table.get_top_edge() + 840, (self.table.get_left_edge().tolist() + BET_AREA_0[0], self.table.get_top_edge().tolist() + BET_AREA_0[1]) + BET_WIDTH_HEIGHT) #Hero clockwise
        player2 = Player(self.table.get_left_edge() + 50, self.table.get_top_edge() + 610, (self.table.get_left_edge().tolist() + BET_AREA_1[0], self.table.get_top_edge().tolist() + BET_AREA_1[1]) + BET_WIDTH_HEIGHT)
        player3 = Player(self.table.get_left_edge() + 50, self.table.get_top_edge() + 320, (self.table.get_left_edge().tolist() + BET_AREA_2[0], self.table.get_top_edge().tolist() + BET_AREA_2[1]) + BET_WIDTH_HEIGHT)
        player4 = Player(self.table.get_left_edge() + 270, self.table.get_top_edge() + 160, (self.table.get_left_edge().tolist() + BET_AREA_3[0], self.table.get_top_edge().tolist() + BET_AREA_3[1]) + BET_WIDTH_HEIGHT)
        player5 = Player(self.table.get_left_edge() + 485, self.table.get_top_edge() + 320, (self.table.get_left_edge().tolist() + BET_AREA_4[0], self.table.get_top_edge().tolist() + BET_AREA_4[1]) + BET_WIDTH_HEIGHT)
        player6 = Player(self.table.get_left_edge() + 485, self.table.get_top_edge() + 610, (self.table.get_left_edge().tolist() + BET_AREA_5[0], self.table.get_top_edge().tolist() + BET_AREA_5[1]) + BET_WIDTH_HEIGHT)
        list = [player1, player2, player3, player4, player5, player6]
        self.list = list
        listener_thread = threading.Thread(target=self.listen_for_key, daemon=True)
        listener_thread.start()

    def start(self):
        while True:
            self.get_button_pos()
            #self.check_ismyturn()
            self.get_table_state()
            time.sleep(2)

    def listen_for_key(self):
        # Set up a listener for the '*' key
        keyboard.on_release_key("*", lambda e: self.my_function())
        keyboard.on_release_key("+", lambda e: self.mouse_pos())
        keyboard.wait("esc")  # Exit the program when 'esc' is pressed

    def my_function(self):
        for i in range(len(self.screenlist)):
            self.screenlist[i].show()

    def check_ismyturn(self):
        while (TableScrapper.check_on_screen("myturn.png") == None):
            pass

    def get_table_state(self):
        anybet = False
        for i in range(len(self.list)):
            self.list[i].set_player_pos(self.button_pos, i)
            self.list[i].bet_size = self.read_image(self.list[i].bet_region, i)
            if isinstance(self.list[i].bet_size, float):
                print(f" Position: '{self.list[i].position}' - Bet: '{self.list[i].bet_size}'")
                anybet = True
        if anybet:
            print("----------------")

    def get_button_pos(self):
        location = None
        while (location == None):
            location = self.table.check_on_screen("M CAM .png")

        if(location.left != self.btn_img_pos): ##check if button changed
            self.btn_img_pos = location.left
            button = 0
            min_dist = 9999
            for i in range(len(self.list)):
                dist = abs(location.left - self.list[i].x) + abs(location.top - self.list[i].y)
                if dist < min_dist:
                    button = i
                    min_dist = dist
                    #print("Button: " + str(button) + " MinDist: " + str(min_dist) + " Dist:" + str(dist))

            self.button_pos = button

    def read_image(self, region, i):
        img = pyautogui.screenshot(region=region)
        img = np.array(img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(img, 160, 255, cv2.THRESH_BINARY)

        self.screenshot = Image.fromarray(binary)
        self.screenlist[i] = self.screenshot

        screenshot_np = cv2.cvtColor(np.array(self.screenshot), cv2.COLOR_GRAY2BGR)
        result = self.ocr.predict(
            screenshot_np,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        if result:
            if isinstance(result[0], dict):
                for text in result[0].get("rec_texts", []):
                    text = text.replace(" ", "").replace("B", "").strip()
                    try:
                        return float(text)
                    except ValueError:
                        continue
            elif result[0]:
                for line in result[0]:
                    text = line[1][0]
                    text = text.replace(" ", "").replace("B", "").strip()
                    try:
                        return float(text)
                    except ValueError:
                        continue

        return ""

    def crop_image(self, image):
        # Use pytesseract to detect text and get bounding box data
        custom_config = r'-c tessedit_char_whitelist=B --psm 11'  # Only allow letters
        detailed_data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)

        for i, text in enumerate(detailed_data["text"]):
            text = text.strip()
            if text == "BB":
                x_start = detailed_data["left"][i] + detailed_data["width"][i] - 25
                number_crop = image.crop((0, 0, x_start, 25))
                return number_crop
        return image

    @staticmethod
    def mouse_pos():
        table = TableScrapper()
        print(f" Table Edge Location - Left: '{table.get_left_edge()}' - Top: '{table.get_top_edge()}'")
        x, y = pyautogui.position()
        print(f" Mouse Location - {x, y}")

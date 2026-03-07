import pyautogui
from PIL import Image, ImageEnhance, ImageFilter
import io
import os
from Player import Player
from TableScrapper import TableScrapper
import time
import numpy as np
import keyboard
import threading
import cv2
import re
from paddleocr import PaddleOCR
from ppocr.utils.logging import get_logger
import logging
logger = get_logger()
logger.setLevel(logging.ERROR)

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
        self.ocr = PaddleOCR(use_angle_cls=True, lang="en")
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
            location = self.table.check_on_screen("dealer.png")

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

        self.screenshot = Image.fromarray(binary)  # A imagem é convertida para o formato PIL
        self.screenlist[i] = self.screenshot  # Armazena a imagem na lista

        # Converte a imagem PIL para np.ndarray para o PaddleOCR
        screenshot_np = np.array(self.screenshot)

        result = self.ocr.ocr(screenshot_np)

        if result and result[0]:
            for line in result[0]:
                text = line[1][0]  # O texto detectado está aqui
                # Remover espaços e a letra "B"
                text = text.replace(" ", "").replace("B", "").strip()
                try:
                    return float(text)
                except ValueError:
                    return ""
        return ""


        # """Binarize image from gray channel with 76 as threshold"""
        # img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        #
        # _, binary = cv2.threshold(img, 160, 255, cv2.THRESH_BINARY)
        #
        # self.screenshot = Image.fromarray(binary)
        # self.screenlist[i] = self.screenshot
        #
        # text = pytesseract.image_to_string(binary, config="--psm 6 tessedit_char_whitelist=0123456789.")
        # print(text.strip())
        # return float(text) if text.strip() == bool(re.match(r"^[+-]?\d*(?:\.\d+)?$", text.strip())) else ""

    def crop_image(self, image):
        # Use pytesseract to detect text and get bounding box data
        custom_config = r'-c tessedit_char_whitelist=B --psm 11'  # Only allow letters
        detailed_data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)

        # Print detected text for debugging
        #print("Detected text:", detailed_data["text"])

        for i, text in enumerate(detailed_data["text"]):
            text = text.strip()
            if text == "BB":  # Check if it's exactly "BB"/
                # Get bounding box for "BB"
                x_start = detailed_data["left"][i] + detailed_data["width"][i] - 25

                number_crop = image.crop((0, 0, x_start, 25))
                return number_crop
        return image #Caso nao ache BB na imagem

    @staticmethod
    def mouse_pos():
        table = TableScrapper()
        print(f" Table Edge Location - Left: '{table.get_left_edge()}' - Top: '{table.get_top_edge()}'")
        x, y = pyautogui.position()  # Setting x and y to the coordinates of mouse
        print(f" Mouse Location - {x, y}")  # Printing x and y values
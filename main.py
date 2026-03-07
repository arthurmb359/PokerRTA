import pyautogui
from Game import Game
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import time
import re
import cv2
from timeit import default_timer as timer
import numpy as np
import io
from TableScrapper import TableScrapper
from paddleocr import PaddleOCR

def crop():
    image_path = r"C:\Users\Arthur\Desktop\Poker\Pics\0.1BB.png"  # Replace with your image file path
    tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
    # Preprocess the image
    img = Image.open(image_path)

    width, height = img.size
    crop_x = int(width * 0.20)  # 20% from the left
    crop_box = (crop_x, 0, width, height)  # (left, upper, right, lower)

    # Crop the image
    cropped_img = img.crop(crop_box)
    cropped_img.show()

# def crop_bb_out():
    # image_path = r"C:\Users\Arthur\Desktop\Poker\Pics\0.1BB.png"  # Replace with your image file path
    # tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"  # Ensure Tesseract is correctly installed
    # image = Image.open(image_path)
    #
    # # Use pytesseract to detect text and get bounding box data
    # custom_config = r'-c tessedit_char_whitelist=B --psm 11'  # Only allow letters
    # detailed_data = pytesseract.image_to_data(image, config=custom_config, output_type=Output.DICT)
    #
    # # Print detected text for debugging
    # print("Detected text:", detailed_data)
    #
    # # Print detected text for debugging
    # # print("Detected text:", detailed_data["text"])
    #
    # for i, text in enumerate(detailed_data["text"]):
    #     text = text.strip()
    #     if text == "BB":  # Check if it's exactly "BB"/
    #         # Get bounding box for "BB"
    #         x_start = detailed_data["left"][i] + detailed_data["width"][i] - 25
    #
    #         number_crop = image.crop((0, 0, x_start, 25))
    #         number_crop.show()

# def test_ocr():
#     game = Game()
#
#     image_path = r"C:\Users\Arthur\Desktop\Poker\Pics\0.5.png"  # Replace with your image file path
#     img = cv2.imread(image_path)
#     tessdata_path = r"C:\Program Files\Tesseract-OCR\tessdata"
#
#     """Binarize image from gray channel with 76 as threshold"""
#     img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#
#     # Aplicar um leve desfoque para reduzir ruído
#     img = cv2.GaussianBlur(img, (3, 3), 0)
#
#     # Aplicar binarização adaptativa para melhor contraste
#     binary = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#                                    cv2.THRESH_BINARY, 11, 2)
#
#     text = pytesseract.image_to_string(binary, config="--psm 6 tessedit_char_whitelist=0123456789.")
#     print(text.strip())

#Serve para testar se o paddle identifica imagem
def paddle_test():
    ocr = PaddleOCR(use_angle_cls=True, lang="en")

    start = timer()

    image_path = r"C:\Users\Arthur\Desktop\Poker\Pics\0.5.png"
    result = ocr.ocr(image_path)
    end = timer()
    print(f" Time Elapsed: '{end - start:.9f}'")

    if result and result[0]:
        for line in result[0]:
            text = line[1][0]  # O texto detectado está aqui
            print(text)
    else:
        print("Nenhum texto detectado.")

    start = timer()
    image_path = r"C:\Users\Arthur\Desktop\Poker\Pics\111.4BB.png"
    result = ocr.ocr(image_path)
    end = timer()
    print(f" Time Elapsed: '{end - start:.9f}'")

    if result and result[0]:
        for line in result[0]:
            text = line[1][0]  # O texto detectado está aqui
            print(text)

#game = Game()
#game.start()
while True:
    Game.mouse_pos()

# paddle_test()
#crop_bb_out()
#testcrop()

'''
1275 645 #bottom
1040 628
1045 430
1245 400
1510 445
1540 610
'''

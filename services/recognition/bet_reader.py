import cv2
import numpy as np
from PIL import Image


class BetReader:
    def __init__(self, ocr_service):
        self.ocr_service = ocr_service

    def read(self, raw_pil, region_key, region):
        raw_np = np.array(raw_pil)
        gray = cv2.cvtColor(raw_np, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        bin_img = Image.fromarray(binary)

        texts = self.ocr_service.predict_texts(self.ocr_service.to_bgr(binary))
        for text in texts:
            parsed = text.replace(" ", "").replace("B", "").strip()
            try:
                return float(parsed), bin_img
            except ValueError:
                continue

        if texts:
            print(f"[OCR] unparseable text on {region_key}, region={region}: {texts}")
        else:
            print(f"[OCR] no text detected on {region_key}, region={region}")
        return "", bin_img


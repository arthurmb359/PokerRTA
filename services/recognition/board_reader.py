import cv2
import numpy as np
from PIL import Image


class BoardReader:
    def __init__(self, ocr_service):
        self.ocr_service = ocr_service

    def read(self, raw_pil, region_key, region):
        raw_np = np.array(raw_pil)
        gray = cv2.cvtColor(raw_np, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 160, 255, cv2.THRESH_BINARY)
        bin_img = Image.fromarray(binary)

        texts = self.ocr_service.predict_texts(self.ocr_service.to_bgr(binary))
        text_out = " ".join([t.strip() for t in texts if str(t).strip()])
        if not text_out:
            print(f"[OCR] no text detected on {region_key}, region={region}")
        return text_out, bin_img


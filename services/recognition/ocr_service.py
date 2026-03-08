import cv2
from paddleocr import PaddleOCR


class OCRService:
    def __init__(self, lang: str = "en"):
        self._ocr = PaddleOCR(lang=lang, use_textline_orientation=False)

    def predict_texts(self, image_bgr):
        result = self._ocr.predict(
            image_bgr,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        texts = []
        if result:
            if isinstance(result[0], dict):
                texts = result[0].get("rec_texts", [])
            elif result[0]:
                for line in result[0]:
                    texts.append(line[1][0])
        return texts

    @staticmethod
    def to_bgr(binary_gray):
        return cv2.cvtColor(binary_gray, cv2.COLOR_GRAY2BGR)


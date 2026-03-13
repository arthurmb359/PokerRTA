import cv2
import threading


class OCRService:
    _shared_ocr_by_lang = {}
    _lock = threading.Lock()
    _warmup_threads = {}

    def __init__(self, lang: str = "en"):
        self.lang = lang

    def _get_ocr(self):
        with self._lock:
            ocr = self._shared_ocr_by_lang.get(self.lang)
            if ocr is not None:
                return ocr

        from paddleocr import PaddleOCR

        ocr = PaddleOCR(lang=self.lang, use_textline_orientation=False)
        with self._lock:
            existing = self._shared_ocr_by_lang.get(self.lang)
            if existing is not None:
                return existing
            self._shared_ocr_by_lang[self.lang] = ocr
            return ocr

    @classmethod
    def warmup_async(cls, lang: str = "en"):
        with cls._lock:
            if lang in cls._shared_ocr_by_lang:
                return
            thread = cls._warmup_threads.get(lang)
            if thread is not None and thread.is_alive():
                return

            thread = threading.Thread(
                target=cls(lang)._get_ocr,
                daemon=True,
                name=f"ocr-warmup-{lang}",
            )
            cls._warmup_threads[lang] = thread
            thread.start()

    def predict_texts(self, image_bgr):
        result = self._get_ocr().predict(
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

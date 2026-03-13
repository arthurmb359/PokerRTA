from pathlib import Path

import cv2
import numpy as np
class HeroActionReader:
    def __init__(self, platform: str = "Suprema", threshold: float = 0.72):
        self.platform = platform
        self.threshold = float(threshold)
        self.template = self._load_template(platform)

    def read(self, raw_pil) -> tuple[bool, float]:
        roi_gray = cv2.cvtColor(np.array(raw_pil.convert("RGB")), cv2.COLOR_RGB2GRAY)
        template = self.template

        if roi_gray.shape[0] < template.shape[0] or roi_gray.shape[1] < template.shape[1]:
            resized_roi = cv2.resize(
                roi_gray,
                (template.shape[1], template.shape[0]),
                interpolation=cv2.INTER_AREA,
            )
            score = float(cv2.matchTemplate(resized_roi, template, cv2.TM_CCOEFF_NORMED)[0][0])
        else:
            score = float(cv2.matchTemplate(roi_gray, template, cv2.TM_CCOEFF_NORMED).max())

        return score >= self.threshold, score

    @staticmethod
    def _load_template(platform: str) -> np.ndarray:
        base_dir = Path(__file__).resolve().parents[2]
        template_path = base_dir / "assets" / platform / "images" / "fold.png"
        template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
        if template is None:
            raise FileNotFoundError(f"Missing fold template: {template_path}")
        return template

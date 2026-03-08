from services.recognition.bet_reader import BetReader


class PotReader:
    def __init__(self, ocr_service):
        self._bet_reader = BetReader(ocr_service)

    def read(self, raw_pil, region_key, region):
        return self._bet_reader.read(raw_pil, region_key, region)


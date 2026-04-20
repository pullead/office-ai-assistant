# src/utils/worker.py
from PySide6.QtCore import QThread, Signal


class OCRWorker(QThread):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, ocr_engine, image_path):
        super().__init__()
        self.ocr = ocr_engine
        self.path = image_path

    def run(self):
        try:
            result = self.ocr.image_to_text(self.path)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))
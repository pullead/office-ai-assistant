# -*- coding: utf-8 -*-
"""共通ワーカーの置き場。"""

from PySide6.QtCore import QThread, Signal


class OCRWorker(QThread):
    """OCR 専用の簡易ワーカー。"""

    finished = Signal(str)
    error = Signal(str)

    def __init__(self, ocr_engine, image_path: str):
        super().__init__()
        self.ocr = ocr_engine
        self.path = image_path

    def run(self):
        try:
            result = self.ocr.image_to_text(self.path)
            self.finished.emit(result)
        except Exception as error:
            self.error.emit(str(error))

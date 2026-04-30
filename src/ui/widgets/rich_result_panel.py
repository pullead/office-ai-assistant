# -*- coding: utf-8 -*-
"""リッチな結果表示パネル。"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QEasingCurve, Qt, QVariantAnimation
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
    QWebEngineView = None
else:
    try:
        from PySide6.QtWebEngineWidgets import QWebEngineView
    except Exception:  # pragma: no cover
        QWebEngineView = None


class RichResultPanel(QWidget):
    """HTML と各種プレビューを並べて表示する。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.summary_browser = QTextBrowser()
        self.summary_browser.setObjectName("ResultSummaryBrowser")
        self.summary_browser.setOpenExternalLinks(True)
        self.summary_browser.setMinimumWidth(420)

        self.preview_stack = QStackedWidget()
        self.preview_stack.setObjectName("ResultPreviewStack")
        self.empty_view = QLabel("ここに詳細プレビューが表示されます。")
        self.empty_view.setAlignment(Qt.AlignCenter)
        self.empty_view.setObjectName("InfoPanel")

        self.text_preview = QTextBrowser()
        self.text_preview.setOpenExternalLinks(True)

        self.image_preview = QLabel()
        self.image_preview.setAlignment(Qt.AlignCenter)
        self.image_preview.setMinimumHeight(300)

        self.table_preview = QTableWidget()
        self.file_list = QListWidget()
        use_plain_html = os.environ.get("QT_QPA_PLATFORM") == "offscreen"
        self.web_view = QWebEngineView() if QWebEngineView is not None and not use_plain_html else QTextBrowser()

        self.preview_stack.addWidget(self.empty_view)
        self.preview_stack.addWidget(self.text_preview)
        self.preview_stack.addWidget(self.image_preview)
        self.preview_stack.addWidget(self.table_preview)
        self.preview_stack.addWidget(self.web_view)
        self.preview_stack.addWidget(self.file_list)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.summary_browser)
        splitter.addWidget(self.preview_stack)
        splitter.setSizes([380, 460])
        layout.addWidget(splitter)

        self._pulse_animation = QVariantAnimation(self)
        self._pulse_animation.setDuration(520)
        self._pulse_animation.setStartValue(0)
        self._pulse_animation.setEndValue(100)
        self._pulse_animation.setEasingCurve(QEasingCurve.OutCubic)
        self._pulse_animation.valueChanged.connect(self._apply_pulse_style)
        self._pulse_animation.finished.connect(self._clear_pulse_style)

    def set_report_html(self, html: str):
        """HTML レポートを表示する。"""
        self.summary_browser.setHtml(html)
        self._pulse_report()

    def set_plain_report(self, text: str):
        """プレーンテキストを整形して表示する。"""
        escaped = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        html = (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<pre style='white-space: pre-wrap; line-height:1.65; font-size:14px;'>"
            f"{escaped}</pre></div>"
        )
        self.summary_browser.setHtml(html)
        self._pulse_report()

    def show_text_preview(self, text: str):
        """テキストプレビューを表示する。"""
        self.text_preview.setPlainText(text)
        self.preview_stack.setCurrentWidget(self.text_preview)
        self._pulse_preview()

    def show_image(self, image_path: str):
        """画像プレビューを表示する。"""
        pixmap = QPixmap(image_path)
        if pixmap.isNull():
            self.show_text_preview(f"画像を読み込めませんでした: {image_path}")
            return
        scaled = pixmap.scaled(1400, 840, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.image_preview.setPixmap(scaled)
        self.preview_stack.setCurrentWidget(self.image_preview)
        self._pulse_preview()

    def show_table_from_dataframe(self, dataframe):
        """DataFrame を表形式で表示する。"""
        self.table_preview.clear()
        self.table_preview.setColumnCount(len(dataframe.columns))
        self.table_preview.setRowCount(min(len(dataframe), 300))
        self.table_preview.setHorizontalHeaderLabels([str(col) for col in dataframe.columns])
        for row_index in range(min(len(dataframe), 300)):
            for column_index, column_name in enumerate(dataframe.columns):
                value = dataframe.iloc[row_index, column_index]
                self.table_preview.setItem(row_index, column_index, QTableWidgetItem(str(value)))
        self.table_preview.resizeColumnsToContents()
        self.preview_stack.setCurrentWidget(self.table_preview)
        self._pulse_preview()

    def show_html_file(self, html_path: str):
        """HTML ファイルを埋め込み表示する。"""
        path = Path(html_path).resolve()
        if QWebEngineView is not None and isinstance(self.web_view, QWebEngineView):
            self.web_view.setUrl(path.as_uri())
        else:
            self.web_view.setHtml(path.read_text(encoding="utf-8"))
        self.preview_stack.setCurrentWidget(self.web_view)
        self._pulse_preview()

    def show_files(self, file_paths: list[str]):
        """ファイル一覧を表示する。"""
        self.file_list.clear()
        self.file_list.addItems(file_paths)
        self.preview_stack.setCurrentWidget(self.file_list)
        self._pulse_preview()

    def clear_preview(self):
        """プレビューを初期状態へ戻す。"""
        self.preview_stack.setCurrentWidget(self.empty_view)

    def _pulse_report(self):
        """レポート更新時の局所ハイライトを開始する。"""
        self._pulse_target = "report"
        self._pulse_animation.stop()
        self._pulse_animation.start()

    def _pulse_preview(self):
        """プレビュー切り替え時の局所ハイライトを開始する。"""
        self._pulse_target = "preview"
        self._pulse_animation.stop()
        self._pulse_animation.start()

    def _apply_pulse_style(self, value):
        """薄い枠線だけを変化させて更新感を出す。"""
        ratio = 1.0 - (float(value) / 100.0)
        alpha = int(80 + 110 * ratio)
        style = (
            f"border: 1.5px solid rgba(106, 72, 243, {alpha});"
            "border-radius: 14px;"
        )
        if getattr(self, "_pulse_target", "report") == "preview":
            self.preview_stack.setStyleSheet(style)
        else:
            self.summary_browser.setStyleSheet(style)

    def _clear_pulse_style(self):
        """一時スタイルを戻す。"""
        self.summary_browser.setStyleSheet("")
        self.preview_stack.setStyleSheet("")

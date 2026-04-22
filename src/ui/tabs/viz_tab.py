# -*- coding: utf-8 -*-
"""データ可視化タブ。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.llm_client import LLMClient
from src.core.visualization import DataVisualizer
from src.ui.tabs.base_tab import BaseTab, make_section_label
from src.ui.widgets.api_settings import show_api_settings_dialog
from src.ui.widgets.rich_result_panel import RichResultPanel


class VizWorker(QThread):
    """可視化処理ワーカー。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, visualizer: DataVisualizer, llm_client: LLMClient, mode: str, file_path: str, use_api: bool):
        super().__init__()
        self.visualizer = visualizer
        self.llm_client = llm_client
        self.mode = mode
        self.file_path = file_path
        self.use_api = use_api

    def run(self):
        try:
            result = self.visualizer.create_visualization(self.file_path, self.mode)
            api_html = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                api_html = self.llm_client.summarize_to_html("データ可視化レポート", result["summary"])
            result["api_html"] = api_html
            result["mode"] = self.mode
            result["file_path"] = self.file_path
            self.finished.emit(result)
        except Exception as error:
            self.error.emit(str(error))


class VizTab(BaseTab):
    """CSV / Excel / テキストを可視化するタブ。"""

    def __init__(self):
        super().__init__(
            title="データ可視化",
            subtitle="CSV、Excel、テキストからインタラクティブなグラフやワードクラウドを生成します。",
            icon="VZ",
        )
        self.visualizer = DataVisualizer(output_dir="output")
        self.llm_client = LLMClient()
        self.current_file = None
        self.last_output = None
        self.worker = None
        self._setup_content()

    def _setup_content(self):
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        controls = QWidget()
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label("入力ファイル"))
        file_row = QHBoxLayout()
        self.select_btn = QPushButton("ファイルを選択")
        self.select_btn.setObjectName("SecondaryButton")
        self.select_btn.setMinimumHeight(40)
        self.select_btn.clicked.connect(self._select_file)
        file_row.addWidget(self.select_btn)

        self.file_label = QLabel("未選択")
        self.file_label.setObjectName("PageSubtitle")
        file_row.addWidget(self.file_label, 1)
        controls_layout.addLayout(file_row)

        controls_layout.addWidget(make_section_label("可視化モード"))
        self.func_combo = QComboBox()
        self.func_combo.setMinimumHeight(40)
        self.func_combo.addItem("棒グラフ", "bar")
        self.func_combo.addItem("折れ線グラフ", "line")
        self.func_combo.addItem("円グラフ", "pie")
        self.func_combo.addItem("ワードクラウド", "wordcloud")
        controls_layout.addWidget(self.func_combo)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox("グラフ結果を AI API で解説する")
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton("API 設定")
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        self.run_btn = QPushButton("生成する")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(42)
        self.run_btn.clicked.connect(self._generate)
        controls_layout.addWidget(self.run_btn)

        self.open_btn = QPushButton("出力ファイルを開く")
        self.open_btn.setObjectName("ToolButton")
        self.open_btn.setEnabled(False)
        self.open_btn.clicked.connect(self._open_output)
        controls_layout.addWidget(self.open_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)

        controls_layout.addWidget(make_section_label("処理ログ"))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(220)
        self.log_text.setPlaceholderText("可視化の進行状況や補足情報をここに表示します。")
        controls_layout.addWidget(self.log_text)
        controls_layout.addStretch()

        result_wrapper = QWidget()
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.setSpacing(10)
        result_layout.addWidget(make_section_label("可視化レポート"))

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([380, 920])
        self.card_layout.addWidget(splitter, 1)

    def _select_file(self):
        """ファイルを選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "ファイルを選択",
            "",
            "対応ファイル (*.xlsx *.xls *.csv *.txt)",
        )
        if path:
            self.current_file = path
            self.file_label.setText(Path(path).name)
            self.log_text.append(f"入力ファイルを選択しました: {path}")

    def _generate(self):
        """可視化を実行する。"""
        if not self.current_file:
            QMessageBox.warning(self, "入力確認", "先にファイルを選択してください。")
            return

        mode = self.func_combo.currentData()
        self.log_text.append(f"処理を開始しました。モード: {self.func_combo.currentText()}")
        self._set_buttons(False)
        self.progress_bar.setVisible(True)

        self.worker = VizWorker(
            self.visualizer,
            self.llm_client,
            mode,
            self.current_file,
            self.use_api_box.isChecked(),
        )
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_finished(self, payload: dict):
        """結果表示を更新する。"""
        self.last_output = payload["output_path"]
        self.open_btn.setEnabled(True)
        self.log_text.append(f"出力を生成しました: {payload['output_path']}")

        html = payload.get("api_html") or self._build_local_html(payload)
        self.result_panel.set_report_html(html)

        if payload["kind"] == "html":
            self.result_panel.show_html_file(payload["output_path"])
            if payload.get("dataframe") is not None:
                self.result_panel.show_table_from_dataframe(payload["dataframe"].head(200))
                self.result_panel.show_html_file(payload["output_path"])
        else:
            self.result_panel.show_image(payload["output_path"])

    def _on_error(self, message: str):
        """エラーを表示する。"""
        self.log_text.append(f"エラー: {message}")
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{message}</p>")
        self.result_panel.clear_preview()

    def _build_local_html(self, payload: dict) -> str:
        """ローカル可視化結果を HTML に整える。"""
        body = self._escape_html(payload["summary"]).replace("\n", "<br>")
        note = "マウスオーバーで詳細値、凡例クリックで系列の切り替え、ホイール操作で拡大縮小ができます。"
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>可視化レポート</h2>"
            f"<p style='color:#475569;'>{note}</p>"
            "<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:18px;'>"
            f"<div style='line-height:1.7;font-size:14px;'>{body}</div>"
            "</div></div>"
        )

    def _open_output(self):
        """出力ファイルを OS 既定アプリで開く。"""
        if self.last_output and Path(self.last_output).exists():
            import os

            os.startfile(self.last_output)

    def _set_buttons(self, enabled: bool):
        """ボタン状態を切り替える。"""
        self.select_btn.setEnabled(enabled)
        self.run_btn.setEnabled(enabled)
        self.api_settings_btn.setEnabled(enabled)

    def _reset_ui(self, *_args):
        """処理終了後に UI を戻す。"""
        self._set_buttons(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

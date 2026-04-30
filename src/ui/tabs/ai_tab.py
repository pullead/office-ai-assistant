# -*- coding: utf-8 -*-
"""AI アシスタントタブ。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QFont, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QFileDialog,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.core.ai_assistant import TaskAssistant
from src.core.file_manager import FileManager
from src.core.llm_client import LLMClient
from src.ui.tabs.base_tab import BaseTab, make_badge, make_section_label
from src.ui.widgets.api_settings import show_api_settings_dialog
from src.ui.widgets.rich_result_panel import RichResultPanel


class AIWorker(QThread):
    """AI タブのバックグラウンド処理。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        assistant: TaskAssistant,
        llm_client: LLMClient,
        mode: str,
        use_api: bool,
        command: str = "",
        text: str = "",
        file_path: str | None = None,
        url: str | None = None,
    ):
        super().__init__()
        self.assistant = assistant
        self.llm_client = llm_client
        self.mode = mode
        self.use_api = use_api
        self.command = command
        self.text = text
        self.file_path = file_path
        self.url = url

    def run(self):
        try:
            if self.mode == "command":
                local_result = self.assistant.execute_command(self.command)
                title = "AI コマンド実行"
            else:
                local_result = self.assistant.run_smart_task(
                    mode=self.mode,
                    text=self.text,
                    file_path=self.file_path,
                    url=self.url,
                )
                title = self.mode

            api_html = None
            api_error = None
            if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                try:
                    api_html = self.llm_client.summarize_to_html(title, local_result)
                except Exception as error:
                    api_error = str(error)

            self.finished.emit(
                {
                    "title": title,
                    "mode": self.mode,
                    "local_result": local_result,
                    "api_html": api_html,
                    "api_error": api_error,
                    "file_path": self.file_path,
                    "url": self.url,
                }
            )
        except Exception as error:
            self.error.emit(str(error))


class AITab(BaseTab):
    """AI 補助機能をまとめたタブ。"""

    def __init__(self):
        super().__init__(
            title="AI ワークスペース",
            subtitle="要約、議事録整理、TODO 抽出、ファイル分析、OCR 保存案などを大きなレポート表示で扱えます。",
            icon="AI",
        )
        self.file_manager = FileManager()
        self.assistant = TaskAssistant(file_manager=self.file_manager)
        self.llm_client = LLMClient()
        self.worker = None
        self.selected_file = None
        self.last_pdf_path = None
        self._setup_content()

    def _setup_content(self):
        self.card_layout.addLayout(self._build_metrics())

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)

        rail = QFrame()
        rail.setObjectName("WorkspaceNav")
        rail.setFixedWidth(190)
        rail_layout = QVBoxLayout(rail)
        rail_layout.setContentsMargins(14, 16, 14, 16)
        rail_layout.setSpacing(12)
        rail_layout.addWidget(make_section_label("AI Flow"))
        for title, hint in (
            ("1. 入力を集める", "テキスト / URL / ファイル"),
            ("2. モードを選ぶ", "要約 / TODO / 異常値"),
            ("3. レポート化", "PDF とプレビューを生成"),
        ):
            card = QFrame()
            card.setObjectName("WorkspaceNavCard")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)
            card_layout.setSpacing(4)
            title_label = QLabel(title)
            title_label.setObjectName("WorkspaceNavTitle")
            hint_label = QLabel(hint)
            hint_label.setObjectName("WorkspaceNavHint")
            hint_label.setWordWrap(True)
            card_layout.addWidget(title_label)
            card_layout.addWidget(hint_label)
            rail_layout.addWidget(card)

        self.rail_analyze_btn = QPushButton("AI で分析")
        self.rail_analyze_btn.setObjectName("PrimaryButton")
        self.rail_analyze_btn.clicked.connect(self.run_smart_tool)
        rail_layout.addWidget(self.rail_analyze_btn)

        self.rail_file_btn = QPushButton("ファイル選択")
        self.rail_file_btn.setObjectName("SecondaryButton")
        self.rail_file_btn.clicked.connect(self._select_file)
        rail_layout.addWidget(self.rail_file_btn)

        self.rail_clear_btn = QPushButton("入力をクリア")
        self.rail_clear_btn.setObjectName("ToolButton")
        self.rail_clear_btn.clicked.connect(self._clear_inputs)
        rail_layout.addWidget(self.rail_clear_btn)
        rail_layout.addStretch()

        controls = QFrame()
        controls.setObjectName("WorkspacePanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(18, 18, 18, 18)
        controls_layout.setSpacing(14)

        controls_layout.addWidget(make_section_label("クイックコマンド"))
        command_row = QHBoxLayout()
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("例: ワークスペースを分析して")
        self.command_input.setMinimumHeight(42)
        self.command_input.returnPressed.connect(self.execute_command)
        command_row.addWidget(self.command_input, 1)

        self.run_btn = QPushButton("実行")
        self.run_btn.setObjectName("PrimaryButton")
        self.run_btn.setMinimumHeight(42)
        self.run_btn.clicked.connect(self.execute_command)
        command_row.addWidget(self.run_btn)
        controls_layout.addLayout(command_row)

        controls_layout.addWidget(make_section_label("分析モード"))
        control_grid = QGridLayout()
        control_grid.setHorizontalSpacing(10)
        control_grid.setVerticalSpacing(10)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("ワークスペース分析", "workspace")
        self.mode_combo.addItem("テキスト要約", "summary")
        self.mode_combo.addItem("TODO 抽出", "todo")
        self.mode_combo.addItem("メール草案", "mail")
        self.mode_combo.addItem("議事録レポート", "meeting_report")
        self.mode_combo.addItem("ファイル分析", "file")
        self.mode_combo.addItem("CSV / Excel 異常値検出", "anomaly")
        self.mode_combo.addItem("OCR 結果の整理保存", "ocr_archive")
        self.mode_combo.addItem("Web 抽出要約", "web")
        self.mode_combo.addItem("改善アイデア提案", "ideas")
        self.mode_combo.setMinimumHeight(40)
        self.mode_combo.currentIndexChanged.connect(self._refresh_hint)

        self.file_btn = QPushButton("ファイル選択")
        self.file_btn.setObjectName("SecondaryButton")
        self.file_btn.setMinimumHeight(40)
        self.file_btn.clicked.connect(self._select_file)

        self.clear_file_btn = QPushButton("解除")
        self.clear_file_btn.setObjectName("ToolButton")
        self.clear_file_btn.setMinimumHeight(40)
        self.clear_file_btn.clicked.connect(self._clear_file)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Web 抽出用 URL")
        self.url_input.setMinimumHeight(40)

        control_grid.addWidget(QLabel("モード"), 0, 0)
        control_grid.addWidget(self.mode_combo, 0, 1, 1, 3)
        control_grid.addWidget(self.file_btn, 1, 0)
        control_grid.addWidget(self.clear_file_btn, 1, 1)
        control_grid.addWidget(self.url_input, 1, 2, 1, 2)
        controls_layout.addLayout(control_grid)

        self.file_label = QLabel("選択ファイル: なし")
        self.file_label.setObjectName("PageSubtitle")
        controls_layout.addWidget(self.file_label)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox("外部 AI API で結果を強化する")
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton("API 設定")
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        preset_row = QHBoxLayout()
        for label, prompt in (
            ("要約", "この内容の要点、重要事項、次アクションを整理してください。"),
            ("TODO", "この内容から TODO と担当候補を抽出してください。"),
            ("議事録", "この議事録から進捗レポートを作成してください。"),
            ("改善案", "この業務フローに役立つ改善アイデアを提案してください。"),
        ):
            button = QPushButton(label)
            button.setObjectName("ToolButton")
            button.clicked.connect(lambda _checked=False, value=prompt: self.input_text.setPlainText(value))
            preset_row.addWidget(button)
        controls_layout.addLayout(preset_row)

        self.input_hint = QLabel()
        self.input_hint.setObjectName("InfoPanel")
        self.input_hint.setWordWrap(True)
        controls_layout.addWidget(self.input_hint)

        self.input_text = QTextEdit()
        self.input_text.setPlaceholderText("ここにメモ、議事録、指示文、分析したい内容を入力してください。")
        self.input_text.setMinimumHeight(240)
        self.input_text.setFont(QFont("Meiryo UI", 11))
        controls_layout.addWidget(self.input_text)

        action_row = QHBoxLayout()
        self.smart_btn = QPushButton("AI で分析")
        self.smart_btn.setObjectName("PrimaryButton")
        self.smart_btn.setMinimumHeight(44)
        self.smart_btn.clicked.connect(self.run_smart_tool)
        action_row.addWidget(self.smart_btn)

        self.copy_btn = QPushButton("結果をコピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.setMinimumHeight(44)
        self.copy_btn.clicked.connect(self._copy_result)
        action_row.addWidget(self.copy_btn)

        self.open_pdf_btn = QPushButton("PDF レポートを開く")
        self.open_pdf_btn.setObjectName("ToolButton")
        self.open_pdf_btn.setMinimumHeight(44)
        self.open_pdf_btn.setEnabled(False)
        self.open_pdf_btn.clicked.connect(self._open_pdf)
        action_row.addWidget(self.open_pdf_btn)

        self.clear_btn = QPushButton("入力をクリア")
        self.clear_btn.setObjectName("ToolButton")
        self.clear_btn.setMinimumHeight(44)
        self.clear_btn.clicked.connect(self._clear_inputs)
        action_row.addWidget(self.clear_btn)
        controls_layout.addLayout(action_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        controls_layout.addWidget(self.progress_bar)
        controls_layout.addStretch()

        result_wrapper = QFrame()
        result_wrapper.setObjectName("WorkspaceFloat")
        result_layout = QVBoxLayout(result_wrapper)
        result_layout.setContentsMargins(18, 18, 18, 18)
        result_layout.setSpacing(10)
        result_layout.addWidget(make_section_label("結果レポート"))

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(rail)
        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([190, 520, 620])
        self.card_layout.addWidget(splitter, 1)

        self._refresh_hint()

    def _build_metrics(self) -> QHBoxLayout:
        """上部の概要カードを作る。"""
        row = QHBoxLayout()
        row.setSpacing(10)
        cards = [
            ("ローカル処理", "常時利用可能"),
            ("外部 AI API", "OpenRouter / 互換 API"),
            ("入力形式", "テキスト / URL / ファイル"),
        ]
        for title, value in cards:
            wrapper = QWidget()
            wrapper.setObjectName("MetricCard")
            layout = QVBoxLayout(wrapper)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(4)
            title_label = QLabel(title)
            title_label.setObjectName("MetricTitle")
            value_label = QLabel(value)
            value_label.setObjectName("MetricValue")
            layout.addWidget(title_label)
            layout.addWidget(value_label)
            row.addWidget(wrapper)
        row.addStretch()
        row.addWidget(make_badge("大画面レポート", "Info"))
        return row

    def execute_command(self):
        """クイックコマンドを実行する。"""
        command = self.command_input.text().strip()
        if not command:
            QMessageBox.warning(self, "入力確認", "クイックコマンドを入力してください。")
            return
        self._start_worker(mode="command", command=command)

    def run_smart_tool(self):
        """選択モードで AI 補助処理を実行する。"""
        mode = self.mode_combo.currentData()
        text = self.input_text.toPlainText().strip()
        url = self.url_input.text().strip()

        text_modes = {"summary", "todo", "mail", "meeting_report", "ideas"}
        file_required_modes = {"file", "anomaly", "ocr_archive"}

        if mode in text_modes and not any([text, self.selected_file, url]):
            QMessageBox.warning(self, "入力確認", "テキスト、ファイル、URL のいずれかを指定してください。")
            return
        if mode in file_required_modes and not self.selected_file:
            QMessageBox.warning(self, "入力確認", "このモードでは対象ファイルが必要です。")
            return
        if mode == "web" and not url:
            QMessageBox.warning(self, "入力確認", "Web 抽出では URL を入力してください。")
            return

        self._start_worker(mode=mode, text=text, file_path=self.selected_file, url=url)

    def _start_worker(
        self,
        mode: str,
        command: str = "",
        text: str = "",
        file_path: str | None = None,
        url: str | None = None,
    ):
        """ワーカーを起動する。"""
        self._set_busy(True)
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.worker = AIWorker(
            assistant=self.assistant,
            llm_client=self.llm_client,
            mode=mode,
            use_api=self.use_api_box.isChecked(),
            command=command,
            text=text,
            file_path=file_path,
            url=url,
        )
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _select_file(self):
        """AI 用のファイルを選択する。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "分析対象ファイルを選択",
            "",
            "対応ファイル (*.txt *.md *.py *.json *.csv *.xlsx *.xls *.png *.jpg *.jpeg *.bmp *.tif *.tiff)",
        )
        if path:
            self.selected_file = path
            self.file_label.setText(f"選択ファイル: {Path(path).name}")

    def _clear_file(self):
        """選択ファイルを解除する。"""
        self.selected_file = None
        self.file_label.setText("選択ファイル: なし")

    def _refresh_hint(self):
        """モード説明を更新する。"""
        mode = self.mode_combo.currentData()
        hints = {
            "workspace": "現在のプロジェクト構成やファイル傾向を整理します。",
            "summary": "長文を短くまとめて重要点を抽出します。",
            "todo": "文章から次アクション候補を抽出します。",
            "mail": "内容をもとに業務メールの草案を作ります。",
            "meeting_report": "議事録から進捗、決定事項、課題、次アクションを整理します。",
            "file": "テキスト、表、画像ファイルを内容ベースで要約します。",
            "anomaly": "CSV / Excel の異常値候補や品質課題を確認します。",
            "ocr_archive": "画像から OCR し、整理保存の提案に使います。",
            "web": "URL の本文を抽出し、レポート化します。",
            "ideas": "運用改善や機能拡張のアイデアを提案します。",
        }
        self.input_hint.setText(hints.get(mode, "AI 補助処理を実行します。"))

    def _copy_result(self):
        """結果表示をクリップボードへコピーする。"""
        text = self.result_panel.summary_browser.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)

    def _clear_inputs(self):
        """入力欄をクリアする。"""
        self.command_input.clear()
        self.input_text.clear()
        self.url_input.clear()
        self._clear_file()
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.result_panel.set_plain_report("")
        self.result_panel.clear_preview()

    def _on_finished(self, payload: dict):
        """処理完了時の表示を行う。"""
        html = payload.get("api_html") or self._build_local_html(payload)
        if payload.get("api_error"):
            html = self._append_api_warning(html, payload["api_error"])
        self.result_panel.set_report_html(html)
        self._update_preview(payload)
        self.last_pdf_path = self._export_pdf_report(payload, html)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))

    def _on_error(self, message: str):
        """エラーを表示する。"""
        self.result_panel.set_report_html(
            f"<h2>エラー</h2><p>{self._escape_html(message)}</p>"
        )
        self.result_panel.clear_preview()

    def _build_local_html(self, payload: dict) -> str:
        """ローカル結果を HTML 化する。"""
        title_map = {
            "command": "AI コマンド実行",
            "workspace": "ワークスペース分析",
            "summary": "要約結果",
            "todo": "TODO 抽出",
            "mail": "メール草案",
            "meeting_report": "議事録レポート",
            "file": "ファイル分析",
            "anomaly": "異常値検出",
            "ocr_archive": "OCR 自動整理",
            "web": "Web 抽出要約",
            "ideas": "改善アイデア提案",
        }
        title = title_map.get(payload["mode"], "分析結果")
        body = self._escape_html(payload["local_result"]).replace("\n", "<br>")
        file_name = Path(payload["file_path"]).name if payload.get("file_path") else "なし"
        url = payload.get("url") or "なし"
        api_note = ""
        if self.use_api_box.isChecked() and not self.llm_client.is_configured():
            api_note = "<p style='color:#b45309;'>AI API は未設定のため、ローカル分析結果を表示しています。</p>"
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            f"<h2 style='margin-bottom:8px;'>{title}</h2>"
            "<p style='color:#475569;'>大きな右側ペインで全文とプレビューを確認できます。</p>"
            f"{api_note}"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('モード', payload.get('mode', 'unknown'))}"
            f"{self._table_row('対象ファイル', file_name)}"
            f"{self._table_row('URL', url)}"
            f"{self._table_row('文字数', str(len(payload.get('local_result', ''))))}"
            "</table>"
            "<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:18px;'>"
            f"<div style='line-height:1.7;font-size:14px;'>{body}</div>"
            "</div></div>"
        )

    def _append_api_warning(self, html: str, message: str) -> str:
        """API 失敗時の警告を本文へ追記する。"""
        warning = (
            "<div style='margin-bottom:10px;padding:10px 12px;border-radius:10px;"
            "background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;'>"
            "<b>AI API 連携は失敗しました。</b><br>"
            f"{self._escape_html(message)}<br>"
            "ローカル解析結果を継続表示しています。"
            "</div>"
        )
        return warning + html

    def _update_preview(self, payload: dict):
        """関連プレビューを更新する。"""
        file_path = payload.get("file_path")
        if not file_path:
            self.result_panel.show_text_preview(payload["local_result"])
            return

        path = Path(file_path)
        suffix = path.suffix.lower()
        if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            self.result_panel.show_image(str(path))
            return
        if suffix == ".csv":
            dataframe = self._read_csv_with_fallback(path)
            if dataframe is not None:
                self.result_panel.show_table_from_dataframe(dataframe.head(200))
            else:
                self.result_panel.show_text_preview(payload["local_result"])
            return
        if suffix in {".xlsx", ".xls"}:
            try:
                dataframe = pd.read_excel(path)
                self.result_panel.show_table_from_dataframe(dataframe.head(200))
            except Exception:
                self.result_panel.show_text_preview(payload["local_result"])
            return
        try:
            self.result_panel.show_text_preview(self._read_text_with_fallback(path)[:12000])
        except Exception:
            self.result_panel.show_text_preview(payload["local_result"])

    def _set_busy(self, busy: bool):
        """実行中の UI 状態を切り替える。"""
        for button in (
            self.run_btn,
            self.smart_btn,
            self.rail_analyze_btn,
            self.rail_file_btn,
            self.rail_clear_btn,
            self.file_btn,
            self.clear_file_btn,
            self.api_settings_btn,
            self.open_pdf_btn,
        ):
            button.setEnabled(not busy)
        self.progress_bar.setVisible(busy)

    def _reset_ui(self, *_args):
        """ワーカー終了後の後始末を行う。"""
        self._set_busy(False)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))
        self.worker = None

    def _export_pdf_report(self, payload: dict, html_report: str) -> str | None:
        """AI レポートを PDF へ保存する。"""
        try:
            output_dir = Path("output") / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_path = output_dir / f"ai_{payload['mode']}_{timestamp}.pdf"
            content = (
                "<html><head><meta charset='utf-8'>"
                "<style>"
                "body{font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#1f2937;line-height:1.7;padding:24px;}"
                "h1{font-size:24px;margin-bottom:8px;} .meta{font-size:12px;color:#475569;}"
                ".box{border:1px solid #e7dcc7;border-radius:14px;padding:14px;background:#fffdf8;margin-top:12px;}"
                "</style></head><body>"
                "<h1>AI 分析レポート</h1>"
                f"<p class='meta'>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} / "
                f"モード: {self._escape_html(payload.get('mode', 'unknown'))}</p>"
                f"<div class='box'>{html_report}</div>"
                "</body></html>"
            )
            writer = QPdfWriter(str(pdf_path))
            writer.setPageSize(QPageSize(QPageSize.A4))
            writer.setResolution(96)
            document = QTextDocument()
            document.setHtml(content)
            document.print_(writer)
            return str(pdf_path)
        except Exception:
            return None

    def _open_pdf(self):
        """最新 PDF を開く。"""
        if not self.last_pdf_path:
            return
        path = Path(self.last_pdf_path)
        if not path.exists():
            return
        import os

        os.startfile(str(path))

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )

    def _table_row(self, label: str, value: str) -> str:
        """2列テーブル行を返す。"""
        return (
            "<tr>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;width:22%;'>{self._escape_html(str(label))}</td>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(str(value))}</td>"
            "</tr>"
        )

    def _read_csv_with_fallback(self, path: Path):
        """CSV を文字コード候補で読み込む。"""
        for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"):
            try:
                return pd.read_csv(path, encoding=encoding)
            except Exception:
                continue
        return None

    def _read_text_with_fallback(self, path: Path) -> str:
        """テキストを文字コード候補で読み込む。"""
        for encoding in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"):
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        return ""

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

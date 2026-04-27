# -*- coding: utf-8 -*-
"""AI メールアシスタントタブ。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.core.email_ai_assistant import EmailAIAssistant
from src.core.email_sender import EmailSender
from src.core.llm_client import LLMClient
from src.ui.tabs.base_tab import BaseTab, make_badge, make_section_label
from src.ui.widgets.api_settings import show_api_settings_dialog
from src.ui.widgets.rich_result_panel import RichResultPanel


class EmailAIWorker(QThread):
    """メール解析と返信生成を行うワーカー。"""

    finished = Signal(dict)
    error = Signal(str)

    def __init__(
        self,
        assistant: EmailAIAssistant,
        llm_client: LLMClient,
        mode: str,
        use_api: bool,
        source_path: str | None,
        raw_text: str,
        subject: str,
        sender: str,
        recipient: str,
        purpose: str,
        tone: str,
        extra_request: str,
        draft_subject: str,
        draft_body: str,
    ):
        super().__init__()
        self.assistant = assistant
        self.llm_client = llm_client
        self.mode = mode
        self.use_api = use_api
        self.source_path = source_path
        self.raw_text = raw_text
        self.subject = subject
        self.sender = sender
        self.recipient = recipient
        self.purpose = purpose
        self.tone = tone
        self.extra_request = extra_request
        self.draft_subject = draft_subject
        self.draft_body = draft_body

    def run(self):
        try:
            if self.source_path:
                parsed = self.assistant.parse_email_file(self.source_path)
            else:
                parsed = self.assistant.parse_email_text(self.raw_text, self.subject, self.sender)
                if self.recipient.strip():
                    parsed["recipient"] = self.recipient.strip()

            payload = {
                "mode": self.mode,
                "parsed": parsed,
                "preview_text": parsed.get("body", ""),
                "draft_subject": self.draft_subject,
                "draft_body": self.draft_body,
                "api_error": None,
                "api_html": None,
            }

            if self.mode == "analyze":
                payload["report_html"] = self.assistant.build_local_analysis_html(parsed)
                if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                    try:
                        payload["api_html"] = self.llm_client.summarize_to_html(
                            "AI メール分析",
                            self.assistant.build_ai_analysis_prompt(parsed),
                        )
                    except Exception as error:
                        payload["api_error"] = str(error)

            elif self.mode == "reply":
                local_draft = self.assistant.build_local_reply(parsed, self.purpose, self.tone, self.extra_request)
                payload["draft_subject"] = local_draft["subject"]
                payload["draft_body"] = local_draft["body"]
                payload["report_html"] = self._build_reply_report_html(parsed, local_draft, "返信候補を生成しました。")
                if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                    try:
                        payload["draft_body"] = self.llm_client.analyze(
                            "あなたは日本語のプロフェッショナルなメールアシスタントです。"
                            "業務メール本文だけを返してください。件名や説明文は不要です。",
                            self.assistant.build_ai_reply_prompt(parsed, self.purpose, self.tone, self.extra_request),
                        )
                    except Exception as error:
                        payload["api_error"] = str(error)

            elif self.mode == "refine":
                payload["draft_subject"] = self.draft_subject or f"Re: {parsed.get('subject', '')}"
                payload["draft_body"] = self.assistant.build_refined_reply(self.draft_body, self.extra_request)
                payload["report_html"] = self._build_reply_report_html(parsed, payload, "返信草案を調整しました。")
                if self.use_api and self.llm_client.is_enabled() and self.llm_client.is_configured():
                    try:
                        payload["draft_body"] = self.llm_client.analyze(
                            "あなたは日本語のプロフェッショナルなメールアシスタントです。"
                            "修正版のメール本文だけを返してください。件名や解説は不要です。",
                            self.assistant.build_ai_refine_prompt(
                                payload["draft_subject"], self.draft_body, self.extra_request
                            ),
                        )
                    except Exception as error:
                        payload["api_error"] = str(error)
            else:
                raise ValueError("未対応のメール処理モードです。")

            self.finished.emit(payload)
        except Exception as error:
            self.error.emit(str(error))

    def _build_reply_report_html(self, parsed: dict[str, str], draft: dict[str, str], heading: str) -> str:
        """返信候補のローカル HTML を組み立てる。"""
        return (
            "<div style='font-family:Yu Gothic UI,Meiryo,sans-serif;color:#1f2937;'>"
            "<h2>AI メールアシスタント</h2>"
            f"<p>{heading}</p>"
            "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
            f"{self._table_row('原件名', parsed.get('subject', ''))}"
            f"{self._table_row('送信者', parsed.get('sender', ''))}"
            f"{self._table_row('返信件名', draft.get('subject', ''))}"
            f"{self._table_row('文体', draft.get('style_note', '丁寧'))}"
            "</table>"
            "<h3>返信本文プレビュー</h3>"
            f"<div style='background:#fffdf8;border:1px solid #eadfce;border-radius:18px;padding:16px;line-height:1.7;'>"
            f"{self._escape_html(draft.get('body', '')[:1800]).replace(chr(10), '<br>')}"
            "</div>"
            "</div>"
        )

    def _table_row(self, label: str, value: str) -> str:
        """2列テーブル行を返す。"""
        return (
            "<tr>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;background:#f8f5ef;width:22%;'>{self._escape_html(label)}</td>"
            f"<td style='border:1px solid #e7dcc7;padding:6px;'>{self._escape_html(value)}</td>"
            "</tr>"
        )

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class EmailSendWorker(QThread):
    """SMTP 送信ワーカー。"""

    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, sender: EmailSender, to_addr: str, subject: str, body: str, attachments: list[str]):
        super().__init__()
        self.sender = sender
        self.to_addr = to_addr
        self.subject = subject
        self.body = body
        self.attachments = attachments

    def run(self):
        try:
            result = self.sender.send(self.to_addr, self.subject, self.body, self.attachments)
            self.finished.emit(result)
        except Exception as error:
            self.error.emit(str(error))


class EmailTab(BaseTab):
    """AI メールアシスタント画面。"""

    def __init__(self):
        super().__init__(
            title="AI メールアシスタント",
            subtitle="メール読解、返信候補生成、修正、SMTP 送信までを一つの画面で扱えます。",
            icon="email",
        )
        self.config = Config()
        self.mail_assistant = EmailAIAssistant()
        self.llm_client = LLMClient()
        self.email_sender = None
        self.attachments: list[str] = []
        self.current_source_path = None
        self.ai_worker = None
        self.send_worker = None
        self.last_pdf_path = None
        self._setup_content()
        self._load_config()

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

        rail_layout.addWidget(make_section_label("Mail Flow"))
        for title, hint in (
            ("1. 受信を読む", "EML / TXT / 手動貼り付け"),
            ("2. AI で返信を作る", "分析 / 草案 / 改稿"),
            ("3. SMTP で送る", "添付ファイルにも対応"),
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

        self.rail_read_btn = QPushButton("帮我读")
        self.rail_read_btn.setObjectName("PrimaryButton")
        self.rail_read_btn.clicked.connect(lambda: self._run_ai("analyze"))
        rail_layout.addWidget(self.rail_read_btn)

        self.rail_reply_btn = QPushButton("帮我回")
        self.rail_reply_btn.setObjectName("SecondaryButton")
        self.rail_reply_btn.clicked.connect(lambda: self._run_ai("reply"))
        rail_layout.addWidget(self.rail_reply_btn)

        self.rail_send_btn = QPushButton("SMTP 送信")
        self.rail_send_btn.setObjectName("ToolButton")
        self.rail_send_btn.clicked.connect(self._send_draft)
        rail_layout.addWidget(self.rail_send_btn)
        rail_layout.addStretch()

        controls = QFrame()
        controls.setObjectName("WorkspacePanel")
        controls_layout = QVBoxLayout(controls)
        controls_layout.setContentsMargins(18, 18, 18, 18)
        controls_layout.setSpacing(14)

        status_row = QHBoxLayout()
        status_row.addWidget(make_section_label("メールソース"))
        status_row.addStretch()
        self.smtp_badge = make_badge("SMTP 未設定", "Warning")
        status_row.addWidget(self.smtp_badge)
        controls_layout.addLayout(status_row)

        source_buttons = QHBoxLayout()
        self.load_mail_btn = QPushButton("EML / TXT 読み込み")
        self.load_mail_btn.setObjectName("SecondaryButton")
        self.load_mail_btn.clicked.connect(self._load_mail_source)
        source_buttons.addWidget(self.load_mail_btn)

        self.clear_mail_btn = QPushButton("入力クリア")
        self.clear_mail_btn.setObjectName("ToolButton")
        self.clear_mail_btn.clicked.connect(self._clear_mail_input)
        source_buttons.addWidget(self.clear_mail_btn)
        controls_layout.addLayout(source_buttons)

        self.source_label = QLabel("読み込み元: なし")
        self.source_label.setObjectName("PageSubtitle")
        self.source_label.setWordWrap(True)
        controls_layout.addWidget(self.source_label)

        mailbox_row = QHBoxLayout()
        self.mailbox_combo = QComboBox()
        self.mailbox_combo.addItem("Gmail")
        self.mailbox_combo.addItem("Outlook / Hotmail")
        self.mailbox_combo.addItem("会社メール（手動）")
        self.mailbox_combo.addItem("その他 IMAP / SMTP")
        self.mailbox_combo.setMinimumHeight(38)
        mailbox_row.addWidget(self.mailbox_combo)

        self.smtp_config_btn = QPushButton("SMTP 設定")
        self.smtp_config_btn.setObjectName("ToolButton")
        self.smtp_config_btn.clicked.connect(self._show_config)
        mailbox_row.addWidget(self.smtp_config_btn)
        controls_layout.addLayout(mailbox_row)

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("件名")
        self.subject_input.setMinimumHeight(38)
        controls_layout.addWidget(self.subject_input)

        self.sender_input = QLineEdit()
        self.sender_input.setPlaceholderText("送信者")
        self.sender_input.setMinimumHeight(38)
        controls_layout.addWidget(self.sender_input)

        self.recipient_input = QLineEdit()
        self.recipient_input.setPlaceholderText("返信先 / 宛先")
        self.recipient_input.setMinimumHeight(38)
        controls_layout.addWidget(self.recipient_input)

        self.mail_text = QTextEdit()
        self.mail_text.setPlaceholderText("メール本文またはヘッダー付きの原文を貼り付けてください。")
        self.mail_text.setMinimumHeight(220)
        controls_layout.addWidget(self.mail_text)

        api_row = QHBoxLayout()
        self.use_api_box = QCheckBox("外部 AI API で分析と返信生成を強化する")
        self.use_api_box.setChecked(self.llm_client.is_enabled())
        api_row.addWidget(self.use_api_box)

        self.api_settings_btn = QPushButton("API 設定")
        self.api_settings_btn.setObjectName("ToolButton")
        self.api_settings_btn.clicked.connect(lambda: show_api_settings_dialog(self))
        api_row.addWidget(self.api_settings_btn)
        api_row.addStretch()
        controls_layout.addLayout(api_row)

        controls_layout.addWidget(make_section_label("返信モード"))
        mode_row = QHBoxLayout()
        self.purpose_combo = QComboBox()
        self.purpose_combo.addItem("通常返信", "reply")
        self.purpose_combo.addItem("受諾返信", "accept")
        self.purpose_combo.addItem("追加確認", "followup")
        self.purpose_combo.setMinimumHeight(38)
        mode_row.addWidget(self.purpose_combo)

        self.tone_combo = QComboBox()
        self.tone_combo.addItem("正式・丁寧", "formal")
        self.tone_combo.addItem("親しみやすい", "friendly")
        self.tone_combo.addItem("簡潔", "brief")
        self.tone_combo.setMinimumHeight(38)
        mode_row.addWidget(self.tone_combo)
        controls_layout.addLayout(mode_row)

        self.extra_request = QTextEdit()
        self.extra_request.setPlaceholderText("例: 納期を必ず確認したい / 英語表現を避けたい / 価格相談を含めたい")
        self.extra_request.setMaximumHeight(92)
        controls_layout.addWidget(self.extra_request)

        action_row = QHBoxLayout()
        self.read_btn = QPushButton("帮我读")
        self.read_btn.setObjectName("PrimaryButton")
        self.read_btn.clicked.connect(lambda: self._run_ai("analyze"))
        action_row.addWidget(self.read_btn)

        self.reply_btn = QPushButton("帮我回")
        self.reply_btn.setObjectName("SecondaryButton")
        self.reply_btn.clicked.connect(lambda: self._run_ai("reply"))
        action_row.addWidget(self.reply_btn)

        self.refine_btn = QPushButton("修改回复")
        self.refine_btn.setObjectName("ToolButton")
        self.refine_btn.clicked.connect(lambda: self._run_ai("refine"))
        action_row.addWidget(self.refine_btn)
        controls_layout.addLayout(action_row)

        controls_layout.addWidget(make_section_label("返信草案"))
        self.reply_subject_input = QLineEdit()
        self.reply_subject_input.setPlaceholderText("返信件名")
        self.reply_subject_input.setMinimumHeight(38)
        controls_layout.addWidget(self.reply_subject_input)

        self.reply_body = QTextEdit()
        self.reply_body.setPlaceholderText("生成された返信本文をここで確認・修正できます。")
        self.reply_body.setMinimumHeight(180)
        controls_layout.addWidget(self.reply_body)

        attach_header = QHBoxLayout()
        attach_header.addWidget(make_section_label("添付ファイル"))
        attach_header.addStretch()

        self.add_attach_btn = QPushButton("追加")
        self.add_attach_btn.setObjectName("ToolButton")
        self.add_attach_btn.clicked.connect(self._add_attachment)
        attach_header.addWidget(self.add_attach_btn)

        self.remove_attach_btn = QPushButton("削除")
        self.remove_attach_btn.setObjectName("ToolButton")
        self.remove_attach_btn.clicked.connect(self._remove_attachment)
        attach_header.addWidget(self.remove_attach_btn)
        controls_layout.addLayout(attach_header)

        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(88)
        controls_layout.addWidget(self.attach_list)

        bottom_actions = QHBoxLayout()
        self.copy_btn = QPushButton("返信文をコピー")
        self.copy_btn.setObjectName("ToolButton")
        self.copy_btn.clicked.connect(self._copy_reply)
        bottom_actions.addWidget(self.copy_btn)

        self.send_btn = QPushButton("SMTP 送信")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.clicked.connect(self._send_draft)
        bottom_actions.addWidget(self.send_btn)
        controls_layout.addLayout(bottom_actions)

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

        result_header = QHBoxLayout()
        result_header.addWidget(make_section_label("AI メールレポート"))
        result_header.addStretch()
        self.open_pdf_btn = QPushButton("PDF レポートを開く")
        self.open_pdf_btn.setObjectName("ToolButton")
        self.open_pdf_btn.setEnabled(False)
        self.open_pdf_btn.clicked.connect(self._open_pdf)
        result_header.addWidget(self.open_pdf_btn)
        result_layout.addLayout(result_header)

        self.result_panel = RichResultPanel()
        result_layout.addWidget(self.result_panel)

        splitter.addWidget(rail)
        splitter.addWidget(controls)
        splitter.addWidget(result_wrapper)
        splitter.setSizes([180, 520, 620])
        self.card_layout.addWidget(splitter, 1)

    def _build_metrics(self) -> QHBoxLayout:
        """上部メトリクスを構築する。"""
        row = QHBoxLayout()
        row.setSpacing(10)
        for title, value in (
            ("入力形式", "貼り付け / EML / TXT"),
            ("AI 連携", "OpenRouter / SiliconFlow / 各社 API"),
            ("送信方式", "SMTP / 添付対応"),
        ):
            card = QWidget()
            card.setObjectName("MetricCard")
            layout = QVBoxLayout(card)
            layout.setContentsMargins(16, 14, 16, 14)
            layout.setSpacing(4)
            label_title = QLabel(title)
            label_title.setObjectName("MetricTitle")
            label_value = QLabel(value)
            label_value.setObjectName("MetricValue")
            layout.addWidget(label_title)
            layout.addWidget(label_value)
            row.addWidget(card)
        row.addStretch()
        row.addWidget(make_badge("AI Reply Flow", "Info"))
        return row

    def _load_config(self):
        """SMTP 設定を読み込む。"""
        sender_email = self.config.get("Email", "sender_email", fallback="")
        password = self.config.get("Email", "sender_password", fallback="")
        if sender_email and password:
            self.email_sender = EmailSender.from_config(self.config)
            self.smtp_badge.setText(sender_email)
            self.smtp_badge.setObjectName("BadgeSuccess")
        else:
            self.email_sender = None
            self.smtp_badge.setText("SMTP 未設定")
            self.smtp_badge.setObjectName("BadgeWarning")
        self.smtp_badge.style().unpolish(self.smtp_badge)
        self.smtp_badge.style().polish(self.smtp_badge)

    def _load_mail_source(self):
        """メールソースを読み込む。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "メールソースを選択",
            "",
            "メールファイル (*.eml *.txt *.md);;すべてのファイル (*.*)",
        )
        if not path:
            return
        self.current_source_path = path
        self.source_label.setText(f"読み込み元: {path}")
        try:
            parsed = self.mail_assistant.parse_email_file(path)
        except Exception as error:
            QMessageBox.warning(self, "読み込みエラー", f"メールソースの読み込みに失敗しました。\n{error}")
            return
        self.subject_input.setText(parsed.get("subject", ""))
        self.sender_input.setText(parsed.get("sender", ""))
        self.recipient_input.setText(parsed.get("recipient", ""))
        self.mail_text.setPlainText(parsed.get("body", ""))
        self.result_panel.set_report_html(self.mail_assistant.build_local_analysis_html(parsed))
        self.result_panel.show_text_preview(parsed.get("body", ""))

    def _clear_mail_input(self):
        """入力欄を初期化する。"""
        self.current_source_path = None
        self.source_label.setText("読み込み元: なし")
        self.subject_input.clear()
        self.sender_input.clear()
        self.recipient_input.clear()
        self.mail_text.clear()
        self.extra_request.clear()
        self.reply_subject_input.clear()
        self.reply_body.clear()
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.result_panel.set_plain_report("")
        self.result_panel.clear_preview()

    def _run_ai(self, mode: str):
        """AI メール処理を開始する。"""
        if not self.current_source_path and not self.mail_text.toPlainText().strip():
            QMessageBox.warning(self, "入力確認", "メール本文を貼り付けるか、EML / TXT を読み込んでください。")
            return
        if mode == "refine" and not self.reply_body.toPlainText().strip():
            QMessageBox.warning(self, "入力確認", "先に返信草案を生成してください。")
            return

        self._set_busy(True)
        self.last_pdf_path = None
        self.open_pdf_btn.setEnabled(False)
        self.ai_worker = EmailAIWorker(
            assistant=self.mail_assistant,
            llm_client=self.llm_client,
            mode=mode,
            use_api=self.use_api_box.isChecked(),
            source_path=self.current_source_path,
            raw_text=self.mail_text.toPlainText(),
            subject=self.subject_input.text().strip(),
            sender=self.sender_input.text().strip(),
            recipient=self.recipient_input.text().strip(),
            purpose=self.purpose_combo.currentData(),
            tone=self.tone_combo.currentData(),
            extra_request=self.extra_request.toPlainText().strip(),
            draft_subject=self.reply_subject_input.text().strip(),
            draft_body=self.reply_body.toPlainText().strip(),
        )
        self.ai_worker.finished.connect(self._on_ai_finished)
        self.ai_worker.error.connect(self._on_ai_error)
        self.ai_worker.finished.connect(self._reset_ai_ui)
        self.ai_worker.error.connect(self._reset_ai_ui)
        self.ai_worker.start()

    def _on_ai_finished(self, payload: dict):
        """AI 処理完了後の表示更新。"""
        html = payload.get("api_html") or payload.get("report_html") or ""
        if payload.get("api_error"):
            html = self._append_api_warning(html, payload["api_error"])
        self.result_panel.set_report_html(html)
        self.result_panel.show_text_preview(payload.get("preview_text", ""))

        if payload.get("draft_subject"):
            self.reply_subject_input.setText(payload["draft_subject"])
        if payload.get("draft_body"):
            self.reply_body.setPlainText(payload["draft_body"])

        self.last_pdf_path = self._export_pdf_report(html, payload)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))

    def _on_ai_error(self, message: str):
        """AI 処理エラーを表示する。"""
        self.result_panel.set_report_html(f"<h2>エラー</h2><p>{self._escape_html(message)}</p>")
        self.result_panel.clear_preview()

    def _send_draft(self):
        """返信草案を SMTP 送信する。"""
        to_addr = self.recipient_input.text().strip()
        subject = self.reply_subject_input.text().strip()
        body = self.reply_body.toPlainText().strip()
        if not to_addr or not subject or not body:
            QMessageBox.warning(self, "入力確認", "宛先、返信件名、返信本文を確認してください。")
            return
        if self.email_sender is None:
            QMessageBox.warning(self, "入力確認", "先に SMTP 設定を保存してください。")
            return

        self._set_busy(True)
        self.send_worker = EmailSendWorker(self.email_sender, to_addr, subject, body, self.attachments)
        self.send_worker.finished.connect(self._on_sent)
        self.send_worker.error.connect(self._on_send_error)
        self.send_worker.finished.connect(self._reset_send_ui)
        self.send_worker.error.connect(self._reset_send_ui)
        self.send_worker.start()

    def _on_sent(self, success: bool):
        """送信完了時のメッセージ。"""
        if success:
            QMessageBox.information(self, "送信完了", "返信メールを送信しました。")
        else:
            QMessageBox.warning(self, "送信失敗", "SMTP 送信に失敗しました。設定または認証情報を確認してください。")

    def _on_send_error(self, message: str):
        """送信エラーを表示する。"""
        QMessageBox.critical(self, "送信エラー", f"メール送信でエラーが発生しました。\n{message}")

    def _add_attachment(self):
        """添付ファイルを追加する。"""
        path, _ = QFileDialog.getOpenFileName(self, "添付ファイルを選択")
        if not path:
            return
        self.attachments.append(path)
        self.attach_list.addItem(Path(path).name)

    def _remove_attachment(self):
        """添付ファイルを削除する。"""
        row = self.attach_list.currentRow()
        if row < 0:
            return
        self.attach_list.takeItem(row)
        self.attachments.pop(row)

    def _copy_reply(self):
        """返信本文をコピーする。"""
        text = self.reply_body.toPlainText().strip()
        if text:
            from PySide6.QtWidgets import QApplication

            QApplication.clipboard().setText(text)

    def _show_config(self):
        """SMTP 設定ダイアログを表示する。"""
        dialog = QDialog(self)
        dialog.setWindowTitle("SMTP 設定")
        dialog.setMinimumWidth(460)

        form = QFormLayout(dialog)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        presets = QComboBox()
        presets.addItems(["手動入力", "Gmail", "Outlook / Hotmail", "Yahoo Mail", "会社メール（手動）"])
        form.addRow("プリセット", presets)

        server_edit = QLineEdit(self.config.get("Email", "smtp_server", fallback=""))
        form.addRow("SMTP サーバー", server_edit)

        port_edit = QLineEdit(self.config.get("Email", "smtp_port", fallback="587"))
        form.addRow("ポート", port_edit)

        email_edit = QLineEdit(self.config.get("Email", "sender_email", fallback=""))
        form.addRow("送信元メール", email_edit)

        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)
        pass_edit.setPlaceholderText("パスワードまたはアプリパスワード")
        form.addRow("パスワード", pass_edit)

        preset_values = {
            "Gmail": ("smtp.gmail.com", "587"),
            "Outlook / Hotmail": ("smtp.office365.com", "587"),
            "Yahoo Mail": ("smtp.mail.yahoo.com", "587"),
        }

        def apply_preset(text: str):
            if text in preset_values:
                server_edit.setText(preset_values[text][0])
                port_edit.setText(preset_values[text][1])

        presets.currentTextChanged.connect(apply_preset)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        self.config.set("Email", "smtp_server", server_edit.text().strip())
        self.config.set("Email", "smtp_port", port_edit.text().strip())
        self.config.set("Email", "sender_email", email_edit.text().strip())
        if pass_edit.text().strip():
            self.config.set("Email", "sender_password", pass_edit.text().strip())
        self._load_config()
        QMessageBox.information(self, "保存完了", "SMTP 設定を保存しました。")

    def _append_api_warning(self, html: str, message: str) -> str:
        """API 失敗時の警告を本文へ付加する。"""
        warning = (
            "<div style='margin-bottom:10px;padding:10px 12px;border-radius:10px;"
            "background:#fff7ed;border:1px solid #fed7aa;color:#9a3412;'>"
            "<b>AI API 連携は失敗しました。</b><br>"
            f"{self._escape_html(message)}<br>"
            "ローカル解析またはローカル草案で継続表示しています。"
            "</div>"
        )
        return warning + html

    def _export_pdf_report(self, html: str, payload: dict) -> str | None:
        """メールレポートを PDF へ保存する。"""
        try:
            output_dir = Path("output") / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_path = output_dir / f"email_ai_report_{timestamp}.pdf"
            content = (
                "<html><head><meta charset='utf-8'>"
                "<style>"
                "body{font-family:'Yu Gothic UI','Meiryo',sans-serif;color:#1f2937;line-height:1.7;padding:24px;}"
                "h1{font-size:24px;margin-bottom:8px;} .meta{font-size:12px;color:#475569;}"
                ".box{border:1px solid #e7dcc7;border-radius:14px;padding:14px;background:#fffdf8;margin-top:12px;}"
                "</style></head><body>"
                "<h1>AI メールアシスタント PDF レポート</h1>"
                f"<p class='meta'>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} / "
                f"モード: {self._escape_html(payload.get('mode', 'unknown'))}</p>"
                f"<div class='box'>{html}</div>"
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

    def _set_busy(self, busy: bool):
        """実行中の UI 状態を切り替える。"""
        for button in (
            self.load_mail_btn,
            self.clear_mail_btn,
            self.smtp_config_btn,
            self.api_settings_btn,
            self.read_btn,
            self.reply_btn,
            self.refine_btn,
            self.send_btn,
            self.rail_read_btn,
            self.rail_reply_btn,
            self.rail_send_btn,
            self.add_attach_btn,
            self.remove_attach_btn,
            self.open_pdf_btn,
        ):
            button.setEnabled(not busy)
        self.progress_bar.setVisible(busy)

    def _reset_ai_ui(self, *_args):
        """AI 処理後の UI 状態を戻す。"""
        self._set_busy(False)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))
        self.ai_worker = None

    def _reset_send_ui(self, *_args):
        """送信後の UI 状態を戻す。"""
        self._set_busy(False)
        self.open_pdf_btn.setEnabled(bool(self.last_pdf_path))
        self.send_worker = None

    def _escape_html(self, text: str) -> str:
        """HTML エスケープを行う。"""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def closeEvent(self, event):
        if self.ai_worker and self.ai_worker.isRunning():
            self.ai_worker.terminate()
            self.ai_worker.wait()
        if self.send_worker and self.send_worker.isRunning():
            self.send_worker.terminate()
            self.send_worker.wait()
        event.accept()

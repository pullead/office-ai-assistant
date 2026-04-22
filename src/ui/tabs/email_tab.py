# -*- coding: utf-8 -*-
"""メール送信タブ。"""

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
)

from src.config import Config
from src.core.email_sender import EmailSender
from src.ui.tabs.base_tab import BaseTab, make_badge, make_section_label


class EmailWorker(QThread):
    """メール送信ワーカー。"""

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
    """メール送信画面。"""

    def __init__(self):
        super().__init__(
            title="メール送信",
            subtitle="SMTP 設定を使って添付ファイル付きメールを送信します。",
            icon="✉️",
        )
        self.config = Config()
        self.email_sender = None
        self.attachments: list[str] = []
        self.worker = None
        self._setup_content()
        self._load_config()

    def _setup_content(self):
        status_row = QHBoxLayout()
        status_row.addWidget(make_section_label("送信設定"))
        status_row.addStretch()
        self.status_badge = make_badge("未設定", "Warning")
        status_row.addWidget(self.status_badge)
        self.card_layout.addLayout(status_row)

        self.config_btn = QPushButton("SMTP 設定")
        self.config_btn.setObjectName("SecondaryButton")
        self.config_btn.setMinimumHeight(38)
        self.config_btn.clicked.connect(self._show_config)
        self.card_layout.addWidget(self.config_btn)

        self.card_layout.addWidget(make_section_label("宛先 / 件名"))
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("recipient@example.com")
        self.to_input.setMinimumHeight(40)
        self.card_layout.addWidget(self.to_input)

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("件名")
        self.subject_input.setMinimumHeight(40)
        self.card_layout.addWidget(self.subject_input)

        self.card_layout.addWidget(make_section_label("本文"))
        self.body_text = QTextEdit()
        self.body_text.setPlaceholderText("メール本文を入力してください。")
        self.body_text.setMinimumHeight(160)
        self.card_layout.addWidget(self.body_text, 1)

        attachment_row = QHBoxLayout()
        attachment_row.addWidget(make_section_label("添付ファイル"))
        attachment_row.addStretch()

        add_attach = QPushButton("追加")
        add_attach.setObjectName("ToolButton")
        add_attach.clicked.connect(self._add_attachment)
        attachment_row.addWidget(add_attach)

        remove_attach = QPushButton("削除")
        remove_attach.setObjectName("ToolButton")
        remove_attach.clicked.connect(self._remove_attachment)
        attachment_row.addWidget(remove_attach)

        self.card_layout.addLayout(attachment_row)

        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(90)
        self.card_layout.addWidget(self.attach_list)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.card_layout.addWidget(self.progress_bar)

        self.send_btn = QPushButton("メール送信")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setMinimumHeight(44)
        self.send_btn.clicked.connect(self._send)
        self.card_layout.addWidget(self.send_btn)

    def _load_config(self):
        sender_email = self.config.get("Email", "sender_email", fallback="")
        password = self.config.get("Email", "sender_password", fallback="")
        if sender_email and password:
            self.email_sender = EmailSender.from_config(self.config)
            self.status_badge.setText(sender_email)
            self.status_badge.setObjectName("BadgeSuccess")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)
        else:
            self.email_sender = None
            self.status_badge.setText("未設定")
            self.status_badge.setObjectName("BadgeWarning")
            self.status_badge.style().unpolish(self.status_badge)
            self.status_badge.style().polish(self.status_badge)

    def _add_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, "添付ファイルを選択")
        if path:
            self.attachments.append(path)
            self.attach_list.addItem(Path(path).name)

    def _remove_attachment(self):
        row = self.attach_list.currentRow()
        if row >= 0:
            self.attach_list.takeItem(row)
            self.attachments.pop(row)

    def _send(self):
        to_addr = self.to_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_text.toPlainText().strip()

        if not to_addr or not subject or not body:
            QMessageBox.warning(self, "エラー", "宛先、件名、本文は必須です。")
            return
        if self.email_sender is None:
            QMessageBox.warning(self, "エラー", "先に SMTP 設定を保存してください。")
            return

        self.send_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = EmailWorker(self.email_sender, to_addr, subject, body, self.attachments)
        self.worker.finished.connect(self._on_sent)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._reset_ui)
        self.worker.error.connect(self._reset_ui)
        self.worker.start()

    def _on_sent(self, success: bool):
        if success:
            QMessageBox.information(self, "成功", "メールを送信しました。")
        else:
            QMessageBox.critical(self, "エラー", "メール送信に失敗しました。設定を確認してください。")

    def _on_error(self, message: str):
        QMessageBox.critical(self, "エラー", f"メール送信でエラーが発生しました。\n{message}")

    def _reset_ui(self, *_args):
        self.send_btn.setEnabled(True)
        self.config_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _show_config(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("SMTP 設定")
        dialog.setMinimumWidth(420)

        form = QFormLayout(dialog)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        presets = QComboBox()
        presets.addItems(["手動入力", "Gmail", "Outlook / Hotmail", "Yahoo Mail"])
        form.addRow("プリセット", presets)

        server_edit = QLineEdit(self.config.get("Email", "smtp_server", fallback=""))
        form.addRow("SMTP サーバー", server_edit)

        port_edit = QLineEdit(self.config.get("Email", "smtp_port", fallback="587"))
        form.addRow("ポート", port_edit)

        email_edit = QLineEdit(self.config.get("Email", "sender_email", fallback=""))
        form.addRow("送信元メール", email_edit)

        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)
        pass_edit.setPlaceholderText("アプリパスワードを入力")
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

        if dialog.exec() == QDialog.Accepted:
            self.config.set("Email", "smtp_server", server_edit.text().strip())
            self.config.set("Email", "smtp_port", port_edit.text().strip())
            self.config.set("Email", "sender_email", email_edit.text().strip())
            if pass_edit.text().strip():
                self.config.set("Email", "sender_password", pass_edit.text().strip())

            self._load_config()
            QMessageBox.information(self, "成功", "SMTP 設定を保存しました。")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

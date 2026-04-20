# -*- coding: utf-8 -*-
"""メール自動送信タブ"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QLabel, QFileDialog,
                               QMessageBox, QListWidget, QProgressBar,
                               QFrame, QDialog, QFormLayout, QDialogButtonBox,
                               QComboBox)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from src.ui.tabs.base_tab import BaseTab, make_section_label, make_badge
from src.core.email_sender import EmailSender
from src.config import Config


class EmailWorker(QThread):
    finished = Signal(bool)
    error = Signal(str)

    def __init__(self, sender, to, subject, body, attachments):
        super().__init__()
        self.sender = sender
        self.to = to
        self.subject = subject
        self.body = body
        self.attachments = attachments

    def run(self):
        try:
            ok = self.sender.send(self.to, self.subject, self.body, self.attachments)
            self.finished.emit(ok)
        except Exception as e:
            self.error.emit(str(e))


class EmailTab(BaseTab):
    def __init__(self):
        super().__init__(
            title="メール自動送信",
            subtitle="SMTPを使って添付ファイル付きメールを送信します",
            icon="📧"
        )
        self.config = Config()
        self.email_sender = None
        self.attachments: list[str] = []
        self.worker = None
        self._setup_content()
        self._load_config()

    def _setup_content(self):
        cl = self.card_layout

        # ── 設定状態バッジ ──
        status_row = QHBoxLayout()
        status_row.addWidget(make_section_label("送信設定"))
        status_row.addStretch()
        self.status_badge = make_badge("未設定", "Warning")
        status_row.addWidget(self.status_badge)
        cl.addLayout(status_row)

        self.config_btn = QPushButton("⚙  SMTP設定")
        self.config_btn.setObjectName("SecondaryButton")
        self.config_btn.setMinimumHeight(38)
        self.config_btn.setCursor(Qt.PointingHandCursor)
        self.config_btn.clicked.connect(self._show_config)
        cl.addWidget(self.config_btn)

        # ── 宛先・件名 ──
        cl.addWidget(make_section_label("宛先 / 件名"))
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("recipient@example.com")
        self.to_input.setMinimumHeight(40)
        cl.addWidget(self.to_input)

        self.subject_input = QLineEdit()
        self.subject_input.setPlaceholderText("件名")
        self.subject_input.setMinimumHeight(40)
        cl.addWidget(self.subject_input)

        # ── 本文 ──
        cl.addWidget(make_section_label("本文"))
        self.body_text = QTextEdit()
        self.body_text.setPlaceholderText("メール本文を入力してください...")
        self.body_text.setMinimumHeight(160)
        self.body_text.setFont(QFont("Meiryo", 11))
        cl.addWidget(self.body_text, 1)

        # ── 添付ファイル ──
        attach_label_row = QHBoxLayout()
        attach_label_row.addWidget(make_section_label("添付ファイル"))
        attach_label_row.addStretch()
        add_attach = QPushButton("＋  追加")
        add_attach.setObjectName("ToolButton")
        add_attach.setMinimumHeight(32)
        add_attach.setCursor(Qt.PointingHandCursor)
        add_attach.clicked.connect(self._add_attachment)
        remove_attach = QPushButton("－  削除")
        remove_attach.setObjectName("ToolButton")
        remove_attach.setMinimumHeight(32)
        remove_attach.setCursor(Qt.PointingHandCursor)
        remove_attach.clicked.connect(self._remove_attachment)
        attach_label_row.addWidget(add_attach)
        attach_label_row.addWidget(remove_attach)
        cl.addLayout(attach_label_row)

        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(90)
        self.attach_list.setFont(QFont("Meiryo", 10))
        cl.addWidget(self.attach_list)

        # ── プログレスバー ──
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(6)
        cl.addWidget(self.progress_bar)

        # ── 送信ボタン ──
        self.send_btn = QPushButton("📤  メール送信")
        self.send_btn.setObjectName("PrimaryButton")
        self.send_btn.setMinimumHeight(44)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self._send)
        cl.addWidget(self.send_btn)

    def _load_config(self):
        email = self.config.get('Email', 'sender_email', fallback='')
        pw = self.config.get('Email', 'sender_password', fallback='')
        if email and pw:
            try:
                self.email_sender = EmailSender.from_config(self.config)
                self.status_badge.setText(f"✅  {email}")
                self.status_badge.setObjectName("BadgeSuccess")
                self.status_badge.style().unpolish(self.status_badge)
                self.status_badge.style().polish(self.status_badge)
            except Exception:
                pass

    def _add_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, "添付ファイルを選択")
        if path:
            self.attachments.append(path)
            self.attach_list.addItem(path.split('/')[-1].split('\\')[-1])

    def _remove_attachment(self):
        row = self.attach_list.currentRow()
        if row >= 0:
            self.attach_list.takeItem(row)
            self.attachments.pop(row)

    def _send(self):
        to = self.to_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_text.toPlainText().strip()

        if not to or not subject or not body:
            QMessageBox.warning(self, "入力エラー", "宛先・件名・本文は必須です。")
            return
        if self.email_sender is None:
            QMessageBox.warning(self, "設定エラー",
                                "SMTP設定が未完了です。\n「⚙ SMTP設定」ボタンから設定してください。")
            return

        self.send_btn.setEnabled(False)
        self.config_btn.setEnabled(False)
        self.progress_bar.setVisible(True)

        self.worker = EmailWorker(
            self.email_sender, to, subject, body, self.attachments)
        self.worker.finished.connect(self._on_sent)
        self.worker.error.connect(self._on_error)
        self.worker.start()

    def _on_sent(self, ok: bool):
        if ok:
            QMessageBox.information(self, "送信完了", "メールを送信しました ✅")
        else:
            QMessageBox.critical(self, "送信失敗", "送信に失敗しました。設定を確認してください。")
        self._reset_ui()

    def _on_error(self, msg: str):
        QMessageBox.critical(self, "エラー", f"送信エラー:\n{msg}")
        self._reset_ui()

    def _reset_ui(self):
        self.send_btn.setEnabled(True)
        self.config_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.worker = None

    def _show_config(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("SMTP 設定")
        dlg.setMinimumWidth(420)
        form = QFormLayout(dlg)
        form.setSpacing(12)
        form.setContentsMargins(20, 20, 20, 20)

        presets = QComboBox()
        presets.addItems(["手動入力", "Gmail", "Outlook / Hotmail", "Yahoo Mail"])
        form.addRow("プリセット:", presets)

        server_edit = QLineEdit(self.config.get('Email', 'smtp_server', fallback=''))
        server_edit.setPlaceholderText("smtp.gmail.com")
        server_edit.setMinimumHeight(36)
        form.addRow("SMTPサーバー:", server_edit)

        port_edit = QLineEdit(self.config.get('Email', 'smtp_port', fallback='587'))
        port_edit.setMinimumHeight(36)
        form.addRow("ポート:", port_edit)

        email_edit = QLineEdit(self.config.get('Email', 'sender_email', fallback=''))
        email_edit.setMinimumHeight(36)
        form.addRow("送信元メール:", email_edit)

        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)
        pass_edit.setPlaceholderText("アプリパスワードを入力")
        pass_edit.setMinimumHeight(36)
        form.addRow("パスワード:", pass_edit)

        PRESETS = {
            "Gmail": ("smtp.gmail.com", "587"),
            "Outlook / Hotmail": ("smtp.office365.com", "587"),
            "Yahoo Mail": ("smtp.mail.yahoo.com", "587"),
        }
        def apply_preset(text):
            if text in PRESETS:
                server_edit.setText(PRESETS[text][0])
                port_edit.setText(PRESETS[text][1])
        presets.currentTextChanged.connect(apply_preset)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("💾  保存")
        btns.button(QDialogButtonBox.Cancel).setText("キャンセル")
        btns.accepted.connect(dlg.accept)
        btns.rejected.connect(dlg.reject)
        form.addRow(btns)

        if dlg.exec() == QDialog.Accepted:
            self.config.set('Email', 'smtp_server', server_edit.text())
            self.config.set('Email', 'smtp_port', port_edit.text())
            self.config.set('Email', 'sender_email', email_edit.text())
            if pass_edit.text():
                self.config.set('Email', 'sender_password', pass_edit.text())
            self._load_config()
            QMessageBox.information(self, "保存完了", "SMTP設定を保存しました。")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        event.accept()

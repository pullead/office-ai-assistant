# -*- coding: utf-8 -*-
"""
メール自動送信タブ - 添付ファイル付きメール
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QTextEdit, QLineEdit, QLabel, QFileDialog, QMessageBox, QListWidget)
from PySide6.QtCore import Qt
from src.core.email_sender import EmailSender
from src.config import Config


class EmailTab(QWidget):
    def __init__(self):
        super().__init__()
        self.config = Config()
        self.sender = None
        self.attachments = []  # 添付ファイルパスのリスト
        self.setup_ui()
        self.load_sender_from_config()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # 宛先
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("宛先:"))
        self.to_input = QLineEdit()
        self.to_input.setPlaceholderText("example@example.com")
        to_layout.addWidget(self.to_input)
        layout.addLayout(to_layout)

        # 件名
        sub_layout = QHBoxLayout()
        sub_layout.addWidget(QLabel("件名:"))
        self.subject_input = QLineEdit()
        sub_layout.addWidget(self.subject_input)
        layout.addLayout(sub_layout)

        # 本文
        layout.addWidget(QLabel("本文:"))
        self.body_text = QTextEdit()
        self.body_text.setPlaceholderText("メール本文を入力...")
        layout.addWidget(self.body_text)

        # 添付ファイル
        attach_layout = QHBoxLayout()
        self.add_attach_btn = QPushButton("添付ファイル追加")
        self.add_attach_btn.clicked.connect(self.add_attachment)
        self.attach_list = QListWidget()
        self.attach_list.setMaximumHeight(80)
        attach_layout.addWidget(self.add_attach_btn)
        attach_layout.addWidget(self.attach_list)
        layout.addLayout(attach_layout)

        # 送信ボタン
        self.send_btn = QPushButton("メール送信")
        self.send_btn.clicked.connect(self.send_email)
        layout.addWidget(self.send_btn)

        # 設定ボタン（簡易）
        self.config_btn = QPushButton("メール設定（SMTP）")
        self.config_btn.clicked.connect(self.show_config_dialog)
        layout.addWidget(self.config_btn)

        # ステータス表示
        self.status_label = QLabel("未送信")
        layout.addWidget(self.status_label)

    def load_sender_from_config(self):
        sender_email = self.config.get('Email', 'sender_email')
        password = self.config.get('Email', 'sender_password')
        if sender_email and password:
            self.sender = EmailSender.from_config(self.config)
            self.status_label.setText(f"設定済み: {sender_email}")
        else:
            self.status_label.setText("未設定 → 設定ボタンからSMTP情報を入力してください")

    def add_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, "添付ファイルを選択")
        if path:
            self.attachments.append(path)
            self.attach_list.addItem(path.split('/')[-1])

    def send_email(self):
        to = self.to_input.text().strip()
        subject = self.subject_input.text().strip()
        body = self.body_text.toPlainText().strip()

        if not to or not subject or not body:
            QMessageBox.warning(self, "エラー", "宛先・件名・本文は必須です。")
            return

        if self.sender is None:
            QMessageBox.warning(self, "エラー",
                                "メール設定が完了していません。設定ボタンからSMTP情報を入力してください。")
            return

        success = self.sender.send(to, subject, body, self.attachments)
        if success:
            QMessageBox.information(self, "成功", "メールを送信しました。")
            self.status_label.setText("送信完了")
        else:
            QMessageBox.critical(self, "失敗", "メール送信に失敗しました。設定を確認してください。")
            self.status_label.setText("送信失敗")

    def show_config_dialog(self):
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox
        dialog = QDialog(self)
        dialog.setWindowTitle("SMTP設定")
        form = QFormLayout(dialog)

        server_edit = QLineEdit(self.config.get('Email', 'smtp_server'))
        port_edit = QLineEdit(self.config.get('Email', 'smtp_port'))
        email_edit = QLineEdit(self.config.get('Email', 'sender_email'))
        pass_edit = QLineEdit()
        pass_edit.setEchoMode(QLineEdit.Password)

        form.addRow("SMTPサーバー:", server_edit)
        form.addRow("ポート:", port_edit)
        form.addRow("送信元メール:", email_edit)
        form.addRow("パスワード:", pass_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            self.config.set('Email', 'smtp_server', server_edit.text())
            self.config.set('Email', 'smtp_port', port_edit.text())
            self.config.set('Email', 'sender_email', email_edit.text())
            if pass_edit.text():
                self.config.set('Email', 'sender_password', pass_edit.text())
            self.load_sender_from_config()
            QMessageBox.information(self, "設定完了", "SMTP設定を保存しました。")
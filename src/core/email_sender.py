# -*- coding: utf-8 -*-
"""
メール自動送信モジュール - 添付ファイル・テンプレート対応
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import List


class EmailSender:
    """SMTPによるメール送信（Gmail/Outlook対応）"""

    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender_email
        self.password = password

    def send(self, to_addr: str, subject: str, body: str, attachments: List[str] = None) -> bool:
        """
        メール送信実行
        Returns: 成功ならTrue
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = to_addr
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain', 'utf-8'))

            # 添付ファイル処理
            if attachments:
                for file_path in attachments:
                    path = Path(file_path)
                    if not path.exists():
                        continue
                    with open(path, 'rb') as f:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(f.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename="{path.name}"')
                        msg.attach(part)

            # SMTP接続
            if self.smtp_port == 587:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.sender, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"メール送信エラー: {e}")
            return False

    @classmethod
    def from_config(cls, config):
        """設定ファイルからインスタンス生成"""
        server = config.get('Email', 'smtp_server')
        port = int(config.get('Email', 'smtp_port'))
        sender = config.get('Email', 'sender_email')
        password = config.get('Email', 'sender_password')
        return cls(server, port, sender, password)
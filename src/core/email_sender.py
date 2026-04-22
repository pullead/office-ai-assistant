# -*- coding: utf-8 -*-
"""
メール送信モジュール。
SMTP を使って本文と添付ファイルを送信する。
"""

import smtplib
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


class EmailSender:
    """SMTP ベースのメール送信クラス。"""

    def __init__(self, smtp_server: str, smtp_port: int, sender_email: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender = sender_email
        self.password = password

    def send(
        self,
        to_addr: str,
        subject: str,
        body: str,
        attachments: list[str] | None = None,
    ) -> bool:
        """メールを送信し、成功時は True を返す。"""
        try:
            message = MIMEMultipart()
            message["From"] = self.sender
            message["To"] = to_addr
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain", "utf-8"))

            for file_path in attachments or []:
                path = Path(file_path)
                if not path.exists():
                    continue

                with open(path, "rb") as file:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(file.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f'attachment; filename="{path.name}"',
                    )
                    message.attach(part)

            server = self._connect()
            server.login(self.sender, self.password)
            server.send_message(message)
            server.quit()
            return True
        except Exception as error:
            print(f"メール送信エラー: {error}")
            return False

    def _connect(self):
        """ポートに応じた SMTP 接続を返す。"""
        if self.smtp_port == 587:
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            return server
        return smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

    @classmethod
    def from_config(cls, config):
        """設定ファイルからインスタンスを生成する。"""
        server = config.get("Email", "smtp_server")
        port = int(config.get("Email", "smtp_port"))
        sender = config.get("Email", "sender_email")
        password = config.get("Email", "sender_password")
        return cls(server, port, sender, password)

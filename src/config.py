# -*- coding: utf-8 -*-
"""アプリケーション設定管理モジュール。"""

import configparser
from pathlib import Path


class Config:
    """設定クラス。"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        """設定ファイルの読み込みと初期化を行う。"""
        self.config_dir = Path.home() / ".office_ai_assistant"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.ini"

        self.parser = configparser.ConfigParser()
        if self.config_file.exists():
            self.parser.read(self.config_file, encoding="utf-8")
        else:
            self._set_defaults()
            self.save()

    def _set_defaults(self):
        """デフォルト設定を作成する。"""
        self.parser["General"] = {
            "language": "ja",
            "theme": "light",
        }
        self.parser["Email"] = {
            "smtp_server": "smtp.gmail.com",
            "smtp_port": "587",
            "sender_email": "",
            "sender_password": "",
        }
        self.parser["AI"] = {
            "openai_api_key": "",
            "use_local": "True",
        }
        self.parser["AIAPI"] = {
            "enabled": "False",
            "provider": "openrouter",
            "base_url": "https://openrouter.ai/api/v1/chat/completions",
            "model": "openrouter/free",
            "api_key": "",
            "timeout": "45",
        }

    def save(self):
        """設定ファイルへ保存する。"""
        with open(self.config_file, "w", encoding="utf-8") as file:
            self.parser.write(file)

    def get(self, section, key, fallback=None):
        """設定値を文字列として取得する。"""
        return self.parser.get(section, key, fallback=fallback)

    def set(self, section, key, value):
        """設定値を保存する。"""
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, key, value)
        self.save()

    def get_bool(self, section, key, fallback=False):
        """真偽値設定を取得する。"""
        if not self.parser.has_section(section):
            return fallback
        try:
            return self.parser.getboolean(section, key, fallback=fallback)
        except ValueError:
            return fallback

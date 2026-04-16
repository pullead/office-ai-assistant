# -*- coding: utf-8 -*-
"""
アプリケーション設定管理モジュール
"""
import os
import configparser
from pathlib import Path


class Config:
    """設定クラス（シングルトン）"""
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_config()
        return cls._instance

    def _init_config(self):
        """設定ファイルの読み込み／デフォルト値設定"""
        self.config_dir = Path.home() / ".office_ai_assistant"
        self.config_dir.mkdir(exist_ok=True)
        self.config_file = self.config_dir / "config.ini"

        self.parser = configparser.ConfigParser()
        if self.config_file.exists():
            self.parser.read(self.config_file, encoding='utf-8')
        else:
            self._set_defaults()
            self.save()

    def _set_defaults(self):
        """デフォルト設定"""
        # 言語設定（'ja', 'en', 'zh'）
        self.parser['General'] = {
            'language': 'ja',
            'theme': 'light'  # 'light' or 'dark'
        }
        # メール設定
        self.parser['Email'] = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': '587',
            'sender_email': '',
            'sender_password': ''
        }
        # AI設定（オプション）
        self.parser['AI'] = {
            'openai_api_key': '',
            'use_local': 'True'
        }

    def save(self):
        """設定をファイルに保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.parser.write(f)

    def get(self, section, key, fallback=None):
        return self.parser.get(section, key, fallback=fallback)

    def set(self, section, key, value):
        if not self.parser.has_section(section):
            self.parser.add_section(section)
        self.parser.set(section, key, value)
        self.save()
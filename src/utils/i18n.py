# -*- coding: utf-8 -*-
"""国際化（日本語・英語・中国語）"""
from src.config import Config


class I18n:
    _instance = None
    _strings = {
        'ja': {
            'ready': '準備完了',
            'error': 'エラー',
            'success': '成功',
        },
        'en': {
            'ready': 'Ready',
            'error': 'Error',
            'success': 'Success',
        },
        'zh': {
            'ready': '准备就绪',
            'error': '错误',
            'success': '成功',
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = Config()
            cls._instance.lang = cls._instance.config.get('General', 'language', fallback='ja')
        return cls._instance

    def get(self, key):
        return self._strings.get(self.lang, {}).get(key, key)
# -*- coding: utf-8 -*-
"""
簡易国際化モジュール。
このプロジェクトでは日本語を主軸にしつつ、
メニュー切り替えで英語と中国語も最低限利用できるようにする。
"""

from src.config import Config


class I18n:
    """UI 文言の管理クラス。"""

    _instance = None

    _strings = {
        "ja": {
            "app_title": "Office AI アシスタント",
            "ready": "準備完了",
            "error": "エラー",
            "success": "成功",
            "warning": "警告",
            "info": "情報",
            "confirm": "確認",
            "ok": "OK",
            "cancel": "キャンセル",
            "close": "閉じる",
            "save": "保存",
            "clear": "クリア",
            "processing": "処理中...",
            "menu_file": "ファイル",
            "menu_open": "開く",
            "menu_exit": "終了",
            "menu_edit": "編集",
            "menu_clear_log": "ステータスをクリア",
            "menu_settings": "設定",
            "menu_view": "表示",
            "menu_theme_light": "ライトテーマ",
            "menu_theme_dark": "ダークテーマ",
            "menu_fullscreen": "フルスクリーン",
            "menu_reset_window": "ウィンドウサイズをリセット",
            "menu_tools": "ツール",
            "menu_language": "言語",
            "menu_lang_ja": "日本語",
            "menu_lang_en": "English",
            "menu_lang_zh": "中文",
            "menu_help": "ヘルプ",
            "menu_usage": "使い方",
            "menu_report_bug": "不具合を報告",
            "menu_github": "GitHub を開く",
            "menu_about": "このアプリについて",
            "sidebar_subtitle": "業務を速く、見やすく、整理して扱うための統合ツール",
            "workspace_label": "Workspace: {name}",
            "sidebar_footer_title": "Quick Status",
            "sidebar_footer_hint": "AI / OCR / 可視化 / Web / Mail / Files",
            "theme_light_short": "Light",
            "theme_dark_short": "Dark",
            "ai_tab_title": "AI アシスタント",
            "ocr_tab_title": "OCR 認識",
            "viz_tab_title": "データ可視化",
            "web_tab_title": "Web 抽出",
            "email_tab_title": "メール送信",
            "file_tab_title": "ファイル整理",
        },
        "en": {
            "app_title": "Office AI Assistant",
            "ready": "Ready",
            "error": "Error",
            "success": "Success",
            "warning": "Warning",
            "info": "Info",
            "confirm": "Confirm",
            "ok": "OK",
            "cancel": "Cancel",
            "close": "Close",
            "save": "Save",
            "clear": "Clear",
            "processing": "Processing...",
            "menu_file": "File",
            "menu_open": "Open",
            "menu_exit": "Exit",
            "menu_edit": "Edit",
            "menu_clear_log": "Clear status",
            "menu_settings": "Settings",
            "menu_view": "View",
            "menu_theme_light": "Light Theme",
            "menu_theme_dark": "Dark Theme",
            "menu_fullscreen": "Fullscreen",
            "menu_reset_window": "Reset Window Size",
            "menu_tools": "Tools",
            "menu_language": "Language",
            "menu_lang_ja": "Japanese",
            "menu_lang_en": "English",
            "menu_lang_zh": "Chinese",
            "menu_help": "Help",
            "menu_usage": "How to Use",
            "menu_report_bug": "Report a Bug",
            "menu_github": "Open GitHub",
            "menu_about": "About",
            "sidebar_subtitle": "An integrated desktop workspace for faster, clearer, and more organized office operations.",
            "workspace_label": "Workspace: {name}",
            "sidebar_footer_title": "Quick Status",
            "sidebar_footer_hint": "AI / OCR / Visual / Web / Mail / Files",
            "theme_light_short": "Light",
            "theme_dark_short": "Dark",
            "ai_tab_title": "AI Assistant",
            "ocr_tab_title": "OCR",
            "viz_tab_title": "Visualization",
            "web_tab_title": "Web Extract",
            "email_tab_title": "Email",
            "file_tab_title": "File Tools",
        },
        "zh": {
            "app_title": "Office AI 助手",
            "ready": "就绪",
            "error": "错误",
            "success": "成功",
            "warning": "警告",
            "info": "信息",
            "confirm": "确认",
            "ok": "确定",
            "cancel": "取消",
            "close": "关闭",
            "save": "保存",
            "clear": "清空",
            "processing": "处理中...",
            "menu_file": "文件",
            "menu_open": "打开",
            "menu_exit": "退出",
            "menu_edit": "编辑",
            "menu_clear_log": "清除状态",
            "menu_settings": "设置",
            "menu_view": "视图",
            "menu_theme_light": "浅色主题",
            "menu_theme_dark": "深色主题",
            "menu_fullscreen": "全屏",
            "menu_reset_window": "重置窗口大小",
            "menu_tools": "工具",
            "menu_language": "语言",
            "menu_lang_ja": "日语",
            "menu_lang_en": "英语",
            "menu_lang_zh": "中文",
            "menu_help": "帮助",
            "menu_usage": "使用说明",
            "menu_report_bug": "报告问题",
            "menu_github": "打开 GitHub",
            "menu_about": "关于",
            "sidebar_subtitle": "用于更快、更清晰、更有条理地处理办公业务的一体化桌面工作台。",
            "workspace_label": "工作区: {name}",
            "sidebar_footer_title": "快速状态",
            "sidebar_footer_hint": "AI / OCR / 可视化 / Web / 邮件 / 文件",
            "theme_light_short": "浅色",
            "theme_dark_short": "深色",
            "ai_tab_title": "AI 助手",
            "ocr_tab_title": "OCR 识别",
            "viz_tab_title": "数据可视化",
            "web_tab_title": "网页提取",
            "email_tab_title": "邮件发送",
            "file_tab_title": "文件整理",
        },
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = Config()
            cls._instance._current_lang = cls._instance.config.get(
                "General", "language", fallback="ja"
            )
        return cls._instance

    def get(self, key: str) -> str:
        """現在の言語から文字列を取得する。"""
        lang_dict = self._strings.get(self._current_lang, self._strings["ja"])
        return lang_dict.get(key, self._strings["ja"].get(key, key))

    def set_language(self, lang_code: str):
        """言語を切り替える。"""
        if lang_code in self._strings:
            self._current_lang = lang_code
            self.config.set("General", "language", lang_code)

    def get_current_language(self) -> str:
        """現在の言語コードを返す。"""
        return self._current_lang

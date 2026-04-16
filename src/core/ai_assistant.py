# -*- coding: utf-8 -*-
"""
AIタスクアシスタント - 自然言語で自動化実行
"""
import subprocess
import os
from pathlib import Path


class TaskAssistant:
    """自然言語コマンドを解釈して実行"""

    def __init__(self, file_manager=None):
        self.file_manager = file_manager

    def execute_command(self, command_text: str) -> str:
        """
        コマンド実行
        例: "デスクトップを整理して" -> ファイル整理を実行
        """
        cmd = command_text.lower()

        # ファイル整理
        if "整理" in cmd and ("デスクトップ" in cmd or "desktop" in cmd):
            return self._organize_desktop()

        # スクリーンショットOCR
        elif "スクリーンショット" in cmd and ("ocr" in cmd or "テキスト" in cmd):
            return self._screenshot_ocr()

        # メール送信案内
        elif "メール" in cmd and ("送信" in cmd or "send" in cmd):
            return "メール送信機能は「メール」タブからご利用いただけます。宛先・件名・本文を入力してください。"

        # ワードクラウド生成
        elif "ワードクラウド" in cmd or "wordcloud" in cmd:
            return "ワードクラウドは「データ可視化」タブで生成できます。テキストファイルまたはExcelを選択してください。"

        else:
            return f"申し訳ありません。「{command_text}」は理解できませんでした。次のようなコマンドを試してください：\n・デスクトップを整理して\n・スクリーンショットをOCR\n・メールを送信"

    def _organize_desktop(self) -> str:
        """デスクトップのファイルを種類別に整理"""
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            desktop = Path.home() / "デスクトップ"
        if not desktop.exists():
            return "デスクトップフォルダが見つかりません。"

        # 拡張子別フォルダ作成
        categories = {
            'Images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
            'Documents': ['.pdf', '.docx', '.txt', '.xlsx', '.pptx'],
            'Archives': ['.zip', '.tar', '.gz', '.7z'],
            'Programs': ['.exe', '.msi', '.dmg', '.app']
        }

        for file in desktop.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                moved = False
                for cat, exts in categories.items():
                    if ext in exts:
                        dest = desktop / cat
                        dest.mkdir(exist_ok=True)
                        file.rename(dest / file.name)
                        moved = True
                        break
                if not moved:
                    dest = desktop / "その他"
                    dest.mkdir(exist_ok=True)
                    file.rename(dest / file.name)

        return "デスクトップの整理が完了しました。画像、ドキュメントなどに分類されました。"

    def _screenshot_ocr(self) -> str:
        """スクリーンショットを撮ってOCR"""
        try:
            from src.core.ocr_engine import InvoiceRecognizer
            from PIL import ImageGrab

            img = ImageGrab.grab()
            temp_path = Path.home() / ".office_ai_assistant" / "temp_screenshot.png"
            temp_path.parent.mkdir(exist_ok=True)
            img.save(temp_path)

            ocr = InvoiceRecognizer(lang='jpn+eng')
            text = ocr.image_to_text(str(temp_path))
            temp_path.unlink()  # 削除

            return f"スクリーンショットから抽出されたテキスト:\n{text[:500]}"
        except Exception as e:
            return f"スクリーンショットOCRに失敗しました: {str(e)}"
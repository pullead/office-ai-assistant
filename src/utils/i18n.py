# -*- coding: utf-8 -*-
"""
国際化（i18n） - 日本語・英語・中国語対応
UI上の全テキストをこのモジュールから取得する
"""
from src.config import Config


class I18n:
    _instance = None

    # 全UI文字列の辞書
    _strings = {
        'ja': {
            # 共通
            # ja セクションに追加
            'menu_edit': '編集',
            'menu_exit': '終了',
            'menu_clear_log': 'ログをクリア',
            'app_title': 'Office AI アシスタント',
            'ready': '準備完了',
            'error': 'エラー',
            'success': '成功',
            'warning': '警告',
            'info': '情報',
            'confirm': '確認',
            'ok': 'OK',
            'cancel': 'キャンセル',
            'close': '閉じる',
            'save': '保存',
            'clear': 'クリア',
            'processing': '処理中...',

            # AIタブ
            'ai_tab_title': '🤖 AIアシスタント',
            'ai_instruction': '自然言語で指示を入力してください。例：「デスクトップを整理して」「スクリーンショットをOCR」',
            'ai_placeholder': 'コマンドを入力...',
            'ai_run': '実行',
            'ai_result_placeholder': '実行結果がここに表示されます',
            'ai_no_command': 'コマンドを入力してください。',

            # OCRタブ
            'ocr_tab_title': '📄 OCR認識',
            'ocr_drop_label': '📁 ここに画像をドロップ\nまたは「画像を選択」ボタン',
            'ocr_select_btn': '📂 画像を選択',
            'ocr_no_image': '未選択',
            'ocr_run_text': '🔍 OCR実行 (全テキスト)',
            'ocr_run_invoice': '🧾 請求書認識 (構造化)',
            'ocr_result_placeholder': '認識結果がここに表示されます',
            'ocr_select_image_first': '画像を選択またはドロップしてください。',
            'ocr_only_images': '画像ファイル（.png, .jpg, .jpeg, .bmp）のみ対応しています。',
            'ocr_error': '処理中にエラーが発生しました',
            'ocr_invoice_result': '【請求書認識結果】',
            'ocr_invoice_no': '番号',
            'ocr_invoice_amount': '金額',
            'ocr_invoice_date': '日付',
            'ocr_invoice_seller': '売り手',
            'ocr_not_detected': '未検出',
            'ocr_full_text': '【全文】',

            # 可視化タブ
            'viz_tab_title': '📊 データ可視化',
            'viz_select_btn': 'Excel/テキストファイルを選択',
            'viz_excel_chart': 'Excel → 棒グラフ',
            'viz_wordcloud': 'テキスト → ワードクラウド',
            'viz_generate': '生成',
            'viz_result_placeholder': '生成結果のパスなどが表示されます',
            'viz_select_file_first': 'ファイルを選択してください。',
            'viz_chart_success': '棒グラフを生成しました。',
            'viz_wordcloud_success': 'ワードクラウドを生成しました。',
            'viz_saved_at': '保存先',

            # Webタブ
            'web_tab_title': '🌐 Web抽出',
            'web_url_placeholder': 'https://example.com',
            'web_extract_text': 'テキスト抽出',
            'web_save_pdf': 'PDF保存',
            'web_save_epub': '電子書籍保存（テキスト）',
            'web_result_placeholder': '抽出されたテキストや処理結果が表示されます',
            'web_enter_url': 'URLを入力してください。',
            'web_pdf_success': 'PDF保存完了',
            'web_epub_success': '電子書籍保存完了',

            # メールタブ
            'email_tab_title': '📧 メール自動送信',
            'email_to': '宛先:',
            'email_subject': '件名:',
            'email_body': '本文:',
            'email_attach_btn': '添付ファイル追加',
            'email_send_btn': 'メール送信',
            'email_config_btn': 'メール設定（SMTP）',
            'email_status_unset': '未設定 → 設定ボタンからSMTP情報を入力してください',
            'email_status_sent': '送信完了',
            'email_status_failed': '送信失敗',
            'email_status_sending': '送信中...',
            'email_config_title': 'SMTP設定',
            'email_server': 'SMTPサーバー:',
            'email_port': 'ポート:',
            'email_sender': '送信元メール:',
            'email_password': 'パスワード:',
            'email_config_saved': 'SMTP設定を保存しました。',
            'email_required_fields': '宛先・件名・本文は必須です。',
            'email_no_config': 'メール設定が完了していません。設定ボタンからSMTP情報を入力してください。',

            # ファイルタブ
            'file_tab_title': '📁 ファイル管理',
            'file_select_dir': '対象ディレクトリ選択',
            'file_organize': '拡張子別に整理',
            'file_rename_pattern': '置換前の文字列',
            'file_rename_replacement': '置換後の文字列',
            'file_rename_btn': '一括リネーム',
            'file_search_placeholder': '検索キーワード',
            'file_search_btn': '内容検索',
            'file_result_placeholder': '処理結果が表示されます',
            'file_select_dir_first': 'ディレクトリを選択してください。',
            'file_enter_pattern': '置換前の文字列を入力してください。',
            'file_enter_keyword': '検索キーワードを入力してください。',
            'file_search_result': '検索結果',
            'file_not_found': 'は見つかりませんでした。',

            # メニュー
            'menu_file': 'ファイル',
            'menu_view': '表示',
            'menu_help': 'ヘルプ',
            'menu_theme_light': 'ライトテーマ',
            'menu_theme_dark': 'ダークテーマ',
            'menu_language': '言語',
            'menu_lang_ja': '日本語',
            'menu_lang_en': 'English',
            'menu_lang_zh': '中文',
            'menu_about': 'このソフトウェアについて',
        },
        'en': {
            'app_title': 'Office AI Assistant',
            'ready': 'Ready',
            'error': 'Error',
            'success': 'Success',
            'warning': 'Warning',
            'info': 'Info',
            'confirm': 'Confirm',
            'ok': 'OK',
            'cancel': 'Cancel',
            'close': 'Close',
            'save': 'Save',
            'clear': 'Clear',
            'processing': 'Processing...',
            'ai_tab_title': '🤖 AI Assistant',
            'ai_instruction': 'Enter natural language command. e.g., "Organize desktop", "OCR screenshot"',
            'ai_placeholder': 'Enter command...',
            'ai_run': 'Run',
            'ai_result_placeholder': 'Result will appear here',
            'ocr_tab_title': '📄 OCR Recognition',
            'ocr_drop_label': '📁 Drop image here\nor click "Select Image"',
            'ocr_select_btn': '📂 Select Image',
            'ocr_run_text': '🔍 OCR (Full Text)',
            'ocr_run_invoice': '🧾 Invoice Recognition',
            # 必要に応じて他のキーも英語に追加可能
        },
        'zh': {
            'app_title': 'Office AI 助手',
            'ready': '准备就绪',
            'error': '错误',
            'success': '成功',
            # 必要に応じて中国語キーを追加
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.config = Config()
            cls._instance._current_lang = cls._instance.config.get('General', 'language', fallback='ja')
        return cls._instance

    def get(self, key: str) -> str:
        """キーに対応する文字列を返す"""
        lang_dict = self._strings.get(self._current_lang, self._strings['ja'])
        return lang_dict.get(key, key)

    def set_language(self, lang_code: str):
        """言語を変更（'ja', 'en', 'zh'）"""
        if lang_code in self._strings:
            self._current_lang = lang_code
            self.config.set('General', 'language', lang_code)

    def get_current_language(self) -> str:
        return self._current_lang
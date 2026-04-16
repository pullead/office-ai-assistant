# Office AI アシスタント — 作品集

## 🎯 プロジェクト概要
`python-office` をベースに開発した、**オールインワン**のオフィス自動化ツールです。  
OCR請求書認識・AIタスクアシスタント・データ可視化・Web抽出・メール自動送信など、実務で頻出する機能を**シンプルなGUI**で提供します。

## ✨ 機能一覧

| タブ | 機能 | 使用ライブラリ | アピールポイント |
|:---:|------|----------------|----------------------|
| 🤖 | **AIアシスタント**<br>自然言語で「デスクトップを整理して」など実行 | `porobot`, `subprocess` | 自然言語処理の基礎・タスク自動化 |
| 📄 | **OCR認識**<br>画像→テキスト変換<br>**請求書の自動認識**（番号・金額・日付） | `pytesseract`, `Pillow` | 画像処理・正規表現・構造化抽出 |
| 📊 | **データ可視化**<br>Excel→グラフ<br>テキスト→ワードクラウド | `matplotlib`, `wordcloud`, `pandas` | データ分析・可視化スキル |
| 🌐 | **Web抽出**<br>URLからテキスト抽出・PDF保存<br>電子書籍（テキスト）生成 | `requests`, `BeautifulSoup`, `popdf` | スクレイピング・文書変換 |
| 📧 | **メール自動送信**<br>添付ファイル・テンプレート対応 | `smtplib`, `email` | 業務コミュニケーション自動化 |
| 📁 | **ファイル管理**<br>拡張子別整理・一括リネーム・内容検索 | `pofile`, `shutil` | OS操作・ファイルシステム知識 |

---
## 🖥️ 動作環境

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11, macOS 12+, Linux (一部機能制限) |
| Python | 3.8 以上 |
| メモリ | 4GB以上（推奨） |
| ディスク | 500MB以上の空き容量 |

### 必要な外部ツール（OCR用）
- **Tesseract OCR** エンジン（無料）
  - [Windows ダウンロード](https://github.com/UB-Mannheim/tesseract/wiki)
  - macOS: `brew install tesseract tesseract-lang`
  - Linux: `sudo apt install tesseract-ocr tesseract-ocr-jpn`

---

## 🚀 インストールと起動
```bash
# 1. リポジトリクローン
git clone https://github.com/yourname/office-ai-assistant.git
cd office-ai-assistant

# 2. 依存パッケージインストール
pip install -r requirements.txt

# 3. Tesseractのインストール（OCR用）
# Windows: https://github.com/UB-Mannheim/tesseract/wiki からインストール
# macOS: brew install tesseract tesseract-lang
# Linux: sudo apt install tesseract-ocr tesseract-ocr-jpn

# 4. アプリケーション実行
python main.py
```
## 🖥️ 仮想環境（推奨）
```bash
python -m venv venv
source venv/bin/activate      # macOS/Linux
venv\Scripts\activate          # Windows
```
## 🖥️依存パッケージのインストール
```bash
pip install -r requirements.txt

```
## 🖥️Tesseractの設定（Windowsのみ）
src/core/ocr_engine.py の先頭に以下の行を追加（インストール先に合わせる）：
```bash
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```
## 🖥️アイコンの生成（初回のみ）
```bash
python generate_icons.py   # Pillowが必要（自動インストール済）

```
## 🖥️アプリケーションの起動
```bash
python main.py
```

## 📁 プロジェクト構造 
``` bash
office-ai-assistant/                    # プロジェクトルート
│
├── main.py                             # エントリーポイント
├── requirements.txt                    # 依存パッケージ一覧
├── README_JP.md                        # 日本語説明書
├── README.md                           # 英語/中国語説明書
├── .gitignore                          # Git除外設定
├── LICENSE                             # Apache 2.0ライセンス
├── generate_icons.py                   # アイコン自動生成スクリプト（実行後削除可）
│
├── src/                                # ソースコードルート
│   ├── __init__.py
│   ├── config.py                       # 設定管理
│   ├── compatibility.py                # クロスプラットフォーム互換性
│   │
│   ├── core/                           # ビジネスロジック
│   │   ├── __init__.py
│   │   ├── ai_assistant.py             # AIタスクアシスタント
│   │   ├── ocr_engine.py               # OCR + 請求書認識
│   │   ├── visualization.py            # グラフ・ワードクラウド生成
│   │   ├── web_extractor.py            # Web抽出・電子書籍生成
│   │   ├── email_sender.py             # メール自動送信
│   │   └── file_manager.py             # ファイル整理・リネーム・検索
│   │
│   ├── ui/                             # GUI関連
│   │   ├── __init__.py
│   │   ├── main_window.py              # メインウィンドウ
│   │   ├── tabs/                       # 各機能タブ
│   │   │   ├── __init__.py
│   │   │   ├── ai_tab.py               # AIアシスタントタブ
│   │   │   ├── ocr_tab.py              # OCRタブ
│   │   │   ├── viz_tab.py              # データ可視化タブ
│   │   │   ├── web_tab.py              # Web抽出タブ
│   │   │   ├── email_tab.py            # メール送信タブ
│   │   │   └── file_tab.py             # ファイル管理タブ
│   │   └── resources/                  # リソースファイル
│   │       ├── style.qss               # Qtスタイルシート
│   │       └── icons/                  # アイコンフォルダ
│   │           ├── ai.png
│   │           ├── ocr.png
│   │           ├── viz.png
│   │           ├── web.png
│   │           ├── email.png
│   │           ├── file.png
│   │           └── settings.png
│   │
│   └── utils/                          # ユーティリティ
│       ├── __init__.py
│       ├── logger.py                   # ログ設定
│       ├── file_helper.py              # ファイル補助関数
│       └── i18n.py                     # 国際化（日本語・英語・中国語）
│
├── tests/                              # 単体テスト
│   ├── test_ocr.py
│   └── test_email.py
│
├── samples/                            # サンプルファイル
│   ├── invoice_sample.jpg              # テスト用請求書画像
│   └── data.xlsx                       # テスト用Excelデータ
│
├── logs/                               # ログ保存ディレクトリ（自動生成）
│   └── app.log
│
├── output/                             # グラフ・ワードクラウド出力先
│
└── web_output/                         # Web抽出結果出力先
```
## 🧪 テストの実行
```bash
pytest tests/
```
カバレッジレポートを生成する場合：
```bash
pip install pytest-cov
pytest --cov=src tests/
```
## 📜 ライセンス  
このプロジェクトは Apache License 2.0 の下で公開されています。

## 🙏 謝辞
python-office – 素晴らしい自動化ライブラリ

Tesseract OCR – オープンソースOCRエンジン

Qt for Python (PySide6) – クロスプラットフォームGUI

## 📧 作者情報
GitHub: pullead

LinkedIn: https://github.com/pullead?tab=repositories

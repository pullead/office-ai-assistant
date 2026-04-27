# -*- coding: utf-8 -*-
"""AI API 設定ダイアログ。"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QMessageBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from src.config import Config
from src.core.llm_client import LLMClient


PROVIDER_PRESETS = {
    "siliconflow": {
        "label": "SiliconFlow（無料枠 / 低価格モデル向け）",
        "base_url": "https://api.siliconflow.com/v1",
        "model": "Qwen/Qwen2.5-7B-Instruct",
    },
    "openrouter": {
        "label": "OpenRouter（無料モデル対応）",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/auto",
    },
    "openai_compatible": {
        "label": "OpenAI 互換 API（手動設定）",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "glm": {
        "label": "Zhipu GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
    },
    "qwen": {
        "label": "Qwen（DashScope互換）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
    },
    "kimi": {
        "label": "Kimi（Moonshot）",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
    },
    "minimax": {
        "label": "MiniMax",
        "base_url": "https://api.minimax.chat/v1/text/chatcompletion_v2",
        "model": "MiniMax-Text-01",
    },
}


def show_api_settings_dialog(parent=None) -> bool:
    """AI API 設定ダイアログを表示する。"""
    config = Config()
    llm_client = LLMClient(config)
    dialog = QDialog(parent)
    dialog.setWindowTitle("AI API 設定")
    dialog.setMinimumWidth(720)

    root = QVBoxLayout(dialog)
    root.setContentsMargins(18, 18, 18, 18)
    root.setSpacing(12)

    form_wrapper = QWidget()
    form = QFormLayout(form_wrapper)
    form.setSpacing(12)

    enabled_box = QCheckBox("AI API を有効にする")
    enabled_box.setChecked(config.get_bool("AIAPI", "enabled", fallback=False))
    form.addRow(enabled_box)

    provider_combo = QComboBox()
    for key, preset in PROVIDER_PRESETS.items():
        provider_combo.addItem(preset["label"], key)

    current_provider = config.get("AIAPI", "provider", fallback="openrouter")
    for index in range(provider_combo.count()):
        if provider_combo.itemData(index) == current_provider:
            provider_combo.setCurrentIndex(index)
            break
    form.addRow("プロバイダー", provider_combo)

    base_url_edit = QLineEdit(config.get("AIAPI", "base_url", fallback=PROVIDER_PRESETS["openrouter"]["base_url"]))
    form.addRow("Base URL", base_url_edit)

    model_edit = QLineEdit(config.get("AIAPI", "model", fallback=PROVIDER_PRESETS["openrouter"]["model"]))
    form.addRow("モデル", model_edit)

    api_key_edit = QLineEdit(config.get("AIAPI", "api_key", fallback=""))
    api_key_edit.setEchoMode(QLineEdit.Password)
    form.addRow("API Key", api_key_edit)

    timeout_edit = QLineEdit(config.get("AIAPI", "timeout", fallback="60"))
    form.addRow("タイムアウト秒", timeout_edit)

    note_edit = QTextEdit()
    note_edit.setReadOnly(True)
    note_edit.setMaximumHeight(88)
    note_edit.setPlainText(
        "SiliconFlow / OpenRouter / DeepSeek / GLM / Qwen / Kimi / MiniMax などの API を切り替えられます。\n"
        "Base URL は /v1 形式でも /chat/completions 完全指定でも入力可能です。"
    )
    form.addRow("ヒント", note_edit)

    root.addWidget(form_wrapper)

    action_row = QHBoxLayout()
    test_button = QPushButton("接続テスト")
    test_button.setObjectName("SecondaryButton")
    action_row.addWidget(test_button)

    diagnose_button = QPushButton("一括診断")
    diagnose_button.setObjectName("ToolButton")
    action_row.addWidget(diagnose_button)

    apply_siliconflow_button = QPushButton("SiliconFlow 推奨を適用")
    apply_siliconflow_button.setObjectName("ToolButton")
    action_row.addWidget(apply_siliconflow_button)
    action_row.addStretch()
    root.addLayout(action_row)

    result_view = QTextEdit()
    result_view.setReadOnly(True)
    result_view.setMinimumHeight(220)
    result_view.setPlaceholderText("ここに接続テスト結果と診断結果を表示します。")
    root.addWidget(result_view)

    def apply_preset():
        provider_key = provider_combo.currentData()
        preset = PROVIDER_PRESETS.get(provider_key)
        if not preset:
            return
        base_url_edit.setText(preset["base_url"])
        model_edit.setText(preset["model"])

    provider_combo.currentIndexChanged.connect(apply_preset)

    def collect_settings() -> dict:
        return {
            "provider": provider_combo.currentData(),
            "base_url": base_url_edit.text().strip(),
            "model": model_edit.text().strip(),
            "api_key": api_key_edit.text().strip(),
            "timeout": _parse_timeout(timeout_edit.text().strip()),
        }

    def run_test():
        settings = collect_settings()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            success, message = llm_client.test_connection(**settings)
            label = "成功" if success else "失敗"
            result_view.setPlainText(f"接続テスト: {label}\n\n{message}")
        except Exception as error:
            result_view.setPlainText(f"接続テスト中に例外が発生しました。\n\n{error}")
        finally:
            QApplication.restoreOverrideCursor()

    def run_diagnose():
        settings = collect_settings()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            result = llm_client.diagnose_connection(**settings)
            result_view.setPlainText(_format_diagnostic_text(result))
        except Exception as error:
            result_view.setPlainText(f"診断中に例外が発生しました。\n\n{error}")
        finally:
            QApplication.restoreOverrideCursor()

    def apply_siliconflow_preset():
        for index in range(provider_combo.count()):
            if provider_combo.itemData(index) == "siliconflow":
                provider_combo.setCurrentIndex(index)
                apply_preset()
                result_view.setPlainText(
                    "SiliconFlow 推奨設定を適用しました。\n"
                    "必要に応じて API Key を入力し、接続テストで確認してください。"
                )
                break

    test_button.clicked.connect(run_test)
    diagnose_button.clicked.connect(run_diagnose)
    apply_siliconflow_button.clicked.connect(apply_siliconflow_preset)

    buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    root.addWidget(buttons)

    if dialog.exec() != QDialog.Accepted:
        return False

    config.set("AIAPI", "enabled", str(enabled_box.isChecked()))
    config.set("AIAPI", "provider", provider_combo.currentData())
    config.set("AIAPI", "base_url", base_url_edit.text().strip())
    config.set("AIAPI", "model", model_edit.text().strip())
    config.set("AIAPI", "api_key", api_key_edit.text().strip())
    config.set("AIAPI", "timeout", timeout_edit.text().strip() or "60")

    if enabled_box.isChecked() and not api_key_edit.text().strip():
        QMessageBox.information(
            parent,
            "確認",
            "AI API を有効にしましたが API Key は未入力です。ローカル解析のみ利用する場合はそのままでも動作します。",
        )
    return True


def _parse_timeout(value: str) -> int:
    """タイムアウト秒を安全に整数化する。"""
    try:
        parsed = int(value or "60")
    except ValueError:
        return 60
    return max(5, min(parsed, 180))


def _format_diagnostic_text(result: dict) -> str:
    """診断結果を表示向けテキストへ整形する。"""
    lines = [
        "AI API 一括診断",
        "",
        f"概要: {result.get('summary', '')}",
        f"プロバイダー: {result.get('provider', '')}",
        f"Base URL: {result.get('base_url', '')}",
        f"モデル: {result.get('model', '')}",
        "",
        "診断項目",
    ]
    for item in result.get("items", []):
        status = item.get("status", "info").upper()
        lines.append(f"- [{status}] {item.get('name', '')}: {item.get('message', '')}")

    preview = result.get("preview")
    if preview:
        lines.extend(["", "応答プレビュー", preview])

    models = result.get("available_models", [])
    if models:
        lines.extend(["", "取得できたモデル例", ", ".join(models)])

    suggestions = result.get("suggestions", [])
    if suggestions:
        lines.extend(["", "改善提案"])
        for suggestion in suggestions:
            lines.append(f"- {suggestion}")

    return "\n".join(lines)

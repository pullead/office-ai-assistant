# -*- coding: utf-8 -*-
"""AI API 設定ダイアログ。"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
)

from src.config import Config


PROVIDER_PRESETS = {
    "openrouter": {
        "label": "OpenRouter（無料モデル対応）",
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "model": "openrouter/auto",
    },
    "openai_compatible": {
        "label": "OpenAI 互換 API（手動設定）",
        "base_url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "label": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1/chat/completions",
        "model": "deepseek-chat",
    },
    "glm": {
        "label": "Zhipu GLM",
        "base_url": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
        "model": "glm-4-flash",
    },
    "qwen": {
        "label": "Qwen（DashScope互換）",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
        "model": "qwen-plus",
    },
    "kimi": {
        "label": "Kimi（Moonshot）",
        "base_url": "https://api.moonshot.cn/v1/chat/completions",
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
    dialog = QDialog(parent)
    dialog.setWindowTitle("AI API 設定")
    dialog.setMinimumWidth(560)

    form = QFormLayout(dialog)
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

    note_edit = QLineEdit("各社 API Key を入力すると、要約・OCR整理・可視化解説に利用できます。")
    note_edit.setReadOnly(True)
    form.addRow("ヒント", note_edit)

    def apply_preset():
        provider_key = provider_combo.currentData()
        preset = PROVIDER_PRESETS.get(provider_key)
        if not preset:
            return
        base_url_edit.setText(preset["base_url"])
        model_edit.setText(preset["model"])

    provider_combo.currentIndexChanged.connect(apply_preset)

    buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    form.addRow(buttons)

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

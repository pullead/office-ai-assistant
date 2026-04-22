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


def show_api_settings_dialog(parent=None) -> bool:
    """AI API 設定ダイアログを表示する。"""
    config = Config()
    dialog = QDialog(parent)
    dialog.setWindowTitle("AI API 設定")
    dialog.setMinimumWidth(520)

    form = QFormLayout(dialog)
    form.setSpacing(12)

    enabled_box = QCheckBox("AI API を有効にする")
    enabled_box.setChecked(config.get_bool("AIAPI", "enabled", fallback=False))
    form.addRow(enabled_box)

    provider_combo = QComboBox()
    provider_combo.addItem("OpenRouter（無料枠モデル向け）", "openrouter")
    provider_combo.addItem("OpenAI 互換 API", "openai_compatible")
    current_provider = config.get("AIAPI", "provider", fallback="openrouter")
    for index in range(provider_combo.count()):
        if provider_combo.itemData(index) == current_provider:
            provider_combo.setCurrentIndex(index)
            break
    form.addRow("プロバイダー", provider_combo)

    base_url_edit = QLineEdit(config.get("AIAPI", "base_url", fallback="https://openrouter.ai/api/v1/chat/completions"))
    form.addRow("Base URL", base_url_edit)

    model_edit = QLineEdit(config.get("AIAPI", "model", fallback="openrouter/free"))
    form.addRow("モデル", model_edit)

    api_key_edit = QLineEdit(config.get("AIAPI", "api_key", fallback=""))
    api_key_edit.setEchoMode(QLineEdit.Password)
    form.addRow("API Key", api_key_edit)

    timeout_edit = QLineEdit(config.get("AIAPI", "timeout", fallback="45"))
    form.addRow("タイムアウト秒", timeout_edit)

    note_edit = QLineEdit("OpenRouter では無料公開モデルや :free モデルを指定できます。")
    note_edit.setReadOnly(True)
    form.addRow("ヒント", note_edit)

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
    config.set("AIAPI", "timeout", timeout_edit.text().strip() or "45")

    if enabled_box.isChecked() and not api_key_edit.text().strip():
        QMessageBox.information(
            parent,
            "確認",
            "AI API は有効ですが API Key が未入力です。ローカル機能のみで使う場合はそのままでも構いません。",
        )
    return True

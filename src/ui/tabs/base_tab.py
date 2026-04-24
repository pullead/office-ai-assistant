# -*- coding: utf-8 -*-
"""共通タブ UI。"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget


class BaseTab(QWidget):
    """共通タブレイアウト。"""

    def __init__(self, title: str, subtitle: str, icon: str = "", parent=None):
        super().__init__(parent)
        self._build_base(title, subtitle, icon)

    def _build_base(self, title: str, subtitle: str, icon: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)

        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        header = QHBoxLayout()
        header.setSpacing(12)

        if icon:
            icon_label = QLabel()
            icon_label.setFixedSize(44, 44)
            icon_label.setAlignment(Qt.AlignCenter)
            pixmap = self._load_header_icon(icon)
            if pixmap is not None:
                icon_label.setPixmap(pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon_label.setText(icon[:2].upper())
                icon_label.setFont(QFont("Yu Gothic UI", 15, QFont.Bold))
            header.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        title_label.setFont(QFont("Meiryo", 16, QFont.Bold))

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        subtitle_label.setFont(QFont("Meiryo", 10))
        subtitle_label.setWordWrap(True)

        title_col.addWidget(title_label)
        title_col.addWidget(subtitle_label)
        header.addLayout(title_col)
        header.addStretch()
        content_layout.addLayout(header)

        self.card = QFrame()
        self.card.setObjectName("CardFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(24, 20, 24, 20)
        self.card_layout.setSpacing(14)
        content_layout.addWidget(self.card, 1)

    def _load_header_icon(self, icon_key: str) -> QPixmap | None:
        """タブ見出しのアイコン画像を読み込む。"""
        icon_name = icon_key.lower().strip()
        icon_path = Path("src/ui/resources/icons") / f"{icon_name}.png"
        if not icon_path.exists():
            return None
        pixmap = QPixmap(str(icon_path))
        if pixmap.isNull():
            return None
        return pixmap


def make_section_label(text: str) -> QLabel:
    """セクション見出しを作る。"""
    label = QLabel(text)
    label.setObjectName("SectionLabel")
    label.setFont(QFont("Meiryo", 10, QFont.Bold))
    return label


def make_badge(text: str, style: str = "Info") -> QLabel:
    """ステータス表示用バッジを作る。"""
    label = QLabel(text)
    label.setObjectName(f"Badge{style}")
    label.setFont(QFont("Meiryo", 10, QFont.Bold))
    label.setAlignment(Qt.AlignCenter)
    return label

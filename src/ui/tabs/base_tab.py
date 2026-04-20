# -*- coding: utf-8 -*-
"""
タブ基底クラス - カードフレームを提供するベースウィジェット
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QFrame, QLabel, QSizePolicy)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class BaseTab(QWidget):
    """全タブの基底クラス。ページタイトル + カードフレームレイアウトを提供"""

    def __init__(self, title: str, subtitle: str, icon: str = "", parent=None):
        super().__init__(parent)
        self._build_base(title, subtitle, icon)

    def _build_base(self, title: str, subtitle: str, icon: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 20, 24, 20)
        outer.setSpacing(16)

        # ── ページヘッダー ──
        header = QHBoxLayout()
        header.setSpacing(12)

        if icon:
            icon_label = QLabel(icon)
            icon_label.setFont(QFont("Segoe UI Emoji", 26))
            icon_label.setFixedWidth(44)
            icon_label.setAlignment(Qt.AlignCenter)
            header.addWidget(icon_label)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)
        t = QLabel(title)
        t.setObjectName("PageTitle")
        t.setFont(QFont("Meiryo", 16, QFont.Bold))
        s = QLabel(subtitle)
        s.setObjectName("PageSubtitle")
        s.setFont(QFont("Meiryo", 10))
        title_col.addWidget(t)
        title_col.addWidget(s)

        header.addLayout(title_col)
        header.addStretch()
        outer.addLayout(header)

        # ── カードフレーム ──
        self.card = QFrame()
        self.card.setObjectName("CardFrame")
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(24, 20, 24, 20)
        self.card_layout.setSpacing(14)

        outer.addWidget(self.card, 1)


def make_section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setObjectName("SectionLabel")
    lbl.setFont(QFont("Meiryo", 10, QFont.Bold))
    return lbl


def make_badge(text: str, style: str = "Info") -> QLabel:
    """style: Info / Success / Warning / Error"""
    lbl = QLabel(text)
    lbl.setObjectName(f"Badge{style}")
    lbl.setFont(QFont("Meiryo", 10, QFont.Bold))
    lbl.setAlignment(Qt.AlignCenter)
    return lbl

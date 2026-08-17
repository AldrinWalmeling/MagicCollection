from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

class SettingsPage(QWidget):

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "SettingsPage"
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )

        layout.setSpacing(
            12
        )

        self.title_label = QLabel(
            "Configurações"
        )

        self.title_label.setObjectName(
            "PageTitle"
        )

        layout.addWidget(
            self.title_label
        )

        self.description_label = QLabel(
            "Ajustes do aplicativo."
        )

        self.description_label.setObjectName(
            "PageDescription"
        )

        layout.addWidget(
            self.description_label
        )

        layout.addStretch()

        placeholder = QLabel(
            "As configurações completas chegarão em breve."
        )

        placeholder.setObjectName(
            "DeckEmptyState"
        )

        placeholder.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            placeholder,
            1,
        )

        layout.addStretch()

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from ui.theme import (
    DARK_THEME,
)


BASE_DIR = Path(__file__).resolve().parent.parent

CARD_ICON_PATH = (
    BASE_DIR
    / "assets"
    / "icons"
    / "card_icon.png"
)


def card_to_dict(card):
    """
    Normaliza uma carta para um dicionário.

    Aceita:
        - dict
        - tupla retornada pelo database
        - carta retornada pelo Scryfall

    Mantém compatibilidade com a estrutura atual.
    """

    if isinstance(card, dict):
        return dict(card)

    if not card:
        return {}

    values = list(card)

    def value(
        index,
        default=None,
    ):
        if index < len(values):
            return values[index]

        return default

    return {
        "id": value(0),
        "name": value(1),
        "printed_name": value(2),
        "lang": value(3),
        "set_name": value(4),
        "collector_number": value(5),
        "mana_cost": value(6),
        "type_line": value(7),
        "oracle_text": value(8),
        "image_url": value(9),
        "quantity": value(10, 0),
        "image_path": value(11),
        "power": value(12),
        "toughness": value(13),
        "deck_quantity": value(14, 0),
    }


class CardDetailsDialog(QDialog):

    def __init__(
        self,
        card,
        pixmap=None,
        parent=None,
    ):
        super().__init__(
            parent
        )

        card = card_to_dict(
            card
        )

        self.card = card

        self.setWindowTitle(
            card.get(
                "name",
                "Carta",
            )
        )

        self.setMinimumSize(
            860,
            680,
        )

        self.resize(
            960,
            720,
        )

        self.setStyleSheet(
            DARK_THEME
        )

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(
            28
        )

        # =====================================================
        # IMAGEM
        # =====================================================

        self.image_label = QLabel()

        self.image_label.setObjectName(
            "CardDetailImage"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setFixedSize(
            320,
            450,
        )

        self.image_label.setScaledContents(
            False
        )

        self.set_card_image(
            pixmap
        )

        layout.addWidget(
            self.image_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        # =====================================================
        # ÁREA DE INFORMAÇÕES
        # =====================================================

        scroll_area = QScrollArea()

        scroll_area.setWidgetResizable(
            True
        )

        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        info_widget = QWidget()

        info_layout = QVBoxLayout(
            info_widget
        )

        info_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        info_layout.setSpacing(
            10
        )

        # =====================================================
        # NOME
        # =====================================================

        name_label = QLabel(
            card.get(
                "name",
                "—",
            )
        )

        name_label.setObjectName(
            "CardDetailName"
        )

        name_label.setWordWrap(
            True
        )

        info_layout.addWidget(
            name_label
        )

        # =====================================================
        # NOME IMPRESSO
        # =====================================================

        printed_name = card.get(
            "printed_name"
        )

        if (
            printed_name
            and printed_name != card.get("name")
        ):
            label = QLabel(
                f"Nome impresso: {printed_name}"
            )

            label.setObjectName(
                "CardDetailField"
            )

            label.setWordWrap(
                True
            )

            info_layout.addWidget(
                label
            )

        # =====================================================
        # MANA
        # =====================================================

        mana_cost = card.get(
            "mana_cost"
        )

        if mana_cost:

            mana_widget = ManaSymbolsWidget(
                mana_cost,
                symbol_size=26,
            )

            mana_widget.setObjectName(
                "CardDetailMana"
            )

            info_layout.addWidget(
                mana_widget
            )

        # =====================================================
        # TIPO
        # =====================================================

        type_line = card.get(
            "type_line"
        )

        if type_line:

            type_label = QLabel(
                type_line
            )

            type_label.setObjectName(
                "CardDetailType"
            )

            type_label.setWordWrap(
                True
            )

            info_layout.addWidget(
                type_label
            )

        # =====================================================
        # PODER / RESISTÊNCIA
        # =====================================================

        power = card.get(
            "power"
        )

        toughness = card.get(
            "toughness"
        )

        if (
            power is not None
            or toughness is not None
        ):

            power_value = (
                power
                if power not in (None, "")
                else "?"
            )

            toughness_value = (
                toughness
                if toughness not in (None, "")
                else "?"
            )

            pt_label = QLabel(
                f"{power_value} / {toughness_value}"
            )

            pt_label.setObjectName(
                "CardDetailPT"
            )

            info_layout.addWidget(
                pt_label
            )

        # =====================================================
        # SEPARADOR
        # =====================================================

        separator = QFrame()

        separator.setObjectName(
            "CardDetailSeparator"
        )

        separator.setFrameShape(
            QFrame.Shape.HLine
        )

        separator.setFixedHeight(
            2
        )

        info_layout.addWidget(
            separator
        )

        # =====================================================
        # INFORMAÇÕES DA EDIÇÃO
        # =====================================================

        self.add_field(
            info_layout,
            "Edição",
            card.get(
                "set_name"
            ),
        )

        self.add_field(
            info_layout,
            "Código da edição",
            card.get(
                "set_code"
            ),
        )

        self.add_field(
            info_layout,
            "Número",
            card.get(
                "collector_number"
            ),
        )

        self.add_field(
            info_layout,
            "Raridade",
            card.get(
                "rarity"
            ),
        )

        self.add_field(
            info_layout,
            "Idioma",
            card.get(
                "lang"
            ),
        )

        self.add_field(
            info_layout,
            "CMC",
            card.get(
                "cmc"
            ),
        )

        self.add_field(
            info_layout,
            "Identidade de cor",
            self.format_colors(
                card.get(
                    "color_identity"
                )
            ),
        )

        # =====================================================
        # QUANTIDADE
        # =====================================================

        quantity = card.get(
            "quantity",
            0,
        )

        deck_quantity = card.get(
            "deck_quantity"
        )

        if deck_quantity is not None:

            quantity_text = (
                f"Na coleção: {quantity}\n"
                f"No deck: {deck_quantity}"
            )

        else:

            quantity_text = (
                f"Na coleção: {quantity}"
            )

        quantity_label = QLabel(
            quantity_text
        )

        quantity_label.setObjectName(
            "CardDetailQuantity"
        )

        quantity_label.setWordWrap(
            True
        )

        info_layout.addWidget(
            quantity_label
        )

        # =====================================================
        # TEXTO DA CARTA
        # =====================================================

        oracle_text = card.get(
            "oracle_text"
        )

        oracle_label = QLabel(
            oracle_text
            or "Sem texto de regras."
        )

        oracle_label.setObjectName(
            "CardDetailText"
        )

        oracle_label.setWordWrap(
            True
        )

        oracle_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        oracle_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        info_layout.addWidget(
            oracle_label,
            1,
        )

        # =====================================================
        # BOTÃO FECHAR
        # =====================================================

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )

        buttons.rejected.connect(
            self.reject
        )

        buttons.accepted.connect(
            self.accept
        )

        info_layout.addWidget(
            buttons
        )

        scroll_area.setWidget(
            info_widget
        )

        layout.addWidget(
            scroll_area,
            1,
        )

    def add_field(
        self,
        layout,
        title,
        value,
    ):

        if value in (
            None,
            "",
            "—",
        ):
            return

        label = QLabel(
            f"{title}: {value}"
        )

        label.setObjectName(
            "CardDetailField"
        )

        label.setWordWrap(
            True
        )

        layout.addWidget(
            label
        )

    def format_colors(
        self,
        colors,
    ):

        if not colors:
            return ""

        if isinstance(
            colors,
            str,
        ):
            return colors

        if isinstance(
            colors,
            (list, tuple, set),
        ):
            return ", ".join(
                str(color)
                for color in colors
            )

        return str(
            colors
        )

    def set_card_image(
        self,
        pixmap,
    ):

        if (
            pixmap
            and not pixmap.isNull()
        ):

            scaled = pixmap.scaled(
                320,
                450,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.image_label.setPixmap(
                scaled
            )

            self.image_label.setText(
                ""
            )

            return

        self.image_label.setText(
            ""
        )

        if CARD_ICON_PATH.exists():

            placeholder = QPixmap(
                str(
                    CARD_ICON_PATH
                )
            )

            if not placeholder.isNull():

                scaled = placeholder.scaled(
                    320,
                    450,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self.image_label.setPixmap(
                    scaled
                )
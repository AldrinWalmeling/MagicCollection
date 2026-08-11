import hashlib
import json
from pathlib import Path

import requests

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from services.scryfall import get_card_by_name
from services.scryfall_symbols import ManaSymbolsWidget
from ui.theme import DARK_THEME


BASE_DIR = Path(__file__).resolve().parent.parent
CARD_ICON_PATH = BASE_DIR / "assets" / "icons" / "card_icon.png"
FACE_CACHE_DIR = BASE_DIR / "cache" / "card_faces"
FACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)


LANGUAGE_LABELS = {
    "en": "English",
    "pt": "Portugues",
    "es": "Espanol",
    "fr": "Francais",
    "de": "Deutsch",
    "it": "Italiano",
    "ja": "Japanese",
    "ko": "Korean",
    "zhs": "Chinese Simplified",
    "zht": "Chinese Traditional",
    "ru": "Russian",
}


def _parse_faces(value):
    if isinstance(value, list):
        return [face for face in value if isinstance(face, dict)]

    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(parsed, list):
        return []

    return [face for face in parsed if isinstance(face, dict)]


def card_to_dict(card):
    if isinstance(card, dict):
        result = dict(card)
        result["card_faces"] = _parse_faces(result.get("card_faces"))
        return result

    if not card:
        return {}

    values = list(card)

    def value(index, default=None):
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
        "card_faces": _parse_faces(value(15)),
    }


def _has_missing_image_status(data):
    status = str(data.get("image_status") or "").casefold()
    return status in ("missing", "placeholder", "lowres")


def _best_image_url(data):
    if not isinstance(data, dict) or _has_missing_image_status(data):
        return None

    image_uris = data.get("image_uris")

    if isinstance(image_uris, dict):
        for key in ("large", "normal", "png", "border_crop", "small"):
            url = image_uris.get(key)
            if url:
                return url

    return data.get("image_url") or data.get("image_uri")


def _download_pixmap(url):
    if not url:
        return None

    cache_key = hashlib.sha1(str(url).encode("utf-8")).hexdigest()
    local_path = FACE_CACHE_DIR / f"{cache_key}.jpg"

    if local_path.exists() and local_path.stat().st_size > 0:
        pixmap = QPixmap(str(local_path))
        if not pixmap.isNull():
            return pixmap

    try:
        response = requests.get(
            url,
            timeout=8,
            headers={
                "User-Agent": "MagicCollection/1.0",
                "Accept": "image/*,*/*;q=0.8",
            },
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        if "image" not in content_type.lower():
            return None

        local_path.write_bytes(response.content)
    except Exception as error:
        print("[DETAILS] Erro ao carregar imagem:", error)
        return None

    pixmap = QPixmap(str(local_path))
    if pixmap.isNull():
        return None
    return pixmap


class DetailCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.setObjectName("DetailInfoCard")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(14, 12, 14, 12)
        self.layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("DetailInfoTitle")
        self.layout.addWidget(self.title_label)

    def set_body(self, widget):
        self.layout.addWidget(widget)


class CardDetailsDialog(QDialog):
    def __init__(self, card, pixmap=None, parent=None):
        super().__init__(parent)

        self.card = card_to_dict(card)
        self.initial_pixmap = pixmap
        self.current_face_index = 0
        self.english_card = None
        self.faces = self._build_faces(self.card)

        self.setWindowTitle(f"{self.card.get('name') or 'Carta'} - Magic Collection")
        self.setMinimumSize(1040, 760)
        self.resize(1120, 800)
        self.setStyleSheet(DARK_THEME)

        root = QHBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(28)

        left_panel = QWidget()
        left_panel.setObjectName("CardDetailLeftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setObjectName("CardDetailImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(360, 505)
        self.image_label.setScaledContents(False)
        left_layout.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.language_combo = QComboBox()
        self.language_combo.setObjectName("DetailSelector")
        self.language_combo.addItem(
            LANGUAGE_LABELS.get(self.card.get("lang") or "en", self.card.get("lang") or "English"),
            self.card.get("lang") or "en",
        )
        self.language_combo.setEnabled(False)
        left_layout.addWidget(self.language_combo)

        self.variant_combo = QComboBox()
        self.variant_combo.setObjectName("DetailSelector")
        self.variant_combo.addItem("Arte atual", 0)
        self.variant_combo.setEnabled(False)
        left_layout.addWidget(self.variant_combo)

        tools_layout = QHBoxLayout()
        tools_layout.setContentsMargins(0, 0, 0, 0)
        tools_layout.setSpacing(8)

        self.save_image_button = QPushButton("Salvar imagem")
        self.save_image_button.setEnabled(False)
        self.zoom_button = QPushButton("Zoom")
        self.zoom_button.setEnabled(False)
        tools_layout.addWidget(self.save_image_button)
        tools_layout.addWidget(self.zoom_button)
        left_layout.addLayout(tools_layout)
        left_layout.addStretch()

        root.addWidget(left_panel, 0, Qt.AlignmentFlag.AlignTop)

        right_panel = QWidget()
        right_panel.setObjectName("CardDetailRightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(14)

        self.face_buttons = QButtonGroup(self)
        self.face_buttons.setExclusive(True)
        self.face_bar = QWidget()
        self.face_bar.setObjectName("FaceSwitch")
        face_layout = QHBoxLayout(self.face_bar)
        face_layout.setContentsMargins(4, 4, 4, 4)
        face_layout.setSpacing(4)

        if len(self.faces) > 1:
            for index in range(len(self.faces)):
                button = QPushButton("Frente" if index == 0 else "Verso")
                button.setObjectName("FaceSwitchButton")
                button.setCheckable(True)
                button.setChecked(index == 0)
                button.clicked.connect(
                    lambda checked=False, face_index=index: self.set_face(face_index)
                )
                self.face_buttons.addButton(button, index)
                face_layout.addWidget(button)
            right_layout.addWidget(self.face_bar, 0, Qt.AlignmentFlag.AlignLeft)

        self.name_label = QLabel()
        self.name_label.setObjectName("CardDetailName")
        self.name_label.setWordWrap(True)
        right_layout.addWidget(self.name_label)

        self.printed_name_label = QLabel()
        self.printed_name_label.setObjectName("CardDetailField")
        self.printed_name_label.setWordWrap(True)
        right_layout.addWidget(self.printed_name_label)

        self.mana_container = QWidget()
        self.mana_container.setObjectName("CardDetailMana")
        self.mana_layout = QHBoxLayout(self.mana_container)
        self.mana_layout.setContentsMargins(0, 0, 0, 0)
        self.mana_layout.setSpacing(4)
        right_layout.addWidget(self.mana_container)

        self.type_label = QLabel()
        self.type_label.setObjectName("CardDetailType")
        self.type_label.setWordWrap(True)
        right_layout.addWidget(self.type_label)

        self.pt_label = QLabel()
        self.pt_label.setObjectName("CardDetailPT")
        right_layout.addWidget(self.pt_label, 0, Qt.AlignmentFlag.AlignLeft)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("CardDetailTabs")
        self.tabs.addTab(self._build_main_tab(), "Carta")
        self.tabs.addTab(self._build_printings_tab(), "Outras impressoes")
        self.tabs.addTab(self._build_extra_tab(), "Informacoes")
        self.tabs.addTab(self._build_history_tab(), "Historico")
        right_layout.addWidget(self.tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        right_layout.addWidget(buttons)

        root.addWidget(right_panel, 1)
        self.set_face(0)

    def _build_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        oracle_card = DetailCard("Oracle")
        self.oracle_label = QLabel()
        self.oracle_label.setObjectName("CardDetailOracle")
        self.oracle_label.setWordWrap(True)
        self.oracle_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        oracle_card.set_body(self.oracle_label)
        layout.addWidget(oracle_card)

        flavor_card = DetailCard("Flavor")
        self.flavor_label = QLabel()
        self.flavor_label.setObjectName("CardDetailFlavor")
        self.flavor_label.setWordWrap(True)
        flavor_card.set_body(self.flavor_label)
        layout.addWidget(flavor_card)

        info_grid = QGridLayout()
        info_grid.setContentsMargins(0, 0, 0, 0)
        info_grid.setSpacing(10)
        self.info_cards = {}

        for index, (title, key) in enumerate(
            (
                ("Edicao", "set_name"),
                ("Codigo", "set_code"),
                ("Numero", "collector_number"),
                ("Raridade", "rarity"),
                ("Idioma", "lang"),
                ("Quantidade", "quantity"),
            )
        ):
            card = DetailCard(title)
            label = QLabel()
            label.setObjectName("DetailInfoValue")
            label.setWordWrap(True)
            card.set_body(label)
            self.info_cards[key] = label
            info_grid.addWidget(card, index // 2, index % 2)

        layout.addLayout(info_grid)
        layout.addStretch()
        return tab

    def _build_printings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        self.printings_label = QLabel(
            "A galeria de impressoes sera preenchida quando as variantes da carta forem sincronizadas."
        )
        self.printings_label.setObjectName("CardDetailMuted")
        self.printings_label.setWordWrap(True)
        layout.addWidget(self.printings_label)
        layout.addStretch()
        return tab

    def _build_extra_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.extra_cards = {}

        fields = (
            ("Scryfall ID", "scryfall_id"),
            ("Oracle ID", "oracle_id"),
            ("Release Date", "released_at"),
            ("Frame", "frame"),
            ("Keywords", "keywords"),
            ("Color Identity", "color_identity"),
            ("Games", "games"),
            ("Legalities", "legalities"),
        )

        for index, (title, key) in enumerate(fields):
            card = DetailCard(title)
            label = QLabel()
            label.setObjectName("DetailInfoValue")
            label.setWordWrap(True)
            card.set_body(label)
            self.extra_cards[key] = label
            layout.addWidget(card, index // 2, index % 2)

        return tab

    def _build_history_tab(self):
        tab = QWidget()
        layout = QGridLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        self.history_cards = {}

        for index, (title, key) in enumerate(
            (
                ("Adicionada em", "created_at"),
                ("Ultima alteracao", "updated_at"),
                ("Na colecao", "quantity"),
                ("No deck", "deck_quantity"),
                ("Favorita", "favorite"),
                ("Tags", "custom_tags"),
            )
        ):
            card = DetailCard(title)
            label = QLabel()
            label.setObjectName("DetailInfoValue")
            label.setWordWrap(True)
            card.set_body(label)
            self.history_cards[key] = label
            layout.addWidget(card, index // 2, index % 2)

        return tab

    def _build_faces(self, card):
        faces = card.get("card_faces")
        if isinstance(faces, list) and faces:
            return faces
        return [card]

    def _face_value(self, face, key, fallback=True):
        value = face.get(key)
        if value not in (None, "", []):
            return value
        if fallback:
            value = self.card.get(key)
            if value not in (None, "", []):
                return value
        return None

    def set_face(self, face_index):
        if face_index < 0 or face_index >= len(self.faces):
            return

        self.current_face_index = face_index
        face = self.faces[face_index]

        name = self._face_value(face, "name") or "Carta"
        printed_name = self._face_value(face, "printed_name", fallback=False)

        self.name_label.setText(str(name))

        if printed_name and printed_name != name:
            self.printed_name_label.setText(f"Nome impresso: {printed_name}")
            self.printed_name_label.show()
        else:
            self.printed_name_label.clear()
            self.printed_name_label.hide()

        self._set_mana_cost(self._face_value(face, "mana_cost"))
        self._set_optional_label(self.type_label, self._face_value(face, "type_line"))
        self._set_pt(face)

        self.oracle_label.setText(
            self._face_value(face, "oracle_text", fallback=False)
            or "Sem texto de regras."
        )
        self._set_optional_label(
            self.flavor_label,
            self._face_value(face, "flavor_text", fallback=False),
        )

        self._update_info_cards()
        self._update_extra_cards()
        self._update_history_cards()
        self._set_face_image(face)

    def _set_mana_cost(self, mana_cost):
        while self.mana_layout.count():
            item = self.mana_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not mana_cost:
            self.mana_container.hide()
            return

        self.mana_container.show()
        widget = ManaSymbolsWidget(mana_cost, symbol_size=26)
        widget.setObjectName("CardDetailManaSymbols")
        self.mana_layout.addWidget(widget)
        self.mana_layout.addStretch()

    def _set_pt(self, face):
        power = self._face_value(face, "power", fallback=False)
        toughness = self._face_value(face, "toughness", fallback=False)
        loyalty = self._face_value(face, "loyalty", fallback=False)
        defense = self._face_value(face, "defense", fallback=False)

        if power not in (None, "") or toughness not in (None, ""):
            self.pt_label.setText(f"{power or '?'} / {toughness or '?'}")
            self.pt_label.show()
        elif loyalty not in (None, ""):
            self.pt_label.setText(f"Lealdade {loyalty}")
            self.pt_label.show()
        elif defense not in (None, ""):
            self.pt_label.setText(f"Defesa {defense}")
            self.pt_label.show()
        else:
            self.pt_label.clear()
            self.pt_label.hide()

    def _update_info_cards(self):
        values = {
            "set_name": self.card.get("set_name"),
            "set_code": self.card.get("set_code"),
            "collector_number": self.card.get("collector_number"),
            "rarity": self.card.get("rarity"),
            "lang": LANGUAGE_LABELS.get(self.card.get("lang"), self.card.get("lang")),
            "quantity": self._quantity_text(),
        }
        self._fill_card_labels(self.info_cards, values)

    def _update_extra_cards(self):
        values = {
            key: self.card.get(key)
            for key in self.extra_cards
        }
        self._fill_card_labels(self.extra_cards, values)

    def _update_history_cards(self):
        values = {
            key: self.card.get(key)
            for key in self.history_cards
        }
        values["quantity"] = self.card.get("quantity", 0)
        values["deck_quantity"] = self.card.get("deck_quantity", 0)
        self._fill_card_labels(self.history_cards, values)

    def _fill_card_labels(self, labels, values):
        for key, label in labels.items():
            value = values.get(key)

            if isinstance(value, dict):
                value = ", ".join(
                    f"{name}: {state}"
                    for name, state in value.items()
                    if state
                )
            elif isinstance(value, (list, tuple, set)):
                value = ", ".join(str(item) for item in value)

            if value in (None, "", [], {}):
                value = "-"

            label.setText(str(value))

    def _set_optional_label(self, label, value):
        if value in (None, "", "-"):
            label.clear()
            label.hide()
            return
        label.setText(str(value))
        label.show()

    def _quantity_text(self):
        quantity = self.card.get("quantity", 0)
        deck_quantity = self.card.get("deck_quantity")

        if deck_quantity is not None:
            return f"Colecao: {quantity}\nDeck: {deck_quantity}"

        return str(quantity)

    def _english_fallback_pixmap(self):
        name = self.card.get("name")
        if not name:
            return None

        if self.english_card is None:
            try:
                self.english_card = get_card_by_name(name, language="en")
            except Exception as error:
                print("[DETAILS] Fallback ingles falhou:", error)
                self.english_card = False

        if not self.english_card:
            return None

        english_faces = self._build_faces(self.english_card)
        if self.current_face_index < len(english_faces):
            url = _best_image_url(english_faces[self.current_face_index])
            pixmap = _download_pixmap(url)
            if pixmap and not pixmap.isNull():
                return pixmap

        return _download_pixmap(_best_image_url(self.english_card))

    def _set_face_image(self, face):
        pixmap = None
        card_lang = str(self.card.get("lang") or "en").casefold()

        if card_lang != "en":
            pixmap = self._english_fallback_pixmap()

        if not pixmap or pixmap.isNull():
            pixmap = _download_pixmap(_best_image_url(face))

        if (not pixmap or pixmap.isNull()) and card_lang != "en":
            pixmap = self._english_fallback_pixmap()

        if (
            (not pixmap or pixmap.isNull())
            and card_lang == "en"
            and self.current_face_index == 0
            and self.initial_pixmap
        ):
            pixmap = self.initial_pixmap

        if (not pixmap or pixmap.isNull()) and card_lang != "en":
            pixmap = self._english_fallback_pixmap()

        if pixmap and not pixmap.isNull():
            self.image_label.setPixmap(
                pixmap.scaled(
                    360,
                    505,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.image_label.setText("")
            return

        if CARD_ICON_PATH.exists():
            placeholder = QPixmap(str(CARD_ICON_PATH))
            if not placeholder.isNull():
                self.image_label.setPixmap(
                    placeholder.scaled(
                        280,
                        390,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                self.image_label.setText("")
                return

        self.image_label.clear()
        self.image_label.setText("Imagem indisponivel")

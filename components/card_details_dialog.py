import hashlib
import json
from pathlib import Path

import requests

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import DARK_THEME


BASE_DIR = Path(__file__).resolve().parent.parent
CARD_ICON_PATH = BASE_DIR / "assets" / "icons" / "card_icon.png"
FACE_CACHE_DIR = BASE_DIR / "cache" / "card_faces"
FACE_CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def _parse_faces(value):
    if isinstance(value, list):
        return [
            face
            for face in value
            if isinstance(face, dict)
        ]

    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(parsed, list):
        return []

    return [
        face
        for face in parsed
        if isinstance(face, dict)
    ]


def card_to_dict(card):
    if isinstance(card, dict):
        result = dict(card)
        result["card_faces"] = _parse_faces(
            result.get("card_faces")
        )
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


def _best_image_url(data):
    image_uris = data.get("image_uris")

    if isinstance(image_uris, dict):
        for key in (
            "large",
            "normal",
            "png",
            "border_crop",
            "small",
        ):
            url = image_uris.get(key)
            if url:
                return url

    return (
        data.get("image_url")
        or data.get("image_uri")
    )


def _download_pixmap(url):
    if not url:
        return None

    cache_key = hashlib.sha1(
        str(url).encode("utf-8")
    ).hexdigest()

    local_path = FACE_CACHE_DIR / f"{cache_key}.jpg"

    if local_path.exists() and local_path.stat().st_size > 0:
        pixmap = QPixmap(
            str(local_path)
        )
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

        content_type = response.headers.get(
            "content-type",
            "",
        )

        if "image" not in content_type.lower():
            return None

        local_path.write_bytes(
            response.content
        )

    except Exception as error:
        print(
            "[DETAILS] Erro ao carregar imagem da face:",
            error,
        )
        return None

    pixmap = QPixmap(
        str(local_path)
    )

    if pixmap.isNull():
        return None

    return pixmap


class CardDetailsDialog(QDialog):
    def __init__(self, card, pixmap=None, parent=None):
        super().__init__(parent)

        self.card = card_to_dict(card)
        self.initial_pixmap = pixmap
        self.current_face_index = 0
        self.faces = self._build_faces()

        self.setWindowTitle(
            self.card.get("name") or "Carta"
        )
        self.setMinimumSize(860, 680)
        self.resize(960, 720)
        self.setStyleSheet(DARK_THEME)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(28)

        self.image_label = QLabel()
        self.image_label.setObjectName("CardDetailImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(320, 450)
        self.image_label.setScaledContents(False)

        layout.addWidget(
            self.image_label,
            0,
            Qt.AlignmentFlag.AlignTop,
        )

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(10)

        self.face_buttons = QButtonGroup(self)
        self.face_buttons.setExclusive(True)

        if len(self.faces) > 1:
            face_layout = QHBoxLayout()
            face_layout.setContentsMargins(0, 0, 0, 0)
            face_layout.setSpacing(8)

            for index, face in enumerate(self.faces):
                button = QPushButton(
                    "Frente" if index == 0 else "Verso"
                )
                button.setCheckable(True)
                button.setChecked(index == 0)
                button.clicked.connect(
                    lambda checked=False, face_index=index:
                    self.set_face(face_index)
                )
                self.face_buttons.addButton(
                    button,
                    index,
                )
                face_layout.addWidget(button)

            face_layout.addStretch()
            info_layout.addLayout(face_layout)

        self.name_label = QLabel()
        self.name_label.setObjectName("CardDetailName")
        self.name_label.setWordWrap(True)
        info_layout.addWidget(self.name_label)

        self.printed_name_label = QLabel()
        self.printed_name_label.setObjectName("CardDetailField")
        self.printed_name_label.setWordWrap(True)
        info_layout.addWidget(self.printed_name_label)

        self.mana_label = QLabel()
        self.mana_label.setObjectName("CardDetailMana")
        self.mana_label.setWordWrap(True)
        info_layout.addWidget(self.mana_label)

        self.type_label = QLabel()
        self.type_label.setObjectName("CardDetailType")
        self.type_label.setWordWrap(True)
        info_layout.addWidget(self.type_label)

        self.pt_label = QLabel()
        self.pt_label.setObjectName("CardDetailPT")
        info_layout.addWidget(self.pt_label)

        separator = QFrame()
        separator.setObjectName("CardDetailSeparator")
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFixedHeight(2)
        info_layout.addWidget(separator)

        self.meta_labels = []

        for title, key in (
            ("Edicao", "set_name"),
            ("Codigo da edicao", "set_code"),
            ("Numero", "collector_number"),
            ("Raridade", "rarity"),
            ("Idioma", "lang"),
            ("CMC", "cmc"),
            ("Identidade de cor", "color_identity"),
        ):
            label = QLabel()
            label.setObjectName("CardDetailField")
            label.setWordWrap(True)
            info_layout.addWidget(label)
            self.meta_labels.append((label, title, key))

        self.quantity_label = QLabel()
        self.quantity_label.setObjectName("CardDetailQuantity")
        self.quantity_label.setWordWrap(True)
        info_layout.addWidget(self.quantity_label)

        self.oracle_label = QLabel()
        self.oracle_label.setObjectName("CardDetailText")
        self.oracle_label.setWordWrap(True)
        self.oracle_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.oracle_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        info_layout.addWidget(self.oracle_label, 1)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        info_layout.addWidget(buttons)

        scroll_area.setWidget(info_widget)
        layout.addWidget(scroll_area, 1)

        self.set_face(0)

    def _build_faces(self):
        faces = self.card.get("card_faces")

        if isinstance(faces, list) and faces:
            return faces

        return [
            self.card
        ]

    def _face_value(self, face, key, fallback=True):
        value = face.get(key)

        if value not in (None, ""):
            return value

        if fallback:
            value = self.card.get(key)
            if value not in (None, ""):
                return value

        return None

    def set_face(self, face_index):
        if face_index < 0 or face_index >= len(self.faces):
            return

        self.current_face_index = face_index
        face = self.faces[face_index]

        name = self._face_value(
            face,
            "name",
        ) or "Carta"

        printed_name = self._face_value(
            face,
            "printed_name",
            fallback=False,
        )

        self.name_label.setText(
            str(name)
        )

        if printed_name and printed_name != name:
            self.printed_name_label.setText(
                f"Nome impresso: {printed_name}"
            )
            self.printed_name_label.show()
        else:
            self.printed_name_label.clear()
            self.printed_name_label.hide()

        self._set_optional_label(
            self.mana_label,
            self._face_value(face, "mana_cost"),
        )

        self._set_optional_label(
            self.type_label,
            self._face_value(face, "type_line"),
        )

        power = self._face_value(
            face,
            "power",
            fallback=False,
        )
        toughness = self._face_value(
            face,
            "toughness",
            fallback=False,
        )

        if power not in (None, "") or toughness not in (None, ""):
            self.pt_label.setText(
                f"{power or '?'} / {toughness or '?'}"
            )
            self.pt_label.show()
        else:
            self.pt_label.clear()
            self.pt_label.hide()

        for label, title, key in self.meta_labels:
            value = self.card.get(key)

            if key == "color_identity" and isinstance(value, (list, tuple, set)):
                value = ", ".join(str(item) for item in value)

            if value in (None, "", "-"):
                label.clear()
                label.hide()
            else:
                label.setText(
                    f"{title}: {value}"
                )
                label.show()

        self.quantity_label.setText(
            self._quantity_text()
        )

        oracle_text = self._face_value(
            face,
            "oracle_text",
            fallback=False,
        )

        self.oracle_label.setText(
            oracle_text
            or "Sem texto de regras."
        )

        self._set_face_image(face)

    def _set_optional_label(self, label, value):
        if value in (None, "", "-"):
            label.clear()
            label.hide()
            return

        label.setText(
            str(value)
        )
        label.show()

    def _quantity_text(self):
        quantity = self.card.get(
            "quantity",
            0,
        )

        deck_quantity = self.card.get(
            "deck_quantity"
        )

        if deck_quantity is not None:
            return (
                f"Na colecao: {quantity}\n"
                f"No deck: {deck_quantity}"
            )

        return f"Na colecao: {quantity}"

    def _set_face_image(self, face):
        pixmap = None

        if self.current_face_index == 0 and self.initial_pixmap:
            pixmap = self.initial_pixmap

        if not pixmap or pixmap.isNull():
            pixmap = _download_pixmap(
                _best_image_url(face)
            )

        if not pixmap or pixmap.isNull():
            pixmap = _download_pixmap(
                _best_image_url(self.card)
            )

        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                320,
                450,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_label.setPixmap(scaled)
            self.image_label.setText("")
            return

        self.image_label.setText("")

        if CARD_ICON_PATH.exists():
            placeholder = QPixmap(
                str(CARD_ICON_PATH)
            )

            if not placeholder.isNull():
                self.image_label.setPixmap(
                    placeholder.scaled(
                        320,
                        450,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )

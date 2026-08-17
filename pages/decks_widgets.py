from pathlib import Path
from datetime import datetime, timezone

from PySide6.QtCore import Qt, Signal, QObject, QTimer, QRunnable, QThreadPool, QSize, QEvent
from PySide6.QtGui import QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QFrame, QScrollArea, QSizePolicy,
    QGridLayout, QDialog, QDialogButtonBox, QMenu,
)

from database import get_all_cards
from services.decks_database import get_deck_card_quantities, change_deck_card_quantity
from services.scryfall_symbols import ManaSymbolsWidget
from ui.theme import DARK_THEME


# =========================================================
# CAMINHOS DOS ASSETS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
CARD_ICON_PATH = ICONS_DIR / "card_icon.png"


# =========================================================
# HELPERS
# =========================================================

def _get_card_value(card, key, index=None, default=None):
    if isinstance(card, dict):
        return card.get(key, default)
    if index is not None:
        try:
            return card[index]
        except (IndexError, TypeError):
            pass
    return default


def _card_to_dict(card):
    if isinstance(card, dict):
        result = dict(card)
        for key in (
            "id", "name", "printed_name", "lang", "set_name",
            "collector_number", "mana_cost", "type_line", "oracle_text",
            "image_url", "image_path", "power", "toughness",
            "card_faces", "card_printings",
        ):
            result.setdefault(key, None)
        result.setdefault("quantity", 0)
        result.setdefault("deck_quantity", 0)
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
        "card_faces": value(15),
        "card_printings": value(16),
        "preferred_language": value(17),
        "preferred_variant": value(18),
        "preferred_finish": value(19),
        "preferred_image": value(20),
        "preferred_face": value(21, 0),
        "favorite": value(22, 0),
        "custom_tags": value(23),
        "last_view": value(24),
    }


def _load_pixmap(path):
    if not path:
        return None
    try:
        path = Path(path)
        if not path.exists():
            return None
        if path.stat().st_size <= 0:
            return None
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        return pixmap
    except Exception:
        return None


def _scaled_pixmap(path, width, height):
    pixmap = _load_pixmap(path)
    if not pixmap:
        return None
    return pixmap.scaled(
        width, height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )


def _display_name(card):
    name = str(_get_card_value(card, "printed_name", 2, "") or "").strip()
    if not name:
        name = str(_get_card_value(card, "name", 1, "Carta") or "Carta")
    return name


def _mana_cmc(mana_cost):
    text = str(mana_cost or "")
    if not text:
        return 0
    total = 0
    symbols = text.replace("{", " ").replace("}", " ").split()
    colors = set("WUBRG")
    for symbol in symbols:
        if symbol.upper() == "X":
            continue
        if symbol.isdigit():
            total += int(symbol)
            continue
        if symbol.upper() in colors:
            total += 1
            continue
        if "/" in symbol:
            parts = symbol.split("/")
            if any(p.upper() in colors for p in parts):
                total += 1
            for part in parts:
                if part.isdigit():
                    total += int(part)
    return total


def _card_type_category(type_line):
    text = str(type_line or "").casefold()
    if "creature" in text:
        return "creature"
    if "land" in text:
        return "land"
    return "spell"


def _format_brl(value):
    value = max(0.0, float(value or 0))
    return "R$ " + (
        f"{value:,.2f}"
        .replace(",", "§")
        .replace(".", ",")
        .replace("§", ".")
    )


def _relative_time(value):
    if not value:
        return ""
    try:
        text = str(value).strip().replace(" ", "T")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - dt).days
        if days <= 0:
            return "Atualizado hoje"
        if days == 1:
            return "Atualizado há 1 dia"
        return f"Atualizado há {days} dias"
    except Exception:
        return ""


def _deck_mana_curve(cards):
    counts = [0] * 8
    for card in cards:
        quantity = int(_get_card_value(card, "deck_quantity", 14, 0) or 0)
        if quantity <= 0:
            continue
        cmc = _mana_cmc(_get_card_value(card, "mana_cost", 6, ""))
        cmc = max(0, min(7, cmc))
        counts[cmc] += quantity
    return counts


def _deck_type_breakdown(cards):
    counts = {"creature": 0, "spell": 0, "land": 0}
    for card in cards:
        quantity = int(_get_card_value(card, "deck_quantity", 14, 0) or 0)
        if quantity <= 0:
            continue
        category = _card_type_category(_get_card_value(card, "type_line", 7, ""))
        counts[category] += quantity
    return counts


def _deck_estimated_value(cards):
    total = 0.0
    for card in cards:
        quantity = int(_get_card_value(card, "deck_quantity", 14, 0) or 0)
        if quantity <= 0:
            continue
        price = _get_card_value(card, "price_usd", None, None)
        if price is None:
            price = 0.0
        try:
            total += float(price or 0) * quantity
        except (TypeError, ValueError):
            pass
    return total


def set_deck_favorite(deck_id, favorite):
    """Persiste o estado de favorito do deck."""
    from database import get_connection
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False
    if deck_id <= 0:
        return False
    connection = get_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(
            "UPDATE decks SET favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (1 if favorite else 0, deck_id),
        )
        changed = cursor.rowcount > 0
        connection.commit()
        return changed
    except Exception as error:
        connection.rollback()
        print("[DECK] Erro ao definir favorito:", error)
        return False
    finally:
        connection.close()


# =========================================================
# DIALOG — NOME
# =========================================================

class DeckNameDialog(QDialog):
    def __init__(self, title, initial_name="", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(420)
        self.setStyleSheet(DARK_THEME)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)

        label = QLabel("Nome do deck")
        label.setObjectName("DeckNameDialogLabel")
        layout.addWidget(label)

        self.input = QLineEdit()
        self.input.setText(initial_name)
        self.input.setPlaceholderText("Ex.: Meu Commander")
        self.input.selectAll()
        layout.addWidget(self.input)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.input.returnPressed.connect(self.validate)

    def validate(self):
        if not self.input.text().strip():
            self.input.setFocus()
            return
        self.accept()

    def get_name(self):
        return self.input.text().strip()


# =========================================================
# DIALOG — ESCOLHER CAPA
# =========================================================

class DeckPreviewCardDialog(QDialog):
    def __init__(self, cards, parent=None):
        super().__init__(parent)
        self.selected_card_id = None
        self.setWindowTitle("Escolher carta de capa")
        self.setMinimumSize(700, 520)
        self.setStyleSheet(DARK_THEME)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Escolha uma carta do deck")
        title.setObjectName("DeckPreviewSelectorTitle")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        grid = QGridLayout(container)
        grid.setContentsMargins(5, 5, 5, 5)
        grid.setSpacing(14)
        columns = 5

        for index, card in enumerate(cards):
            card_id = int(_get_card_value(card, "id", 0, 0) or 0)
            button = QPushButton()
            button.setObjectName("DeckPreviewSelectorCard")
            button.setFixedSize(120, 175)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            image_path = _get_card_value(card, "image_path", 11)
            pixmap = _load_pixmap(image_path)
            if pixmap:
                scaled = pixmap.scaled(
                    110, 165,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                button.setIcon(QIcon(scaled))
                button.setIconSize(QSize(110, 165))
            else:
                button.setText(str(_get_card_value(card, "name", 1, "Carta")))

            button.clicked.connect(
                lambda checked=False, cid=card_id: self.select_card(cid)
            )
            grid.addWidget(button, index // columns, index % columns)

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def select_card(self, card_id):
        self.selected_card_id = int(card_id)
        self.accept()


# =========================================================
# PREVIEW DO DECK
# =========================================================

class DeckPreviewFrame(QFrame):
    clicked = Signal()

    def __init__(self, deck_data, preview_pixmap=None, parent=None):
        super().__init__(parent)
        self.deck_data = deck_data
        self.setObjectName("DeckPreviewFrame")
        self.setFixedSize(220, 315)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMouseTracking(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("DeckPreviewImageArea")
        self.preview_frame.setFixedHeight(260)

        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        self.image_label = QLabel()
        self.image_label.setFixedSize(180, 252)
        self.image_label.setScaledContents(False)
        self.image_label.setObjectName("DeckPreviewCard")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.image_label.setText("")

        placeholder = _scaled_pixmap(CARD_ICON_PATH, 180, 252)
        if placeholder:
            self.image_label.setPixmap(placeholder)

        preview_layout.addWidget(self.image_label)
        layout.addWidget(self.preview_frame)

        self.name_label = QLabel(deck_data["name"])
        self.name_label.setObjectName("DeckPreviewName")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        layout.addWidget(self.name_label)

        self.total_label = QLabel("0 cartas")
        self.total_label.setObjectName("DeckPreviewTotal")
        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.total_label)

        if deck_data.get("favorite"):
            badge = QLabel("★", self)
            badge.setStyleSheet(
                "background-color: rgba(10,12,17,200);"
                "color: #d4a84b;"
                "border: 1px solid #d4a84b;"
                "border-radius: 10px;"
                "font-size: 15px;"
                "font-weight: 700;"
            )
            badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge.setFixedSize(24, 24)
            badge.move(10, 10)
            badge.raise_()

        if preview_pixmap and not preview_pixmap.isNull():
            self.set_preview_image(preview_pixmap)

    def set_preview_image(self, pixmap):
        if not pixmap or pixmap.isNull():
            return
        scaled = pixmap.scaled(
            180, 252,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setText("")

    def set_total(self, total):
        total = int(total or 0)
        self.total_label.setText(f"{total} {'carta' if total == 1 else 'cartas'}")

    def enterEvent(self, event):
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


# =========================================================
# NOVO DECK
# =========================================================

class NewDeckFrame(QFrame):
    clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NewDeckFrame")
        self.setFixedSize(220, 315)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(12)

        plus = QLabel("+")
        plus.setObjectName("NewDeckPlus")
        plus.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(plus)

        text = QLabel("Novo Deck")
        text.setObjectName("NewDeckText")
        text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mousePressEvent(event)


# =========================================================
# CARTA DA COLEÇÃO (PAINEL LATERAL)
# =========================================================

class CollectionCardItem(QFrame):
    clicked = Signal(int)
    removed = Signal(int)

    def __init__(self, card, deck_quantity, parent=None):
        super().__init__(parent)
        self.card = card
        self.card_id = int(_get_card_value(card, "id", 0, 0) or 0)
        self.deck_quantity = max(0, int(deck_quantity or 0))
        self.setObjectName("CollectionDeckCard")
        self.setMinimumHeight(86)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.image_label = QLabel()
        self.image_label.setObjectName("CollectionDeckThumbnail")
        self.image_label.setFixedSize(48, 68)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setText("")
        placeholder = _scaled_pixmap(CARD_ICON_PATH, 48, 68)
        if placeholder:
            self.image_label.setPixmap(placeholder)
        layout.addWidget(self.image_label)

        info = QWidget()
        info_layout = QVBoxLayout(info)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        display_name = str(_get_card_value(card, "printed_name", 2, "") or "")
        if not display_name.strip():
            display_name = str(_get_card_value(card, "name", 1, "Carta") or "Carta")

        name = QLabel(display_name)
        name.setObjectName("CollectionDeckCardName")
        name.setWordWrap(True)
        info_layout.addWidget(name)

        self.status = QLabel()
        self.status.setObjectName("CollectionDeckCardStatus")
        info_layout.addWidget(self.status)
        info_layout.addStretch()
        layout.addWidget(info, 1)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        self.minus_button = QPushButton("−")
        self.minus_button.setObjectName("CollectionDeckRemoveButton")
        self.minus_button.setFixedSize(30, 30)
        self.minus_button.setToolTip("Remover uma cópia do deck")
        self.minus_button.clicked.connect(self.remove_one)
        controls.addWidget(self.minus_button)

        self.quantity_label = QLabel("0")
        self.quantity_label.setObjectName("CollectionDeckQuantity")
        self.quantity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.quantity_label.setFixedWidth(30)
        controls.addWidget(self.quantity_label)

        self.add_button = QPushButton("+")
        self.add_button.setObjectName("CollectionDeckAddButton")
        self.add_button.setFixedSize(30, 30)
        self.add_button.setToolTip("Adicionar uma cópia ao deck")
        self.add_button.clicked.connect(self.add_one)
        controls.addWidget(self.add_button)

        layout.addLayout(controls)

        self.update_state()
        self.load_image()

    def update_state(self):
        collection_quantity = max(
            0, int(_get_card_value(self.card, "quantity", 10, 0) or 0)
        )
        self.deck_quantity = max(0, int(self.deck_quantity or 0))
        self.status.setText(f"Coleção: {collection_quantity}   •   Deck: {self.deck_quantity}")
        self.quantity_label.setText(str(self.deck_quantity))
        self.add_button.setEnabled(self.deck_quantity < collection_quantity)
        self.minus_button.setEnabled(self.deck_quantity > 0)

    def add_one(self):
        self.clicked.emit(self.card_id)

    def remove_one(self):
        if self.deck_quantity <= 0:
            return
        self.removed.emit(self.card_id)

    def load_image(self):
        pixmap = _scaled_pixmap(_get_card_value(self.card, "image_path", 11), 48, 68)
        if not pixmap:
            return
        self.image_label.setText("")
        self.image_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.card_id)
            event.accept()
            return
        super().mousePressEvent(event)


# =========================================================
# PAINEL LATERAL — COLEÇÃO
# =========================================================

class DeckCollectionPanel(QFrame):
    closed = Signal()
    cardAdded = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DeckCollectionPanel")
        self.setFixedWidth(380)
        self.all_cards = []
        self.filtered_cards = []
        self.deck_quantities = {}
        self.deck_id = None
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_set = "all"
        self.filter_language = "all"

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(180)
        self.search_timer.timeout.connect(self.apply_search)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Adicionar cartas")
        title.setObjectName("DeckPanelTitle")
        header.addWidget(title)
        header.addStretch()

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("DeckPanelCloseButton")
        self.close_button.setFixedSize(32, 32)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setToolTip("Fechar painel")
        self.close_button.clicked.connect(self.close_panel)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        search_frame = QFrame()
        search_frame.setObjectName("DeckPanelSearchFrame")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 0, 10, 0)
        search_layout.setSpacing(8)

        search_icon = QLabel("🔎")
        search_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar na coleção...")
        self.search_input.setFrame(False)
        self.search_input.textChanged.connect(self.schedule_search)
        search_layout.addWidget(self.search_input, 1)

        self.filters_button = QPushButton("Filtros")
        self.filters_button.setObjectName("DeckPanelFiltersButton")
        self.filters_button.setFixedWidth(70)
        self.filters_button.clicked.connect(self.show_filters_menu)
        search_layout.addWidget(self.filters_button)
        layout.addWidget(search_frame)

        self.status_label = QLabel("Escolha uma carta para adicionar.")
        self.status_label.setObjectName("DeckPanelStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(7)
        self.list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.list_container)
        layout.addWidget(self.scroll_area, 1)

    def open(self, deck_id):
        try:
            deck_id = int(deck_id)
        except (TypeError, ValueError):
            return
        if deck_id <= 0:
            return
        self.deck_id = deck_id
        self.search_timer.stop()
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.load_cards()
        self.show()
        self.raise_()
        self.search_input.setFocus()

    def load_cards(self):
        self.all_cards = list(get_all_cards() or [])
        self.deck_quantities = get_deck_card_quantities(self.deck_id)
        self.apply_search()

    def schedule_search(self, _text):
        self.search_timer.start()

    def show_filters_menu(self):
        menu = QMenu(self)

        color_menu = menu.addMenu("Cor")
        color_menu.addAction("Todas", lambda: self.set_filter_color("all"))
        color_menu.addSeparator()
        for label, code in (("Branco", "W"), ("Azul", "U"), ("Preto", "B"),
                            ("Vermelho", "R"), ("Verde", "G"), ("Incolor", "C"),
                            ("Multicolorido", "M")):
            color_menu.addAction(label, lambda checked=False, value=code: self.set_filter_color(value))

        type_menu = menu.addMenu("Tipo")
        type_menu.addAction("Todos", lambda: self.set_filter_type("all"))
        type_menu.addSeparator()
        for label, code in (("Criatura", "creature"), ("Instantânea", "instant"),
                            ("Feitiço", "sorcery"), ("Encantamento", "enchantment"),
                            ("Artefato", "artifact"), ("Planeswalker", "planeswalker"),
                            ("Terreno", "land")):
            type_menu.addAction(label, lambda checked=False, value=code: self.set_filter_type(value))

        language_menu = menu.addMenu("Idioma")
        language_menu.addAction("Todos", lambda: self.set_filter_language("all"))
        language_menu.addSeparator()
        languages = {"Inglês": "en", "Português": "pt", "Espanhol": "es", "Francês": "fr",
                     "Alemão": "de", "Italiano": "it", "Japonês": "ja", "Coreano": "ko",
                     "Chinês Simplificado": "zhs", "Chinês Tradicional": "zht", "Russo": "ru"}
        for label, code in languages.items():
            language_menu.addAction(label, lambda checked=False, value=code: self.set_filter_language(value))

        set_menu = menu.addMenu("Edição")
        set_menu.addAction("Todas", lambda: self.set_filter_set("all"))
        set_menu.addSeparator()
        sets = sorted(
            {str(_get_card_value(c, "set_name", 4, "") or "") for c in self.all_cards
             if _get_card_value(c, "set_name", 4, "")},
            key=str.casefold,
        )
        for set_name in sets:
            set_menu.addAction(set_name, lambda checked=False, value=set_name: self.set_filter_set(value))

        menu.addSeparator()
        menu.addAction("Limpar filtros", self.clear_filters)

        menu.exec(self.filters_button.mapToGlobal(self.filters_button.rect().bottomLeft()))

    def set_filter_color(self, color):
        self.filter_color = color
        self.apply_search()

    def set_filter_type(self, card_type):
        self.filter_type = card_type
        self.apply_search()

    def set_filter_set(self, set_name):
        self.filter_set = set_name
        self.apply_search()

    def set_filter_language(self, language):
        self.filter_language = language
        self.apply_search()

    def clear_filters(self):
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_set = "all"
        self.filter_language = "all"
        self.apply_search()

    def apply_search(self):
        text = self.search_input.text().strip().casefold()
        filtered = []
        for card in self.all_cards:
            if text:
                searchable = " ".join(
                    (
                        str(_get_card_value(card, "name", 1, "") or ""),
                        str(_get_card_value(card, "printed_name", 2, "") or ""),
                        str(_get_card_value(card, "set_name", 4, "") or ""),
                        str(_get_card_value(card, "collector_number", 5, "") or ""),
                        str(_get_card_value(card, "type_line", 7, "") or ""),
                    )
                ).casefold()
                if text not in searchable:
                    continue
            if self.filter_color != "all":
                mana_cost = str(_get_card_value(card, "mana_cost", 6, "") or "").upper()
                colors = set()
                for color_symbol in ("{W}", "{U}", "{B}", "{R}", "{G}"):
                    if color_symbol in mana_cost:
                        colors.add(color_symbol[1])
                if self.filter_color == "C":
                    if colors:
                        continue
                elif self.filter_color == "M":
                    if len(colors) < 2:
                        continue
                elif self.filter_color not in colors:
                    continue
            if self.filter_type != "all":
                type_line = str(_get_card_value(card, "type_line", 7, "") or "").casefold()
                if self.filter_type.casefold() not in type_line:
                    continue
            if self.filter_set != "all":
                set_name = str(_get_card_value(card, "set_name", 4, "") or "")
                if set_name.casefold() != self.filter_set.casefold():
                    continue
            if self.filter_language != "all":
                language = str(_get_card_value(card, "lang", 3, "") or "").casefold()
                if language != self.filter_language.casefold():
                    continue
            filtered.append(card)
        self.filtered_cards = filtered
        self.render_cards(filtered)

    def render_cards(self, cards):
        self.clear_list()
        visible_count = 0
        for card in cards:
            collection_quantity = max(0, int(_get_card_value(card, "quantity", 10, 0) or 0))
            if collection_quantity <= 0:
                continue
            card_id = int(_get_card_value(card, "id", 0, 0) or 0)
            deck_quantity = int(self.deck_quantities.get(card_id, 0) or 0)
            item = CollectionCardItem(card, deck_quantity)
            item.clicked.connect(self.add_card)
            item.removed.connect(self.remove_card)
            self.list_layout.addWidget(item)
            visible_count += 1
        if visible_count == 0:
            empty = QLabel("Nenhuma carta encontrada.")
            empty.setObjectName("DeckPanelEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setWordWrap(True)
            self.list_layout.addWidget(empty)
        self.list_layout.addStretch()

    def clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def add_card(self, card_id):
        if not self.deck_id:
            return
        try:
            card_id = int(card_id)
        except (TypeError, ValueError):
            return
        current_quantity = max(0, int(self.deck_quantities.get(card_id, 0) or 0))
        collection_quantity = 0
        for card in self.filtered_cards:
            try:
                current_id = int(_get_card_value(card, "id", 0, 0) or 0)
            except (TypeError, ValueError):
                continue
            if current_id != card_id:
                continue
            collection_quantity = max(0, int(_get_card_value(card, "quantity", 10, 0) or 0))
            break
        if collection_quantity > 0 and current_quantity >= collection_quantity:
            self.status_label.setText("Limite da coleção atingido.")
            return
        if not change_deck_card_quantity(self.deck_id, card_id, 1):
            return
        self.deck_quantities[card_id] = current_quantity + 1
        self.status_label.setText("Carta adicionada ao deck.")
        self.cardAdded.emit(card_id)
        self.render_cards(self.filtered_cards)

    def remove_card(self, card_id):
        if not self.deck_id:
            return
        current = int(self.deck_quantities.get(card_id, 0) or 0)
        if current <= 0:
            return
        if not change_deck_card_quantity(self.deck_id, card_id, -1):
            return
        new_quantity = max(0, current - 1)
        if new_quantity <= 0:
            self.deck_quantities.pop(card_id, None)
        else:
            self.deck_quantities[card_id] = new_quantity
        self.status_label.setText("Carta removida do deck.")
        self.cardAdded.emit(card_id)
        self.render_cards(self.filtered_cards)

    def close_panel(self):
        self.search_timer.stop()
        self.hide()
        self.closed.emit()

    def closeEvent(self, event):
        self.search_timer.stop()
        self.hide()
        self.closed.emit()
        event.ignore()


# =========================================================
# WORKER — SCRYFALL
# =========================================================

class ScryfallWorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class ScryfallWorker(QRunnable):
    def __init__(self, text, filters=None):
        super().__init__()
        self.text = str(text or "").strip()
        self.filters = dict(filters or {})
        self.signals = ScryfallWorkerSignals()

    def run(self):
        try:
            query_parts = []
            if self.text:
                query_parts.append(self.text)
            color = self.filters.get("color")
            if color and color != "all":
                if color == "M":
                    query_parts.append("c:m")
                elif color == "C":
                    query_parts.append("c:c")
                else:
                    query_parts.append(f"c:{color.lower()}")
            card_type = self.filters.get("type")
            if card_type and card_type != "all":
                query_parts.append(f"t:{card_type}")
            subtype = self.filters.get("subtype")
            if subtype:
                query_parts.append(f"t:{subtype}")
            rarity = self.filters.get("rarity")
            if rarity and rarity != "all":
                query_parts.append(f"r:{rarity}")
            set_code = self.filters.get("set")
            if set_code:
                query_parts.append(f"set:{set_code}")
            cmc = self.filters.get("cmc")
            if cmc not in (None, "", "all"):
                query_parts.append(f"cmc={cmc}")
            color_identity = self.filters.get("color_identity")
            if color_identity and color_identity != "all":
                query_parts.append(f"id:{color_identity.lower()}")
            language = self.filters.get("language")
            if language and language != "all":
                query_parts.append(f"lang:{language}")

            query = " ".join(part for part in query_parts if part)

            from services.scryfall import search_cards

            cards = search_cards(query, language="all", unique="prints", order="name")
            results = []
            for card in cards[:30]:
                image_uris = card.get("image_uris") or {}
                results.append({
                    "name": card.get("name") or "Carta",
                    "printed_name": card.get("printed_name") or "",
                    "set_name": card.get("set_name") or "",
                    "set": card.get("set") or "",
                    "collector_number": card.get("collector_number") or "",
                    "mana_cost": card.get("mana_cost") or "",
                    "cmc": card.get("cmc"),
                    "type_line": card.get("type_line") or "",
                    "oracle_text": card.get("oracle_text") or "",
                    "power": card.get("power"),
                    "toughness": card.get("toughness"),
                    "rarity": card.get("rarity") or "",
                    "colors": card.get("colors") or [],
                    "color_identity": card.get("color_identity") or [],
                    "lang": card.get("lang") or "",
                    "image_url": image_uris.get("normal") or "",
                    "scryfall_id": card.get("id") or "",
                })
            self.signals.finished.emit(results)
        except Exception as error:
            self.signals.error.emit(str(error))


# =========================================================
# PAINEL LATERAL — MAGIC / SCRYFALL
# =========================================================

class DeckScryfallPanel(QFrame):
    closed = Signal()
    cardAdded = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DeckScryfallPanel")
        self.setFixedWidth(380)
        self.deck_id = None
        self.all_cards = []
        self.filtered_cards = []
        self._results = []
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_subtype = ""
        self.filter_rarity = "all"
        self.filter_set = ""
        self.filter_cmc = "all"
        self.filter_color_identity = "all"
        self.filter_language = "all"

        self.search_pool = QThreadPool(self)
        self.search_pool.setMaxThreadCount(4)
        self.current_search_id = 0
        self._active_workers = {}

        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.setInterval(300)
        self.search_timer.timeout.connect(self.search_scryfall)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        header = QHBoxLayout()
        title = QLabel("Magic / Scryfall")
        title.setObjectName("DeckPanelTitle")
        header.addWidget(title)
        header.addStretch()

        self.close_button = QPushButton("X")
        self.close_button.setObjectName("DeckPanelCloseButton")
        self.close_button.setFixedSize(32, 32)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.setToolTip("Fechar painel")
        self.close_button.clicked.connect(self.close_panel)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        description = QLabel("Pesquise cartas do Magic diretamente no Scryfall.")
        description.setObjectName("DeckPanelStatus")
        description.setWordWrap(True)
        layout.addWidget(description)

        search_frame = QFrame()
        search_frame.setObjectName("DeckPanelSearchFrame")
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(10, 0, 10, 0)
        search_layout.setSpacing(8)

        search_icon = QLabel("🔎")
        search_layout.addWidget(search_icon)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar carta...")
        self.search_input.setFrame(False)
        self.search_input.textChanged.connect(self.schedule_search)
        self.search_input.installEventFilter(self)
        search_layout.addWidget(self.search_input, 1)

        self.filters_button = QPushButton("Filtros")
        self.filters_button.setObjectName("DeckPanelFiltersButton")
        self.filters_button.setFixedWidth(70)
        self.filters_button.clicked.connect(self.show_filters_menu)
        search_layout.addWidget(self.filters_button)
        layout.addWidget(search_frame)

        self.status_label = QLabel("Digite o nome de uma carta.")
        self.status_label.setObjectName("DeckPanelStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.results_list = QListWidget()
        self.results_list.setObjectName("DeckPanelResultsList")
        self.results_list.itemClicked.connect(self.add_selected_card)
        layout.addWidget(self.results_list, 1)

    def add_selected_card(self, item):
        if item is None:
            return
        card = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(card, dict):
            self.status_label.setText("Dados da carta inválidos.")
            return
        self.add_card(card)

    def show_filters_menu(self):
        menu = QMenu(self)

        color_menu = menu.addMenu("Cor")
        color_menu.addAction("Todas", lambda: self.set_filter_color("all"))
        for label, code in (("Branco", "W"), ("Azul", "U"), ("Preto", "B"),
                            ("Vermelho", "R"), ("Verde", "G"), ("Incolor", "C"),
                            ("Multicolorido", "M")):
            color_menu.addAction(label, lambda checked=False, value=code: self.set_filter_color(value))

        type_menu = menu.addMenu("Tipo")
        type_menu.addAction("Todos", lambda: self.set_filter_type("all"))
        for label, code in (("Criatura", "creature"), ("Instantânea", "instant"),
                            ("Feitiço", "sorcery"), ("Encantamento", "enchantment"),
                            ("Artefato", "artifact"), ("Planeswalker", "planeswalker"),
                            ("Terreno", "land")):
            type_menu.addAction(label, lambda checked=False, value=code: self.set_filter_type(value))

        menu.addAction("Subtipo...", self.set_filter_subtype)

        rarity_menu = menu.addMenu("Raridade")
        rarity_menu.addAction("Todas", lambda: self.set_filter_rarity("all"))
        for label, code in (("Comum", "common"), ("Incomum", "uncommon"),
                            ("Rara", "rare"), ("Mítica", "mythic")):
            rarity_menu.addAction(label, lambda checked=False, value=code: self.set_filter_rarity(value))

        menu.addAction("Edição / Set...", self.set_filter_set)

        cmc_menu = menu.addMenu("Valor de Mana")
        cmc_menu.addAction("Qualquer", lambda: self.set_filter_cmc("all"))
        for value in range(0, 11):
            cmc_menu.addAction(str(value), lambda checked=False, value=value: self.set_filter_cmc(value))

        identity_menu = menu.addMenu("Identidade de cor")
        identity_menu.addAction("Todas", lambda: self.set_filter_identity("all"))
        for value in ("W", "U", "B", "R", "G", "WU", "UB", "BR", "RG", "GW",
                      "WUB", "UBR", "BRG", "RGW", "GWU",
                      "WUBR", "UBRG", "BRGW", "RGWU", "GWUB", "WUBRG"):
            identity_menu.addAction(value, lambda checked=False, value=value: self.set_filter_identity(value))

        language_menu = menu.addMenu("Idioma")
        language_menu.addAction("Todos", lambda: self.set_filter_language("all"))
        languages = {"Inglês": "en", "Português": "pt", "Espanhol": "es", "Francês": "fr",
                     "Alemão": "de", "Italiano": "it", "Japonês": "ja", "Coreano": "ko",
                     "Chinês Simplificado": "zhs", "Chinês Tradicional": "zht", "Russo": "ru"}
        for label, code in languages.items():
            language_menu.addAction(label, lambda checked=False, value=code: self.set_filter_language(value))

        menu.addSeparator()
        menu.addAction("Limpar filtros", self.clear_filters_menu)

        menu.exec(self.filters_button.mapToGlobal(self.filters_button.rect().bottomLeft()))

    def set_filter_color(self, color):
        self.filter_color = color
        self.perform_search_again()

    def set_filter_type(self, card_type):
        self.filter_type = card_type
        self.perform_search_again()

    def set_filter_rarity(self, rarity):
        self.filter_rarity = rarity
        self.perform_search_again()

    def set_filter_subtype(self):
        from PySide6.QtWidgets import QInputDialog
        value, accepted = QInputDialog.getText(self, "Subtipo", "Digite o subtipo da carta:")
        if not accepted:
            return
        self.filter_subtype = value.strip()
        self.perform_search_again()

    def set_filter_set(self):
        from PySide6.QtWidgets import QInputDialog
        value, accepted = QInputDialog.getText(self, "Edição", "Digite o código da edição:")
        if not accepted:
            return
        self.filter_set = value.strip()
        self.perform_search_again()

    def set_filter_cmc(self, value):
        self.filter_cmc = value
        self.perform_search_again()

    def set_filter_identity(self, value):
        self.filter_color_identity = value
        self.perform_search_again()

    def set_filter_language(self, value):
        self.filter_language = value
        self.perform_search_again()

    def _build_filters(self):
        return {
            "color": self.filter_color,
            "type": self.filter_type,
            "subtype": self.filter_subtype,
            "rarity": self.filter_rarity,
            "set": self.filter_set,
            "cmc": self.filter_cmc,
            "color_identity": self.filter_color_identity,
            "language": self.filter_language,
        }

    def perform_search_again(self):
        text = self.search_input.text().strip()
        if not text:
            return
        self.current_search_id += 1
        search_id = self.current_search_id
        worker = ScryfallWorker(text, self._build_filters())
        self._active_workers[search_id] = worker
        worker.signals.finished.connect(
            lambda cards, sid=search_id: self._scryfall_search_finished(sid, cards)
        )
        worker.signals.error.connect(
            lambda error, sid=search_id: self._scryfall_search_error(sid, error)
        )
        self.search_pool.start(worker)

    def clear_filters_menu(self):
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_subtype = ""
        self.filter_rarity = "all"
        self.filter_set = ""
        self.filter_cmc = "all"
        self.filter_color_identity = "all"
        self.filter_language = "all"
        self.perform_search_again()

    def open(self, deck_id):
        try:
            deck_id = int(deck_id)
        except (TypeError, ValueError):
            return
        if deck_id <= 0:
            return
        self.deck_id = deck_id
        self.search_timer.stop()
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.all_cards = []
        self.filtered_cards = []
        self._results = []
        try:
            self.results_list.clear()
        except RuntimeError:
            pass
        self.status_label.setText("Digite o nome de uma carta.")
        self.show()
        self.raise_()
        self.search_input.setFocus()

    def schedule_search(self, _text):
        self.search_timer.stop()
        text = self.search_input.text().strip()
        if not text:
            self.results_list.clear()
            self.status_label.setText("Digite o nome de uma carta.")
            return
        self.status_label.setText("Pesquisando...")
        self.search_timer.start()

    def search_scryfall(self):
        text = self.search_input.text().strip()
        if not text:
            self.results_list.clear()
            self.status_label.setText("Digite o nome de uma carta.")
            return
        self.current_search_id += 1
        search_id = self.current_search_id
        self.results_list.clear()
        self.status_label.setText("Pesquisando no Scryfall...")
        worker = ScryfallWorker(text, self._build_filters())
        self._active_workers[search_id] = worker
        worker.signals.finished.connect(
            lambda cards, sid=search_id: self._scryfall_search_finished(sid, cards)
        )
        worker.signals.error.connect(
            lambda error, sid=search_id: self._scryfall_search_error(sid, error)
        )
        self.search_pool.start(worker)

    def _scryfall_search_finished(self, search_id, cards):
        self._active_workers.pop(search_id, None)
        if search_id != self.current_search_id:
            return
        if not self.isVisible():
            return
        cards = list(cards or [])
        self.all_cards = cards
        self.filtered_cards = cards
        self._results = cards
        if not cards:
            self.status_label.setText("Nenhuma carta encontrada.")
        else:
            self.status_label.setText(
                f"{len(cards)} " + ("resultado encontrado." if len(cards) == 1 else "resultados encontrados.")
            )
        self.display_results()

    def _scryfall_search_error(self, search_id, error):
        self._active_workers.pop(search_id, None)
        if search_id != self.current_search_id:
            return
        self.results_list.clear()
        self.status_label.setText("Erro ao pesquisar no Scryfall.")
        print("[SCRYFALL] Erro:", error)

    def display_results(self):
        try:
            self.results_list.clear()
        except RuntimeError:
            return
        for card in self.filtered_cards:
            name = str(card.get("name", "Carta") or "Carta")
            set_name = str(card.get("set_name", "") or "")
            collector_number = str(card.get("collector_number", "") or "")
            text = name
            if set_name:
                text += f"\n{set_name}"
            if collector_number:
                text += f" • {collector_number}"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, card)
            self.results_list.addItem(item)

    def add_card(self, card):
        if not self.deck_id:
            self.status_label.setText("Nenhum deck está aberto.")
            return
        if not isinstance(card, dict):
            self.status_label.setText("Dados da carta inválidos.")
            return
        name = str(card.get("name", "Carta") or "Carta").strip()
        scryfall_id = str(card.get("scryfall_id", "") or "").strip()
        if not name:
            self.status_label.setText("A carta não possui um nome válido.")
            return
        if not scryfall_id:
            self.status_label.setText("A carta não possui um Scryfall ID válido.")
            return
        self.status_label.setText(f"Adicionando {name}...")

        from database import ensure_card_exists
        from services.decks_database import add_card_to_deck

        card_id = ensure_card_exists(card)
        if not card_id:
            self.status_label.setText(f"Não foi possível preparar {name} para o deck.")
            return
        if not add_card_to_deck(self.deck_id, card_id, 1):
            self.status_label.setText(f"Não foi possível adicionar {name} ao deck.")
            return
        self.status_label.setText(f"{name} adicionada ao deck.")
        print("[SCRYFALL] Carta adicionada ao deck:", name, "| card_id=", card_id, "| deck_id=", self.deck_id)
        self.cardAdded.emit(int(card_id))

    def eventFilter(self, obj, event):
        if obj is self.search_input and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Down:
                self._move_selection(1)
                return True
            if key == Qt.Key.Key_Up:
                self._move_selection(-1)
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                item = self.results_list.currentItem()
                if item is not None:
                    self.add_selected_card(item)
                return True
            if key == Qt.Key.Key_Escape:
                self.close_panel()
                return True
        return super().eventFilter(obj, event)

    def _move_selection(self, direction):
        count = self.results_list.count()
        if count <= 0:
            return
        row = self.results_list.currentRow()
        if row < 0:
            row = 0 if direction > 0 else count - 1
        else:
            row = max(0, min(row + direction, count - 1))
        self.results_list.setCurrentRow(row)
        self.results_list.scrollToItem(self.results_list.currentItem())

    def close_panel(self):
        self.current_search_id += 1
        self.search_timer.stop()
        self.hide()
        self.closed.emit()

    def closeEvent(self, event):
        self.current_search_id += 1
        self.search_timer.stop()
        self.hide()
        self.closed.emit()
        event.ignore()


# =========================================================
# LISTA DE CARTAS DO DECK
# =========================================================

class DeckListCardFrame(QFrame):
    selected = Signal(int)
    detailsRequested = Signal(int)
    quantityChanged = Signal(int, int)
    moveToSideboard = Signal(int)

    def __init__(self, card, quantity, in_sideboard=False, parent=None):
        super().__init__(parent)
        self.card = card
        self.card_id = int(_get_card_value(card, "id", 0, 0) or 0)
        self.quantity = max(0, int(quantity or 0))
        self.in_sideboard = bool(in_sideboard)
        self._selected = False

        self.setObjectName("DeckListCard")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(62)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(9)

        self.qty_label = QLabel(str(self.quantity))
        self.qty_label.setObjectName("DeckListQuantity")
        self.qty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_label.setFixedWidth(34)
        layout.addWidget(self.qty_label)

        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("DeckListThumbnail")
        self.thumb_label.setFixedSize(40, 56)
        self.thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.thumb_label.setText("")
        placeholder = _scaled_pixmap(CARD_ICON_PATH, 40, 56)
        if placeholder:
            self.thumb_label.setPixmap(placeholder)
        layout.addWidget(self.thumb_label)

        info = QVBoxLayout()
        info.setContentsMargins(0, 0, 0, 0)
        info.setSpacing(1)

        self.name_label = QLabel(_display_name(card))
        self.name_label.setObjectName("DeckListName")
        self.name_label.setWordWrap(True)
        info.addWidget(self.name_label)

        sub_parts = []
        type_line = _get_card_value(card, "type_line", 7, "") or ""
        set_name = _get_card_value(card, "set_name", 4, "") or ""
        if type_line:
            sub_parts.append(str(type_line))
        if set_name:
            sub_parts.append(str(set_name))

        self.sub_label = QLabel("  •  ".join(sub_parts))
        self.sub_label.setObjectName("DeckListSub")
        self.sub_label.setWordWrap(True)
        info.addWidget(self.sub_label)
        layout.addLayout(info, 1)

        mana_cost = _get_card_value(card, "mana_cost", 6, "") or ""
        self.mana_widget = ManaSymbolsWidget(str(mana_cost), 15, self)
        layout.addWidget(self.mana_widget, 0, Qt.AlignmentFlag.AlignVCenter)

        controls = QHBoxLayout()
        controls.setContentsMargins(0, 0, 0, 0)
        controls.setSpacing(4)

        if not in_sideboard:
            self.minus_button = QPushButton("−")
            self.minus_button.setObjectName("DeckActionSmall")
            self.minus_button.setFixedSize(26, 26)
            self.minus_button.clicked.connect(lambda: self._change_quantity(-1))
            controls.addWidget(self.minus_button)

            self.plus_button = QPushButton("+")
            self.plus_button.setObjectName("DeckActionSmall")
            self.plus_button.setFixedSize(26, 26)
            self.plus_button.clicked.connect(lambda: self._change_quantity(1))
            controls.addWidget(self.plus_button)

            self.sb_button = QPushButton("SB")
            self.sb_button.setObjectName("SideboardMoveButton")
            self.sb_button.setToolTip("Mover para o sideboard")
            self.sb_button.clicked.connect(lambda: self.moveToSideboard.emit(self.card_id))
            controls.addWidget(self.sb_button)
        else:
            self.deck_button = QPushButton("Deck")
            self.deck_button.setObjectName("SideboardMoveButton")
            self.deck_button.setToolTip("Mover para o deck principal")
            self.deck_button.clicked.connect(
                lambda: self.quantityChanged.emit(self.card_id, 1)
            )
            controls.addWidget(self.deck_button)

        layout.addLayout(controls)

        self.load_image()

    def set_selected(self, selected):
        selected = bool(selected)
        if selected == self._selected:
            return
        self._selected = selected
        self.setProperty("selected", str(selected).lower())
        self.style().unpolish(self)
        self.style().polish(self)

    def set_quantity(self, quantity):
        self.quantity = max(0, int(quantity or 0))
        self.qty_label.setText(str(self.quantity))

    def _change_quantity(self, amount):
        self.quantityChanged.emit(self.card_id, amount)

    def load_image(self):
        pixmap = _scaled_pixmap(_get_card_value(self.card, "image_path", 11), 40, 56)
        if not pixmap:
            return
        self.thumb_label.setText("")
        self.thumb_label.setPixmap(pixmap)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected.emit(self.card_id)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.detailsRequested.emit(self.card_id)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


# =========================================================
# PAINEL DE PREVIEW DA CARTA
# =========================================================

class CardPreviewPanel(QFrame):
    detailsRequested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CardPreviewPanel")
        self.setFixedWidth(300)
        self.current_card = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        self.image_label = QLabel()
        self.image_label.setObjectName("CardPreviewImage")
        self.image_label.setFixedSize(270, 380)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder = _scaled_pixmap(CARD_ICON_PATH, 270, 380)
        if placeholder:
            self.image_label.setPixmap(placeholder)
        layout.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.name_label = QLabel("Selecione uma carta")
        self.name_label.setObjectName("CardPreviewName")
        self.name_label.setWordWrap(True)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)

        self.mana_widget = ManaSymbolsWidget("", 16, self)
        self.mana_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.mana_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        separator = QFrame()
        separator.setObjectName("CardPreviewSeparator")
        separator.setFixedHeight(1)
        layout.addWidget(separator)

        self.type_label = QLabel("")
        self.type_label.setObjectName("CardPreviewType")
        self.type_label.setWordWrap(True)
        layout.addWidget(self.type_label)

        self.oracle_scroll = QScrollArea()
        self.oracle_scroll.setWidgetResizable(True)
        self.oracle_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.oracle_container = QWidget()
        self.oracle_layout = QVBoxLayout(self.oracle_container)
        self.oracle_layout.setContentsMargins(0, 0, 0, 0)
        self.oracle_label = QLabel("Clique em uma carta do deck para ver os detalhes.")
        self.oracle_label.setObjectName("CardPreviewOracle")
        self.oracle_label.setWordWrap(True)
        self.oracle_layout.addWidget(self.oracle_label)
        self.oracle_layout.addStretch()
        self.oracle_scroll.setWidget(self.oracle_container)
        layout.addWidget(self.oracle_scroll, 1)

        self.details_button = QPushButton("Ver detalhes completos")
        self.details_button.setObjectName("DeckToolbarButton")
        self.details_button.setEnabled(False)
        self.details_button.clicked.connect(self.detailsRequested.emit)
        layout.addWidget(self.details_button)

    def show_card(self, card):
        if not card:
            self.clear()
            return
        self.current_card = card
        self.name_label.setText(_display_name(card))

        mana_cost = _get_card_value(card, "mana_cost", 6, "") or ""
        self.mana_widget.setParent(None)
        self.mana_widget.deleteLater()
        self.mana_widget = ManaSymbolsWidget(str(mana_cost), 16, self)
        self.mana_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().insertWidget(3, self.mana_widget, 0, Qt.AlignmentFlag.AlignHCenter)

        self.type_label.setText(str(_get_card_value(card, "type_line", 7, "") or ""))
        oracle = str(_get_card_value(card, "oracle_text", 8, "") or "")
        self.oracle_label.setText(oracle or "Sem texto.")

        self.image_label.setText("")
        placeholder = _scaled_pixmap(CARD_ICON_PATH, 270, 380)
        if placeholder:
            self.image_label.setPixmap(placeholder)
        pixmap = _scaled_pixmap(_get_card_value(card, "image_path", 11), 270, 380)
        if pixmap:
            self.image_label.setPixmap(pixmap)

        self.details_button.setEnabled(True)

    def clear(self):
        self.current_card = None
        self.name_label.setText("Selecione uma carta")
        self.type_label.setText("")
        self.oracle_label.setText("Clique em uma carta do deck para ver os detalhes.")
        self.image_label.setText("")
        placeholder = _scaled_pixmap(CARD_ICON_PATH, 270, 380)
        if placeholder:
            self.image_label.setPixmap(placeholder)
        self.details_button.setEnabled(False)

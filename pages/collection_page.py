from pathlib import Path
import requests

from PySide6.QtCore import (
    Qt,
    QEvent,
    Signal,
    QObject,
    QTimer,
    QRunnable,
    QThreadPool,
    QSettings,
    QRect,
    Property,
)

import shiboken6

from PySide6.QtGui import (
    QPixmap,
    QAction,
    QIntValidator,
)

from components.card_details_dialog import (
    CardDetailsDialog,
)


# =========================================================
# CAMINHOS DOS ASSETS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"

ICONS_DIR = ASSETS_DIR / "icons"

CARD_ICON_PATH = ICONS_DIR / "card_icon.png"

COLLECTION_ICON_PATH = ICONS_DIR / "collection_icon.png"

SCRYFALL_LANGUAGES = {
    "Inglês": "en",
    "Português": "pt",
    "Espanhol": "es",
    "Francês": "fr",
    "Alemão": "de",
    "Italiano": "it",
    "Japonês": "ja",
    "Coreano": "ko",
    "Chinês Simplificado": "zhs",
    "Chinês Tradicional": "zht",
    "Russo": "ru",
}

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QListWidget,
    QFileDialog,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QMessageBox,
    QComboBox,
)

from services.scryfall import (
    autocomplete_card_names,
    get_card_by_name,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from services.collection_export import (
    ExportConfig,
    export_collection_custom,
    get_all_export_presets,
    config_from_preset,
    save_export_preset,
    delete_export_preset,
    EXPORT_FIELDS,
)

from export_dialog import CollectionExportDialog

from database import (
    add_card,
    ensure_card_exists,
    get_all_cards,
    get_all_catalog_cards,
    search_cards,
    change_quantity,
    set_card_quantity,
    get_collection_for_export,
    get_card_image_path,
    get_collection_stats,
)

from export import (
    export_collection_csv,
    export_collection_json,
    export_collection_treated_json,
    export_collection_txt,
)

from ui.theme import DARK_THEME


# =========================================================
# CONFIGURAÇÃO
# =========================================================

COLLECTION_RENDER_DELAY = 0  # Delay em ms antes de exibir cartas (0 = imediato)


# =========================================================
# CACHE GLOBAL DE IMAGENS
# =========================================================

_IMAGE_PIXMAP_CACHE = {}
_MAX_IMAGE_CACHE_SIZE = 500  # Limite de imagens em cache

def _cleanup_image_cache():
    """Remove entradas mais antigas do cache se exceder o limite."""
    global _IMAGE_PIXMAP_CACHE
    if len(_IMAGE_PIXMAP_CACHE) > _MAX_IMAGE_CACHE_SIZE:
        # Remove 20% das entradas mais antigas
        keys_to_remove = list(_IMAGE_PIXMAP_CACHE.keys())[:int(_MAX_IMAGE_CACHE_SIZE * 0.2)]
        for key in keys_to_remove:
            del _IMAGE_PIXMAP_CACHE[key]

# =========================================================
# CACHE LOCAL DE SÍMBOLOS
# =========================================================

_MANA_SYMBOL_WIDGET_DATA_CACHE = {}
_MAX_SYMBOL_CACHE_SIZE = 200

def _cleanup_symbol_cache():
    """Remove entradas mais antigas do cache de símbolos se exceder o limite."""
    global _MANA_SYMBOL_WIDGET_DATA_CACHE
    if len(_MANA_SYMBOL_WIDGET_DATA_CACHE) > _MAX_SYMBOL_CACHE_SIZE:
        keys_to_remove = list(_MANA_SYMBOL_WIDGET_DATA_CACHE.keys())[:int(_MAX_SYMBOL_CACHE_SIZE * 0.2)]
        for key in keys_to_remove:
            del _MANA_SYMBOL_WIDGET_DATA_CACHE[key]


# =========================================================
# TAREFA SCRYFALL — AUTOCOMPLETE
# =========================================================

class ScryfallSignals(QObject):
    finished = Signal(str, list)



class ScryfallTask(QRunnable):

    def __init__(
        self,
        query,
        language="en",
    ):
        super().__init__()

        self.query = str(
            query or ""
        ).strip()

        self.language = (
            language
            or "en"
        )

        self.signals = ScryfallSignals()

    def run(self):

        try:

            suggestions = (
                autocomplete_card_names(
                    self.query,
                    language=self.language,
                )
            )

            suggestions = suggestions[:8]

            self.signals.finished.emit(
                self.query,
                suggestions,
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro no autocomplete:",
                error,
            )

            self.signals.finished.emit(
                self.query,
                [],
            )



# =========================================================
# TAREFA SCRYFALL — CARTA COMPLETA
# =========================================================


class ScryfallCardSignals(QObject):

    finished = Signal(
        str,
        object,
    )

    failed = Signal(
        str,
        str,
    )


class ScryfallCardTask(QRunnable):

    def __init__(
        self,
        name,
        language="en",
    ):
        super().__init__()

        self.name = str(
            name or ""
        ).strip()

        self.language = (
            language
            or "en"
        )

        self.signals = (
            ScryfallCardSignals()
        )

    def run(self):

        try:

            if not self.name:
                self.signals.failed.emit(
                    "",
                    "Nome da carta vazio.",
                )

                return

            card_data = get_card_by_name(
                self.name,
                language=self.language,
            )

            self.signals.finished.emit(
                self.name,
                card_data,
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro ao buscar carta:",
                error,
            )

            self.signals.failed.emit(
                self.name,
                str(error),
            )


class RefreshCardDataSignals(QObject):
    progress = Signal(int, int, str)
    finished = Signal(int, int)
    failed = Signal(str)


class RefreshCardDataTask(QRunnable):
    def __init__(self, cards):
        super().__init__()
        self.cards = list(cards or [])
        self.signals = RefreshCardDataSignals()

    def run(self):
        total = len(self.cards)
        updated = 0

        try:
            for index, card in enumerate(self.cards, start=1):
                name = (
                    card.get("printed_name")
                    or card.get("name")
                    or ""
                )

                name = str(name).strip()

                if not name:
                    continue

                language = (
                    card.get("lang")
                    or "en"
                )

                if language not in SCRYFALL_LANGUAGES.values():
                    language = "en"

                self.signals.progress.emit(
                    index,
                    total,
                    name,
                )

                card_data = get_card_by_name(
                    name,
                    language=language,
                )

                if not card_data and language != "en":
                    card_data = get_card_by_name(
                        card.get("name") or name,
                        language="en",
                    )

                if not card_data:
                    continue

                if ensure_card_exists(card_data):
                    updated += 1

            self.signals.finished.emit(
                updated,
                total,
            )

        except Exception as error:
            self.signals.failed.emit(
                str(error)
            )

class ImageSignals(QObject):
    finished = Signal(str, str, bytes, object)
    failed = Signal(str, str, object)



class ImageTask(QRunnable):

    def __init__(
        self,
        url,
        local_path,
        label,
    ):
        super().__init__()

        self.url = url
        self.local_path = str(local_path)
        self.label = label

        self.signals = ImageSignals()

    def run(self):

        if not self.url:
            return

        try:

            path = Path(
                self.local_path
            )

            # -------------------------------------------------
            # CACHE DE DISCO
            # -------------------------------------------------

            if (
                path.exists()
                and path.stat().st_size > 0
            ):
                data = path.read_bytes()

                self.signals.finished.emit(
                    self.url,
                    str(path),
                    data,
                    self.label,
                )

                return

            headers = {
                "User-Agent": (
                    "MagicCollection/1.0 "
                    "(personal collection manager)"
                ),
                "Accept": "image/*,*/*;q=0.8",
            }

            response = requests.get(
                self.url,
                headers=headers,
                timeout=20,
            )

            response.raise_for_status()

            data = response.content

            if not data:
                raise RuntimeError(
                    "Scryfall retornou uma imagem vazia."
                )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temp_path = Path(
                str(path) + ".tmp"
            )

            temp_path.write_bytes(
                data
            )

            temp_path.replace(
                path
            )

            self.signals.finished.emit(
                self.url,
                str(path),
                data,
                self.label,
            )

        except Exception as error:

            print(
                "[IMAGE] Erro ao carregar:",
                self.url,
                "|",
                error,
            )

            self.signals.failed.emit(
                self.url,
                str(error),
                self.label,
            )




# =========================================================
# CARD FRAME
# =========================================================

class CardFrame(QFrame):

    doubleClicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    def mouseDoubleClickEvent(self, event):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.doubleClicked.emit()

            event.accept()

            return

        super().mouseDoubleClickEvent(
            event
        )
    
    def enterEvent(self, event):
        # Aplicar estilo de hover como nos Decks
        self.setProperty("hover", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        # Remover estilo de hover como nos Decks
        self.setProperty("hover", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)


# =========================================================
# IMAGEM CLICÁVEL
# =========================================================

class CardImageLabel(QLabel):

    doubleClicked = Signal()

    def mouseDoubleClickEvent(self, event):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):
            self.doubleClicked.emit()

            event.accept()

            return

        super().mouseDoubleClickEvent(
            event
        )


# =========================================================
# CARTA DA GRADE
# =========================================================

# =========================================================
# CARD DA GRADE
# =========================================================

# =========================================================
# CARD DA GRADE — COLLECTION
# =========================================================

class GridCardFrame(QFrame):

    doubleClicked = Signal()

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(parent)

        self.setObjectName(
            "GridCardFrame"
        )

        self._grid_generation = 0

        self.setMouseTracking(
            True
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True,
        )

        self.setMinimumSize(
            120,
            168,
        )

        self.setMaximumWidth(
            500,
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # =================================================
        # TAMANHO BASE
        # =================================================

        self._base_width = 120
        self._base_height = round(
            120 * 88 / 63
        )

        self._hover_scale = 1.08

        # =================================================
        # IMAGEM DA CARTA
        # =================================================

        self.image_label = CardImageLabel(
            self
        )

        self.image_label.setObjectName(
            "GridCardImage"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setText(
            ""
        )

        self.image_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        # Placeholder
        if CARD_ICON_PATH.exists():

            pixmap = QPixmap(
                str(CARD_ICON_PATH)
            )

            if not pixmap.isNull():

                scaled = pixmap.scaled(
                    self._base_width,
                    self._base_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self.image_label.setPixmap(
                    scaled
                )

        self.image_label.doubleClicked.connect(
            self.doubleClicked.emit
        )

        # =================================================
        # BADGE DE QUANTIDADE
        # =================================================

        self.quantity_badge = QLabel(
            "×0",
            self,
        )

        self.quantity_badge.setObjectName(
            "GridQuantityBadge"
        )

        self.quantity_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.quantity_badge.setFixedHeight(
            27
        )

        self.quantity_badge.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        # =================================================
        # CONTROLES
        # =================================================

        self.controls = QFrame(
            self
        )

        self.controls.setObjectName(
            "GridQuantityOverlay"
        )

        controls_layout = QHBoxLayout(
            self.controls
        )

        controls_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        controls_layout.setSpacing(
            14
        )

        controls_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # -------------------------------------------------
        # BOTÃO -
        # -------------------------------------------------

        self.minus_button = QPushButton(
            "−",
            self.controls,
        )

        self.minus_button.setObjectName(
            "GridQuantityButton"
        )

        self.minus_button.setFixedSize(
            32,
            32,
        )

        self.minus_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.minus_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        controls_layout.addWidget(
            self.minus_button,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        # -------------------------------------------------
        # QUANTIDADE
        # -------------------------------------------------

        self.control_quantity = QLineEdit(
            "0",
            self.controls,
        )

        self.control_quantity.setObjectName(
            "GridQuantityInput"
        )

        self.control_quantity.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.control_quantity.setValidator(
            QIntValidator(
                0,
                999999,
                self.control_quantity,
            )
        )

        self.control_quantity.setFixedSize(
            34,
            32,
        )

        controls_layout.addWidget(
            self.control_quantity,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        # -------------------------------------------------
        # BOTÃO +
        # -------------------------------------------------

        self.plus_button = QPushButton(
            "+",
            self.controls,
        )

        self.plus_button.setObjectName(
            "GridQuantityButton"
        )

        self.plus_button.setFixedSize(
            32,
            32,
        )

        self.plus_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.plus_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        controls_layout.addWidget(
            self.plus_button,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        self.controls.adjustSize()

        self.controls.hide()

        self._hovering = False
        self._editing_quantity = False

        self.controls.setMouseTracking(
            True
        )
        self.controls.installEventFilter(
            self
        )
        self.minus_button.installEventFilter(
            self
        )
        self.plus_button.installEventFilter(
            self
        )
        self.control_quantity.installEventFilter(
            self
        )
        self.control_quantity.editingFinished.connect(
            self._finish_quantity_edit
        )

    # =====================================================
    # TAMANHO NORMAL
    # =====================================================

    def set_card_width(
        self,
        width,
    ):

        width = max(
            120,
            int(width),
        )

        height = round(
            width * 88 / 63
        )

        self._base_width = width
        self._base_height = height

        self.setFixedSize(
            width,
            height,
        )

        self._normal_geometry = self.geometry()

        self.image_label.setGeometry(
            0,
            0,
            width,
            height,
        )

        self._update_overlays()

    # =====================================================
    # OVERLAYS
    # =====================================================

    def _update_overlays(
        self,
    ):

        width = self.width()
        height = self.height()

        self.image_label.setGeometry(
            0,
            0,
            width,
            height,
        )

        # -------------------------------------------------
        # CONTROLES
        # -------------------------------------------------

        overlay_height = 58

        self.controls.setGeometry(
            10,
            height - overlay_height - 10,
            max(80, width - 20),
            overlay_height,
        )

        # -------------------------------------------------
        # BADGE
        # -------------------------------------------------

        self.quantity_badge.adjustSize()

        badge_width = max(
            38,
            self.quantity_badge.width(),
        )

        badge_height = max(
            27,
            self.quantity_badge.height(),
        )

        margin_right = 7
        margin_top = 7

        self.quantity_badge.setGeometry(
            width
            - badge_width
            - margin_right,
            margin_top,
            badge_width,
            badge_height,
        )

        self.controls.raise_()
        self.quantity_badge.raise_()

    # =====================================================
    # RESIZE
    # =====================================================

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        self._update_overlays()

    # =====================================================
    # QUANTIDADE
    # =====================================================

    def set_quantity(
        self,
        quantity,
    ):

        quantity = max(
            0,
            int(quantity or 0),
        )

        self.quantity_badge.setText(
            f"×{quantity}"
        )

        self.control_quantity.setText(
            str(quantity)
        )

    def eventFilter(
        self,
        watched,
        event,
    ):
        if watched in (
            self.controls,
            self.minus_button,
            self.plus_button,
            self.control_quantity,
        ):
            if event.type() in (
                QEvent.Type.Enter,
                QEvent.Type.FocusIn,
                QEvent.Type.MouseButtonPress,
            ):
                self._editing_quantity = True
                self._animate_hover(True)

            elif event.type() == QEvent.Type.FocusOut:
                self._finish_quantity_edit()

        return super().eventFilter(
            watched,
            event,
        )

    def _finish_quantity_edit(self):
        self._editing_quantity = False
        if not self.underMouse():
            self._animate_hover(False)

    # =====================================================
    # DADOS DA CARTA
    # =====================================================

    def set_card_data(
        self,
        card_data,
        face_index=0,
        art_index=0,
    ):

        self.card_data = card_data
        self.current_face_index = face_index
        self.current_art_index = art_index

        self.update_card_image()

    def update_card_image(self):

        if not self.card_data:
            return

        # Obter URL da imagem
        face = self.card_data.get("card_faces", [self.card_data])[self.current_face_index] if self.card_data.get("card_faces") else self.card_data
        image_uris = face.get("image_uris") or {}

        # Se houver arte selecionada
        url = None
        if self.current_art_index > 0 and "artworks" in face:
            artworks = face.get("artworks") or []
            if self.current_art_index <= len(artworks):
                art = artworks[self.current_art_index - 1]
                url = art.get("large") or art.get("image_uri") or art.get("normal")

        if not url:
            for key in ("large", "normal", "png", "border_crop", "small"):
                url = image_uris.get(key)
                if url:
                    break

        if not url:
            # Fallback para imagem padrão
            scryfall_id = self.card_data.get("scryfall_id") or self.card_data.get("id")
            if scryfall_id:
                from database import build_scryfall_image_url
                url = build_scryfall_image_url(scryfall_id)

        if not url:
            return

        # Caminho local
        scryfall_id = self.card_data.get("scryfall_id") or self.card_data.get("id")
        if scryfall_id:
            from database import get_card_image_path
            local_path = get_card_image_path(
                scryfall_id
            )

            if local_path and Path(local_path).exists():
                pixmap = QPixmap(
                    str(local_path)
                )

                if not pixmap.isNull():
                    width = max(
                        120,
                        self.card_width,
                    )

                    height = round(
                        width * 88 / 63
                    )

                    self.image_label.setPixmap(
                        pixmap.scaled(
                            width,
                            height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                    )

                    self.image_label.setText(
                        ""
                    )


    # =====================================================
    # COMEÇAR ZOOM
    # =====================================================

    def _animate_hover(
        self,
        hovering,
    ):

        self._hovering = hovering

        # -------------------------------------------------
        # Controles e Badge
        # -------------------------------------------------

        if hovering:

            self.controls.show()

            # Ficar acima das cartas vizinhas
            self.raise_()

            self.quantity_badge.raise_()
            self.controls.raise_()

        else:
            if self._editing_quantity:
                self.controls.show()
                return

            self.controls.hide()

        # Removida animação de zoom que causava reposicionamento
        # O hover agora é puramente visual via CSS

    # =====================================================
    # ENTER
    # =====================================================

    def enterEvent(
        self,
        event,
    ):

        self._animate_hover(
            True
        )

        super().enterEvent(
            event
        )

    # =====================================================
    # LEAVE
    # =====================================================

    def leaveEvent(
        self,
        event,
    ):

        if not self._editing_quantity:
            self._animate_hover(
                False
            )

        super().leaveEvent(
            event
        )

    # =====================================================
    # DOUBLE CLICK
    # =====================================================

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.doubleClicked.emit()

            event.accept()

            return

        super().mouseDoubleClickEvent(
            event
        )
# =========================================================
# CONTAINER DA GRADE
# =========================================================

class CardsContainer(QWidget):

    resized = Signal()

    def resizeEvent(self, event):

        old_size = event.oldSize()
        new_size = event.size()

        super().resizeEvent(
            event
        )

        if (
            old_size.width()
            != new_size.width()
        ):
            self.resized.emit()


# =========================================================
# COLLECTION PAGE
# =========================================================
class SuggestionLineEdit(QLineEdit):

    keyPressed = Signal(object)

    def keyPressEvent(
        self,
        event,
    ):

        self.keyPressed.emit(
            event
        )

class CollectionPage(QWidget):

    def __init__(self, parent=None):

        super().__init__(
            parent
        )

        self.setStyleSheet(
            DARK_THEME
        )

        # =================================================
        # DADOS
        # =================================================

        self.pending_search = ""

        self.settings = QSettings(
            "MagicCollection",
            "MagicCollection"
        )

        self.current_layout = self.settings.value(
            "collection/layout",
            "grid",
            type=str
        )

        if self.current_layout not in (
                "list",
                "grid",
        ):
            self.current_layout = "grid"

        self.current_cards = []

        self.all_collection_cards = []
        self.search_result_cards = []

        self.active_color_filter = "all"
        self.active_type_filter = "all"
        self.active_set_filter = "all"
        self.active_sort = "name_asc"

        self.card_rows = {}

        self.rebuilding_grid = False

        self._grid_columns = None

        self._grid_generation = 0
        # =================================================
        # THREAD POOLS
        # =================================================

        self.scryfall_pool = QThreadPool(
            self
        )

        self.scryfall_pool.setMaxThreadCount(
            4
        )

        self.card_search_pool = QThreadPool(
            self
        )

        self.card_search_pool.setMaxThreadCount(
            4
        )

        self.image_pool = QThreadPool(
            self
        )

        self.image_pool.setMaxThreadCount(
            8
        )

        # =================================================
        # CACHE
        # =================================================

        self.image_cache = _IMAGE_PIXMAP_CACHE

        self.mana_widget_cache = (
            _MANA_SYMBOL_WIDGET_DATA_CACHE
        )

        # =================================================
        # TIMERS
        # =================================================

        self.search_timer = QTimer(
            self
        )

        self.search_timer.setSingleShot(
            True
        )

        self.search_timer.setInterval(
            300
        )

        self.search_timer.timeout.connect(
            self.perform_scryfall_search
        )

        self._grid_resize_timer = QTimer(
            self
        )

        self._grid_resize_timer.setSingleShot(
            True
        )

        self._grid_resize_timer.setInterval(
            100
        )

        self._grid_resize_timer.timeout.connect(
            self.rebuild_grid_after_resize
        )

        # =================================================
        # UI
        # =================================================

        self.setup_ui()

        QTimer.singleShot(
            0,
            self.load_cards
        )





    # =====================================================
    # SETUP
    # =====================================================
    def update_card_quantity_in_list(
            self,
            cards,
            card_id,
            new_quantity,
    ):

        updated = []

        for card in cards:

            try:

                current_id = int(
                    card[0]
                )

            except (
                    TypeError,
                    ValueError,
            ):

                updated.append(
                    card
                )

                continue

            if current_id != card_id:
                updated.append(
                    card
                )

                continue

            card = list(
                card
            )

            if len(card) > 10:
                card[10] = new_quantity

            updated.append(
                tuple(card)
            )

        return updated
    def setup_ui(self):

        self.main_layout = QVBoxLayout(
            self
        )

        self.main_layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )

        self.main_layout.setSpacing(
            18
        )

        # =================================================
        # TÍTULO
        # =================================================

        title = QLabel(
            "Minha coleção"
        )

        title.setObjectName(
            "SectionTitle"
        )

        self.main_layout.addWidget(
            title
        )

        description = QLabel(
            "Gerencie as cartas que você possui."
        )

        description.setObjectName(
            "SectionDescription"
        )

        self.main_layout.addWidget(
            description
        )

        # =================================================
        # AÇÕES
        # =================================================

        actions_layout = QHBoxLayout()

        actions_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        actions_layout.setSpacing(
            8
        )

        self.export_button = QPushButton(
            "Exportar"
        )

        self.export_button.setObjectName(
            "ExportButton"
        )

        self.export_button.clicked.connect(
            self.export_collection
        )

        actions_layout.addWidget(
            self.export_button
        )

        self.refresh_data_button = QPushButton(
            "Atualizar dados"
        )

        self.refresh_data_button.setObjectName(
            "RefreshDataButton"
        )

        self.refresh_data_button.clicked.connect(
            self.refresh_missing_card_data
        )

        actions_layout.addWidget(
            self.refresh_data_button
        )

        # =================================================
        # CONTADOR DA COLEÇÃO
        # =================================================

        self.collection_count_label = QLabel(
            "0 cartas · 0 diferentes"
        )

        self.collection_count_label.setObjectName(
            "CollectionCountLabel"
        )

        self.collection_count_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        actions_layout.addWidget(
            self.collection_count_label
        )

        actions_layout.addStretch()

        self.layout_button = QPushButton(
            "Layouts"
        )

        self.layout_button.setObjectName(
            "LayoutButton"
        )

        self.layout_button.clicked.connect(
            self.show_layout_menu
        )

        actions_layout.addWidget(
            self.layout_button
        )

        self.main_layout.addLayout(
            actions_layout
        )

        # =================================================
        # PESQUISA
        # =================================================

        search_frame = QFrame()

        search_frame.setObjectName(
            "SearchFrame"
        )

        search_layout = QHBoxLayout(
            search_frame
        )

        search_layout.setContentsMargins(
            12,
            0,
            12,
            0,
        )

        search_icon = QLabel(
            "🔎"
        )

        search_icon.setObjectName(
            "SearchIcon"
        )

        search_layout.addWidget(
            search_icon
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Pesquisar cartas da sua coleção..."
        )

        self.search_input.setFrame(
            False
        )

        self.search_input.textChanged.connect(
            self.search_collection
        )

        search_layout.addWidget(
            self.search_input
        )

        self.main_layout.addWidget(
            search_frame
        )

        # =================================================
        # FILTROS DA COLEÇÃO
        # =================================================

        self.filters_frame = QFrame()

        self.filters_frame.setObjectName(
            "CollectionFilters"
        )

        filters_layout = QHBoxLayout(
            self.filters_frame
        )

        filters_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        filters_layout.setSpacing(8)

        # -------------------------------------------------
        # COR
        # -------------------------------------------------

        self.color_filter = QComboBox()

        self.color_filter.addItem(
            "Todas as cores",
            "all",
        )

        self.color_filter.addItem(
            "Branco",
            "W",
        )

        self.color_filter.addItem(
            "Azul",
            "U",
        )

        self.color_filter.addItem(
            "Preto",
            "B",
        )

        self.color_filter.addItem(
            "Vermelho",
            "R",
        )

        self.color_filter.addItem(
            "Verde",
            "G",
        )

        self.color_filter.addItem(
            "Incolor",
            "C",
        )

        self.color_filter.addItem(
            "Multicolor",
            "M",
        )

        self.color_filter.currentIndexChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.color_filter
        )

        # -------------------------------------------------
        # TIPO
        # -------------------------------------------------

        self.type_filter = QComboBox()

        self.type_filter.addItem(
            "Todos os tipos",
            "all",
        )

        self.type_filter.addItem(
            "Criatura",
            "Criatura",
        )

        self.type_filter.addItem(
            "Mágica Instantânea",
            "Mágica Instantânea",
        )

        self.type_filter.addItem(
            "Feitiço",
            "Feitiço",
        )

        self.type_filter.addItem(
            "Encantamento",
            "Encantamento",
        )

        self.type_filter.addItem(
            "Artefato",
            "Artefato",
        )

        self.type_filter.addItem(
            "Planeswalker",
            "Planeswalker",
        )

        self.type_filter.addItem(
            "Terreno",
            "Terreno",
        )

        self.type_filter.currentIndexChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.type_filter
        )

        # -------------------------------------------------
        # EDIÇÃO
        # -------------------------------------------------

        self.set_filter = QComboBox()

        self.set_filter.addItem(
            "Todas as edições",
            "all",
        )

        self.set_filter.currentIndexChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.set_filter
        )

        # -------------------------------------------------
        # ORDENAÇÃO
        # -------------------------------------------------

        self.sort_filter = QComboBox()

        self.sort_filter.addItem(
            "Nome: A → Z",
            "name_asc",
        )

        self.sort_filter.addItem(
            "Nome: Z → A",
            "name_desc",
        )

        self.sort_filter.addItem(
            "Quantidade: menor → maior",
            "quantity_asc",
        )

        self.sort_filter.addItem(
            "Quantidade: maior → menor",
            "quantity_desc",
        )

        self.sort_filter.addItem(
            "Edição: A → Z",
            "set_asc",
        )

        self.sort_filter.addItem(
            "Edição: Z → A",
            "set_desc",
        )

        self.sort_filter.addItem(
            "Mais recentes",
            "newest",
        )

        self.sort_filter.addItem(
            "Mais antigas",
            "oldest",
        )

        self.sort_filter.currentIndexChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.sort_filter
        )

        # -------------------------------------------------
        # LIMPAR
        # -------------------------------------------------

        clear_filters_button = QPushButton(
            "Limpar filtros"
        )

        clear_filters_button.clicked.connect(
            self.clear_collection_filters
        )

        filters_layout.addWidget(
            clear_filters_button
        )

        self.main_layout.addWidget(
            self.filters_frame
        )

        # =================================================
        # ADICIONAR
        # =================================================

        self.add_area = QWidget()

        self.add_area.setObjectName(
            "AddArea"
        )

        self.add_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        self.add_area.setFixedHeight(
            48
        )

        add_area_layout = QVBoxLayout(
            self.add_area
        )

        add_area_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        add_area_layout.setSpacing(
            0
        )

        add_frame = QFrame()

        add_frame.setObjectName(
            "AddFrame"
        )

        add_frame.setFixedHeight(
            48
        )

        add_layout = QHBoxLayout(
            add_frame
        )

        add_layout.setContentsMargins(
            12,
            0,
            12,
            0,
        )

        add_layout.setSpacing(
            10
        )

        add_icon = QLabel(
            "＋"
        )

        add_icon.setObjectName(
            "AddIcon"
        )

        add_layout.addWidget(
            add_icon
        )

        self.add_input = SuggestionLineEdit()

        self.add_input.setPlaceholderText(
            "Adicionar carta à coleção..."
        )

        # =========================================================
        # SELETOR DE IDIOMAS
        # =========================================================

        self.selected_languages = [
            "en",
        ]

        self.selected_language = "en"

        self.language_button = QPushButton(
            "🇺🇸 Inglês"
        )

        self.language_button.setObjectName(
            "LanguageButton"
        )

        self.language_menu = QMenu(
            self.language_button
        )

        self.language_actions = {}

        language_options = [
            ("🇺🇸 Inglês", "en"),
            ("🇧🇷 Português", "pt"),
            ("🇪🇸 Espanhol", "es"),
            ("🇫🇷 Francês", "fr"),
            ("🇩🇪 Alemão", "de"),
            ("🇮🇹 Italiano", "it"),
            ("🇯🇵 Japonês", "ja"),
            ("🇰🇷 Coreano", "ko"),
            ("🇨🇳 Chinês Simplificado", "zhs"),
            ("🇹🇼 Chinês Tradicional", "zht"),
            ("🇷🇺 Russo", "ru"),
        ]

        for label, code in language_options:
            action = QAction(
                label,
                self.language_menu,
            )

            action.setCheckable(
                True
            )

            action.setChecked(
                code == "en"
            )

            action.triggered.connect(
                lambda checked,
                       language=code:
                self.on_language_toggled(
                    language,
                    checked,
                )
            )

            self.language_menu.addAction(
                action
            )

            self.language_actions[
                code
            ] = action

        self.language_button.setMenu(
            self.language_menu
        )

        add_layout.addWidget(
            self.language_button
        )

        self.add_input.setFrame(
            False
        )

        self.add_input.textChanged.connect(
            self.search_scryfall
        )



        self.add_input.keyPressed.connect(
            self.handle_add_input_keypress
        )

        add_layout.addWidget(
            self.add_input
        )

        self.search_status = QLabel()

        self.search_status.setObjectName(
            "SearchStatus"
        )

        self.search_status.setFixedWidth(
            28
        )

        self.search_status.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        add_layout.addWidget(
            self.search_status
        )

        self.add_button = QPushButton(
            "Adicionar"
        )

        self.add_button.setObjectName(
            "AddButton"
        )

        self.add_button.clicked.connect(
            self.add_card_from_input
        )

        add_layout.addWidget(
            self.add_button
        )

        add_area_layout.addWidget(
            add_frame
        )

        self.main_layout.addWidget(
            self.add_area
        )

        # =================================================
        # SUGESTÕES
        # =================================================

        self.suggestion_list = QListWidget()

        self.suggestion_list.setObjectName(
            "SuggestionList"
        )

        self.suggestion_list.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self.suggestion_list.setMouseTracking(
            True
        )

        self.suggestion_list.setMinimumHeight(
            0
        )

        self.suggestion_list.setMaximumHeight(
            320
        )

        self.suggestion_list.itemClicked.connect(
            self.select_suggestion
        )

        self.suggestion_list.hide()

        self.main_layout.addWidget(
            self.suggestion_list
        )

        # =================================================
        # LISTA / GRADE
        # =================================================

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setObjectName(
            "CardsScrollArea"
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        
        # Importante: desabilitar scroll durante o carregamento inicial
        self.scroll_area.setUpdatesEnabled(False)

        self.cards_container = CardsContainer()

        self.cards_container.setObjectName(
            "CardsContainer"
        )

        self.cards_layout = QVBoxLayout(
            self.cards_container
        )

        self.cards_layout.setContentsMargins(
            0,
            5,
            0,
            5,
        )

        self.cards_layout.setSpacing(
            9
        )

        self.cards_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.cards_container.resized.connect(
            self.handle_container_resize
        )

        self.scroll_area.setWidget(
            self.cards_container
        )

        self.main_layout.addWidget(
            self.scroll_area
        )

        self.scroll_area.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    # =====================================================
    # MENU DE LAYOUT
    # =====================================================

    def show_layout_menu(self):

        menu = QMenu(
            self
        )

        menu.setObjectName(
            "LayoutMenu"
        )

        list_action = menu.addAction(
            "☰  Lista"
        )

        grid_action = menu.addAction(
            "▦  Grade"
        )

        list_action.setCheckable(
            True
        )

        grid_action.setCheckable(
            True
        )

        list_action.setChecked(
            self.current_layout == "list"
        )

        grid_action.setChecked(
            self.current_layout == "grid"
        )

        list_action.triggered.connect(
            lambda:
            self.set_layout(
                "list"
            )
        )

        grid_action.triggered.connect(
            lambda:
            self.set_layout(
                "grid"
            )
        )

        menu.exec(
            self.layout_button.mapToGlobal(
                self.layout_button.rect().bottomLeft()
            )
        )



        # =====================================================
        # SETUP
        # =====================================================

        def setup_ui(
                self,
        ):
            self.main_layout = QVBoxLayout(
                self
            )

    # =====================================================
    # ALTERAR LAYOUT
    # =====================================================
    def handle_add_input_keypress(
            self,
            event,
    ):

        key = event.key()

        # =================================================
        # SETA PARA BAIXO
        # =================================================

        if key == Qt.Key.Key_Down:

            if (
                    not self.suggestion_list.isVisible()
                    or self.suggestion_list.count() == 0
            ):
                return

            current_row = (
                self.suggestion_list.currentRow()
            )

            next_row = current_row + 1

            if next_row >= self.suggestion_list.count():
                next_row = 0

            self.suggestion_list.setCurrentRow(
                next_row
            )

            return

        # =================================================
        # SETA PARA CIMA
        # =================================================

        if key == Qt.Key.Key_Up:

            if (
                    not self.suggestion_list.isVisible()
                    or self.suggestion_list.count() == 0
            ):
                return

            current_row = (
                self.suggestion_list.currentRow()
            )

            previous_row = current_row - 1

            if previous_row < 0:
                previous_row = (
                        self.suggestion_list.count() - 1
                )

            self.suggestion_list.setCurrentRow(
                previous_row
            )

            return

        # =================================================
        # ENTER
        # =================================================

        if key in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
        ):

            if (
                    self.suggestion_list.isVisible()
                    and self.suggestion_list.count() > 0
            ):

                current_row = (
                    self.suggestion_list.currentRow()
                )

                if current_row < 0:
                    current_row = 0

                item = (
                    self.suggestion_list.item(
                        current_row
                    )
                )

                if item:
                    self.select_suggestion(
                        item
                    )

                    return

            self.add_card_from_input()

            return

        # =================================================
        # ESC
        # =================================================

        if key == Qt.Key.Key_Escape:

            if self.suggestion_list.isVisible():
                self.suggestion_list.hide()
                self.suggestion_list.clear()

                return

        # =================================================
        # OUTRAS TECLAS
        # =================================================

        QLineEdit.keyPressEvent(
            self.add_input,
            event,
        )

    def set_layout(self, layout_name):

        if layout_name not in (
                "list",
                "grid",
        ):
            return

        if self.current_layout == layout_name:
            return

        self.current_layout = layout_name

        self.settings.setValue(
            "collection/layout",
            layout_name
        )

        self._grid_columns = None

        self._grid_resize_timer.stop()

        self.display_cards(
            self.current_cards
        )

    # =====================================================
    # RESIZE
    # =====================================================

    def handle_container_resize(self):

        if self.current_layout != "grid":
            return

        if self.rebuilding_grid:
            return

        if not self.current_cards:
            return

        viewport_width = (
            self.scroll_area
            .viewport()
            .width()
        )

        if viewport_width <= 0:
            return

        min_card_width = 160
        spacing = 14

        columns = max(
            1,
            int(
                (
                    viewport_width
                    + spacing
                )
                /
                (
                    min_card_width
                    + spacing
                )
            ),
        )

        if self._grid_columns == columns:
            return

        self._grid_columns = columns

        self._grid_resize_timer.start()

    def rebuild_grid_after_resize(self):

        if self.current_layout != "grid":
            return

        if self.rebuilding_grid:
            return

        if not self.current_cards:
            return

        self.display_cards(
            self.current_cards
        )

    # =========================================================
    # ALTERAR IDIOMAS
    # =========================================================
    def on_language_toggled(
            self,
            language,
            checked,
    ):
        if checked:
            self.selected_languages.add(
                language
            )
        else:
            self.selected_languages.discard(
                language
            )

        self.update_language_button()

        self.apply_collection_filters()
    def on_language_toggled(
            self,
            language,
            checked,
    ):
        if checked:

            if language not in self.selected_languages:
                self.selected_languages.append(
                    language
                )

        else:

            if language in self.selected_languages:
                self.selected_languages.remove(
                    language
                )

        def update_language_button(
                self,
        ):
            languages = getattr(
                self,
                "selected_languages",
                set(),
            )

            if not languages:
                self.language_button.setText(
                    "🌐"
                )

                return

            flags = {
                "br": "🇧🇷",
                "us": "🇺🇸",
                "es": "🇪🇸",
                "fr": "🇫🇷",
                "de": "🇩🇪",
                "it": "🇮🇹",
                "ja": "🇯🇵",
                "ko": "🇰🇷",
                "zhs": "🇨🇳",
                "zht": "🇹🇼",
                "ru": "🇷🇺",
            }

            selected_flags = []

            for language in languages:
                flag = flags.get(
                    language,
                    language.upper(),
                )

                selected_flags.append(
                    flag
                )

            self.language_button.setText(
                " ".join(
                    selected_flags
                )
            )

        def update_language_button(
                self,
        ):

            if not self.selected_languages:
                self.language_filter_button.setText(
                    "🌐 Idioma"
                )

                return

            language_flags = {
                "br": "🇧🇷",
                "us": "🇺🇸",
                "es": "🇪🇸",
                "fr": "🇫🇷",
                "de": "🇩🇪",
                "it": "🇮🇹",
                "ja": "🇯🇵",
                "ko": "🇰🇷",
                "zhs": "🇨🇳",
                "zht": "🇹🇼",
                "ru": "🇷🇺",
            }

            flags = []

            for language in sorted(
                    self.selected_languages
            ):
                flag = language_flags.get(
                    language,
                    language,
                )

                flags.append(
                    flag
                )

            self.language_button.setText(
                " ".join(flags)
            )

        # -------------------------------------------------
        # GARANTIR PELO MENOS UM IDIOMA
        # -------------------------------------------------

        if not self.selected_languages:

            self.selected_languages = [
                "en",
            ]

            action = self.language_actions.get(
                "en"
            )

            if action is not None:
                action.blockSignals(
                    True
                )

                action.setChecked(
                    True
                )

                action.blockSignals(
                    False
                )


        self.update_language_button()

        # -------------------------------------------------
        # REFAZER AUTOCOMPLETE
        # -------------------------------------------------

        self.search_timer.stop()

        self.pending_search = ""

        self.suggestion_list.clear()

        self.suggestion_list.hide()

        self.search_status.clear()

        current_text = (
            self.add_input
            .text()
            .strip()
        )

        if len(current_text) < 2:
            return

        self.pending_search = current_text

        self.search_status.setText(
            "🔄"
        )

        self.search_timer.start()

        print(
            "[SCRYFALL] Idioma selecionado:",
            self.selected_language,
        )

        # =========================================================
        # ATUALIZAR TEXTO DO BOTÃO DE IDIOMAS
        # =========================================================

        def update_language_button(
                self,
        ):
            language_labels = {
                "en": "🇺🇸 Inglês",
                "pt": " Português",
                "es": "🇪🇸 Espanhol",
                "fr": "🇫🇷 Francês",
                "de": "🇩🇪 Alemão",
                "it": "🇮🇹 Italiano",
                "ja": "🇯🇵 Japonês",
                "ko": "🇰🇷 Coreano",
                "zhs": "🇨🇳 Chinês Simplificado",
                "zht": "🇹🇼 Chinês Tradicional",
                "ru": "🇷🇺 Russo",
            }

            selected = [
                language_labels.get(
                    language,
                    language,
                )
                for language
                in self.selected_languages
            ]

            if not selected:
                self.language_button.setText(
                    "Idioma"
                )

                return

            if len(selected) == 1:
                self.language_button.setText(
                    selected[0]
                )

                return

            self.language_button.setText(
                f"{len(selected)} idiomas selecionados"
            )

        # =====================================================
        # CANCELA PESQUISA ANTERIOR
        # =====================================================

        self.search_timer.stop()

        self.pending_search = ""

        # =====================================================
        # LIMPA SUGESTÕES ANTIGAS
        # =====================================================

        self.suggestion_list.clear()

        self.suggestion_list.hide()

        self.search_status.clear()

        # =====================================================
        # REFAZ A PESQUISA NO NOVO IDIOMA
        # =====================================================

        current_text = (
            self.add_input
            .text()
            .strip()
        )

        if len(current_text) < 2:
            return

        self.pending_search = current_text

        self.search_status.setText(
            "🔄"
        )

        self.search_timer.start()
    # =====================================================
    # AUTOCOMPLETE
    # =====================================================

    def update_language_button(
            self,
    ):
        language_labels = {
            "en": "Ingles",
            "pt": "Portugues",
            "es": "Espanhol",
            "fr": "Frances",
            "de": "Alemao",
            "it": "Italiano",
            "ja": "Japones",
            "ko": "Coreano",
            "zhs": "Chines Simplificado",
            "zht": "Chines Tradicional",
            "ru": "Russo",
        }

        if not self.selected_languages:
            self.selected_languages = [
                "en",
            ]

        self.selected_language = (
            self.selected_languages[0]
        )

        selected = [
            language_labels.get(
                language,
                language,
            )
            for language in self.selected_languages
        ]

        if len(selected) == 1:
            self.language_button.setText(
                selected[0]
            )
            return

        self.language_button.setText(
            f"{len(selected)} idiomas"
        )

    def search_scryfall(self, text):

        text = text.strip()

        self.search_timer.stop()

        if len(text) < 2:

            self.pending_search = ""

            self.suggestion_list.clear()

            self.suggestion_list.hide()

            self.search_status.clear()

            return

        self.pending_search = text

        self.search_status.setText(
            "🔄"
        )

        self.search_timer.start()

    def perform_scryfall_search(
            self,
    ):
        query = self.pending_search

        if not query:
            return

        languages = list(
            self.selected_languages
        )

        if not languages:
            languages = [
                "en",
            ]

        print(
            "[SCRYFALL] Pesquisando autocomplete:",
            query,
            "| Idiomas:",
            languages,
        )

        # =====================================================
        # LIMPAR RESULTADOS ANTERIORES
        # =====================================================

        self.suggestion_list.clear()

        self.search_status.setText(
            "🔄"
        )

        # =====================================================
        # PESQUISAR EM CADA IDIOMA
        # =====================================================

        self._language_search_pending = len(
            languages
        )

        self._language_search_results = []

        for language in languages:
            task = ScryfallTask(
                query,
                language,
            )

            task.signals.finished.connect(
                self.receive_multi_language_results
            )

            self.scryfall_pool.start(
                task
            )

    # =========================================================
    # RECEBER RESULTADOS DE MÚLTIPLOS IDIOMAS
    # =========================================================

    def receive_multi_language_results(
            self,
            query,
            suggestions,
    ):
        current_text = (
            self.add_input
            .text()
            .strip()
        )

        if query != current_text:
            return

        if not hasattr(
                self,
                "_language_search_results",
        ):
            self._language_search_results = []

        self._language_search_results.extend(
            suggestions or []
        )

        self._language_search_pending = max(
            0,
            getattr(
                self,
                "_language_search_pending",
                1,
            ) - 1,
        )

        if (
                self._language_search_pending
                > 0
        ):
            return

        # =====================================================
        # REMOVER DUPLICADOS
        # =====================================================

        unique_suggestions = []

        seen = set()

        for name in self._language_search_results:

            name = str(
                name or ""
            ).strip()

            if not name:
                continue

            key = name.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            unique_suggestions.append(
                name
            )

            if len(
                    unique_suggestions
            ) >= 8:
                break

        self._language_search_results = []

        self.search_status.clear()

        self.suggestion_list.clear()

        if not unique_suggestions:
            self.suggestion_list.hide()

            return

        for name in unique_suggestions:
            self.suggestion_list.addItem(
                name
            )

        if self.suggestion_list.count() > 0:
            self.suggestion_list.setCurrentRow(
                0
            )

        self.update_suggestion_height()

        self.suggestion_list.show()


    # =====================================================
    # ALTURA DAS SUGESTÕES
    # =====================================================

    def update_suggestion_height(
        self,
    ):

        count = (
            self.suggestion_list.count()
        )

        if count <= 0:

            self.suggestion_list.hide()

            return

        row_height = (
            self.suggestion_list.sizeHintForRow(
                0
            )
        )

        if row_height <= 0:

            row_height = 38

        visible_rows = min(
            count,
            8,
        )

        height = (
            row_height
            * visible_rows
        ) + 8

        height = min(
            height,
            320,
        )

        self.suggestion_list.setFixedHeight(
            height
        )

    # =====================================================
    # SUGESTÃO
    # =====================================================

    def select_suggestion(
        self,
        item,
    ):

        name = item.text()

        self.suggestion_list.hide()

        self.add_input.setText(
            name
        )

        self.add_input.setFocus()

        self.add_card_from_input()

    def handle_add_enter(self):

        if self.suggestion_list.isVisible():

            current_item = (
                self.suggestion_list.currentItem()
            )

            if current_item:

                self.select_suggestion(
                    current_item
                )

                return

            if self.suggestion_list.count():

                self.select_suggestion(
                    self.suggestion_list.item(0)
                )

                return

        self.add_card_from_input()

    # =====================================================
    # ADICIONAR CARTA
    # =====================================================

    def add_card_from_input(self):

        name = (
            self.add_input
            .text()
            .strip()
        )

        if not name:
            return

        if len(name) > 200:
            self.search_status.setText(
                "!"
            )

            return

        self.search_status.setText(
            "🔄"
        )

        self.add_button.setEnabled(
            False
        )

        try:

            card_data = None

            languages = list(
                self.selected_languages
            )

            if not languages:
                languages = [
                    "en",
                ]

            # =================================================
            # TENTAR CADA IDIOMA SELECIONADO
            # =================================================

            for language in languages:

                card_data = get_card_by_name(
                    name,
                    language=language,
                )

                if card_data:
                    break


        except requests.RequestException as error:
            print(
                "[SCRYFALL] Erro de rede:",
                error,
            )

            self.search_status.setText(
                "!"
            )

            self.add_button.setEnabled(
                True
            )

            return

        except (ValueError, KeyError) as error:
            print(
                "[SCRYFALL] Erro ao processar dados:",
                error,
            )

            self.search_status.setText(
                "!"
            )

            self.add_button.setEnabled(
                True
            )

            return

        except Exception as error:
            print(
                "[SCRYFALL] Erro inesperado:",
                error,
            )

            self.search_status.setText(
                "!"
            )

            self.add_button.setEnabled(
                True
            )

            return

        if not card_data:

            self.search_status.setText(
                "!"
            )

            self.add_button.setEnabled(
                True
            )

            return

        try:

            success = add_card(
                card_data,
                1,
            )

        except Exception as error:

            print(
                "[DATABASE] Erro:",
                error,
            )

            success = False

        if not success:
            self.search_status.setText(
                "!"
            )

            self.add_button.setEnabled(
                True
            )

            return

        # =================================================
        # LIMPAR PESQUISA
        # =================================================

        self.add_input.clear()

        self.suggestion_list.clear()
        self.suggestion_list.hide()

        self.search_status.clear()

        self.add_button.setEnabled(
            True
        )

        self.add_input.setFocus()

        # =================================================
        # RECARREGAR COLEÇÃO
        # =================================================

        self.load_cards()

        # Garante que o QScrollArea volte a atualizar.
        self.scroll_area.setUpdatesEnabled(
            True
        )

        # Força uma atualização visual imediata.
        self.scroll_area.viewport().update()
        self.cards_container.update()

    # =====================================================
    # CARREGAR CARTAS
    # =====================================================

    def load_cards(
            self,
    ):

        try:

            cards = get_all_cards()

        except Exception as error:

            print(
                "[DATABASE] Erro ao carregar coleção:",
                error,
            )

            cards = []

        # =================================================
        # FONTE PRINCIPAL DA COLEÇÃO
        # =================================================

        self.all_collection_cards = list(
            cards
        )

        # =================================================
        # RESULTADO ATUAL DA PESQUISA
        # =================================================

        self.search_result_cards = list(
            cards
        )

        # =================================================
        # ATUALIZAR EDIÇÕES
        # =================================================

        self.populate_set_filter()

        # =================================================
        # APLICAR FILTROS
        # =================================================

        # =====================================================
        # ATUALIZAR CONTADOR DA COLEÇÃO
        # =====================================================

        def update_collection_count(
                self,
                cards,
        ):
            if cards is None:
                cards = []

            total_quantity = 0

            for card in cards:
                try:
                    quantity = int(
                        card[10]
                        if len(card) > 10
                        else 0
                    )

                except (
                        TypeError,
                        ValueError,
                        IndexError,
                ):
                    quantity = 0

                total_quantity += max(
                    quantity,
                    0,
                )

            different_cards = len(
                cards
            )

            self.collection_count_label.setText(
                f"{total_quantity} cartas · "
                f"{different_cards} diferentes"
            )

        self.apply_collection_filters()

    def refresh_missing_card_data(
            self,
    ):
        try:
            catalog_cards = get_all_catalog_cards()
        except Exception as error:
            QMessageBox.warning(
                self,
                "Atualizar dados",
                f"Nao foi possivel ler o catalogo:\n{error}",
            )
            return

        missing_cards = [
            card
            for card in catalog_cards
            if not card.get("card_faces")
        ]

        if not missing_cards:
            QMessageBox.information(
                self,
                "Atualizar dados",
                "Todas as cartas existentes ja possuem dados completos.",
            )
            return

        reply = QMessageBox.question(
            self,
            "Atualizar dados",
            (
                f"Encontradas {len(missing_cards)} cartas sem dados "
                "de faces salvos.\n\n"
                "Deseja consultar o Scryfall e atualizar essas cartas?"
            ),
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.refresh_data_button.setEnabled(False)
        self.refresh_data_button.setText("Atualizando...")

        task = RefreshCardDataTask(
            missing_cards
        )
        task.signals.progress.connect(
            self.on_refresh_card_data_progress
        )
        task.signals.finished.connect(
            self.on_refresh_card_data_finished
        )
        task.signals.failed.connect(
            self.on_refresh_card_data_failed
        )

        self.scryfall_pool.start(task)

    def on_refresh_card_data_progress(
            self,
            current,
            total,
            name,
    ):
        self.refresh_data_button.setText(
            f"Atualizando {current}/{total}"
        )
        self.collection_count_label.setText(
            f"Analisando: {name}"
        )

    def on_refresh_card_data_finished(
            self,
            updated,
            total,
    ):
        self.refresh_data_button.setEnabled(True)
        self.refresh_data_button.setText("Atualizar dados")
        self.load_cards()

        QMessageBox.information(
            self,
            "Atualizar dados",
            (
                "Analise concluida.\n\n"
                f"Cartas verificadas: {total}\n"
                f"Cartas atualizadas: {updated}"
            ),
        )

    def on_refresh_card_data_failed(
            self,
            message,
    ):
        self.refresh_data_button.setEnabled(True)
        self.refresh_data_button.setText("Atualizar dados")

        QMessageBox.warning(
            self,
            "Atualizar dados",
            f"Nao foi possivel concluir a atualizacao:\n{message}",
        )

    # =====================================================
    # PESQUISA DA COLEÇÃO
    # =====================================================

    def search_collection(
            self,
            text,
    ):

        text = str(
            text or ""
        ).strip()

        # =================================================
        # PESQUISA VAZIA
        # =================================================

        if not text:
            self.search_result_cards = list(
                self.all_collection_cards
            )

            self.apply_collection_filters()

            return

        # =================================================
        # PESQUISAR NO BANCO
        # =================================================

        try:

            cards = search_cards(
                text
            )

        except Exception as error:

            print(
                "[DATABASE] Erro na pesquisa:",
                error,
            )

            cards = []

        # =================================================
        # GUARDAR RESULTADO DA PESQUISA
        # =================================================

        self.search_result_cards = list(
            cards
        )

        # =================================================
        # APLICAR FILTROS
        # =================================================

        self.apply_collection_filters()



    # =====================================================
    # VERIFICAR FILTRO DE COR
    # =====================================================

    def card_matches_color(
            self,
            card,
            color,
    ):

        if color == "all":
            return True

        colors = self.get_card_colors(
            card
        )

        # -------------------------------------------------
        # INCOLOR
        # -------------------------------------------------

        if color == "C":
            return len(
                colors
            ) == 0

        # -------------------------------------------------
        # MULTICOLOR
        # -------------------------------------------------

        if color == "M":
            return len(
                colors
            ) >= 2

        # -------------------------------------------------
        # COR ESPECÍFICA
        # -------------------------------------------------

        return color in colors



        # -------------------------------------------------
        # CRIATURA
        # -------------------------------------------------

        if type_filter == "Criatura":
            return (
                    "criatura" in type_line
                    or
                    "creature" in type_line
            )

        # -------------------------------------------------
        # MÁGICA INSTANTÂNEA
        # -------------------------------------------------

        if type_filter == "Mágica Instantânea":
            return (
                    "mágica instantânea" in type_line
                    or
                    "instant" in type_line
            )

        # -------------------------------------------------
        # FEITIÇO
        # -------------------------------------------------

        if type_filter == "Feitiço":
            return (
                    "feitiço" in type_line
                    or
                    "sorcery" in type_line
            )

        # -------------------------------------------------
        # ENCANTAMENTO
        # -------------------------------------------------

        if type_filter == "Encantamento":
            return (
                    "encantamento" in type_line
                    or
                    "enchantment" in type_line
            )

        # -------------------------------------------------
        # ARTEFATO
        # -------------------------------------------------

        if type_filter == "Artefato":
            return (
                    "artefato" in type_line
                    or
                    "artifact" in type_line
            )

        # -------------------------------------------------
        # PLANESWALKER
        # -------------------------------------------------

        if type_filter == "Planeswalker":
            return (
                    "planeswalker" in type_line
            )

        # -------------------------------------------------
        # TERRENO
        # -------------------------------------------------

        if type_filter == "Terreno":
            return (
                    "terreno" in type_line
                    or
                    "land" in type_line
            )

        return True

    # =====================================================
    # VERIFICAR FILTRO DE EDIÇÃO
    # =====================================================





        # =================================================
        # RECRIAR COMBOBOX
        # =================================================

        self.set_filter.blockSignals(
            True
        )

        try:

            self.set_filter.clear()

            self.set_filter.addItem(
                "Todas as edições",
                "all",
            )

            for set_name in sets:
                self.set_filter.addItem(
                    set_name,
                    set_name,
                )

            index = (
                self.set_filter.findData(
                    current
                )
            )

            if index >= 0:

                self.set_filter.setCurrentIndex(
                    index
                )

            else:

                self.set_filter.setCurrentIndex(
                    0
                )

        finally:

            self.set_filter.blockSignals(
                False
            )

    # =====================================================
    # OBTER QUANTIDADE
    # =====================================================

    def get_card_quantity(
            self,
            card,
    ):

        try:

            return int(
                card[10] or 0
            )

        except (
                IndexError,
                TypeError,
                ValueError,
        ):

            return 0

    # =====================================================
    # APLICAR TODOS OS FILTROS
    # =====================================================

    def apply_all_filters(self):
        # =================================================
        # LER VALORES
        # =================================================

        color = (
            self.color_filter.currentData()
        )

        card_type = (
            self.type_filter.currentData()
        )

        set_name = (
            self.set_filter.currentData()
        )

        sort_mode = (
            self.sort_filter.currentData()
        )

        if color is None:
            color = "all"

        if card_type is None:
            card_type = "all"

        if set_name is None:
            set_name = "all"

        if sort_mode is None:
            sort_mode = "name_asc"

        # =================================================
        # SALVAR ESTADO
        # =================================================

        self.active_color_filter = color
        self.active_type_filter = card_type
        self.active_set_filter = set_name
        self.active_sort = sort_mode

        # =================================================
        # ESCOLHER FONTE
        # =================================================
        #
        # Se existe texto na pesquisa:
        #     usa somente os resultados da pesquisa.
        #
        # Se não existe:
        #     usa toda a coleção.
        #
        # =================================================

        search_text = ""

        if hasattr(
                self,
                "search_input",
        ):
            search_text = (
                self.search_input.text()
                .strip()
            )

        if search_text:

            cards = list(
                self.search_result_cards
            )

        else:

            cards = list(
                self.all_collection_cards
            )

        # =================================================
        # FILTRAR
        # =================================================

        filtered = []

        for card in cards:

            # -------------------------------------------------
            # COR
            # -------------------------------------------------

            if not self.card_matches_color(
                    card,
                    color,
            ):
                continue

            # -------------------------------------------------
            # TIPO
            # -------------------------------------------------

            if not self.card_matches_type(
                    card,
                    card_type,
            ):
                continue

            # -------------------------------------------------
            # EDIÇÃO
            # -------------------------------------------------

            if not self.card_matches_set(
                    card,
                    set_name,
            ):
                continue

            filtered.append(
                card
            )

        # =================================================
        # ORDENAÇÃO
        # =================================================

        if sort_mode == "name_asc":

            filtered.sort(
                key=lambda card: str(
                    card[1] if len(card) > 1 else ""
                ).lower()
            )

        elif sort_mode == "name_desc":

            filtered.sort(
                key=lambda card: str(
                    card[1] if len(card) > 1 else ""
                ).lower(),
                reverse=True,
            )

        elif sort_mode == "quantity_asc":

            filtered.sort(
                key=lambda card:
                self.get_card_quantity(
                    card
                )
            )

        elif sort_mode == "quantity_desc":

            filtered.sort(
                key=lambda card:
                self.get_card_quantity(
                    card
                ),
                reverse=True,
            )

        elif sort_mode == "set_asc":

            filtered.sort(
                key=lambda card: str(
                    card[4] if len(card) > 4 else ""
                ).lower()
            )

        elif sort_mode == "set_desc":

            filtered.sort(
                key=lambda card: str(
                    card[4] if len(card) > 4 else ""
                ).lower(),
                reverse=True,
            )

        elif sort_mode == "newest":
            filtered.sort(
                key=lambda card: (
                    str(card[14] if len(card) > 14 else ""),
                    int(card[0] if len(card) > 0 else 0),
                ),
                reverse=True,
            )

        elif sort_mode == "oldest":

            filtered.sort(
                key=lambda card: (
                    str(card[14] if len(card) > 14 else ""),
                    int(card[0] if len(card) > 0 else 0),
                ),
            )
        # =================================================
        # MOSTRAR RESULTADO
        # =================================================

        self.display_cards(
            filtered
        )

    # =====================================================
    # LIMPAR FILTROS
    # =====================================================
    # =====================================================
    # CONTADOR DA COLEÇÃO
    # =====================================================

    def update_collection_count(
            self,
            cards,
    ):
        if cards is None:
            cards = []

        total_quantity = 0

        for card in cards:

            try:
                quantity = int(
                    card[10]
                    if len(card) > 10
                    else 0
                )

            except (
                    TypeError,
                    ValueError,
                    IndexError,
            ):
                quantity = 0

            total_quantity += max(
                quantity,
                0,
            )

        different_cards = len(
            cards
        )

        self.collection_count_label.setText(
            f"{total_quantity} cartas · "
            f"{different_cards} diferentes"
        )
    def clear_collection_filters(
            self,
    ):



        # =================================================
        # ESTADO PADRÃO
        # =================================================

        self.active_color_filter = "all"
        self.active_type_filter = "all"
        self.active_set_filter = "all"
        self.active_sort = "name_asc"

        # =================================================
        # ATUALIZAR
        # =================================================

        self.apply_collection_filters()

    # =====================================================
    # ATUALIZAR QUANTIDADE EM UMA LISTA
    # =====================================================

    def update_card_quantity_in_list(
            self,
            cards,
            card_id,
            new_quantity,
    ):

        updated = []

        for card in cards:

            try:

                current_id = int(
                    card[0]
                )

            except (
                    TypeError,
                    ValueError,
                    IndexError,
            ):

                updated.append(
                    card
                )

                continue

            # -------------------------------------------------
            # CARTA DIFERENTE
            # -------------------------------------------------

            if current_id != card_id:
                updated.append(
                    card
                )

                continue

            # -------------------------------------------------
            # CARTA ENCONTRADA
            # -------------------------------------------------

            card_data = list(
                card
            )

            if len(card_data) > 10:
                card_data[10] = (
                    new_quantity
                )

            updated.append(
                tuple(
                    card_data
                )
            )

        return updated

    # =====================================================
    # ATUALIZAR QUANTIDADE NAS FONTES
    # =====================================================

    def update_quantity_in_filter_sources(
            self,
            card_id,
            new_quantity,
    ):

        self.all_collection_cards = (
            self.update_card_quantity_in_list(
                self.all_collection_cards,
                card_id,
                new_quantity,
            )
        )

        self.search_result_cards = (
            self.update_card_quantity_in_list(
                self.search_result_cards,
                card_id,
                new_quantity,
            )
        )

        self.current_cards = (
            self.update_card_quantity_in_list(
                self.current_cards,
                card_id,
                new_quantity,
            )
        )

    # =====================================================
    # LIMPAR LAYOUT
    # =====================================================

    # =====================================================
    # LIMPAR LAYOUT
    # =====================================================

    def clear_cards_layout(self):

        while self.cards_layout.count():

            item = (
                self.cards_layout.takeAt(0)
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()

                continue

            nested_layout = item.layout()

            if nested_layout:

                while nested_layout.count():

                    nested_item = (
                        nested_layout.takeAt(0)
                    )

                    nested_widget = (
                        nested_item.widget()
                    )

                    if nested_widget:

                        nested_widget.deleteLater()

    # =====================================================
    # DISPLAY
    # =====================================================

    def display_cards(
            self,
            cards,
    ):

        if cards is None:
            cards = []

        self._grid_generation += 1

        generation = self._grid_generation

        self.current_cards = list(
            cards
        )

        self.card_rows.clear()

        self.rebuilding_grid = True

        self.setUpdatesEnabled(
            False
        )
        
        self.scroll_area.setUpdatesEnabled(True)

        try:

            self.clear_cards_layout()

            if self.current_layout == "grid":

                self.display_cards_grid(
                    self.current_cards,
                    generation,
                )

            else:

                self.display_cards_list(
                    self.current_cards,
                )

        finally:

            self.rebuilding_grid = False

            # Aplicar delay configurável antes de mostrar as cartas
            if COLLECTION_RENDER_DELAY > 0:
                QTimer.singleShot(
                    COLLECTION_RENDER_DELAY,
                    lambda: self.setUpdatesEnabled(True)
                )
            else:
                self.setUpdatesEnabled(True)
            
            self.scroll_area.setUpdatesEnabled(True)

    # =====================================================
    # DISPLAY — LISTA
    # =====================================================

    def display_cards_list(
        self,
        cards,
    ):

        for card in cards:

            try:
                card_id = card[0] if len(card) > 0 else None
                name = card[1] if len(card) > 1 else ""
                printed_name = card[2] if len(card) > 2 else None
                lang = card[3] if len(card) > 3 else None
                set_name = card[4] if len(card) > 4 else None
                collector_number = card[5] if len(card) > 5 else None
                mana_cost = card[6] if len(card) > 6 else None
                type_line = card[7] if len(card) > 7 else None
                oracle_text = card[8] if len(card) > 8 else None
                image_url = card[9] if len(card) > 9 else None
                quantity = card[10] if len(card) > 10 else 0
                image_path = card[11] if len(card) > 11 else None
                power = card[12] if len(card) > 12 else None
                toughness = card[13] if len(card) > 13 else None
                created_at = card[14] if len(card) > 14 else None
                card_faces = card[15] if len(card) > 15 else None
            except (IndexError, TypeError):
                continue

            self.create_card_widget(
                card_id,
                name,
                printed_name,
                lang,
                set_name,
                collector_number,
                mana_cost,
                type_line,
                oracle_text,
                image_url,
                quantity,
                image_path,
                power,
                toughness,
                card_faces,
            )

    # =====================================================
    # MANA — CACHE
    # =====================================================

    def get_cached_mana_widget(
            self,
            mana_cost,
            symbol_size=22,
            parent=None,
    ):
        if not mana_cost:
            return None
        
        widget = ManaSymbolsWidget(
            mana_cost,
            symbol_size=symbol_size,
        )
        
        if parent:
            widget.setParent(parent)
        
        return widget

    # =====================================================
    # FILTROS DA COLEÇÃO
    # =====================================================

    def get_card_colors(
        self,
        mana_cost,
    ):

        if not mana_cost:
            return set()

        mana = str(
            mana_cost
        ).upper()

        colors = set()

        if "{W}" in mana:
            colors.add("W")

        if "{U}" in mana:
            colors.add("U")

        if "{B}" in mana:
            colors.add("B")

        if "{R}" in mana:
            colors.add("R")

        if "{G}" in mana:
            colors.add("G")

        return colors

    def card_matches_type(
            self,
            card,
            type_filter,
    ):
        if (
                not type_filter
                or type_filter == "all"
        ):
            return True

        if not card:
            return False

        try:
            type_line = str(
                card[7]
                if len(card) > 7
                else ""
            ).strip().lower()

        except (
                IndexError,
                TypeError,
        ):
            return False

        if not type_line:
            return False

        type_map = {
            "Criatura": (
                "criatura",
                "creature",
            ),

            "Mágica Instantânea": (
                "mágica instantânea",
                "instant",
            ),

            "Feitiço": (
                "feitiço",
                "sorcery",
            ),

            "Encantamento": (
                "encantamento",
                "enchantment",
            ),

            "Artefato": (
                "artefato",
                "artifact",
            ),

            "Planeswalker": (
                "planeswalker",
            ),

            "Terreno": (
                "terreno",
                "land",
            ),
        }

        accepted_types = (
            type_map.get(
                type_filter
            )
        )

        if not accepted_types:
            # Fallback para filtros futuros
            return (
                    str(type_filter)
                    .strip()
                    .lower()
                    in type_line
            )

        return any(
            accepted_type in type_line
            for accepted_type
            in accepted_types
        )
    def card_matches_set(
        self,
        card,
        set_filter,
    ):

        if set_filter == "all":
            return True

        if not card or len(card) <= 4:
            return False

        return (
            str(card[4] if len(card) > 4 else "").lower()
            == str(set_filter or "").lower()
        )

    def sort_collection_cards(
            self,
            cards,
            sort_mode,
    ):

        cards = list(
            cards
        )

        if sort_mode == "name_asc":

            cards.sort(
                key=lambda card: str(
                    card[1] or ""
                ).lower()
            )

        elif sort_mode == "name_desc":

            cards.sort(
                key=lambda card: str(
                    card[1] or ""
                ).lower(),
                reverse=True,
            )

        elif sort_mode == "quantity_asc":

            cards.sort(
                key=lambda card: int(
                    card[10] or 0
                )
            )

        elif sort_mode == "quantity_desc":

            cards.sort(
                key=lambda card: int(
                    card[10] or 0
                ),
                reverse=True,
            )

        elif sort_mode == "set_asc":

            cards.sort(
                key=lambda card: str(
                    card[4] or ""
                ).lower()
            )

        elif sort_mode == "set_desc":

            cards.sort(
                key=lambda card: str(
                    card[4] or ""
                ).lower(),
                reverse=True,
            )

        elif sort_mode == "newest":

            cards.sort(
                key=lambda card: str(
                    card[14] or ""
                ),
                reverse=True,
            )

        elif sort_mode == "oldest":

            cards.sort(
                key=lambda card: str(
                    card[14] or ""
                ),
                reverse=False,
            )

        return cards

    def apply_collection_filters(
            self,
    ):
        if not hasattr(
                self,
                "color_filter",
        ):
            return

        color = (
                self.color_filter.currentData()
                or "all"
        )

        card_type = (
                self.type_filter.currentData()
                or "all"
        )

        set_name = (
                self.set_filter.currentData()
                or "all"
        )

        sort_mode = (
                self.sort_filter.currentData()
                or "name_asc"
        )

        self.active_color_filter = (
            color
        )

        self.active_type_filter = (
            card_type
        )

        self.active_set_filter = (
            set_name
        )

        self.active_sort = (
            sort_mode
        )

        # =================================================
        # FONTE DOS DADOS
        # =================================================

        search_text = ""

        if hasattr(
                self,
                "search_input",
        ):
            search_text = (
                self.search_input
                .text()
                .strip()
            )

        if search_text:
            cards = list(
                self.search_result_cards
            )
        else:
            cards = list(
                self.all_collection_cards
            )

        # =================================================
        # FILTROS
        # =================================================

        filtered = []

        for card in cards:

            if not self.card_matches_color(
                    card,
                    color,
            ):
                continue

            if not self.card_matches_type(
                    card,
                    card_type,
            ):
                continue

            if not self.card_matches_set(
                    card,
                    set_name,
            ):
                continue

            filtered.append(
                card
            )

        # =================================================
        # ORDENAÇÃO
        # =================================================

        filtered = (
            self.sort_collection_cards(
                filtered,
                sort_mode,
            )
        )

        # =================================================
        # CONTADOR
        # =================================================

        self.update_collection_count(
            filtered
        )

        # =================================================
        # MOSTRAR
        # =================================================

        self.current_cards = list(
            filtered
        )

        self.display_cards(
            self.current_cards
        )

    def clear_collection_filters(
            self,
    ):

        self.color_filter.blockSignals(
            True
        )

        self.type_filter.blockSignals(
            True
        )

        self.set_filter.blockSignals(
            True
        )

        self.sort_filter.blockSignals(
            True
        )

        self.color_filter.setCurrentIndex(
            0
        )

        self.type_filter.setCurrentIndex(
            0
        )

        self.set_filter.setCurrentIndex(
            0
        )

        self.sort_filter.setCurrentIndex(
            0
        )

        self.color_filter.blockSignals(
            False
        )

        self.type_filter.blockSignals(
            False
        )

        self.set_filter.blockSignals(
            False
        )

        self.sort_filter.blockSignals(
            False
        )

        self.apply_collection_filters()
    def populate_set_filter(
        self,
    ):

        if not hasattr(
            self,
            "set_filter",
        ):
            return

        current = (
            self.set_filter.currentData()
        )

        sets = sorted(
            {
                str(card[4])
                for card
                in self.all_collection_cards
                if (
                    len(card) > 4
                    and card[4]
                )
            },
            key=str.lower,
        )

        self.set_filter.blockSignals(
            True
        )

        self.set_filter.clear()

        self.set_filter.addItem(
            "Todas as edições",
            "all",
        )

        for set_name in sets:

            self.set_filter.addItem(
                set_name,
                set_name,
            )

        index = (
            self.set_filter.findData(
                current
            )
        )

        if index >= 0:

            self.set_filter.setCurrentIndex(
                index
            )

        self.set_filter.blockSignals(
            False
        )

    def save_collection_filter_settings(
        self,
    ):

        self.settings.setValue(
            "collection/color_filter",
            self.active_color_filter,
        )

        self.settings.setValue(
            "collection/type_filter",
            self.active_type_filter,
        )

        self.settings.setValue(
            "collection/set_filter",
            self.active_set_filter,
        )

        self.settings.setValue(
            "collection/sort_filter",
            self.active_sort,
        )

    def restore_collection_filter_settings(
        self,
    ):

        color = self.settings.value(
            "collection/color_filter",
            "all",
            type=str,
        )

        card_type = self.settings.value(
            "collection/type_filter",
            "all",
            type=str,
        )

        set_name = self.settings.value(
            "collection/set_filter",
            "all",
            type=str,
        )

        sort_mode = self.settings.value(
            "collection/sort_filter",
            "name_asc",
            type=str,
        )

        self.color_filter.blockSignals(
            True
        )

        self.type_filter.blockSignals(
            True
        )

        self.set_filter.blockSignals(
            True
        )

        self.sort_filter.blockSignals(
            True
        )

        color_index = (
            self.color_filter.findData(
                color
            )
        )

        if color_index >= 0:

            self.color_filter.setCurrentIndex(
                color_index
            )

        type_index = (
            self.type_filter.findData(
                card_type
            )
        )

        if type_index >= 0:

            self.type_filter.setCurrentIndex(
                type_index
            )

        set_index = (
            self.set_filter.findData(
                set_name
            )
        )

        if set_index >= 0:

            self.set_filter.setCurrentIndex(
                set_index
            )

        sort_index = (
            self.sort_filter.findData(
                sort_mode
            )
        )

        if sort_index >= 0:

            self.sort_filter.setCurrentIndex(
                sort_index
            )

        self.color_filter.blockSignals(
            False
        )

        self.type_filter.blockSignals(
            False
        )

        self.set_filter.blockSignals(
            False
        )

        self.sort_filter.blockSignals(
            False
        )

        self.active_color_filter = (
            self.color_filter.currentData()
            or "all"
        )

        self.active_type_filter = (
            self.type_filter.currentData()
            or "all"
        )

        self.active_set_filter = (
            self.set_filter.currentData()
            or "all"
        )

        self.active_sort = (
            self.sort_filter.currentData()
            or "name_asc"
        )

    # =====================================================
    # DISPLAY — GRADE
    # =====================================================

    def display_cards_grid(
            self,
            cards,
            generation,
    ):

        grid_layout = QGridLayout()

        grid_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        grid_layout.setHorizontalSpacing(
            12
        )

        grid_layout.setVerticalSpacing(
            12
        )

        available_width = (
            self.scroll_area
            .viewport()
            .width()
        )

        if available_width <= 0:

            available_width = (
                self.cards_container.width()
            )

        if available_width <= 0:

            available_width = 800

        spacing = 14
        min_card_width = 160

        columns = max(
            1,
            int(
                (
                    available_width
                    + spacing
                )
                /
                (
                    min_card_width
                    + spacing
                )
            ),
        )

        total_spacing = (
            (columns - 1)
            * spacing
        )

        card_width = int(
            (
                available_width
                - total_spacing
            )
            /
            columns
        )

        card_width = max(
            min_card_width,
            card_width,
        )

        card_width = min(
            card_width,
            500,
        )

        self._grid_columns = columns

        for index, card in enumerate(cards):

            try:
                card_id = card[0] if len(card) > 0 else None
                name = card[1] if len(card) > 1 else ""
                printed_name = card[2] if len(card) > 2 else None
                lang = card[3] if len(card) > 3 else None
                set_name = card[4] if len(card) > 4 else None
                collector_number = card[5] if len(card) > 5 else None
                mana_cost = card[6] if len(card) > 6 else None
                type_line = card[7] if len(card) > 7 else None
                oracle_text = card[8] if len(card) > 8 else None
                image_url = card[9] if len(card) > 9 else None
                quantity = card[10] if len(card) > 10 else 0
                image_path = card[11] if len(card) > 11 else None
                power = card[12] if len(card) > 12 else None
                toughness = card[13] if len(card) > 13 else None
                created_at = card[14] if len(card) > 14 else None
                card_faces = card[15] if len(card) > 15 else None
            except (IndexError, TypeError):
                continue

            try:

                card_id = int(
                    card_id
                )

            except (
                TypeError,
                ValueError,
            ):

                continue

            if card_id <= 0:
                continue

            card_data = {
                "id": card_id,
                "name": name,
                "printed_name": printed_name,
                "lang": lang,
                "set_name": set_name,
                "collector_number": collector_number,
                "mana_cost": mana_cost,
                "type_line": type_line,
                "oracle_text": oracle_text,
                "image_url": image_url,
                "image_path": image_path,
                "quantity": quantity,
                "power": power,
                "toughness": toughness,
                "created_at": created_at,
                "card_faces": card_faces,
            }

            frame = GridCardFrame()

            frame.set_card_width(
                card_width
            )

            frame.setToolTip(
                name or ""
            )

            frame.doubleClicked.connect(
                lambda card=card_data:
                self.show_card_details(
                    card
                )
            )

            frame.set_quantity(
                quantity
            )

            frame.minus_button.clicked.connect(
                lambda checked=False,
                       cid=card_id:
                self.change_card_quantity(
                    cid,
                    -1,
                )
            )

            frame.plus_button.clicked.connect(
                lambda checked=False,
                       cid=card_id:
                self.change_card_quantity(
                    cid,
                    1,
                )
            )

            frame.control_quantity.editingFinished.connect(
                lambda cid=card_id,
                       widget=frame.control_quantity:
                self.set_card_quantity_from_input(
                    cid,
                    widget,
                )
            )

            self.card_rows[card_id] = {
                "frame": frame,
                "grid": True,
            }

            # -------------------------------------------------
            # IMAGEM - CARREGAR ANTES DE ADICIONAR AO GRID
            # -------------------------------------------------

            local_path = None
            pixmap = None

            if image_path:
                local_path = Path(
                    image_path
                )

                if local_path.exists():
                    # Carregar imagem síncrona como nos Decks
                    cache_key = str(local_path)
                    pixmap = self.image_cache.get(cache_key)
                    
                    if pixmap is None or pixmap.isNull():
                        try:
                            pixmap = QPixmap(str(local_path))
                            if not pixmap.isNull():
                                self.image_cache[cache_key] = pixmap
                                _cleanup_image_cache()
                        except Exception:
                            pixmap = None

            # Definir imagem no frame antes de adicionar ao grid
            if pixmap and not pixmap.isNull():
                self.set_grid_thumbnail(frame.image_label, pixmap)
            else:
                # Usa card.png como placeholder
                if CARD_ICON_PATH.exists():
                    placeholder = QPixmap(str(CARD_ICON_PATH))
                    if not placeholder.isNull():
                        width = card_width
                        height = round(width * 88 / 63)
                        scaled = placeholder.scaled(
                            width,
                            height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )
                        frame.image_label.setPixmap(scaled)
                        frame.image_label.setText("")

            row = (
                index
                // columns
            )

            column = (
                index
                % columns
            )

            grid_layout.addWidget(
                frame,
                row,
                column,
                Qt.AlignmentFlag.AlignTop
                |
                Qt.AlignmentFlag.AlignLeft,
            )

            # -------------------------------------------------
            # DOWNLOAD ASSÍNCRONO SE NECESSÁRIO
            # -------------------------------------------------

            # Se não tem imagem local e tem URL, baixa assíncrono
            if not (pixmap and not pixmap.isNull()) and image_url:
                if not image_path:
                    scryfall_id = (
                        self.get_scryfall_id_from_url(
                            image_url
                        )
                    )

                    local_path = (
                        get_card_image_path(
                            scryfall_id
                        )
                        if scryfall_id
                        else None
                    )

                if local_path:
                    task = ImageTask(
                        image_url,
                        local_path,
                        frame.image_label,
                    )

                    task.signals.finished.connect(
                        self.receive_image
                    )

                    task.signals.failed.connect(
                        self.receive_image_error
                    )

                    self.image_pool.start(
                        task
                    )

        for column in range(
            columns
        ):

            grid_layout.setColumnStretch(
                column,
                1,
            )

        self.cards_layout.addLayout(
            grid_layout
        )

    # =====================================================
    # CRIAR LINHA DA CARTA
    # =====================================================

    def create_card_widget(
        self,
        card_id,
        name,
        printed_name,
        lang,
        set_name,
        collector_number,
        mana_cost,
        type_line,
        oracle_text,
        image_url,
        quantity,
        image_path,
        power,
        toughness,
        card_faces=None,
    ):

        try:

            card_id = int(
                card_id
            )

        except (
            TypeError,
            ValueError,
        ):

            return

        if card_id <= 0:
            return

        frame = CardFrame()

        frame.setObjectName(
            "CardFrame"
        )

        frame.setMinimumHeight(
            96
        )

        frame.setMaximumHeight(
            96
        )

        frame.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        card_data = {
            "id": card_id,
            "name": name,
            "printed_name": printed_name,
            "lang": lang,
            "set_name": set_name,
            "collector_number": collector_number,
            "mana_cost": mana_cost,
            "type_line": type_line,
            "oracle_text": oracle_text,
            "image_url": image_url,
            "image_path": image_path,
            "quantity": quantity,
            "power": power,
            "toughness": toughness,
            "card_faces": card_faces,
        }

        frame.doubleClicked.connect(
            lambda card=card_data:
            self.show_card_details(
                card
            )
        )

        layout = QHBoxLayout(
            frame
        )

        layout.setContentsMargins(
            10,
            8,
            12,
            8,
        )

        layout.setSpacing(
            14
        )

        # =================================================
        # MINIATURA
        # =================================================

        image_label = CardImageLabel()

        image_label.setObjectName(
            "CardThumbnail"
        )

        image_label.setFixedSize(
            58,
            78,
        )

        image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        image_label.setText(
            ""
        )
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    58,
                    78,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                image_label.setPixmap(scaled)

        image_label.doubleClicked.connect(
            lambda card=card_data:
            self.show_card_details(
                card
            )
        )

        layout.addWidget(
            image_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        # =================================================
        # INFORMAÇÕES
        # =================================================

        info_widget = QWidget()

        info_widget.setObjectName(
            "CardInfo"
        )

        info_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        info_widget.setFixedHeight(
            78
        )

        info_layout = QVBoxLayout(
            info_widget
        )

        info_layout.setContentsMargins(
            0,
            1,
            0,
            1,
        )

        info_layout.setSpacing(
            3
        )

        name_label = QLabel(
            name
        )

        name_label.setObjectName(
            "CardName"
        )

        name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        name_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        info_layout.addWidget(
            name_label
        )

        # =================================================
        # MANA + P/T
        # =================================================

        has_mana = bool(
            mana_cost
        )

        has_pt = (
            power is not None
            and toughness is not None
        )

        if has_mana or has_pt:

            meta_widget = QWidget()

            meta_widget.setObjectName(
                "CardMeta"
            )

            meta_widget.setSizePolicy(
                QSizePolicy.Policy.Minimum,
                QSizePolicy.Policy.Fixed,
            )

            meta_widget.setFixedHeight(
                34
            )

            meta_layout = QHBoxLayout(
                meta_widget
            )

            meta_layout.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            meta_layout.setSpacing(
                9
            )

            # =================================================
            # MANA
            # =================================================

            if has_mana:

                mana_widget = (
                    self.get_cached_mana_widget(
                        mana_cost,
                        symbol_size=22,
                        parent=meta_widget,
                    )
                )

                if mana_widget:

                    meta_layout.addWidget(
                        mana_widget,
                        0,
                        Qt.AlignmentFlag.AlignVCenter,
                    )

            # =================================================
            # SEPARADOR
            # =================================================

            if has_mana and has_pt:

                separator = QFrame()

                separator.setObjectName(
                    "CardMetaSeparator"
                )

                separator.setFrameShape(
                    QFrame.Shape.VLine
                )

                separator.setFrameShadow(
                    QFrame.Shadow.Plain
                )

                separator.setMinimumSize(
                    1,
                    24,
                )

                separator.setMaximumSize(
                    1,
                    24,
                )

                meta_layout.addWidget(
                    separator,
                    0,
                    Qt.AlignmentFlag.AlignVCenter,
                )

            # =================================================
            # POWER / TOUGHNESS
            # =================================================

            if has_pt:

                pt_label = QLabel(
                    f"{power} / {toughness}"
                )

                pt_label.setObjectName(
                    "CardPT"
                )

                pt_label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                pt_label.setFixedSize(
                    64,
                    32,
                )

                meta_layout.addWidget(
                    pt_label,
                    0,
                    Qt.AlignmentFlag.AlignVCenter,
                )

            meta_row = QHBoxLayout()

            meta_row.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            meta_row.addStretch()

            meta_row.addWidget(
                meta_widget,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

            info_layout.addLayout(
                meta_row
            )

        # =================================================
        # TIPO
        # =================================================

        type_label = QLabel(
            type_line or "—"
        )

        type_label.setObjectName(
            "CardType"
        )

        type_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        type_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        info_layout.addWidget(
            type_label
        )

        # =================================================
        # EDIÇÃO
        # =================================================

        set_text = (
            set_name
            or "Edição desconhecida"
        )

        if collector_number:

            set_text += (
                f"   •   #{collector_number}"
            )

        set_label = QLabel(
            set_text
        )

        set_label.setObjectName(
            "CardSet"
        )

        set_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        set_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        info_layout.addWidget(
            set_label
        )

        layout.addWidget(
            info_widget,
            1,
        )

        # =================================================
        # SEPARADOR
        # =================================================

        quantity_separator = QFrame()

        quantity_separator.setObjectName(
            "CardMetaSeparator"
        )

        quantity_separator.setFrameShape(
            QFrame.Shape.VLine
        )

        quantity_separator.setFrameShadow(
            QFrame.Shadow.Plain
        )

        layout.addWidget(
            quantity_separator,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        # =================================================
        # QUANTIDADE
        # =================================================

        quantity_frame = QFrame()

        quantity_frame.setObjectName(
            "QuantityFrame"
        )

        quantity_frame.setFixedHeight(
            78
        )

        quantity_layout = QHBoxLayout(
            quantity_frame
        )

        quantity_layout.setContentsMargins(
            10,
            0,
            0,
            0,
        )

        quantity_layout.setSpacing(
            4
        )

        minus_button = QPushButton(
            "−"
        )

        minus_button.setObjectName(
            "QuantityButton"
        )

        minus_button.setFixedSize(
            30,
            30,
        )

        minus_button.clicked.connect(
            lambda checked=False,
                   cid=card_id:
            self.change_card_quantity(
                cid,
                -1,
            )
        )

        quantity_layout.addWidget(
            minus_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        quantity_label = QLineEdit(
            str(quantity)
        )

        quantity_label.setObjectName(
            "Quantity"
        )

        quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        quantity_label.setValidator(
            QIntValidator(
                0,
                999999,
                quantity_label,
            )
        )

        quantity_label.setFixedSize(
            28,
            30,
        )

        quantity_layout.addWidget(
            quantity_label,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        plus_button = QPushButton(
            "+"
        )

        plus_button.setObjectName(
            "QuantityButton"
        )

        plus_button.setFixedSize(
            30,
            30,
        )

        plus_button.clicked.connect(
            lambda checked=False,
                   cid=card_id:
            self.change_card_quantity(
                cid,
                1,
            )
        )

        quantity_label.editingFinished.connect(
            lambda cid=card_id,
                   widget=quantity_label:
            self.set_card_quantity_from_input(
                cid,
                widget,
            )
        )

        quantity_layout.addWidget(
            plus_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        layout.addWidget(
            quantity_frame,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        self.card_rows[card_id] = {
            "frame": frame,
            "quantity_label": quantity_label,
            "grid": False,
        }

        # =================================================
        # IMAGEM LOCAL - CARREGAR ANTES DE ADICIONAR AO LAYOUT
        # =================================================

        local_path = None
        pixmap = None

        if image_path:
            local_path = Path(image_path)
            
            if local_path.exists() and local_path.stat().st_size > 0:
                # Carregar imagem síncrona como nos Decks
                cache_key = str(local_path)
                pixmap = self.image_cache.get(cache_key)
                
                if pixmap is None or pixmap.isNull():
                    try:
                        pixmap = QPixmap(str(local_path))
                        if not pixmap.isNull():
                            self.image_cache[cache_key] = pixmap
                            _cleanup_image_cache()
                    except Exception:
                        pixmap = None

        # Definir imagem no label antes de adicionar ao layout
        if pixmap and not pixmap.isNull():
            scaled = pixmap.scaled(
                58,
                78,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            image_label.setPixmap(scaled)
            image_label.setText("")

        self.cards_layout.addWidget(
            frame
        )

        # =================================================
        # DOWNLOAD ASSÍNCRONO SE NECESSÁRIO
        # =================================================

        # Se não tem imagem local e tem URL, baixa assíncrono
        if not (pixmap and not pixmap.isNull()) and image_url:
            if not image_path:
                scryfall_id = (
                    self.get_scryfall_id_from_url(
                        image_url
                    )
                )

                local_path = (
                    get_card_image_path(
                        scryfall_id
                    )
                    if scryfall_id
                    else None
                )

            if local_path:
                task = ImageTask(
                    image_url,
                    local_path,
                    image_label,
                )

                task.signals.finished.connect(
                    self.receive_image
                )

                task.signals.failed.connect(
                    self.receive_image_error
                )

                self.image_pool.start(
                    task
                )


    # =====================================================
    # ID PELO URL
    # =====================================================

    def get_scryfall_id_from_url(
        self,
        url,
    ):

        if not url:
            return None

        try:

            filename = (
                url
                .split("/")[-1]
                .split("?")[0]
            )

            if filename.endswith(
                ".jpg"
            ):

                return filename[:-4]

        except Exception:
            pass

        return None

    # =====================================================
    # IMAGEM LOCAL — LISTA
    # =====================================================

    def load_local_thumbnail(
        self,
        label,
        path,
    ):

        try:

            cache_key = str(
                path
            )

            pixmap = self.image_cache.get(
                cache_key
            )

            if (
                pixmap is None
                or pixmap.isNull()
            ):

                pixmap = QPixmap(
                    str(path)
                )

                if pixmap.isNull():
                    return

                self.image_cache[
                    cache_key
                ] = pixmap
                
                # Limpar cache se necessário
                _cleanup_image_cache()

            self.set_thumbnail(
                label,
                pixmap,
            )

        except (FileNotFoundError, PermissionError, OSError) as error:
            print(f"[IMAGE] Erro ao carregar imagem local: {error}")
        except Exception as error:
            print(f"[IMAGE] Erro inesperado ao carregar imagem: {error}")

    # =====================================================
    # IMAGEM LOCAL — GRADE
    # =====================================================

    def load_grid_thumbnail(
        self,
        label,
        path,
    ):

        try:

            cache_key = str(
                path
            )

            pixmap = self.image_cache.get(
                cache_key
            )

            if (
                pixmap is None
                or pixmap.isNull()
            ):

                pixmap = QPixmap(
                    str(path)
                )

                if pixmap.isNull():
                    return

                self.image_cache[
                    cache_key
                ] = pixmap
                
                # Limpar cache se necessário
                _cleanup_image_cache()

            self.set_grid_thumbnail(
                label,
                pixmap,
            )

        except Exception as error:

            print(
                "[IMAGE] Erro ao carregar imagem da grade:",
                error,
            )

    # =====================================================
    # DOWNLOAD RECEBIDO
    # =====================================================

    # =====================================================
    # DOWNLOAD RECEBIDO
    # =====================================================

    def receive_image(
            self,
            url,
            path,
            data,
            label,
            generation=None,
    ):

        # -------------------------------------------------
        # VALIDAR LABEL
        # -------------------------------------------------

        if (
                label is None
                or not shiboken6.isValid(label)
        ):
            return

        # -------------------------------------------------
        # CRIAR PIXMAP
        # -------------------------------------------------

        pixmap = QPixmap()

        if not pixmap.loadFromData(data):
            print(
                "[IMAGE] Não foi possível carregar "
                "a imagem recebida."
            )
            return

        # -------------------------------------------------
        # CACHE POR URL
        # -------------------------------------------------

        if url:
            self.image_cache[
                str(url)
            ] = pixmap

        # -------------------------------------------------
        # CACHE POR CAMINHO LOCAL
        # -------------------------------------------------

        if path:
            self.image_cache[
                str(path)
            ] = pixmap

        # -------------------------------------------------
        # ATUALIZAR LABEL IMEDIATAMENTE
        # -------------------------------------------------

        if (
                label.objectName()
                == "GridCardImage"
        ):

            self.set_grid_thumbnail(
                label,
                pixmap,
            )

        else:

            self.set_thumbnail(
                label,
                pixmap,
            )

        # -------------------------------------------------
        # FORÇAR ATUALIZAÇÃO VISUAL
        # -------------------------------------------------

        label.clear()

        if (
                label.objectName()
                == "GridCardImage"
        ):

            self.set_grid_thumbnail(
                label,
                pixmap,
            )

        else:

            self.set_thumbnail(
                label,
                pixmap,
            )

        label.update()
        label.repaint()

        try:

            self.scroll_area.viewport().update()

            self.cards_container.update()

        except Exception:
            pass

    # =====================================================
    # ATUALIZAR CARTAS APÓS RECEBER IMAGEM
    # =====================================================

    def refresh_card_images(
            self,
    ):

        try:

            if not self.current_cards:
                return

            # Força a interface a reconstruir
            # os cards usando o cache de imagens atualizado.
            self.display_cards(
                self.current_cards
            )

            # Garante que as atualizações visuais
            # estejam habilitadas.
            self.scroll_area.setUpdatesEnabled(
                True
            )

            self.scroll_area.viewport().update()

            self.cards_container.update()

        except Exception as error:

            print(
                "[IMAGE] Erro ao atualizar cards:",
                error,
            )

    def receive_image_error(
        self,
        url,
        error,
        label,
    ):

        print(
            f"[IMAGE] Falha: {url} | {error}"
        )

        if label:

            label.setText(
                "🃏"
            )

    # =====================================================
    # MINIATURA — LISTA
    # =====================================================

    def set_thumbnail(self, label, pixmap):
        if pixmap is None or pixmap.isNull():
            pixmap = QPixmap(str(CARD_ICON_PATH))

        scaled = pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        label.clear()
        label.setPixmap(scaled)

    # =====================================================
    # MINIATURA — GRADE
    # =====================================================

    def set_grid_thumbnail(
        self,
        label,
        pixmap,
    ):

        if (
            not pixmap
            or pixmap.isNull()
        ):

            label.setText(
                ""
            )
            
            # Usar card.png como placeholder
            if CARD_ICON_PATH.exists():
                pixmap = QPixmap(str(CARD_ICON_PATH))
                if not pixmap.isNull():
                    width = label.width()
                    height = label.height()
                    if width <= 0:
                        width = 160
                    if height <= 0:
                        height = round(width * 88 / 63)
                    scaled = pixmap.scaled(
                        width,
                        height,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    label.setPixmap(scaled)

            return

        width = label.width()
        height = label.height()

        if width <= 0:
            width = 160

        if height <= 0:

            height = round(
                width * 88 / 63
            )

        scaled = pixmap.scaled(
            label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        label.setText(
            ""
        )

        label.setPixmap(
            scaled
        )

    # =====================================================
    # DETALHES DA CARTA
    # =====================================================

    def show_card_details(
        self,
        card,
    ):

        if not card:
            return

        pixmap = None

        image_url = card.get(
            "image_url"
        )

        if image_url:

            pixmap = self.image_cache.get(
                image_url
            )

        if (
            pixmap is None
            or pixmap.isNull()
        ):

            image_path = card.get(
                "image_path"
            )

            if image_path:

                try:

                    path = Path(
                        image_path
                    )

                    if (
                        path.exists()
                        and path.stat().st_size > 0
                    ):

                        cache_key = str(
                            path
                        )

                        pixmap = self.image_cache.get(
                            cache_key
                        )

                        if (
                            pixmap is None
                            or pixmap.isNull()
                        ):

                            pixmap = QPixmap(
                                str(path)
                            )

                            if not pixmap.isNull():

                                self.image_cache[
                                    cache_key
                                ] = pixmap
                                
                                # Limpar cache se necessário
                                _cleanup_image_cache()

                                if image_url:

                                    self.image_cache[
                                        image_url
                                    ] = pixmap
                                    
                                    # Limpar cache se necessário
                                    _cleanup_image_cache()

                except Exception as error:

                    print(
                        "[DETAILS] Erro ao carregar imagem:",
                        error,
                    )

        dialog = CardDetailsDialog(
            card,
            pixmap,
            self,
        )

        dialog.exec()



    # =====================================================
    # QUANTIDADE
    # =====================================================

    def set_card_quantity_from_input(
            self,
            card_id,
            quantity_widget,
    ):
        try:
            card_id = int(
                card_id
            )
        except (
                TypeError,
                ValueError,
        ):
            return

        if card_id <= 0 or quantity_widget is None:
            return

        text = (
            quantity_widget
            .text()
            .strip()
        )

        try:
            new_quantity = int(
                text
            )
        except (
                TypeError,
                ValueError,
        ):
            new_quantity = 0

        new_quantity = max(
            0,
            new_quantity,
        )

        success = set_card_quantity(
            card_id,
            new_quantity,
        )

        if not success:
            return

        if new_quantity <= 0:
            self.card_rows.pop(
                card_id,
                None,
            )

            self.current_cards = [
                card
                for card in self.current_cards
                if str(card[0]) != str(card_id)
            ]

            self.all_collection_cards = [
                card
                for card in self.all_collection_cards
                if str(card[0]) != str(card_id)
            ]

            self.search_result_cards = [
                card
                for card in self.search_result_cards
                if str(card[0]) != str(card_id)
            ]

            self.apply_collection_filters()
            return

        row_data = self.card_rows.get(
            card_id,
            {},
        )

        frame = row_data.get(
            "frame"
        )

        if row_data.get("grid") and frame is not None:
            if hasattr(
                    frame,
                    "set_quantity",
            ):
                frame.set_quantity(
                    new_quantity
                )
        else:
            quantity_widget.setText(
                str(new_quantity)
            )

        self.update_quantity_in_filter_sources(
            card_id,
            new_quantity,
        )

        self.update_collection_count(
            self.current_cards
        )

    def change_card_quantity(
            self,
            card_id,
            amount,
    ):
        try:

            card_id = int(
                card_id
            )

            amount = int(
                amount
            )

        except (
                TypeError,
                ValueError,
        ):

            return

        if card_id <= 0:
            return

        # =================================================
        # LOCALIZAR LINHA / CARD
        # =================================================

        row_data = self.card_rows.get(
            card_id
        )

        if not row_data:
            self.load_cards()

            return

        frame = row_data.get(
            "frame"
        )

        is_grid = row_data.get(
            "grid",
            False,
        )

        quantity_label = row_data.get(
            "quantity_label"
        )

        # =================================================
        # QUANTIDADE ATUAL
        # =================================================
        #
        # GRID:
        #     usa o QLabel interno do hover.
        #
        # LISTA:
        #     usa o QLabel da linha.
        #
        # =================================================

        if is_grid:

            if (
                    frame is None
                    or not hasattr(
                frame,
                "control_quantity",
            )
            ):
                return

            quantity_widget = (
                frame.control_quantity
            )

        else:

            quantity_widget = (
                quantity_label
            )

        if quantity_widget is None:
            return

        try:

            current_quantity = int(
                quantity_widget.text()
            )

        except (
                TypeError,
                ValueError,
        ):

            current_quantity = 0

        # =================================================
        # CONFIRMAR REMOÇÃO DA ÚLTIMA CARTA
        # =================================================

        if (
                amount < 0
                and current_quantity == 1
        ):

            card_name = "esta carta"

            for card in self.current_cards:

                try:

                    current_id = int(
                        card[0]
                    )

                except (
                        TypeError,
                        ValueError,
                        IndexError,
                ):

                    continue

                if current_id != card_id:
                    continue

                if (
                        len(card) > 1
                        and card[1]
                ):
                    card_name = str(
                        card[1]
                    )

                break

            reply = QMessageBox.question(
                self,
                "Remover carta",
                (
                    f"Você está prestes a remover "
                    f"a última cópia de:\n\n"
                    f"{card_name}\n\n"
                    f"Essa carta será removida "
                    f"da sua coleção. "
                    f"Deseja continuar?"
                ),
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )

            if (
                    reply
                    != QMessageBox.StandardButton.Yes
            ):
                return

        # =================================================
        # ALTERAR NO BANCO
        # =================================================

        new_quantity = max(
            0,
            current_quantity + amount,
        )

        success = set_card_quantity(
            card_id,
            new_quantity,
        )

        if not success:
            return

        # =================================================
        # CARTA REMOVIDA
        # =================================================

        if new_quantity <= 0:

            self.card_rows.pop(
                card_id,
                None,
            )

            self.current_cards = [
                card
                for card in self.current_cards
                if str(card[0])
                   != str(card_id)
            ]

            self.all_collection_cards = [
                card
                for card in self.all_collection_cards
                if str(card[0])
                   != str(card_id)
            ]

            self.search_result_cards = [
                card
                for card in self.search_result_cards
                if str(card[0])
                   != str(card_id)
            ]

            if frame:
                frame.deleteLater()

            # Reorganizar a visualização
            if self.current_layout == "grid":

                self.display_cards(
                    self.current_cards
                )

            else:

                self.display_cards_list(
                    self.current_cards
                )

            self.update_collection_count(
                self.current_cards
            )

            return

        # =================================================
        # ATUALIZAR WIDGET
        # =================================================

        if is_grid:

            # GridCardFrame possui set_quantity().
            if (
                    frame is not None
                    and hasattr(
                frame,
                "set_quantity",
            )
            ):
                frame.set_quantity(
                    new_quantity
                )

        else:

            # CardFrame da lista usa QLabel diretamente.
            if quantity_label is not None:
                quantity_label.setText(
                    str(new_quantity)
                )

        # =================================================
        # ATUALIZAR current_cards
        # =================================================

        updated_cards = []

        for card in self.current_cards:

            try:

                current_id = int(
                    card[0]
                )

            except (
                    TypeError,
                    ValueError,
                    IndexError,
            ):

                updated_cards.append(
                    card
                )

                continue

            if current_id != card_id:
                updated_cards.append(
                    card
                )

                continue

            # -------------------------------------------------
            # PRESERVAR TODOS OS DADOS DA CARTA
            # -------------------------------------------------

            card = list(
                card
            )

            # Índice 10 = quantity
            while len(card) <= 10:
                card.append(
                    None
                )

            card[10] = (
                new_quantity
            )

            updated_cards.append(
                tuple(card)
            )

        self.current_cards = (
            updated_cards
        )

        # =================================================
        # ATUALIZAR OUTRAS FONTES
        # =================================================

        self.update_quantity_in_filter_sources(
            card_id,
            new_quantity,
        )

        self.update_collection_count(
            self.current_cards
        )

    # =====================================================
    # EXPORTAÇÃO
    # =====================================================

    def export_collection(
        self,
    ):

        menu = QMenu(
            self
        )

        menu.setObjectName(
            "ExportMenu"
        )

        backup_action = menu.addAction(
            "💾  Backup completo (JSON)"
        )

        backup_action.triggered.connect(
            self.export_backup_json
        )

        menu.addSeparator()

        treated_json_action = menu.addAction(
            "📋  Tratado (JSON)"
        )

        treated_json_action.triggered.connect(
            self.export_treated_json
        )

        treated_txt_action = menu.addAction(
            "📄  Tratado (TXT)"
        )

        treated_txt_action.triggered.connect(
            self.export_treated_txt
        )

        menu.addSeparator()

        csv_action = menu.addAction(
            "📊  Planilha (CSV)"
        )

        csv_action.triggered.connect(
            self.export_csv
        )

        menu.addSeparator()

        custom_action = menu.addAction(
            "⚙️  Exportação personalizada..."
        )

        custom_action.triggered.connect(
            self.export_custom
        )

        menu.exec(
            self.export_button.mapToGlobal(
                self.export_button.rect().bottomLeft()
            )
        )

    def export_custom(
        self,
    ):
        cards = get_collection_for_export()

        if not cards:
            QMessageBox.information(
                self,
                "Coleção vazia",
                "Não há cartas na coleção para exportar.",
            )
            return

        dialog = CollectionExportDialog(
            cards,
            self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        dialog.export_cards()

    def export_backup_json(
        self,
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar backup da coleção",
            "magic_collection_backup.json",
            "JSON (*.json)",
        )

        if not filepath:
            return

        try:

            export_collection_json(
                filepath,
                cards,
            )

        except Exception as error:

            print(
                f"Erro ao exportar backup: {error}"
            )

    def export_treated_json(
        self,
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção tratada",
            "minha_colecao.json",
            "JSON (*.json)",
        )

        if not filepath:
            return

        try:

            export_collection_treated_json(
                filepath,
                cards,
            )

        except Exception as error:

            print(
                f"Erro ao exportar JSON: {error}"
            )

    def export_treated_txt(
        self,
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção tratada",
            "minha_colecao.txt",
            "Texto (*.txt)",
        )

        if not filepath:
            return

        try:

            export_collection_txt(
                filepath,
                cards,
            )

        except Exception as error:

            print(
                f"Erro ao exportar TXT: {error}"
            )

    def export_csv(
        self,
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção",
            "minha_colecao.csv",
            "CSV (*.csv)",
        )

        if not filepath:
            return

        try:

            export_collection_csv(
                filepath,
                cards,
            )

        except Exception as error:

            print(
                f"Erro ao exportar CSV: {error}"
            )



from pathlib import Path
import requests

from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QTimer,
    QRunnable,
    QThreadPool,
)

from PySide6.QtGui import QPixmap

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
)

from services.scryfall import (
    autocomplete_card_names,
    get_card_by_name,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from database import (
    add_card,
    get_all_cards,
    search_cards,
    change_quantity,
    get_collection_for_export,
    get_card_image_path,
)

from export import (
    export_collection_csv,
    export_collection_json,
    export_collection_treated_json,
    export_collection_txt,
)

from ui.theme import DARK_THEME


# =========================================================
# CACHE GLOBAL DE IMAGENS
# =========================================================

_IMAGE_PIXMAP_CACHE = {}

# =========================================================
# CACHE LOCAL DE SÍMBOLOS
# =========================================================

_MANA_SYMBOL_WIDGET_DATA_CACHE = {}


# =========================================================
# TAREFA SCRYFALL — AUTOCOMPLETE
# =========================================================

class ScryfallSignals(QObject):
    finished = Signal(str, list)


class ScryfallTask(QRunnable):

    def __init__(self, query):
        super().__init__()

        self.query = query
        self.signals = ScryfallSignals()

    def run(self):
        try:
            suggestions = autocomplete_card_names(
                self.query
            )

            suggestions = suggestions[:8]

        except Exception as error:
            print(
                "[SCRYFALL] Erro no autocomplete:",
                error,
            )

            suggestions = []

        self.signals.finished.emit(
            self.query,
            suggestions,
        )


# =========================================================
# TAREFA SCRYFALL — CARTA COMPLETA
# =========================================================

class ScryfallCardSignals(QObject):
    finished = Signal(str, object)
    failed = Signal(str, str)


class ScryfallCardTask(QRunnable):

    def __init__(self, name):
        super().__init__()

        self.name = name
        self.signals = ScryfallCardSignals()

    def run(self):
        try:
            card_data = get_card_by_name(
                self.name
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


# =========================================================
# TAREFA DE IMAGEM
# =========================================================

class ImageSignals(QObject):
    finished = Signal(str, str, bytes)
    failed = Signal(str, str)


class ImageTask(QRunnable):

    def __init__(self, url, local_path):
        super().__init__()

        self.url = url
        self.local_path = str(local_path)

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
            )


# =========================================================
# CARD FRAME
# =========================================================

class CardFrame(QFrame):

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

class GridCardFrame(QFrame):

    doubleClicked = Signal()

    def __init__(self, parent=None):

        super().__init__(parent)

        self.setObjectName(
            "GridCardFrame"
        )

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
            "🃏"
        )

        self.image_label.doubleClicked.connect(
            self.doubleClicked.emit
        )

        # =================================================
        # BADGE DE QUANTIDADE
        # =================================================
        #
        # Fica permanentemente no canto superior direito.
        #
        # Exemplo:
        #
        #             ┌───────┐
        #             │  × 4  │
        #             └───────┘
        #
        # =================================================

        self.quantity_badge = QFrame(
            self
        )

        self.quantity_badge.setObjectName(
            "GridQuantityBadge"
        )

        self.quantity_badge.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        badge_layout = QHBoxLayout(
            self.quantity_badge
        )

        badge_layout.setContentsMargins(
            8,
            4,
            8,
            4,
        )

        badge_layout.setSpacing(
            2
        )

        self.quantity_label = QLabel(
            "0",
            self.quantity_badge
        )

        self.quantity_label.setObjectName(
            "GridQuantityLabel"
        )

        self.quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.quantity_label.setMinimumWidth(
            20
        )

        badge_layout.addWidget(
            self.quantity_label
        )

        # Badge visível por padrão
        self.quantity_badge.show()

        # =================================================
        # CONTROLES DE QUANTIDADE
        # =================================================
        #
        # Eles continuam existindo para permitir alterar
        # a quantidade ao passar o mouse.
        #
        # =================================================

        self.quantity_overlay = QFrame(
            self
        )

        self.quantity_overlay.setObjectName(
            "GridQuantityOverlay"
        )

        self.quantity_overlay.setFixedHeight(
            48
        )

        overlay_layout = QHBoxLayout(
            self.quantity_overlay
        )

        overlay_layout.setContentsMargins(
            8,
            7,
            8,
            7,
        )

        overlay_layout.setSpacing(
            6
        )

        self.minus_button = QPushButton(
            "−",
            self.quantity_overlay,
        )

        self.minus_button.setObjectName(
            "GridQuantityButton"
        )

        self.minus_button.setFixedSize(
            34,
            34,
        )

        overlay_layout.addWidget(
            self.minus_button
        )

        self.overlay_quantity_label = QLabel(
            "0",
            self.quantity_overlay,
        )

        self.overlay_quantity_label.setObjectName(
            "GridQuantityLabel"
        )

        self.overlay_quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.overlay_quantity_label.setFixedWidth(
            42
        )

        overlay_layout.addWidget(
            self.overlay_quantity_label
        )

        self.plus_button = QPushButton(
            "+",
            self.quantity_overlay,
        )

        self.plus_button.setObjectName(
            "GridQuantityButton"
        )

        self.plus_button.setFixedSize(
            34,
            34,
        )

        overlay_layout.addWidget(
            self.plus_button
        )

        # Inicialmente escondido.
        self.quantity_overlay.hide()

    # =====================================================
    # TAMANHO
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

        self.setFixedSize(
            width,
            height,
        )

        self.image_label.setGeometry(
            0,
            0,
            width,
            height,
        )

        # -------------------------------------------------
        # CONTROLES INFERIORES
        # -------------------------------------------------

        overlay_height = 48

        self.quantity_overlay.setGeometry(
            0,
            height - overlay_height,
            width,
            overlay_height,
        )

        self.quantity_overlay.raise_()

        # -------------------------------------------------
        # BADGE SUPERIOR DIREITO
        # -------------------------------------------------

        self.quantity_badge.adjustSize()

        badge_width = self.quantity_badge.width()
        badge_height = self.quantity_badge.height()

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

        self.quantity_badge.raise_()

    # =====================================================
    # RESIZE
    # =====================================================

    def resizeEvent(
        self,
        event,
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

        overlay_height = 48

        self.quantity_overlay.setGeometry(
            0,
            height - overlay_height,
            width,
            overlay_height,
        )

        # -------------------------------------------------
        # BADGE
        # -------------------------------------------------

        self.quantity_badge.adjustSize()

        badge_width = self.quantity_badge.width()
        badge_height = self.quantity_badge.height()

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

        self.quantity_overlay.raise_()
        self.quantity_badge.raise_()

        super().resizeEvent(
            event
        )

    # =====================================================
    # ATUALIZAR QUANTIDADE
    # =====================================================

    def set_quantity(
            self,
            quantity,
    ):
        text = str(
            quantity
        )

        # Badge permanente
        self.quantity_label.setText(
            text
        )

        # Controle inferior / hover
        self.overlay_quantity_label.setText(
            text
        )

        # O tamanho do badge pode mudar
        self.quantity_badge.adjustSize()

        # Reposiciona o badge
        width = self.width()
        height = self.height()

        badge_width = self.quantity_badge.width()
        badge_height = self.quantity_badge.height()

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

        self.quantity_badge.raise_()

    # =====================================================
    # HOVER
    # =====================================================

    def enterEvent(
        self,
        event,
    ):

        self.quantity_overlay.show()

        self.quantity_overlay.raise_()

        # Badge continua no topo
        self.quantity_badge.raise_()

        super().enterEvent(
            event
        )

    # =====================================================

    def leaveEvent(
        self,
        event,
    ):

        self.quantity_overlay.hide()

        # Badge continua visível
        self.quantity_badge.show()

        self.quantity_badge.raise_()

        super().leaveEvent(
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

        self.current_layout = "list"

        self.current_cards = []

        self.card_rows = {}

        self.rebuilding_grid = False

        self._grid_columns = None

        # =================================================
        # THREAD POOLS
        # =================================================

        self.scryfall_pool = QThreadPool(
            self
        )

        self.scryfall_pool.setMaxThreadCount(
            2
        )

        self.card_search_pool = QThreadPool(
            self
        )

        self.card_search_pool.setMaxThreadCount(
            2
        )

        self.image_pool = QThreadPool(
            self
        )

        self.image_pool.setMaxThreadCount(
            4
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

        self.suggestion_list.setFixedHeight(
            220
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

    # =====================================================
    # AUTOCOMPLETE
    # =====================================================

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

    def perform_scryfall_search(self):

        query = self.pending_search

        if not query:
            return

        task = ScryfallTask(
            query
        )

        task.signals.finished.connect(
            self.receive_scryfall_results
        )

        self.scryfall_pool.start(
            task
        )

    def receive_scryfall_results(
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

        self.search_status.clear()

        self.suggestion_list.clear()

        if not suggestions:

            self.suggestion_list.hide()

            return

        for name in suggestions[:8]:
            self.suggestion_list.addItem(
                name
            )

        if self.suggestion_list.count() > 0:
            self.suggestion_list.setCurrentRow(
                0
            )

        self.suggestion_list.show()

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

            card_data = get_card_by_name(
                name
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro:",
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

        self.add_input.clear()

        self.suggestion_list.clear()

        self.suggestion_list.hide()

        self.search_status.clear()

        self.add_button.setEnabled(
            True
        )

        self.add_input.setFocus()

        self.load_cards()

    # =====================================================
    # CARREGAR CARTAS
    # =====================================================

    def load_cards(self):

        try:

            cards = get_all_cards()

        except Exception as error:

            print(
                "[DATABASE] Erro ao carregar coleção:",
                error,
            )

            cards = []

        self.display_cards(
            cards
        )

    # =====================================================
    # PESQUISA DA COLEÇÃO
    # =====================================================

    def search_collection(
        self,
        text,
    ):

        text = text.strip()

        try:

            if not text:

                cards = get_all_cards()

            else:

                cards = search_cards(
                    text
                )

        except Exception as error:

            print(
                "[DATABASE] Erro na pesquisa:",
                error,
            )

            cards = []

        self.display_cards(
            cards
        )

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

        self.current_cards = list(
            cards
        )

        self.card_rows.clear()

        self.rebuilding_grid = True

        self.setUpdatesEnabled(
            False
        )

        try:

            self.clear_cards_layout()

            if self.current_layout == "grid":

                self.display_cards_grid(
                    self.current_cards
                )

            else:

                self.display_cards_list(
                    self.current_cards
                )

        finally:

            self.rebuilding_grid = False

            self.setUpdatesEnabled(
                True
            )

    # =====================================================
    # DISPLAY — LISTA
    # =====================================================

    def display_cards_list(
        self,
        cards,
    ):

        for card in cards:

            (
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
            ) = card

            self.create_card_widget(
                card_id,
                name,
                printed_name,
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

        mana_cost = str(
            mana_cost
        )

        cache_key = (
            mana_cost,
            int(symbol_size),
        )

        self.mana_widget_cache.setdefault(
            cache_key,
            True,
        )

        widget = ManaSymbolsWidget(
            mana_cost,
            symbol_size=symbol_size,
            parent=parent,
        )

        widget.setObjectName(
            "CardMana"
        )

        widget.setSizePolicy(
            QSizePolicy.Policy.Minimum,
            QSizePolicy.Policy.Fixed,
        )

        widget.setFixedHeight(
            symbol_size + 4
        )

        return widget

    # =====================================================
    # DISPLAY — GRADE
    # =====================================================

    def display_cards_grid(
        self,
        cards,
    ):

        grid_layout = QGridLayout()

        grid_layout.setContentsMargins(
            0,
            5,
            0,
            5,
        )

        grid_layout.setHorizontalSpacing(
            14
        )

        grid_layout.setVerticalSpacing(
            14
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

            (
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
            ) = card

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

            self.card_rows[card_id] = {
                "frame": frame,
                "quantity_label": (
                    frame.quantity_label
                ),
                "grid": True,
            }

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
            # IMAGEM
            # -------------------------------------------------

            local_path = None

            if image_path:

                local_path = Path(
                    image_path
                )

            if (
                local_path
                and local_path.exists()
                and local_path.stat().st_size > 0
            ):

                self.load_grid_thumbnail(
                    frame.image_label,
                    local_path,
                )

                continue

            if image_url:

                if image_path:

                    local_path = Path(
                        image_path
                    )

                else:

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

                cached = self.image_cache.get(
                    image_url
                )

                if (
                    cached
                    and not cached.isNull()
                ):

                    self.set_grid_thumbnail(
                        frame.image_label,
                        cached,
                    )

                    continue

                if local_path:

                    task = ImageTask(
                        image_url,
                        local_path,
                    )

                    task.signals.finished.connect(
                        lambda url,
                               path,
                               data,
                               label=frame.image_label:
                        self.receive_image(
                            url,
                            path,
                            data,
                            label,
                        )
                    )

                    task.signals.failed.connect(
                        lambda url,
                               error,
                               label=frame.image_label:
                        self.receive_image_error(
                            url,
                            error,
                            label,
                        )
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
            "🃏"
        )

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

        quantity_label = QLabel(
            str(quantity)
        )

        quantity_label.setObjectName(
            "Quantity"
        )

        quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
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

        self.cards_layout.addWidget(
            frame
        )

        # =================================================
        # IMAGEM LOCAL
        # =================================================

        local_path = None

        if image_path:

            local_path = Path(
                image_path
            )

        if (
            local_path
            and local_path.exists()
            and local_path.stat().st_size > 0
        ):

            self.load_local_thumbnail(
                image_label,
                local_path,
            )

            return

        # =================================================
        # CACHE EM MEMÓRIA
        # =================================================

        if image_url:

            cached = self.image_cache.get(
                image_url
            )

            if (
                cached
                and not cached.isNull()
            ):

                self.set_thumbnail(
                    image_label,
                    cached,
                )

                return

        # =================================================
        # DOWNLOAD
        # =================================================

        if image_url:

            if image_path:

                local_path = Path(
                    image_path
                )

            else:

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
                    local_path
                )

                task.signals.finished.connect(
                    lambda url,
                           path,
                           data,
                           label=image_label:
                    self.receive_image(
                        url,
                        path,
                        data,
                        label,
                    )
                )

                task.signals.failed.connect(
                    lambda url,
                           error,
                           label=image_label:
                    self.receive_image_error(
                        url,
                        error,
                        label,
                    )
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

            self.set_thumbnail(
                label,
                pixmap,
            )

        except Exception as error:

            print(
                "[IMAGE] Erro:",
                error,
            )

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

    def receive_image(
        self,
        url,
        path,
        data,
        label,
    ):

        pixmap = QPixmap()

        if not pixmap.loadFromData(
            data
        ):

            return

        self.image_cache[
            url
        ] = pixmap

        if path:

            self.image_cache[
                str(path)
            ] = pixmap

        if (
            label
            and label.objectName()
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

    def set_thumbnail(
        self,
        label,
        pixmap,
    ):

        if (
            not pixmap
            or pixmap.isNull()
        ):

            label.setText(
                "🃏"
            )

            return

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
                "🃏"
            )

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

                                if image_url:

                                    self.image_cache[
                                        image_url
                                    ] = pixmap

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

    # =====================================================
    # QUANTIDADE
    # =====================================================

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
            # Caso o widget não exista mais,
            # recarrega tudo diretamente do banco.
            self.load_cards()

            return

        quantity_label = row_data.get(
            "quantity_label"
        )

        frame = row_data.get(
            "frame"
        )

        is_grid = row_data.get(
            "grid",
            False,
        )

        # =================================================
        # QUANTIDADE ATUAL
        # =================================================

        try:

            current_quantity = int(
                quantity_label.text()
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

            # Tenta encontrar o nome da carta
            # dentro de current_cards.
            for card in self.current_cards:

                try:

                    current_id = int(
                        card[0]
                    )

                except (
                        TypeError,
                        ValueError,
                ):

                    continue

                if current_id == card_id:

                    if len(card) > 1 and card[1]:
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
                    f"Essa carta será removida da sua coleção. "
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

        success = change_quantity(
            card_id,
            amount,
        )

        if not success:
            return

        # =================================================
        # NOVA QUANTIDADE
        # =================================================

        new_quantity = (
                current_quantity
                + amount
        )

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

            if frame:
                frame.deleteLater()

            return

        # =================================================
        # ATUALIZAR QUANTIDADE
        # =================================================

        if is_grid:

            # GridCardFrame possui set_quantity()
            if hasattr(
                    frame,
                    "set_quantity",
            ):

                frame.set_quantity(
                    new_quantity
                )

            else:

                quantity_label.setText(
                    str(new_quantity)
                )

        else:

            # CardFrame da lista não possui set_quantity().
            # Atualizamos diretamente o QLabel.
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

            # Tupla da coleção:
            #
            # 0  = id
            # ...
            # 10 = quantity
            #
            # Mantemos todos os outros dados
            # e alteramos somente quantity.

            card = list(
                card
            )

            if len(card) > 10:
                card[10] = new_quantity

            updated_cards.append(
                tuple(card)
            )

        self.current_cards = updated_cards

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

        menu.exec(
            self.export_button.mapToGlobal(
                self.export_button.rect().bottomLeft()
            )
        )

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


# =========================================================
# DETALHES
# =========================================================

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

        self.setWindowTitle(
            card.get(
                "name",
                "Carta",
            )
        )

        self.setMinimumSize(
            760,
            620,
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
            24
        )

        # =================================================
        # IMAGEM
        # =================================================

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

        if (
            pixmap
            and not pixmap.isNull()
        ):

            self.set_image(
                pixmap
            )

        else:

            self.image_label.setText(
                "Imagem indisponível"
            )

        layout.addWidget(
            self.image_label
        )

        # =================================================
        # INFORMAÇÕES
        # =================================================

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

        # =================================================
        # NOME
        # =================================================

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

        # =================================================
        # MANA
        # =================================================

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

        # =================================================
        # POWER / TOUGHNESS
        # =================================================

        power = card.get(
            "power"
        )

        toughness = card.get(
            "toughness"
        )

        has_pt = (
            power is not None
            and toughness is not None
            and str(power).strip() != ""
            and str(toughness).strip() != ""
        )

        if has_pt:

            pt_label = QLabel(
                f"{power} / {toughness}"
            )

            pt_label.setObjectName(
                "CardDetailPT"
            )

            pt_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            pt_label.setMinimumHeight(
                36
            )

            info_layout.addWidget(
                pt_label
            )

        # =================================================
        # TIPO
        # =================================================

        type_label = QLabel(
            card.get(
                "type_line"
            ) or "—"
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

        # =================================================
        # EDIÇÃO
        # =================================================

        set_label = QLabel(
            (
                f"Edição: "
                f"{card.get('set_name') or '—'}\n"
                f"Número: "
                f"{card.get('collector_number') or '—'}"
            )
        )

        set_label.setObjectName(
            "CardDetailSet"
        )

        info_layout.addWidget(
            set_label
        )

        # =================================================
        # QUANTIDADE
        # =================================================

        quantity = card.get(
            "quantity",
            0,
        )

        quantity_label = QLabel(
            f"Quantidade na coleção: "
            f"{quantity}"
        )

        quantity_label.setObjectName(
            "CardDetailQuantity"
        )

        info_layout.addWidget(
            quantity_label
        )

        # =================================================
        # TEXTO DA CARTA
        # =================================================

        oracle_text = card.get(
            "oracle_text"
        ) or "Sem texto de regras."

        text_label = QLabel(
            oracle_text
        )

        text_label.setObjectName(
            "CardDetailText"
        )

        text_label.setWordWrap(
            True
        )

        text_label.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        text_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        info_layout.addWidget(
            text_label
        )

        # =================================================
        # FECHAR
        # =================================================

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )

        button_box.rejected.connect(
            self.reject
        )

        button_box.accepted.connect(
            self.accept
        )

        info_layout.addWidget(
            button_box
        )

        layout.addWidget(
            info_widget
        )

    # =====================================================
    # IMAGEM
    # =====================================================

    def set_image(
        self,
        pixmap,
    ):

        if (
            not pixmap
            or pixmap.isNull()
        ):

            self.image_label.setText(
                "Imagem indisponível"
            )

            return

        scaled = pixmap.scaled(
            320,
            450,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setText(
            ""
        )

        self.image_label.setPixmap(
            scaled
        )
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

from PySide6.QtGui import (
    QPixmap,
)

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
# TAREFA SCRYFALL — AUTOCOMPLETE
# =========================================================

class ScryfallSignals(QObject):

    finished = Signal(
        str,
        list
    )


class ScryfallTask(QRunnable):

    def __init__(
        self,
        query
    ):

        super().__init__()

        self.query = query

        self.signals = ScryfallSignals()

    def run(
        self
    ):

        try:

            suggestions = (
                autocomplete_card_names(
                    self.query
                )
            )

            suggestions = suggestions[:8]

        except Exception as error:

            print(
                "[SCRYFALL] Erro no autocomplete:",
                error
            )

            suggestions = []

        self.signals.finished.emit(
            self.query,
            suggestions
        )


# =========================================================
# TAREFA SCRYFALL — BUSCAR CARTA COMPLETA
# =========================================================

class ScryfallCardSignals(QObject):

    finished = Signal(
        str,
        object
    )

    failed = Signal(
        str,
        str
    )


class ScryfallCardTask(QRunnable):

    def __init__(
        self,
        name
    ):

        super().__init__()

        self.name = name

        self.signals = ScryfallCardSignals()

    def run(
        self
    ):

        try:

            card_data = get_card_by_name(
                self.name
            )

            self.signals.finished.emit(
                self.name,
                card_data
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro ao buscar carta:",
                error
            )

            self.signals.failed.emit(
                self.name,
                str(error)
            )


# =========================================================
# TAREFA DE IMAGEM
# =========================================================

class ImageSignals(QObject):

    finished = Signal(
        str,
        str,
        bytes
    )

    failed = Signal(
        str,
        str
    )


class ImageTask(QRunnable):

    def __init__(
        self,
        url,
        local_path
    ):

        super().__init__()

        self.url = url

        self.local_path = str(
            local_path
        )

        self.signals = ImageSignals()

    def run(
        self
    ):

        if not self.url:
            return

        try:

            path = Path(
                self.local_path
            )

            # =================================================
            # IMAGEM JÁ EXISTE LOCALMENTE
            # =================================================

            if (
                path.exists()
                and path.stat().st_size > 0
            ):

                data = path.read_bytes()

                self.signals.finished.emit(
                    self.url,
                    str(path),
                    data
                )

                return

            # =================================================
            # DOWNLOAD
            # =================================================

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
                timeout=20
            )

            response.raise_for_status()

            data = response.content

            if not data:

                raise RuntimeError(
                    "Scryfall retornou uma imagem vazia."
                )

            # =================================================
            # SALVAR
            # =================================================

            path.parent.mkdir(
                parents=True,
                exist_ok=True
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

            # =================================================
            # AVISAR A UI
            # =================================================

            self.signals.finished.emit(
                self.url,
                str(path),
                data
            )

        except Exception as error:

            print(
                "[IMAGE] Erro ao carregar:",
                self.url,
                "|",
                error
            )

            self.signals.failed.emit(
                self.url,
                str(error)
            )


# =========================================================
# CARD FRAME
# =========================================================

class CardFrame(QFrame):

    doubleClicked = Signal()

    def mouseDoubleClickEvent(
        self,
        event
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
# IMAGEM CLICÁVEL
# =========================================================

class CardImageLabel(QLabel):

    doubleClicked = Signal()

    def mouseDoubleClickEvent(
        self,
        event
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
# CARTA DA GRADE
# =========================================================

class GridCardFrame(QFrame):

    doubleClicked = Signal()

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.setObjectName(
            "GridCardFrame"
        )

        self.setMouseTracking(
            True
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True
        )

        # =================================================
        # TAMANHO INICIAL
        # =================================================

        self.setMinimumSize(
            120,
            168
        )

        self.setMaximumWidth(
            500
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        # =================================================
        # IMAGEM
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

        self.image_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            False
        )

        self.image_label.doubleClicked.connect(
            self.doubleClicked.emit
        )

        # =================================================
        # OVERLAY DE QUANTIDADE
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
            7
        )

        overlay_layout.setSpacing(
            6
        )

        # =================================================
        # MENOS
        # =================================================

        self.minus_button = QPushButton(
            "−",
            self.quantity_overlay
        )

        self.minus_button.setObjectName(
            "GridQuantityButton"
        )

        self.minus_button.setFixedSize(
            34,
            34
        )

        overlay_layout.addWidget(
            self.minus_button
        )

        # =================================================
        # QUANTIDADE
        # =================================================

        self.quantity_label = QLabel(
            "0",
            self.quantity_overlay
        )

        self.quantity_label.setObjectName(
            "GridQuantityLabel"
        )

        self.quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.quantity_label.setFixedWidth(
            42
        )

        overlay_layout.addWidget(
            self.quantity_label
        )

        # =================================================
        # MAIS
        # =================================================

        self.plus_button = QPushButton(
            "+",
            self.quantity_overlay
        )

        self.plus_button.setObjectName(
            "GridQuantityButton"
        )

        self.plus_button.setFixedSize(
            34,
            34
        )

        overlay_layout.addWidget(
            self.plus_button
        )

        self.quantity_overlay.hide()

    # =====================================================
    # DEFINIR TAMANHO DA CARTA
    # =====================================================

    def set_card_width(
        self,
        width
    ):

        width = max(
            120,
            int(width)
        )

        # MTG aproximadamente 63:88
        height = round(
            width * 88 / 63
        )

        self.setFixedSize(
            width,
            height
        )

        self.image_label.setGeometry(
            0,
            0,
            width,
            height
        )

        overlay_height = 48

        self.quantity_overlay.setGeometry(
            0,
            height - overlay_height,
            width,
            overlay_height
        )

        self.quantity_overlay.raise_()

    # =====================================================
    # RESIZE
    # =====================================================

    def resizeEvent(
        self,
        event
    ):

        width = self.width()
        height = self.height()

        self.image_label.setGeometry(
            0,
            0,
            width,
            height
        )

        overlay_height = 48

        self.quantity_overlay.setGeometry(
            0,
            height - overlay_height,
            width,
            overlay_height
        )

        self.quantity_overlay.raise_()

        super().resizeEvent(
            event
        )

    # =====================================================
    # HOVER
    # =====================================================

    def enterEvent(
        self,
        event
    ):

        self.quantity_overlay.show()

        self.quantity_overlay.raise_()

        super().enterEvent(
            event
        )

    def leaveEvent(
        self,
        event
    ):

        self.quantity_overlay.hide()

        super().leaveEvent(
            event
        )


# =========================================================
# CONTAINER DA GRADE
# =========================================================

class CardsContainer(QWidget):

    resized = Signal()

    def resizeEvent(
        self,
        event
    ):

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

class CollectionPage(QWidget):

    def __init__(
        self,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.setStyleSheet(
            DARK_THEME
        )

        # =================================================
        # AUTOCOMPLETE
        # =================================================

        self.pending_search = ""

        self.scryfall_pool = (
            QThreadPool()
        )

        self.search_timer = (
            QTimer()
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

        # =================================================
        # BUSCA DE CARTA COMPLETA
        # =================================================

        self.card_search_pool = (
            QThreadPool()
        )

        # =================================================
        # IMAGENS
        # =================================================

        self.image_pool = (
            QThreadPool()
        )

        self.image_cache = {}

        # =================================================
        # REFERÊNCIAS DAS LINHAS
        # =================================================

        self.card_rows = {}

        # =================================================
        # LAYOUT ATUAL
        # =================================================

        self.current_layout = "list"

        self.current_cards = []

        self.rebuilding_grid = False

        self._grid_columns = None

        # Evita reconstruções excessivas durante resize
        self._grid_resize_timer = QTimer()
        self._grid_resize_timer.setSingleShot(
            True
        )
        self._grid_resize_timer.setInterval(
            80
        )
        self._grid_resize_timer.timeout.connect(
            self.rebuild_grid_after_resize
        )

        # =================================================
        # UI
        # =================================================

        self.setup_ui()

        self.load_cards()

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(
        self
    ):

        self.main_layout = QVBoxLayout(
            self
        )

        self.main_layout.setContentsMargins(
            32,
            28,
            32,
            28
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
        # AÇÕES DO TOPO
        # =================================================

        actions_layout = QHBoxLayout()

        actions_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        actions_layout.setSpacing(
            8
        )

        # =================================================
        # EXPORTAR
        # =================================================

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

        # =================================================
        # LAYOUTS
        # =================================================

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
            0
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

        add_area_layout = QVBoxLayout(
            self.add_area
        )

        add_area_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        add_area_layout.setSpacing(
            0
        )

        add_frame = QFrame()

        add_frame.setObjectName(
            "AddFrame"
        )

        add_layout = QHBoxLayout(
            add_frame
        )

        add_layout.setContentsMargins(
            12,
            0,
            12,
            0
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

        self.add_input = QLineEdit()

        self.add_input.setPlaceholderText(
            "Adicionar carta à coleção..."
        )

        self.add_input.setFrame(
            False
        )

        self.add_input.textChanged.connect(
            self.search_scryfall
        )

        self.add_input.returnPressed.connect(
            self.handle_add_enter
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

        self.suggestion_list.setMaximumHeight(
            220
        )

        self.suggestion_list.itemClicked.connect(
            self.select_suggestion
        )

        self.suggestion_list.hide()

        add_area_layout.addWidget(
            self.suggestion_list
        )

        self.main_layout.addWidget(
            self.add_area
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
            5
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

    # =====================================================
    # MENU DE LAYOUT
    # =====================================================

    def show_layout_menu(
        self
    ):

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

    def set_layout(
        self,
        layout_name
    ):

        if layout_name not in (
            "list",
            "grid"
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
    # RESIZE DO CONTAINER
    # =====================================================

    def handle_container_resize(
        self
    ):

        if self.current_layout != "grid":
            return

        if self.rebuilding_grid:
            return

        if not self.current_cards:
            return

        # O viewport é a largura real disponível.
        viewport_width = (
            self.scroll_area
            .viewport()
            .width()
        )

        if viewport_width <= 0:
            return

        # Largura mínima desejada de uma carta.
        min_card_width = 160

        # Espaçamento entre cartas.
        spacing = 14

        # Calcula quantas cartas cabem.
        columns = max(
            1,
            int(
                (
                    viewport_width + spacing
                )
                /
                (
                    min_card_width + spacing
                )
            )
        )

        # Não reconstrói se a quantidade
        # de colunas continua igual.
        if self._grid_columns == columns:
            return

        self._grid_columns = columns

        # Aguarda um pouco para evitar reconstruções
        # dezenas de vezes durante o resize da janela.
        self._grid_resize_timer.start()

    # =====================================================
    # RECONSTRUIR GRADE
    # =====================================================

    def rebuild_grid_after_resize(
        self
    ):

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
    # EXPORTAÇÃO
    # =====================================================

    def export_collection(
        self
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
        self
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Exportar backup da coleção",
                "magic_collection_backup.json",
                "JSON (*.json)"
            )
        )

        if not filepath:
            return

        try:

            export_collection_json(
                filepath,
                cards
            )

        except Exception as error:

            print(
                f"Erro ao exportar backup: {error}"
            )

    def export_treated_json(
        self
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Exportar coleção tratada",
                "minha_colecao.json",
                "JSON (*.json)"
            )
        )

        if not filepath:
            return

        try:

            export_collection_treated_json(
                filepath,
                cards
            )

        except Exception as error:

            print(
                f"Erro ao exportar JSON: {error}"
            )

    def export_treated_txt(
        self
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Exportar coleção tratada",
                "minha_colecao.txt",
                "Texto (*.txt)"
            )
        )

        if not filepath:
            return

        try:

            export_collection_txt(
                filepath,
                cards
            )

        except Exception as error:

            print(
                f"Erro ao exportar TXT: {error}"
            )

    def export_csv(
        self
    ):

        cards = get_collection_for_export()

        if not cards:
            return

        filepath, _ = (
            QFileDialog.getSaveFileName(
                self,
                "Exportar coleção",
                "minha_colecao.csv",
                "CSV (*.csv)"
            )
        )

        if not filepath:
            return

        try:

            export_collection_csv(
                filepath,
                cards
            )

        except Exception as error:

            print(
                f"Erro ao exportar CSV: {error}"
            )

    # =====================================================
    # AUTOCOMPLETE
    # =====================================================

    def search_scryfall(
        self,
        text
    ):

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
        self
    ):

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
        suggestions
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

        self.suggestion_list.show()

    # =====================================================
    # SUGESTÃO
    # =====================================================

    def select_suggestion(
        self,
        item
    ):

        name = item.text()

        self.suggestion_list.hide()

        self.add_input.setText(
            name
        )

        self.add_input.setFocus()

        self.add_card_from_input()

    def handle_add_enter(
        self
    ):

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

    def add_card_from_input(
        self
    ):

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
                error
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
                1
            )

        except Exception as error:

            print(
                "[DATABASE] Erro:",
                error
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
    # CARREGAR
    # =====================================================

    def load_cards(
        self
    ):

        cards = get_all_cards()

        self.display_cards(
            cards
        )

    # =====================================================
    # PESQUISA
    # =====================================================

    def search_collection(
        self,
        text
    ):

        if not text.strip():

            cards = get_all_cards()

        else:

            cards = search_cards(
                text
            )

        self.display_cards(
            cards
        )

    # =====================================================
    # LIMPAR LAYOUT
    # =====================================================

    def clear_cards_layout(
        self
    ):

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
        cards
    ):

        if cards is None:
            cards = []

        self.current_cards = list(
            cards
        )

        self.card_rows.clear()

        self.rebuilding_grid = True

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

    # =====================================================
    # DISPLAY — LISTA
    # =====================================================

    def display_cards_list(
        self,
        cards
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
                toughness
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
                toughness
            )

    # =====================================================
    # DISPLAY — GRADE
    # =====================================================

    def display_cards_grid(
        self,
        cards
    ):

        grid_layout = QGridLayout()

        grid_layout.setContentsMargins(
            0,
            5,
            0,
            5
        )

        grid_layout.setHorizontalSpacing(
            14
        )

        grid_layout.setVerticalSpacing(
            14
        )

        # =================================================
        # LARGURA DISPONÍVEL
        # =================================================

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

        # =================================================
        # LARGURA MÍNIMA
        # =================================================

        min_card_width = 160

        # =================================================
        # CALCULAR COLUNAS
        # =================================================

        columns = max(
            1,
            int(
                (
                    available_width + spacing
                )
                /
                (
                    min_card_width + spacing
                )
            )
        )

        # =================================================
        # LARGURA REAL DE CADA CARTA
        # =================================================

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
            card_width
        )

        # Evita ultrapassar demais a largura.
        max_card_width = 500

        card_width = min(
            card_width,
            max_card_width
        )

        # =================================================
        # GUARDAR COLUNAS
        # =================================================

        self._grid_columns = columns

        # =================================================
        # CRIAR CARTAS
        # =================================================

        for index, card in enumerate(
            cards
        ):

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
                toughness
            ) = card

            try:

                card_id = int(
                    card_id
                )

            except (
                TypeError,
                ValueError
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

            # =================================================
            # QUANTIDADE
            # =================================================

            frame.quantity_label.setText(
                str(quantity)
            )

            frame.minus_button.clicked.connect(
                lambda checked=False,
                       cid=card_id:
                self.change_card_quantity(
                    cid,
                    -1
                )
            )

            frame.plus_button.clicked.connect(
                lambda checked=False,
                       cid=card_id:
                self.change_card_quantity(
                    cid,
                    1
                )
            )

            # =================================================
            # REGISTRAR REFERÊNCIA
            # =================================================

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
                | Qt.AlignmentFlag.AlignLeft
            )

            # =================================================
            # IMAGEM
            # =================================================

            local_path = None

            if image_path:

                local_path = Path(
                    image_path
                )

            if local_path:

                if (
                    local_path.exists()
                    and local_path.stat().st_size > 0
                ):

                    self.load_grid_thumbnail(
                        frame.image_label,
                        local_path
                    )

                    continue

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
                               label=frame.image_label:
                        self.receive_image(
                            url,
                            path,
                            data,
                            label
                        )
                    )

                    task.signals.failed.connect(
                        lambda url,
                               error,
                               label=frame.image_label:
                        self.receive_image_error(
                            url,
                            error,
                            label
                        )
                    )

                    self.image_pool.start(
                        task
                    )

        # =================================================
        # ESTICAR COLUNAS
        # =================================================

        for column in range(
            columns
        ):

            grid_layout.setColumnStretch(
                column,
                1
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
        toughness
    ):

        try:

            card_id = int(
                card_id
            )

        except (
            TypeError,
            ValueError
        ):

            return

        if card_id <= 0:
            return

        # =================================================
        # FRAME PRINCIPAL
        # =================================================

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

        # =================================================
        # DADOS DA CARTA
        # =================================================

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

        # =================================================
        # LAYOUT PRINCIPAL
        # =================================================

        layout = QHBoxLayout(
            frame
        )

        layout.setContentsMargins(
            10,
            8,
            12,
            8
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
            78
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
            Qt.AlignmentFlag.AlignVCenter
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
            QSizePolicy.Policy.Fixed
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
            1
        )

        info_layout.setSpacing(
            3
        )

        # =================================================
        # NOME
        # =================================================

        name_label = QLabel(
            name
        )

        name_label.setObjectName(
            "CardName"
        )

        name_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )

        name_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        info_layout.addWidget(
            name_label
        )

        # =================================================
        # MANA + POWER / TOUGHNESS
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
                QSizePolicy.Policy.Fixed
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
                0
            )

            meta_layout.setSpacing(
                9
            )

            # =================================================
            # MANA
            # =================================================

            if has_mana:

                mana_widget = ManaSymbolsWidget(
                    mana_cost,
                    symbol_size=20
                )

                mana_widget.setObjectName(
                    "CardMana"
                )

                mana_widget.setSizePolicy(
                    QSizePolicy.Policy.Preferred,
                    QSizePolicy.Policy.Fixed
                )

                mana_widget.setFixedHeight(
                    26
                )

                meta_layout.addWidget(
                    mana_widget,
                    0,
                    Qt.AlignmentFlag.AlignVCenter
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
                    24
                )

                separator.setMaximumSize(
                    1,
                    24
                )

                meta_layout.addWidget(
                    separator,
                    0,
                    Qt.AlignmentFlag.AlignVCenter
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
                    32
                )

                pt_label.setSizePolicy(
                    QSizePolicy.Policy.Fixed,
                    QSizePolicy.Policy.Fixed
                )

                meta_layout.addWidget(
                    pt_label,
                    0,
                    Qt.AlignmentFlag.AlignVCenter
                )

            # =================================================
            # CENTRALIZAÇÃO
            # =================================================

            meta_row = QHBoxLayout()

            meta_row.setContentsMargins(
                0,
                0,
                0,
                0
            )

            meta_row.addStretch()

            meta_row.addWidget(
                meta_widget,
                0,
                Qt.AlignmentFlag.AlignVCenter
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
            QSizePolicy.Policy.Fixed
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
            QSizePolicy.Policy.Fixed
        )

        set_label.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        info_layout.addWidget(
            set_label
        )

        # =================================================
        # ADICIONAR INFORMAÇÕES
        # =================================================

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
            Qt.AlignmentFlag.AlignVCenter
        )

        # =================================================
        # ÁREA DE QUANTIDADE
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
            0
        )

        quantity_layout.setSpacing(
            4
        )

        # =================================================
        # MENOS
        # =================================================

        minus_button = QPushButton(
            "−"
        )

        minus_button.setObjectName(
            "QuantityButton"
        )

        minus_button.setFixedSize(
            30,
            30
        )

        minus_button.clicked.connect(
            lambda checked=False,
                   cid=card_id:
            self.change_card_quantity(
                cid,
                -1
            )
        )

        quantity_layout.addWidget(
            minus_button,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        # =================================================
        # QUANTIDADE
        # =================================================

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
            30
        )

        quantity_layout.addWidget(
            quantity_label,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        # =================================================
        # MAIS
        # =================================================

        plus_button = QPushButton(
            "+"
        )

        plus_button.setObjectName(
            "QuantityButton"
        )

        plus_button.setFixedSize(
            30,
            30
        )

        plus_button.clicked.connect(
            lambda checked=False,
                   cid=card_id:
            self.change_card_quantity(
                cid,
                1
            )
        )

        quantity_layout.addWidget(
            plus_button,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        layout.addWidget(
            quantity_frame,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        # =================================================
        # REGISTRAR REFERÊNCIA
        # =================================================

        self.card_rows[card_id] = {
            "frame": frame,
            "quantity_label": quantity_label,
            "grid": False,
        }

        # =================================================
        # ADICIONAR À LISTA
        # =================================================

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

        if local_path:

            if (
                local_path.exists()
                and local_path.stat().st_size > 0
            ):

                self.load_local_thumbnail(
                    image_label,
                    local_path
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
                        label
                    )
                )

                task.signals.failed.connect(
                    lambda url,
                           error,
                           label=image_label:
                    self.receive_image_error(
                        url,
                        error,
                        label
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
        url
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
        path
    ):

        try:

            pixmap = QPixmap(
                str(path)
            )

            if pixmap.isNull():
                return

            self.set_thumbnail(
                label,
                pixmap
            )

        except Exception as error:

            print(
                "[IMAGE] Erro:",
                error
            )

    # =====================================================
    # IMAGEM LOCAL — GRADE
    # =====================================================

    def load_grid_thumbnail(
        self,
        label,
        path
    ):

        try:

            pixmap = QPixmap(
                str(path)
            )

            if pixmap.isNull():
                return

            self.set_grid_thumbnail(
                label,
                pixmap
            )

        except Exception as error:

            print(
                "[IMAGE] Erro ao carregar imagem da grade:",
                error
            )

    # =====================================================
    # DOWNLOAD RECEBIDO
    # =====================================================

    def receive_image(
        self,
        url,
        path,
        data,
        label
    ):

        pixmap = QPixmap()

        if not pixmap.loadFromData(
            data
        ):

            return

        self.image_cache[
            url
        ] = pixmap

        if (
            label
            and label.objectName()
            == "GridCardImage"
        ):

            self.set_grid_thumbnail(
                label,
                pixmap
            )

        else:

            self.set_thumbnail(
                label,
                pixmap
            )

    def receive_image_error(
        self,
        url,
        error,
        label
    ):

        print(
            f"[IMAGE] Falha: {url} | {error}"
        )

        label.setText(
            "🃏"
        )

    # =====================================================
    # MINIATURA — LISTA
    # =====================================================

    def set_thumbnail(
        self,
        label,
        pixmap
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
            58,
            78,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
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
        pixmap
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
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
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
        card
    ):

        if not card:
            return

        # =================================================
        # CACHE
        # =================================================

        pixmap = None

        image_url = card.get(
            "image_url"
        )

        if image_url:

            pixmap = self.image_cache.get(
                image_url
            )

        # =================================================
        # CAMINHO LOCAL
        # =================================================

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

                        local_pixmap = QPixmap(
                            str(path)
                        )

                        if (
                            not local_pixmap.isNull()
                        ):

                            pixmap = local_pixmap

                            if image_url:

                                self.image_cache[
                                    image_url
                                ] = local_pixmap

                except Exception as error:

                    print(
                        "[DETAILS] Erro ao carregar imagem:",
                        error
                    )

        # =================================================
        # ABRIR
        # =================================================

        dialog = CardDetailsDialog(
            card,
            pixmap,
            self
        )

        dialog.exec()

    # =====================================================
    # QUANTIDADE
    # =====================================================

    def change_card_quantity(
        self,
        card_id,
        amount
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
            ValueError
        ):

            return

        if card_id <= 0:
            return

        # =================================================
        # ALTERAR BANCO
        # =================================================

        success = change_quantity(
            card_id,
            amount
        )

        if not success:
            return

        # =================================================
        # LOCALIZAR LINHA
        # =================================================

        row_data = self.card_rows.get(
            card_id
        )

        if not row_data:

            self.load_cards()

            return

        quantity_label = row_data[
            "quantity_label"
        ]

        frame = row_data[
            "frame"
        ]

        # =================================================
        # QUANTIDADE ATUAL
        # =================================================

        try:

            current_quantity = int(
                quantity_label.text()
            )

        except (
            TypeError,
            ValueError
        ):

            current_quantity = 0

        new_quantity = (
            current_quantity
            + amount
        )

        # =================================================
        # QUANTIDADE ZERO
        # =================================================

        if new_quantity <= 0:

            self.card_rows.pop(
                card_id,
                None
            )

            self.current_cards = [
                card
                for card in self.current_cards
                if str(card[0]) != str(card_id)
            ]

            if self.current_layout == "grid":

                self.display_cards(
                    self.current_cards
                )

            else:

                frame.deleteLater()

            return

        # =================================================
        # ATUALIZAR VISUAL
        # =================================================

        quantity_label.setText(
            str(new_quantity)
        )


# =========================================================
# DETALHES
# =========================================================

class CardDetailsDialog(QDialog):

    def __init__(
        self,
        card,
        pixmap=None,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.setWindowTitle(
            card.get(
                "name",
                "Carta"
            )
        )

        self.setMinimumSize(
            760,
            620
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
            24
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
            450
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
            0
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
                "—"
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
        # MANA + P/T
        # =================================================

        mana_cost = card.get(
            "mana_cost"
        )

        power = card.get(
            "power"
        )

        toughness = card.get(
            "toughness"
        )

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

            meta_layout = QHBoxLayout(
                meta_widget
            )

            meta_layout.setContentsMargins(
                0,
                0,
                0,
                0
            )

            meta_layout.setSpacing(
                9
            )

            # =================================================
            # MANA
            # =================================================

            if has_mana:

                mana_widget = ManaSymbolsWidget(
                    mana_cost,
                    symbol_size=26
                )

                mana_widget.setObjectName(
                    "CardDetailMana"
                )

                mana_layout = QHBoxLayout()

                mana_layout.setContentsMargins(
                    0,
                    0,
                    0,
                    0
                )

                mana_layout.addWidget(
                    mana_widget
                )

                meta_layout.addLayout(
                    mana_layout
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

                separator.setFixedWidth(
                    1
                )

                separator.setFixedHeight(
                    32
                )

                meta_layout.addWidget(
                    separator,
                    0,
                    Qt.AlignmentFlag.AlignVCenter
                )

            # =================================================
            # POWER / TOUGHNESS
            # =================================================

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

                meta_layout.addWidget(
                    pt_label,
                    0,
                    Qt.AlignmentFlag.AlignVCenter
                )

            info_layout.addWidget(
                meta_widget
            )

        # =================================================
        # TIPO
        # =================================================

        type_line = card.get(
            "type_line"
        ) or "—"

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

        # =================================================
        # EDIÇÃO
        # =================================================

        set_name = card.get(
            "set_name"
        ) or "—"

        collector_number = card.get(
            "collector_number"
        ) or "—"

        set_label = QLabel(
            f"Edição: {set_name}\n"
            f"Número: {collector_number}"
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
            0
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
        # TEXTO
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
            QSizePolicy.Policy.Expanding
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

        # =================================================
        # FINAL
        # =================================================

        layout.addWidget(
            info_widget
        )

    def set_image(
        self,
        pixmap
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
            Qt.TransformationMode.SmoothTransformation
        )

        self.image_label.setText(
            ""
        )

        self.image_label.setPixmap(
            scaled
        )
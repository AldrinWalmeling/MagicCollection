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

            suggestions = autocomplete_card_names(
                self.query
            )

            if not suggestions:
                suggestions = []

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

        self.last_completed_query = ""

        self.scryfall_pool = QThreadPool()

        # Não deixar uma quantidade enorme de requisições
        # serem executadas simultaneamente.
        self.scryfall_pool.setMaxThreadCount(
            2
        )

        self.search_timer = QTimer()

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

        self.card_search_pool = QThreadPool()

        self.card_search_pool.setMaxThreadCount(
            2
        )

        self.card_search_in_progress = False

        self.pending_card_name = ""

        # =================================================
        # IMAGENS
        # =================================================

        self.image_pool = QThreadPool()

        self.image_pool.setMaxThreadCount(
            4
        )

        self.image_cache = {}

        # =================================================
        # REFERÊNCIAS DAS LINHAS
        # =================================================

        self.card_rows = {}

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
        # EXPORTAR
        # =================================================

        export_layout = QHBoxLayout()

        self.export_button = QPushButton(
            "Exportar"
        )

        self.export_button.setObjectName(
            "ExportButton"
        )

        self.export_button.clicked.connect(
            self.export_collection
        )

        export_layout.addWidget(
            self.export_button
        )

        export_layout.addStretch()

        self.main_layout.addLayout(
            export_layout
        )

        # =================================================
        # PESQUISA DA COLEÇÃO
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
        # LISTA
        # =================================================

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setObjectName(
            "CardsScrollArea"
        )

        self.cards_container = QWidget()

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

        self.scroll_area.setWidget(
            self.cards_container
        )

        self.main_layout.addWidget(
            self.scroll_area
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

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar backup da coleção",
            "magic_collection_backup.json",
            "JSON (*.json)"
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

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção tratada",
            "minha_colecao.json",
            "JSON (*.json)"
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

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção tratada",
            "minha_colecao.txt",
            "Texto (*.txt)"
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

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exportar coleção",
            "minha_colecao.csv",
            "CSV (*.csv)"
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

        # Sempre invalida resultados antigos.
        self.pending_search = text

        if len(text) < 2:

            self.suggestion_list.clear()

            self.suggestion_list.hide()

            self.search_status.clear()

            return

        # Se já buscamos exatamente esse texto,
        # não faça outra requisição.
        if text == self.last_completed_query:

            return

        self.search_status.setText(
            "🔄"
        )

        self.search_timer.start()

    def perform_scryfall_search(
        self
    ):

        query = self.pending_search.strip()

        if len(query) < 2:
            return

        # =================================================
        # GARANTIR QUE O TEXTO AINDA É O MESMO
        # =================================================

        current_text = (
            self.add_input
            .text()
            .strip()
        )

        if query != current_text:
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

        # =================================================
        # RESPOSTA ANTIGA
        # =================================================

        if query != current_text:
            return

        self.last_completed_query = query

        self.search_status.clear()

        self.suggestion_list.clear()

        if not suggestions:

            self.suggestion_list.hide()

            return

        # =================================================
        # REMOVER DUPLICATAS
        # =================================================

        unique_suggestions = []

        seen = set()

        for name in suggestions:

            if not name:
                continue

            name = str(
                name
            ).strip()

            key = name.casefold()

            if key in seen:
                continue

            seen.add(
                key
            )

            unique_suggestions.append(
                name
            )

            if len(unique_suggestions) >= 8:
                break

        if not unique_suggestions:

            self.suggestion_list.hide()

            return

        # =================================================
        # ADICIONAR SUGESTÕES
        # =================================================

        self.suggestion_list.addItems(
            unique_suggestions
        )

        self.suggestion_list.setCurrentRow(
            -1
        )

        self.suggestion_list.show()

    # =====================================================
    # SUGESTÃO
    # =====================================================

    def select_suggestion(
        self,
        item
    ):

        if not item:
            return

        name = item.text().strip()

        if not name:
            return

        # Primeiro define o texto.
        self.add_input.blockSignals(
            True
        )

        self.add_input.setText(
            name
        )

        self.add_input.blockSignals(
            False
        )

        self.pending_search = name

        self.last_completed_query = name

        self.suggestion_list.hide()

        self.add_input.setFocus()

        # Busca a carta sem bloquear a interface.
        self.add_card_from_input()

    def handle_add_enter(
        self
    ):

        # =================================================
        # SE EXISTIR SUGESTÃO, USAR A PRIMEIRA
        # =================================================

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

        # =================================================
        # SEM SUGESTÃO
        # =================================================

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

        # =================================================
        # JÁ ESTÁ BUSCANDO
        # =================================================

        if self.card_search_in_progress:

            return

        # =================================================
        # INICIAR BUSCA
        # =================================================

        self.card_search_in_progress = True

        self.pending_card_name = name

        self.search_status.setText(
            "🔄"
        )

        self.add_button.setEnabled(
            False
        )

        self.suggestion_list.hide()

        task = ScryfallCardTask(
            name
        )

        task.signals.finished.connect(
            self.receive_card_data
        )

        task.signals.failed.connect(
            self.receive_card_error
        )

        self.card_search_pool.start(
            task
        )

    # =====================================================
    # CARTA RECEBIDA
    # =====================================================

    def receive_card_data(
        self,
        requested_name,
        card_data
    ):

        # =================================================
        # GARANTIR QUE É A BUSCA ATUAL
        # =================================================

        if requested_name != self.pending_card_name:

            return

        self.card_search_in_progress = False

        self.add_button.setEnabled(
            True
        )

        if not card_data:

            self.search_status.setText(
                "!"
            )

            return

        # =================================================
        # SALVAR NO BANCO
        #
        # A operação é rápida e acontece apenas depois
        # que a requisição HTTP terminou.
        # =================================================

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

            return

        # =================================================
        # LIMPAR INPUT
        # =================================================

        self.add_input.blockSignals(
            True
        )

        self.add_input.clear()

        self.add_input.blockSignals(
            False
        )

        self.pending_search = ""

        self.last_completed_query = ""

        self.suggestion_list.clear()

        self.suggestion_list.hide()

        self.search_status.clear()

        self.add_input.setFocus()

        # =================================================
        # ATUALIZAR LISTA
        # =================================================

        self.load_cards()

    # =====================================================
    # ERRO AO BUSCAR CARTA
    # =====================================================

    def receive_card_error(
        self,
        requested_name,
        error
    ):

        if requested_name != self.pending_card_name:

            return

        print(
            "[SCRYFALL] Falha ao buscar carta:",
            requested_name,
            "|",
            error
        )

        self.card_search_in_progress = False

        self.add_button.setEnabled(
            True
        )

        self.search_status.setText(
            "!"
        )

    # =====================================================
    # CARREGAR
    # =====================================================

    def load_cards(
        self
    ):

        try:

            cards = get_all_cards()

        except Exception as error:

            print(
                "[DATABASE] Erro ao carregar coleção:",
                error
            )

            cards = []

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

        try:

            if not text.strip():

                cards = get_all_cards()

            else:

                cards = search_cards(
                    text
                )

            self.display_cards(
                cards
            )

        except Exception as error:

            print(
                "[DATABASE] Erro na pesquisa:",
                error
            )

    # =====================================================
    # DISPLAY
    # =====================================================

    def display_cards(
        self,
        cards
    ):

        # =================================================
        # LIMPAR REFERÊNCIAS ANTIGAS
        # =================================================

        self.card_rows.clear()

        # =================================================
        # LIMPAR LAYOUT
        # =================================================

        while self.cards_layout.count():

            item = (
                self.cards_layout.takeAt(0)
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()

        # =================================================
        # CRIAR CARTAS
        # =================================================

        for card in cards:

            try:

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

            except ValueError:

                print(
                    "[DATABASE] Registro de carta inválido:",
                    card
                )

                continue

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
            self.show_card_details(card)
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

        image_label = QLabel()

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

            # =============================================
            # MANA
            # =============================================

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

            # =============================================
            # SEPARADOR
            # =============================================

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

            # =============================================
            # POWER / TOUGHNESS
            # =============================================

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

            # =============================================
            # CENTRALIZAÇÃO
            # =============================================

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
            1
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
        # DOWNLOAD DA IMAGEM
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

                # =================================================
                # CACHE DE IMAGEM
                # =================================================

                cached_pixmap = (
                    self.image_cache.get(
                        image_url
                    )
                )

                if (
                    cached_pixmap
                    and not cached_pixmap.isNull()
                ):

                    self.set_thumbnail(
                        image_label,
                        cached_pixmap
                    )

                    return

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
    # IMAGEM LOCAL
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

            # Colocar também no cache pelo caminho.
            # O cache principal por URL continuará sendo
            # preenchido quando o download retornar.

        except Exception as error:

            print(
                "[IMAGE] Erro:",
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

        # =================================================
        # GARANTIR QUE O LABEL AINDA EXISTE
        # =================================================

        try:

            if label is None:

                return

            self.set_thumbnail(
                label,
                pixmap
            )

        except RuntimeError:

            # Widget pode ter sido destruído enquanto
            # o download estava acontecendo.
            pass

    def receive_image_error(
        self,
        url,
        error,
        label
    ):

        print(
            f"[IMAGE] Falha: {url} | {error}"
        )

        try:

            label.setText(
                "🃏"
            )

        except RuntimeError:

            pass

    # =====================================================
    # MINIATURA
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
    # DETALHES DA CARTA
    # =====================================================

    def show_card_details(
        self,
        card
    ):

        if not card:
            return

        # =================================================
        # TENTAR RECUPERAR DO CACHE
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
        # TENTAR CAMINHO LOCAL
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

                        if not local_pixmap.isNull():

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
        # ABRIR JANELA
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
        # ALTERAR NO BANCO
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

            frame.deleteLater()

            return

        # =================================================
        # ATUALIZAR SOMENTE LABEL
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

            # =============================================
            # MANA
            # =============================================

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

            # =============================================
            # SEPARADOR
            # =============================================

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

            # =============================================
            # POWER / TOUGHNESS
            # =============================================

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

    # =====================================================
    # IMAGEM
    # =====================================================

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
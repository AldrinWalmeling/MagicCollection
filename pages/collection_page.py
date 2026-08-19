from pathlib import Path
import webbrowser
from urllib.parse import quote_plus

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
    QSize,

)

import shiboken6

from PySide6.QtGui import (
    QPixmap,
    QIcon,
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

ALERTA_ICON_PATH = ICONS_DIR / "alerta.png"

REFRESH_ICON_PATH = ICONS_DIR / "refresh.png"

LUPA_ICON_PATH = ICONS_DIR / "lupa.png"

EXPORTAR_ICON_PATH = ICONS_DIR / "exportar.png"

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
    QApplication,
    QCheckBox,
    QWidgetAction,
)


from services.scryfall import (
    autocomplete_card_names,
    get_card_by_name,
    get_card_by_scryfall_id,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from services.app_events import (
    app_events,
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
    initialize_database,
    get_card_collection_value,
    get_card_by_id,
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

# =========================================================
# PLACEHOLDER GLOBAL DA GRADE
# =========================================================

_GRID_PLACEHOLDER_PIXMAP = None

# =========================================================
# CACHE GLOBAL DE THUMBNAILS
# =========================================================

_GRID_THUMBNAIL_CACHE = {}

_MAX_GRID_THUMBNAIL_CACHE_SIZE = 500


def _get_grid_placeholder_pixmap(
        width,
        height,
):
    """
    Retorna o placeholder da grade usando cache.

    O arquivo card.png é carregado e redimensionado apenas
    quando ainda não existe uma versão desse tamanho.
    """

    global _GRID_PLACEHOLDER_PIXMAP

    if not CARD_ICON_PATH.exists():
        return QPixmap()

    # -----------------------------------------------------
    # CARREGAR ORIGINAL UMA ÚNICA VEZ
    # -----------------------------------------------------

    if (
            _GRID_PLACEHOLDER_PIXMAP is None
            or _GRID_PLACEHOLDER_PIXMAP.isNull()
    ):
        _GRID_PLACEHOLDER_PIXMAP = QPixmap(
            str(CARD_ICON_PATH)
        )

    if (
            _GRID_PLACEHOLDER_PIXMAP is None
            or _GRID_PLACEHOLDER_PIXMAP.isNull()
    ):
        return QPixmap()

    # -----------------------------------------------------
    # CACHE POR TAMANHO
    # -----------------------------------------------------

    cache_key = (
        f"__grid_placeholder__"
        f"{width}x{height}"
    )

    cached = (
        _GRID_THUMBNAIL_CACHE.get(
            cache_key
        )
        if "_GRID_THUMBNAIL_CACHE" in globals()
        else None
    )

    if (
            cached is not None
            and not cached.isNull()
    ):
        return cached

    # -----------------------------------------------------
    # REDIMENSIONAR
    # -----------------------------------------------------

    scaled = _GRID_PLACEHOLDER_PIXMAP.scaled(
        width,
        height,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation,
    )

    # -----------------------------------------------------
    # GUARDAR
    # -----------------------------------------------------

    if "_GRID_THUMBNAIL_CACHE" in globals():
        _GRID_THUMBNAIL_CACHE[
            cache_key
        ] = scaled

    return scaled


def _cleanup_grid_thumbnail_cache():
    """
    Mantém o cache de thumbnails dentro do limite.
    Remove as entradas mais antigas quando necessário.
    """

    global _GRID_THUMBNAIL_CACHE

    if (
            len(_GRID_THUMBNAIL_CACHE)
            > _MAX_GRID_THUMBNAIL_CACHE_SIZE
    ):

        keys_to_remove = list(
            _GRID_THUMBNAIL_CACHE.keys()
        )[
                         :int(
                             _MAX_GRID_THUMBNAIL_CACHE_SIZE
                             * 0.2
                         )
                         ]

        for key in keys_to_remove:
            del _GRID_THUMBNAIL_CACHE[key]


def _cleanup_grid_thumbnail_cache():
    """
    Mantém o cache de thumbnails dentro do limite.
    Remove as entradas mais antigas quando necessário.
    """

    global _GRID_THUMBNAIL_CACHE

    if (
            len(_GRID_THUMBNAIL_CACHE)
            > _MAX_GRID_THUMBNAIL_CACHE_SIZE
    ):

        keys_to_remove = list(
            _GRID_THUMBNAIL_CACHE.keys()
        )[
                         :int(
                             _MAX_GRID_THUMBNAIL_CACHE_SIZE
                             * 0.2
                         )
                         ]

        for key in keys_to_remove:
            del _GRID_THUMBNAIL_CACHE[key]


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
# FILTRO DE MÚLTIPLA SELEÇÃO
# =========================================================

class MultiSelectFilterButton(QPushButton):
    """
    Botão de filtro com seleção múltipla.

    Comportamento:
    - Clique abre um menu.
    - Permite selecionar múltiplas opções.
    - Mostra as seleções no próprio botão.
    - Muitas opções usam lista com scrollbar.
    """

    selectionChanged = Signal(list)

    def __init__(
            self,
            title,
            options,
            parent=None,
    ):
        super().__init__(
            parent
        )

        # =================================================
        # DADOS
        # =================================================

        self.title = title

        self.options = list(
            options or []
        )

        self.selected_values = set()

        self.actions = {}

        # =================================================
        # BOTÃO
        # =================================================

        self.setObjectName(
            "MultiSelectFilterButton"
        )

        self.setText(
            f"{self.title}: Todas"
        )

        self.setMinimumHeight(
            36
        )

        if self.title == "Cor":

            scroll_height = 145
            menu_width = 95

        elif self.title == "Tipo":

            scroll_height = 145
            menu_width = 150

        elif self.title == "Supertipo":

            scroll_height = 85
            menu_width = 120

        elif self.title == "Raridade":

            scroll_height = 125
            menu_width = 125

        elif self.title == "Edição":

            scroll_height = 340
            menu_width = 300

        elif self.title == "Ordenação":

            scroll_height = 250
            menu_width = 260


        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        # =================================================
        # MENU
        # =================================================

        self.menu = QMenu(
            self
        )

        # -------------------------------------------------
        # POPUP SEM MOLDURA NATIVA
        # -------------------------------------------------

        self.menu.setWindowFlags(
            Qt.WindowType.Popup
            |
            Qt.WindowType.FramelessWindowHint
        )

        self.menu.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        self.menu.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True
        )

        self.menu.setObjectName(
            "CollectionFilterPopup"
        )

        self._build_menu()

        self.setMenu(
            self.menu
        )

    # =====================================================
    # CRIAR MENU
    # =====================================================

    def _build_menu(
            self,
    ):
        # =================================================
        # LIMPAR MENU
        # =================================================

        self.menu.clear()

        self.actions = {}

        # =================================================
        # CONTAINER PRINCIPAL
        # =================================================

        container = QWidget()

        container.setObjectName(
            "CollectionFilterMenu"
        )

        container.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        container_layout = QVBoxLayout(
            container
        )

        container_layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        container_layout.setSpacing(
            4
        )

        # =================================================
        # "TODAS"
        # =================================================

        all_checkbox = QCheckBox(
            "Todas"
        )

        all_checkbox.setChecked(
            not self.selected_values
        )

        all_checkbox.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        all_checkbox.toggled.connect(
            self._toggle_all_checkbox
        )

        container_layout.addWidget(
            all_checkbox
        )

        self.all_action = (
            all_checkbox
        )

        # =================================================
        # SEPARADOR
        # =================================================

        separator = QWidget()

        separator.setObjectName(
            "CollectionFilterSeparator"
        )

        separator.setFixedHeight(
            1
        )

        container_layout.addWidget(
            separator
        )

        # =================================================
        # ÁREA DA LISTA
        # =================================================

        scroll_area = QScrollArea()

        scroll_area.setObjectName(
            "CollectionFilterScrollArea"
        )

        scroll_area.setWidgetResizable(
            True
        )

        scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll_area.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        # =================================================
        # TAMANHO DO MENU
        # =================================================

        option_count = len(
            self.options
        )

        # -------------------------------------------------
        # TAMANHOS PADRÃO
        # -------------------------------------------------

        scroll_height = 220
        menu_width = 240

        # -------------------------------------------------
        # TAMANHO ESPECÍFICO POR FILTRO
        # -------------------------------------------------

        if self.title == "Cor":

            scroll_height = 280
            menu_width = 120

        elif self.title == "Tipo":

            scroll_height = 280
            menu_width = 180

        elif self.title == "Supertipo":

            scroll_height = 160
            menu_width = 130

        elif self.title == "Raridade":

            scroll_height = 240
            menu_width = 120

        elif self.title == "Edição":

            scroll_height = 340
            menu_width = 300

        elif self.title == "Ordenação":

            scroll_height = 250
            menu_width = 260

        # -------------------------------------------------
        # APLICAR TAMANHO
        # -------------------------------------------------

        scroll_area.setFixedHeight(
            scroll_height
        )

        scroll_area.setMinimumWidth(
            menu_width
        )

        scroll_area.setMaximumWidth(
            menu_width
        )

        # =================================================
        # LISTA
        # =================================================

        list_widget = QWidget()

        list_widget.setObjectName(
            "CollectionFilterList"
        )

        list_widget.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground,
            True
        )

        list_layout = QVBoxLayout(
            list_widget
        )

        list_layout.setContentsMargins(
            4,
            0,
            4,
            0,
        )

        list_layout.setSpacing(
            2
        )

        # =================================================
        # OPÇÕES
        # =================================================

        for label, value in self.options:
            checkbox = QCheckBox(
                label
            )

            if self.title == "Cor":
                checkbox.setProperty(
                    "filterColor",
                    value
                )

            # -------------------------------------------------
            # IDENTIDADE VISUAL DA OPÇÃO
            # -------------------------------------------------

            if self.title == "Cor":

                checkbox.setProperty(
                    "filterOption",
                    f"color_{value}"
                )

            elif self.title == "Tipo":

                checkbox.setProperty(
                    "filterOption",
                    f"type_{value}"
                )

            elif self.title == "Supertipo":

                checkbox.setProperty(
                    "filterOption",
                    f"supertype_{value}"
                )

            elif self.title == "Raridade":

                checkbox.setProperty(
                    "filterOption",
                    f"rarity_{value}"
                )

            elif self.title == "Edição":

                checkbox.setProperty(
                    "filterOption",
                    "edition"
                )

            checkbox.setChecked(
                value
                in self.selected_values
            )

            checkbox.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            checkbox.toggled.connect(
                lambda checked,
                       value=value:
                self.toggle_value(
                    value,
                    checked,
                )
            )

            list_layout.addWidget(
                checkbox
            )

            self.actions[
                value
            ] = checkbox

        list_layout.addStretch()

        scroll_area.setWidget(
            list_widget
        )

        container_layout.addWidget(
            scroll_area
        )

        # =================================================
        # COLOCAR NO QMENU
        # =================================================

        widget_action = QWidgetAction(
            self.menu
        )

        widget_action.setDefaultWidget(
            container
        )

        self.menu.addAction(
            widget_action
        )
    # =====================================================
    # TODAS — LISTA ROLÁVEL
    # =====================================================

    def _toggle_all_checkbox(
            self,
            checked,
    ):
        if not checked:
            return

        self.selected_values.clear()

        for action in self.actions.values():

            action.blockSignals(
                True
            )

            action.setChecked(
                False
            )

            action.blockSignals(
                False
            )

        self.update_button_text()

        self.selectionChanged.emit(
            []
        )

    # =====================================================
    # ALTERAR OPÇÕES
    # =====================================================

    def set_options(
            self,
            options,
    ):
        # -------------------------------------------------
        # GUARDAR SELEÇÕES ATUAIS
        # -------------------------------------------------

        current_selection = set(
            self.selected_values
        )

        # -------------------------------------------------
        # NOVAS OPÇÕES
        # -------------------------------------------------

        self.options = list(
            options or []
        )

        # -------------------------------------------------
        # VALIDAR SELEÇÕES
        # -------------------------------------------------

        valid_values = {
            value
            for label, value
            in self.options
        }

        current_selection &= (
            valid_values
        )

        self.selected_values = (
            current_selection
        )

        # -------------------------------------------------
        # RECRIAR MENU
        # -------------------------------------------------

        self._build_menu()

        # -------------------------------------------------
        # RESTAURAR CHECKS
        # -------------------------------------------------

        for value, action in (
                self.actions.items()
        ):

            action.blockSignals(
                True
            )

            action.setChecked(
                value
                in self.selected_values
            )

            action.blockSignals(
                False
            )

        # -------------------------------------------------
        # ATUALIZAR "TODAS"
        # -------------------------------------------------

        self.all_action.blockSignals(
            True
        )

        self.all_action.setChecked(
            not self.selected_values
        )

        self.all_action.blockSignals(
            False
        )

        # -------------------------------------------------
        # ATUALIZAR TEXTO
        # -------------------------------------------------

        self.update_button_text()

    # =====================================================
    # SELECIONAR VALORES
    # =====================================================

    def set_selected_values(
            self,
            values,
    ):
        values = set(
            values or []
        )

        valid_values = {
            value
            for label, value
            in self.options
        }

        values &= valid_values

        self.selected_values = (
            values
        )

        # -------------------------------------------------
        # ATUALIZAR OPÇÕES
        # -------------------------------------------------

        for value, action in (
                self.actions.items()
        ):

            action.blockSignals(
                True
            )

            action.setChecked(
                value
                in self.selected_values
            )

            action.blockSignals(
                False
            )

        # -------------------------------------------------
        # ATUALIZAR TODAS
        # -------------------------------------------------

        self.all_action.blockSignals(
            True
        )

        self.all_action.setChecked(
            not self.selected_values
        )

        self.all_action.blockSignals(
            False
        )

        # -------------------------------------------------
        # TEXTO
        # -------------------------------------------------

        self.update_button_text()

    # =====================================================
    # OBTER VALORES
    # =====================================================

    def get_selected_values(
            self,
    ):
        return list(
            self.selected_values
        )

    # =====================================================
    # SELECIONAR / DESSELECIONAR
    # =====================================================

    def toggle_value(
            self,
            value,
            checked,
    ):
        if checked:

            self.selected_values.add(
                value
            )

        else:

            self.selected_values.discard(
                value
            )

        # -------------------------------------------------
        # "TODAS"
        # -------------------------------------------------

        self.all_action.blockSignals(
            True
        )

        self.all_action.setChecked(
            not self.selected_values
        )

        self.all_action.blockSignals(
            False
        )

        # -------------------------------------------------
        # TEXTO
        # -------------------------------------------------

        self.update_button_text()

        # -------------------------------------------------
        # AVISAR FILTRO
        # -------------------------------------------------

        self.selectionChanged.emit(
            list(
                self.selected_values
            )
        )

    # =====================================================
    # LIMPAR SELEÇÃO
    # =====================================================

    def clear_selection(
            self,
    ):
        self.selected_values.clear()

        for action in (
                self.actions.values()
        ):

            action.blockSignals(
                True
            )

            action.setChecked(
                False
            )

            action.blockSignals(
                False
            )

        self.all_action.blockSignals(
            True
        )

        self.all_action.setChecked(
            True
        )

        self.all_action.blockSignals(
            False
        )

        self.update_button_text()

        self.selectionChanged.emit(
            []
        )

    # =====================================================
    # TEXTO DO BOTÃO
    # =====================================================

    def update_button_text(
            self,
    ):
        count = len(
            self.selected_values
        )

        # -------------------------------------------------
        # NADA SELECIONADO
        # -------------------------------------------------

        if count == 0:

            self.setText(
                f"{self.title}: Todas"
            )

            return

        # -------------------------------------------------
        # UMA OPÇÃO
        # -------------------------------------------------

        if count == 1:

            value = next(
                iter(
                    self.selected_values
                )
            )

            label = next(
                (
                    label
                    for label, option_value
                    in self.options
                    if option_value == value
                ),
                value,
            )

            self.setText(
                f"{self.title}: {label}"
            )

            return

        # -------------------------------------------------
        # DUAS OPÇÕES
        # -------------------------------------------------

        if count == 2:

            labels = []

            for label, value in (
                    self.options
            ):

                if value in (
                        self.selected_values
                ):
                    labels.append(
                        label
                    )

            self.setText(
                f"{self.title}: "
                + ", ".join(
                    labels
                )
            )

            return

        # -------------------------------------------------
        # MUITAS OPÇÕES
        # -------------------------------------------------

        self.setText(
            f"{self.title}: "
            f"{count} selecionadas"
        )

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
                scryfall_id = str(
                    card.get("scryfall_id")
                    or ""
                ).strip()

                name = (
                        card.get("printed_name")
                        or card.get("name")
                        or ""
                )

                name = str(
                    name
                ).strip()

                if not name and not scryfall_id:
                    continue

                self.signals.progress.emit(
                    index,
                    total,
                    name or scryfall_id,
                )

                # =====================================================
                # PRIORIDADE 1
                # PRINTING EXATO
                # =====================================================

                card_data = None

                if scryfall_id:
                    card_data = (
                        get_card_by_scryfall_id(
                            scryfall_id
                        )
                    )

                # =====================================================
                # FALLBACK
                #
                # Só usamos nome quando o registro antigo
                # não possui Scryfall ID.
                # =====================================================

                if (
                        not card_data
                        and not scryfall_id
                        and name
                ):
                    language = (
                            card.get("lang")
                            or "en"
                    )

                    if language not in (
                            SCRYFALL_LANGUAGES.values()
                    ):
                        language = "en"

                    card_data = (
                        get_card_by_name(
                            name,
                            language=language,
                        )
                    )

                    if (
                            not card_data
                            and language != "en"
                    ):
                        card_data = (
                            get_card_by_name(
                                card.get("name")
                                or name,
                                language="en",
                            )
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
    clicked = Signal()
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
        # =========================================================
        # PLACEHOLDER
        # =========================================================

        placeholder = _get_grid_placeholder_pixmap(
            self._base_width,
            self._base_height,
        )

        if (
                placeholder is not None
                and not placeholder.isNull()
        ):
            self.image_label.setPixmap(
                placeholder
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
        if watched is self.control_quantity:
            if event.type() in (
                    QEvent.Type.FocusIn,
                    QEvent.Type.MouseButtonPress,
            ):
                self._editing_quantity = True
                self._animate_hover(True)

            elif event.type() in (
                    QEvent.Type.FocusOut,
                    QEvent.Type.KeyPress,
            ):
                if (
                        event.type() == QEvent.Type.KeyPress
                        and event.key()
                        not in (
                        Qt.Key.Key_Return,
                        Qt.Key.Key_Enter,
                        Qt.Key.Key_Escape,
                )
                ):
                    return super().eventFilter(
                        watched,
                        event,
                    )

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
        if not isinstance(card_data, dict):
            print(
                "[GRID] set_card_data recebeu dados inválidos"
            )
            return

        # -----------------------------------------------------
        # ATUALIZAR DADOS DA CARTA
        # -----------------------------------------------------

        self.card_data = card_data
        self.current_face_index = face_index
        self.current_art_index = art_index

        print(
            "[GRID] Dados da carta atualizados:",
            self.card_data.get("name"),
        )

        print(
            "[GRID] Novo image_path:",
            self.card_data.get("image_path"),
        )

        # -----------------------------------------------------
        # ATUALIZAR IMAGEM
        # -----------------------------------------------------

        self.update_card_image()

    def update_card_image(self):
        """
        Atualiza somente a imagem desta carta no Grid.

        A imagem é obtida do image_path presente em self.card_data.
        O cache da Collection é invalidado quando necessário para
        garantir que uma imagem recém-substituída não continue
        sendo exibida como a antiga.
        """

        if not isinstance(self.card_data, dict):
            print("[GRID] card_data inválido")
            return

        image_path = (
            self.card_data.get("image_path")
        )

        if not image_path:
            print(
                "[GRID] Carta sem image_path:",
                self.card_data.get("name"),
            )
            return

        image_path = Path(
            str(image_path)
        )

        if not image_path.exists():
            print(
                "[GRID] Imagem não encontrada:",
                image_path,
            )
            return

        # =====================================================
        # INVALIDAR CACHE LOCAL DA CARTA
        # =====================================================

        try:
            cache_key = str(
                image_path
            )

            if hasattr(
                    self,
                    "image_cache",
            ):
                self.image_cache.pop(
                    cache_key,
                    None,
                )

        except Exception as error:
            print(
                "[GRID] Erro ao invalidar cache local:",
                error,
            )

        # =====================================================
        # CARREGAR IMAGEM NOVAMENTE
        # =====================================================

        pixmap = QPixmap()

        try:
            pixmap = QPixmap(
                str(image_path)
            )

        except Exception as error:
            print(
                "[GRID] Erro ao carregar imagem:",
                error,
            )
            return

        if pixmap.isNull():
            print(
                "[GRID] QPixmap inválido:",
                image_path,
            )
            return

        print(
            "[GRID] Nova imagem carregada:",
            image_path,
            "| válido:",
            not pixmap.isNull(),
        )

        # =====================================================
        # TAMANHO DO WIDGET
        # =====================================================

        width = self.image_label.width()
        height = self.image_label.height()

        if width <= 0:
            width = self.width()

        if height <= 0:
            height = self.height()

        if width <= 0 or height <= 0:
            print(
                "[GRID] Tamanho inválido para atualização:",
                width,
                height,
            )
            return

        # =====================================================
        # ESCALAR
        # =====================================================

        scaled_pixmap = pixmap.scaled(
            width,
            height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # =====================================================
        # ATUALIZAR LABEL
        # =====================================================

        self.image_label.setPixmap(
            scaled_pixmap
        )

        self.image_label.setText(
            ""
        )

        print(
            "[GRID] Imagem atualizada:",
            self.card_data.get("name"),
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

    def mousePressEvent(
            self,
            event,
    ):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

        super().mousePressEvent(
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
        self.active_supertype_filter = "all"
        self.active_set_filter = "all"
        self.active_sort = "name_asc"

        self.card_rows = {}
        self.selected_card_id = None

        self.rebuilding_grid = False

        self._grid_columns = None

        self._grid_generation = 0

        # =========================================================
        # RENDERIZAÇÃO INCREMENTAL DA GRADE
        # =========================================================
        # A coleção não será mais construída inteira de uma vez.
        #
        # Em vez de:
        #   500 cartas -> criar 500 widgets imediatamente
        #
        # faremos:
        #   30 cartas -> pausa -> 30 -> pausa -> 30...
        #
        # Isso mantém a interface responsiva durante a abertura.
        self._grid_render_batch_size = 6
        # =========================================================
        # VIRTUALIZAÇÃO DA GRADE
        # =========================================================

        self._virtual_grid_enabled = False

        # Quantidade aproximada de linhas extras mantidas
        # acima/abaixo da área visível.
        self._virtual_grid_buffer_rows = 2

        # Widgets atualmente utilizados pela grade.
        self._virtual_grid_widgets = []

        # Número de colunas atual.
        self._virtual_grid_columns = 1

        # Primeira linha atualmente renderizada.
        self._virtual_grid_first_row = -1

        # Último conjunto de cartas utilizado.
        self._virtual_grid_cards = []

        # Evita chamadas repetidas durante o mesmo evento.
        self._virtual_grid_update_pending = False

        # Guarda a última posição vertical conhecida.
        self._virtual_grid_last_scroll_value = -1

        self._grid_render_timer = QTimer(self)
        self._grid_render_timer.setSingleShot(True)
        self._grid_rendering_pending = False
        self._grid_render_cards = []
        self._grid_render_index = 0
        self._grid_render_generation = 0
        self._grid_render_layout = None

        # =========================================================
        # EVENTOS DA APLICAÇÃO
        # =========================================================

        app_events.collection_card_changed.connect(
            self._on_collection_card_changed
        )

        app_events.card_data_changed.connect(
            self._on_card_data_changed
        )
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

        # =========================================================
        # DOWNLOADS DE IMAGEM
        # =========================================================
        # Mantemos poucos downloads simultâneos para evitar que
        # a abertura da coleção dispute CPU/disco/rede com a GUI.
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

        self._show_collection_loading(
            "Preparando suas cartas..."
        )

        QTimer.singleShot(
            0,
            self.load_cards
        )

    # =========================================================
    # LOADING DA COLLECTION
    # =========================================================

    def _create_collection_loading_overlay(self):
        """
        Cria o overlay exibido enquanto a grade da coleção
        está sendo construída.

        O overlay fica por cima da área de cartas e não
        interfere na estrutura do QGridLayout.
        """

        # Evita criar duas vezes.
        if hasattr(
                self,
                "_collection_loading_overlay",
        ):
            return

        # =====================================================
        # OVERLAY
        # =====================================================

        overlay = QFrame(
            self.scroll_area.viewport()
        )

        overlay.setObjectName(
            "collectionLoadingOverlay"
        )

        overlay.setFrameShape(
            QFrame.Shape.NoFrame
        )

        overlay.setStyleSheet(
            """
            QFrame#collectionLoadingOverlay {

            }

            QLabel#collectionLoadingTitle {
                color: #f2f2f2;
                font-size: 18px;
                font-weight: 600;
            }

            QLabel#collectionLoadingSubtitle {
                color: #9299a8;
                font-size: 13px;
            }

            QLabel#collectionLoadingSpinner {
                color: #d8b56a;
                font-size: 28px;
                font-weight: 400;
            }
            """
        )

        # =====================================================
        # CONTAINER CENTRAL
        # =====================================================

        container = QFrame(
            overlay
        )

        container.setObjectName(
            "collectionLoadingContainer"
        )

        container.setStyleSheet(
            """
            QFrame#collectionLoadingContainer {
                background: transparent;
            }
            """
        )

        layout = QVBoxLayout(
            container
        )

        layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        layout.setSpacing(
            6
        )

        layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # =====================================================
        # INDICADOR
        # =====================================================

        spinner = QLabel(
            "✦"
        )

        spinner.setObjectName(
            "collectionLoadingSpinner"
        )

        spinner.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # =====================================================
        # TÍTULO
        # =====================================================

        title = QLabel(
            "Carregando coleção"
        )

        title.setObjectName(
            "collectionLoadingTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # =====================================================
        # SUBTÍTULO
        # =====================================================

        subtitle = QLabel(
            "Preparando suas cartas..."
        )

        subtitle.setObjectName(
            "collectionLoadingSubtitle"
        )

        subtitle.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # =====================================================
        # ADICIONAR
        # =====================================================

        layout.addWidget(
            spinner
        )

        layout.addWidget(
            title
        )

        layout.addWidget(
            subtitle
        )

        # =====================================================
        # GUARDAR REFERÊNCIAS
        # =====================================================

        self._collection_loading_overlay = overlay
        self._collection_loading_container = container
        self._collection_loading_spinner = spinner
        self._collection_loading_title = title
        self._collection_loading_subtitle = subtitle

        # =====================================================
        # POSICIONAR
        # =====================================================

        self._resize_collection_loading_overlay()

        overlay.hide()

    # =========================================================
    # REDIMENSIONAR LOADING
    # =========================================================

    # =========================================================
    # REDIMENSIONAR LOADING
    # =========================================================

    def _resize_collection_loading_overlay(
            self,
    ):
        """
        Mantém o overlay exatamente sobre o viewport
        da coleção.

        O cálculo é feito usando o tamanho REAL do viewport,
        evitando o problema de o loading aparecer deslocado
        no primeiro carregamento da página.
        """

        overlay = getattr(
            self,
            "_collection_loading_overlay",
            None,
        )

        if overlay is None:
            return

        viewport = self.scroll_area.viewport()

        if viewport is None:
            return

        # -----------------------------------------------------
        # Garantir que o viewport já possui geometria válida
        # -----------------------------------------------------

        viewport_width = viewport.width()
        viewport_height = viewport.height()

        if (
                viewport_width <= 0
                or viewport_height <= 0
        ):
            return

        # -----------------------------------------------------
        # Overlay ocupa exatamente o viewport
        # -----------------------------------------------------

        overlay.setGeometry(
            0,
            0,
            viewport_width,
            viewport_height,
        )

        # -----------------------------------------------------
        # Container central
        # -----------------------------------------------------

        container = getattr(
            self,
            "_collection_loading_container",
            None,
        )

        if container is None:
            return

        container.adjustSize()

        container_width = container.sizeHint().width()
        container_height = container.sizeHint().height()

        # -----------------------------------------------------
        # Centralizar
        # -----------------------------------------------------

        x = (
                    viewport_width
                    - container_width
            ) // 2

        y = (
                    viewport_height
                    - container_height
            ) // 2

        container.setGeometry(
            x,
            y,
            container_width,
            container_height,
        )

    # =========================================================
    # MOSTRAR LOADING
    # =========================================================

    # =========================================================
    # MOSTRAR LOADING
    # =========================================================

    def _show_collection_loading(
            self,
            message="Preparando suas cartas...",
    ):
        """
        Mostra o overlay de carregamento.

        O posicionamento é recalculado depois que o Qt
        processa o layout da página.
        """

        if not hasattr(
                self,
                "_collection_loading_overlay",
        ):
            self._create_collection_loading_overlay()

        # -----------------------------------------------------
        # Texto
        # -----------------------------------------------------

        self._collection_loading_subtitle.setText(
            message
        )

        # -----------------------------------------------------
        # Mostrar primeiro
        # -----------------------------------------------------

        self._collection_loading_overlay.show()

        self._collection_loading_overlay.raise_()

        # -----------------------------------------------------
        # Forçar atualização de layout
        # -----------------------------------------------------

        self.scroll_area.viewport().update()

        # -----------------------------------------------------
        # PRIMEIRO POSICIONAMENTO
        #
        # singleShot(0) espera o Qt terminar o ciclo atual
        # de layout antes de calcular a geometria.
        # -----------------------------------------------------

        QTimer.singleShot(
            0,
            self._resize_collection_loading_overlay,
        )

        self._collection_loading_overlay.update()

    # =========================================================
    # ESCONDER LOADING
    # =========================================================

    def _hide_collection_loading(self):
        """
        Esconde o overlay após a grade terminar.
        """

        overlay = getattr(
            self,
            "_collection_loading_overlay",
            None,
        )

        if overlay is None:
            return

        overlay.hide()

    # =========================================================
    # RESIZE DA PÁGINA
    # =========================================================

    def resizeEvent(
            self,
            event,
    ):
        """
        Reposiciona o loading sempre que a página
        muda de tamanho.
        """

        super().resizeEvent(
            event
        )

        QTimer.singleShot(
            0,
            self._resize_collection_loading_overlay,
        )

        # =========================================================
        # SHOW EVENT
        # =========================================================

        def showEvent(
                self,
                event,
        ):
            """
            Garante que a geometria do loading seja calculada
            novamente quando a CollectionPage aparece.
            """

            super().showEvent(
                event
            )

            QTimer.singleShot(
                0,
                self._resize_collection_loading_overlay,
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

        self.export_button.setIcon(
            QIcon(str(EXPORTAR_ICON_PATH))
        )

        self.export_button.setIconSize(
            QSize(20, 20)
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

        search_icon = QLabel()

        search_icon.setPixmap(
            QIcon(str(LUPA_ICON_PATH)).pixmap(20, 20)
        )

        search_icon.setFixedSize(
            20,
            20
        )

        search_icon.setObjectName(
            "SearchIcon"
        )

        search_layout.addWidget(
            search_icon
        )

        search_layout.setSpacing(
            8
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
        self.color_filter = MultiSelectFilterButton(
            "Cor",
            [
                ("Branco", "W"),
                ("Azul", "U"),
                ("Preto", "B"),
                ("Vermelho", "R"),
                ("Verde", "G"),
                ("Incolor", "C"),
                ("Multicolor", "M"),
            ],
            self,
        )

        self.color_filter.setFixedWidth(
            120
        )

        self.color_filter.selectionChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.color_filter
        )

        # -------------------------------------------------
        # TIPO
        # -------------------------------------------------

        self.type_filter = MultiSelectFilterButton(
            "Tipo",
            [
                ("Criatura", "Criatura"),
                ("Mágica Instantânea", "Mágica Instantânea"),
                ("Feitiço", "Feitiço"),
                ("Encantamento", "Encantamento"),
                ("Artefato", "Artefato"),
                ("Planeswalker", "Planeswalker"),
                ("Terreno", "Terreno"),
            ],
            self,
        )

        self.type_filter.setFixedWidth(
            120
        )

        self.type_filter.selectionChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.type_filter
        )

        # -------------------------------------------------
        # SUPERTIPO
        # -------------------------------------------------

        self.supertype_filter = MultiSelectFilterButton(
            "Supertipo",
            [
                ("Lendária", "legendary"),
                ("Básica", "basic"),
                ("Nevada", "snow"),
                ("Mundo", "world"),
            ],
            self,
        )

        self.supertype_filter.setFixedWidth(
            150
        )

        self.supertype_filter.selectionChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.supertype_filter
        )

        # -------------------------------------------------
        # RARIDADE
        # -------------------------------------------------

        self.rarity_filter = MultiSelectFilterButton(
            "Raridade",
            [
                ("Comum", "common"),
                ("Incomum", "uncommon"),
                ("Rara", "rare"),
                ("Mítica", "mythic"),
                ("Especial", "special"),
                ("Bônus", "bonus"),
            ],
            self,
        )

        self.rarity_filter.setFixedWidth(
            150
        )

        self.rarity_filter.selectionChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.rarity_filter
        )
        # -------------------------------------------------
        # EDIÇÃO
        # -------------------------------------------------

        self.set_filter = MultiSelectFilterButton(
            "Edição",
            [],
            self,
        )

        self.set_filter.selectionChanged.connect(
            self.apply_collection_filters
        )

        filters_layout.addWidget(
            self.set_filter
        )

        self.set_filter.setFixedWidth(
            125
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
            "Menor → Maior",
            "quantity_asc",
        )

        self.sort_filter.addItem(
            "Maior → Menor",
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

        self.sort_filter.setFixedWidth(
            135
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

        self.clear_filters_button = QPushButton(
            "Limpar filtros"
        )

        self.clear_filters_button.setMinimumWidth(
            130
        )

        self.clear_filters_button.setMaximumWidth(
            200
        )

        self.clear_filters_button.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )

        self.clear_filters_button.clicked.connect(
            self.clear_collection_filters
        )

        filters_layout.addWidget(
            self.clear_filters_button
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

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_area.setObjectName(
            "CardsScrollArea"
        )

        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.cards_container = CardsContainer()

        self.cards_container.setObjectName(
            "CardsContainer"
        )

        self.cards_container.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )

        self.cards_container.setMinimumWidth(0)
        self.cards_container.setMinimumHeight(0)

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

        # =========================================================
        # SCROLL — ATUALIZAÇÃO DA GRADE VIRTUAL
        # =========================================================

        self.scroll_area.verticalScrollBar().valueChanged.connect(
            self._on_virtual_grid_scroll
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

    def handle_container_resize(
            self,
    ):
        """
        Recalcula a geometria da grade somente quando
        a quantidade de colunas realmente muda.

        O tamanho das cartas e a quantidade de colunas
        são determinados exclusivamente por
        _calculate_grid_geometry().
        """

        self._resize_collection_loading_overlay()

        if self.current_layout != "grid":
            return

        if self.rebuilding_grid:
            return

        if not self.current_cards:
            return

        columns, card_width = (
            self._calculate_grid_geometry()
        )

        if columns == self._grid_columns:
            return

        self._grid_columns = columns

        self._grid_resize_timer.start()

    def rebuild_grid_after_resize(
            self,
    ):
        """
        Reconstrói a grade após o resize.

        O timer impede múltiplos rebuilds durante
        o redimensionamento contínuo da janela.
        """

        if self.current_layout != "grid":
            return

        if self.rebuilding_grid:
            return

        if not self.current_cards:
            return

        columns, card_width = (
            self._calculate_grid_geometry()
        )

        self._grid_columns = columns

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

            if language not in self.selected_languages:
                self.selected_languages.append(
                    language
                )

        else:

            if language in self.selected_languages:
                self.selected_languages.remove(
                    language
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

        self.search_status.setPixmap(
            QIcon(str(REFRESH_ICON_PATH)).pixmap(20, 20)
        )

        self.search_timer.start()

    # =====================================================
    # AUTOCOMPLETE
    # =====================================================
    def update_language_button(
            self,
    ):

        language_labels = {
            "en": "🇺🇸 Inglês",
            "pt": "🇧🇷 Português",
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
            for language
            in self.selected_languages
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

        self.search_status.setPixmap(
            QIcon(str(REFRESH_ICON_PATH)).pixmap(20, 20)
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

        self.search_status.setPixmap(
            QIcon(str(REFRESH_ICON_PATH)).pixmap(20, 20)
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
            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
            )

            return

        self.search_status.setPixmap(
            QIcon(str(REFRESH_ICON_PATH)).pixmap(20, 20)
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
            # PRIORIDADE 1 — INGLÊS
            #
            # O autocomplete do Scryfall normalmente retorna
            # o nome canônico da carta.
            #
            # Isso é especialmente importante para cartas
            # de duas faces:
            #
            # Accursed Witch // Infectious Curse
            #
            # =================================================

            card_data = get_card_by_name(
                name,
                language="en",
            )

            # =================================================
            # PRIORIDADE 2 — IDIOMAS SELECIONADOS
            #
            # Se não encontrou em inglês, tenta os idiomas
            # escolhidos pelo usuário.
            # =================================================

            if not card_data:

                for language in languages:

                    if language == "en":
                        continue

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

            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
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

            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
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

            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
            )

            self.add_button.setEnabled(
                True
            )

            return

        if not card_data:
            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
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

            import traceback

            print(
                "[DATABASE] Erro:",
                error,
            )

            print(
                "[DATABASE] Tipo de card_data:",
                type(card_data),
            )

            print(
                "[DATABASE] card_data:",
                repr(card_data),
            )

            traceback.print_exc()

            success = False

        if not success:
            self.search_status.setPixmap(
                QIcon(str(ALERTA_ICON_PATH)).pixmap(20, 20)
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

    # =====================================================
    # VERIFICAR FILTRO DE COR
    # =====================================================

    def card_matches_color(
            self,
            card,
            colors,
    ):

        # -------------------------------------------------
        # NENHUM FILTRO
        # -------------------------------------------------

        if not colors:
            return True

        # -------------------------------------------------
        # SEGURANÇA
        # -------------------------------------------------

        if not card:
            return False

        # -------------------------------------------------
        # OBTER CUSTO DE MANA
        # -------------------------------------------------

        try:

            mana_cost = (
                card[6]
                if len(card) > 6
                else ""
            )

        except (
                IndexError,
                TypeError,
        ):

            mana_cost = ""

        # -------------------------------------------------
        # OBTER CORES DA CARTA
        # -------------------------------------------------

        card_colors = self.get_card_colors(
            mana_cost
        )

        # -------------------------------------------------
        # INCOLOR
        # -------------------------------------------------

        if "C" in colors:

            if not card_colors:
                return True

        # -------------------------------------------------
        # MULTICOLOR
        # -------------------------------------------------

        if "M" in colors:

            if len(card_colors) >= 2:
                return True

        # -------------------------------------------------
        # CORES NORMAIS
        # -------------------------------------------------

        normal_colors = {
            "W",
            "U",
            "B",
            "R",
            "G",
        }

        selected_normal_colors = (
                set(colors)
                & normal_colors
        )

        if card_colors.intersection(
                selected_normal_colors
        ):
            return True

        return False

    # =====================================================
    # OBTER CORES DA CARTA
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

        rarity = (
            self.rarity_filter.currentData()
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

        if rarity is None:
            rarity = "all"

        if set_name is None:
            set_name = "all"

        if sort_mode is None:
            sort_mode = "name_asc"

        # =================================================
        # SALVAR ESTADO
        # =================================================

        self.active_color_filter = color
        self.active_type_filter = card_type
        self.active_rarity_filter = rarity
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
        self.active_rarity_filter = "all"
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

    # =========================================================
    # ATUALIZAR WIDGET DE UMA CARTA
    # =========================================================

    def update_card_widget(
            self,
            card_id,
            new_quantity,
            card_data=None,
    ):
        try:

            card_id = int(
                card_id
            )

            new_quantity = int(
                new_quantity
            )

        except (
                TypeError,
                ValueError,
        ):
            return False

        row_data = self.card_rows.get(
            card_id
        )

        if not row_data:
            print(
                "[COLLECTION] Widget não encontrado:",
                card_id,
            )
            return False

        frame = row_data.get(
            "frame"
        )

        if frame is None:
            print(
                "[COLLECTION] Frame não encontrado:",
                card_id,
            )
            return False

        # =====================================================
        # 1. ATUALIZAR QUANTIDADE
        # =====================================================

        if row_data.get("grid"):

            if hasattr(
                    frame,
                    "set_quantity",
            ):
                frame.set_quantity(
                    new_quantity
                )

        else:

            quantity_widget = row_data.get(
                "quantity_label"
            )

            if quantity_widget is not None:
                quantity_widget.setText(
                    str(new_quantity)
                )

        # =====================================================
        # 2. ATUALIZAR DADOS DA CARTA
        # =====================================================

        if isinstance(
                card_data,
                dict,
        ):

            row_data["card"] = card_data

            print(
                "[COLLECTION] Atualizando imagem da carta:",
                card_id,
            )

            # -------------------------------------------------
            # FRAME DE GRADE
            # -------------------------------------------------

            if row_data.get("grid"):

                if hasattr(
                        frame,
                        "set_card_data",
                ):

                    try:

                        frame.set_card_data(
                            card_data
                        )

                        print(
                            "[COLLECTION] Dados do GridCardFrame atualizados:",
                            card_id,
                        )

                    except Exception as error:

                        print(
                            "[COLLECTION] Erro ao atualizar GridCardFrame:",
                            error,
                        )

            # -------------------------------------------------
            # FRAME DE LISTA
            # -------------------------------------------------

            else:

                self.update_card_image(
                    card_id,
                    card_data,
                )

        return True

    def update_card_image(
            self,
            card_id,
            updated_card,
    ):
        try:

            card_id = int(
                card_id
            )

        except (
                TypeError,
                ValueError,
        ):
            return False

        if not isinstance(
                updated_card,
                dict,
        ):
            return False

        row_data = self.card_rows.get(
            card_id
        )

        if not row_data:
            return False

        frame = row_data.get(
            "frame"
        )

        if frame is None:
            return False

        image_path = (
            updated_card.get(
                "image_path"
            )
        )

        image_url = (
            updated_card.get(
                "image_url"
            )
        )

        print(
            "[COLLECTION] Atualizando widget da imagem:",
            card_id,
            image_path,
        )

        # -------------------------------------------------
        # INVALIDAR CACHE DA CARTA
        # -------------------------------------------------

        if image_path:
            _IMAGE_PIXMAP_CACHE.pop(
                image_path,
                None,
            )

        if image_url:
            _IMAGE_PIXMAP_CACHE.pop(
                image_url,
                None,
            )

        # -------------------------------------------------
        # ATUALIZAR DADOS GUARDADOS NO ROW
        # -------------------------------------------------

        row_data["card"] = updated_card

        print(
            "[COLLECTION] MÉTODOS DO FRAME:",
            [
                name
                for name in dir(frame)
                if "image" in name.lower()
                   or "pixmap" in name.lower()
                   or "thumbnail" in name.lower()
            ],
        )
        # -------------------------------------------------
        # TENTAR ATUALIZAR O WIDGET EXISTENTE
        # -------------------------------------------------

        if hasattr(
                frame,
                "set_card_image",
        ):
            frame.set_card_image(
                image_path,
                image_url,
            )

            return True

        if hasattr(
                frame,
                "set_image",
        ):
            frame.set_image(
                image_path,
            )

            return True

        return False

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

    # =========================================================
    # EVENTOS — CARTA DA COLEÇÃO ALTERADA
    # =========================================================

    # =========================================================
    # EVENTOS — CARTA DA COLEÇÃO ALTERADA
    # =========================================================

    def _on_collection_card_changed(
            self,
            card_id,
            new_quantity,
    ):
        try:

            card_id = int(
                card_id
            )

            new_quantity = int(
                new_quantity
            )

        except (
                TypeError,
                ValueError,
        ):
            return

        if card_id <= 0:
            return

        # -----------------------------------------------------
        # 1. ATUALIZAR DADOS EM MEMÓRIA
        # -----------------------------------------------------

        self.update_quantity_in_filter_sources(
            card_id,
            new_quantity,
        )

        # -----------------------------------------------------
        # 2. ATUALIZAR SOMENTE O WIDGET DA CARTA
        # -----------------------------------------------------

        self.update_card_widget(
            card_id,
            new_quantity,
        )

        # -----------------------------------------------------
        # 3. ATUALIZAR CONTADOR
        # -----------------------------------------------------

        self.update_collection_count(
            self.current_cards
        )

    # =========================================================
    # EVENTOS — DADOS DA CARTA ALTERADOS
    # =========================================================

    def _on_card_data_changed(
            self,
            card_id,
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

        print(
            "[COLLECTION] Dados da carta alterados:",
            card_id,
        )

        try:

            updated_card = get_card_by_id(
                card_id
            )

        except Exception as error:

            print(
                "[COLLECTION] Erro ao recarregar carta:",
                error,
            )

            return

        if not updated_card:
            return

        print(
            "[COLLECTION] IMAGEM ATUALIZADA:",
            updated_card.get("image_path"),
        )

        print(
            "[COLLECTION] URL ATUALIZADA:",
            updated_card.get("image_url"),
        )

        self.update_quantity_in_filter_sources(
            card_id,
            updated_card.get(
                "quantity",
                0,
            ),
        )

        self.update_card_widget(
            card_id,
            updated_card.get(
                "quantity",
                0,
            ),
            updated_card,
        )

    # =====================================================
    # DISPLAY
    # =====================================================

    def display_cards(
            self,
            cards,
    ):

        print(
            "[COLLECTION DISPLAY]",
            len(cards),
            "layout=",
            self.current_layout,
        )

        if cards is None:
            cards = []

        # =========================================================
        # INVALIDAR RENDERIZAÇÃO ANTERIOR
        # =========================================================

        self._grid_generation += 1

        generation = self._grid_generation

        # Cancela qualquer continuação pendente da grade anterior.
        self._grid_render_timer.stop()

        self._grid_rendering_pending = False
        self._grid_render_cards = []
        self._grid_render_index = 0
        self._grid_render_layout = None
        self._grid_render_generation = generation

        self.current_cards = list(
            cards
        )

        self.card_rows.clear()

        # =========================================================
        # MOSTRAR LOADING
        # =========================================================

        self._show_collection_loading(
            "Preparando suas cartas..."
        )

        self.rebuilding_grid = True

        self.cards_container.setUpdatesEnabled(
            False
        )

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

            if not self._grid_rendering_pending:
                self.cards_container.setUpdatesEnabled(
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
                card_printings = card[16] if len(card) > 16 else None
                preferred_language = card[17] if len(card) > 17 else None
                preferred_variant = card[18] if len(card) > 18 else None
                preferred_finish = card[19] if len(card) > 19 else None
                preferred_image = card[20] if len(card) > 20 else None
                preferred_face = card[21] if len(card) > 21 else 0
                favorite = card[22] if len(card) > 22 else 0
                custom_tags = card[23] if len(card) > 23 else None
                last_view = card[24] if len(card) > 24 else None
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
                card_printings,
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                preferred_face,
                favorite,
                custom_tags,
                last_view,
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

    def card_matches_type(
            self,
            card,
            type_filter,
    ):
        if (
                not type_filter
                or type_filter == "all"
                or type_filter == []
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

        # -------------------------------------------------
        # GARANTIR LISTA
        # -------------------------------------------------

        if isinstance(
                type_filter,
                str,
        ):
            type_filter = [
                type_filter,
            ]

        # -------------------------------------------------
        # VERIFICAR QUALQUER TIPO SELECIONADO
        # -------------------------------------------------

        for selected_type in type_filter:

            accepted_types = type_map.get(
                selected_type,
            )

            if not accepted_types:
                if (
                        str(selected_type)
                                .strip()
                                .lower()
                        in type_line
                ):
                    return True

                continue

            if any(
                    accepted_type in type_line
                    for accepted_type
                    in accepted_types
            ):
                return True

        return False

    def card_matches_set(
            self,
            card,
            set_filter,
    ):
        if (
                not set_filter
                or set_filter == "all"
                or set_filter == []
        ):
            return True

        if not card or len(card) <= 4:
            return False

        card_set = str(
            card[4]
            if len(card) > 4
            else ""
        ).strip().lower()

        if not card_set:
            return False

        if isinstance(
                set_filter,
                str,
        ):
            set_filter = [
                set_filter,
            ]

        selected_sets = {
            str(value)
            .strip()
            .lower()
            for value
            in set_filter
        }

        return card_set in selected_sets

    def card_matches_supertype(
            self,
            card,
            supertype_filter,
    ):
        if (
                not supertype_filter
                or supertype_filter == "all"
                or supertype_filter == []
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

        # -------------------------------------------------
        # GARANTIR LISTA
        # -------------------------------------------------

        if isinstance(
                supertype_filter,
                str,
        ):
            supertype_filter = [
                supertype_filter,
            ]

        # -------------------------------------------------
        # MAPA DE SUPERTIPOS
        # -------------------------------------------------

        supertype_map = {
            "legendary": (
                "lendária",
                "legendary",
            ),

            "basic": (
                "básica",
                "basic",
            ),

            "snow": (
                "nevada",
                "snow",
            ),

            "world": (
                "mundo",
                "world",
            ),
        }

        # -------------------------------------------------
        # VERIFICAR QUALQUER SUPERTIPO
        # -------------------------------------------------

        for selected_supertype in supertype_filter:

            accepted_values = (
                supertype_map.get(
                    selected_supertype,
                    (),
                )
            )

            if not accepted_values:
                continue

            if any(
                    value in type_line
                    for value
                    in accepted_values
            ):
                return True

        return False

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

    def card_matches_rarity(
            self,
            card,
            rarity_filter,
    ):
        if (
                not rarity_filter
                or rarity_filter == "all"
                or rarity_filter == []
        ):
            return True

        if not card:
            return False

        try:
            rarity = str(
                card[-1] or ""
            ).strip().lower()

        except (
                TypeError,
                IndexError,
        ):
            return False

        if isinstance(
                rarity_filter,
                str,
        ):
            rarity_filter = [
                rarity_filter,
            ]

        return (
                rarity
                in [
                    str(value)
                .strip()
                .lower()
                    for value
                    in rarity_filter
                ]
        )

    def apply_collection_filters(
            self,
    ):

        # =================================================
        # VERIFICAR FILTROS EXISTENTES
        # =================================================

        if not hasattr(
                self,
                "color_filter",
        ):
            return

        if not hasattr(
                self,
                "type_filter",
        ):
            return

        if not hasattr(
                self,
                "supertype_filter",
        ):
            return

        if not hasattr(
                self,
                "rarity_filter",
        ):
            return

        if not hasattr(
                self,
                "set_filter",
        ):
            return

        if not hasattr(
                self,
                "sort_filter",
        ):
            return

        # =================================================
        # OBTER FILTROS ATUAIS
        # =================================================

        color = (
            self.color_filter.get_selected_values()
        )

        card_type = (
            self.type_filter.get_selected_values()
        )

        supertype = (
            self.supertype_filter.get_selected_values()
        )

        rarity = (
            self.rarity_filter.get_selected_values()
        )

        set_name = (
            self.set_filter.get_selected_values()
        )

        sort_mode = (
                self.sort_filter.currentData()
                or "name_asc"
        )

        # =================================================
        # SALVAR FILTROS ATIVOS
        # =================================================

        self.active_color_filter = (
            color
        )

        self.active_type_filter = (
            card_type
        )

        self.active_supertype_filter = (
            supertype
        )

        self.active_rarity_filter = (
            rarity
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
        # APLICAR FILTROS
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
            # SUPERTIPO
            # -------------------------------------------------

            if not self.card_matches_supertype(
                    card,
                    supertype,
            ):
                continue

            # -------------------------------------------------
            # RARIDADE
            # -------------------------------------------------

            if not self.card_matches_rarity(
                    card,
                    rarity,
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

            # -------------------------------------------------
            # CARTA APROVADA
            # -------------------------------------------------

            filtered.append(
                card
            )

        # =================================================
        # ORDENAÇÃO
        # =================================================

        filtered = self.sort_collection_cards(
            filtered,
            sort_mode,
        )

        # =================================================
        # CONTADOR
        # =================================================

        self.update_collection_count(
            filtered
        )

        # =================================================
        # ATUALIZAR CARTAS ATUAIS
        # =================================================

        self.current_cards = list(
            filtered
        )

        # =================================================
        # MOSTRAR CARTAS
        # =================================================

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

        self.supertype_filter.blockSignals(
            True
        )

        self.rarity_filter.blockSignals(
            True
        )

        self.set_filter.blockSignals(
            True
        )

        self.sort_filter.blockSignals(
            True
        )

        self.color_filter.clear_selection()

        self.type_filter.clear_selection()

        self.supertype_filter.clear_selection()

        self.rarity_filter.clear_selection()

        self.set_filter.clear_selection()

        self.sort_filter.setCurrentIndex(
            0
        )

        self.color_filter.blockSignals(
            False
        )

        self.type_filter.blockSignals(
            False
        )

        self.supertype_filter.blockSignals(
            False
        )

        self.rarity_filter.blockSignals(
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

        # -------------------------------------------------
        # EDIÇÕES EXISTENTES NA COLEÇÃO
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PRESERVAR SELEÇÃO ATUAL
        # -------------------------------------------------

        current = (
            self.set_filter.get_selected_values()
        )

        # -------------------------------------------------
        # ATUALIZAR OPÇÕES
        # -------------------------------------------------

        self.set_filter.set_options(
            [
                (
                    set_name,
                    set_name,
                )
                for set_name
                in sets
            ]
        )

        # -------------------------------------------------
        # RESTAURAR SELEÇÕES QUE AINDA EXISTEM
        # -------------------------------------------------

        valid_current = [
            value
            for value
            in current
            if value in sets
        ]

        self.set_filter.set_selected_values(
            valid_current
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
            "collection/supertype_filter",
            self.active_supertype_filter,
        )

        self.settings.setValue(
            "collection/rarity_filter",
            self.active_rarity_filter,
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
            [],
        )

        card_type = self.settings.value(
            "collection/type_filter",
            [],
        )

        supertype = self.settings.value(
            "collection/supertype_filter",
            [],
        )

        rarity = self.settings.value(
            "collection/rarity_filter",
            [],
        )

        set_name = self.settings.value(
            "collection/set_filter",
            [],
        )

        sort_mode = self.settings.value(
            "collection/sort_filter",
            "name_asc",
            type=str,
        )

        # -------------------------------------------------
        # GARANTIR LISTAS
        # -------------------------------------------------

        if isinstance(
                color,
                str,
        ):
            if color == "all":
                color = []
            else:
                color = [color]

        if isinstance(
                card_type,
                str,
        ):
            if card_type == "all":
                card_type = []
            else:
                card_type = [card_type]

        if isinstance(
                supertype,
                str,
        ):
            if supertype == "all":
                supertype = []
            else:
                supertype = [supertype]

        if isinstance(
                rarity,
                str,
        ):
            if rarity == "all":
                rarity = []
            else:
                rarity = [rarity]

        if isinstance(
                set_name,
                str,
        ):
            if set_name == "all":
                set_name = []
            else:
                set_name = [set_name]

        # -------------------------------------------------
        # BLOQUEAR SINAIS
        # -------------------------------------------------

        self.color_filter.blockSignals(
            True
        )

        self.type_filter.blockSignals(
            True
        )

        self.supertype_filter.blockSignals(
            True
        )

        self.rarity_filter.blockSignals(
            True
        )

        self.set_filter.blockSignals(
            True
        )

        self.sort_filter.blockSignals(
            True
        )

        # -------------------------------------------------
        # RESTAURAR FILTROS
        # -------------------------------------------------

        self.color_filter.set_selected_values(
            color
        )

        self.type_filter.set_selected_values(
            card_type
        )

        self.supertype_filter.set_selected_values(
            supertype
        )

        self.rarity_filter.set_selected_values(
            rarity
        )

        self.set_filter.set_selected_values(
            set_name
        )

        # -------------------------------------------------
        # RESTAURAR ORDENAÇÃO
        # -------------------------------------------------

        sort_index = (
            self.sort_filter.findData(
                sort_mode
            )
        )

        if sort_index >= 0:
            self.sort_filter.setCurrentIndex(
                sort_index
            )

        # -------------------------------------------------
        # DESBLOQUEAR SINAIS
        # -------------------------------------------------

        self.color_filter.blockSignals(
            False
        )

        self.type_filter.blockSignals(
            False
        )

        self.supertype_filter.blockSignals(
            False
        )

        self.rarity_filter.blockSignals(
            False
        )

        self.set_filter.blockSignals(
            False
        )

        self.sort_filter.blockSignals(
            False
        )

        # -------------------------------------------------
        # ATUALIZAR VALORES ATIVOS
        # -------------------------------------------------

        self.active_color_filter = (
            self.color_filter.get_selected_values()
        )

        self.active_type_filter = (
            self.type_filter.get_selected_values()
        )

        self.active_supertype_filter = (
            self.supertype_filter.get_selected_values()
        )

        self.active_rarity_filter = (
            self.rarity_filter.get_selected_values()
        )

        self.active_set_filter = (
            self.set_filter.get_selected_values()
        )

        self.active_sort = (
                self.sort_filter.currentData()
                or "name_asc"
        )

    # =========================================================
    # VIRTUALIZAÇÃO — SCROLL
    # =========================================================

    def _on_virtual_grid_scroll(
            self,
            value,
    ):
        """
        Atualiza a grade virtual quando o usuário rola.

        Não reconstruímos imediatamente a cada pequeno evento.
        Usamos um QTimer de 0 ms para deixar o Qt terminar
        o evento atual antes de atualizar os cards.
        """

        if not self._virtual_grid_enabled:
            return

        if self.current_layout != "grid":
            return

        if not self._virtual_grid_cards:
            return

        if value == self._virtual_grid_last_scroll_value:
            return

        self._virtual_grid_last_scroll_value = value

        if self._virtual_grid_update_pending:
            return

        self._virtual_grid_update_pending = True

        QTimer.singleShot(
            0,
            self._update_virtual_grid,
        )

    # =========================================================
    # VIRTUALIZAÇÃO — ATUALIZAR GRADE
    # =========================================================

    def _update_virtual_grid(
            self,
    ):
        """
        Calcula quais linhas estão visíveis e atualiza
        somente os widgets necessários.
        """

        self._virtual_grid_update_pending = False

        if not self._virtual_grid_enabled:
            return

        if self.current_layout != "grid":
            return

        cards = self._virtual_grid_cards

        if not cards:
            return

        viewport = (
            self.scroll_area.viewport()
        )

        viewport_height = viewport.height()

        if viewport_height <= 0:
            return

        # -----------------------------------------------------
        # ALTURA APROXIMADA DE UMA CARTA
        # -----------------------------------------------------

        card_height = 300
        vertical_spacing = 12

        row_height = (
                card_height
                + vertical_spacing
        )

        # -----------------------------------------------------
        # POSIÇÃO DO SCROLL
        # -----------------------------------------------------

        scroll_value = (
            self.scroll_area
            .verticalScrollBar()
            .value()
        )

        # -----------------------------------------------------
        # PRIMEIRA LINHA VISÍVEL
        # -----------------------------------------------------

        first_visible_row = max(
            0,
            int(
                scroll_value
                / row_height
            ),
        )

        # -----------------------------------------------------
        # ÚLTIMA LINHA VISÍVEL
        # -----------------------------------------------------

        visible_rows = max(
            1,
            int(
                viewport_height
                / row_height
            )
            + 1,
        )

        first_row = max(
            0,
            first_visible_row
            - self._virtual_grid_buffer_rows,
        )

        last_row = (
                first_visible_row
                + visible_rows
                + self._virtual_grid_buffer_rows
        )

        # -----------------------------------------------------
        # LIMITAR
        # -----------------------------------------------------

        total_cards = len(cards)

        total_rows = int(
            (
                    total_cards
                    + self._virtual_grid_columns
                    - 1
            )
            /
            self._virtual_grid_columns
        )

        last_row = min(
            last_row,
            total_rows,
        )

        # -----------------------------------------------------
        # SE A LINHA NÃO MUDOU, NÃO FAZER NADA
        # -----------------------------------------------------

        if (
                first_row
                == self._virtual_grid_first_row
        ):
            return

        self._virtual_grid_first_row = (
            first_row
        )

        # -----------------------------------------------------
        # CARTAS QUE DEVEM EXISTIR
        # -----------------------------------------------------

        start_index = (
                first_row
                * self._virtual_grid_columns
        )

        end_index = min(
            last_row
            * self._virtual_grid_columns,
            total_cards,
        )

        visible_cards = cards[
                        start_index:end_index
                        ]

        # -----------------------------------------------------
        # RENDERIZAR
        # -----------------------------------------------------

        self._render_virtual_grid_cards(
            visible_cards,
            start_index,
        )

    # =========================================================
    # VIRTUALIZAÇÃO — CONFIGURAR CARD
    # =========================================================

    def _configure_virtual_card(
            self,
            frame,
            card,
    ):
        """
        Reutiliza um GridCardFrame existente para representar
        uma nova carta.
        """

        if frame is None:
            return

        if not card:
            frame.hide()
            return

        try:

            card_id = int(
                card[0]
            )

        except (
                TypeError,
                ValueError,
        ):

            frame.hide()
            return

        if card_id <= 0:
            frame.hide()
            return

        name = (
            card[1]
            if len(card) > 1
            else ""
        )

        printed_name = (
            card[2]
            if len(card) > 2
            else None
        )

        lang = (
            card[3]
            if len(card) > 3
            else None
        )

        set_name = (
            card[4]
            if len(card) > 4
            else None
        )

        collector_number = (
            card[5]
            if len(card) > 5
            else None
        )

        mana_cost = (
            card[6]
            if len(card) > 6
            else None
        )

        type_line = (
            card[7]
            if len(card) > 7
            else None
        )

        oracle_text = (
            card[8]
            if len(card) > 8
            else None
        )

        image_url = (
            card[9]
            if len(card) > 9
            else None
        )

        quantity = (
            card[10]
            if len(card) > 10
            else 0
        )

        image_path = (
            card[11]
            if len(card) > 11
            else None
        )

        power = (
            card[12]
            if len(card) > 12
            else None
        )

        toughness = (
            card[13]
            if len(card) > 13
            else None
        )

        created_at = (
            card[14]
            if len(card) > 14
            else None
        )

        card_faces = (
            card[15]
            if len(card) > 15
            else None
        )

        card_printings = (
            card[16]
            if len(card) > 16
            else None
        )

        preferred_language = (
            card[17]
            if len(card) > 17
            else None
        )

        preferred_variant = (
            card[18]
            if len(card) > 18
            else None
        )

        preferred_finish = (
            card[19]
            if len(card) > 19
            else None
        )

        preferred_image = (
            card[20]
            if len(card) > 20
            else None
        )

        preferred_face = (
            card[21]
            if len(card) > 21
            else 0
        )

        favorite = (
            card[22]
            if len(card) > 22
            else 0
        )

        custom_tags = (
            card[23]
            if len(card) > 23
            else None
        )

        last_view = (
            card[24]
            if len(card) > 24
            else None
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
            "created_at": created_at,
            "card_faces": card_faces,
            "card_printings": card_printings,
            "preferred_language": preferred_language,
            "preferred_variant": preferred_variant,
            "preferred_finish": preferred_finish,
            "preferred_image": preferred_image,
            "preferred_face": preferred_face,
            "favorite": favorite,
            "custom_tags": custom_tags,
            "last_view": last_view,
        }

        # -----------------------------------------------------
        # DADOS ASSOCIADOS AO WIDGET
        # -----------------------------------------------------

        frame._virtual_card_id = card_id
        frame._virtual_card_data = card_data

        # -----------------------------------------------------
        # TAMANHO
        # -----------------------------------------------------

        available_width = (
            self.scroll_area
            .viewport()
            .width()
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

        frame.set_card_width(
            card_width
        )

        frame.setToolTip(
            name or ""
        )

        frame.set_quantity(
            quantity
        )

        # -----------------------------------------------------
        # IMAGEM
        # -----------------------------------------------------

        pixmap = None

        if image_path:

            local_path = Path(
                image_path
            )

            if local_path.exists():

                cache_key = str(
                    local_path
                )

                pixmap = (
                    self.image_cache.get(
                        cache_key
                    )
                )

                if (
                        pixmap is None
                        or pixmap.isNull()
                ):

                    try:

                        pixmap = QPixmap(
                            str(local_path)
                        )

                        if not pixmap.isNull():
                            self.image_cache[
                                cache_key
                            ] = pixmap

                            _cleanup_image_cache()

                    except Exception:
                        pixmap = None

        if (
                pixmap
                and not pixmap.isNull()
        ):

            self.set_grid_thumbnail(
                frame.image_label,
                pixmap,
            )

        else:

            self.set_grid_thumbnail(
                frame.image_label,
                None,
            )

        # -----------------------------------------------------
        # MOSTRAR
        # -----------------------------------------------------

        frame.show()

    # =========================================================
    # VIRTUALIZAÇÃO — CRIAR WIDGETS
    # =========================================================

    def _create_virtual_grid_widgets(
            self,
            count,
            card_width,
    ):
        """
        Cria somente a quantidade de widgets necessária
        para a área visível da grade.
        """

        # -----------------------------------------------------
        # NÃO CRIAR NOVAMENTE SE JÁ TEMOS O SUFICIENTE
        # -----------------------------------------------------

        while len(
                self._virtual_grid_widgets
        ) < count:
            frame = GridCardFrame()

            frame.set_card_width(
                card_width
            )

            frame._virtual_card_id = None
            frame._virtual_card_data = None

            # -------------------------------------------------
            # CLIQUE
            # -------------------------------------------------

            frame.clicked.connect(
                lambda
                    cid=None,
                    widget=frame:
                self._virtual_card_clicked(
                    widget
                )
            )

            # -------------------------------------------------
            # DUPLO CLIQUE
            # -------------------------------------------------

            frame.doubleClicked.connect(
                lambda
                    widget=frame:
                self._virtual_card_double_clicked(
                    widget
                )
            )

            # -------------------------------------------------
            # QUANTIDADE +
            # -------------------------------------------------

            frame.plus_button.clicked.connect(
                lambda
                    checked=False,
                    widget=frame:
                self._virtual_change_quantity(
                    widget,
                    1,
                )
            )

            # -------------------------------------------------
            # QUANTIDADE -
            # -------------------------------------------------

            frame.minus_button.clicked.connect(
                lambda
                    checked=False,
                    widget=frame:
                self._virtual_change_quantity(
                    widget,
                    -1,
                )
            )

            # -------------------------------------------------
            # QUANTIDADE MANUAL
            # -------------------------------------------------

            frame.control_quantity.editingFinished.connect(
                lambda
                    widget=frame:
                self._virtual_set_quantity(
                    widget
                )
            )

            self._virtual_grid_widgets.append(
                frame
            )

    # =====================================================
    # CALCULAR GEOMETRIA DA GRADE
    # =====================================================

    def _calculate_grid_geometry(
            self,
    ):
        """
        Calcula uma grade que sempre cabe dentro
        da largura disponível do viewport.

        Retorna:

            (quantidade_de_colunas, largura_da_carta)
        """

        viewport = (
            self.scroll_area.viewport()
        )

        if viewport is None:
            return (
                1,
                180,
            )

        available_width = (
            viewport.width()
        )

        if available_width <= 0:
            return (
                1,
                180,
            )

        # =====================================================
        # CONFIGURAÇÃO
        # =====================================================

        spacing = 12

        min_card_width = 160
        max_card_width = 210

        # =====================================================
        # CALCULAR MÁXIMO DE COLUNAS
        # =====================================================

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

        # =====================================================
        # GARANTIR QUE A LARGURA REAL CABE
        # =====================================================

        while columns > 1:

            total_spacing = (
                                    columns - 1
                            ) * spacing

            card_width = int(
                (
                        available_width
                        - total_spacing
                )
                /
                columns
            )

            if card_width >= min_card_width:
                break

            columns -= 1

        # =====================================================
        # LARGURA FINAL
        # =====================================================

        total_spacing = (
                                columns - 1
                        ) * spacing

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
            max_card_width,
            card_width,
        )

        return (
            columns,
            card_width,
        )

    # =========================================================
    # DISPLAY — GRADE
    # =========================================================

    def display_cards_grid(
            self,
            cards,
            generation,
            start_index=0,
            grid_layout=None,
    ):

        # =====================================================
        # VALIDAR GERAÇÃO
        # =====================================================

        if generation != self._grid_generation:
            return
        # =====================================================
        # GARANTIR QUE A GRADE CONTINUE OCULTA DURANTE O LOTE
        # =====================================================

        self.cards_container.setUpdatesEnabled(
            False
        )

        # =====================================================
        # PREPARAR LISTA
        # =====================================================

        if cards is None:
            cards = []

        if start_index == 0:
            cards = list(cards)

        # =====================================================
        # PRIMEIRA EXECUÇÃO
        # =====================================================

        if start_index == 0:
            self._grid_render_cards = cards
            self._grid_render_index = 0
            self._grid_render_generation = generation
            self._grid_rendering_pending = True

        # =====================================================
        # VALIDAR ESTADO
        # =====================================================

        if (
                self._grid_render_generation
                != generation
        ):
            return

        cards = self._grid_render_cards

        # =========================================================
        # COLEÇÃO VAZIA
        # =========================================================

        if not cards:
            self._grid_render_index = 0

            self._grid_rendering_pending = False

            self._grid_render_layout = None

            self.cards_container.setUpdatesEnabled(
                True
            )

            self.cards_container.update()

            self.scroll_area.viewport().update()

            self._hide_collection_loading()

            self.scroll_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )

            return
        # =====================================================
        # CRIAR GRID
        # =====================================================

        if grid_layout is None:
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

            self._grid_render_layout = grid_layout

        # =====================================================
        # CALCULAR TAMANHO
        # =====================================================

        columns, card_width = (
            self._calculate_grid_geometry()
        )

        spacing = 12

        self._grid_columns = columns

        # =====================================================
        # DEFINIR LOTE
        # =====================================================

        batch_size = (
            self._grid_render_batch_size
        )

        end_index = min(
            start_index + batch_size,
            len(cards),
        )

        # =====================================================
        # RENDERIZAR LOTE
        # =====================================================

        for index in range(
                start_index,
                end_index,
        ):

            card = cards[index]

            try:

                card_id = (
                    card[0]
                    if len(card) > 0
                    else None
                )

                name = (
                    card[1]
                    if len(card) > 1
                    else ""
                )

                printed_name = (
                    card[2]
                    if len(card) > 2
                    else None
                )

                lang = (
                    card[3]
                    if len(card) > 3
                    else None
                )

                set_name = (
                    card[4]
                    if len(card) > 4
                    else None
                )

                collector_number = (
                    card[5]
                    if len(card) > 5
                    else None
                )

                mana_cost = (
                    card[6]
                    if len(card) > 6
                    else None
                )

                type_line = (
                    card[7]
                    if len(card) > 7
                    else None
                )

                oracle_text = (
                    card[8]
                    if len(card) > 8
                    else None
                )

                image_url = (
                    card[9]
                    if len(card) > 9
                    else None
                )

                quantity = (
                    card[10]
                    if len(card) > 10
                    else 0
                )

                image_path = (
                    card[11]
                    if len(card) > 11
                    else None
                )

                power = (
                    card[12]
                    if len(card) > 12
                    else None
                )

                toughness = (
                    card[13]
                    if len(card) > 13
                    else None
                )

                created_at = (
                    card[14]
                    if len(card) > 14
                    else None
                )

                card_faces = (
                    card[15]
                    if len(card) > 15
                    else None
                )

                card_printings = (
                    card[16]
                    if len(card) > 16
                    else None
                )

                preferred_language = (
                    card[17]
                    if len(card) > 17
                    else None
                )

                preferred_variant = (
                    card[18]
                    if len(card) > 18
                    else None
                )

                preferred_finish = (
                    card[19]
                    if len(card) > 19
                    else None
                )

                preferred_image = (
                    card[20]
                    if len(card) > 20
                    else None
                )

                preferred_face = (
                    card[21]
                    if len(card) > 21
                    else 0
                )

                favorite = (
                    card[22]
                    if len(card) > 22
                    else 0
                )

                custom_tags = (
                    card[23]
                    if len(card) > 23
                    else None
                )

                last_view = (
                    card[24]
                    if len(card) > 24
                    else None
                )

            except (
                    IndexError,
                    TypeError,
            ):
                continue

            # =================================================
            # VALIDAR ID
            # =================================================

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

            # =================================================
            # DADOS DA CARTA
            # =================================================

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
                "card_printings": card_printings,
                "preferred_language": preferred_language,
                "preferred_variant": preferred_variant,
                "preferred_finish": preferred_finish,
                "preferred_image": preferred_image,
                "preferred_face": preferred_face,
                "favorite": favorite,
                "custom_tags": custom_tags,
                "last_view": last_view,
            }

            # =================================================
            # CRIAR FRAME
            # =================================================

            frame = GridCardFrame()

            frame.set_card_width(
                card_width
            )

            frame.setToolTip(
                name or ""
            )

            # =================================================
            # DUPLO CLIQUE
            # =================================================

            frame.doubleClicked.connect(
                lambda card=card_data:
                self.show_card_details(
                    card
                )
            )

            # =================================================
            # CLIQUE
            # =================================================

            frame.clicked.connect(
                lambda cid=card_id:
                self.select_collection_card(
                    cid
                )
            )

            # =================================================
            # MENU DE CONTEXTO
            # =================================================

            frame.setContextMenuPolicy(
                Qt.ContextMenuPolicy.CustomContextMenu
            )

            frame.customContextMenuRequested.connect(
                lambda position,
                       cid=card_id,
                       card=card_data,
                       widget=frame:
                self.show_card_context_menu(
                    cid,
                    card,
                    widget,
                    position,
                )
            )

            # =================================================
            # QUANTIDADE
            # =================================================

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

            # =================================================
            # REGISTRAR CARD
            # =================================================

            self.card_rows[card_id] = {
                "frame": frame,
                "grid": True,
            }

            # =================================================
            # IMAGEM LOCAL
            # =================================================

            local_path = None
            pixmap = None

            if image_path:

                local_path = Path(
                    image_path
                )

                if local_path.exists():

                    cache_key = str(
                        local_path
                    )

                    pixmap = (
                        self.image_cache.get(
                            cache_key
                        )
                    )

                    if (
                            pixmap is None
                            or pixmap.isNull()
                    ):

                        try:

                            pixmap = QPixmap(
                                str(local_path)
                            )

                            if not pixmap.isNull():
                                self.image_cache[
                                    cache_key
                                ] = pixmap

                                _cleanup_image_cache()

                        except Exception:
                            pixmap = None

            # =================================================
            # APLICAR IMAGEM
            # =================================================

            if (
                    pixmap
                    and not pixmap.isNull()
            ):

                self.set_grid_thumbnail(
                    frame.image_label,
                    pixmap,
                )

            else:

                # -------------------------------------------------
                # PLACEHOLDER
                # -------------------------------------------------

                self.set_grid_thumbnail(
                    frame.image_label,
                    None,
                )
            # =================================================
            # POSIÇÃO NO GRID
            # =================================================

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
                Qt.AlignmentFlag.AlignCenter,
            )

            # =================================================
            # DOWNLOAD ASSÍNCRONO
            # =================================================

            if (
                    not (
                            pixmap
                            and not pixmap.isNull()
                    )
                    and image_url
            ):

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

        # =====================================================
        # CONFIGURAR COLUNAS DO GRID
        # =====================================================

        if start_index == 0:

            for column in range(columns):
                grid_layout.setColumnStretch(
                    column,
                    0,
                )

            grid_layout.setAlignment(
                Qt.AlignmentFlag.AlignTop
                |
                Qt.AlignmentFlag.AlignLeft
            )

        # =====================================================
        # PRIMEIRO LOTE
        # =====================================================

        if start_index == 0:
            self.cards_layout.addLayout(
                grid_layout
            )

        # =====================================================
        # VERIFICAR SE TERMINOU
        # =====================================================

        if end_index >= len(cards):
            self._grid_render_index = end_index

            self._grid_rendering_pending = False

            self._grid_render_layout = None

            # =====================================================
            # GRADE TERMINOU
            # =====================================================

            self.cards_container.setUpdatesEnabled(
                True
            )

            # =====================================================
            # ATUALIZAÇÃO FINAL DA GRADE
            # =====================================================

            self.cards_container.update()

            self.scroll_area.viewport().update()

            # =====================================================
            # LOADING TERMINOU
            # =====================================================

            self._hide_collection_loading()

            # =====================================================
            # LIBERAR SCROLL
            # =====================================================

            self.scroll_area.setVerticalScrollBarPolicy(
                Qt.ScrollBarPolicy.ScrollBarAsNeeded
            )

            return  # =====================================================
        # AGENDAR PRÓXIMO LOTE
        # =====================================================

        self._grid_render_index = end_index
        self._grid_rendering_pending = True

        next_index = end_index

        QTimer.singleShot(
            0,
            lambda:
            self.display_cards_grid(
                self._grid_render_cards,
                generation,
                next_index,
                grid_layout,
            )
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
            card_printings=None,
            preferred_language=None,
            preferred_variant=None,
            preferred_finish=None,
            preferred_image=None,
            preferred_face=0,
            favorite=0,
            custom_tags=None,
            last_view=None,
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
            "card_printings": card_printings,
            "preferred_language": preferred_language,
            "preferred_variant": preferred_variant,
            "preferred_finish": preferred_finish,
            "preferred_image": preferred_image,
            "preferred_face": preferred_face,
            "favorite": favorite,
            "custom_tags": custom_tags,
            "last_view": last_view,
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

            if local_path.exists() and local_path.stat().st_size > 2:
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

        label.update()

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

        print(
            "[GRID] Aplicando pixmap:",
            width,
            "x",
            height,
        )

        label.clear()
        label.setPixmap(scaled)

    # =====================================================
    # MINIATURA — GRADE
    # =====================================================

    # =====================================================
    # MINIATURA — GRADE
    # =====================================================

    def set_grid_thumbnail(
            self,
            label,
            pixmap,
    ):
        """
        Aplica uma imagem na grade usando cache de thumbnails.

        O QPixmap original continua no cache de imagens.
        A versão reduzida para a grade fica em um segundo cache.
        """

        # =====================================================
        # VALIDAR PIXMAP
        # =====================================================

        if (
                pixmap is None
                or pixmap.isNull()
        ):

            label.setText("")

            if CARD_ICON_PATH.exists():

                placeholder = QPixmap(
                    str(CARD_ICON_PATH)
                )

                if not placeholder.isNull():

                    width = label.width()

                    height = label.height()

                    if width <= 0:
                        width = 160

                    if height <= 0:
                        height = round(
                            width * 88 / 63
                        )

                    cache_key = (
                        "__placeholder__"
                        f"_{width}"
                        f"x{height}"
                    )

                    cached = (
                        _GRID_THUMBNAIL_CACHE.get(
                            cache_key
                        )
                    )

                    if (
                            cached is None
                            or cached.isNull()
                    ):
                        cached = placeholder.scaled(
                            width,
                            height,
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                        _GRID_THUMBNAIL_CACHE[
                            cache_key
                        ] = cached

                        _cleanup_grid_thumbnail_cache()

                    label.setPixmap(
                        cached
                    )

            return

        # =====================================================
        # DIMENSÕES
        # =====================================================

        width = label.width()

        height = label.height()

        if width <= 0:
            width = 160

        if height <= 0:
            height = round(
                width * 88 / 63
            )

        # =====================================================
        # CHAVE DO CACHE
        # =====================================================

        cache_key = (
            f"{id(pixmap)}"
            f"_{width}"
            f"x{height}"
        )

        # =====================================================
        # PROCURAR THUMBNAIL
        # =====================================================

        scaled = (
            _GRID_THUMBNAIL_CACHE.get(
                cache_key
            )
        )

        # =====================================================
        # GERAR SOMENTE SE NÃO EXISTIR
        # =====================================================

        if (
                scaled is None
                or scaled.isNull()
        ):
            scaled = pixmap.scaled(
                width,
                height,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            _GRID_THUMBNAIL_CACHE[
                cache_key
            ] = scaled

            _cleanup_grid_thumbnail_cache()

        # =====================================================
        # APLICAR
        # =====================================================

        label.setText("")

        label.setPixmap(
            scaled
        )

    # =====================================================
    # DETALHES DA CARTA
    # =====================================================

    def select_collection_card(
            self,
            card_id,
    ):
        try:
            card_id = int(card_id)
        except (
                TypeError,
                ValueError,
        ):
            return

        if self.selected_card_id == card_id:
            return

        previous_id = self.selected_card_id
        self.selected_card_id = card_id

        for current_id in (
                previous_id,
                card_id,
        ):
            if not current_id:
                continue

            row_data = self.card_rows.get(
                current_id
            )

            if not row_data:
                continue

            frame = row_data.get(
                "frame"
            )

            if not frame:
                continue

            frame.setProperty(
                "selected",
                current_id == card_id,
            )
            frame.style().unpolish(frame)
            frame.style().polish(frame)
            frame.update()

    def show_card_context_menu(
            self,
            card_id,
            card,
            widget,
            position,
    ):
        self.select_collection_card(
            card_id
        )

        menu = QMenu(
            self
        )
        menu.setObjectName(
            "CardContextMenu"
        )

        add_action = menu.addAction(
            "Adicionar copia"
        )
        remove_action = menu.addAction(
            "Remover copia"
        )
        menu.addSeparator()
        details_action = menu.addAction(
            "Abrir detalhes"
        )
        scryfall_action = menu.addAction(
            "Abrir no Scryfall"
        )
        menu.addSeparator()
        copy_name_action = menu.addAction(
            "Copiar nome"
        )
        copy_oracle_action = menu.addAction(
            "Copiar Oracle"
        )

        chosen = menu.exec(
            widget.mapToGlobal(position)
        )

        if chosen is None:
            return

        if chosen == add_action:
            self.change_card_quantity(
                card_id,
                1,
            )
            return

        if chosen == remove_action:
            self.change_card_quantity(
                card_id,
                -1,
            )
            return

        if chosen == details_action:
            self.show_card_details(
                card
            )
            return

        if chosen == scryfall_action:
            name = str(
                card.get("name")
                or ""
            ).strip()

            if name:
                webbrowser.open(
                    "https://scryfall.com/search?q="
                    + quote_plus(f'!"{name}"')
                )
            return

        if chosen == copy_name_action:
            QApplication.clipboard().setText(
                str(card.get("name") or "")
            )
            return

        if chosen == copy_oracle_action:
            QApplication.clipboard().setText(
                str(card.get("oracle_text") or "")
            )
            return

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

        # =========================================================
        # AVISAR A APLICAÇÃO
        # =========================================================

        app_events.collection_card_changed.emit(
            card_id,
            new_quantity,
        )

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

        # =========================================================
        # AVISAR A APLICAÇÃO
        # =========================================================

        app_events.collection_card_changed.emit(
            card_id,
            new_quantity,
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



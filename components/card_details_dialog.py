import hashlib
import json
from pathlib import Path

import requests

from PySide6.QtCore import (
    Qt,
    QObject,
    Signal,
    QRunnable,
    QThreadPool,
    QTimer,
)
from PySide6.QtGui import (
    QPixmap,
    QGuiApplication,
)
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

from database import (
    get_card_by_id,
    update_card_printing,
)

from services.scryfall import (
    get_card_by_name,
    get_card_printings,
)
from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from services.app_events import (
    app_events,
)

from ui.theme import DARK_THEME



BASE_DIR = Path(__file__).resolve().parent.parent
CARD_ICON_PATH = BASE_DIR / "assets" / "icons" / "card_icon.png"
FACE_CACHE_DIR = BASE_DIR / "cache" / "card_faces"
FACE_CACHE_DIR.mkdir(parents=True, exist_ok=True)

# =========================================================
# COTAÇÃO USD → BRL
# =========================================================

DEFAULT_USD_BRL = 5.50
CACHED_USD_BRL = DEFAULT_USD_BRL


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


def _parse_printings(value):
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]

    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError, json.JSONDecodeError):
        return []

    if not isinstance(parsed, list):
        return []

    return [item for item in parsed if isinstance(item, dict)]


def card_to_dict(card):
    if isinstance(card, dict):
        result = dict(card)
        result["card_faces"] = _parse_faces(result.get("card_faces"))
        result["card_printings"] = _parse_printings(result.get("card_printings"))
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
        "card_printings": _parse_printings(value(16)),
        "preferred_language": value(17),
        "preferred_variant": value(18),
        "preferred_finish": value(19),
        "preferred_image": value(20),
        "preferred_face": value(21, 0),
        "favorite": value(22, 0),
        "custom_tags": value(23),
        "last_view": value(24),
    }


def _has_missing_image_status(data):
    status = str(data.get("image_status") or "").casefold()
    return status in ("missing", "placeholder")


def _best_image_url(data):
    if (
        not isinstance(data, dict)
        or _has_missing_image_status(data)
    ):
        return None

    image_uris = data.get("image_uris")

    if isinstance(image_uris, dict):

        # Prioridade máxima:
        # PNG original da carta.
        png_url = image_uris.get("png")

        if png_url:
            return png_url

        # Fallbacks caso o PNG não exista.
        for key in (
            "large",
            "normal",
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

    url_text = str(url).lower()

    if ".png" in url_text:
        extension = "png"
    elif ".webp" in url_text:
        extension = "webp"
    else:
        extension = "jpg"

    local_path = (
        FACE_CACHE_DIR
        / f"{cache_key}.{extension}"
    )

    # =====================================================
    # CACHE
    # =====================================================

    if (
        local_path.exists()
        and local_path.stat().st_size > 0
    ):
        pixmap = QPixmap(
            str(local_path)
        )

        if not pixmap.isNull():
            return pixmap

    # =====================================================
    # DOWNLOAD
    # =====================================================

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

        content_type = (
            response.headers.get(
                "content-type",
                "",
            )
        ).lower()

        if "image" not in content_type:
            return None

        # =================================================
        # CORRIGIR EXTENSÃO PELO CONTEÚDO REAL
        # =================================================

        if "png" in content_type:
            extension = "png"
        elif "webp" in content_type:
            extension = "webp"
        elif "jpeg" in content_type or "jpg" in content_type:
            extension = "jpg"

        local_path = (
            FACE_CACHE_DIR
            / f"{cache_key}.{extension}"
        )

        local_path.write_bytes(
            response.content
        )

    except Exception as error:
        print(
            "[DETAILS] Erro ao carregar imagem:",
            error,
        )
        return None

    pixmap = QPixmap(
        str(local_path)
    )

    if pixmap.isNull():
        return None

    return pixmap

class DetailCard(QFrame):
    def __init__(self, title, parent=None):
        super().__init__(parent)

        self.setObjectName(
            "DetailInfoCard"
        )

        # =====================================================
        # LAYOUT INTERNO
        # =====================================================

        self.card_layout = QVBoxLayout(
            self
        )

        self.card_layout.setContentsMargins(
            14,
            12,
            14,
            12,
        )

        self.card_layout.setSpacing(
            6
        )

        # =====================================================
        # TÍTULO
        # =====================================================

        self.title_label = QLabel(
            title
        )

        self.title_label.setObjectName(
            "DetailInfoTitle"
        )

        self.card_layout.addWidget(
            self.title_label
        )

    def set_body(self, widget):
        """
        Adiciona o widget de conteúdo dentro do card.
        """

        self.card_layout.addWidget(
            widget
        )

# =========================================================
# WORKER - BUSCAR IMPRESSÕES DO SCRYFALL SEM TRAVAR A UI
# =========================================================

class PrintingsWorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class PrintingsWorker(QRunnable):

    def __init__(self, card):
        super().__init__()

        self.card = card
        self.signals = PrintingsWorkerSignals()

    def run(self):
        try:
            print(
                "[DETAILS] Buscando impressões no Scryfall..."
            )

            printings = get_card_printings(
                self.card
            )

            self.signals.finished.emit(
                printings or []
            )

        except Exception as error:

            print(
                "[DETAILS] Erro ao buscar impressões:",
                error,
            )

            self.signals.error.emit(
                str(error)
            )
class CardDetailsDialog(QDialog):

    def _make_scrollable_tab(self, content_widget):
        """
        Coloca o conteúdo de uma aba dentro de uma QScrollArea.

        Isso evita que o conteúdo fique para fora da janela
        em monitores menores ou quando a janela é redimensionada.
        """

        scroll = QScrollArea()
        scroll.setObjectName(
            "CardDetailScrollArea"
        )

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        scroll.setWidget(
            content_widget
        )

        return scroll

    def _refresh_layouts_after_show(self):
        """
        Recalcula os layouts principais da janela.
        """

        # =====================================================
        # LAYOUT DO PRÓPRIO DIÁLOGO
        # =====================================================

        main_layout = QWidget.layout(self)

        if main_layout is not None:
            main_layout.invalidate()
            main_layout.activate()

        # =====================================================
        # TAB WIDGET
        # =====================================================

        if self.tabs is not None:

            tabs_layout = QWidget.layout(
                self.tabs
            )

            if tabs_layout is not None:
                tabs_layout.invalidate()
                tabs_layout.activate()

            self.tabs.updateGeometry()
            self.tabs.update()

        # =====================================================
        # ABA ATUAL
        # =====================================================

        current_tab = self.tabs.currentWidget()

        if current_tab is not None:

            current_layout = QWidget.layout(
                current_tab
            )

            if current_layout is not None:
                current_layout.invalidate()
                current_layout.activate()

            current_tab.updateGeometry()
            current_tab.update()

        # =====================================================
        # DIÁLOGO
        # =====================================================

        self.updateGeometry()
        self.update()

        # =====================================================
        # PROCESSAR EVENTOS PENDENTES
        # =====================================================

        QGuiApplication.processEvents()
    def resizeEvent(self, event):
        """
        Recalcula os layouts quando a janela muda de tamanho.
        """

        super().resizeEvent(event)

        # Não recalcular dezenas de vezes durante o mesmo
        # processo de redimensionamento.
        QTimer.singleShot(
            0,
            self._refresh_layouts_after_show,
        )

    def _fit_window_to_screen(self):
        """
        Ajusta a janela para caber na área disponível da tela.

        A janela pode ser grande quando houver espaço,
        mas nunca deve ultrapassar a área visível.
        """

        if self.isMaximized():
            return

        screen = self.screen()

        if screen is None:
            screen = QGuiApplication.primaryScreen()

        if screen is None:
            return

        available = screen.availableGeometry()

        # =====================================================
        # TAMANHO PREFERIDO
        # =====================================================

        preferred_width = 1120
        preferred_height = 800

        # =====================================================
        # MARGEM DE SEGURANÇA DA TELA
        # =====================================================

        max_width = max(
            760,
            available.width() - 40,
        )

        max_height = max(
            520,
            available.height() - 60,
        )

        # =====================================================
        # TAMANHO FINAL
        # =====================================================

        width = min(
            preferred_width,
            max_width,
        )

        height = min(
            preferred_height,
            max_height,
        )

        # =====================================================
        # TAMANHO MÍNIMO
        # =====================================================

        self.setMinimumSize(
            min(760, max_width),
            min(520, max_height),
        )

        # =====================================================
        # APLICAR TAMANHO
        # =====================================================

        self.resize(
            width,
            height,
        )

        # =====================================================
        # CENTRALIZAR
        # =====================================================

        x = (
                available.left()
                + (
                        available.width()
                        - self.width()
                ) // 2
        )

        y = (
                available.top()
                + (
                        available.height()
                        - self.height()
                ) // 2
        )

        # =====================================================
        # GARANTIR QUE NÃO SAIA DA TELA
        # =====================================================

        x = max(
            available.left(),
            min(
                x,
                available.right()
                - self.width()
                + 1,
            ),
        )

        y = max(
            available.top(),
            min(
                y,
                available.bottom()
                - self.height()
                + 1,
            ),
        )

        self.move(
            x,
            y,
        )

    def __init__(self, card, pixmap=None, parent=None):
        super().__init__(parent)

        # =====================================================
        # CARTA RECEBIDA PELA UI
        # =====================================================

        incoming_card = card_to_dict(
            card
        )

        # =====================================================
        # BUSCAR A VERSÃO COMPLETA NO BANCO
        # =====================================================

        local_id = incoming_card.get(
            "id"
        )

        stored_card = None

        if local_id:
            try:
                stored_card = get_card_by_id(
                    local_id
                )

            except Exception as error:
                print(
                    "[DETAILS] Erro ao carregar "
                    "carta completa do banco:",
                    error,
                )

        # =====================================================
        # FONTE DE DADOS DOS DETALHES
        # =====================================================

        if isinstance(
                stored_card,
                dict,
        ):
            self.card = {
                **incoming_card,
                **stored_card,
            }

        else:
            self.card = incoming_card

        self.initial_pixmap = pixmap
        try:
            self.current_face_index = int(
                self.card.get("preferred_face") or 0
            )
        except (
            TypeError,
            ValueError,
        ):
            self.current_face_index = 0
        self.english_card = None

        # =====================================================
        # IMPRESSÕES JÁ SALVAS LOCALMENTE
        # =====================================================

        self.printings = self._load_printings()

        self._syncing_controls = False

        self.faces = self._build_faces(
            self.card
        )

        # Worker será iniciado depois que a UI estiver pronta.
        # =====================================================
        # CONTROLE DA SINCRONIZAÇÃO
        # =====================================================

        self.printings_worker = None
        self.printings_sync_running = False

        self.setWindowTitle(
            f"{self.card.get('name') or 'Carta'} - Magic Collection"
        )

        # =====================================================
        # CONFIGURAÇÃO DA JANELA
        # =====================================================

        self.setSizeGripEnabled(True)

        self.setWindowFlag(
            Qt.WindowType.WindowMaximizeButtonHint,
            True,
        )

        self.setWindowFlag(
            Qt.WindowType.WindowMinimizeButtonHint,
            True,
        )

        self.setStyleSheet(
            DARK_THEME
        )

        # Ajustar automaticamente ao tamanho da tela.
        self._fit_window_to_screen()

        root = QHBoxLayout(self)
        root.setContentsMargins(26, 24, 26, 24)
        root.setSpacing(28)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("CardDetailLeftPanel")
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setObjectName("CardDetailImage")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(
            280,
            390,
        )

        self.image_label.setMaximumSize(
            360,
            505,
        )

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Preferred,
        )
        self.image_label.setScaledContents(False)
        left_layout.addWidget(self.image_label, 0, Qt.AlignmentFlag.AlignHCenter)

        self.image_status_label = QLabel()
        self.image_status_label.setObjectName("CardDetailImageStatus")
        self.image_status_label.setWordWrap(True)
        self.image_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_status_label.hide()
        left_layout.addWidget(self.image_status_label)

        self.language_combo = QComboBox()
        self.language_combo.setObjectName("DetailSelector")
        self.language_combo.currentIndexChanged.connect(
            self.on_language_changed
        )
        left_layout.addWidget(self.language_combo)

        self.variant_combo = QComboBox()
        self.variant_combo.setObjectName("DetailSelector")
        self.variant_combo.currentIndexChanged.connect(
            self.on_variant_changed
        )
        left_layout.addWidget(self.variant_combo)

        # =====================================================
        # STATUS DA SINCRONIZAÇÃO DAS IMPRESSÕES
        # =====================================================

        self.printings_sync_label = QLabel(
            "🔄 Verificando idiomas e artes..."
        )

        self.printings_sync_label.setObjectName(
            "CardDetailMuted"
        )

        self.printings_sync_label.setWordWrap(True)
        self.printings_sync_label.hide()

        left_layout.addWidget(
            self.printings_sync_label
        )

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

        root.addWidget(self.left_panel, 0, Qt.AlignmentFlag.AlignTop)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("CardDetailRightPanel")
        right_layout = QVBoxLayout(self.right_panel)
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
        self.tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        right_layout.addWidget(self.tabs, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        right_layout.addWidget(buttons)

        root.addWidget(self.right_panel, 1)
        self._populate_selectors()

        # =====================================================
        # MOSTRAR A CARTA IMEDIATAMENTE
        # =====================================================

        if self.variant_combo.currentIndex() >= 0:

            self.apply_selected_printing(
                save_changes=False
            )

        else:

            if self.current_face_index >= len(self.faces):
                self.current_face_index = 0

        # =====================================================
        # AJUSTAR TAMANHO DA JANELA
        # =====================================================

        self._fit_window_to_screen()

        # =====================================================
        # PRIMEIRO RECÁLCULO DOS LAYOUTS
        # =====================================================

        if self.layout() is not None:
            self.layout().invalidate()
            self.layout().activate()

        QWidget.layout(
            self.right_panel
        ).invalidate()

        QWidget.layout(
            self.right_panel
        ).activate()

        QWidget.layout(
            self.left_panel
        ).invalidate()

        QWidget.layout(
            self.left_panel
        ).activate()

        self.tabs.updateGeometry()

        QGuiApplication.processEvents()

        # =====================================================
        # ATUALIZAR A FACE DEPOIS DO LAYOUT
        # =====================================================

        self.set_face(
            self.current_face_index,
            save_changes=False,
        )

        # =====================================================
        # SINCRONIZAR IMPRESSÕES EM BACKGROUND
        # =====================================================

        self._start_printings_sync()

        # =====================================================
        # RECÁLCULO FINAL DA INTERFACE
        # =====================================================

        if self.layout() is not None:
            self.layout().invalidate()
            self.layout().activate()

        if self.tabs.layout() is not None:
            self.tabs.layout().invalidate()
            self.tabs.layout().activate()

        self.tabs.updateGeometry()

        QGuiApplication.processEvents()

        # Garantir que a imagem seja redimensionada
        # corretamente depois do tamanho final.
        if self.faces:
            self._set_face_image(
                self.faces[self.current_face_index]
            )

        # =====================================================
        # RECÁLCULO APÓS A JANELA ENTRAR NO EVENT LOOP
        # =====================================================

        QTimer.singleShot(
            0,
            self._refresh_layouts_after_show,
        )
    def _start_printings_sync(self):

        # =====================================================
        # EVITAR DUAS CONSULTAS SIMULTÂNEAS
        # =====================================================

        if self.printings_sync_running:
            return

        self.printings_sync_running = True

        # Mostrar indicador de carregamento
        self.printings_sync_label.setText(
            "🔄 Verificando idiomas e artes..."
        )

        self.printings_sync_label.show()

        # =====================================================
        # COPIAR OS DADOS DA CARTA
        # =====================================================

        card = dict(self.card)

        # =====================================================
        # CRIAR WORKER
        # =====================================================

        self.printings_worker = PrintingsWorker(
            card
        )

        self.printings_worker.signals.finished.connect(
            self._on_printings_loaded
        )

        self.printings_worker.signals.error.connect(
            self._on_printings_error
        )

        # =====================================================
        # EXECUTAR EM BACKGROUND
        # =====================================================

        QThreadPool.globalInstance().start(
            self.printings_worker
        )
    def _on_printings_loaded(self, printings):

        # =====================================================
        # FINALIZAR ESTADO DO WORKER
        # =====================================================

        self.printings_sync_running = False

        # =====================================================
        # NENHUM RESULTADO
        # =====================================================

        if not printings:

            self.printings_sync_label.setText(
                "⚠ Não foi possível atualizar as impressões."
            )

            self.printings_sync_label.show()

            print(
                "[DETAILS] Nenhuma impressão adicional encontrada."
            )

            return

        # =====================================================
        # COMPARAR IMPRESSÕES LOCAIS X SCRYFALL
        # =====================================================

        local_ids = set()

        for printing in self.printings:

            if not isinstance(
                    printing,
                    dict,
            ):
                continue

            printing_id = (
                    printing.get("id")
                    or printing.get("scryfall_id")
            )

            if printing_id:
                local_ids.add(
                    str(printing_id)
                )

        remote_ids = set()

        for printing in printings:

            if not isinstance(
                    printing,
                    dict,
            ):
                continue

            printing_id = (
                    printing.get("id")
                    or printing.get("scryfall_id")
            )

            if printing_id:
                remote_ids.add(
                    str(printing_id)
                )

        # =====================================================
        # DESCOBRIR O QUE MUDOU
        # =====================================================

        new_ids = remote_ids - local_ids
        removed_ids = local_ids - remote_ids

        changed = bool(
            new_ids
            or removed_ids
            or len(local_ids) != len(remote_ids)
        )

        print(
            "[DETAILS] Impressões locais:",
            len(local_ids),
        )

        print(
            "[DETAILS] Impressões no Scryfall:",
            len(remote_ids),
        )

        if new_ids:

            print(
                "[DETAILS] Novas impressões encontradas:",
                len(new_ids),
            )

        if removed_ids:

            print(
                "[DETAILS] Impressões removidas:",
                len(removed_ids),
            )

        # =====================================================
        # ATUALIZAR DADOS EM MEMÓRIA
        # =====================================================

        self.printings = printings
        self.card["card_printings"] = printings

        # =====================================================
        # SALVAR CACHE NO BANCO
        #
        # IMPORTANTE:
        # Isso salva somente as impressões.
        # Não emitimos card_data_changed.
        # =====================================================

        local_id = self.card.get("id")

        if local_id and changed:

            try:

                update_card_printing(
                    local_id,
                    self.card,
                    printings=printings,
                    preferred_language=self.card.get(
                        "preferred_language"
                    ),
                    preferred_variant=self.card.get(
                        "preferred_variant"
                    ),
                    preferred_finish=self.card.get(
                        "preferred_finish"
                    ),
                    preferred_face=self.card.get(
                        "preferred_face",
                        self.current_face_index,
                    ),
                )

                print(
                    "[DETAILS] Cache de impressões salvo no banco:",
                    local_id,
                )

            except Exception as error:

                print(
                    "[DETAILS] Erro ao salvar cache de impressões:",
                    error,
                )

        # =====================================================
        # GUARDAR SELEÇÃO ATUAL
        # =====================================================

        current_language = (
            self.language_combo.currentData()
        )

        current_variant = (
                self.card.get("preferred_variant")
                or self.card.get("scryfall_id")
        )

        # =====================================================
        # ATUALIZAR COMBOS SEM DISPARAR EVENTOS
        # =====================================================

        self._syncing_controls = True

        try:

            self._populate_selectors()

            # -------------------------------------------------
            # RESTAURAR IDIOMA
            # -------------------------------------------------

            if current_language:

                language_index = (
                    self.language_combo.findData(
                        current_language
                    )
                )

                if language_index >= 0:

                    self.language_combo.setCurrentIndex(
                        language_index
                    )

                    self._populate_variant_combo(
                        current_language
                    )

            # -------------------------------------------------
            # RESTAURAR IMPRESSÃO
            # -------------------------------------------------

            if current_variant:

                for index in range(
                        self.variant_combo.count()
                ):

                    printing = (
                        self.variant_combo.itemData(
                            index
                        )
                    )

                    if not isinstance(
                            printing,
                            dict,
                    ):
                        continue

                    printing_id = (
                            printing.get("id")
                            or printing.get("scryfall_id")
                    )

                    if (
                            printing_id
                            and str(printing_id)
                            == str(current_variant)
                    ):

                        self.variant_combo.setCurrentIndex(
                            index
                        )

                        break

        finally:

            self._syncing_controls = False

        # =====================================================
        # ATUALIZAR TEXTO DA INTERFACE
        # =====================================================

        if changed:

            self.printings_sync_label.setText(
                f"✓ Impressões atualizadas: "
                f"{len(remote_ids)} disponíveis."
            )

            print(
                "[DETAILS] Novas impressões sincronizadas."
            )

        else:

            self.printings_sync_label.setText(
                f"✓ Impressões verificadas: "
                f"{len(remote_ids)} disponíveis."
            )

            print(
                "[DETAILS] Impressões já estavam atualizadas."
            )

        self.printings_sync_label.show()

        # =====================================================
        # ATUALIZAR ABA "OUTRAS IMPRESSÕES"
        # =====================================================

        if hasattr(
                self,
                "printings_label",
        ):

            self.printings_label.setText(
                f"{len(remote_ids)} impressões encontradas."
            )

    def _on_printings_error(self, error):

        self.printings_sync_running = False

        self.printings_sync_label.setText(
            "⚠ Não foi possível verificar as impressões."
        )

        self.printings_sync_label.show()

        print(
            "[DETAILS] Sincronização de impressões falhou:",
            error,
        )

    def _build_main_tab(self):

        content = QWidget()

        layout = QVBoxLayout(
            content
        )

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

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
        # =====================================================
        # VALOR DA COLEÇÃO
        # =====================================================

        market_card = DetailCard(
            "Valor da colecao"
        )

        market_card.setObjectName(
            "MarketValueCard"
        )

        self.market_value_labels = {}

        market_widget = QWidget()

        market_widget.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        market_layout = QGridLayout(
            market_widget
        )

        market_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        market_layout.setHorizontalSpacing(
            18
        )

        market_layout.setVerticalSpacing(
            8
        )

        # -----------------------------------------------------
        # VALOR UNITÁRIO
        # -----------------------------------------------------

        unit_title = QLabel(
            "Valor unitario"
        )

        unit_title.setObjectName(
            "DetailPriceTitle"
        )

        unit_value = QLabel(
            "-"
        )

        unit_value.setObjectName(
            "DetailMarketValue"
        )

        unit_value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.market_value_labels[
            "unit"
        ] = unit_value

        market_layout.addWidget(
            unit_title,
            0,
            0,
        )

        market_layout.addWidget(
            unit_value,
            0,
            1,
        )

        # -----------------------------------------------------
        # QUANTIDADE
        # -----------------------------------------------------

        quantity_title = QLabel(
            "Quantidade"
        )

        quantity_title.setObjectName(
            "DetailPriceTitle"
        )

        quantity_value = QLabel(
            "0"
        )

        quantity_value.setObjectName(
            "DetailPriceValue"
        )

        quantity_value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.market_value_labels[
            "quantity"
        ] = quantity_value

        market_layout.addWidget(
            quantity_title,
            1,
            0,
        )

        market_layout.addWidget(
            quantity_value,
            1,
            1,
        )

        # -----------------------------------------------------
        # VALOR TOTAL
        # -----------------------------------------------------

        total_title = QLabel(
            "Valor total"
        )

        total_title.setObjectName(
            "DetailPriceTitle"
        )

        total_value = QLabel(
            "-"
        )

        total_value.setObjectName(
            "DetailMarketTotal"
        )

        total_value.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        self.market_value_labels[
            "total"
        ] = total_value

        market_layout.addWidget(
            total_title,
            2,
            0,
        )

        market_layout.addWidget(
            total_value,
            2,
            1,
        )

        market_card.set_body(
            market_widget
        )

        layout.addWidget(
            market_card
        )

        # =====================================================
        # PREÇOS ORIGINAIS
        # =====================================================

        price_card = DetailCard(
            "Precos de mercado"
        )

        self.price_labels = {}

        price_widget = QWidget()

        price_widget.setAttribute(
            Qt.WidgetAttribute.WA_TranslucentBackground
        )

        price_layout = QGridLayout(
            price_widget
        )

        price_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        price_layout.setHorizontalSpacing(
            18
        )

        price_layout.setVerticalSpacing(
            6
        )

        price_fields = (
            ("Normal", "price_usd"),
            ("Foil", "price_usd_foil"),
            ("Etched", "price_usd_etched"),
            ("EUR", "price_eur"),
            ("EUR Foil", "price_eur_foil"),
            ("MTGO", "price_tix"),
        )

        for index, (
                title,
                key,
        ) in enumerate(
            price_fields
        ):
            title_label = QLabel(
                title
            )

            title_label.setObjectName(
                "DetailPriceTitle"
            )

            value_label = QLabel(
                "-"
            )

            value_label.setObjectName(
                "DetailPriceValue"
            )

            value_label.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            self.price_labels[
                key
            ] = value_label

            row = index // 2
            column = index % 2

            price_layout.addWidget(
                title_label,
                row,
                column * 2,
            )

            price_layout.addWidget(
                value_label,
                row,
                column * 2 + 1,
            )

        price_card.set_body(
            price_widget
        )

        layout.addWidget(
            price_card
        )

        layout.addStretch()

        return self._make_scrollable_tab(
            content
        )

    def _update_market_value(self):
        """
        Calcula o valor estimado da carta em reais.

        Fórmula:

            preço USD × cotação USD/BRL = valor unitário

            valor unitário × quantidade = valor total
        """

        # -------------------------------------------------
        # VERIFICAR SE A INTERFACE JÁ FOI CRIADA
        # -------------------------------------------------

        if not hasattr(
            self,
            "market_value_labels",
        ):
            return

        # -------------------------------------------------
        # QUANTIDADE
        # -------------------------------------------------

        quantity = self.card.get(
            "quantity",
            0,
        )

        try:
            quantity = int(
                quantity or 0
            )

        except (
            TypeError,
            ValueError,
        ):
            quantity = 0

        # -------------------------------------------------
        # PREÇO NORMAL EM USD
        # -------------------------------------------------

        usd_price = self.card.get(
            "price_usd"
        )

        try:
            usd_price = float(
                usd_price
            )

        except (
            TypeError,
            ValueError,
        ):
            usd_price = None

        # -------------------------------------------------
        # SEM PREÇO
        # -------------------------------------------------

        if usd_price is None:
            self.market_value_labels[
                "unit"
            ].setText(
                "Sem preço"
            )

            self.market_value_labels[
                "quantity"
            ].setText(
                str(quantity)
            )

            self.market_value_labels[
                "total"
            ].setText(
                "Sem preço"
            )

            return

        # -------------------------------------------------
        # COTAÇÃO USD → BRL
        # -------------------------------------------------

        usd_brl = CACHED_USD_BRL

        # -------------------------------------------------
        # CÁLCULO
        # -------------------------------------------------

        unit_brl = (
            usd_price
            * usd_brl
        )

        total_brl = (
            unit_brl
            * quantity
        )

        # -------------------------------------------------
        # FORMATAÇÃO BRASILEIRA
        # -------------------------------------------------

        unit_text = (
            f"R$ {unit_brl:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        total_text = (
            f"R$ {total_brl:,.2f}"
            .replace(",", "X")
            .replace(".", ",")
            .replace("X", ".")
        )

        # -------------------------------------------------
        # ATUALIZAR INTERFACE
        # -------------------------------------------------

        self.market_value_labels[
            "unit"
        ].setText(
            unit_text
        )

        self.market_value_labels[
            "quantity"
        ].setText(
            str(quantity)
        )

        self.market_value_labels[
            "total"
        ].setText(
            total_text
        )

        print(
            "[DETAILS] Valor de mercado:",
            unit_text,
            "| Quantidade:",
            quantity,
            "| Total:",
            total_text,
        )

    def _update_price_labels(self):
        """
        Atualiza os preços da impressão atualmente exibida.
        """

        def format_usd(value):
            if value in (
                None,
                "",
            ):
                return "-"

            try:
                return f"US$ {float(value):.2f}"
            except (
                TypeError,
                ValueError,
            ):
                return "-"

        def format_eur(value):
            if value in (
                None,
                "",
            ):
                return "-"

            try:
                return f"€ {float(value):.2f}"
            except (
                TypeError,
                ValueError,
            ):
                return "-"

        def format_tix(value):
            if value in (
                None,
                "",
            ):
                return "-"

            try:
                return f"{float(value):.2f} tix"
            except (
                TypeError,
                ValueError,
            ):
                return "-"

        values = {
            "price_usd": format_usd(
                self.card.get("price_usd")
            ),

            "price_usd_foil": format_usd(
                self.card.get("price_usd_foil")
            ),

            "price_usd_etched": format_usd(
                self.card.get("price_usd_etched")
            ),

            "price_eur": format_eur(
                self.card.get("price_eur")
            ),

            "price_eur_foil": format_eur(
                self.card.get("price_eur_foil")
            ),

            "price_tix": format_tix(
                self.card.get("price_tix")
            ),
        }

        for key, label in self.price_labels.items():
            label.setText(
                values.get(
                    key,
                    "-"
                )
            )

        self._update_market_value()

    def _build_printings_tab(self):

        tab = QWidget()

        layout = QVBoxLayout(tab)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        self.printings_label = QLabel(
            "🔄 Verificando impressões disponíveis..."
        )

        self.printings_label.setObjectName(
            "CardDetailMuted"
        )

        self.printings_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.printings_label
        )

        layout.addStretch()

        return tab

    def _build_extra_tab(self):

        content = QWidget()

        layout = QGridLayout(
            content
        )
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

        return self._make_scrollable_tab(
            content
        )

    def _build_history_tab(self):

        content = QWidget()

        layout = QGridLayout(
            content
        )
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

        return self._make_scrollable_tab(
            content
        )

    def _build_faces(self, card):
        faces = card.get("card_faces")
        if isinstance(faces, list) and faces:
            return faces
        return [card]

    def _load_printings(self):
        printings = _parse_printings(
            self.card.get("card_printings")
        )

        if printings:
            return printings

        # Ainda não temos as variantes armazenadas.
        # Usamos a própria carta para abrir imediatamente.
        return [
            self.card
        ]

    def _populate_selectors(self):
        self._syncing_controls = True

        self.language_combo.clear()

        languages = []
        seen_languages = set()

        for printing in self.printings:
            language = printing.get("lang") or "en"

            if language in seen_languages:
                continue

            seen_languages.add(language)
            languages.append(language)

        if not languages:
            languages = [
                self.card.get("lang") or "en"
            ]

        preferred_language = (
            self.card.get("preferred_language")
            or self.card.get("lang")
            or languages[0]
        )

        for language in languages:
            self.language_combo.addItem(
                LANGUAGE_LABELS.get(language, language),
                language,
            )

        index = self.language_combo.findData(
            preferred_language
        )
        if index < 0:
            index = 0

        self.language_combo.setCurrentIndex(
            index
        )

        self._populate_variant_combo(
            self.language_combo.currentData()
        )

        self._syncing_controls = False

    def _populate_variant_combo(
        self,
        language,
    ):
        self.variant_combo.clear()

        variants = [
            printing
            for printing in self.printings
            if (printing.get("lang") or "en") == language
        ]

        if not variants:
            variants = list(self.printings)

        variants = sorted(
            variants,
            key=lambda printing: (
                0 if self._printing_has_image(printing) else 1,
                str(printing.get("released_at") or ""),
                str(printing.get("collector_number") or ""),
            ),
        )

        preferred_variant = (
            self.card.get("preferred_variant")
            or self.card.get("scryfall_id")
            or self.card.get("id")
        )

        for printing in variants:
            self.variant_combo.addItem(
                self._variant_label(printing),
                printing,
            )

        preferred_index = -1
        image_index = -1

        for item_index in range(self.variant_combo.count()):
            printing = self.variant_combo.itemData(
                item_index
            )
            printing_id = (
                printing.get("id")
                or printing.get("scryfall_id")
            )

            if printing_id == preferred_variant and self._printing_has_image(printing):
                preferred_index = item_index

            if image_index < 0 and self._printing_has_image(printing):
                image_index = item_index

        if preferred_index >= 0:
            index = preferred_index
        elif image_index >= 0:
            index = image_index
        else:
            index = 0

        self.variant_combo.setCurrentIndex(
            index
        )

    def _variant_label(self, printing):
        set_code = str(
            printing.get("set")
            or printing.get("set_code")
            or ""
        ).upper()

        collector = printing.get("collector_number") or "?"
        language = printing.get("lang") or "en"
        rarity = printing.get("rarity") or ""

        finishes = printing.get("finishes") or []
        finish_text = "/".join(finishes) if finishes else "normal"

        parts = [
            f"{set_code} #{collector}",
            LANGUAGE_LABELS.get(language, language),
            finish_text,
        ]

        if rarity:
            parts.append(str(rarity).title())

        if not self._printing_has_image(printing):
            parts.append("sem imagem")

        return " | ".join(parts)

    def _printing_has_image(self, printing):
        if _best_image_url(printing):
            return True

        for face in self._build_faces(printing):
            if _best_image_url(face):
                return True

        return False

    def on_language_changed(self, *_args):
        if self._syncing_controls:
            return

        language = self.language_combo.currentData()

        self._syncing_controls = True
        self._populate_variant_combo(language)
        self._syncing_controls = False

        self.apply_selected_printing()

    def on_variant_changed(self, *_args):
        if self._syncing_controls:
            return

        self.apply_selected_printing()

    def apply_selected_printing(self, save_changes=True):
        printing = self.variant_combo.currentData()

        if not isinstance(printing, dict):
            return

        quantity = self.card.get("quantity", 0)
        deck_quantity = self.card.get("deck_quantity")
        local_id = self.card.get("id")

        self.card.update(printing)

        # =====================================================
        # PREÇOS DA IMPRESSÃO SELECIONADA
        # =====================================================

        prices = (
            printing.get("prices")
            or {}
        )

        def parse_price(value):
            try:
                if value in (
                    None,
                    "",
                ):
                    return None

                return float(value)

            except (
                TypeError,
                ValueError,
            ):
                return None

        self.card["price_usd"] = parse_price(
            prices.get("usd")
        )

        self.card["price_usd_foil"] = parse_price(
            prices.get("usd_foil")
        )

        self.card["price_usd_etched"] = parse_price(
            prices.get("usd_etched")
        )

        self.card["price_eur"] = parse_price(
            prices.get("eur")
        )

        self.card["price_eur_foil"] = parse_price(
            prices.get("eur_foil")
        )

        self.card["price_tix"] = parse_price(
            prices.get("tix")
        )

        self.card["id"] = local_id
        # =====================================================
        # PREÇOS DA IMPRESSÃO SELECIONADA
        # =====================================================

        prices = (
            printing.get("prices")
            or {}
        )

        def parse_price(value):
            try:
                if value in (
                    None,
                    "",
                ):
                    return None

                return float(value)

            except (
                TypeError,
                ValueError,
            ):
                return None

        self.card["price_usd"] = parse_price(
            prices.get("usd")
        )

        self.card["price_usd_foil"] = parse_price(
            prices.get("usd_foil")
        )

        self.card["price_usd_etched"] = parse_price(
            prices.get("usd_etched")
        )

        self.card["price_eur"] = parse_price(
            prices.get("eur")
        )

        self.card["price_eur_foil"] = parse_price(
            prices.get("eur_foil")
        )

        self.card["price_tix"] = parse_price(
            prices.get("tix")
        )
        self.card["scryfall_id"] = (
            printing.get("id")
            or printing.get("scryfall_id")
        )
        self.card["set_code"] = (
            printing.get("set")
            or printing.get("set_code")
        )
        self.card["quantity"] = quantity
        self.card["deck_quantity"] = deck_quantity
        self.card["card_faces"] = _parse_faces(
            printing.get("card_faces")
        )
        self.card["card_printings"] = self.printings
        self.card["preferred_language"] = (
            self.language_combo.currentData()
        )
        self.card["preferred_variant"] = self.card.get(
            "scryfall_id"
        )

        # =====================================================
        # SALVAR A IMAGEM DA IMPRESSÃO SELECIONADA
        # =====================================================

        selected_face = None

        if self.card.get("card_faces"):
            faces = self.card.get("card_faces")

            if (
                    isinstance(faces, list)
                    and faces
                    and self.current_face_index < len(faces)
            ):
                selected_face = faces[
                    self.current_face_index
                ]

        image_source = selected_face or self.card

        image_url = _best_image_url(
            image_source
        )

        if not image_url:
            image_url = _best_image_url(
                self.card
            )

        selected_scryfall_id = (
            self.card.get("scryfall_id")
        )

        if (
                save_changes
                and image_url
                and selected_scryfall_id
        ):

            saved_path = self._save_selected_image(
                image_url,
                selected_scryfall_id,
            )

            if saved_path:

                self.card["image_path"] = str(
                    saved_path
                )

                self.card["image_url"] = image_url

        self.faces = self._build_faces(
            self.card
        )

        if self.current_face_index >= len(self.faces):
            self.current_face_index = 0

        if save_changes and local_id:

            update_card_printing(
                local_id,
                self.card,
                printings=self.printings,
                preferred_language=self.card.get(
                    "preferred_language"
                ),
                preferred_variant=self.card.get(
                    "preferred_variant"
                ),
                preferred_finish=self.card.get(
                    "preferred_finish"
                ),
                preferred_face=self.current_face_index,
            )

            # =====================================================
            # AVISAR QUE OS DADOS DA CARTA MUDARAM
            #
            # Só acontece quando o usuário realmente alterou
            # alguma coisa.
            # =====================================================

            try:

                app_events.card_data_changed.emit(
                    int(local_id)
                )

                print(
                    "[DETAILS] Evento card_data_changed emitido:",
                    local_id,
                )

            except Exception as error:

                print(
                    "[DETAILS] Erro ao emitir card_data_changed:",
                    error,
                )
        self.setWindowTitle(
            f"{self.card.get('name') or 'Carta'} - Magic Collection"
        )
        self.set_face(
            self.current_face_index,
            save_changes=save_changes,
        )

    def _face_value(self, face, key, fallback=True):
        localized_key = {
            "name": "printed_name",
            "type_line": "printed_type_line",
            "oracle_text": "printed_text",
        }.get(key)

        if localized_key:
            value = face.get(localized_key)
            if value not in (None, "", []):
                return value

        value = face.get(key)
        if value not in (None, "", []):
            return value
        if fallback:
            if localized_key:
                value = self.card.get(localized_key)
                if value not in (None, "", []):
                    return value

            value = self.card.get(key)
            if value not in (None, "", []):
                return value
        return None

    def set_face(self, face_index, save_changes=True):
        if face_index < 0 or face_index >= len(self.faces):
            return

        self.current_face_index = face_index
        face = self.faces[face_index]
        self.card["preferred_face"] = face_index

        face_button = self.face_buttons.button(
            face_index
        )

        if face_button:
            face_button.setChecked(True)

        local_id = self.card.get("id")

        if save_changes and local_id:

            update_card_printing(
                local_id,
                self.card,
                printings=self.printings,
                preferred_language=self.card.get(
                    "preferred_language"
                ),
                preferred_variant=self.card.get(
                    "preferred_variant"
                ),
                preferred_finish=self.card.get(
                    "preferred_finish"
                ),
                preferred_face=face_index,
            )

            try:

                app_events.card_data_changed.emit(
                    int(local_id)
                )

            except Exception as error:

                print(
                    "[DETAILS] Erro ao emitir alteração da carta:",
                    error,
                )

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
        self._update_price_labels()
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


    def _get_usd_brl_rate(self):
        """
        Obtém a cotação atual do dólar em relação ao real.

        Caso a consulta falhe, utiliza DEFAULT_USD_BRL
        para que a interface continue funcionando.
        """

        try:
            response = requests.get(
                "https://economia.awesomeapi.com.br/json/last/USD-BRL",
                timeout=5,
            )

            response.raise_for_status()

            data = response.json()

            rate_data = data.get(
                "USDBRL",
                {},
            )

            rate = rate_data.get(
                "bid"
            )

            if rate in (
                None,
                "",
            ):
                raise ValueError(
                    "Cotação USD/BRL não encontrada."
                )

            rate = float(rate)

            if rate <= 0:
                raise ValueError(
                    "Cotação USD/BRL inválida."
                )

            print(
                "[DETAILS] Cotação USD/BRL:",
                rate,
            )

            return rate

        except Exception as error:
            print(
                "[DETAILS] Falha ao obter cotação USD/BRL:",
                error,
            )

            print(
                "[DETAILS] Usando cotação padrão:",
                DEFAULT_USD_BRL,
            )

            return DEFAULT_USD_BRL

        def _update_market_value(self):
            """
            Calcula o valor estimado da carta em reais.

            O cálculo utiliza:
                preço USD × cotação USD/BRL × quantidade
            """

            if not hasattr(
                    self,
                    "market_value_labels",
            ):
                return

            # -------------------------------------------------
            # QUANTIDADE
            # -------------------------------------------------

            quantity = self.card.get(
                "quantity",
                0,
            )

            try:
                quantity = int(
                    quantity or 0
                )
            except (
                    TypeError,
                    ValueError,
            ):
                quantity = 0

            # -------------------------------------------------
            # PREÇO USD
            # -------------------------------------------------

            usd_price = self.card.get(
                "price_usd"
            )

            try:
                usd_price = float(
                    usd_price
                )
            except (
                    TypeError,
                    ValueError,
            ):
                usd_price = None

            # -------------------------------------------------
            # SEM PREÇO
            # -------------------------------------------------

            if usd_price is None:
                self.market_value_labels[
                    "unit"
                ].setText(
                    "Sem preço"
                )

                self.market_value_labels[
                    "quantity"
                ].setText(
                    str(quantity)
                )

                self.market_value_labels[
                    "total"
                ].setText(
                    "Sem preço"
                )

                return

            # -------------------------------------------------
            # COTAÇÃO
            # -------------------------------------------------

            usd_brl = self._get_usd_brl_rate()

            # -------------------------------------------------
            # CÁLCULOS
            # -------------------------------------------------

            unit_brl = (
                    usd_price
                    * usd_brl
            )

            total_brl = (
                    unit_brl
                    * quantity
            )

            # -------------------------------------------------
            # ATUALIZAR INTERFACE
            # -------------------------------------------------

            self.market_value_labels[
                "unit"
            ].setText(
                f"R$ {unit_brl:,.2f}".replace(
                    ",",
                    "X",
                ).replace(
                    ".",
                    ",",
                ).replace(
                    "X",
                    ".",
                )
            )

            self.market_value_labels[
                "quantity"
            ].setText(
                str(quantity)
            )

            self.market_value_labels[
                "total"
            ].setText(
                f"R$ {total_brl:,.2f}".replace(
                    ",",
                    "X",
                ).replace(
                    ".",
                    ",",
                ).replace(
                    "X",
                    ".",
                )
            )
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

    def _save_selected_image(self, url, scryfall_id):
        if not url or not scryfall_id:
            return None

        try:
            from database import get_card_image_path

            image_path = get_card_image_path(
                scryfall_id
            )

            if not image_path:
                return None

            image_path = Path(
                image_path
            )

            image_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "MagicCollection/1.0",
                    "Accept": "image/png,image/*,*/*;q=0.8",
                },
            )

            response.raise_for_status()

            content_type = response.headers.get(
                "content-type",
                "",
            ).lower()

            if "image" not in content_type:
                print(
                    "[DETAILS] Resposta não é uma imagem."
                )
                return None

            image_path.write_bytes(
                response.content
            )

            print(
                "[DETAILS] Imagem salva:",
                image_path,
            )

            return image_path

        except Exception as error:
            print(
                "[DETAILS] Erro ao salvar imagem:",
                error,
            )

            return None

    def _set_face_image(self, face):
        card_lang = str(self.card.get("lang") or "en").casefold()

        # =====================================================
        # PRIMEIRO: usar a imagem que já veio da coleção
        # =====================================================
        pixmap = None

        if (
                self.current_face_index == 0
                and self.initial_pixmap
                and not self.initial_pixmap.isNull()
        ):
            pixmap = self.initial_pixmap

        # =====================================================
        # SEGUNDO: tentar imagem local da carta
        # =====================================================
        if pixmap is None or pixmap.isNull():
            image_path = self.card.get("image_path")

            if image_path:
                try:
                    path = Path(image_path)

                    if path.exists() and path.stat().st_size > 0:
                        local_pixmap = QPixmap(str(path))

                        if not local_pixmap.isNull():
                            pixmap = local_pixmap

                except Exception as error:
                    print(
                        "[DETAILS] Erro ao carregar imagem local:",
                        error,
                    )

        # =====================================================
        # TERCEIRO: fallback para cache da face
        #
        # IMPORTANTE:
        # NÃO baixar da internet ao abrir a janela.
        # =====================================================
        if (
                (pixmap is None or pixmap.isNull())
                and self.current_face_index != 0
        ):
            image_url = _best_image_url(face)

            if image_url:
                try:
                    pixmap = _download_pixmap(image_url)
                except Exception as error:
                    print(
                        "[DETAILS] Erro ao carregar imagem da face:",
                        error,
                    )

        # =====================================================
        # MOSTRAR IMAGEM
        # =====================================================
        if pixmap and not pixmap.isNull():
            self.image_status_label.clear()
            self.image_status_label.hide()

            target_size = self.image_label.size()

            # Garantir um tamanho válido caso o layout ainda
            # esteja sendo calculado.
            if (
                    target_size.width() <= 0
                    or target_size.height() <= 0
            ):

                target_width = 360
                target_height = 505

            else:

                target_width = target_size.width()
                target_height = target_size.height()

            self.image_label.setPixmap(
                pixmap.scaled(
                    target_width,
                    target_height,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            self.image_label.setText("")
            return

        # =====================================================
        # SEM IMAGEM
        # =====================================================
        self.image_label.clear()

        self.image_status_label.setText(
            "Imagem não disponível localmente."
        )
        sel
import re
import requests

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtGui import QPixmap


# =========================================================
# CONFIGURAÇÃO
# =========================================================

SYMBOLS_URL = (
    "https://api.scryfall.com/symbology"
)


# =========================================================
# CACHE
# =========================================================

_symbol_cache = {}


# =========================================================
# CARREGAR SÍMBOLOS
# =========================================================

def load_scryfall_symbols():
    """
    Carrega a tabela de símbolos do Scryfall.

    Retorna:

        {
            "{R}": "https://...",
            "{U}": "https://...",
            "{2}": "https://...",
            ...
        }
    """

    if _symbol_cache:
        return _symbol_cache

    try:

        response = requests.get(
            SYMBOLS_URL,
            headers={
                "User-Agent":
                    "MagicCollection/1.0 "
                    "(personal collection manager)",
                "Accept":
                    "application/json",
            },
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        for symbol in data.get(
            "data",
            []
        ):

            symbol_text = symbol.get(
                "symbol"
            )

            svg_uri = symbol.get(
                "svg_uri"
            )

            if (
                symbol_text
                and svg_uri
            ):

                _symbol_cache[
                    symbol_text
                ] = svg_uri

        print(
            "[SCRYFALL] Símbolos carregados:",
            len(_symbol_cache)
        )

    except Exception as error:

        print(
            "[SCRYFALL] Erro ao carregar "
            f"símbolos: {error}"
        )

    return _symbol_cache


# =========================================================
# EXTRAIR SÍMBOLOS
# =========================================================

def parse_mana_symbols(
    mana_cost
):

    if not mana_cost:
        return []

    return re.findall(
        r"\{[^}]+\}",
        str(mana_cost)
    )


# =========================================================
# TAREFA DE SÍMBOLOS
# =========================================================

class SymbolSignals(QObject):

    finished = Signal(
        dict
    )

    failed = Signal(
        str
    )


class SymbolTask(QRunnable):

    def __init__(
        self
    ):

        super().__init__()

        self.signals = (
            SymbolSignals()
        )

    def run(
        self
    ):

        try:

            symbols = (
                load_scryfall_symbols()
            )

            self.signals.finished.emit(
                symbols
            )

        except Exception as error:

            self.signals.failed.emit(
                str(error)
            )


# =========================================================
# TAREFA DE IMAGEM SVG
# =========================================================

class SymbolImageSignals(QObject):

    finished = Signal(
        str,
        bytes
    )

    failed = Signal(
        str,
        str
    )


class SymbolImageTask(QRunnable):

    def __init__(
        self,
        symbol,
        url
    ):

        super().__init__()

        self.symbol = symbol
        self.url = url

        self.signals = (
            SymbolImageSignals()
        )

    def run(
        self
    ):

        try:

            response = requests.get(
                self.url,
                headers={
                    "User-Agent":
                        "MagicCollection/1.0",
                    "Accept":
                        "image/svg+xml,image/*,*/*",
                },
                timeout=15
            )

            response.raise_for_status()

            data = response.content

            if not data:

                raise RuntimeError(
                    "SVG vazio."
                )

            self.signals.finished.emit(
                self.symbol,
                data
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro no símbolo:",
                self.symbol,
                error
            )

            self.signals.failed.emit(
                self.symbol,
                str(error)
            )


# =========================================================
# WIDGET DE MANA
# =========================================================

from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
)

from PySide6.QtCore import (
    Qt,
    QByteArray,
)

from PySide6.QtSvg import (
    QSvgRenderer,
)


class ManaSymbolsWidget(QWidget):

    def __init__(
        self,
        mana_cost=None,
        symbol_size=22,
        parent=None
    ):

        super().__init__(
            parent
        )

        self.mana_cost = (
            mana_cost or ""
        )

        self.symbol_size = (
            symbol_size
        )

        self.thread_pool = (
            QThreadPool()
        )

        self.symbol_urls = {}
        self.symbol_images = {}

        self.layout = QHBoxLayout(
            self
        )

        self.layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.layout.setSpacing(
            3
        )

        self.layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        self.build()

    # =====================================================
    # CONSTRUIR
    # =====================================================

    def build(
        self
    ):

        symbols = parse_mana_symbols(
            self.mana_cost
        )

        if not symbols:

            label = QLabel(
                "—"
            )

            label.setObjectName(
                "CardManaEmpty"
            )

            self.layout.addWidget(
                label
            )

            return

        symbol_table = (
            load_scryfall_symbols()
        )

        for symbol in symbols:

            url = symbol_table.get(
                symbol
            )

            if not url:

                self.add_fallback_symbol(
                    symbol
                )

                continue

            self.symbol_urls[
                symbol
            ] = url

            task = SymbolImageTask(
                symbol,
                url
            )

            task.signals.finished.connect(
                self.receive_symbol
            )

            task.signals.failed.connect(
                self.receive_symbol_error
            )

            self.thread_pool.start(
                task
            )

    # =====================================================
    # RECEBER
    # =====================================================

    def receive_symbol(
        self,
        symbol,
        data
    ):

        self.symbol_images[
            symbol
        ] = data

        self.rebuild_images()

    # =====================================================
    # ERRO
    # =====================================================

    def receive_symbol_error(
        self,
        symbol,
        error
    ):

        print(
            "[SCRYFALL] Falha ao baixar símbolo:",
            symbol,
            error
        )

        self.add_fallback_symbol(
            symbol
        )

    # =====================================================
    # FALLBACK
    # =====================================================

    def add_fallback_symbol(
        self,
        symbol
    ):

        label = QLabel(
            symbol
        )

        label.setObjectName(
            "CardManaFallback"
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        label.setMinimumWidth(
            self.symbol_size
        )

        self.layout.addWidget(
            label
        )

    # =====================================================
    # RENDERIZAR SVG
    # =====================================================

    def rebuild_images(
        self
    ):

        while self.layout.count():

            item = (
                self.layout.takeAt(0)
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()

        symbols = parse_mana_symbols(
            self.mana_cost
        )

        for symbol in symbols:

            data = self.symbol_images.get(
                symbol
            )

            if not data:

                self.add_fallback_symbol(
                    symbol
                )

                continue

            label = QLabel()

            label.setObjectName(
                "ManaSymbol"
            )

            label.setFixedSize(
                self.symbol_size,
                self.symbol_size
            )

            label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            renderer = QSvgRenderer(
                QByteArray(data)
            )

            pixmap = QPixmap(
                self.symbol_size,
                self.symbol_size
            )

            pixmap.fill(
                Qt.GlobalColor.transparent
            )

            from PySide6.QtGui import QPainter

            painter = QPainter(
                pixmap
            )

            renderer.render(
                painter
            )

            painter.end()

            label.setPixmap(
                pixmap
            )

            self.layout.addWidget(
                label
            )
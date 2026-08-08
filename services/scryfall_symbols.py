from pathlib import Path
import json
import re
import requests

from PySide6.QtCore import (
    QObject,
    Signal,
    QRunnable,
    QThreadPool,
    Qt,
    QByteArray,
)
from PySide6.QtGui import (
    QPixmap,
    QPainter,
)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
)


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parents[2]

SYMBOLS_DIR = (
    BASE_DIR
    / "cards"
    / "symbols"
)

MANA_SYMBOLS_DIR = (
    SYMBOLS_DIR
    / "mana"
)

SYMBOLS_CACHE_FILE = (
    SYMBOLS_DIR
    / "scryfall_symbology.json"
)

SYMBOLS_URL = (
    "https://api.scryfall.com/symbology"
)

USER_AGENT = (
    "MagicCollection/1.0 "
    "(personal collection manager)"
)


# =========================================================
# CACHE EM MEMÓRIA
# =========================================================

_symbol_cache = {}
_image_cache = {}

# Símbolos que estão sendo baixados neste momento.
_downloading_symbols = set()


# =========================================================
# GARANTIR PASTAS
# =========================================================

def ensure_symbols_directories():
    try:
        MANA_SYMBOLS_DIR.mkdir(
            parents=True,
            exist_ok=True,
        )
    except Exception as error:
        print(
            "[SCRYFALL] Erro ao criar pasta "
            "de símbolos:",
            error,
        )


# =========================================================
# NORMALIZAR NOME DO ARQUIVO
# =========================================================

def symbol_filename(symbol):
    """
    Converte:

        {R}  -> R
        {U}  -> U
        {5}  -> 5
        {2/W} -> 2-W
        {W/P} -> W-P
        {1000000} -> 1000000

    O nome é usado apenas para localizar o arquivo local.
    """

    value = str(symbol or "").strip()

    if not value:
        return ""

    value = value.replace(
        "{",
        "",
    ).replace(
        "}",
        "",
    )

    value = re.sub(
        r"[^a-zA-Z0-9_.\-]+",
        "-",
        value,
    )

    return value


# =========================================================
# LOCALIZAR ARQUIVO DO SÍMBOLO
# =========================================================

def find_local_symbol_file(symbol):
    """
    Procura o símbolo dentro de:

        cards/symbols/mana/

    Aceita SVG, PNG, WEBP e JPG/JPEG.
    """

    ensure_symbols_directories()

    filename = symbol_filename(symbol)

    if not filename:
        return None

    extensions = (
        ".svg",
        ".png",
        ".webp",
        ".jpg",
        ".jpeg",
    )

    for extension in extensions:

        path = (
            MANA_SYMBOLS_DIR
            / f"{filename}{extension}"
        )

        if (
            path.exists()
            and path.is_file()
            and path.stat().st_size > 0
        ):
            return path

    return None


# =========================================================
# CARREGAR ARQUIVO LOCAL
# =========================================================

def load_local_symbol(symbol):
    """
    Retorna:

        {
            "type": "svg" ou "pixmap",
            "data": bytes ou QPixmap,
            "path": Path
        }

    ou None se não existir.
    """

    cache_key = str(symbol)

    if cache_key in _image_cache:
        return _image_cache[cache_key]

    path = find_local_symbol_file(symbol)

    if not path:
        return None

    try:

        suffix = (
            path.suffix
            .lower()
        )

        if suffix == ".svg":

            data = path.read_bytes()

            if not data:
                return None

            result = {
                "type": "svg",
                "data": data,
                "path": path,
            }

        else:

            pixmap = QPixmap(
                str(path)
            )

            if pixmap.isNull():
                return None

            result = {
                "type": "pixmap",
                "data": pixmap,
                "path": path,
            }

        _image_cache[cache_key] = result

        return result

    except Exception as error:

        print(
            "[SCRYFALL] Erro ao carregar "
            "símbolo local:",
            symbol,
            error,
        )

        return None


# =========================================================
# CARREGAR CACHE DA API
# =========================================================

def _load_symbol_cache_file():
    global _symbol_cache

    if _symbol_cache:
        return _symbol_cache

    if not SYMBOLS_CACHE_FILE.exists():
        return {}

    try:

        data = json.loads(
            SYMBOLS_CACHE_FILE.read_text(
                encoding="utf-8"
            )
        )

        if isinstance(data, dict):

            _symbol_cache.update(
                data
            )

    except Exception as error:

        print(
            "[SCRYFALL] Erro ao ler cache "
            "de símbolos:",
            error,
        )

    return _symbol_cache


# =========================================================
# SALVAR CACHE DA API
# =========================================================

def _save_symbol_cache_file():
    try:

        ensure_symbols_directories()

        SYMBOLS_CACHE_FILE.write_text(
            json.dumps(
                _symbol_cache,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    except Exception as error:

        print(
            "[SCRYFALL] Erro ao salvar cache "
            "de símbolos:",
            error,
        )


# =========================================================
# CARREGAR SÍMBOLOS DO SCRYFALL
# =========================================================

def load_scryfall_symbols():
    """
    Carrega a tabela de símbolos.

    Primeiro tenta o cache local:

        cards/symbols/scryfall_symbology.json

    Só consulta o Scryfall se o cache ainda
    não existir.

    Retorna:

        {
            "{R}": "https://...",
            "{U}": "https://...",
            "{5}": "https://...",
            ...
        }
    """

    cached = _load_symbol_cache_file()

    if cached:
        return cached

    try:

        response = requests.get(
            SYMBOLS_URL,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        for symbol in data.get(
            "data",
            [],
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

        if _symbol_cache:

            _save_symbol_cache_file()

        print(
            "[SCRYFALL] Símbolos carregados:",
            len(_symbol_cache),
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

def parse_mana_symbols(mana_cost):
    if not mana_cost:
        return []

    return re.findall(
        r"\{[^}]+\}",
        str(mana_cost),
    )


# =========================================================
# SINAIS — TABELA DE SÍMBOLOS
# =========================================================

class SymbolSignals(QObject):

    finished = Signal(dict)

    failed = Signal(str)


# =========================================================
# TASK — TABELA DE SÍMBOLOS
# =========================================================

class SymbolTask(QRunnable):

    def __init__(self):

        super().__init__()

        self.signals = (
            SymbolSignals()
        )

    def run(self):

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
# SINAIS — IMAGEM
# =========================================================

class SymbolImageSignals(QObject):

    finished = Signal(
        str,
        bytes,
        str,
    )

    failed = Signal(
        str,
        str,
    )


# =========================================================
# TASK — BAIXAR E SALVAR IMAGEM
# =========================================================

class SymbolImageTask(QRunnable):

    def __init__(
        self,
        symbol,
        url,
    ):

        super().__init__()

        self.symbol = symbol
        self.url = url

        self.signals = (
            SymbolImageSignals()
        )

    def run(self):

        try:

            ensure_symbols_directories()

            # ---------------------------------------------
            # VERIFICAR NOVAMENTE
            # ---------------------------------------------

            local_file = (
                find_local_symbol_file(
                    self.symbol
                )
            )

            if local_file:

                data = local_file.read_bytes()

                if data:

                    suffix = (
                        local_file.suffix
                        .lower()
                    )

                    self.signals.finished.emit(
                        self.symbol,
                        data,
                        suffix,
                    )

                    return

            # ---------------------------------------------
            # DOWNLOAD
            # ---------------------------------------------

            response = requests.get(
                self.url,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "image/svg+xml,"
                        "image/png,"
                        "image/*,"
                        "*/*"
                    ),
                },
                timeout=20,
            )

            response.raise_for_status()

            data = response.content

            if not data:

                raise RuntimeError(
                    "Imagem do símbolo vazia."
                )

            # ---------------------------------------------
            # DETERMINAR FORMATO
            # ---------------------------------------------

            content_type = (
                response.headers.get(
                    "Content-Type",
                    ""
                ).lower()
            )

            if (
                "svg" in content_type
                or data.lstrip().startswith(
                    b"<svg"
                )
                or b"<svg" in data[:500]
            ):

                extension = ".svg"

            elif "png" in content_type:

                extension = ".png"

            elif "webp" in content_type:

                extension = ".webp"

            elif "jpeg" in content_type:

                extension = ".jpg"

            else:

                # Scryfall normalmente retorna SVG.
                extension = ".svg"

            filename = (
                symbol_filename(
                    self.symbol
                )
            )

            if not filename:

                raise RuntimeError(
                    "Nome de símbolo inválido."
                )

            target_path = (
                MANA_SYMBOLS_DIR
                / f"{filename}{extension}"
            )

            # ---------------------------------------------
            # ESCRITA ATÔMICA
            # ---------------------------------------------

            temp_path = Path(
                str(target_path)
                + ".tmp"
            )

            temp_path.write_bytes(
                data
            )

            temp_path.replace(
                target_path
            )

            self.signals.finished.emit(
                self.symbol,
                data,
                extension,
            )

        except Exception as error:

            print(
                "[SCRYFALL] Erro ao baixar "
                "símbolo:",
                self.symbol,
                error,
            )

            self.signals.failed.emit(
                self.symbol,
                str(error),
            )


# =========================================================
# WIDGET DE MANA
# =========================================================

class ManaSymbolsWidget(QWidget):

    def __init__(
        self,
        mana_cost=None,
        symbol_size=22,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.mana_cost = (
            mana_cost or ""
        )

        self.symbol_size = max(
            8,
            int(symbol_size or 22),
        )

        self.thread_pool = (
            QThreadPool()
        )

        self.thread_pool.setMaxThreadCount(
            3
        )

        self.symbol_images = {}

        self.symbol_states = {}

        self.layout = QHBoxLayout(
            self
        )

        self.layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.layout.setSpacing(
            3
        )

        self.layout.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        self.build()

    # =====================================================
    # BUILD
    # =====================================================

    def build(self):

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

        # -------------------------------------------------
        # PRIMEIRO: LOCAL
        # -------------------------------------------------

        missing_symbols = []

        for symbol in symbols:

            local = (
                load_local_symbol(
                    symbol
                )
            )

            if local:

                self.symbol_images[
                    symbol
                ] = local

                self.symbol_states[
                    symbol
                ] = "ready"

            else:

                missing_symbols.append(
                    symbol
                )

        # -------------------------------------------------
        # RENDER IMEDIATO
        # -------------------------------------------------

        self.rebuild_images()

        # -------------------------------------------------
        # SE TUDO ESTIVER LOCAL,
        # NÃO FAZ NENHUMA REQUISIÇÃO
        # -------------------------------------------------

        if not missing_symbols:
            return

        # -------------------------------------------------
        # CARREGAR TABELA DE URLS
        # -------------------------------------------------

        symbol_table = (
            load_scryfall_symbols()
        )

        if not symbol_table:

            for symbol in missing_symbols:

                self.symbol_states[
                    symbol
                ] = "failed"

            self.rebuild_images()

            return

        # -------------------------------------------------
        # BAIXAR APENAS O QUE NÃO EXISTE
        # -------------------------------------------------

        started = set()

        for symbol in missing_symbols:

            if symbol in started:
                continue

            started.add(symbol)

            url = symbol_table.get(
                symbol
            )

            if not url:

                self.symbol_states[
                    symbol
                ] = "failed"

                continue

            # Outra instância do widget pode
            # já estar baixando este símbolo.
            if symbol in _downloading_symbols:

                self.symbol_states[
                    symbol
                ] = "waiting"

                continue

            _downloading_symbols.add(
                symbol
            )

            self.symbol_states[
                symbol
            ] = "loading"

            task = SymbolImageTask(
                symbol,
                url,
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
    # RECEBER IMAGEM
    # =====================================================

    def receive_symbol(
        self,
        symbol,
        data,
        extension,
    ):

        _downloading_symbols.discard(
            symbol
        )

        try:

            # ---------------------------------------------
            # SALVAR NO CACHE EM MEMÓRIA
            # ---------------------------------------------

            if extension == ".svg":

                result = {
                    "type": "svg",
                    "data": data,
                }

            else:

                pixmap = QPixmap()

                if not pixmap.loadFromData(
                    data
                ):

                    raise RuntimeError(
                        "Não foi possível "
                        "carregar a imagem."
                    )

                result = {
                    "type": "pixmap",
                    "data": pixmap,
                }

            _image_cache[
                symbol
            ] = result

            self.symbol_images[
                symbol
            ] = result

            self.symbol_states[
                symbol
            ] = "ready"

            # ---------------------------------------------
            # ATUALIZAR ESTE WIDGET
            # ---------------------------------------------

            self.rebuild_images()

        except Exception as error:

            print(
                "[SCRYFALL] Erro ao processar "
                "símbolo:",
                symbol,
                error,
            )

            self.receive_symbol_error(
                symbol,
                str(error),
            )

    # =====================================================
    # ERRO
    # =====================================================

    def receive_symbol_error(
        self,
        symbol,
        error,
    ):

        _downloading_symbols.discard(
            symbol
        )

        print(
            "[SCRYFALL] Falha no símbolo:",
            symbol,
            error,
        )

        self.symbol_states[
            symbol
        ] = "failed"

        self.rebuild_images()

    # =====================================================
    # RENDERIZAR
    # =====================================================

    def rebuild_images(self):

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

        for symbol in symbols:

            image = (
                self.symbol_images.get(
                    symbol
                )
            )

            # -------------------------------------------------
            # IMAGEM PRONTA
            # -------------------------------------------------

            if image:

                label = (
                    self.create_symbol_label(
                        image
                    )
                )

                self.layout.addWidget(
                    label
                )

                continue

            # -------------------------------------------------
            # CARREGANDO
            # -------------------------------------------------

            state = (
                self.symbol_states.get(
                    symbol
                )
            )

            if state in (
                "loading",
                "waiting",
            ):

                # Mantém o símbolo textual enquanto
                # o arquivo ainda não existe.
                label = QLabel(
                    symbol
                )

                label.setObjectName(
                    "CardManaLoading"
                )

                label.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                label.setFixedSize(
                    self.symbol_size,
                    self.symbol_size,
                )

                self.layout.addWidget(
                    label
                )

                continue

            # -------------------------------------------------
            # FALLBACK
            # -------------------------------------------------

            self.add_fallback_symbol(
                symbol
            )

    # =====================================================
    # CRIAR LABEL DO SÍMBOLO
    # =====================================================

    def create_symbol_label(
        self,
        image,
    ):

        label = QLabel()

        label.setObjectName(
            "ManaSymbol"
        )

        label.setFixedSize(
            self.symbol_size,
            self.symbol_size,
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # -------------------------------------------------
        # SVG
        # -------------------------------------------------

        if image.get(
            "type"
        ) == "svg":

            data = image.get(
                "data"
            )

            renderer = QSvgRenderer(
                QByteArray(data)
            )

            if not renderer.isValid():

                label.setText(
                    "?"
                )

                return label

            pixmap = QPixmap(
                self.symbol_size,
                self.symbol_size,
            )

            pixmap.fill(
                Qt.GlobalColor.transparent
            )

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

            return label

        # -------------------------------------------------
        # PNG / WEBP / JPG
        # -------------------------------------------------

        pixmap = image.get(
            "data"
        )

        if isinstance(
            pixmap,
            QPixmap,
        ) and not pixmap.isNull():

            scaled = pixmap.scaled(
                self.symbol_size,
                self.symbol_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            label.setPixmap(
                scaled
            )

            return label

        label.setText(
            "?"
        )

        return label

    # =====================================================
    # FALLBACK
    # =====================================================

    def add_fallback_symbol(
        self,
        symbol,
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
    # LIMPEZA
    # =====================================================

    def closeEvent(
        self,
        event,
    ):

        try:

            self.thread_pool.clear()

        except Exception:
            pass

        super().closeEvent(
            event
        )
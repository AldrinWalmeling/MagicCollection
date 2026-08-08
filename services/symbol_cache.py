# services/symbol_cache.py

import json
import os
import re
import threading
from pathlib import Path

import requests


# ============================================================
# CONFIGURAÇÃO
# ============================================================

SYMBOLS_URL = "https://api.scryfall.com/symbology"

APP_NAME = "MagicCollection"

BASE_DIR = Path(__file__).resolve().parent.parent

SYMBOLS_DIR = BASE_DIR / "cards" / "symbols"
CACHE_DIR = BASE_DIR / "cache"

SYMBOL_TABLE_FILE = CACHE_DIR / "symbol_table.json"

REQUEST_TIMEOUT = 20

USER_AGENT = (
    "MagicCollection/1.0 "
    "(personal collection manager)"
)


# ============================================================
# CACHE EM MEMÓRIA
# ============================================================

_symbol_table = None
_symbol_table_lock = threading.Lock()

_downloaded_symbols = set()


# ============================================================
# DIRETÓRIOS
# ============================================================

def ensure_directories():
    """
    Garante que as pastas necessárias existam.
    """

    SYMBOLS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    CACHE_DIR.mkdir(
        parents=True,
        exist_ok=True
    )


# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalize_symbol(symbol):
    """
    Normaliza um símbolo de mana.

    Exemplos:

        {R} -> {R}
        { r } -> {R}
        R -> {R}
    """

    if symbol is None:
        return ""

    symbol = str(symbol).strip()

    if not symbol:
        return ""

    if not symbol.startswith("{"):
        symbol = "{" + symbol

    if not symbol.endswith("}"):
        symbol = symbol + "}"

    return symbol.upper()


# ============================================================
# NOME SEGURO DO ARQUIVO
# ============================================================

def symbol_to_filename(symbol):
    """
    Converte:

        {R}      -> R.svg
        {2}      -> 2.svg
        {2/W}    -> 2_W.svg
        {W/P}    -> W_P.svg
        {CHAOS}  -> CHAOS.svg
    """

    symbol = normalize_symbol(symbol)

    content = symbol[1:-1]

    content = re.sub(
        r"[^A-Za-z0-9_-]+",
        "_",
        content
    )

    content = content.strip("_")

    if not content:
        content = "unknown"

    return f"{content}.svg"


# ============================================================
# CAMINHO DO SÍMBOLO
# ============================================================

def get_symbol_path(symbol):
    """
    Retorna o caminho local do SVG.
    """

    ensure_directories()

    return SYMBOLS_DIR / symbol_to_filename(
        symbol
    )


# ============================================================
# EXISTÊNCIA LOCAL
# ============================================================

def has_local_symbol(symbol):
    """
    Verifica se o símbolo já foi baixado.
    """

    path = get_symbol_path(symbol)

    return (
        path.exists()
        and path.is_file()
        and path.stat().st_size > 0
    )


# ============================================================
# LER ARQUIVO LOCAL
# ============================================================

def load_local_symbol(symbol):
    """
    Carrega o SVG diretamente do disco.

    Retorna bytes ou None.
    """

    path = get_symbol_path(symbol)

    try:

        if not path.exists():
            return None

        data = path.read_bytes()

        if not data:
            return None

        return data

    except Exception as error:

        print(
            "[SYMBOL CACHE] Erro ao ler:",
            symbol,
            error
        )

        return None


# ============================================================
# SALVAR ARQUIVO LOCAL
# ============================================================

def save_local_symbol(symbol, data):
    """
    Salva o SVG no diretório:

        cards/symbols/
    """

    if not data:
        return False

    ensure_directories()

    path = get_symbol_path(symbol)

    temporary_path = path.with_suffix(
        ".tmp"
    )

    try:

        temporary_path.write_bytes(
            data
        )

        temporary_path.replace(
            path
        )

        _downloaded_symbols.add(
            normalize_symbol(symbol)
        )

        return True

    except Exception as error:

        print(
            "[SYMBOL CACHE] Erro ao salvar:",
            symbol,
            error
        )

        try:

            if temporary_path.exists():
                temporary_path.unlink()

        except Exception:
            pass

        return False


# ============================================================
# BAIXAR UM SÍMBOLO
# ============================================================

def download_symbol(
    symbol,
    svg_url
):
    """
    Baixa um símbolo do Scryfall apenas quando
    ele ainda não existe localmente.

    Retorna:

        bytes do SVG
        ou None em caso de erro.
    """

    symbol = normalize_symbol(
        symbol
    )

    if not symbol:
        return None

    # --------------------------------------------------------
    # JÁ EXISTE LOCALMENTE
    # --------------------------------------------------------

    local_data = load_local_symbol(
        symbol
    )

    if local_data:
        return local_data

    if not svg_url:
        return None

    # --------------------------------------------------------
    # DOWNLOAD
    # --------------------------------------------------------

    try:

        response = requests.get(
            svg_url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": (
                    "image/svg+xml,"
                    "image/*,*/*"
                ),
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.content

        if not data:
            raise RuntimeError(
                "Resposta vazia."
            )

        if save_local_symbol(
            symbol,
            data
        ):

            print(
                "[SYMBOL CACHE] Baixado:",
                symbol
            )

            return data

    except Exception as error:

        print(
            "[SYMBOL CACHE] Erro ao baixar:",
            symbol,
            error
        )

    return None


# ============================================================
# BAIXAR SOMENTE SE NECESSÁRIO
# ============================================================

def ensure_symbol(
    symbol,
    svg_url
):
    """
    Garante que um símbolo exista localmente.

    Se já existir:

        não faz request.

    Se não existir:

        baixa e salva.
    """

    symbol = normalize_symbol(
        symbol
    )

    if not symbol:
        return None

    local_data = load_local_symbol(
        symbol
    )

    if local_data:
        return local_data

    return download_symbol(
        symbol,
        svg_url
    )


# ============================================================
# TABELA DE SÍMBOLOS
# ============================================================

def load_symbol_table_from_disk():
    """
    Carrega a tabela de símbolos salva em cache.
    """

    global _symbol_table

    if _symbol_table is not None:
        return _symbol_table

    with _symbol_table_lock:

        if _symbol_table is not None:
            return _symbol_table

        if not SYMBOL_TABLE_FILE.exists():
            return {}

        try:

            data = json.loads(
                SYMBOL_TABLE_FILE.read_text(
                    encoding="utf-8"
                )
            )

            if isinstance(
                data,
                dict
            ):

                _symbol_table = data

                return _symbol_table

        except Exception as error:

            print(
                "[SYMBOL CACHE] Erro ao ler tabela:",
                error
            )

    return {}


# ============================================================
# SALVAR TABELA
# ============================================================

def save_symbol_table(
    table
):
    """
    Salva:

        {R} -> URL
        {U} -> URL
        {2} -> URL
        etc.
    """

    global _symbol_table

    ensure_directories()

    try:

        temporary_path = (
            SYMBOL_TABLE_FILE.with_suffix(
                ".tmp"
            )
        )

        temporary_path.write_text(
            json.dumps(
                table,
                ensure_ascii=False,
                indent=2
            ),
            encoding="utf-8"
        )

        temporary_path.replace(
            SYMBOL_TABLE_FILE
        )

        _symbol_table = table

        return True

    except Exception as error:

        print(
            "[SYMBOL CACHE] Erro ao salvar tabela:",
            error
        )

        return False


# ============================================================
# CARREGAR TABELA DO SCRYFALL
# ============================================================

def load_scryfall_symbol_table(
    force=False
):
    """
    Carrega a tabela de símbolos do Scryfall.

    A tabela inteira também fica em:

        cache/symbol_table.json

    Isso evita consultar a API toda vez que o programa abre.
    """

    global _symbol_table

    if not force:

        cached = load_symbol_table_from_disk()

        if cached:
            return cached

    with _symbol_table_lock:

        if (
            not force
            and _symbol_table
        ):
            return _symbol_table

        try:

            response = requests.get(
                SYMBOLS_URL,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": (
                        "application/json"
                    ),
                },
                timeout=REQUEST_TIMEOUT
            )

            response.raise_for_status()

            payload = response.json()

            table = {}

            for item in payload.get(
                "data",
                []
            ):

                symbol = normalize_symbol(
                    item.get(
                        "symbol"
                    )
                )

                svg_uri = item.get(
                    "svg_uri"
                )

                if (
                    symbol
                    and svg_uri
                ):

                    table[
                        symbol
                    ] = svg_uri

            if table:

                save_symbol_table(
                    table
                )

                print(
                    "[SYMBOL CACHE] Símbolos encontrados:",
                    len(table)
                )

                return table

        except Exception as error:

            print(
                "[SYMBOL CACHE] Erro ao consultar Scryfall:",
                error
            )

    return (
        _symbol_table
        or {}
    )


# ============================================================
# PARSE DE MANA
# ============================================================

def parse_mana_symbols(
    mana_cost
):
    """
    Extrai símbolos de uma mana cost.

    Exemplo:

        {2}{U}{U}

    retorna:

        ["{2}", "{U}", "{U}"]
    """

    if not mana_cost:
        return []

    return re.findall(
        r"\{[^}]+\}",
        str(mana_cost)
    )


# ============================================================
# PREPARAR MANA
# ============================================================

def prepare_mana_symbols(
    mana_cost
):
    """
    Garante que todos os símbolos necessários
    estejam disponíveis localmente.

    Retorna uma lista:

        [
            {
                "symbol": "{2}",
                "path": ".../2.svg",
                "data": b"..."
            },
            ...
        ]
    """

    symbols = parse_mana_symbols(
        mana_cost
    )

    if not symbols:
        return []

    table = load_scryfall_symbol_table()

    result = []

    for symbol in symbols:

        symbol = normalize_symbol(
            symbol
        )

        local_data = load_local_symbol(
            symbol
        )

        if not local_data:

            svg_url = table.get(
                symbol
            )

            if svg_url:

                local_data = ensure_symbol(
                    symbol,
                    svg_url
                )

        result.append(
            {
                "symbol": symbol,
                "path": str(
                    get_symbol_path(
                        symbol
                    )
                ),
                "data": local_data,
            }
        )

    return result


# ============================================================
# PEGAR BYTES DO SÍMBOLO
# ============================================================

def get_symbol_data(
    symbol
):
    """
    Retorna os bytes do SVG local.

    Não faz request automaticamente.
    """

    return load_local_symbol(
        symbol
    )


# ============================================================
# PEGAR CAMINHO
# ============================================================

def get_symbol_file(
    symbol
):
    """
    Retorna o caminho do SVG local
    se ele existir.
    """

    path = get_symbol_path(
        symbol
    )

    if (
        path.exists()
        and path.is_file()
    ):

        return str(path)

    return None


# ============================================================
# PRÉ-CARREGAR TODOS OS SÍMBOLOS
# ============================================================

def preload_all_symbols():
    """
    Baixa todos os símbolos disponíveis no Scryfall
    que ainda não existem em cards/symbols.

    Pode ser executado uma única vez na instalação
    ou em uma tarefa de background.
    """

    table = load_scryfall_symbol_table()

    if not table:
        return 0

    downloaded = 0

    for symbol, url in table.items():

        if has_local_symbol(
            symbol
        ):
            continue

        data = download_symbol(
            symbol,
            url
        )

        if data:
            downloaded += 1

    print(
        "[SYMBOL CACHE] Novos símbolos baixados:",
        downloaded
    )

    return downloaded


# ============================================================
# STATUS DO CACHE
# ============================================================

def get_cache_status():
    """
    Retorna informações úteis sobre o cache.
    """

    ensure_directories()

    files = list(
        SYMBOLS_DIR.glob(
            "*.svg"
        )
    )

    return {
        "directory": str(
            SYMBOLS_DIR
        ),
        "table_file": str(
            SYMBOL_TABLE_FILE
        ),
        "symbols": len(files),
        "table_cached": (
            SYMBOL_TABLE_FILE.exists()
        ),
    }


# ============================================================
# LIMPAR CACHE
# ============================================================

def clear_symbol_cache(
    clear_table=False
):
    """
    Remove os SVGs locais.

    Por padrão mantém a tabela do Scryfall.
    """

    global _symbol_table

    ensure_directories()

    removed = 0

    for file_path in SYMBOLS_DIR.glob(
        "*.svg"
    ):

        try:

            file_path.unlink()

            removed += 1

        except Exception as error:

            print(
                "[SYMBOL CACHE] Erro ao remover:",
                file_path,
                error
            )

    _downloaded_symbols.clear()

    if clear_table:

        try:

            if SYMBOL_TABLE_FILE.exists():
                SYMBOL_TABLE_FILE.unlink()

        except Exception as error:

            print(
                "[SYMBOL CACHE] Erro ao remover tabela:",
                error
            )

        _symbol_table = None

    return removed
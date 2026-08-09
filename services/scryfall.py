
import time

from threading import Lock

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import requests


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_URL = "https://api.scryfall.com"

HEADERS = {
    "User-Agent": (
        "MagicCollection/1.0 "
        "(personal collection manager)"
    ),
    "Accept": "application/json",
}


# =========================================================
# CONFIGURAÇÃO DE REDE
# =========================================================

# Tempo máximo para estabelecer conexão.
CONNECT_TIMEOUT = 5

# Tempo máximo esperando os dados chegarem.
READ_TIMEOUT = 15

# Quantidade de tentativas adicionais.
MAX_RETRIES = 2

# Pequeno intervalo entre requisições.
# Evita bombardear o Scryfall quando o usuário digita.
MIN_REQUEST_INTERVAL = 0.15


# =========================================================
# CACHE
# =========================================================

# Cache simples em memória.
#
# Estrutura:
#
# {
#     chave: (
#         timestamp,
#         resultado
#     )
# }
#
# O cache evita repetir imediatamente a mesma requisição.

_AUTOCOMPLETE_CACHE: Dict[
    Tuple[str, str],
    Tuple[float, List[str]],
] = {}

_CARD_CACHE: Dict[
    Tuple[str, str],
    Tuple[float, Optional[Dict[str, Any]]],
] = {}


# Tempo de vida do autocomplete.
AUTOCOMPLETE_CACHE_TTL = 30


# Tempo de vida dos dados completos da carta.
CARD_CACHE_TTL = 300


# Limites do cache.
MAX_AUTOCOMPLETE_CACHE = 200
MAX_CARD_CACHE = 200


# =========================================================
# CONTROLE DE CONCORRÊNCIA
# =========================================================

# A aplicação usa QThreadPool.
#
# Várias threads podem chamar o Scryfall ao mesmo tempo.
#
# O lock evita que várias requisições HTTP sejam disparadas
# simultaneamente pela mesma sessão.

_REQUEST_LOCK = Lock()

_LAST_REQUEST_TIME = 0.0


# =========================================================
# SESSÃO HTTP
# =========================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# =========================================================
# IDIOMAS SUPORTADOS PELO SCRYFALL
# =========================================================

SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "zhs": "Chinese Simplified",
    "zht": "Chinese Traditional",
}


# =========================================================
# NORMALIZAR IDIOMA
# =========================================================

def _normalize_language(
    language: str,
) -> str:

    language = str(
        language or "en"
    ).strip().lower()

    if language not in SUPPORTED_LANGUAGES:
        return "en"

    return language


# =========================================================
# LIMPAR CACHE
# =========================================================

def _cleanup_autocomplete_cache():

    if len(
        _AUTOCOMPLETE_CACHE
    ) <= MAX_AUTOCOMPLETE_CACHE:

        return

    # Remove as entradas mais antigas.
    ordered = sorted(
        _AUTOCOMPLETE_CACHE.items(),
        key=lambda item: item[1][0],
    )

    remove_count = max(
        1,
        len(ordered)
        - MAX_AUTOCOMPLETE_CACHE,
    )

    for key, _ in ordered[
        :remove_count
    ]:

        _AUTOCOMPLETE_CACHE.pop(
            key,
            None,
        )


def _cleanup_card_cache():

    if len(
        _CARD_CACHE
    ) <= MAX_CARD_CACHE:

        return

    ordered = sorted(
        _CARD_CACHE.items(),
        key=lambda item: item[1][0],
    )

    remove_count = max(
        1,
        len(ordered)
        - MAX_CARD_CACHE,
    )

    for key, _ in ordered[
        :remove_count
    ]:

        _CARD_CACHE.pop(
            key,
            None,
        )


# =========================================================
# ESPERAR ENTRE REQUISIÇÕES
# =========================================================

def _wait_before_request():

    global _LAST_REQUEST_TIME

    elapsed = (
        time.monotonic()
        - _LAST_REQUEST_TIME
    )

    if elapsed < MIN_REQUEST_INTERVAL:

        time.sleep(
            MIN_REQUEST_INTERVAL
            - elapsed
        )

    _LAST_REQUEST_TIME = (
        time.monotonic()
    )


# =========================================================
# REQUISIÇÃO HTTP ROBUSTA
# =========================================================

def _request_json(
    endpoint: str,
    params: Optional[
        Dict[str, Any]
    ] = None,
    retries: int = MAX_RETRIES,
) -> Optional[
    Dict[str, Any]
]:

    url = (
        f"{BASE_URL}"
        f"{endpoint}"
    )

    last_error = None

    for attempt in range(
        retries + 1
    ):

        try:

            # -------------------------------------------------
            # CONTROLAR REQUISIÇÕES
            # -------------------------------------------------

            with _REQUEST_LOCK:

                _wait_before_request()

                response = session.get(
                    url,
                    params=params,
                    timeout=(
                        CONNECT_TIMEOUT,
                        READ_TIMEOUT,
                    ),
                )

            # -------------------------------------------------
            # ERROS HTTP
            # -------------------------------------------------

            response.raise_for_status()

            data = response.json()

            if not isinstance(
                data,
                dict,
            ):

                raise ValueError(
                    "O Scryfall retornou "
                    "um JSON inválido."
                )

            return data

        except requests.Timeout as error:

            last_error = error

            print(
                "[SCRYFALL] Timeout "
                f"(tentativa "
                f"{attempt + 1}/"
                f"{retries + 1}):",
                error,
            )

            # Se ainda houver tentativa,
            # espera progressivamente.
            if attempt < retries:

                delay = (
                    1.0
                    * (
                        2 ** attempt
                    )
                )

                time.sleep(
                    delay
                )

                continue

            break

        except requests.ConnectionError as error:

            last_error = error

            print(
                "[SCRYFALL] Erro de conexão "
                f"(tentativa "
                f"{attempt + 1}/"
                f"{retries + 1}):",
                error,
            )

            if attempt < retries:

                delay = (
                    1.0
                    * (
                        2 ** attempt
                    )
                )

                time.sleep(
                    delay
                )

                continue

            break

        except requests.HTTPError as error:

            last_error = error

            status_code = (
                error.response.status_code
                if error.response is not None
                else None
            )

            print(
                "[SCRYFALL] Erro HTTP:",
                status_code,
                error,
            )

            # -------------------------------------------------
            # NÃO REPETIR ERROS DEFINITIVOS
            # -------------------------------------------------
            #
            # 400 / 404:
            # consulta inválida ou carta não encontrada.
            #
            # Não adianta repetir imediatamente.

            if status_code in (
                400,
                404,
            ):

                break

            # 429 = rate limit.
            #
            # Espera mais antes de tentar novamente.

            if status_code == 429:

                retry_after = (
                    response.headers.get(
                        "Retry-After"
                    )
                )

                try:

                    delay = float(
                        retry_after
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    delay = 3.0

            else:

                delay = (
                    1.0
                    * (
                        2 ** attempt
                    )
                )

            if attempt < retries:

                time.sleep(
                    delay
                )

                continue

            break

        except ValueError as error:

            last_error = error

            print(
                "[SCRYFALL] JSON inválido:",
                error,
            )

            break

        except requests.RequestException as error:

            last_error = error

            print(
                "[SCRYFALL] Erro de requisição "
                f"(tentativa "
                f"{attempt + 1}/"
                f"{retries + 1}):",
                error,
            )

            if attempt < retries:

                delay = (
                    1.0
                    * (
                        2 ** attempt
                    )
                )

                time.sleep(
                    delay
                )

                continue

            break

        except Exception as error:

            last_error = error

            print(
                "[SCRYFALL] Erro inesperado:",
                error,
            )

            break

    if last_error:

        print(
            "[SCRYFALL] Requisição falhou "
            "após todas as tentativas."
        )

    return None


# =========================================================
# AUTOCOMPLETE
# =========================================================

def autocomplete_card_names(
    query,
    language="en",
):
    """
    Retorna sugestões de cartas no
    idioma selecionado.

    Inglês:
        /cards/autocomplete

    Outros idiomas:
        /cards/search com lang:XX

    O resultado é armazenado em cache
    para evitar requisições repetidas.
    """

    query = str(
        query or ""
    ).strip()

    if len(query) < 2:

        return []

    language = _normalize_language(
        language
    )

    cache_key = (
        language,
        query.casefold(),
    )

    # =====================================================
    # CACHE
    # =====================================================

    cached = (
        _AUTOCOMPLETE_CACHE.get(
            cache_key
        )
    )

    if cached:

        timestamp, suggestions = (
            cached
        )

        if (
            time.monotonic()
            - timestamp
            < AUTOCOMPLETE_CACHE_TTL
        ):

            return list(
                suggestions
            )

        _AUTOCOMPLETE_CACHE.pop(
            cache_key,
            None,
        )

    # =====================================================
    # INGLÊS
    # =====================================================

    if language == "en":

        data = _request_json(
            "/cards/autocomplete",
            params={
                "q": query,
            },
        )

        if not data:

            return []

        suggestions = data.get(
            "data",
            [],
        )

        if not isinstance(
            suggestions,
            list,
        ):

            return []

        suggestions = [
            str(item)
            for item in suggestions
            if item
        ][:8]

        _AUTOCOMPLETE_CACHE[
            cache_key
        ] = (
            time.monotonic(),
            suggestions,
        )

        _cleanup_autocomplete_cache()

        return list(
            suggestions
        )

    # =====================================================
    # OUTROS IDIOMAS
    # =====================================================

    data = _request_json(
        "/cards/search",
        params={
            "q": (
                f'lang:{language} '
                f'name:"{query}"'
            ),
            "unique": "cards",
            "order": "name",
        },
    )

    if not data:

        return []

    cards = data.get(
        "data",
        [],
    )

    if not isinstance(
        cards,
        list,
    ):

        return []

    suggestions = []

    for card in cards:

        if not isinstance(
            card,
            dict,
        ):

            continue

        # -------------------------------------------------
        # NOME LOCALIZADO
        # -------------------------------------------------

        localized_name = (
            card.get(
                "printed_name"
            )
            or card.get(
                "name"
            )
        )

        if not localized_name:

            continue

        localized_name = str(
            localized_name
        ).strip()

        if not localized_name:

            continue

        if (
            localized_name
            not in suggestions
        ):

            suggestions.append(
                localized_name
            )

        if len(
            suggestions
        ) >= 8:

            break

    _AUTOCOMPLETE_CACHE[
        cache_key
    ] = (
        time.monotonic(),
        suggestions,
    )

    _cleanup_autocomplete_cache()

    return list(
        suggestions
    )


# =========================================================
# BUSCAR CARTA PELO NOME
# =========================================================

def get_card_by_name(
    name,
    language="en",
):
    """
    Busca uma carta pelo nome.

    Inglês:
        /cards/named

    Outros idiomas:
        /cards/search com lang:XX

    Retorna o objeto completo da carta.
    """

    name = str(
        name or ""
    ).strip()

    if not name:

        return None

    language = _normalize_language(
        language
    )

    cache_key = (
        language,
        name.casefold(),
    )

    # =====================================================
    # CACHE
    # =====================================================

    cached = (
        _CARD_CACHE.get(
            cache_key
        )
    )

    if cached:

        timestamp, card = cached

        if (
            time.monotonic()
            - timestamp
            < CARD_CACHE_TTL
        ):

            return card

        _CARD_CACHE.pop(
            cache_key,
            None,
        )

    # =====================================================
    # INGLÊS
    # =====================================================

    if language == "en":

        data = _request_json(
            "/cards/named",
            params={
                "exact": name,
            },
        )

        if not data:

            return None

        _CARD_CACHE[
            cache_key
        ] = (
            time.monotonic(),
            data,
        )

        _cleanup_card_cache()

        return data

    # =====================================================
    # OUTROS IDIOMAS
    # =====================================================

    data = _request_json(
        "/cards/search",
        params={
            "q": (
                f'lang:{language} '
                f'name:"{name}"'
            ),
            "unique": "cards",
        },
    )

    if not data:

        return None

    cards = data.get(
        "data",
        [],
    )

    if not isinstance(
        cards,
        list,
    ):

        return None

    if not cards:

        return None

    # =====================================================
    # PROCURAR NOME LOCALIZADO EXATO
    # =====================================================

    normalized_name = (
        name.casefold()
    )

    for card in cards:

        if not isinstance(
            card,
            dict,
        ):

            continue

        printed_name = str(
            card.get(
                "printed_name"
            )
            or ""
        ).strip()

        card_name = str(
            card.get(
                "name"
            )
            or ""
        ).strip()

        # -------------------------------------------------
        # printed_name
        # -------------------------------------------------

        if (
            printed_name.casefold()
            == normalized_name
        ):

            _CARD_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                card,
            )

            _cleanup_card_cache()

            return card

        # -------------------------------------------------
        # name
        # -------------------------------------------------

        if (
            card_name.casefold()
            == normalized_name
        ):

            _CARD_CACHE[
                cache_key
            ] = (
                time.monotonic(),
                card,
            )

            _cleanup_card_cache()

            return card

    # =====================================================
    # FALLBACK
    # =====================================================
    #
    # Se o Scryfall encontrou uma carta para a consulta,
    # mas o nome não bateu exatamente, usa o primeiro
    # resultado, mantendo o comportamento anterior.

    card = cards[0]

    if not isinstance(
        card,
        dict,
    ):

        return None

    _CARD_CACHE[
        cache_key
    ] = (
        time.monotonic(),
        card,
    )

    _cleanup_card_cache()

    return card


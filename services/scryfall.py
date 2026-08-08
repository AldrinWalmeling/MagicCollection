import requests


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_URL = "https://api.scryfall.com"

HEADERS = {
    "User-Agent": "MagicCollection/1.0",
    "Accept": "application/json",
}


# =========================================================
# SESSÃO HTTP
# =========================================================

session = requests.Session()

session.headers.update(
    HEADERS
)


# =========================================================
# AUTOCOMPLETE
# =========================================================

def autocomplete_card_names(query):
    """
    Retorna sugestões de nomes de cartas
    através da API do Scryfall.
    """

    query = query.strip()

    # Não pesquisa textos muito pequenos
    if len(query) < 2:
        return []

    try:

        response = session.get(
            f"{BASE_URL}/cards/autocomplete",

            params={
                "q": query
            },

            timeout=5
        )

        response.raise_for_status()

        data = response.json()

        suggestions = data.get(
            "data",
            []
        )

        # Garante que sempre retornamos uma lista
        if not isinstance(
            suggestions,
            list
        ):
            return []

        # Limita resultados
        return suggestions[:8]

    except requests.RequestException as error:

        print(
            f"Erro no autocomplete do Scryfall: {error}"
        )

        return []

    except ValueError as error:

        print(
            f"Resposta inválida do Scryfall: {error}"
        )

        return []

    except Exception as error:

        print(
            f"Erro inesperado no autocomplete: {error}"
        )

        return []


# =========================================================
# BUSCAR CARTA PELO NOME
# =========================================================

def get_card_by_name(name):
    """
    Busca os dados completos de uma carta
    pelo nome exato no Scryfall.
    """

    name = name.strip()

    if not name:
        return None

    try:

        response = session.get(
            f"{BASE_URL}/cards/named",

            params={
                "exact": name
            },

            timeout=8
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict
        ):
            return None

        return data

    except requests.RequestException as error:

        print(
            f"Erro ao buscar carta no Scryfall: {error}"
        )

        return None

    except ValueError as error:

        print(
            f"Resposta inválida do Scryfall: {error}"
        )

        return None

    except Exception as error:

        print(
            f"Erro inesperado ao buscar carta: {error}"
        )

        return None
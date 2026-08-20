"""
SERVIÇO DE REFERÊNCIA DE PREÇO (IMPRINT)
========================================

Gerencia a "referência em Inglês" usada para calcular valores
quando o modo "Inglês (Imprint)" está ativo.

CONCEITO IMPORTANTE
-------------------

A carta física da coleção NUNCA é alterada:

- idioma original
- quantidade
- favoritos
- tags
- decks
- histórico
- identificação do print original

O que é armazenado é apenas uma REFERÊNCIA para a versão em
inglês correspondente:

    price_reference_scryfall_id
    price_reference_name
    price_ref_usd
    price_ref_usd_foil
    price_ref_eur
    price_ref_tix
    price_ref_rarity

Quando o modo "Inglês (Imprint)" está ativo, as consultas de
valor do Dashboard usam esses preços de referência no lugar
do preço do print original (quando existem).

Quando o modo é "Idioma original", os preços originais são
usados normalmente.

Se não existir referência, o comportamento atual é mantido.
Nenhum preço é inventado.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings

from database import get_connection
from services.scryfall import (
    get_card_by_name,
    get_card_printings,
)


# =========================================================
# MODO DE PREÇO
# =========================================================
#
# "original" -> usa o preço do print/idioma original.
# "imprint"  -> usa a referência em Inglês quando existir.

PRICING_MODE_ORIGINAL = "original"
PRICING_MODE_IMPRINT = "imprint"

PRICING_MODE_LABELS = {
    PRICING_MODE_ORIGINAL: "Idioma original",
    PRICING_MODE_IMPRINT: "Inglês (Imprint)",
}


def get_pricing_mode() -> str:
    settings = QSettings(
        "MagicCollection",
        "MagicCollection",
    )

    mode = settings.value(
        "pricing/mode",
        PRICING_MODE_ORIGINAL,
        type=str,
    )

    if mode not in (
        PRICING_MODE_ORIGINAL,
        PRICING_MODE_IMPRINT,
    ):
        mode = PRICING_MODE_ORIGINAL

    return mode


def set_pricing_mode(mode: str) -> None:
    if mode not in (
        PRICING_MODE_ORIGINAL,
        PRICING_MODE_IMPRINT,
    ):
        return

    settings = QSettings(
        "MagicCollection",
        "MagicCollection",
    )

    settings.setValue(
        "pricing/mode",
        mode,
    )


def pricing_mode_label(mode: str) -> str:
    return PRICING_MODE_LABELS.get(
        mode,
        PRICING_MODE_LABELS[PRICING_MODE_ORIGINAL],
    )


def is_imprint_mode() -> bool:
    return (
        get_pricing_mode()
        == PRICING_MODE_IMPRINT
    )


# =========================================================
# EXPRESSÃO SQL DO PREÇO EFETIVO
# =========================================================
#
# Retorna a expressão que deve ser usada nas consultas de
# valor do Dashboard de acordo com o modo ativo.
#
# Modo original:
#     COALESCE(price_usd, 0)
#
# Modo imprint:
#     COALESCE(price_ref_usd, price_usd, 0)


def price_column_expression(
    column: str = "usd",
    alias: str | None = None,
) -> str:
    ref_column = {
        "usd": "price_ref_usd",
        "eur": "price_ref_eur",
        "tix": "price_ref_tix",
    }.get(
        column,
        "price_ref_usd",
    )

    original_column = {
        "usd": "price_usd",
        "eur": "price_eur",
        "tix": "price_tix",
    }.get(
        column,
        "price_usd",
    )

    if is_imprint_mode():

        expression = (
            f"COALESCE({ref_column}, {original_column}, 0)"
        )

    else:

        expression = (
            f"COALESCE({original_column}, 0)"
        )

    if alias:
        expression = (
            f"{expression} AS {alias}"
        )

    return expression


# =========================================================
# BANCO DE DADOS
# =========================================================


def _get_connection():
    return get_connection()


# =========================================================
# ENCONTRAR REFERÊNCIA EM INGLÊS
# =========================================================
#
# card é um dict com ao menos:
#     name  -> nome em inglês (coluna "name" do Scryfall)
#
# A busca usa o nome inglês armazenado no banco.
# Se o print encontrado não tiver preço, procura entre os
# prints ingleses da mesma carta.


def find_english_reference(card) -> dict | None:
    if not isinstance(
        card,
        dict,
    ):
        return None

    name = str(
        card.get("name")
        or card.get("printed_name")
        or ""
    ).strip()

    if not name:
        return None

    # Se a carta já é inglesa, ela mesma é a referência.
    if (
        str(
            card.get("lang")
            or ""
        ).strip().casefold()
        == "en"
    ):
        return None

    english_card = get_card_by_name(
        name,
        language="en",
    )

    if not isinstance(
        english_card,
        dict,
    ):
        return None

    reference = _reference_from_scryfall_card(
        english_card
    )

    if reference is not None:
        return reference

    # Procura entre os prints ingleses por um com preço.
    printings = get_card_printings(
        english_card
    )

    for printing in printings:

        if not isinstance(
            printing,
            dict,
        ):

            continue

        if (
            str(
                printing.get("lang")
                or ""
            ).strip().casefold()
            != "en"
        ):

            continue

        reference = _reference_from_scryfall_card(
            printing
        )

        if reference is not None:
            return reference

    return None


def _parse_price(value) -> float | None:
    try:

        if value in (
            None,
            "",
        ):

            return None

        value = float(value)

        if value <= 0:
            return None

        return value

    except (
        TypeError,
        ValueError,
    ):

        return None


def _reference_from_scryfall_card(
    card_data: dict,
) -> dict | None:
    scryfall_id = (
        card_data.get("scryfall_id")
        or card_data.get("id")
    )

    if not scryfall_id:
        return None

    scryfall_id = str(
        scryfall_id
    ).strip()

    if not scryfall_id:
        return None

    prices = (
        card_data.get("prices")
        or {}
    )

    price_usd = _parse_price(
        prices.get("usd")
    )

    if price_usd is None:
        return None

    return {
        "scryfall_id": scryfall_id,
        "name": (
            card_data.get("name")
            or card_data.get("printed_name")
            or "Carta"
        ),
        "lang": "en",
        "rarity": (
            card_data.get("rarity")
            or ""
        ),
        "price_usd": price_usd,
        "price_usd_foil": _parse_price(
            prices.get("usd_foil")
        ),
        "price_eur": _parse_price(
            prices.get("eur")
        ),
        "price_tix": _parse_price(
            prices.get("tix")
        ),
    }


# =========================================================
# SALVAR REFERÊNCIA
# =========================================================


def set_price_reference(
    card_id,
    reference: dict,
) -> bool:
    if not reference:
        return False

    try:

        card_id = int(
            card_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return False

    if card_id <= 0:
        return False

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE cards
            SET
                price_reference_scryfall_id = ?,
                price_reference_name = ?,
                price_ref_usd = ?,
                price_ref_usd_foil = ?,
                price_ref_eur = ?,
                price_ref_tix = ?,
                price_ref_rarity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                reference.get("scryfall_id"),
                reference.get("name"),
                reference.get("price_usd"),
                reference.get("price_usd_foil"),
                reference.get("price_eur"),
                reference.get("price_tix"),
                reference.get("rarity"),
                card_id,
            ),
        )

        connection.commit()

        return True

    except Exception as error:

        print(
            "[IMPRINT] Erro ao salvar referência:",
            error,
        )

        connection.rollback()

        return False

    finally:

        connection.close()


def clear_price_reference(
    card_id,
) -> bool:
    try:

        card_id = int(
            card_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return False

    if card_id <= 0:
        return False

    connection = get_connection()

    try:

        connection.execute(
            """
            UPDATE cards
            SET
                price_reference_scryfall_id = NULL,
                price_reference_name = NULL,
                price_ref_usd = NULL,
                price_ref_usd_foil = NULL,
                price_ref_eur = NULL,
                price_ref_tix = NULL,
                price_ref_rarity = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                card_id,
            ),
        )

        connection.commit()

        return True

    except Exception as error:

        print(
            "[IMPRINT] Erro ao limpar referência:",
            error,
        )

        connection.rollback()

        return False

    finally:

        connection.close()


# =========================================================
# CONSULTAS AUXILIARES
# =========================================================


def get_reference_summary() -> dict:
    """
    Resumo das referências armazenadas.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total
            FROM cards
            WHERE
                quantity > 0
                AND price_reference_scryfall_id IS NOT NULL
            """
        )

        row = cursor.fetchone()

        with_reference = int(
            row["total"]
            or 0
        )

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total
            FROM cards
            WHERE quantity > 0
            """
        )

        row = cursor.fetchone()

        total = int(
            row["total"]
            or 0
        )

    finally:

        connection.close()

    return {
        "total": total,
        "with_reference": with_reference,
        "without_reference": max(
            0,
            total - with_reference,
        ),
    }


def get_cards_pending_reference() -> list[dict]:
    """
    Cartas da coleção (quantity > 0) que ainda não possuem
    referência em inglês.
    """

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                printed_name,
                lang,
                quantity
            FROM cards
            WHERE
                quantity > 0
                AND (
                    price_reference_scryfall_id IS NULL
                    OR TRIM(price_reference_scryfall_id) = ''
                )
                AND COALESCE(lang, '') != 'en'
            ORDER BY
                quantity DESC,
                id ASC
            """
        )

        return [
            dict(row)
            for row in cursor.fetchall()
        ]

    finally:

        connection.close()
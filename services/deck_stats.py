"""
Estatísticas do deck.

Calcula, a partir das cartas devolvidas por ``get_deck_cards``:

    - curva de mana
    - distribuição por tipo
    - distribuição por identidade de cor
    - valor estimado do deck
"""

from services.deck_formats import (
    card_color_identity,
)


CURVE_BUCKETS = 8


TYPE_ORDER = (
    "creature",
    "instant",
    "sorcery",
    "artifact",
    "enchantment",
    "planeswalker",
    "battle",
    "land",
    "other",
)


TYPE_LABELS = {
    "creature": "Criaturas",
    "instant": "Instantâneas",
    "sorcery": "Feitiços",
    "artifact": "Artefatos",
    "enchantment": "Encantamentos",
    "planeswalker": "Planeswalkers",
    "battle": "Batalhas",
    "land": "Terrenos",
    "other": "Outros",
}


GROUP_LABELS = {
    "creatures": "Criaturas",
    "spells": "Mágicas",
    "lands": "Terrenos",
    "others": "Outros",
}


_TYPE_KEYWORDS = (
    ("land", ("land", "terreno")),
    ("creature", ("creature", "criatura")),
    ("planeswalker", ("planeswalker",)),
    ("battle", ("battle", "batalha")),
    ("instant", ("instant", "instantânea", "instantanea")),
    ("sorcery", ("sorcery", "feitiço", "feitico")),
    ("artifact", ("artifact", "artefato")),
    ("enchantment", ("enchantment", "encantamento")),
)


def card_type_key(type_line):
    text = str(type_line or "").casefold()

    for key, keywords in _TYPE_KEYWORDS:
        if any(word in text for word in keywords):
            return key

    return "other"


def type_group(type_key):
    if type_key == "creature":
        return "creatures"

    if type_key == "land":
        return "lands"

    if type_key in ("instant", "sorcery"):
        return "spells"

    if type_key in ("artifact", "enchantment", "planeswalker", "battle"):
        return "others"

    return "others"


def card_cmc(card):
    value = card.get("cmc")

    try:
        if value is not None:
            return int(float(value))
    except (TypeError, ValueError):
        pass

    return _cmc_from_mana_cost(card.get("mana_cost"))


def _cmc_from_mana_cost(mana_cost):
    text = str(mana_cost or "")

    if not text:
        return 0

    total = 0

    for symbol in text.replace("{", " ").replace("}", " ").split():
        symbol = symbol.upper()

        if symbol == "X":
            continue

        if symbol.isdigit():
            total += int(symbol)
            continue

        if "/" in symbol:
            parts = symbol.split("/")

            digits = [part for part in parts if part.isdigit()]

            total += int(digits[0]) if digits else 1
            continue

        total += 1

    return total


def card_price(card):
    try:
        return float(card.get("price_usd") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def compute_deck_stats(cards):
    cards = list(cards or [])

    curve = [0] * CURVE_BUCKETS

    types = {key: 0 for key in TYPE_ORDER}

    groups = {key: 0 for key in GROUP_LABELS}

    colors = {color: 0 for color in ("W", "U", "B", "R", "G", "C")}

    multicolor = 0

    total = 0
    unique = 0
    value = 0.0

    most_expensive = None
    cheapest = None

    for card in cards:
        quantity = max(0, int(card.get("deck_quantity") or 0))

        if quantity <= 0:
            continue

        total += quantity
        unique += 1

        type_key = card_type_key(card.get("type_line"))

        types[type_key] += quantity

        groups[type_group(type_key)] += quantity

        if type_key != "land":
            bucket = max(0, min(CURVE_BUCKETS - 1, card_cmc(card)))

            curve[bucket] += quantity

        identity = card_color_identity(card)

        if not identity:
            colors["C"] += quantity
        else:
            for color in identity:
                colors[color] += quantity

            if len(identity) > 1:
                multicolor += quantity

        price = card_price(card)

        value += price * quantity

        if price > 0:
            if most_expensive is None or price > most_expensive[1]:
                most_expensive = (card, price)

            if cheapest is None or price < cheapest[1]:
                cheapest = (card, price)

    return {
        "total": total,
        "unique": unique,
        "curve": curve,
        "types": types,
        "groups": groups,
        "colors": colors,
        "multicolor": multicolor,
        "value_usd": value,
        "most_expensive": most_expensive,
        "cheapest": cheapest,
    }


def format_usd(value):
    try:
        value = float(value or 0.0)
    except (TypeError, ValueError):
        value = 0.0

    return "$ " + f"{value:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")

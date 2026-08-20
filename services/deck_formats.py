"""
Formatos de deck e validação de regras.

Cada formato descreve:

    - tamanho mínimo / máximo do deck principal
    - limite de cópias da mesma carta
    - tamanho do sideboard
    - se exige comandante
    - qual chave usar em ``cards.legalities`` (Scryfall)

A função ``validate_deck`` recebe as cartas do deck (como
dicionários vindos de ``get_deck_cards``) e devolve os problemas
encontrados, para a interface exibir a análise do deck.
"""

import json


# =========================================================
# FORMATOS
# =========================================================

FORMATS = {

    "livre": {
        "label": "Livre",
        "legality_key": None,
        "min_cards": 0,
        "max_cards": None,
        "max_copies": None,
        "max_sideboard": None,
        "requires_commander": False,
        "singleton": False,
    },

    "standard": {
        "label": "Padrão",
        "legality_key": "standard",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "pioneer": {
        "label": "Pioneer",
        "legality_key": "pioneer",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "modern": {
        "label": "Modern",
        "legality_key": "modern",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "legacy": {
        "label": "Legacy",
        "legality_key": "legacy",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "vintage": {
        "label": "Vintage",
        "legality_key": "vintage",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "pauper": {
        "label": "Pauper",
        "legality_key": "pauper",
        "min_cards": 60,
        "max_cards": None,
        "max_copies": 4,
        "max_sideboard": 15,
        "requires_commander": False,
        "singleton": False,
    },

    "commander": {
        "label": "Commander",
        "legality_key": "commander",
        "min_cards": 100,
        "max_cards": 100,
        "max_copies": 1,
        "max_sideboard": 0,
        "requires_commander": True,
        "singleton": True,
    },

    "brawl": {
        "label": "Brawl",
        "legality_key": "brawl",
        "min_cards": 60,
        "max_cards": 60,
        "max_copies": 1,
        "max_sideboard": 0,
        "requires_commander": True,
        "singleton": True,
    },
}


DEFAULT_FORMAT = "livre"

BASIC_LANDS = {
    "plains",
    "island",
    "swamp",
    "mountain",
    "forest",
    "wastes",
    "planalto",
    "ilha",
    "pântano",
    "pantano",
    "montanha",
    "floresta",
}

UNLIMITED_COPIES_TEXT = "A quantity of any number of cards named"


# =========================================================
# HELPERS
# =========================================================

def normalize_format(format_key):
    key = str(format_key or "").strip().lower()

    if key in FORMATS:
        return key

    for candidate, data in FORMATS.items():
        if data["label"].lower() == key:
            return candidate

    return DEFAULT_FORMAT


def get_format(format_key):
    return FORMATS[normalize_format(format_key)]


def format_label(format_key):
    return get_format(format_key)["label"]


def format_choices():
    return [
        (key, data["label"])
        for key, data in FORMATS.items()
    ]


def _loads(value, default):
    if value is None or value == "":
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return default

    return parsed if parsed is not None else default


def card_legalities(card):
    return _loads(card.get("legalities"), {}) or {}


def card_color_identity(card):
    identity = _loads(card.get("color_identity"), []) or []

    return [
        str(color).upper()
        for color in identity
        if str(color).upper() in ("W", "U", "B", "R", "G")
    ]


def card_colors(card):
    colors = _loads(card.get("colors"), []) or []

    return [
        str(color).upper()
        for color in colors
        if str(color).upper() in ("W", "U", "B", "R", "G")
    ]


def is_basic_land(card):
    type_line = str(card.get("type_line") or "").casefold()

    if "basic" in type_line and "land" in type_line:
        return True

    if "básico" in type_line and "terreno" in type_line:
        return True

    name = str(card.get("name") or "").casefold().strip()

    return name in BASIC_LANDS and "land" in type_line


def _card_name(card):
    printed = str(card.get("printed_name") or "").strip()

    if printed:
        return printed

    return str(card.get("name") or "Carta").strip()


def deck_color_identity(cards):
    identity = set()

    for card in cards:
        if int(card.get("deck_quantity") or 0) <= 0:
            continue

        identity.update(card_color_identity(card))

    return [
        color
        for color in ("W", "U", "B", "R", "G")
        if color in identity
    ]


# =========================================================
# VALIDAÇÃO
# =========================================================

def validate_deck(cards, format_key, total_cards=None):
    """
    Valida o deck contra as regras do formato escolhido.

    Retorna:

        {
            "format": "commander",
            "label": "Commander",
            "total": 87,
            "valid": False,
            "errors": [...],
            "warnings": [...],
        }
    """

    cards = list(cards or [])

    rules = get_format(format_key)

    if total_cards is None:
        total_cards = sum(
            max(0, int(card.get("deck_quantity") or 0))
            for card in cards
        )

    errors = []
    warnings = []

    # -----------------------------------------------------
    # TAMANHO DO DECK
    # -----------------------------------------------------

    min_cards = rules["min_cards"] or 0
    max_cards = rules["max_cards"]

    if min_cards and total_cards < min_cards:
        errors.append(
            f"Faltam {min_cards - total_cards} cartas "
            f"(mínimo de {min_cards})."
        )

    if max_cards and total_cards > max_cards:
        errors.append(
            f"{total_cards - max_cards} cartas acima do limite "
            f"de {max_cards}."
        )

    # -----------------------------------------------------
    # CÓPIAS E LEGALIDADE
    # -----------------------------------------------------

    max_copies = rules["max_copies"]

    legality_key = rules["legality_key"]

    illegal = []
    restricted = []
    over_limit = []

    for card in cards:
        quantity = max(0, int(card.get("deck_quantity") or 0))

        if quantity <= 0:
            continue

        name = _card_name(card)

        if max_copies and quantity > max_copies and not is_basic_land(card):
            over_limit.append(f"{name} (×{quantity})")

        if not legality_key:
            continue

        status = str(
            card_legalities(card).get(legality_key) or ""
        ).lower()

        if status == "restricted":
            if quantity > 1:
                restricted.append(f"{name} (×{quantity})")

        elif status and status != "legal":
            illegal.append(name)

    if over_limit:
        limit_text = (
            "1 cópia"
            if max_copies == 1
            else f"{max_copies} cópias"
        )

        errors.append(
            f"{len(over_limit)} cartas acima do limite de "
            f"{limit_text}: " + ", ".join(over_limit[:4])
            + ("..." if len(over_limit) > 4 else "")
        )

    if illegal:
        errors.append(
            f"{len(illegal)} cartas não permitidas em "
            f"{rules['label']}: " + ", ".join(illegal[:4])
            + ("..." if len(illegal) > 4 else "")
        )

    if restricted:
        errors.append(
            "Cartas restritas com mais de 1 cópia: "
            + ", ".join(restricted[:4])
        )

    # -----------------------------------------------------
    # AVISOS
    # -----------------------------------------------------

    if rules["requires_commander"]:
        warnings.append(
            "Escolha um comandante e confira a identidade de cor: "
            + ("".join(deck_color_identity(cards)) or "incolor")
        )

    lands = sum(
        max(0, int(card.get("deck_quantity") or 0))
        for card in cards
        if "land" in str(card.get("type_line") or "").casefold()
        or "terreno" in str(card.get("type_line") or "").casefold()
    )

    if total_cards >= 40 and lands == 0:
        warnings.append(
            "O deck não possui terrenos."
        )

    return {
        "format": normalize_format(format_key),
        "label": rules["label"],
        "total": total_cards,
        "min_cards": min_cards,
        "max_cards": max_cards,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
    }

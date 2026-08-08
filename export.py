
import csv
import json


# =========================================================
# HELPERS
# =========================================================

def _value(card, key, default="—"):
    """
    Retorna um valor tratado para exportação.

    Evita que campos inexistentes apareçam como None.
    """
    value = card.get(key)

    if value is None or value == "":
        return default

    return value


def _quantity(card):
    """
    Retorna a quantidade da carta como inteiro.
    """
    try:
        return int(card.get("quantity", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _power_toughness(card):
    """
    Retorna Power/Toughness quando disponíveis.

    Algumas cartas não possuem esses campos.
    """
    power = card.get("power")
    toughness = card.get("toughness")

    if power is None and toughness is None:
        return "—"

    power = power if power not in (None, "") else "?"
    toughness = toughness if toughness not in (None, "") else "?"

    return f"{power}/{toughness}"


def _card_faces(card):
    """
    Preserva informações de faces de cartas transformáveis,
    modais ou similares.
    """
    faces = card.get("card_faces")

    if not faces:
        return None

    treated_faces = []

    for face in faces:
        treated_faces.append({
            "nome": _value(face, "name"),
            "mana": _value(face, "mana_cost"),
            "tipo": _value(face, "type_line"),
            "efeito": _value(face, "oracle_text"),
            "power": _value(face, "power"),
            "toughness": _value(face, "toughness"),
            "lealdade": _value(face, "loyalty"),
            "imagem": _value(face, "image_uris", None),
        })

    return treated_faces


# =========================================================
# BACKUP COMPLETO
# =========================================================

def export_collection_json(filepath, cards):

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            cards,
            file,
            ensure_ascii=False,
            indent=4
        )


# =========================================================
# TRATADO JSON
# =========================================================

def export_collection_treated_json(filepath, cards):

    treated_cards = []

    for card in cards:

        treated_card = {
            "nome": _value(card, "name"),
            "nome_impresso": _value(card, "printed_name"),
            "mana": _value(card, "mana_cost"),
            "tipo": _value(card, "type_line"),
            "efeito": _value(card, "oracle_text"),

            "power": _value(card, "power"),
            "toughness": _value(card, "toughness"),
            "power_toughness": _power_toughness(card),

            "lealdade": _value(card, "loyalty"),
            "defesa": _value(card, "defense"),

            "quantidade": _quantity(card),

            "set": _value(card, "set_name"),
            "set_code": _value(card, "set_code"),
            "numero_coletor": _value(card, "collector_number"),
            "idioma": _value(card, "lang"),

            "scryfall_id": _value(card, "scryfall_id"),
            "imagem": _value(card, "image_url"),
        }

        faces = _card_faces(card)

        if faces:
            treated_card["faces"] = faces

        treated_cards.append(treated_card)

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            treated_cards,
            file,
            ensure_ascii=False,
            indent=4
        )



# =========================================================
# TRATADO TXT
# =========================================================

def export_collection_txt(
    filepath,
    cards
):

    with open(
        filepath,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "══════════════════════════════════════════════════\n"
        )

        file.write(
            "              MINHA COLEÇÃO — MAGIC\n"
        )

        file.write(
            "══════════════════════════════════════════════════\n\n"
        )

        total_cards = sum(
            card.get("quantity", 0)
            for card in cards
        )

        unique_cards = len(cards)

        file.write(
            f"Total de cartas: {total_cards}\n"
        )

        file.write(
            f"Cartas únicas: {unique_cards}\n\n"
        )

        for card in cards:

            name = card.get(
                "name"
            ) or "Sem nome"

            mana = card.get(
                "mana_cost"
            ) or "—"

            type_line = card.get(
                "type_line"
            ) or "—"

            oracle_text = card.get(
                "oracle_text"
            ) or "—"

            power = card.get(
                "power"
            )

            toughness = card.get(
                "toughness"
            )

            quantity = card.get(
                "quantity",
                0
            )

            file.write(
                "──────────────────────────────────────────────────\n"
            )

            file.write(
                f"{name.upper()}\n"
            )

            file.write(
                "──────────────────────────────────────────────────\n\n"
            )

            file.write(
                f"Mana: {mana}\n\n"
            )

            file.write(
                f"Tipo: {type_line}\n\n"
            )

            file.write(
                "Efeito:\n"
            )

            file.write(
                f"{oracle_text}\n\n"
            )

            # =============================================
            # PODER / RESISTÊNCIA
            # =============================================

            if power is not None or toughness is not None:

                power_value = power or "—"
                toughness_value = toughness or "—"

                file.write(
                    f"Poder/Resistência: {power_value}/{toughness_value}\n\n"
                )

            file.write(
                f"Quantidade: {quantity}\n\n"
            )



# =========================================================
# CSV
# =========================================================

def export_collection_csv(filepath, cards):

    fieldnames = [
        "scryfall_id",
        "name",
        "printed_name",

        "lang",

        "set_code",
        "set_name",
        "collector_number",

        "mana_cost",
        "type_line",
        "oracle_text",

        "power",
        "toughness",
        "loyalty",
        "defense",

        "image_url",

        "quantity"
    ]

    with open(
        filepath,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )

        writer.writeheader()

        for card in cards:

            row = {
                "scryfall_id": card.get("scryfall_id", ""),
                "name": card.get("name", ""),
                "printed_name": card.get("printed_name", ""),

                "lang": card.get("lang", ""),

                "set_code": card.get("set_code", ""),
                "set_name": card.get("set_name", ""),
                "collector_number": card.get(
                    "collector_number",
                    ""
                ),

                "mana_cost": card.get("mana_cost", ""),
                "type_line": card.get("type_line", ""),
                "oracle_text": card.get("oracle_text", ""),

                "power": card.get("power", ""),
                "toughness": card.get("toughness", ""),
                "loyalty": card.get("loyalty", ""),
                "defense": card.get("defense", ""),

                "image_url": card.get("image_url", ""),

                "quantity": _quantity(card)
            }

            writer.writerow(row)

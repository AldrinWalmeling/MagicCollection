import csv
import json


# =========================================================
# BACKUP COMPLETO
# =========================================================

def export_collection_json(
    filepath,
    cards
):

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

def export_collection_treated_json(
    filepath,
    cards
):

    treated_cards = []

    for card in cards:

        treated_cards.append({
            "nome": card.get("name"),
            "mana": card.get("mana_cost"),
            "tipo": card.get("type_line"),
            "efeito": card.get("oracle_text"),
            "quantidade": card.get("quantity")
        })

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

            file.write(
                f"Quantidade: {quantity}\n\n"
            )


# =========================================================
# CSV
# =========================================================

def export_collection_csv(
    filepath,
    cards
):

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
            fieldnames=fieldnames
        )

        writer.writeheader()

        for card in cards:

            writer.writerow(card)
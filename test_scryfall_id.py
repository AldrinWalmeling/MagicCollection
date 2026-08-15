from services.scryfall import (
    get_card_by_scryfall_id,
)


scryfall_id = "COLOQUE_UM_ID_REAL_AQUI"


card = get_card_by_scryfall_id(
    scryfall_id
)

if not card:
    print(
        "Carta não encontrada."
    )

else:
    print(
        "ID:",
        card.get("id")
    )

    print(
        "Nome:",
        card.get("name")
    )

    print(
        "Set:",
        card.get("set")
    )

    print(
        "Collector:",
        card.get(
            "collector_number"
        )
    )

    print(
        "Idioma:",
        card.get("lang")
    )

    print(
        "Preços:",
        card.get("prices")
    )
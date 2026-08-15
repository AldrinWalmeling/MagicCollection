from database import (
    get_all_cards,
    get_card_by_id,
)


cards = get_all_cards()

if not cards:
    print(
        "Nenhuma carta encontrada."
    )

else:
    card_id = cards[0][0]

    card = get_card_by_id(
        card_id
    )

    print(
        "\n===== METADADOS ====="
    )

    print(
        "ID:",
        card.get("id")
    )

    print(
        "Nome:",
        card.get("name")
    )

    print(
        "Scryfall ID:",
        card.get("scryfall_id")
    )

    print(
        "Oracle ID:",
        card.get("oracle_id")
    )

    print(
        "Illustration ID:",
        card.get("illustration_id")
    )

    print(
        "Released:",
        card.get("released_at")
    )

    print(
        "Artist:",
        card.get("artist")
    )

    print(
        "Frame:",
        card.get("frame")
    )

    print(
        "Keywords:",
        card.get("keywords")
    )

    print(
        "Games:",
        card.get("games")
    )

    print(
        "Legalities:",
        card.get("legalities")
    )
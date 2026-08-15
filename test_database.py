from database import (
    get_connection,
)


connection = get_connection()

try:
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,

            -- IDENTIDADE
            scryfall_id,
            oracle_id,
            illustration_id,

            -- VERSÃO / IMPRESSÃO
            lang,
            set_code,
            set_name,
            collector_number,
            rarity,

            -- QUANTIDADE
            quantity,

            -- IMAGEM
            image_url,
            image_path,

            -- PREFERÊNCIAS SALVAS
            preferred_language,
            preferred_variant,
            preferred_finish,
            preferred_image,
            preferred_face,

            -- METADADOS
            released_at,
            artist,
            frame,

            -- PREÇOS
            price_usd,
            price_usd_foil,
            price_usd_etched,
            price_eur,
            price_eur_foil,
            price_tix

        FROM cards

        ORDER BY id
        """
    )

    rows = cursor.fetchall()

    if not rows:
        print(
            "Nenhuma carta encontrada no banco."
        )

    for row in rows:

        data = dict(row)

        print()
        print(
            "=" * 70
        )

        print(
            f"ID: {data.get('id')}"
        )

        print(
            f"Nome: {data.get('name')}"
        )

        print()
        print(
            "===== IDENTIDADE ====="
        )

        print(
            f"Scryfall ID: "
            f"{data.get('scryfall_id')}"
        )

        print(
            f"Oracle ID: "
            f"{data.get('oracle_id')}"
        )

        print(
            f"Illustration ID: "
            f"{data.get('illustration_id')}"
        )

        print()
        print(
            "===== IMPRESSÃO / VERSÃO ====="
        )

        print(
            f"Idioma: "
            f"{data.get('lang')}"
        )

        print(
            f"Set Code: "
            f"{data.get('set_code')}"
        )

        print(
            f"Set Name: "
            f"{data.get('set_name')}"
        )

        print(
            f"Collector Number: "
            f"{data.get('collector_number')}"
        )

        print(
            f"Raridade: "
            f"{data.get('rarity')}"
        )

        print()
        print(
            "===== QUANTIDADE ====="
        )

        print(
            f"Quantidade: "
            f"{data.get('quantity')}"
        )

        print()
        print(
            "===== IMAGEM ====="
        )

        print(
            f"Image URL:"
        )

        print(
            data.get('image_url')
        )

        print()

        print(
            f"Image Path:"
        )

        print(
            data.get('image_path')
        )

        print()
        print(
            "===== PREFERÊNCIA SALVA ====="
        )

        print(
            f"Preferred Language: "
            f"{data.get('preferred_language')}"
        )

        print(
            f"Preferred Variant: "
            f"{data.get('preferred_variant')}"
        )

        print(
            f"Preferred Finish: "
            f"{data.get('preferred_finish')}"
        )

        print(
            f"Preferred Image:"
        )

        print(
            data.get('preferred_image')
        )

        print()

        print(
            f"Preferred Face: "
            f"{data.get('preferred_face')}"
        )

        print()
        print(
            "===== METADADOS ====="
        )

        print(
            f"Released: "
            f"{data.get('released_at')}"
        )

        print(
            f"Artist: "
            f"{data.get('artist')}"
        )

        print(
            f"Frame: "
            f"{data.get('frame')}"
        )

        print()
        print(
            "===== PREÇOS ====="
        )

        print(
            f"USD: "
            f"{data.get('price_usd')}"
        )

        print(
            f"USD Foil: "
            f"{data.get('price_usd_foil')}"
        )

        print(
            f"USD Etched: "
            f"{data.get('price_usd_etched')}"
        )

        print(
            f"EUR: "
            f"{data.get('price_eur')}"
        )

        print(
            f"EUR Foil: "
            f"{data.get('price_eur_foil')}"
        )

        print(
            f"TIX: "
            f"{data.get('price_tix')}"
        )

        print(
            "=" * 70
        )

finally:
    connection.close()
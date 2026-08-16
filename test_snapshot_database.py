from database import get_connection


connection = get_connection()

try:

    cursor = connection.cursor()

    # =====================================================
    # SNAPSHOT PRINCIPAL
    # =====================================================

    print()
    print("=" * 70)
    print("COLLECTION SNAPSHOTS")
    print("=" * 70)

    cursor.execute(
        """
        SELECT
            id,
            snapshot_date,
            total_cards,
            unique_cards,
            total_sets,
            value_usd,
            usd_brl,
            value_brl
        FROM collection_snapshots
        ORDER BY id
        """
    )

    snapshots = cursor.fetchall()

    for row in snapshots:

        print()
        print(
            f"ID: {row['id']}"
        )

        print(
            f"Data: {row['snapshot_date']}"
        )

        print(
            f"Total de cartas: {row['total_cards']}"
        )

        print(
            f"Cartas únicas: {row['unique_cards']}"
        )

        print(
            f"Sets: {row['total_sets']}"
        )

        print(
            f"Valor USD: {row['value_usd']}"
        )

        print(
            f"USD/BRL: {row['usd_brl']}"
        )

        print(
            f"Valor BRL: {row['value_brl']}"
        )

    # =====================================================
    # ITENS DOS SNAPSHOTS
    # =====================================================

    print()
    print("=" * 70)
    print("COLLECTION SNAPSHOT ITEMS")
    print("=" * 70)

    cursor.execute(
        """
        SELECT

            collection_snapshot_items.id,

            collection_snapshot_items.snapshot_id,

            collection_snapshot_items.card_id,

            cards.name,

            collection_snapshot_items.quantity,

            collection_snapshot_items.finish,

            collection_snapshot_items.unit_price_usd,

            collection_snapshot_items.unit_price_brl,

            collection_snapshot_items.total_value_usd,

            collection_snapshot_items.total_value_brl

        FROM collection_snapshot_items

        INNER JOIN cards
            ON cards.id =
                collection_snapshot_items.card_id

        ORDER BY
            collection_snapshot_items.id
        """
    )

    items = cursor.fetchall()

    for row in items:

        print()
        print(
            f"Item ID: {row['id']}"
        )

        print(
            f"Snapshot ID: {row['snapshot_id']}"
        )

        print(
            f"Carta ID: {row['card_id']}"
        )

        print(
            f"Carta: {row['name']}"
        )

        print(
            f"Quantidade: {row['quantity']}"
        )

        print(
            f"Finish: {row['finish']}"
        )

        print(
            f"Preço unitário USD: "
            f"{row['unit_price_usd']}"
        )

        print(
            f"Preço unitário BRL: "
            f"{row['unit_price_brl']}"
        )

        print(
            f"Valor total USD: "
            f"{row['total_value_usd']}"
        )

        print(
            f"Valor total BRL: "
            f"{row['total_value_brl']}"
        )

finally:

    connection.close()
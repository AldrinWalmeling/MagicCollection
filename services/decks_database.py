import sqlite3
import json
from datetime import datetime

from database import (
    get_connection,
    ensure_card_exists,
)


# =========================================================
# DECKS DATABASE
# =========================================================
#
# Responsabilidade deste arquivo:
#
# - Criar / migrar tabelas de decks
# - Criar / excluir / renomear decks
# - Gerenciar cartas dentro dos decks
# - Gerenciar quantidades
# - Gerenciar preview do deck
# - Estatísticas do deck
#
# IMPORTANTE:
#
# Uma carta adicionada diretamente ao deck NÃO é adicionada
# à coleção.
#
# Quando uma carta do Scryfall ainda não existe em "cards",
# ela é criada com quantity = 0.
#
# Assim:
#
#     cards.quantity > 0
#         -> carta pertence à coleção
#
#     cards.quantity == 0
#         -> carta pode existir somente como referência
#            usada por um deck
#
# A relação real do deck fica em:
#
#     deck_cards
#
# =========================================================


# =========================================================
# HELPERS
# =========================================================

def _to_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_name(value):
    return str(value or "").strip()


def _row_to_dict(row):
    if row is None:
        return None

    if isinstance(row, sqlite3.Row):
        return dict(row)

    if isinstance(row, dict):
        return dict(row)

    try:
        return dict(row)
    except Exception:
        return row


# =========================================================
# INICIALIZAÇÃO
# =========================================================

def initialize_decks_database():
    """
    Cria e migra as tabelas relacionadas aos decks.

    Pode ser chamada várias vezes sem destruir os dados.
    """

    connection = get_connection()

    try:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            "PRAGMA foreign_keys = ON"
        )

        # =================================================
        # DECKS
        # =================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decks (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                name TEXT NOT NULL,

                preview_card_id INTEGER,

                preview_image_path TEXT,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # =================================================
        # MIGRAÇÃO DA TABELA DECKS
        # =================================================

        cursor.execute(
            """
            PRAGMA table_info(decks)
            """
        )

        deck_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "preview_card_id" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN preview_card_id INTEGER
                """
            )

        if "preview_image_path" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN preview_image_path TEXT
                """
            )

        if "created_at" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN created_at TIMESTAMP
                """
            )

        if "updated_at" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN updated_at TIMESTAMP
                """
            )

        if "format" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN format TEXT DEFAULT 'livre'
                """
            )

        if "favorite" not in deck_columns:

            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN favorite INTEGER DEFAULT 0
                """
            )

        cursor.execute(
            """
            UPDATE decks
            SET format = 'livre'
            WHERE format IS NULL OR format = ''
            """
        )

        cursor.execute(
            """
            UPDATE decks
            SET favorite = 0
            WHERE favorite IS NULL
            """
        )

        cursor.execute(
            """
            UPDATE decks
            SET created_at = COALESCE(
                created_at,
                CURRENT_TIMESTAMP
            )
            WHERE created_at IS NULL
            """
        )

        cursor.execute(
            """
            UPDATE decks
            SET updated_at = COALESCE(
                updated_at,
                created_at,
                CURRENT_TIMESTAMP
            )
            WHERE updated_at IS NULL
            """
        )

        # =================================================
        # DECK CARDS
        # =================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deck_cards (

                deck_id INTEGER NOT NULL,

                card_id INTEGER NOT NULL,

                quantity INTEGER NOT NULL DEFAULT 1,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                PRIMARY KEY (
                    deck_id,
                    card_id
                ),

                FOREIGN KEY (
                    deck_id
                )
                REFERENCES decks(id)
                ON DELETE CASCADE,

                FOREIGN KEY (
                    card_id
                )
                REFERENCES cards(id)
                ON DELETE CASCADE
            )
            """
        )

        # =================================================
        # ÍNDICES
        # =================================================

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_deck_cards_deck_id

            ON deck_cards(deck_id)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_deck_cards_card_id

            ON deck_cards(card_id)
            """
        )

        connection.commit()

        print(
            "[DECKS DATABASE] Inicializado com sucesso."
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao inicializar:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# DECK EXISTE
# =========================================================

def deck_exists(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM decks
            WHERE id = ?
            LIMIT 1
            """,
            (deck_id,)
        )

        return cursor.fetchone() is not None

    except Exception:

        return False

    finally:

        connection.close()


# =========================================================
# CRIAR DECK
# =========================================================

def create_deck(name):
    name = _clean_name(name)

    if not name:
        return None

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO decks (
                name
            )
            VALUES (?)
            """,
            (name,)
        )

        deck_id = cursor.lastrowid

        connection.commit()

        print(
            "[DECKS DATABASE] Deck criado:",
            deck_id,
            name
        )

        return int(deck_id)

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao criar deck:",
            error
        )

        return None

    finally:

        connection.close()


# =========================================================
# OBTER DECK
# =========================================================

def get_deck(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return None

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                d.id,
                d.name,
                d.created_at,
                d.updated_at,

                d.preview_card_id,
                d.preview_image_path,

                d.format,
                d.favorite,

                COALESCE(
                    SUM(dc.quantity),
                    0
                ) AS card_count,

                COUNT(
                    DISTINCT dc.card_id
                ) AS unique_cards

            FROM decks d

            LEFT JOIN deck_cards dc
                ON dc.deck_id = d.id

            WHERE d.id = ?

            GROUP BY
                d.id
            """,
            (deck_id,)
        )

        row = cursor.fetchone()

        return _row_to_dict(row)

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao obter deck:",
            error
        )

        return None

    finally:

        connection.close()


# =========================================================
# COMPATIBILIDADE
# =========================================================

def get_deck_by_id(deck_id):
    return get_deck(deck_id)


# =========================================================
# TODOS OS DECKS
# =========================================================

def get_all_decks():
    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                d.id,
                d.name,
                d.created_at,
                d.updated_at,

                d.preview_card_id,
                d.preview_image_path,

                d.format,
                d.favorite,

                COALESCE(
                    SUM(dc.quantity),
                    0
                ) AS card_count,

                COUNT(
                    DISTINCT dc.card_id
                ) AS unique_cards,

                COALESCE(
                    SUM(dc.quantity * COALESCE(c.price_usd, 0)),
                    0
                ) AS estimated_value,

                GROUP_CONCAT(c.color_identity, '|') AS color_identities

            FROM decks d

            LEFT JOIN deck_cards dc
                ON dc.deck_id = d.id

            LEFT JOIN cards c
                ON c.id = dc.card_id

            GROUP BY
                d.id

            ORDER BY
                d.updated_at DESC,
                d.id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao listar decks:",
            error
        )

        return []

    finally:

        connection.close()


# =========================================================
# RENOMEAR DECK
# =========================================================

def rename_deck(deck_id, name):
    deck_id = _to_int(deck_id)
    name = _clean_name(name)

    if deck_id <= 0 or not name:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks
            SET
                name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                name,
                deck_id
            )
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao renomear deck:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# FORMATO DO DECK
# =========================================================

def set_deck_format(deck_id, format_key):
    deck_id = _to_int(deck_id)

    format_key = _clean_name(format_key).lower()

    if deck_id <= 0 or not format_key:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks
            SET
                format = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                format_key,
                deck_id
            )
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao definir formato:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# FAVORITO
# =========================================================

def set_deck_favorite(deck_id, favorite):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks
            SET favorite = ?
            WHERE id = ?
            """,
            (
                1 if favorite else 0,
                deck_id
            )
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao definir favorito:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# EXCLUIR DECK
# =========================================================

def delete_deck(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM decks
            WHERE id = ?
            """,
            (deck_id,)
        )

        deleted = cursor.rowcount > 0

        connection.commit()

        return deleted

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao excluir deck:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# ATUALIZAR DATA DO DECK
# =========================================================

def touch_deck(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks
            SET
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (deck_id,)
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception:

        connection.rollback()

        return False

    finally:

        connection.close()


# =========================================================
# CARTAS DO DECK
# =========================================================

def get_deck_cards(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return []

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                c.id,

                c.scryfall_id,

                c.name,
                c.printed_name,

                c.lang,

                c.set_code,
                c.set_name,

                c.collector_number,

                c.mana_cost,

                c.type_line,
                c.oracle_text,

                c.rarity,
                c.cmc,
                c.colors,
                c.color_identity,
                c.legalities,

                c.price_usd,
                c.price_eur,

                c.power,
                c.toughness,

                c.image_url,
                c.image_path,
                c.card_faces,
                c.card_printings,
                c.preferred_language,
                c.preferred_variant,
                c.preferred_finish,
                c.preferred_image,
                c.preferred_face,
                c.favorite,
                c.custom_tags,
                c.last_view,

                c.quantity
                    AS collection_quantity,

                dc.quantity
                    AS deck_quantity,

                dc.created_at
                    AS deck_added_at,

                dc.updated_at
                    AS deck_updated_at

            FROM deck_cards dc

            INNER JOIN cards c
                ON c.id = dc.card_id

            WHERE dc.deck_id = ?

            ORDER BY
                c.name COLLATE NOCASE ASC
            """,
            (deck_id,)
        )

        rows = cursor.fetchall()

        cards = []

        for row in rows:
            card = dict(row)

            for key in (
                "card_faces",
                "card_printings",
            ):
                value = card.get(key)

                if not value:
                    card[key] = [] if key == "card_printings" else None
                    continue

                if isinstance(value, str):
                    try:
                        card[key] = json.loads(value)
                    except (
                        TypeError,
                        ValueError,
                        json.JSONDecodeError,
                    ):
                        card[key] = [] if key == "card_printings" else None

            cards.append(card)

        return cards

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao obter cartas:",
            error
        )

        return []

    finally:

        connection.close()


# =========================================================
# QUANTIDADES DAS CARTAS
# =========================================================

def get_deck_card_quantities(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return {}

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                card_id,
                quantity
            FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,)
        )

        rows = cursor.fetchall()

        return {
            int(row["card_id"]):
            int(row["quantity"] or 0)
            for row in rows
        }

    except Exception:

        return {}

    finally:

        connection.close()


# =========================================================
# QUANTIDADE DE UMA CARTA
# =========================================================

def get_deck_card_quantity(
    deck_id,
    card_id
):
    deck_id = _to_int(deck_id)
    card_id = _to_int(card_id)

    if deck_id <= 0 or card_id <= 0:
        return 0

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT quantity
            FROM deck_cards
            WHERE
                deck_id = ?
                AND card_id = ?
            """,
            (
                deck_id,
                card_id
            )
        )

        row = cursor.fetchone()

        if not row:
            return 0

        return int(
            row["quantity"] or 0
        )

    except Exception:

        return 0

    finally:

        connection.close()


# =========================================================
# TOTAL DE CARTAS DO DECK
# =========================================================

def get_deck_total_cards(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return 0

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COALESCE(
                    SUM(quantity),
                    0
                )
            FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,)
        )

        row = cursor.fetchone()

        return int(
            row[0] or 0
        )

    except Exception:

        return 0

    finally:

        connection.close()


# =========================================================
# CARTAS ÚNICAS DO DECK
# =========================================================

def get_deck_unique_cards(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return 0

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*)
            FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,)
        )

        row = cursor.fetchone()

        return int(
            row[0] or 0
        )

    except Exception:

        return 0

    finally:

        connection.close()


# =========================================================
# ESTATÍSTICAS DO DECK
# =========================================================

def get_deck_stats(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:

        return {
            "total_cards": 0,
            "unique_cards": 0,
            "cards_with_collection": 0,
            "cards_only_in_deck": 0,
        }

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                COALESCE(
                    SUM(dc.quantity),
                    0
                ) AS total_cards,

                COUNT(
                    DISTINCT dc.card_id
                ) AS unique_cards,

                COUNT(
                    DISTINCT CASE
                        WHEN c.quantity > 0
                        THEN dc.card_id
                    END
                ) AS cards_with_collection,

                COUNT(
                    DISTINCT CASE
                        WHEN c.quantity <= 0
                        THEN dc.card_id
                    END
                ) AS cards_only_in_deck

            FROM deck_cards dc

            INNER JOIN cards c
                ON c.id = dc.card_id

            WHERE dc.deck_id = ?
            """,
            (deck_id,)
        )

        row = cursor.fetchone()

        if not row:

            return {
                "total_cards": 0,
                "unique_cards": 0,
                "cards_with_collection": 0,
                "cards_only_in_deck": 0,
            }

        return {
            "total_cards": int(
                row["total_cards"] or 0
            ),

            "unique_cards": int(
                row["unique_cards"] or 0
            ),

            "cards_with_collection": int(
                row["cards_with_collection"] or 0
            ),

            "cards_only_in_deck": int(
                row["cards_only_in_deck"] or 0
            ),
        }

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro nas estatísticas:",
            error
        )

        return {
            "total_cards": 0,
            "unique_cards": 0,
            "cards_with_collection": 0,
            "cards_only_in_deck": 0,
        }

    finally:

        connection.close()


# =========================================================
# CARTAS DISPONÍVEIS NA COLEÇÃO
# =========================================================

def get_cards_available_for_deck(
    deck_id,
    search_text=""
):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return []

    search_text = _clean_name(
        search_text
    )

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        if search_text:

            search = f"%{search_text}%"

            cursor.execute(
                """
                SELECT

                    c.id,
                    c.scryfall_id,

                    c.name,
                    c.printed_name,

                    c.lang,

                    c.set_code,
                    c.set_name,

                    c.collector_number,

                    c.mana_cost,

                    c.type_line,
                    c.oracle_text,

                    c.power,
                    c.toughness,

                    c.image_url,
                    c.image_path,

                    c.quantity
                        AS collection_quantity,

                    COALESCE(
                        dc.quantity,
                        0
                    ) AS deck_quantity

                FROM cards c

                LEFT JOIN deck_cards dc
                    ON dc.card_id = c.id
                    AND dc.deck_id = ?

                WHERE

                    c.quantity > 0

                    AND (

                        c.name LIKE ?

                        OR c.printed_name LIKE ?

                        OR c.set_name LIKE ?

                        OR c.collector_number LIKE ?

                        OR c.type_line LIKE ?

                        OR c.oracle_text LIKE ?

                    )

                ORDER BY
                    c.name COLLATE NOCASE ASC
                """,
                (
                    deck_id,
                    search,
                    search,
                    search,
                    search,
                    search,
                    search,
                )
            )

        else:

            cursor.execute(
                """
                SELECT

                    c.id,
                    c.scryfall_id,

                    c.name,
                    c.printed_name,

                    c.lang,

                    c.set_code,
                    c.set_name,

                    c.collector_number,

                    c.mana_cost,

                    c.type_line,
                    c.oracle_text,

                    c.power,
                    c.toughness,

                    c.image_url,
                    c.image_path,

                    c.quantity
                        AS collection_quantity,

                    COALESCE(
                        dc.quantity,
                        0
                    ) AS deck_quantity

                FROM cards c

                LEFT JOIN deck_cards dc
                    ON dc.card_id = c.id
                    AND dc.deck_id = ?

                WHERE c.quantity > 0

                ORDER BY
                    c.name COLLATE NOCASE ASC
                """,
                (deck_id,)
            )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao listar cartas disponíveis:",
            error
        )

        return []

    finally:

        connection.close()


# =========================================================
# GARANTIR CARTA PARA O DECK
# =========================================================

def _ensure_card_for_deck(card_data):
    """
    Garante que a carta exista em cards.

    IMPORTANTE:

    ensure_card_exists() cria uma carta com quantity = 0.

    Portanto uma carta pesquisada no Scryfall pode ser colocada
    no deck sem entrar na coleção.
    """

    if not card_data:
        return None

    try:

        card_id = ensure_card_exists(
            card_data
        )

        if card_id:
            return int(card_id)

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao garantir carta:",
            error
        )

    return None


# =========================================================
# ADICIONAR CARTA AO DECK
# =========================================================

def add_card_to_deck(
    deck_id,
    card_id=None,
    quantity=1,
    card_data=None
):
    """
    Adiciona uma carta ao deck.

    Existem duas possibilidades:

    1. Carta já existe no banco:

        add_card_to_deck(
            deck_id,
            card_id,
            quantity
        )

    2. Carta veio diretamente do Scryfall:

        add_card_to_deck(
            deck_id,
            quantity=1,
            card_data=card_data
        )

    Nesse segundo caso a carta é criada em cards com
    quantity = 0.

    Ela NÃO entra na coleção.
    """

    deck_id = _to_int(deck_id)

    try:
        quantity = int(quantity)
    except (TypeError, ValueError):
        quantity = 1

    if deck_id <= 0:
        return False

    if quantity <= 0:
        return False

    # =====================================================
    # GARANTIR CARTA
    # =====================================================

    if card_id is None and card_data:

        card_id = _ensure_card_for_deck(
            card_data
        )

    card_id = _to_int(card_id)

    if card_id <= 0:
        return False

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        # =================================================
        # VERIFICAR DECK
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM decks
            WHERE id = ?
            LIMIT 1
            """,
            (deck_id,)
        )

        if not cursor.fetchone():

            print(
                "[DECKS DATABASE] Deck não encontrado:",
                deck_id
            )

            return False

        # =================================================
        # VERIFICAR CARTA
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                quantity
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (card_id,)
        )

        card = cursor.fetchone()

        if not card:

            print(
                "[DECKS DATABASE] Carta não encontrada:",
                card_id
            )

            return False

        # =================================================
        # QUANTIDADE ATUAL
        # =================================================

        cursor.execute(
            """
            SELECT quantity
            FROM deck_cards
            WHERE
                deck_id = ?
                AND card_id = ?
            LIMIT 1
            """,
            (
                deck_id,
                card_id
            )
        )

        existing = cursor.fetchone()

        current_quantity = (
            int(existing["quantity"] or 0)
            if existing
            else 0
        )

        new_quantity = (
            current_quantity
            + quantity
        )

        # =================================================
        # ATUALIZAR / INSERIR
        # =================================================

        if existing:

            cursor.execute(
                """
                UPDATE deck_cards

                SET
                    quantity = ?,
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    new_quantity,
                    deck_id,
                    card_id
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO deck_cards (

                    deck_id,
                    card_id,
                    quantity

                )
                VALUES (?, ?, ?)
                """,
                (
                    deck_id,
                    card_id,
                    quantity
                )
            )

        # =================================================
        # ATUALIZAR DECK
        # =================================================

        cursor.execute(
            """
            UPDATE decks

            SET
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (deck_id,)
        )

        connection.commit()

        print(
            "[DECKS DATABASE] Carta adicionada:",
            f"deck={deck_id}",
            f"card={card_id}",
            f"quantity={new_quantity}"
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao adicionar carta:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# DEFINIR QUANTIDADE
# =========================================================

def set_deck_card_quantity(
    deck_id,
    card_id,
    quantity
):
    deck_id = _to_int(deck_id)
    card_id = _to_int(card_id)
    quantity = _to_int(quantity)

    if deck_id <= 0 or card_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # =================================================
        # QUANTIDADE ZERO = REMOVE
        # =================================================

        if quantity <= 0:

            cursor.execute(
                """
                DELETE FROM deck_cards
                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    deck_id,
                    card_id
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO deck_cards (
                    deck_id,
                    card_id,
                    quantity
                )
                VALUES (?, ?, ?)

                ON CONFLICT(
                    deck_id,
                    card_id
                )

                DO UPDATE SET

                    quantity =
                        excluded.quantity,

                    updated_at =
                        CURRENT_TIMESTAMP
                """,
                (
                    deck_id,
                    card_id,
                    quantity
                )
            )

        cursor.execute(
            """
            UPDATE decks

            SET
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (deck_id,)
        )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao definir quantidade:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# ALTERAR QUANTIDADE
# =========================================================

def change_deck_card_quantity(
    deck_id,
    card_id,
    amount,
):
    """
    Altera a quantidade de uma carta dentro do deck.

    Regras:

    1. Carta que existe na coleção:
       - collection_quantity > 0
       - a quantidade no deck nunca pode ultrapassar
         a quantidade existente na coleção.

    2. Carta adicionada diretamente pelo Scryfall:
       - collection_quantity <= 0
       - não possui limite baseado na coleção.
       - pode aumentar normalmente dentro do deck.

    3. A quantidade nunca pode ficar negativa.
    """

    try:

        deck_id = int(deck_id)
        card_id = int(card_id)
        amount = int(amount)

    except (
        TypeError,
        ValueError,
    ):

        return False

    if (
        deck_id <= 0
        or card_id <= 0
        or amount == 0
    ):
        return False

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        # =================================================
        # VERIFICAR CARTA
        # =================================================

        cursor.execute(
            """
            SELECT
                id,
                quantity
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (
                card_id,
            ),
        )

        card_row = cursor.fetchone()

        if not card_row:

            return False

        collection_quantity = max(
            0,
            int(
                card_row["quantity"]
                or 0
            ),
        )

        # =================================================
        # QUANTIDADE ATUAL NO DECK
        # =================================================

        cursor.execute(
            """
            SELECT
                quantity
            FROM deck_cards
            WHERE
                deck_id = ?
                AND card_id = ?
            LIMIT 1
            """,
            (
                deck_id,
                card_id,
            ),
        )

        deck_row = cursor.fetchone()

        current_quantity = (
            int(
                deck_row["quantity"]
                or 0
            )
            if deck_row
            else 0
        )

        # =================================================
        # NOVA QUANTIDADE
        # =================================================

        new_quantity = (
            current_quantity
            + amount
        )

        # Nunca permitir quantidade negativa.
        new_quantity = max(
            0,
            new_quantity,
        )

        # =================================================
        # LIMITE DA COLEÇÃO
        # =================================================
        #
        # SOMENTE cartas que realmente existem
        # na coleção possuem esse limite.
        #
        # collection_quantity <= 0 significa que
        # a carta pode ser uma carta Scryfall-only.
        #
        # Portanto NÃO aplicamos o limite nesse caso.
        #
        # =================================================

        if collection_quantity > 0:

            new_quantity = min(
                new_quantity,
                collection_quantity,
            )

        # =================================================
        # QUANTIDADE ZERO = REMOVER
        # =================================================

        if new_quantity <= 0:

            cursor.execute(
                """
                DELETE FROM deck_cards
                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    deck_id,
                    card_id,
                ),
            )

            # Se essa carta era a capa do deck,
            # remove a referência.

            cursor.execute(
                """
                UPDATE decks

                SET
                    preview_card_id = NULL,
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE
                    id = ?
                    AND preview_card_id = ?
                """,
                (
                    deck_id,
                    card_id,
                ),
            )

        # =================================================
        # INSERIR CARTA
        # =================================================

        elif not deck_row:

            cursor.execute(
                """
                INSERT INTO deck_cards (
                    deck_id,
                    card_id,
                    quantity
                )
                VALUES (?, ?, ?)
                """,
                (
                    deck_id,
                    card_id,
                    new_quantity,
                ),
            )

        # =================================================
        # ATUALIZAR CARTA
        # =================================================

        else:

            cursor.execute(
                """
                UPDATE deck_cards

                SET
                    quantity = ?,
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    new_quantity,
                    deck_id,
                    card_id,
                ),
            )

        # =================================================
        # ATUALIZAR DECK
        # =================================================

        cursor.execute(
            """
            UPDATE decks

            SET
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                deck_id,
            ),
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] "
            "Erro de integridade ao alterar carta:",
            error,
        )

        return False

    except sqlite3.OperationalError as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] "
            "Erro operacional ao alterar carta:",
            error,
        )

        return False

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] "
            "Erro inesperado ao alterar carta:",
            error,
        )

        return False

    finally:

        connection.close()


# =========================================================
# REMOVER CARTA DO DECK
# =========================================================

def remove_card_from_deck(
    deck_id,
    card_id,
    quantity=None
):
    """
    Se quantity for None:
        remove completamente.

    Se quantity for informado:
        remove somente aquela quantidade.
    """

    deck_id = _to_int(deck_id)
    card_id = _to_int(card_id)

    if deck_id <= 0 or card_id <= 0:
        return False

    if quantity is None:

        quantity = None

    else:

        quantity = _to_int(quantity)

        if quantity <= 0:
            return False

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT quantity
            FROM deck_cards

            WHERE
                deck_id = ?
                AND card_id = ?
            """,
            (
                deck_id,
                card_id
            )
        )

        row = cursor.fetchone()

        if not row:
            return False

        current_quantity = int(
            row["quantity"] or 0
        )

        # =================================================
        # REMOVER TUDO
        # =================================================

        if quantity is None:

            new_quantity = 0

        else:

            new_quantity = (
                current_quantity
                - quantity
            )

            new_quantity = max(
                0,
                new_quantity
            )

        # =================================================
        # DELETE
        # =================================================

        if new_quantity <= 0:

            cursor.execute(
                """
                DELETE FROM deck_cards
                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    deck_id,
                    card_id
                )
            )

            # Se essa carta era o preview,
            # limpa o preview.

            cursor.execute(
                """
                UPDATE decks

                SET
                    preview_card_id = NULL,
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE
                    id = ?
                    AND preview_card_id = ?
                """,
                (
                    deck_id,
                    card_id
                )
            )

        # =================================================
        # UPDATE
        # =================================================

        else:

            cursor.execute(
                """
                UPDATE deck_cards

                SET
                    quantity = ?,
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE
                    deck_id = ?
                    AND card_id = ?
                """,
                (
                    new_quantity,
                    deck_id,
                    card_id
                )
            )

            cursor.execute(
                """
                UPDATE decks

                SET
                    updated_at =
                        CURRENT_TIMESTAMP

                WHERE id = ?
                """,
                (deck_id,)
            )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao remover carta:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# LIMPAR DECK
# =========================================================

def clear_deck_cards(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,)
        )

        cursor.execute(
            """
            UPDATE decks

            SET
                preview_card_id = NULL,
                preview_image_path = NULL,
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (deck_id,)
        )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao limpar deck:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# PREVIEW DO DECK
# =========================================================

def get_deck_preview(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return None

    connection = get_connection()

    try:

        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                preview_card_id,
                preview_image_path
            FROM decks
            WHERE id = ?
            """,
            (deck_id,)
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "preview_card_id": (
                int(row["preview_card_id"])
                if row["preview_card_id"] is not None
                else None
            ),

            "preview_image_path": (
                row["preview_image_path"]
                or None
            ),
        }

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro ao obter preview:",
            error
        )

        return None

    finally:

        connection.close()


# =========================================================
# PREVIEW = CARTA
# =========================================================

def set_deck_preview_card(
    deck_id,
    card_id
):
    deck_id = _to_int(deck_id)
    card_id = _to_int(card_id)

    if deck_id <= 0 or card_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # A carta precisa estar no deck.

        cursor.execute(
            """
            SELECT 1

            FROM deck_cards

            WHERE
                deck_id = ?
                AND card_id = ?

            LIMIT 1
            """,
            (
                deck_id,
                card_id
            )
        )

        if not cursor.fetchone():
            return False

        cursor.execute(
            """
            UPDATE decks

            SET
                preview_card_id = ?,
                preview_image_path = NULL,
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                card_id,
                deck_id
            )
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao definir preview:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# PREVIEW = IMAGEM
# =========================================================

def set_deck_preview_image(
    deck_id,
    image_path
):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    image_path = str(
        image_path or ""
    ).strip()

    if not image_path:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks

            SET
                preview_card_id = NULL,
                preview_image_path = ?,
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                image_path,
                deck_id
            )
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao definir imagem:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# LIMPAR PREVIEW
# =========================================================

def clear_deck_preview(deck_id):
    deck_id = _to_int(deck_id)

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE decks

            SET
                preview_card_id = NULL,
                preview_image_path = NULL,
                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (deck_id,)
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DECKS DATABASE] Erro ao limpar preview:",
            error
        )

        return False

    finally:

        connection.close()


# =========================================================
# ESTATÍSTICAS GERAIS DOS DECKS
# =========================================================

def get_all_decks_stats():
    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                COUNT(
                    DISTINCT d.id
                ) AS total_decks,

                COALESCE(
                    SUM(dc.quantity),
                    0
                ) AS total_cards,

                COUNT(
                    DISTINCT dc.card_id
                ) AS unique_cards

            FROM decks d

            LEFT JOIN deck_cards dc
                ON dc.deck_id = d.id
            """
        )

        row = cursor.fetchone()

        if not row:

            return {
                "total_decks": 0,
                "total_cards": 0,
                "unique_cards": 0,
            }

        return {
            "total_decks": int(
                row["total_decks"] or 0
            ),

            "total_cards": int(
                row["total_cards"] or 0
            ),

            "unique_cards": int(
                row["unique_cards"] or 0
            ),
        }

    except Exception as error:

        print(
            "[DECKS DATABASE] Erro nas estatísticas gerais:",
            error
        )

        return {
            "total_decks": 0,
            "total_cards": 0,
            "unique_cards": 0,
        }

    finally:

        connection.close()
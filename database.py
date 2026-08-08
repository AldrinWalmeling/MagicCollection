import sqlite3
from pathlib import Path


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SAVE_DIR = BASE_DIR / "save"

SAVE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

DATABASE_FILE = SAVE_DIR / "save.db"

CARDS_DIR = BASE_DIR / "cards"

CARDS_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# =========================================================
# CONEXÃO
# =========================================================

def get_connection():

    connection = sqlite3.connect(
        str(DATABASE_FILE)
    )

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection

# =========================================================
# URL DA IMAGEM DO SCRYFALL
# =========================================================

def build_scryfall_image_url(
    scryfall_id
):

    if not scryfall_id:
        return None

    scryfall_id = str(
        scryfall_id
    ).strip()

    if len(scryfall_id) < 2:
        return None

    first = scryfall_id[0]
    second = scryfall_id[1]

    return (
        "https://cards.scryfall.io/"
        "normal/front/"
        f"{first}/{second}/"
        f"{scryfall_id}.jpg"
    )


# =========================================================
# NORMALIZAR URL DA IMAGEM
# =========================================================

def normalize_image_url(
    image_url
):

    if not image_url:
        return None

    image_url = str(
        image_url
    ).strip()

    # -----------------------------------------------------
    # Markdown:
    #
    # [texto](https://exemplo.com)
    # -----------------------------------------------------

    if (
        image_url.startswith("[")
        and "](" in image_url
    ):

        try:

            image_url = image_url.split(
                "](",
                1
            )[1]

            image_url = image_url.rsplit(
                ")",
                1
            )[0]

        except Exception:

            return None

    # -----------------------------------------------------
    # HTML entity
    # -----------------------------------------------------

    image_url = (
        image_url
        .replace("&amp;", "&")
        .strip()
    )

    # -----------------------------------------------------
    # URL válida
    # -----------------------------------------------------

    if not (
        image_url.startswith("http://")
        or image_url.startswith("https://")
    ):

        return None

    return image_url


# =========================================================
# OBTER URL DA IMAGEM DOS DADOS DO SCRYFALL
# =========================================================

def extract_image_url(
    card_data
):

    if not card_data:
        return None

    # -----------------------------------------------------
    # image_url
    # -----------------------------------------------------

    image_url = normalize_image_url(
        card_data.get(
            "image_url"
        )
    )

    if image_url:
        return image_url

    # -----------------------------------------------------
    # image_uris
    # -----------------------------------------------------

    image_uris = card_data.get(
        "image_uris"
    )

    if isinstance(
        image_uris,
        dict
    ):

        normal = image_uris.get(
            "normal"
        )

        normal = normalize_image_url(
            normal
        )

        if normal:
            return normal

    # -----------------------------------------------------
    # card_faces
    # -----------------------------------------------------

    card_faces = card_data.get(
        "card_faces"
    )

    if isinstance(
        card_faces,
        list
    ):

        for face in card_faces:

            if not isinstance(
                face,
                dict
            ):
                continue

            face_image_uris = face.get(
                "image_uris"
            )

            if not isinstance(
                face_image_uris,
                dict
            ):
                continue

            normal = face_image_uris.get(
                "normal"
            )

            normal = normalize_image_url(
                normal
            )

            if normal:
                return normal

    # -----------------------------------------------------
    # Último recurso
    # -----------------------------------------------------

    scryfall_id = (
        card_data.get(
            "scryfall_id"
        )
        or card_data.get(
            "id"
        )
    )

    return build_scryfall_image_url(
        scryfall_id
    )


# =========================================================
# CAMINHO LOCAL DA IMAGEM
# =========================================================

def get_card_image_path(
    scryfall_id
):

    if not scryfall_id:
        return None

    scryfall_id = str(
        scryfall_id
    ).strip()

    if not scryfall_id:
        return None

    return CARDS_DIR / (
        f"{scryfall_id}.jpg"
    )


# =========================================================
# INICIALIZAÇÃO DA COLEÇÃO
# =========================================================

def init_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cards (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            scryfall_id TEXT,

            name TEXT NOT NULL,

            printed_name TEXT,

            lang TEXT,

            set_code TEXT,

            set_name TEXT,

            collector_number TEXT,

            mana_cost TEXT,

            type_line TEXT,

            oracle_text TEXT,

            power TEXT,

            toughness TEXT,

            image_url TEXT,

            image_path TEXT,

            quantity INTEGER NOT NULL DEFAULT 0,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    connection.commit()

    connection.close()


# =========================================================
# MIGRAÇÃO DA COLEÇÃO
# =========================================================

def migrate_database():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        "PRAGMA table_info(cards)"
    )

    columns = {
        row["name"]
        for row in cursor.fetchall()
    }

    required_columns = {

        "scryfall_id":
            "TEXT",

        "printed_name":
            "TEXT",

        "lang":
            "TEXT",

        "set_code":
            "TEXT",

        "set_name":
            "TEXT",

        "collector_number":
            "TEXT",

        "mana_cost":
            "TEXT",

        "type_line":
            "TEXT",

        "oracle_text":
            "TEXT",

        "power":
            "TEXT",

        "toughness":
            "TEXT",

        "image_url":
            "TEXT",

        "image_path":
            "TEXT",

        "quantity":
            "INTEGER NOT NULL DEFAULT 0",

        "created_at":
            "TIMESTAMP",

        "updated_at":
            "TIMESTAMP",
    }

    for column_name, column_type in required_columns.items():

        if column_name in columns:
            continue

        try:

            cursor.execute(
                f"""
                ALTER TABLE cards
                ADD COLUMN {column_name}
                {column_type}
                """
            )

            print(
                "[DATABASE] Coluna adicionada: "
                f"{column_name}"
            )

        except sqlite3.OperationalError as error:

            print(
                "[DATABASE] Erro ao adicionar "
                f"{column_name}: {error}"
            )

    connection.commit()

    connection.close()


# =========================================================
# CORRIGIR IDS INVÁLIDOS
# =========================================================

def repair_invalid_ids():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            scryfall_id,
            name
        FROM cards
        ORDER BY id ASC
        """
    )

    rows = cursor.fetchall()

    invalid_ids = [
        row
        for row in rows
        if row["id"] is None
        or int(row["id"]) <= 0
    ]

    if not invalid_ids:

        connection.close()

        return 0

    print(
        "[DATABASE] Foram encontrados "
        f"{len(invalid_ids)} registros com ID inválido."
    )

    repaired = 0

    for row in invalid_ids:

        old_id = row["id"]

        cursor.execute(
            """
            SELECT *
            FROM cards
            WHERE id = ?
            """,
            (
                old_id,
            )
        )

        old_row = cursor.fetchone()

        if not old_row:
            continue

        data = dict(
            old_row
        )

        cursor.execute(
            """
            INSERT INTO cards (

                scryfall_id,
                name,
                printed_name,
                lang,
                set_code,
                set_name,
                collector_number,
                mana_cost,
                type_line,
                oracle_text,
                power,
                toughness,
                image_url,
                image_path,
                quantity,
                created_at,
                updated_at

            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                data.get("scryfall_id"),
                data.get("name"),
                data.get("printed_name"),
                data.get("lang"),
                data.get("set_code"),
                data.get("set_name"),
                data.get("collector_number"),
                data.get("mana_cost"),
                data.get("type_line"),
                data.get("oracle_text"),
                data.get("power"),
                data.get("toughness"),
                data.get("image_url"),
                data.get("image_path"),
                data.get("quantity", 1),
                data.get("created_at"),
                data.get("updated_at"),
            )
        )

        cursor.execute(
            """
            DELETE FROM cards
            WHERE id = ?
            """,
            (
                old_id,
            )
        )

        repaired += 1

    connection.commit()

    connection.close()

    print(
        "[DATABASE] IDs reparados: "
        f"{repaired}"
    )

    return repaired


# =========================================================
# CORRIGIR URLS / CAMINHOS DAS IMAGENS
# =========================================================

def fix_image_urls():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            scryfall_id,
            image_url,
            image_path
        FROM cards
        """
    )

    rows = cursor.fetchall()

    fixed = 0

    for row in rows:

        card_id = row["id"]

        scryfall_id = row[
            "scryfall_id"
        ]

        image_url = row[
            "image_url"
        ]

        image_path = row[
            "image_path"
        ]

        changed = False

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        normalized_url = normalize_image_url(
            image_url
        )

        if not normalized_url and scryfall_id:

            normalized_url = (
                build_scryfall_image_url(
                    scryfall_id
                )
            )

        if normalized_url != image_url:

            image_url = normalized_url

            changed = True

        # -------------------------------------------------
        # CAMINHO LOCAL
        # -------------------------------------------------

        expected_path = get_card_image_path(
            scryfall_id
        )

        expected_path_string = (
            str(expected_path)
            if expected_path
            else None
        )

        if (
            expected_path_string
            and image_path != expected_path_string
        ):

            image_path = expected_path_string

            changed = True

        # -------------------------------------------------
        # SALVAR
        # -------------------------------------------------

        if changed:

            cursor.execute(
                """
                UPDATE cards
                SET
                    image_url = ?,
                    image_path = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    image_url,
                    image_path,
                    card_id
                )
            )

            fixed += 1

    connection.commit()

    connection.close()

    print(
        "[DATABASE] Registros corrigidos: "
        f"{fixed}"
    )

    return fixed


# =========================================================
# INICIALIZAÇÃO COMPLETA DA COLEÇÃO
# =========================================================

def initialize_database():

    CARDS_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    init_database()

    migrate_database()

    repair_invalid_ids()

    fix_image_urls()


# =========================================================
# BANCO DE DADOS DOS DECKS
# =========================================================

def initialize_decks_database():

    connection = get_connection()

    cursor = connection.cursor()

    # =====================================================
    # DECKS
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS decks (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    # =====================================================
    # CARTAS DOS DECKS
    # =====================================================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS deck_cards (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            deck_id INTEGER NOT NULL,

            card_id INTEGER NOT NULL,

            quantity INTEGER NOT NULL DEFAULT 1,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            updated_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(
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

    # =====================================================
    # ÍNDICES
    # =====================================================

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

    connection.close()

    print(
        "[DATABASE] Banco de decks inicializado."
    )


# =========================================================
# ADICIONAR CARTA À COLEÇÃO
# =========================================================

def add_card(
    card_data,
    quantity=1
):

    if not card_data:
        return False

    # =====================================================
    # DADOS
    # =====================================================

    scryfall_id = (
        card_data.get(
            "scryfall_id"
        )
        or card_data.get(
            "id"
        )
    )

    if scryfall_id:

        scryfall_id = str(
            scryfall_id
        ).strip()

    name = (
        card_data.get(
            "name"
        )
        or ""
    ).strip()

    if not name:
        return False

    printed_name = card_data.get(
        "printed_name"
    )

    lang = card_data.get(
        "lang"
    )

    set_code = card_data.get(
        "set_code"
    )

    set_name = card_data.get(
        "set_name"
    )

    collector_number = card_data.get(
        "collector_number"
    )

    mana_cost = card_data.get(
        "mana_cost"
    )

    type_line = card_data.get(
        "type_line"
    )

    oracle_text = card_data.get(
        "oracle_text"
    )

    power = card_data.get(
        "power"
    )

    toughness = card_data.get(
        "toughness"
    )

    # =====================================================
    # IMAGEM
    # =====================================================

    image_url = extract_image_url(
        card_data
    )

    image_path = get_card_image_path(
        scryfall_id
    )

    image_path_string = (
        str(image_path)
        if image_path
        else None
    )

    # =====================================================
    # QUANTIDADE
    # =====================================================

    try:

        quantity = int(
            quantity
        )

    except (
        TypeError,
        ValueError
    ):

        quantity = 1

    if quantity <= 0:
        quantity = 1

    # =====================================================
    # BANCO
    # =====================================================

    connection = get_connection()

    cursor = connection.cursor()

    try:

        existing = None

        # -------------------------------------------------
        # Primeiro pelo Scryfall ID
        # -------------------------------------------------

        if scryfall_id:

            cursor.execute(
                """
                SELECT
                    id,
                    quantity
                FROM cards
                WHERE scryfall_id = ?
                LIMIT 1
                """,
                (
                    scryfall_id,
                )
            )

            existing = cursor.fetchone()

        # -------------------------------------------------
        # Compatibilidade
        # -------------------------------------------------

        if not existing:

            cursor.execute(
                """
                SELECT
                    id,
                    quantity
                FROM cards
                WHERE name = ?
                  AND COALESCE(set_name, '') =
                      COALESCE(?, '')
                  AND COALESCE(collector_number, '') =
                      COALESCE(?, '')
                LIMIT 1
                """,
                (
                    name,
                    set_name,
                    collector_number
                )
            )

            existing = cursor.fetchone()

        # =================================================
        # EXISTENTE
        # =================================================

        if existing:

            existing_id = int(
                existing["id"]
            )

            current_quantity = int(
                existing["quantity"]
            )

            new_quantity = (
                current_quantity
                + quantity
            )

            cursor.execute(
                """
                UPDATE cards
                SET
                    scryfall_id = ?,
                    printed_name = ?,
                    lang = ?,
                    set_code = ?,
                    set_name = ?,
                    collector_number = ?,
                    mana_cost = ?,
                    type_line = ?,
                    oracle_text = ?,
                    power = ?,
                    toughness = ?,
                    image_url = ?,
                    image_path = ?,
                    quantity = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    scryfall_id,
                    printed_name,
                    lang,
                    set_code,
                    set_name,
                    collector_number,
                    mana_cost,
                    type_line,
                    oracle_text,
                    power,
                    toughness,
                    image_url,
                    image_path_string,
                    new_quantity,
                    existing_id
                )
            )

            connection.commit()

            print(
                "[DATABASE] Carta atualizada: "
                f"{name} | ID={existing_id} | "
                f"Quantidade={new_quantity}"
            )

            return True

        # =================================================
        # NOVA CARTA
        # =================================================

        cursor.execute(
            """
            INSERT INTO cards (

                scryfall_id,
                name,
                printed_name,
                lang,
                set_code,
                set_name,
                collector_number,
                mana_cost,
                type_line,
                oracle_text,
                power,
                toughness,
                image_url,
                image_path,
                quantity

            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?
            )
            """,
            (
                scryfall_id,
                name,
                printed_name,
                lang,
                set_code,
                set_name,
                collector_number,
                mana_cost,
                type_line,
                oracle_text,
                power,
                toughness,
                image_url,
                image_path_string,
                quantity
            )
        )

        connection.commit()

        new_id = cursor.lastrowid

        print(
            "[DATABASE] Carta adicionada: "
            f"{name} | ID={new_id}"
        )

        print(
            "[DATABASE] Scryfall ID: "
            f"{scryfall_id}"
        )

        print(
            "[DATABASE] Imagem remota: "
            f"{image_url}"
        )

        print(
            "[DATABASE] Imagem local: "
            f"{image_path_string}"
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao adicionar carta: "
            f"{error}"
        )

        return False

    finally:

        connection.close()


# =========================================================
# TODAS AS CARTAS
# =========================================================

def get_all_cards():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            name,
            printed_name,
            lang,
            set_name,
            collector_number,
            mana_cost,
            type_line,
            oracle_text,
            image_url,
            quantity,
            image_path,
            power,
            toughness
        FROM cards
        ORDER BY name COLLATE NOCASE ASC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        tuple(row)
        for row in rows
    ]


# =========================================================
# PESQUISAR CARTAS
# =========================================================

def search_cards(
    text
):

    text = (
        text or ""
    ).strip()

    if not text:
        return get_all_cards()

    connection = get_connection()

    cursor = connection.cursor()

    search_text = (
        f"%{text}%"
    )

    cursor.execute(
        """
        SELECT
            id,
            name,
            printed_name,
            lang,
            set_name,
            collector_number,
            mana_cost,
            type_line,
            oracle_text,
            image_url,
            quantity,
            image_path,
            power,
            toughness
        FROM cards
        WHERE
            name LIKE ?
            OR printed_name LIKE ?
            OR set_name LIKE ?
            OR collector_number LIKE ?
            OR type_line LIKE ?
            OR oracle_text LIKE ?
        ORDER BY name COLLATE NOCASE ASC
        """,
        (
            search_text,
            search_text,
            search_text,
            search_text,
            search_text,
            search_text
        )
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        tuple(row)
        for row in rows
    ]


# =========================================================
# ALTERAR QUANTIDADE DA COLEÇÃO
# =========================================================

def change_quantity(
    card_id,
    amount
):

    try:

        card_id = int(
            card_id
        )

        amount = int(
            amount
        )

    except (
        TypeError,
        ValueError
    ):

        print(
            "[DATABASE] ID ou quantidade inválida: "
            f"{card_id} / {amount}"
        )

        return False

    if card_id <= 0:

        print(
            "[DATABASE] ID inválido: "
            f"{card_id}"
        )

        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                quantity
            FROM cards
            WHERE id = ?
            """,
            (
                card_id,
            )
        )

        row = cursor.fetchone()

        if not row:

            print(
                "[DATABASE] Carta não encontrada. "
                f"ID: {card_id}"
            )

            return False

        current_quantity = int(
            row["quantity"]
        )

        new_quantity = (
            current_quantity
            + amount
        )

        if new_quantity < 0:
            new_quantity = 0

        if new_quantity == 0:

            cursor.execute(
                """
                DELETE FROM cards
                WHERE id = ?
                """,
                (
                    card_id,
                )
            )

            print(
                "[DATABASE] Carta removida. "
                f"ID={card_id}"
            )

        else:

            cursor.execute(
                """
                UPDATE cards
                SET
                    quantity = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    new_quantity,
                    card_id
                )
            )

            print(
                "[DATABASE] Quantidade alterada: "
                f"ID={card_id} | "
                f"{current_quantity} -> "
                f"{new_quantity}"
            )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao alterar quantidade: "
            f"{error}"
        )

        return False

    finally:

        connection.close()


# =========================================================
# CARTA POR ID
# =========================================================

def get_card_by_id(
    card_id
):

    try:

        card_id = int(
            card_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            scryfall_id,
            name,
            printed_name,
            lang,
            set_code,
            set_name,
            collector_number,
            mana_cost,
            type_line,
            oracle_text,
            power,
            toughness,
            image_url,
            image_path,
            quantity
        FROM cards
        WHERE id = ?
        """,
        (
            card_id,
        )
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    return dict(row)

# =========================================================
# CARTA POR SCRYFALL ID
# =========================================================

def get_card_id_by_scryfall_id(
    scryfall_id
):
    if not scryfall_id:
        return None

    scryfall_id = str(
        scryfall_id
    ).strip()

    if not scryfall_id:
        return None

    connection = get_connection()

    try:

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM cards
            WHERE scryfall_id = ?
            LIMIT 1
            """,
            (
                scryfall_id,
            )
        )

        row = cursor.fetchone()

        if not row:
            return None

        return int(
            row["id"]
        )

    except Exception as error:

        print(
            "[DATABASE] Erro ao buscar "
            "carta pelo Scryfall ID:",
            error,
        )

        return None

    finally:

        connection.close()
# =========================================================
# EXPORTAÇÃO
# =========================================================

def get_collection_for_export():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            scryfall_id,
            name,
            printed_name,
            lang,
            set_code,
            set_name,
            collector_number,
            mana_cost,
            type_line,
            oracle_text,
            power,
            toughness,
            image_url,
            quantity
        FROM cards
        ORDER BY name COLLATE NOCASE ASC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# TOTAL DE CARTAS
# =========================================================

def get_total_cards():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COALESCE(
            SUM(quantity),
            0
        )
        FROM cards
        """
    )

    total = cursor.fetchone()[0]

    connection.close()

    return int(
        total or 0
    )


# =========================================================
# CARTAS DIFERENTES
# =========================================================

def get_unique_cards():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT COUNT(*)
        FROM cards
        """
    )

    total = cursor.fetchone()[0]

    connection.close()

    return int(
        total or 0
    )


# =========================================================
# RECONSTRUIR IMAGENS FALTANTES
# =========================================================

def rebuild_missing_image_paths():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            id,
            scryfall_id,
            image_url,
            image_path
        FROM cards
        """
    )

    rows = cursor.fetchall()

    fixed = 0

    for row in rows:

        card_id = row["id"]

        scryfall_id = row[
            "scryfall_id"
        ]

        if not scryfall_id:
            continue

        expected_path = (
            get_card_image_path(
                scryfall_id
            )
        )

        if not expected_path:
            continue

        expected_path = str(
            expected_path
        )

        # -------------------------------------------------
        # CAMINHO
        # -------------------------------------------------

        if row["image_path"] != expected_path:

            cursor.execute(
                """
                UPDATE cards
                SET
                    image_path = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    expected_path,
                    card_id
                )
            )

            fixed += 1

        # -------------------------------------------------
        # URL
        # -------------------------------------------------

        if not row["image_url"]:

            image_url = (
                build_scryfall_image_url(
                    scryfall_id
                )
            )

            if image_url:

                cursor.execute(
                    """
                    UPDATE cards
                    SET
                        image_url = ?,
                        updated_at =
                            CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (
                        image_url,
                        card_id
                    )
                )

                fixed += 1

    connection.commit()

    connection.close()

    print(
        "[DATABASE] Caminhos de imagem "
        f"reconstruídos: {fixed}"
    )

    return fixed


# =========================================================
# =========================================================
# DECKS
# =========================================================
# =========================================================


# =========================================================
# CRIAR DECK
# =========================================================

def create_deck(
    name
):

    name = (
        name or ""
    ).strip()

    if not name:
        return None

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO decks (
                name
            )
            VALUES (?)
            """,
            (
                name,
            )
        )

        connection.commit()

        deck_id = cursor.lastrowid

        print(
            "[DATABASE] Deck criado: "
            f"{name} | ID={deck_id}"
        )

        return int(
            deck_id
        )

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao criar deck: "
            f"{error}"
        )

        return None

    finally:

        connection.close()


# =========================================================
# TODOS OS DECKS
# =========================================================

def get_all_decks():

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            d.id,
            d.name,
            d.created_at,
            d.updated_at,

            COALESCE(
                SUM(dc.quantity),
                0
            ) AS card_count

        FROM decks d

        LEFT JOIN deck_cards dc
            ON dc.deck_id = d.id

        GROUP BY
            d.id

        ORDER BY
            d.name COLLATE NOCASE ASC
        """
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# DECK POR ID
# =========================================================

def get_deck_by_id(
    deck_id
):

    try:

        deck_id = int(
            deck_id
        )

    except (
        TypeError,
        ValueError
    ):

        return None

    connection = get_connection()

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            d.id,
            d.name,
            d.created_at,
            d.updated_at,

            COALESCE(
                SUM(dc.quantity),
                0
            ) AS card_count

        FROM decks d

        LEFT JOIN deck_cards dc
            ON dc.deck_id = d.id

        WHERE d.id = ?

        GROUP BY
            d.id
        """,
        (
            deck_id,
        )
    )

    row = cursor.fetchone()

    connection.close()

    if not row:
        return None

    return dict(row)


# =========================================================
# RENOMEAR DECK
# =========================================================

def rename_deck(
    deck_id,
    name
):

    try:

        deck_id = int(
            deck_id
        )

    except (
        TypeError,
        ValueError
    ):

        return False

    name = (
        name or ""
    ).strip()

    if not name:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            UPDATE decks
            SET
                name = ?,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                name,
                deck_id
            )
        )

        changed = (
            cursor.rowcount > 0
        )

        connection.commit()

        if changed:

            print(
                "[DATABASE] Deck renomeado: "
                f"ID={deck_id} | "
                f"Nome={name}"
            )

        return changed

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao renomear deck: "
            f"{error}"
        )

        return False

    finally:

        connection.close()


# =========================================================
# EXCLUIR DECK
# =========================================================

def delete_deck(
    deck_id
):

    try:

        deck_id = int(
            deck_id
        )

    except (
        TypeError,
        ValueError
    ):

        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            DELETE FROM decks
            WHERE id = ?
            """,
            (
                deck_id,
            )
        )

        deleted = (
            cursor.rowcount > 0
        )

        connection.commit()

        if deleted:

            print(
                "[DATABASE] Deck excluído: "
                f"ID={deck_id}"
            )

        return deleted

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao excluir deck: "
            f"{error}"
        )

        return False

    finally:

        connection.close()


# =========================================================
# CARTAS DE UM DECK
# =========================================================

def get_deck_cards(
    deck_id
):

    try:

        deck_id = int(
            deck_id
        )

    except (
        TypeError,
        ValueError
    ):

        return []

    connection = get_connection()

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

            c.power,

            c.toughness,

            c.image_url,

            c.image_path,

            c.quantity AS collection_quantity,

            dc.quantity AS deck_quantity

        FROM deck_cards dc

        INNER JOIN cards c
            ON c.id = dc.card_id

        WHERE dc.deck_id = ?

        ORDER BY
            c.name COLLATE NOCASE ASC
        """,
        (
            deck_id,
        )
    )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# CARTAS DISPONÍVEIS PARA ADICIONAR AO DECK
# =========================================================

def get_cards_available_for_deck(
    deck_id,
    search_text=""
):

    try:

        deck_id = int(
            deck_id
        )

    except (
        TypeError,
        ValueError
    ):

        return []

    search_text = (
        search_text or ""
    ).strip()

    connection = get_connection()

    cursor = connection.cursor()

    # -----------------------------------------------------
    # SEM PESQUISA
    # -----------------------------------------------------

    if not search_text:

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
            (
                deck_id,
            )
        )

    # -----------------------------------------------------
    # COM PESQUISA
    # -----------------------------------------------------

    else:

        search = (
            f"%{search_text}%"
        )

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
                search
            )
        )

    rows = cursor.fetchall()

    connection.close()

    return [
        dict(row)
        for row in rows
    ]


# =========================================================
# ADICIONAR CARTA AO DECK
# =========================================================

def add_card_to_deck(
    deck_id,
    card_id,
    quantity=1
):

    try:

        deck_id = int(
            deck_id
        )

        card_id = int(
            card_id
        )

        quantity = int(
            quantity
        )

    except (
        TypeError,
        ValueError
    ):

        return False

    if deck_id <= 0:
        return False

    if card_id <= 0:
        return False

    if quantity <= 0:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

        # =================================================
        # VERIFICAR DECK
        # =================================================

        cursor.execute(
            """
            SELECT id
            FROM decks
            WHERE id = ?
            """,
            (
                deck_id,
            )
        )

        deck = cursor.fetchone()

        if not deck:

            print(
                "[DATABASE] Deck não encontrado: "
                f"{deck_id}"
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
            """,
            (
                card_id,
            )
        )

        card = cursor.fetchone()

        if not card:

            print(
                "[DATABASE] Carta não encontrada: "
                f"{card_id}"
            )

            return False

        collection_quantity = int(
            card["quantity"]
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
            """,
            (
                deck_id,
                card_id
            )
        )

        existing = cursor.fetchone()

        current_quantity = (
            int(existing["quantity"])
            if existing
            else 0
        )

        new_quantity = (
            current_quantity
            + quantity
        )

        # =================================================
        # NÃO PODE USAR MAIS CARTAS QUE A COLEÇÃO
        # =================================================

        if new_quantity > collection_quantity:

            print(
                "[DATABASE] Quantidade insuficiente "
                "na coleção. "
                f"Coleção={collection_quantity} | "
                f"Deck={current_quantity} | "
                f"Solicitado={quantity}"
            )

            return False

        # =================================================
        # ATUALIZAR EXISTENTE
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

        # =================================================
        # NOVA CARTA
        # =================================================

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
            (
                deck_id,
            )
        )

        connection.commit()

        print(
            "[DATABASE] Carta adicionada ao deck: "
            f"Deck={deck_id} | "
            f"Carta={card_id} | "
            f"Quantidade={new_quantity}"
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao adicionar "
            f"carta ao deck: {error}"
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
    quantity=1
):

    try:

        deck_id = int(
            deck_id
        )

        card_id = int(
            card_id
        )

        quantity = int(
            quantity
        )

    except (
        TypeError,
        ValueError
    ):

        return False

    if deck_id <= 0:
        return False

    if card_id <= 0:
        return False

    if quantity <= 0:
        return False

    connection = get_connection()

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            SELECT
                quantity
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

            print(
                "[DATABASE] Carta não está no deck."
            )

            return False

        current_quantity = int(
            row["quantity"]
        )

        new_quantity = (
            current_quantity
            - quantity
        )

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

            new_quantity = 0

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
            )
        )

        connection.commit()

        print(
            "[DATABASE] Carta removida do deck: "
            f"Deck={deck_id} | "
            f"Carta={card_id} | "
            f"Quantidade={new_quantity}"
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao remover "
            f"carta do deck: {error}"
        )

        return False

    finally:

        connection.close()
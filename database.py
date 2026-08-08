import sqlite3
from pathlib import Path


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

DATABASE_FILE = BASE_DIR / "collection.db"

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
        f"normal/front/"
        f"{first}/{second}/"
        f"{scryfall_id}.jpg"
    )


# =========================================================
# LIMPAR URL DE IMAGEM
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
    # [https://exemplo](https://exemplo)
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

            image_url = image_url.rstrip(
                ")"
            )

        except Exception:
            pass

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
def normalize_image_url(image_url):

    if not image_url:
        return None

    image_url = str(
        image_url
    ).strip()

    # ---------------------------------------------
    # Markdown:
    # [texto](URL)
    # ---------------------------------------------

    if image_url.startswith("[") and "](" in image_url:

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

    # ---------------------------------------------
    # HTML
    # ---------------------------------------------

    image_url = (
        image_url
        .replace("&amp;", "&")
        .strip()
    )

    # ---------------------------------------------
    # Garantir URL
    # ---------------------------------------------

    if not (
        image_url.startswith("http://")
        or image_url.startswith("https://")
    ):
        return None

    return image_url

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
# INICIALIZAÇÃO
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
# MIGRAÇÃO
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
                f"[DATABASE] Coluna adicionada: "
                f"{column_name}"
            )

        except sqlite3.OperationalError as error:

            print(
                f"[DATABASE] Erro ao adicionar "
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
        f"[DATABASE] IDs reparados: {repaired}"
    )

    return repaired


# =========================================================
# CORRIGIR URLs / CAMINHOS DAS IMAGENS
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
        f"[DATABASE] Registros corrigidos: {fixed}"
    )

    return fixed


# =========================================================
# INICIALIZAÇÃO COMPLETA
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
# ADICIONAR CARTA
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
                f"[DATABASE] Carta atualizada: "
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
            f"[DATABASE] Carta adicionada: "
            f"{name} | ID={new_id}"
        )

        print(
            f"[DATABASE] Scryfall ID: "
            f"{scryfall_id}"
        )

        print(
            f"[DATABASE] Imagem remota: "
            f"{image_url}"
        )

        print(
            f"[DATABASE] Imagem local: "
            f"{image_path_string}"
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            f"[DATABASE] Erro ao adicionar carta: "
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
# ALTERAR QUANTIDADE
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
            f"[DATABASE] ID ou quantidade inválida: "
            f"{card_id} / {amount}"
        )

        return False

    if card_id <= 0:

        print(
            f"[DATABASE] ID inválido: {card_id}"
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
                f"[DATABASE] Carta não encontrada. "
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
                f"[DATABASE] Carta removida. "
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
                f"[DATABASE] Quantidade alterada: "
                f"ID={card_id} | "
                f"{current_quantity} -> "
                f"{new_quantity}"
            )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            f"[DATABASE] Erro ao alterar quantidade: "
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

    return fixed
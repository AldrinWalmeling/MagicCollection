import json
import sqlite3
import unicodedata
from pathlib import Path


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

SAVE_DIR = BASE_DIR / "save"
SAVE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_FILE = SAVE_DIR / "save.db"

CARDS_DIR = BASE_DIR / "cards"
CARDS_DIR.mkdir(
    parents=True,
    exist_ok=True,
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
# IMAGENS — SCRYFALL
# =========================================================

def build_scryfall_image_url(scryfall_id):
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
        "large/front/"
        f"{first}/{second}/"
        f"{scryfall_id}.jpg"
    )


def normalize_image_url(image_url):
    if not image_url:
        return None

    image_url = str(
        image_url
    ).strip()

    if (
        image_url.startswith("[")
        and "](" in image_url
    ):
        try:
            image_url = image_url.split(
                "](",
                1,
            )[1]

            image_url = image_url.rsplit(
                ")",
                1,
            )[0]

        except Exception:
            return None

    image_url = (
        image_url
        .replace("&amp;", "&")
        .strip()
    )

    if not (
        image_url.startswith("http://")
        or image_url.startswith("https://")
    ):
        return None

    return image_url


def normalize_search_text(value):
    value = str(value or "").casefold()
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(
        character
        for character in normalized
        if not unicodedata.combining(character)
    )


def serialize_card_faces(card_data):
    faces = card_data.get(
        "card_faces"
    )

    if not isinstance(
        faces,
        list,
    ):
        return None

    try:
        return json.dumps(
            faces,
            ensure_ascii=False,
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def serialize_card_printings(printings):
    if not isinstance(printings, list):
        return None

    try:
        return json.dumps(
            printings,
            ensure_ascii=False,
        )
    except (
        TypeError,
        ValueError,
    ):
        return None


def deserialize_card_faces(value):
    if not value:
        return None

    if isinstance(
        value,
        list,
    ):
        return value

    try:
        faces = json.loads(
            value
        )
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None

    if isinstance(
        faces,
        list,
    ):
        return faces

    return None


def deserialize_card_printings(value):
    if not value:
        return []

    if isinstance(value, list):
        return [
            item
            for item in value
            if isinstance(item, dict)
        ]

    try:
        data = json.loads(value)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return []

    if not isinstance(data, list):
        return []

    return [
        item
        for item in data
        if isinstance(item, dict)
    ]


def extract_image_url(card_data):
    if not card_data:
        return None

    image_url = normalize_image_url(
        card_data.get("image_url")
    )

    if image_url:
        return image_url

    image_uris = card_data.get(
        "image_uris"
    )

    if isinstance(image_uris, dict):
        normal = normalize_image_url(
            image_uris.get("large")
            or image_uris.get("normal")
        )

        if normal:
            return normal

    card_faces = card_data.get(
        "card_faces"
    )

    if isinstance(card_faces, list):
        for face in card_faces:
            if not isinstance(face, dict):
                continue

            face_image_uris = face.get(
                "image_uris"
            )

            if not isinstance(
                face_image_uris,
                dict,
            ):
                continue

            normal = normalize_image_url(
                face_image_uris.get("large")
                or face_image_uris.get("normal")
            )

            if normal:
                return normal

    scryfall_id = (
        card_data.get("scryfall_id")
        or card_data.get("id")
    )

    return build_scryfall_image_url(
        scryfall_id
    )


def get_card_image_path(scryfall_id):
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
# BANCO — INICIALIZAÇÃO
# =========================================================

def init_database():
    connection = get_connection()

    try:
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

                card_faces TEXT,

                quantity INTEGER NOT NULL DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP,

                updated_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS
            idx_cards_scryfall_id
            ON cards(scryfall_id)
            WHERE scryfall_id IS NOT NULL
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_cards_name
            ON cards(name)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_cards_set
            ON cards(set_name)
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_cards_quantity
            ON cards(quantity)
            """
        )

        connection.commit()

    except sqlite3.OperationalError as error:
        connection.rollback()

        print(
            "[DATABASE] Erro operacional ao inicializar:",
            error,
        )

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao inicializar:",
            error,
        )

    finally:
        connection.close()


# =========================================================
# MIGRAÇÃO
# =========================================================

def migrate_database():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            PRAGMA table_info(cards)
            """
        )

        columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        required_columns = {
            "scryfall_id": "TEXT",
            "printed_name": "TEXT",
            "lang": "TEXT",
            "set_code": "TEXT",
            "set_name": "TEXT",
            "collector_number": "TEXT",
            "mana_cost": "TEXT",
            "type_line": "TEXT",
            "oracle_text": "TEXT",
            "power": "TEXT",
            "toughness": "TEXT",
            "image_url": "TEXT",
            "image_path": "TEXT",
            "card_faces": "TEXT",
            "card_printings": "TEXT",
            "preferred_language": "TEXT",
            "preferred_variant": "TEXT",
            "preferred_finish": "TEXT",
            "preferred_image": "TEXT",
            "preferred_face": "INTEGER NOT NULL DEFAULT 0",
            "favorite": "INTEGER NOT NULL DEFAULT 0",
            "custom_tags": "TEXT",
            "last_view": "TIMESTAMP",
            "rarity": "TEXT",
            "cmc": "REAL",
            "colors": "TEXT",
            "color_identity": "TEXT",
            "quantity": "INTEGER NOT NULL DEFAULT 0",
            "created_at": "TIMESTAMP",
            "updated_at": "TIMESTAMP",
        }

        added = 0

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

                added += 1

                print(
                    "[DATABASE] Coluna adicionada:",
                    column_name,
                )

            except sqlite3.OperationalError as error:
                print(
                    "[DATABASE] Erro ao adicionar "
                    f"{column_name}: {error}"
                )

        cursor.execute(
            """
            UPDATE cards
            SET
                quantity = 0
            WHERE quantity IS NULL
            """
        )

        cursor.execute(
            """
            UPDATE cards
            SET
                created_at = COALESCE(
                    created_at,
                    updated_at,
                    CURRENT_TIMESTAMP
                )
            WHERE created_at IS NULL
            """
        )

        cursor.execute(
            """
            UPDATE cards
            SET
                updated_at = COALESCE(
                    updated_at,
                    created_at,
                    CURRENT_TIMESTAMP
                )
            WHERE updated_at IS NULL
            """
        )

        connection.commit()

        print(
            "[DATABASE] Migração concluída.",
            f"Colunas adicionadas: {added}",
        )

    except sqlite3.OperationalError as error:
        connection.rollback()

        print(
            "[DATABASE] Erro operacional na migração:",
            error,
        )

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro na migração:",
            error,
        )

    finally:
        connection.close()


# =========================================================
# INICIALIZAÇÃO COMPLETA
# =========================================================

def initialize_database():
    CARDS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    init_database()
    migrate_database()
    repair_invalid_ids()
    fix_image_urls()
    rebuild_missing_image_paths()


# =========================================================
# CORRIGIR IDS INVÁLIDOS
# =========================================================

def repair_invalid_ids():
    connection = get_connection()

    try:
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

        invalid_ids = []

        for row in rows:
            try:
                if (
                    row["id"] is None
                    or int(row["id"]) <= 0
                ):
                    invalid_ids.append(row)
            except (TypeError, ValueError):
                invalid_ids.append(row)

        if not invalid_ids:
            return 0

        print(
            "[DATABASE] Registros com ID inválido:",
            len(invalid_ids),
        )

        repaired = 0

        for row in invalid_ids:

            data = dict(row)

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
                    image_path,
                    quantity,
                    created_at,
                    updated_at
                FROM cards
                WHERE rowid = ?
                """,
                (
                    data.get("id"),
                ),
            )

            cursor.execute(
                """
                DELETE FROM cards
                WHERE rowid = ?
                """,
                (
                    data.get("id"),
                ),
            )

            repaired += 1

        connection.commit()

        print(
            "[DATABASE] IDs reparados:",
            repaired,
        )

        return repaired

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao reparar IDs:",
            error,
        )

        return 0

    finally:
        connection.close()


# =========================================================
# CORRIGIR URLS DAS IMAGENS
# =========================================================

def fix_image_urls():
    connection = get_connection()

    try:
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

            normalized_url = normalize_image_url(
                image_url
            )

            if (
                not normalized_url
                and scryfall_id
            ):
                normalized_url = (
                    build_scryfall_image_url(
                        scryfall_id
                    )
                )

            if normalized_url != image_url:
                image_url = normalized_url
                changed = True

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
                        card_id,
                    ),
                )

                fixed += 1

        connection.commit()

        print(
            "[DATABASE] Registros de imagem corrigidos:",
            fixed,
        )

        return fixed

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao corrigir imagens:",
            error,
        )

        return 0

    finally:
        connection.close()


# =========================================================
# RECONSTRUIR CAMINHOS DE IMAGEM
# =========================================================

def rebuild_missing_image_paths():
    connection = get_connection()

    try:
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

            expected_path = get_card_image_path(
                scryfall_id
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
                        card_id,
                    ),
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
                            card_id,
                        ),
                    )

                    fixed += 1

        connection.commit()

        print(
            "[DATABASE] Caminhos reconstruídos:",
            fixed,
        )

        return fixed

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao reconstruir imagens:",
            error,
        )

        return 0

    finally:
        connection.close()


# =========================================================
# GARANTIR CARTA NO CATÁLOGO
#
# IMPORTANTE:
#
# quantity = 0
#
# significa:
# a carta existe no banco/catalogo,
# mas NÃO pertence à coleção.
#
# Isso permite colocar uma carta do Scryfall
# diretamente em um deck sem adicioná-la
# à coleção.
# =========================================================

def ensure_card_exists(card_data):
    if not card_data:
        return None

    scryfall_id = (
        card_data.get("scryfall_id")
        or card_data.get("id")
    )

    if scryfall_id:
        scryfall_id = str(
            scryfall_id
        ).strip()

    name = str(
        card_data.get("name")
        or ""
    ).strip()

    if not name:
        return None

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

    type_line = (
        card_data.get("printed_type_line")
        or card_data.get("type_line")
    )

    oracle_text = (
        card_data.get("printed_text")
        or card_data.get("oracle_text")
    )

    power = card_data.get(
        "power"
    )

    toughness = card_data.get(
        "toughness"
    )

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

    card_faces = serialize_card_faces(
        card_data
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

        existing = None

        if scryfall_id:

            cursor.execute(
                """
                SELECT id
                FROM cards
                WHERE scryfall_id = ?
                LIMIT 1
                """,
                (
                    scryfall_id,
                ),
            )

            existing = cursor.fetchone()

        if not existing:

            cursor.execute(
                """
                SELECT id
                FROM cards
                WHERE
                    name = ?
                    AND COALESCE(
                        set_name,
                        ''
                    ) = COALESCE(
                        ?,
                        ''
                    )
                    AND COALESCE(
                        collector_number,
                        ''
                    ) = COALESCE(
                        ?,
                        ''
                    )
                LIMIT 1
                """,
                (
                    name,
                    set_name,
                    collector_number,
                ),
            )

            existing = cursor.fetchone()

        if existing:

            card_id = int(
                existing["id"]
            )

            cursor.execute(
                """
                UPDATE cards
                SET
                    scryfall_id = COALESCE(
                        ?,
                        scryfall_id
                    ),
                    name = ?,
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
                    card_faces = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
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
                    card_faces,
                    card_id,
                ),
            )

            connection.commit()

            return card_id

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
                card_faces,
                quantity
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, 0
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
                card_faces,
            ),
        )

        connection.commit()

        return int(
            cursor.lastrowid
        )

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao garantir carta:",
            error,
        )

        return None

    finally:
        connection.close()


# =========================================================
# ADICIONAR CARTA À COLEÇÃO
#
# Aqui SIM a quantidade aumenta.
# =========================================================

def add_card(card_data, quantity=1):
    if not card_data:
        return False

    try:
        quantity = int(
            quantity
        )
    except (
        TypeError,
        ValueError,
    ):
        quantity = 1

    if quantity <= 0:
        quantity = 1

    card_id = ensure_card_exists(
        card_data
    )

    if not card_id:
        return False

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE cards
            SET
                quantity =
                    quantity + ?,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                quantity,
                card_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao adicionar "
            f"carta à coleção: {error}"
        )

        return False

    finally:
        connection.close()


def update_card_printing(
    card_id,
    card_data,
    printings=None,
    preferred_language=None,
    preferred_variant=None,
    preferred_finish=None,
    preferred_face=None,
):
    try:
        card_id = int(card_id)
    except (
        TypeError,
        ValueError,
    ):
        return False

    if card_id <= 0 or not card_data:
        return False

    scryfall_id = (
        card_data.get("scryfall_id")
        or card_data.get("id")
    )

    if scryfall_id:
        scryfall_id = str(scryfall_id).strip()

    image_url = extract_image_url(card_data)
    image_path = get_card_image_path(scryfall_id)
    image_path_string = str(image_path) if image_path else None
    card_faces = serialize_card_faces(card_data)
    card_printings = serialize_card_printings(printings)

    preferred_language = (
        preferred_language
        or card_data.get("lang")
    )
    preferred_variant = (
        preferred_variant
        or scryfall_id
    )
    preferred_image = image_url

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT scryfall_id
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (
                card_id,
            ),
        )

        current_row = cursor.fetchone()
        current_scryfall_id = (
            current_row["scryfall_id"]
            if current_row
            else None
        )

        if scryfall_id:
            cursor.execute(
                """
                SELECT id
                FROM cards
                WHERE scryfall_id = ?
                    AND id != ?
                LIMIT 1
                """,
                (
                    scryfall_id,
                    card_id,
                ),
            )

            if cursor.fetchone():
                scryfall_id = current_scryfall_id

        cursor.execute(
            """
            UPDATE cards
            SET
                scryfall_id = ?,
                name = ?,
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
                card_faces = ?,
                card_printings = COALESCE(?, card_printings),
                preferred_language = ?,
                preferred_variant = ?,
                preferred_finish = ?,
                preferred_image = ?,
                preferred_face = ?,
                last_view = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                scryfall_id,
                card_data.get("name"),
                card_data.get("printed_name"),
                card_data.get("lang"),
                card_data.get("set_code")
                or card_data.get("set"),
                card_data.get("set_name"),
                card_data.get("collector_number"),
                card_data.get("mana_cost"),
                card_data.get("printed_type_line")
                or card_data.get("type_line"),
                card_data.get("printed_text")
                or card_data.get("oracle_text"),
                card_data.get("power"),
                card_data.get("toughness"),
                image_url,
                image_path_string,
                card_faces,
                card_printings,
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                int(preferred_face or 0),
                card_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception as error:
        connection.rollback()
        print(
            "[DATABASE] Erro ao atualizar impressao:",
            error,
        )
        return False

    finally:
        connection.close()


# =========================================================
# TODAS AS CARTAS DA COLEÇÃO
#
# Somente quantity > 0.
# =========================================================

def get_all_cards():
    connection = get_connection()

    try:
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
                toughness,
                created_at,
                card_faces,
                card_printings,
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                preferred_face,
                favorite,
                custom_tags,
                last_view
            FROM cards
            WHERE quantity > 0
            ORDER BY
                name COLLATE NOCASE ASC
            """
        )

        rows = cursor.fetchall()

        return [
            tuple(row)
            for row in rows
        ]

    finally:
        connection.close()


# =========================================================
# PESQUISAR CARTAS DA COLEÇÃO
# =========================================================

def search_cards(text):
    text = str(
        text or ""
    ).strip()

    if not text:
        return get_all_cards()

    connection = get_connection()

    try:
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
                toughness,
                created_at,
                card_faces,
                card_printings,
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                preferred_face,
                favorite,
                custom_tags,
                last_view
            FROM cards
            WHERE
                quantity > 0
            ORDER BY
                name COLLATE NOCASE ASC
            """
        )

        rows = cursor.fetchall()

        query = normalize_search_text(
            text
        )

        results = []

        for row in rows:
            searchable = " ".join(
                str(row[key] or "")
                for key in row.keys()
                if key in (
                    "name",
                    "printed_name",
                    "set_name",
                    "collector_number",
                    "type_line",
                    "oracle_text",
                )
            )

            if query in normalize_search_text(searchable):
                results.append(
                    tuple(row)
                )

        return results

    finally:
        connection.close()


# =========================================================
# CARTA POR ID
# =========================================================

def get_card_by_id(card_id):
    try:
        card_id = int(
            card_id
        )
    except (
        TypeError,
        ValueError,
    ):
        return None

    if card_id <= 0:
        return None

    connection = get_connection()

    try:
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
                quantity,
                card_faces,
                card_printings,
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                preferred_face,
                favorite,
                custom_tags,
                last_view
            FROM cards
            WHERE id = ?
            """,
            (
                card_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return None

        card = dict(row)
        card["card_faces"] = deserialize_card_faces(
            card.get("card_faces")
        )
        card["card_printings"] = deserialize_card_printings(
            card.get("card_printings")
        )

        return card

    finally:
        connection.close()


# =========================================================
# CARTA PELO SCRYFALL ID
# =========================================================

def get_card_id_by_scryfall_id(
    scryfall_id,
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
            ),
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
            "Scryfall ID:",
            error,
        )

        return None

    finally:
        connection.close()


# =========================================================
# ALTERAR QUANTIDADE DA COLEÇÃO
# =========================================================

def change_quantity(card_id, amount):
    try:
        card_id = int(
            card_id
        )

        amount = int(
            amount
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if card_id <= 0:
        return False

    if amount == 0:
        return True

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT quantity
            FROM cards
            WHERE id = ?
            """,
            (
                card_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return False

        current_quantity = int(
            row["quantity"] or 0
        )

        new_quantity = (
            current_quantity
            + amount
        )

        if new_quantity < 0:
            new_quantity = 0

        connection.close()

        return set_card_quantity(
            card_id,
            new_quantity,
        )

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao alterar "
            "quantidade:",
            error,
        )

        return False

    finally:
        try:
            connection.close()
        except Exception:
            pass


def set_card_quantity(card_id, quantity):
    try:
        card_id = int(
            card_id
        )

        quantity = int(
            quantity
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if card_id <= 0:
        return False

    quantity = max(
        0,
        quantity,
    )

    connection = get_connection()

    try:
        cursor = connection.cursor()

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
                quantity,
                card_id,
            ),
        )

        connection.commit()

        return cursor.rowcount > 0

    except Exception as error:
        connection.rollback()

        print(
            "[DATABASE] Erro ao definir quantidade:",
            error,
        )

        return False

    finally:
        connection.close()


# =========================================================
# ESTATÍSTICAS DA COLEÇÃO
# =========================================================

def get_collection_stats():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT

                COALESCE(
                    SUM(quantity),
                    0
                ) AS total_cards,

                COUNT(
                    CASE
                        WHEN quantity > 0
                        THEN 1
                    END
                ) AS unique_cards,

                COUNT(
                    DISTINCT CASE
                        WHEN quantity > 0
                        THEN set_name
                    END
                ) AS total_sets

            FROM cards
            """
        )

        row = cursor.fetchone()

        if not row:
            return {
                "total_cards": 0,
                "unique_cards": 0,
                "total_sets": 0,
            }

        return {
            "total_cards": int(
                row["total_cards"] or 0
            ),
            "unique_cards": int(
                row["unique_cards"] or 0
            ),
            "total_sets": int(
                row["total_sets"] or 0
            ),
        }

    finally:
        connection.close()


# =========================================================
# TOTAL DE CARTAS NA COLEÇÃO
# =========================================================

def get_total_cards():
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
            FROM cards
            WHERE quantity > 0
            """
        )

        return int(
            cursor.fetchone()[0] or 0
        )

    finally:
        connection.close()


# =========================================================
# CARTAS ÚNICAS NA COLEÇÃO
# =========================================================

def get_unique_cards():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*)
            FROM cards
            WHERE quantity > 0
            """
        )

        return int(
            cursor.fetchone()[0] or 0
        )

    finally:
        connection.close()


# =========================================================
# EXPORTAÇÃO DA COLEÇÃO
# =========================================================

def get_collection_for_export():
    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
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
                c.quantity,
                c.card_faces,
                GROUP_CONCAT(
                    DISTINCT d.name
                ) AS decks
            FROM cards c
            LEFT JOIN deck_cards dc
                ON dc.card_id = c.id
            LEFT JOIN decks d
                ON d.id = dc.deck_id
            WHERE c.quantity > 0
            GROUP BY
                c.id
            ORDER BY
                c.name COLLATE NOCASE ASC
            """
        )

        rows = cursor.fetchall()

        cards = []

        for row in rows:
            card = dict(row)
            card["card_faces"] = deserialize_card_faces(
                card.get("card_faces")
            )
            cards.append(
                card
            )

        return cards

    finally:
        connection.close()


# =========================================================
# CATÁLOGO — CARTAS EXISTENTES NO BANCO
#
# Diferente de get_all_cards():
#
# aqui aparecem também cartas quantity = 0.
#
# Isso é necessário para cartas vindas do Scryfall
# usadas somente em decks.
# =========================================================

def get_all_catalog_cards():
    connection = get_connection()

    try:
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
                quantity,
                created_at,
                updated_at,
                card_faces
            FROM cards
            ORDER BY
                name COLLATE NOCASE ASC
            """
        )

        rows = cursor.fetchall()

        cards = []

        for row in rows:
            card = dict(row)
            card["card_faces"] = deserialize_card_faces(
                card.get("card_faces")
            )
            cards.append(card)

        return cards

    finally:
        connection.close()


# =========================================================
# GARANTIR BANCO PRONTO AO IMPORTAR
# =========================================================

try:
    initialize_database()
except Exception as error:
    print(
        "[DATABASE] Falha na inicialização automática:",
        error,
    )

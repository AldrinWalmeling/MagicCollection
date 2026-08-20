import json
import sqlite3
import unicodedata
from pathlib import Path

print(
    "[DATABASE] ARQUIVO CARREGADO:",
    __file__
)


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

def get_active_database_file():
    """
    Retorna o banco que deve ser utilizado pela aplicação.

    Prioridade:

    1. Banco do perfil ativo.
    2. Save antigo/default.

    Isso mantém compatibilidade com instalações
    antigas que ainda não possuem perfis.
    """

    try:

        from profile_manager import (
            profile_manager,
        )

        active_database = (
            profile_manager
            .get_active_database_path()
        )

        if (
            active_database is not None
            and active_database.exists()
        ):
            return active_database

    except Exception as error:

        print(
            "[DATABASE] "
            "Não foi possível obter banco "
            f"do perfil ativo: {error}"
        )

    # -------------------------------------------------
    # Compatibilidade com save antigo
    # -------------------------------------------------

    return DATABASE_FILE


def get_connection():

    database_file = (
        get_active_database_file()
    )

    connection = sqlite3.connect(
        str(database_file)
    )

    connection.row_factory = (
        sqlite3.Row
    )

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
            image_uris.get("png")
            or image_uris.get("large")
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
                face_image_uris.get("png")
                or face_image_uris.get("large")
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

    png_path = CARDS_DIR / (
        f"{scryfall_id}.png"
    )

    jpg_path = CARDS_DIR / (
        f"{scryfall_id}.jpg"
    )

    # PNG é o formato principal
    if png_path.exists() and png_path.stat().st_size > 0:
        return png_path

    # Compatibilidade com imagens antigas
    if jpg_path.exists() and jpg_path.stat().st_size > 0:
        return jpg_path

    # O caminho oficial continua sendo PNG
    return png_path


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
            "oracle_id": "TEXT",
            "illustration_id": "TEXT",
            "released_at": "TEXT",
            "artist": "TEXT",
            "frame": "TEXT",
            "keywords": "TEXT",
            "games": "TEXT",
            "legalities": "TEXT",

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

            # Preferências da coleção
            "preferred_language": "TEXT",
            "preferred_variant": "TEXT",
            "preferred_finish": "TEXT",
            "preferred_image": "TEXT",
            "preferred_face": "INTEGER NOT NULL DEFAULT 0",

            # Informações gerais
            "favorite": "INTEGER NOT NULL DEFAULT 0",
            "custom_tags": "TEXT",
            "last_view": "TIMESTAMP",
            "rarity": "TEXT",
            "cmc": "REAL",
            "colors": "TEXT",
            "color_identity": "TEXT",

            # Quantidade possuída deste printing
            "quantity": "INTEGER NOT NULL DEFAULT 0",

            # PREÇOS SCRYFALL
            "price_usd": "REAL",
            "price_usd_foil": "REAL",
            "price_usd_etched": "REAL",
            "price_eur": "REAL",
            "price_eur_foil": "REAL",
            "price_tix": "REAL",

            # Referência de preço em Inglês (Imprint).
            # A carta original da coleção NÃO é alterada:
            # o idioma, print, quantidade, favoritos, tags e decks
            # continuam intactos.
            # Estas colunas armazenam APENAS a referência inglesa
            # usada para calcular valores quando o modo
            # "Inglês (Imprint)" está ativo.
            "price_reference_scryfall_id": "TEXT",
            "price_reference_name": "TEXT",
            "price_ref_usd": "REAL",
            "price_ref_usd_foil": "REAL",
            "price_ref_eur": "REAL",
            "price_ref_tix": "REAL",
            "price_ref_rarity": "TEXT",

            # Datas
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

    init_collection_history_database()




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

# =========================================================
# HISTÓRICO DA COLEÇÃO
#
# Responsabilidade:
#
# - Criar a tabela collection_snapshots
# - Criar a tabela collection_snapshot_items
# - Criar índices necessários
#
# IMPORTANTE:
#
# Esta função NÃO cria snapshots.
# Ela apenas garante que a estrutura do banco exista.
# =========================================================

def init_collection_history_database():

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # =====================================================
        # SNAPSHOTS
        #
        # Um snapshot representa um retrato da coleção
        # em determinado momento.
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS collection_snapshots (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                snapshot_date TEXT NOT NULL,

                total_cards INTEGER NOT NULL DEFAULT 0,

                unique_cards INTEGER NOT NULL DEFAULT 0,

                total_sets INTEGER NOT NULL DEFAULT 0,

                value_usd REAL NOT NULL DEFAULT 0,

                usd_brl REAL,

                value_brl REAL NOT NULL DEFAULT 0,

                created_at TIMESTAMP
                    DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # =====================================================
        # ITENS DO SNAPSHOT
        #
        # Guarda exatamente quais cartas faziam parte
        # daquele retrato da coleção.
        # =====================================================

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS
            collection_snapshot_items (

                id INTEGER PRIMARY KEY AUTOINCREMENT,

                snapshot_id INTEGER NOT NULL,

                card_id INTEGER NOT NULL,

                quantity INTEGER NOT NULL DEFAULT 0,

                finish TEXT NOT NULL DEFAULT 'nonfoil',

                unit_price_usd REAL,

                unit_price_brl REAL,

                total_value_usd REAL
                    NOT NULL DEFAULT 0,

                total_value_brl REAL
                    NOT NULL DEFAULT 0,

                FOREIGN KEY (
                    snapshot_id
                )
                REFERENCES collection_snapshots(id)
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
            idx_collection_snapshots_date

            ON collection_snapshots(
                snapshot_date
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_snapshot_items_snapshot

            ON collection_snapshot_items(
                snapshot_id
            )
            """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_snapshot_items_card

            ON collection_snapshot_items(
                card_id
            )
            """
        )

        # =====================================================
        # FINALIZAÇÃO
        # =====================================================

        connection.commit()

        print(
            "[DATABASE] Histórico da coleção inicializado."
        )

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao inicializar "
            "histórico da coleção:",
            error,
        )

        return False

    finally:

        connection.close()

        # =========================================================
        # CRIAR SNAPSHOT DA COLEÇÃO
        #
        # Responsabilidade:
        #
        # - Criar um retrato da coleção atual
        # - Considerar somente cartas com quantity > 0
        # - Calcular o valor atual baseado nos preços salvos
        # - Salvar o resumo em collection_snapshots
        # - Salvar cada carta em collection_snapshot_items
        #
        # IMPORTANTE:
        #
        # O snapshot representa o estado da coleção naquele dia.
        #
        # Depois que for criado, os valores ficam congelados.
        # Se o preço da carta mudar amanhã, o snapshot antigo
        # continua representando o valor que foi registrado naquele dia.
        # =========================================================

def create_collection_snapshot(
        snapshot_date=None,
        usd_brl=None,
):
    from datetime import date

    connection = get_connection()

    try:

        cursor = connection.cursor()

        # =====================================================
        # DATA DO SNAPSHOT
        #
        # Se nenhuma data for informada, usamos o dia atual.
        #
        # Formato:
        #
        # YYYY-MM-DD
        #
        # Exemplo:
        #
        # 2026-08-15
        # =====================================================

        if snapshot_date is None:

            snapshot_date = date.today().isoformat()

        else:

            snapshot_date = str(
                snapshot_date
            ).strip()

        if not snapshot_date:
            print(
                "[SNAPSHOT] Data inválida."
            )

            return None

        # =====================================================
        # IMPEDIR DUPLICAÇÃO DO SNAPSHOT DO DIA
        # =====================================================

        cursor.execute(
            """
            SELECT
                id
            FROM collection_snapshots
            WHERE snapshot_date = ?
            LIMIT 1
            """,
            (
                snapshot_date,
            ),
        )

        existing_snapshot = (
            cursor.fetchone()
        )

        if existing_snapshot:
            print(
                "[SNAPSHOT] Snapshot já existe:",
                snapshot_date,
                "| ID:",
                existing_snapshot["id"],
            )

            return int(
                existing_snapshot["id"]
            )

        # =====================================================
        # BUSCAR CARTAS DA COLEÇÃO
        #
        # IMPORTANTE:
        #
        # quantity > 0
        #
        # Cartas que estão somente no catálogo e possuem
        # quantity = 0 NÃO entram no patrimônio da coleção.
        # =====================================================

        cursor.execute(
            """
            SELECT

                id,
                name,

                quantity,

                price_usd,
                price_usd_foil,
                price_usd_etched

            FROM cards

            WHERE quantity > 0

            ORDER BY id
            """
        )

        cards = cursor.fetchall()

        if not cards:
            print(
                "[SNAPSHOT] Nenhuma carta encontrada "
                "na coleção."
            )

            return None

        # =====================================================
        # VARIÁVEIS DO SNAPSHOT
        # =====================================================

        total_cards = 0
        unique_cards = 0

        total_value_usd = 0.0

        snapshot_items = []

        # =====================================================
        # PROCESSAR CADA CARTA
        # =====================================================

        for card in cards:

            card_id = int(
                card["id"]
            )

            quantity = int(
                card["quantity"] or 0
            )

            if quantity <= 0:
                continue

            # =================================================
            # PREÇO BASE
            #
            # Nesta primeira versão usamos o preço normal.
            #
            # Foil/Etched serão tratados na próxima etapa,
            # quando ligarmos isso ao preferred_finish.
            # =================================================

            unit_price_usd = card[
                "price_usd"
            ]

            if unit_price_usd is None:
                unit_price_usd = 0.0

            try:

                unit_price_usd = float(
                    unit_price_usd
                )

            except (
                    TypeError,
                    ValueError,
            ):

                unit_price_usd = 0.0

            # =================================================
            # VALOR TOTAL DA CARTA
            # =================================================

            total_card_value_usd = (
                    unit_price_usd
                    * quantity
            )

            # =================================================
            # ACUMULAR ESTATÍSTICAS
            # =================================================

            total_cards += quantity

            unique_cards += 1

            total_value_usd += (
                total_card_value_usd
            )

            # =================================================
            # VALOR EM BRL
            #
            # Se usd_brl ainda não estiver disponível,
            # deixamos como 0 por enquanto.
            #
            # Na próxima etapa vamos conectar uma cotação
            # real e obrigatoriamente salvar a cotação usada.
            # =================================================

            if usd_brl is not None:

                try:

                    current_usd_brl = float(
                        usd_brl
                    )

                except (
                        TypeError,
                        ValueError,
                ):

                    current_usd_brl = None

            else:

                current_usd_brl = None

            if current_usd_brl is not None:

                unit_price_brl = (
                        unit_price_usd
                        * current_usd_brl
                )

                total_card_value_brl = (
                        total_card_value_usd
                        * current_usd_brl
                )

            else:

                unit_price_brl = None

                total_card_value_brl = 0.0

            # =================================================
            # GUARDAR ITEM TEMPORÁRIO
            # =================================================

            snapshot_items.append(
                {
                    "card_id": card_id,

                    "quantity": quantity,

                    "finish": "nonfoil",

                    "unit_price_usd":
                        unit_price_usd,

                    "unit_price_brl":
                        unit_price_brl,

                    "total_value_usd":
                        total_card_value_usd,

                    "total_value_brl":
                        total_card_value_brl,
                }
            )

        # =====================================================
        # VALOR TOTAL EM BRL
        # =====================================================

        if current_usd_brl is not None:

            total_value_brl = (
                    total_value_usd
                    * current_usd_brl
            )

        else:

            total_value_brl = 0.0

        # =====================================================
        # TOTAL DE SETS
        #
        # Conta quantos set_name diferentes estão presentes
        # na coleção.
        # =====================================================

        cursor.execute(
            """
            SELECT
                COUNT(
                    DISTINCT set_name
                ) AS total_sets

            FROM cards

            WHERE quantity > 0

            AND set_name IS NOT NULL

            AND TRIM(set_name) != ''
            """
        )

        sets_row = cursor.fetchone()

        total_sets = int(
            sets_row["total_sets"] or 0
        )

        # =====================================================
        # CRIAR SNAPSHOT PRINCIPAL
        # =====================================================

        cursor.execute(
            """
            INSERT INTO collection_snapshots (

                snapshot_date,

                total_cards,

                unique_cards,

                total_sets,

                value_usd,

                usd_brl,

                value_brl

            )

            VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                snapshot_date,

                total_cards,

                unique_cards,

                total_sets,

                total_value_usd,

                current_usd_brl,

                total_value_brl,
            ),
        )

        snapshot_id = int(
            cursor.lastrowid
        )

        # =====================================================
        # INSERIR ITENS DO SNAPSHOT
        # =====================================================

        for item in snapshot_items:
            cursor.execute(
                """
                INSERT INTO
                collection_snapshot_items (

                    snapshot_id,

                    card_id,

                    quantity,

                    finish,

                    unit_price_usd,

                    unit_price_brl,

                    total_value_usd,

                    total_value_brl

                )

                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    snapshot_id,

                    item["card_id"],

                    item["quantity"],

                    item["finish"],

                    item["unit_price_usd"],

                    item["unit_price_brl"],

                    item["total_value_usd"],

                    item["total_value_brl"],
                ),
            )

        # =====================================================
        # SALVAR TUDO
        # =====================================================

        connection.commit()

        # =====================================================
        # LOG
        # =====================================================

        print(
            "[SNAPSHOT] Snapshot criado com sucesso."
        )

        print(
            "[SNAPSHOT] ID:",
            snapshot_id,
        )

        print(
            "[SNAPSHOT] Data:",
            snapshot_date,
        )

        print(
            "[SNAPSHOT] Cartas:",
            total_cards,
        )

        print(
            "[SNAPSHOT] Únicas:",
            unique_cards,
        )

        print(
            "[SNAPSHOT] Sets:",
            total_sets,
        )

        print(
            "[SNAPSHOT] Valor USD:",
            round(
                total_value_usd,
                2,
            ),
        )

        if current_usd_brl is not None:

            print(
                "[SNAPSHOT] Cotação USD/BRL:",
                current_usd_brl,
            )

            print(
                "[SNAPSHOT] Valor BRL:",
                round(
                    total_value_brl,
                    2,
                ),
            )

        else:

            print(
                "[SNAPSHOT] Valor BRL:",
                "aguardando cotação",
            )

        # =====================================================
        # RETORNO
        # =====================================================

        return {
            "id": snapshot_id,

            "snapshot_date":
                snapshot_date,

            "total_cards":
                total_cards,

            "unique_cards":
                unique_cards,

            "total_sets":
                total_sets,

            "value_usd":
                total_value_usd,

            "usd_brl":
                current_usd_brl,

            "value_brl":
                total_value_brl,
        }

    except Exception as error:

        connection.rollback()

        print(
            "[SNAPSHOT] Erro ao criar snapshot:",
            error,
        )

        return None

    finally:

        connection.close()

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

    # =========================================================
    # PREÇOS SCRYFALL
    # =========================================================

    prices = (
            card_data.get("prices")
            or {}
    )

    def _parse_price(value):
        try:
            if value in (
                    None,
                    "",
            ):
                return None

            return float(value)

        except (
                TypeError,
                ValueError,
        ):
            return None

    price_usd = _parse_price(
        prices.get("usd")
    )

    price_usd_foil = _parse_price(
        prices.get("usd_foil")
    )

    price_usd_etched = _parse_price(
        prices.get("usd_etched")
    )

    price_eur = _parse_price(
        prices.get("eur")
    )

    price_eur_foil = _parse_price(
        prices.get("eur_foil")
    )

    price_tix = _parse_price(
        prices.get("tix")
    )

    # =========================================================
    # METADADOS DO SCRYFALL
    # =========================================================

    oracle_id = (
            card_data.get("oracle_id")
            or None
    )

    illustration_id = (
            card_data.get("illustration_id")
            or None
    )

    released_at = (
            card_data.get("released_at")
            or None
    )

    artist = (
            card_data.get("artist")
            or None
    )

    frame = (
            card_data.get("frame")
            or None
    )

    rarity = (
            card_data.get("rarity")
            or None
    )

    cmc = card_data.get(
        "cmc"
    )

    colors = json.dumps(
        card_data.get("colors")
        or [],
        ensure_ascii=False,
    )

    color_identity = json.dumps(
        card_data.get("color_identity")
        or [],
        ensure_ascii=False,
    )

    keywords = json.dumps(
        card_data.get("keywords")
        or [],
        ensure_ascii=False,
    )

    games = json.dumps(
        card_data.get("games")
        or [],
        ensure_ascii=False,
    )

    legalities = json.dumps(
        card_data.get("legalities")
        or {},
        ensure_ascii=False,
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

        # =========================================================
        # IDENTIDADE DO PRINTING
        #
        # O Scryfall ID é a identidade principal da impressão.
        #
        # Não devemos reutilizar automaticamente um registro
        # apenas por nome + set + collector number.
        # =========================================================

        if not existing and not scryfall_id:
            cursor.execute(
                """
                SELECT id
                FROM cards
                WHERE
                    name = ?
                    AND COALESCE(set_name, '') = COALESCE(?, '')
                    AND COALESCE(collector_number, '') = COALESCE(?, '')
                    AND COALESCE(lang, '') = COALESCE(?, '')
                LIMIT 1
                """,
                (
                    name,
                    set_name,
                    collector_number,
                    lang,
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

                    oracle_id = ?,
                    illustration_id = ?,
                    released_at = ?,
                    artist = ?,
                    frame = ?,
                    rarity = ?,
                    cmc = ?,
                    colors = ?,
                    color_identity = ?,
                    keywords = ?,
                    games = ?,
                    legalities = ?,
                    
                    price_usd = ?,
                    price_usd_foil = ?,
                    price_usd_etched = ?,
                    price_eur = ?,
                    price_eur_foil = ?,
                    price_tix = ?,

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

                    oracle_id,
                    illustration_id,
                    released_at,
                    artist,
                    frame,
                    rarity,
                    cmc,
                    colors,
                    color_identity,
                    keywords,
                    games,
                    legalities,

                    price_usd,
                    price_usd_foil,
                    price_usd_etched,
                    price_eur,
                    price_eur_foil,
                    price_tix,

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
        
                oracle_id,
                illustration_id,
                released_at,
                artist,
                frame,
                rarity,
                cmc,
                colors,
                color_identity,
                keywords,
                games,
                legalities,
        
                price_usd,
                price_usd_foil,
                price_usd_etched,
                price_eur,
                price_eur_foil,
                price_tix,
        
                quantity
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
        
                ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?,
        
                ?, ?, ?, ?, ?, ?,
        
                0
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

                oracle_id,
                illustration_id,
                released_at,
                artist,
                frame,
                rarity,
                cmc,
                colors,
                color_identity,
                keywords,
                games,
                legalities,

                price_usd,
                price_usd_foil,
                price_usd_etched,
                price_eur,
                price_eur_foil,
                price_tix,
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
        card_id = int(
            card_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return False

    if (
        card_id <= 0
        or not card_data
    ):
        return False

    # =====================================================
    # IDENTIDADE DO PRINTING
    # =====================================================

    scryfall_id = (
        card_data.get("scryfall_id")
        or card_data.get("id")
    )

    if scryfall_id:
        scryfall_id = str(
            scryfall_id
        ).strip()

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
    # FACES
    # =====================================================

    card_faces = serialize_card_faces(
        card_data
    )

    # =====================================================
    # IMPRESSÕES
    # =====================================================

    card_printings = (
        serialize_card_printings(
            printings
        )
    )

    # =====================================================
    # PREFERÊNCIAS
    # =====================================================

    preferred_language = (
        preferred_language
        or card_data.get("lang")
    )

    preferred_variant = (
        preferred_variant
        or scryfall_id
    )

    preferred_image = image_url

    try:
        preferred_face = int(
            preferred_face
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        preferred_face = 0

    # =====================================================
    # METADADOS SCRYFALL
    # =====================================================

    oracle_id = (
        card_data.get("oracle_id")
        or None
    )

    illustration_id = (
        card_data.get("illustration_id")
        or None
    )

    released_at = (
        card_data.get("released_at")
        or None
    )

    artist = (
        card_data.get("artist")
        or None
    )

    frame = (
        card_data.get("frame")
        or None
    )

    rarity = (
            card_data.get("rarity")
            or None
    )

    cmc = card_data.get(
        "cmc"
    )

    colors = json.dumps(
        card_data.get("colors")
        or [],
        ensure_ascii=False,
    )

    color_identity = json.dumps(
        card_data.get("color_identity")
        or [],
        ensure_ascii=False,
    )

    keywords = json.dumps(
        card_data.get("keywords")
        or [],
        ensure_ascii=False,
    )

    games = json.dumps(
        card_data.get("games")
        or [],
        ensure_ascii=False,
    )

    legalities = json.dumps(
        card_data.get("legalities")
        or {},
        ensure_ascii=False,
    )

    # =====================================================
    # PREÇOS
    # =====================================================

    prices = (
        card_data.get("prices")
        or {}
    )

    def parse_price(value):
        try:
            if value in (
                None,
                "",
            ):
                return None

            return float(
                value
            )

        except (
            TypeError,
            ValueError,
        ):
            return None

    price_usd = parse_price(
        prices.get("usd")
    )

    price_usd_foil = parse_price(
        prices.get("usd_foil")
    )

    price_usd_etched = parse_price(
        prices.get("usd_etched")
    )

    price_eur = parse_price(
        prices.get("eur")
    )

    price_eur_foil = parse_price(
        prices.get("eur_foil")
    )

    price_tix = parse_price(
        prices.get("tix")
    )

    # =====================================================
    # BANCO
    # =====================================================

    connection = get_connection()

    try:
        cursor = connection.cursor()

        # -------------------------------------------------
        # VERIFICAR SCRYFALL ID ATUAL
        # -------------------------------------------------

        cursor.execute(
            """
            SELECT
                scryfall_id
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (
                card_id,
            ),
        )

        current_row = (
            cursor.fetchone()
        )

        current_scryfall_id = (
            current_row["scryfall_id"]
            if current_row
            else None
        )

        # -------------------------------------------------
        # NÃO PERMITIR DUPLICAÇÃO DE PRINTING
        # -------------------------------------------------

        if scryfall_id:

            cursor.execute(
                """
                SELECT
                    id
                FROM cards
                WHERE
                    scryfall_id = ?
                    AND id != ?
                LIMIT 1
                """,
                (
                    scryfall_id,
                    card_id,
                ),
            )

            if cursor.fetchone():

                scryfall_id = (
                    current_scryfall_id
                )

        # -------------------------------------------------
        # ATUALIZAR CARTA
        # -------------------------------------------------

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
                card_printings =
                    COALESCE(
                        ?,
                        card_printings
                    ),

                preferred_language = ?,
                preferred_variant = ?,
                preferred_finish = ?,
                preferred_image = ?,
                preferred_face = ?,

                oracle_id = ?,
                illustration_id = ?,
                released_at = ?,
                artist = ?,
                frame = ?,
                rarity = ?,
                cmc = ?,
                colors = ?,
                color_identity = ?,
                
                keywords = ?,
                games = ?,
                legalities = ?,

                price_usd = ?,
                price_usd_foil = ?,
                price_usd_etched = ?,

                price_eur = ?,
                price_eur_foil = ?,
                price_tix = ?,

                last_view =
                    CURRENT_TIMESTAMP,

                updated_at =
                    CURRENT_TIMESTAMP

            WHERE id = ?
            """,
            (
                # identidade
                scryfall_id,

                # dados principais
                card_data.get(
                    "name"
                ),

                card_data.get(
                    "printed_name"
                ),

                card_data.get(
                    "lang"
                ),

                # edição
                card_data.get(
                    "set_code"
                )
                or card_data.get(
                    "set"
                ),

                card_data.get(
                    "set_name"
                ),

                card_data.get(
                    "collector_number"
                ),

                # carta
                card_data.get(
                    "mana_cost"
                ),

                card_data.get(
                    "printed_type_line"
                )
                or card_data.get(
                    "type_line"
                ),

                card_data.get(
                    "printed_text"
                )
                or card_data.get(
                    "oracle_text"
                ),

                card_data.get(
                    "power"
                ),

                card_data.get(
                    "toughness"
                ),

                # imagem
                image_url,
                image_path_string,

                # faces / impressões
                card_faces,
                card_printings,

                # preferências
                preferred_language,
                preferred_variant,
                preferred_finish,
                preferred_image,
                preferred_face,

                # metadados
                oracle_id,
                illustration_id,
                released_at,
                artist,
                frame,
                rarity,
                cmc,
                colors,
                color_identity,

                keywords,
                games,
                legalities,

                # preços
                price_usd,
                price_usd_foil,
                price_usd_etched,

                price_eur,
                price_eur_foil,
                price_tix,

                # ID local
                card_id,
            ),
        )

        connection.commit()

        return (
            cursor.rowcount > 0
        )

    except Exception as error:

        connection.rollback()

        print(
            "[DATABASE] Erro ao atualizar "
            "impressao:",
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
                last_view,
                rarity,
                colors,
                color_identity,
                cmc
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
                last_view,
                rarity,
                colors,
                color_identity,
                cmc
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
                oracle_id,
                illustration_id,
                released_at,
                artist,
                frame,
                rarity,
                cmc,
                colors,
                color_identity,
                keywords,
                games,
                legalities,
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
                price_usd,
                price_usd_foil,
                price_usd_etched,
                price_eur,
                price_eur_foil,
                price_tix,
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

        try:
            card["keywords"] = json.loads(
                card.get("keywords")
                or "[]"
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            card["keywords"] = []

        try:
            card["games"] = json.loads(
                card.get("games")
                or "[]"
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            card["games"] = []

        try:
            card["legalities"] = json.loads(
                card.get("legalities")
                or "{}"
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            card["legalities"] = {}

            try:
                card["colors"] = json.loads(
                    card.get("colors")
                    or "[]"
                )
            except (
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
            ):
                card["colors"] = []

            try:
                card["color_identity"] = json.loads(
                    card.get("color_identity")
                    or "[]"
                )
            except (
                    TypeError,
                    ValueError,
                    json.JSONDecodeError,
            ):
                card["color_identity"] = []

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
# PREÇOS DE UM PRINTING
# =========================================================

def get_card_prices(card_id):
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
                price_usd,
                price_usd_foil,
                price_usd_etched,
                price_eur,
                price_eur_foil,
                price_tix
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (
                card_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return None

        return {
            "usd": row["price_usd"],
            "usd_foil": row["price_usd_foil"],
            "usd_etched": row["price_usd_etched"],
            "eur": row["price_eur"],
            "eur_foil": row["price_eur_foil"],
            "tix": row["price_tix"],
        }

    finally:
        connection.close()

# =========================================================
# VALOR ESTIMADO DE UM PRINTING
# =========================================================

def get_card_collection_value(
    card_id,
    finish="nonfoil",
):
    try:
        card_id = int(
            card_id
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0.0

    if card_id <= 0:
        return 0.0

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                quantity,
                price_usd,
                price_usd_foil,
                price_usd_etched
            FROM cards
            WHERE id = ?
            LIMIT 1
            """,
            (
                card_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return 0.0

        quantity = int(
            row["quantity"] or 0
        )

        finish = str(
            finish or "nonfoil"
        ).strip().casefold()

        if finish == "foil":
            unit_price = (
                row["price_usd_foil"]
                or row["price_usd"]
                or 0.0
            )

        elif finish == "etched":
            unit_price = (
                row["price_usd_etched"]
                or row["price_usd_foil"]
                or row["price_usd"]
                or 0.0
            )

        else:
            unit_price = (
                row["price_usd"]
                or 0.0
            )

        return float(
            quantity
            * float(unit_price)
        )

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




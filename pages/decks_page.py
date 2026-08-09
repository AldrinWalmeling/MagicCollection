from pathlib import Path
import sqlite3
import requests

from PySide6.QtCore import (
    Qt,
    Signal,
    Slot,
    QObject,
    QTimer,
    QRunnable,
    QThreadPool,
    QSize,
    QEvent,
)

from PySide6.QtGui import (
    QPixmap,
    QIcon,
)


# =========================================================
# CAMINHOS DOS ASSETS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"

ICONS_DIR = ASSETS_DIR / "icons"

COLLECTION_ICON_PATH = ICONS_DIR / "collection_icon.png"

CARD_ICON_PATH = ICONS_DIR / "card_icon.png"

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QGridLayout,
    QDialog,
    QDialogButtonBox,
    QMessageBox,
    QStackedWidget,
    QFileDialog,
    QComboBox,
    QMenu,
)

from services.scryfall import (
    autocomplete_card_names,
    get_card_by_name,
)

from database import (
    get_connection,
    get_all_cards,
    get_card_by_id,
    get_card_image_path,
    get_card_id_by_scryfall_id,
    ensure_card_exists,
    add_card as database_add_card,
    get_collection_stats,
)

from services.decks_database import (
    add_card_to_deck,
    change_deck_card_quantity,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from ui.theme import (
    DARK_THEME,
)


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SAVE_DIR = BASE_DIR / "save"
SAVE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

DATABASE_FILE = SAVE_DIR / "save.db"


# =========================================================
# HELPERS
# =========================================================

def _row_to_dict(row):
    if row is None:
        return None

    if isinstance(row, sqlite3.Row):
        return dict(row)

    if isinstance(row, dict):
        return dict(row)

    return row


def _card_to_dict(card):
    """
    Converte uma carta retornada pelo database.py para dict.

    Estrutura esperada:
        0  id
        1  name
        2  printed_name
        3  lang
        4  set_name
        5  collector_number
        6  mana_cost
        7  type_line
        8  oracle_text
        9  image_url
        10 quantity
        11 image_path
        12 power
        13 toughness
        14 deck_quantity
    """

    if isinstance(card, dict):
        return dict(card)

    if not card:
        return {}

    values = list(card)

    def value(index, default=None):
        if index < len(values):
            return values[index]
        return default

    return {
        "id": value(0),
        "name": value(1),
        "printed_name": value(2),
        "lang": value(3),
        "set_name": value(4),
        "collector_number": value(5),
        "mana_cost": value(6),
        "type_line": value(7),
        "oracle_text": value(8),
        "image_url": value(9),
        "quantity": value(10, 0),
        "image_path": value(11),
        "power": value(12),
        "toughness": value(13),
        "deck_quantity": value(14, 0),
    }


def _get_card_value(card, key, index=None, default=None):
    if isinstance(card, dict):
        return card.get(key, default)

    if index is not None:
        try:
            return card[index]
        except (IndexError, TypeError):
            pass

    return default


def _load_pixmap(path):
    if not path:
        return None

    try:
        path = Path(path)

        if not path.exists():
            return None

        if path.stat().st_size <= 0:
            return None

        pixmap = QPixmap(str(path))

        if pixmap.isNull():
            return None

        return pixmap

    except Exception:
        return None


# =========================================================
# BANCO DE DADOS — DECKS
# =========================================================

def initialize_decks_database():
    connection = get_connection()

    try:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute("PRAGMA foreign_keys = ON")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS decks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                preview_card_id INTEGER,
                preview_image_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("PRAGMA table_info(decks)")

        existing_columns = {
            row["name"]
            for row in cursor.fetchall()
        }

        if "preview_card_id" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN preview_card_id INTEGER
                """
            )

        if "preview_image_path" not in existing_columns:
            cursor.execute(
                """
                ALTER TABLE decks
                ADD COLUMN preview_image_path TEXT
                """
            )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS deck_cards (
                deck_id INTEGER NOT NULL,
                card_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,

                PRIMARY KEY (
                    deck_id,
                    card_id
                ),

                FOREIGN KEY (
                    deck_id
                )
                REFERENCES decks(id)
                ON DELETE CASCADE
            )
            """
        )

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

    except Exception as error:
        connection.rollback()

        print(
            "[DECK DATABASE] Erro ao inicializar:",
            error,
        )

    finally:
        connection.close()


# =========================================================
# BANCO — LISTAR DECKS
# =========================================================

def get_all_decks():
    connection = get_connection()

    try:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                name,
                created_at,
                updated_at,
                preview_card_id,
                preview_image_path
            FROM decks
            ORDER BY
                updated_at DESC,
                id DESC
            """
        )

        rows = cursor.fetchall()

        return [
            dict(row)
            for row in rows
        ]

    except Exception as error:
        print(
            "[DECK] Erro ao listar decks:",
            error,
        )

        return []

    finally:
        connection.close()


# =========================================================
# BANCO — PREVIEW
# =========================================================

def get_deck_preview(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return None

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
            (deck_id,),
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
            "[DECK] Erro ao obter preview:",
            error,
        )

        return None

    finally:
        connection.close()


def set_deck_preview_card(deck_id, card_id):
    try:
        deck_id = int(deck_id)
        card_id = int(card_id)
    except (TypeError, ValueError):
        return False

    if deck_id <= 0 or card_id <= 0:
        return False

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT 1
            FROM deck_cards
            WHERE
                deck_id = ?
                AND card_id = ?
            """,
            (
                deck_id,
                card_id,
            ),
        )

        if not cursor.fetchone():
            return False

        cursor.execute(
            """
            UPDATE decks
            SET
                preview_card_id = ?,
                preview_image_path = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                card_id,
                deck_id,
            ),
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao definir carta de preview:",
            error,
        )

        return False

    finally:
        connection.close()


def set_deck_preview_image(deck_id, image_path):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False

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
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                image_path,
                deck_id,
            ),
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao definir imagem de preview:",
            error,
        )

        return False

    finally:
        connection.close()


def clear_deck_preview(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False

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
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (deck_id,),
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao limpar preview:",
            error,
        )

        return False

    finally:
        connection.close()


# =========================================================
# BANCO — CRIAR DECK
# =========================================================

def create_deck(name):
    name = str(name or "").strip()

    if not name:
        return None

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO decks (name)
            VALUES (?)
            """,
            (name,),
        )

        connection.commit()

        return int(cursor.lastrowid)

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao criar deck:",
            error,
        )

        return None

    finally:
        connection.close()


# =========================================================
# BANCO — RENOMEAR DECK
# =========================================================

def rename_deck(deck_id, name):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False

    name = str(name or "").strip()

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
                deck_id,
            ),
        )

        changed = cursor.rowcount > 0

        connection.commit()

        return changed

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao renomear:",
            error,
        )

        return False

    finally:
        connection.close()


# =========================================================
# BANCO — EXCLUIR DECK
# =========================================================

def delete_deck(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False

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
            (deck_id,),
        )

        deleted = cursor.rowcount > 0

        connection.commit()

        return deleted

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro ao excluir:",
            error,
        )

        return False

    finally:
        connection.close()


# =========================================================
# BANCO — CARTAS DO DECK
# =========================================================

def get_deck_cards(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return []

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
                c.name,
                c.printed_name,
                c.lang,
                c.set_name,
                c.collector_number,
                c.mana_cost,
                c.type_line,
                c.oracle_text,
                c.image_url,
                c.quantity,
                c.image_path,
                c.power,
                c.toughness,
                dc.quantity AS deck_quantity

            FROM deck_cards dc

            INNER JOIN cards c
                ON c.id = dc.card_id

            WHERE dc.deck_id = ?

            ORDER BY
                c.name COLLATE NOCASE ASC
            """,
            (deck_id,),
        )

        rows = cursor.fetchall()

        return [
            tuple(row)
            for row in rows
        ]

    except Exception as error:
        print(
            "[DECK] Erro ao carregar cartas:",
            error,
        )

        return []

    finally:
        connection.close()


# =========================================================
# BANCO — QUANTIDADES
# =========================================================

def get_deck_card_quantities(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return {}

    if deck_id <= 0:
        return {}

    connection = get_connection()

    try:
        connection.row_factory = sqlite3.Row

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                card_id,
                quantity
            FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,),
        )

        rows = cursor.fetchall()

        result = {}

        for row in rows:
            result[int(row["card_id"])] = int(
                row["quantity"] or 0
            )

        return result

    except Exception as error:
        print(
            "[DECK] Erro ao carregar quantidades:",
            error,
        )

        return {}

    finally:
        connection.close()


def get_deck_card_quantity(deck_id, card_id):
    try:
        deck_id = int(deck_id)
        card_id = int(card_id)
    except (TypeError, ValueError):
        return 0

    if deck_id <= 0 or card_id <= 0:
        return 0

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
                card_id,
            ),
        )

        row = cursor.fetchone()

        if not row:
            return 0

        return int(row["quantity"] or 0)

    except Exception:
        return 0

    finally:
        connection.close()


def get_deck_total_cards(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return 0

    if deck_id <= 0:
        return 0

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COALESCE(SUM(quantity), 0)
            FROM deck_cards
            WHERE deck_id = ?
            """,
            (deck_id,),
        )

        row = cursor.fetchone()

        if not row:
            return 0

        return int(row[0] or 0)

    except Exception:
        return 0

    finally:
        connection.close()


# =========================================================
# BANCO — ALTERAR CARTA
# =========================================================



def remove_card_from_deck(deck_id, card_id):
    try:
        deck_id = int(deck_id)
        card_id = int(card_id)
    except (TypeError, ValueError):
        return False

    if deck_id <= 0 or card_id <= 0:
        return False

    connection = get_connection()

    try:
        cursor = connection.cursor()

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

        cursor.execute(
            """
            UPDATE decks
            SET
                preview_card_id = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE
                id = ?
                AND preview_card_id = ?
            """,
            (
                deck_id,
                card_id,
            ),
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError as error:
        connection.rollback()

        print(
            "[DECK] Erro de integridade ao remover carta:",
            error,
        )

        return False

    except sqlite3.OperationalError as error:
        connection.rollback()

        print(
            "[DECK] Erro operacional ao remover carta:",
            error,
        )

        return False

    except Exception as error:
        connection.rollback()

        print(
            "[DECK] Erro inesperado ao remover carta:",
            error,
        )

        return False

    finally:
        connection.close()


def deck_exists(deck_id):
    try:
        deck_id = int(deck_id)
    except (TypeError, ValueError):
        return False

    if deck_id <= 0:
        return False

    connection = get_connection()

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT id
            FROM decks
            WHERE id = ?
            """,
            (deck_id,),
        )

        return bool(cursor.fetchone())

    except Exception:
        return False

    finally:
        connection.close()


# =========================================================
# TASK DE IMAGEM
# =========================================================

class ImageSignals(QObject):

    finished = Signal(
        int,
        str,
        str,
        bytes,
        int,
    )

    failed = Signal(
        str,
        str,
    )


class ImageTask(QRunnable):

    def __init__(
        self,
        url,
        local_path,
        generation,
    ):
        super().__init__()

        self.url = str(url or "")
        self.local_path = str(local_path)
        self.generation = int(generation)

        self.signals = ImageSignals()

    def run(self):

        if not self.url:
            return

        try:

            path = Path(self.local_path)

            if (
                path.exists()
                and path.stat().st_size > 0
            ):

                data = path.read_bytes()

                self.signals.finished.emit(
                    self.card_id,
                    self.url,
                    str(path),
                    data,
                    self.generation,
                )

                return

            headers = {
                "User-Agent": (
                    "MagicCollection/1.0 "
                    "(personal collection manager)"
                ),
                "Accept": "image/*,*/*;q=0.8",
            }

            response = requests.get(
                self.url,
                headers=headers,
                timeout=20,
            )

            response.raise_for_status()

            data = response.content

            if not data:
                raise RuntimeError(
                    "Imagem vazia."
                )

            path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            temp_path = Path(
                str(path) + ".tmp"
            )

            temp_path.write_bytes(data)
            temp_path.replace(path)

            self.signals.finished.emit(
                self.url,
                str(path),
                data,
                self.generation,
            )


        except Exception as error:

            print(
                "[DECK IMAGE] Erro:",
                error,
            )

            self.signals.failed.emit(
                self.url,
                str(error),
            )


# =========================================================
# CARTA CLICÁVEL
# =========================================================

class DeckCardImage(QLabel):

    doubleClicked = Signal()

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.doubleClicked.emit()

            event.accept()

            return

        super().mouseDoubleClickEvent(event)


# =========================================================
# CARD DO DECK
# =========================================================

class DeckCardFrame(QFrame):

    doubleClicked = Signal()

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "DeckCardFrame"
        )

        self.setFixedSize(
            160,
            230,
        )

        self.setMouseTracking(True)

        self.setAttribute(
            Qt.WidgetAttribute.WA_Hover,
            True,
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.image_label = DeckCardImage(self)

        self.image_label.setObjectName(
            "DeckCardImage"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.image_label.setGeometry(
            0,
            0,
            160,
            230,
        )

        self.image_label.setText("")
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    160,
                    230,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)

        self.quantity_badge = QLabel(
            "×0",
            self,
        )

        self.quantity_badge.setObjectName(
            "DeckQuantityBadge"
        )

        self.quantity_badge.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.quantity_badge.setFixedHeight(27)

        self.quantity_badge.move(
            8,
            8,
        )

        self.controls = QFrame(self)

        self.controls.setObjectName(
            "DeckQuantityControls"
        )

        controls_layout = QHBoxLayout(
            self.controls
        )

        controls_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        controls_layout.setSpacing(
            14
        )

        controls_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.minus_button = QPushButton(
            "−",
            self.controls,
        )

        self.minus_button.setObjectName(
            "DeckQuantityButton"
        )

        self.minus_button.setFixedSize(
            32,
            32,
        )

        self.minus_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.minus_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        controls_layout.addWidget(
            self.minus_button,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        self.control_quantity = QLabel(
            "0",
            self.controls,
        )

        self.control_quantity.setObjectName(
            "DeckControlQuantity"
        )

        self.control_quantity.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.control_quantity.setFixedSize(
            34,
            32,
        )

        controls_layout.addWidget(
            self.control_quantity,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

        self.plus_button = QPushButton(
            "+",
            self.controls,
        )

        self.plus_button.setObjectName(
            "DeckQuantityButton"
        )

        self.plus_button.setFixedSize(
            32,
            32,
        )

        self.plus_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.plus_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        controls_layout.addWidget(
            self.plus_button,
            0,
            Qt.AlignmentFlag.AlignCenter,
        )

    def set_quantity(
        self,
        quantity,
    ):

        quantity = max(
            0,
            int(quantity or 0),
        )

        self.quantity_badge.setText(
            f"×{quantity}"
        )


        self.control_quantity.setText(
            str(quantity)
        )

    def resizeEvent(
            self,
            event,
    ):

        super().resizeEvent(
            event
        )

        self.image_label.setGeometry(
            0,
            0,
            self.width(),
            self.height(),
        )

        # -------------------------------------------------
        # CONTROLES DE QUANTIDADE / HOVER
        # -------------------------------------------------

        self.controls.adjustSize()

        control_margin = 4

        self.controls.move(
            self.width()
            - self.controls.width()
            - control_margin,
            self.height()
            - self.controls.height()
            - control_margin,
        )

        # -------------------------------------------------
        # BADGE SUPERIOR DIREITO
        # -------------------------------------------------

        badge_width = 38
        badge_height = 27

        margin_right = 8
        margin_top = 8

        self.quantity_badge.setGeometry(
            self.width()
            - badge_width
            - margin_right,
            margin_top,
            badge_width,
            badge_height,
        )

        self.quantity_badge.raise_()

        self.controls.hide()

    def enterEvent(
        self,
        event,
    ):

        self.controls.show()
        self.controls.raise_()
        self.quantity_badge.raise_()

        super().enterEvent(event)

    def leaveEvent(
        self,
        event,
    ):

        self.controls.hide()

        super().leaveEvent(event)

    def mouseDoubleClickEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.doubleClicked.emit()

            event.accept()

            return

        super().mouseDoubleClickEvent(event)


# =========================================================
# DIALOG — ESCOLHER CAPA
# =========================================================

class DeckPreviewCardDialog(QDialog):

    def __init__(
        self,
        cards,
        parent=None,
    ):
        super().__init__(parent)

        self.selected_card_id = None

        self.setWindowTitle(
            "Escolher carta de capa"
        )

        self.setMinimumSize(
            700,
            520,
        )

        self.setStyleSheet(
            DARK_THEME
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            20,
            20,
            20,
            20,
        )

        layout.setSpacing(14)

        title = QLabel(
            "Escolha uma carta do deck"
        )

        title.setObjectName(
            "DeckPreviewSelectorTitle"
        )

        layout.addWidget(title)

        scroll = QScrollArea()

        scroll.setWidgetResizable(True)

        scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        container = QWidget()

        grid = QGridLayout(container)

        grid.setContentsMargins(
            5,
            5,
            5,
            5,
        )

        grid.setSpacing(14)

        columns = 5

        for index, card in enumerate(cards):

            card_id = int(
                _get_card_value(
                    card,
                    "id",
                    0,
                    0,
                )
                or 0
            )

            button = QPushButton()

            button.setObjectName(
                "DeckPreviewSelectorCard"
            )

            button.setFixedSize(
                120,
                175,
            )

            button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            image_path = _get_card_value(
                card,
                "image_path",
                11,
            )

            pixmap = _load_pixmap(
                image_path
            )

            if pixmap:

                scaled = pixmap.scaled(
                    110,
                    165,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                button.setIcon(
                    QIcon(scaled)
                )

                button.setIconSize(
                    QSize(
                        110,
                        165,
                    )
                )

            else:

                button.setText(
                    str(
                        _get_card_value(
                            card,
                            "name",
                            1,
                            "Carta",
                        )
                    )
                )

            button.clicked.connect(
                lambda checked=False,
                cid=card_id:
                self.select_card(cid)
            )

            row = index // columns
            column = index % columns

            grid.addWidget(
                button,
                row,
                column,
            )

        scroll.setWidget(container)

        layout.addWidget(
            scroll,
            1,
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(buttons)

    def select_card(
        self,
        card_id,
    ):

        self.selected_card_id = int(card_id)

        self.accept()


# =========================================================
# PREVIEW DO DECK
# =========================================================

class DeckPreviewFrame(QFrame):

    clicked = Signal()

    def __init__(
        self,
        deck_data,
        preview_pixmap=None,
        parent=None,
    ):
        super().__init__(parent)

        self.deck_data = deck_data

        self.setObjectName(
            "DeckPreviewFrame"
        )

        self.setFixedSize(
            220,
            315,
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMouseTracking(True)

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            12,
            12,
            12,
            12,
        )

        layout.setSpacing(8)

        self.preview_frame = QFrame()

        self.preview_frame.setObjectName(
            "DeckPreviewImageArea"
        )

        self.preview_frame.setFixedHeight(
            260
        )

        preview_layout = QVBoxLayout(
            self.preview_frame
        )

        preview_layout.setContentsMargins(
            4,
            4,
            4,
            4,
        )

        self.image_label = QLabel()

        self.image_label.setFixedSize(
            180,
            252,
        )

        self.image_label.setScaledContents(False)

        self.image_label.setObjectName(
            "DeckPreviewCard"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed,
        )

        self.image_label.setText("")
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                # Usar mesma proporção que DeckCardFrame (156x226 ajustado para 180x252)
                scaled = pixmap.scaled(
                    180,
                    252,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)

        preview_layout.addWidget(
            self.image_label
        )

        layout.addWidget(
            self.preview_frame
        )

        self.name_label = QLabel(
            deck_data["name"]
        )

        self.name_label.setObjectName(
            "DeckPreviewName"
        )

        self.name_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.name_label.setWordWrap(True)

        layout.addWidget(
            self.name_label
        )

        self.total_label = QLabel(
            "0 cartas"
        )

        self.total_label.setObjectName(
            "DeckPreviewTotal"
        )

        self.total_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.total_label
        )

        if (
            preview_pixmap
            and not preview_pixmap.isNull()
        ):
            self.set_preview_image(
                preview_pixmap
            )

    def set_preview_image(
        self,
        pixmap,
    ):

        if (
            not pixmap
            or pixmap.isNull()
        ):
            return

        # Usar o tamanho do label (180x252) para escala consistente
        scaled = pixmap.scaled(
            180,
            252,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(
            scaled
        )

        self.image_label.setText("")

    def set_total(
        self,
        total,
    ):

        total = int(total or 0)

        self.total_label.setText(
            f"{total} "
            f"{'carta' if total == 1 else 'cartas'}"
        )

    def enterEvent(
        self,
        event,
    ):

        self.setProperty(
            "hover",
            True,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        super().enterEvent(event)

    def leaveEvent(
        self,
        event,
    ):

        self.setProperty(
            "hover",
            False,
        )

        self.style().unpolish(self)
        self.style().polish(self)

        super().leaveEvent(event)

    def mousePressEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.clicked.emit()

            event.accept()

            return

        super().mousePressEvent(event)


# =========================================================
# NOVO DECK
# =========================================================

class NewDeckFrame(QFrame):

    clicked = Signal()

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "NewDeckFrame"
        )

        self.setFixedSize(
            220,
            315,
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        layout = QVBoxLayout(self)

        layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.setSpacing(12)

        plus = QLabel("+")
        plus.setObjectName(
            "NewDeckPlus"
        )

        plus.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(plus)

        text = QLabel("Novo Deck")

        text.setObjectName(
            "NewDeckText"
        )

        text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(text)

    def mousePressEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.clicked.emit()

            event.accept()

            return

        super().mousePressEvent(event)


# =========================================================
# CARTA DA COLEÇÃO
# =========================================================

class CollectionCardItem(QFrame):

    clicked = Signal(int)
    removed = Signal(int)

    def __init__(
        self,
        card,
        deck_quantity,
        parent=None,
    ):
        super().__init__(parent)

        self.card = card

        self.card_id = int(
            _get_card_value(
                card,
                "id",
                0,
                0,
            )
            or 0
        )

        self.deck_quantity = max(
            0,
            int(deck_quantity or 0),
        )

        self.setObjectName(
            "CollectionDeckCard"
        )

        self.setMinimumHeight(86)

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            8,
            8,
            8,
            8,
        )

        layout.setSpacing(10)

        self.image_label = QLabel()

        self.image_label.setObjectName(
            "CollectionDeckThumbnail"
        )

        self.image_label.setFixedSize(
            48,
            68,
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setText("")
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    48,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.image_label.setPixmap(scaled)

        layout.addWidget(
            self.image_label
        )

        info = QWidget()

        info_layout = QVBoxLayout(info)

        info_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        info_layout.setSpacing(2)

        # -------------------------------------------------
        # NOME DA CARTA
        # -------------------------------------------------

        display_name = (
                _get_card_value(
                    card,
                    "printed_name",
                    2,
                    "",
                )
                or ""
        )

        if not str(
                display_name
        ).strip():
            display_name = (
                    _get_card_value(
                        card,
                        "name",
                        1,
                        "Carta",
                    )
                    or "Carta"
            )

        name = QLabel(
            str(
                display_name
            )
        )

        name.setObjectName(
            "CollectionDeckCardName"
        )

        name.setWordWrap(True)

        info_layout.addWidget(
            name
        )

        collection_quantity = max(
            0,
            int(
                _get_card_value(
                    card,
                    "quantity",
                    10,
                    0,
                )
                or 0
            ),
        )

        self.status = QLabel()

        self.status.setObjectName(
            "CollectionDeckCardStatus"
        )

        info_layout.addWidget(
            self.status
        )

        info_layout.addStretch()

        layout.addWidget(
            info,
            1,
        )

        # -------------------------------------------------
        # CONTROLES + / QUANTIDADE / -
        # -------------------------------------------------

        controls = QHBoxLayout()

        controls.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        controls.setSpacing(4)

        self.minus_button = QPushButton("−")

        self.minus_button.setObjectName(
            "CollectionDeckRemoveButton"
        )

        self.minus_button.setFixedSize(
            30,
            30,
        )

        self.minus_button.setToolTip(
            "Remover uma cópia do deck"
        )

        self.minus_button.clicked.connect(
            self.remove_one
        )

        controls.addWidget(
            self.minus_button
        )

        self.quantity_label = QLabel(
            "0"
        )

        self.quantity_label.setObjectName(
            "CollectionDeckQuantity"
        )

        self.quantity_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.quantity_label.setFixedWidth(
            30
        )

        controls.addWidget(
            self.quantity_label
        )

        self.add_button = QPushButton("+")

        self.add_button.setObjectName(
            "CollectionDeckAddButton"
        )

        self.add_button.setFixedSize(
            30,
            30,
        )

        self.add_button.setToolTip(
            "Adicionar uma cópia ao deck"
        )

        self.add_button.clicked.connect(
            self.add_one
        )

        controls.addWidget(
            self.add_button
        )

        layout.addLayout(
            controls
        )

        self.update_state()
        self.load_image()

    def update_state(self):

        collection_quantity = max(
            0,
            int(
                _get_card_value(
                    self.card,
                    "quantity",
                    10,
                    0,
                )
                or 0
            ),
        )

        self.deck_quantity = max(
            0,
            int(self.deck_quantity or 0),
        )

        self.status.setText(
            f"Coleção: {collection_quantity}"
            f"   •   Deck: {self.deck_quantity}"
        )

        self.quantity_label.setText(
            str(self.deck_quantity)
        )

        self.add_button.setEnabled(
            self.deck_quantity < collection_quantity
        )

        self.minus_button.setEnabled(
            self.deck_quantity > 0
        )

    def add_one(self):

        if self.deck_quantity <= 0:
            self.clicked.emit(self.card_id)
            return

        self.clicked.emit(self.card_id)

    def remove_one(self):

        if self.deck_quantity <= 0:
            return

        self.removed.emit(
            self.card_id
        )

    def load_image(self):

        image_path = _get_card_value(
            self.card,
            "image_path",
            11,
        )

        pixmap = _load_pixmap(
            image_path
        )

        if not pixmap:
            return

        scaled = pixmap.scaled(
            48,
            68,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setText("")

        self.image_label.setPixmap(
            scaled
        )

    def mousePressEvent(
        self,
        event,
    ):

        if (
            event.button()
            == Qt.MouseButton.LeftButton
        ):

            self.clicked.emit(
                self.card_id
            )

            event.accept()

            return

        super().mousePressEvent(event)


# =========================================================
# PAINEL LATERAL
# =========================================================

class DeckCollectionPanel(QFrame):

    closed = Signal()
    cardAdded = Signal(int)

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "DeckCollectionPanel"
        )

        self.setFixedWidth(380)

        self.all_cards = []
        self.filtered_cards = []
        self.deck_quantities = {}
        self.deck_id = None

        self.search_timer = QTimer(self)

        self.search_timer.setSingleShot(True)

        self.search_timer.setInterval(180)

        self.search_timer.timeout.connect(
            self.apply_search
        )

        self.setup_ui()

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        layout.setSpacing(12)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = QHBoxLayout()

        title = QLabel(
            "Adicionar cartas"
        )

        title.setObjectName(
            "DeckPanelTitle"
        )

        header.addWidget(title)

        header.addStretch()

        self.close_button = QPushButton("X")

        self.close_button.setObjectName(
            "DeckPanelCloseButton"
        )

        self.close_button.setFixedSize(
            32,
            32,
        )

        self.close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.close_button.setToolTip(
            "Fechar painel"
        )

        self.close_button.clicked.connect(
            self.close_panel
        )

        header.addWidget(
            self.close_button
        )

        layout.addLayout(header)

        # -------------------------------------------------
        # BUSCA
        # -------------------------------------------------

        search_frame = QFrame()

        search_frame.setObjectName(
            "DeckPanelSearchFrame"
        )

        search_layout = QHBoxLayout(
            search_frame
        )

        search_layout.setContentsMargins(
            10,
            0,
            10,
            0,
        )

        search_icon = QLabel("🔎")

        search_layout.addWidget(
            search_icon
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Pesquisar na coleção..."
        )

        self.search_input.setFrame(False)

        self.search_input.textChanged.connect(
            self.schedule_search
        )

        search_layout.addWidget(
            self.search_input
        )

        layout.addWidget(
            search_frame
        )

        # -------------------------------------------------
        # STATUS
        # -------------------------------------------------

        self.status_label = QLabel(
            "Escolha uma carta para adicionar."
        )

        self.status_label.setObjectName(
            "DeckPanelStatus"
        )

        self.status_label.setWordWrap(True)

        layout.addWidget(
            self.status_label
        )

        # -------------------------------------------------
        # LISTA
        # -------------------------------------------------

        self.scroll_area = QScrollArea()

        self.scroll_area.setWidgetResizable(
            True
        )

        self.scroll_area.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.list_container = QWidget()

        self.list_layout = QVBoxLayout(
            self.list_container
        )

        self.list_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.list_layout.setSpacing(7)

        self.list_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        self.scroll_area.setWidget(
            self.list_container
        )

        layout.addWidget(
            self.scroll_area,
            1,
        )

    def open(
        self,
        deck_id,
    ):

        try:
            deck_id = int(deck_id)
        except (TypeError, ValueError):
            return

        if deck_id <= 0:
            return

        self.deck_id = deck_id

        self.search_timer.stop()

        self.search_input.blockSignals(True)

        self.search_input.clear()

        self.search_input.blockSignals(False)

        self.load_cards()

        self.show()
        self.raise_()

        self.search_input.setFocus()

    def load_cards(self):

        self.all_cards = list(
            get_all_cards() or []
        )

        self.deck_quantities = (
            get_deck_card_quantities(
                self.deck_id
            )
        )

        self.apply_search()

    def schedule_search(
        self,
        _text,
    ):

        self.search_timer.start()

    def apply_search(self):

        text = (
            self.search_input
            .text()
            .strip()
            .casefold()
        )

        if not text:

            filtered = list(
                self.all_cards
            )

        else:

            filtered = []

            for card in self.all_cards:

                searchable = " ".join(
                    (
                        str(
                            _get_card_value(
                                card,
                                "name",
                                1,
                                "",
                            )
                            or ""
                        ),
                        str(
                            _get_card_value(
                                card,
                                "printed_name",
                                2,
                                "",
                            )
                            or ""
                        ),
                        str(
                            _get_card_value(
                                card,
                                "set_name",
                                4,
                                "",
                            )
                            or ""
                        ),
                        str(
                            _get_card_value(
                                card,
                                "collector_number",
                                5,
                                "",
                            )
                            or ""
                        ),
                        str(
                            _get_card_value(
                                card,
                                "type_line",
                                7,
                                "",
                            )
                            or ""
                        ),
                    )
                ).casefold()

                if text in searchable:
                    filtered.append(card)

        self.filtered_cards = filtered

        self.render_cards(
            filtered
        )

    def render_cards(
        self,
        cards,
    ):

        self.clear_list()

        visible_count = 0

        for card in cards:

            collection_quantity = max(
                0,
                int(
                    _get_card_value(
                        card,
                        "quantity",
                        10,
                        0,
                    )
                    or 0
                ),
            )

            if collection_quantity <= 0:
                continue

            card_id = int(
                _get_card_value(
                    card,
                    "id",
                    0,
                    0,
                )
                or 0
            )

            deck_quantity = int(
                self.deck_quantities.get(
                    card_id,
                    0,
                )
                or 0
            )

            item = CollectionCardItem(
                card,
                deck_quantity,
            )

            item.clicked.connect(
                self.add_card
            )

            item.removed.connect(
                self.remove_card
            )

            self.list_layout.addWidget(
                item
            )

            visible_count += 1

        if visible_count == 0:

            empty = QLabel(
                "Nenhuma carta encontrada."
            )

            empty.setObjectName(
                "DeckPanelEmpty"
            )

            empty.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            empty.setWordWrap(True)

            self.list_layout.addWidget(
                empty
            )

        self.list_layout.addStretch()

    def clear_list(self):

        while self.list_layout.count():

            item = self.list_layout.takeAt(0)

            widget = item.widget()

            if widget:

                widget.deleteLater()

    def add_card(
            self,
            card_id,
    ):
        if not self.deck_id:
            return

        try:

            card_id = int(
                card_id
            )

        except (
                TypeError,
                ValueError,
        ):

            return

        # =================================================
        # QUANTIDADE ATUAL NO DECK
        # =================================================

        current_quantity = max(
            0,
            int(
                self.deck_quantities.get(
                    card_id,
                    0,
                )
                or 0
            ),
        )

        # =================================================
        # QUANTIDADE DISPONÍVEL NA COLEÇÃO
        # =================================================

        collection_quantity = 0

        for card in self.filtered_cards:

            try:

                current_id = int(
                    _get_card_value(
                        card,
                        "id",
                        0,
                        0,
                    )
                    or 0
                )

            except (
                    TypeError,
                    ValueError,
            ):

                continue

            if current_id != card_id:
                continue

            collection_quantity = max(
                0,
                int(
                    _get_card_value(
                        card,
                        "quantity",
                        10,
                        0,
                    )
                    or 0
                ),
            )

            break

        # =================================================
        # LIMITE DA COLEÇÃO
        # =================================================

        if (
                collection_quantity > 0
                and current_quantity
                >= collection_quantity
        ):
            self.status_label.setText(
                "Limite da coleção atingido."
            )

            return

        # =================================================
        # ALTERAR NO BANCO
        # =================================================

        success = change_deck_card_quantity(
            self.deck_id,
            card_id,
            1,
        )

        if not success:
            return

        # =================================================
        # ATUALIZAR CONTADOR LOCAL
        # =================================================

        self.deck_quantities[card_id] = (
                current_quantity + 1
        )

        self.status_label.setText(
            "Carta adicionada ao deck."
        )

        self.cardAdded.emit(
            card_id
        )

        self.render_cards(
            self.filtered_cards
        )

    def remove_card(
        self,
        card_id,
    ):

        if not self.deck_id:
            return

        current = int(
            self.deck_quantities.get(
                card_id,
                0,
            )
            or 0
        )

        if current <= 0:
            return

        success = change_deck_card_quantity(
            self.deck_id,
            card_id,
            -1,
        )

        if not success:
            return

        new_quantity = max(
            0,
            current - 1,
        )

        if new_quantity <= 0:
            self.deck_quantities.pop(
                card_id,
                None,
            )
        else:
            self.deck_quantities[card_id] = (
                new_quantity
            )

        self.status_label.setText(
            "Carta removida do deck."
        )

        self.cardAdded.emit(
            card_id
        )

        self.render_cards(
            self.filtered_cards
        )

    def close_panel(self):

        self.search_timer.stop()

        self.hide()

        self.closed.emit()

    def closeEvent(
        self,
        event,
    ):

        self.search_timer.stop()

        self.hide()

        self.closed.emit()

        event.ignore()


# =========================================================
# WORKER — SCRYFALL
# =========================================================

class ScryfallWorkerSignals(QObject):

    finished = Signal(object)
    error = Signal(str)


class ScryfallWorker(QRunnable):

    def __init__(
        self,
        text,
    ):

        super().__init__()

        self.text = str(
            text or ""
        ).strip()

        self.signals = ScryfallWorkerSignals()

    def run(
        self,
    ):

        try:

            if not self.text:

                self.signals.finished.emit(
                    []
                )

                return

            response = requests.get(
                "https://api.scryfall.com/cards/search",
                params={
                    "q": self.text,
                    "unique": "prints",
                    "order": "name",
                },
                headers={
                    "User-Agent":
                        "MagicCollection/1.0"
                },
                timeout=10,
            )

            response.raise_for_status()

            payload = response.json()

            cards = payload.get(
                "data",
                []
            )

            if not isinstance(
                cards,
                list,
            ):

                cards = []

            results = []

            for card in cards[:20]:

                if not isinstance(
                    card,
                    dict,
                ):
                    continue

                image_uris = (
                    card.get(
                        "image_uris"
                    )
                    or {}
                )

                results.append(
                    {
                        "name":
                            card.get(
                                "name"
                            )
                            or "Carta",

                        "set_name":
                            card.get(
                                "set_name"
                            )
                            or "",

                        "collector_number":
                            card.get(
                                "collector_number"
                            )
                            or "",

                        "mana_cost":
                            card.get(
                                "mana_cost"
                            )
                            or "",

                        "type_line":
                            card.get(
                                "type_line"
                            )
                            or "",

                        "oracle_text":
                            card.get(
                                "oracle_text"
                            )
                            or "",

                        "image_url":
                            image_uris.get(
                                "normal"
                            )
                            or "",

                        "scryfall_id":
                            card.get(
                                "id"
                            )
                            or "",

                        "set":
                            card.get(
                                "set"
                            )
                            or "",

                        "lang":
                            card.get(
                                "lang"
                            )
                            or "",
                    }
                )

            self.signals.finished.emit(
                results
            )

        except requests.RequestException as error:

            self.signals.error.emit(
                f"Falha de conexão com o Scryfall: {error}"
            )

        except Exception as error:

            self.signals.error.emit(
                f"Erro no worker do Scryfall: {error}"
            )


# =========================================================
# DENTRO DE DeckScryfallPanel
# =========================================================

def __init__(
    self,
    parent=None,
):

    super().__init__(parent)

    self.setObjectName(
        "DeckScryfallPanell"
    )

    self.setFixedWidth(
        380
    )

    self.deck_id = None

    self.all_cards = []

    self.filtered_cards = []

    self.search_pool = QThreadPool(
        self
    )

    self.search_pool.setMaxThreadCount(
        4
    )

    self.current_search_id = 0

    # Mantém referências aos workers ativos.
    self._active_workers = {}

    self.search_timer = QTimer(
        self
    )

    self.search_timer.setSingleShot(
        True
    )

    self.search_timer.setInterval(
        300
    )

    self.search_timer.timeout.connect(
        self.search_scryfall
    )


    self.setup_ui()


# =========================================================
# PESQUISAR NO SCRYFALL
# =========================================================

def search_scryfall(
    self,
):

    text = (
        self.search_input
        .text()
        .strip()
    )

    if not text:

        return

    self.current_search_id += 1

    search_id = (
        self.current_search_id
    )

    self.results_list.clear()

    self.status_label.setText(
        "Pesquisando no Scryfall..."
    )

    worker = ScryfallWorker(
        text
    )

    self._active_workers[
        search_id
    ] = worker

    worker.signals.finished.connect(
        self._on_scryfall_finished
    )

    worker.signals.error.connect(
        self._on_scryfall_error
    )

    self.search_pool.start(
        worker
    )


# =========================================================
# RESULTADO DO WORKER
# IMPORTANTE:
# ESSE MÉTODO RODA NA THREAD PRINCIPAL
# =========================================================

@Slot(object)
def _on_scryfall_finished(
    self,
    cards,
):

    # Descobre o worker atual pelo texto/
    # busca mais recente.
    search_id = (
        self.current_search_id
    )

    self._active_workers.pop(
        search_id,
        None
    )

    if not self.isVisible():

        return

    cards = list(
        cards or []
    )

    self.all_cards = cards

    self.filtered_cards = cards

    if not cards:

        self.status_label.setText(
            "Nenhuma carta encontrada."
        )

    else:

        self.status_label.setText(
            f"{len(cards)} "
            + (
                "resultado encontrado."
                if len(cards) == 1
                else "resultados encontrados."
            )
        )

    self.render_cards(
        cards
    )


# =========================================================
# ERRO DO WORKER
# =========================================================

@Slot(str)
def _on_scryfall_error(
    self,
    error,
):

    search_id = (
        self.current_search_id
    )

    self._active_workers.pop(
        search_id,
        None
    )

    if not self.isVisible():

        return

    self.results_list.clear()

    self.status_label.setText(
        "Erro ao pesquisar no Scryfall."
    )

    print(
        "[SCRYFALL] Erro:",
        error,
    )

# =========================================================
# PAINEL LATERAL — MAGIC / SCRYFALL
# =========================================================

class DeckScryfallPanel(QFrame):

    closed = Signal()
    cardAdded = Signal(int)

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "DeckScryfallPanel"
        )

        self.setFixedWidth(
            380
        )

        self.deck_id = None

        self.all_cards = []
        self.filtered_cards = []
        
        # Filtros
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_rarity = "all"

        self.search_pool = QThreadPool(
            self
        )

        self.search_pool.setMaxThreadCount(
            4
        )

        self.current_search_id = 0

        self.search_timer = QTimer(
            self
        )

        self.search_timer.setSingleShot(
            True
        )

        self.search_timer.setInterval(
            300
        )

        self.search_timer.timeout.connect(
            self.search_scryfall
        )

        self.setup_ui()

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(self):

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            16,
            16,
            16,
            16,
        )

        layout.setSpacing(
            12
        )

        # =================================================
        # HEADER
        # =================================================

        header = QHBoxLayout()

        title = QLabel(
            "Magic / Scryfall"
        )

        title.setObjectName(
            "DeckPanelTitle"
        )

        header.addWidget(
            title
        )

        header.addStretch()

        self.close_button = QPushButton(
            "X"
        )

        self.close_button.setObjectName(
            "DeckPanelCloseButton"
        )

        self.close_button.setFixedSize(
            32,
            32,
        )

        self.close_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.close_button.setToolTip(
            "Fechar painel"
        )

        self.close_button.clicked.connect(
            self.close_panel
        )

        header.addWidget(
            self.close_button
        )

        layout.addLayout(
            header
        )

        # =================================================
        # DESCRIÇÃO
        # =================================================

        description = QLabel(
            "Pesquise cartas do Magic "
            "diretamente no Scryfall."
        )

        description.setObjectName(
            "DeckPanelStatus"
        )

        description.setWordWrap(
            True
        )

        layout.addWidget(
            description
        )

        # =================================================
        # BUSCA E FILTROS
        # =================================================

        search_frame = QFrame()

        search_frame.setObjectName(
            "DeckPanelSearchFrame"
        )

        search_layout = QHBoxLayout(
            search_frame
        )

        search_layout.setContentsMargins(
            10,
            0,
            10,
            0,
        )

        search_layout.setSpacing(
            8
        )

        search_icon = QLabel(
            "🔎"
        )

        search_layout.addWidget(
            search_icon
        )

        self.search_input = QLineEdit()

        self.search_input.setPlaceholderText(
            "Pesquisar carta..."
        )

        self.search_input.setFrame(
            False
        )

        self.search_input.textChanged.connect(
            self.schedule_search
        )

        self.search_input.installEventFilter(
            self
        )

        search_layout.addWidget(
            self.search_input,
            1,
        )
        
        # Botão de filtros dropdown
        self.filters_button = QPushButton("Filtros")
        self.filters_button.setObjectName("DeckPanelFiltersButton")
        self.filters_button.setFixedWidth(70)
        self.filters_button.clicked.connect(self.show_filters_menu)
        search_layout.addWidget(self.filters_button)

        layout.addWidget(
            search_frame
        )

        # =================================================
        # STATUS
        # =================================================

        self.status_label = QLabel(
            "Digite o nome de uma carta."
        )

        self.status_label.setObjectName(
            "DeckPanelStatus"
        )

        self.status_label.setWordWrap(
            True
        )

        layout.addWidget(
            self.status_label
        )

        # =================================================
        # LISTA DE RESULTADOS
        # =================================================

        self.results_list = QListWidget()
        self.results_list.setObjectName("DeckPanelResultsList")

        self.results_list.itemClicked.connect(
            self.add_selected_card
        )
        
        layout.addWidget(
            self.results_list,
            1
        )

    # =====================================================
    # ADICIONAR CARTA SELECIONADA
    # =====================================================

    def add_selected_card(
            self,
            item,
    ):
        """
        Adiciona ao deck a carta selecionada no resultado do Scryfall.
        """

        if item is None:
            return

        card = item.data(
            Qt.ItemDataRole.UserRole
        )

        if not isinstance(
                card,
                dict,
        ):
            self.status_label.setText(
                "Dados da carta inválidos."
            )
            return

        self.add_card(
            card
        )

    # =====================================================
    # FILTROS
    # =====================================================

    def apply_filters(self):
        """Aplica os filtros selecionados (método compatível)"""
        self.apply_filters_with_ui()

    def display_results(self):
        """Exibe os resultados filtrados na lista"""
        try:
            self.results_list.clear()
        except RuntimeError:
            # Widget foi deletado, ignorar
            return
        
        for card in self.filtered_cards:
            item = QListWidgetItem(card.get("name", ""))
            item.setData(Qt.ItemDataRole.UserRole, card)
            self.results_list.addItem(item)
        
        self.status_label.setText(
            f"{len(self.filtered_cards)} resultado(s) encontrado(s)."
        )

    def clear_filters(self):
        """Limpa todos os filtros"""
        self.search_input.clear()
        self.apply_filters()
    
    def show_filters_menu(self):
        """Mostra o menu dropdown de filtros"""
        menu = QMenu(self)
        
        # Filtro de Cor
        color_menu = menu.addMenu("Cor")
        color_menu.addAction("Todas", lambda: self.set_filter_color("all"))
        color_menu.addSeparator()
        color_menu.addAction("Branco (W)", lambda: self.set_filter_color("W"))
        color_menu.addAction("Azul (U)", lambda: self.set_filter_color("U"))
        color_menu.addAction("Preto (B)", lambda: self.set_filter_color("B"))
        color_menu.addAction("Vermelho (R)", lambda: self.set_filter_color("R"))
        color_menu.addAction("Verde (G)", lambda: self.set_filter_color("G"))
        
        # Filtro de Tipo
        type_menu = menu.addMenu("Tipo")
        type_menu.addAction("Todos", lambda: self.set_filter_type("all"))
        type_menu.addSeparator()
        type_menu.addAction("Criatura", lambda: self.set_filter_type("Creature"))
        type_menu.addAction("Instantânea", lambda: self.set_filter_type("Instant"))
        type_menu.addAction("Feitiço", lambda: self.set_filter_type("Sorcery"))
        type_menu.addAction("Encantamento", lambda: self.set_filter_type("Enchantment"))
        type_menu.addAction("Artefato", lambda: self.set_filter_type("Artifact"))
        type_menu.addAction("Planeswalker", lambda: self.set_filter_type("Planeswalker"))
        type_menu.addAction("Terreno", lambda: self.set_filter_type("Land"))
        
        # Filtro de Raridade
        rarity_menu = menu.addMenu("Raridade")
        rarity_menu.addAction("Todas", lambda: self.set_filter_rarity("all"))
        rarity_menu.addSeparator()
        rarity_menu.addAction("Comum", lambda: self.set_filter_rarity("common"))
        rarity_menu.addAction("Incomum", lambda: self.set_filter_rarity("uncommon"))
        rarity_menu.addAction("Rara", lambda: self.set_filter_rarity("rare"))
        rarity_menu.addAction("Mítica", lambda: self.set_filter_rarity("mythic"))
        
        menu.addSeparator()
        
        # Limpar filtros
        menu.addAction("Limpar filtros", self.clear_filters_menu)
        
        # Posicionar menu abaixo do botão
        button_pos = self.filters_button.mapToGlobal(self.filters_button.rect().bottomLeft())
        menu.exec(button_pos)
    
    def set_filter_color(self, color):
        """Define o filtro de cor"""
        self.filter_color = color
        self.apply_filters_with_ui()
    
    def set_filter_type(self, card_type):
        """Define o filtro de tipo"""
        self.filter_type = card_type
        self.apply_filters_with_ui()
    
    def set_filter_rarity(self, rarity):
        """Define o filtro de raridade"""
        self.filter_rarity = rarity
        self.apply_filters_with_ui()
    
    def clear_filters_menu(self):
        """Limpa todos os filtros do menu"""
        self.filter_color = "all"
        self.filter_type = "all"
        self.filter_rarity = "all"
        self.apply_filters_with_ui()
    
    def apply_filters_with_ui(self):
        """Aplica filtros com atualização da UI"""
        if not self.all_cards:
            return
        
        search_text = self.search_input.text().strip().lower()
        
        filtered = []
        
        for card in self.all_cards:
            # Filtro de texto
            if search_text and search_text not in card.get("name", "").lower():
                continue
            
            # Filtro de cor
            if self.filter_color != "all":
                mana_cost = card.get("mana_cost", "")
                if self.filter_color not in mana_cost:
                    continue
            
            # Filtro de tipo
            if self.filter_type != "all":
                type_line = card.get("type_line", "")
                if self.filter_type not in type_line:
                    continue
            
            # Filtro de raridade
            if self.filter_rarity != "all":
                card_rarity = card.get("rarity", "")
                if self.filter_rarity not in card_rarity:
                    continue
            
            filtered.append(card)
        
        self.filtered_cards = filtered
        self.display_results()

    # =====================================================
    # ABRIR
    # =====================================================

    def open(
        self,
        deck_id,
    ):

        try:

            deck_id = int(
                deck_id
            )

        except (
            TypeError,
            ValueError,
        ):

            return

        if deck_id <= 0:
            return

        self.deck_id = deck_id

        self.search_timer.stop()

        self.search_input.blockSignals(
            True
        )

        self.search_input.clear()

        self.search_input.blockSignals(
            False
        )

        self.all_cards = []
        self.filtered_cards = []

        try:
            self.results_list.clear()
        except RuntimeError:
            # Widget foi deletado, ignorar
            pass

        self.status_label.setText(
            "Digite o nome de uma carta."
        )

        self.show()

        self.raise_()

        self.search_input.setFocus()

    # =====================================================
    # BUSCA
    # =====================================================

    def schedule_search(
        self,
        _text,
    ):

        self.search_timer.stop()

        text = (
            self.search_input
            .text()
            .strip()
        )

        if not text:

            self.results_list.clear()

            self.status_label.setText(
                "Digite o nome de uma carta."
            )

            return

        self.status_label.setText(
            "Pesquisando..."
        )

        self.search_timer.start()

    # =====================================================
    # PESQUISAR NO SCRYFALL
    # =====================================================

    def search_scryfall(
            self,
    ):

        text = (
            self.search_input
            .text()
            .strip()
        )

        if not text:
            return

        self.current_search_id += 1

        search_id = (
            self.current_search_id
        )

        self.results_list.clear()

        self.status_label.setText(
            "Pesquisando no Scryfall..."
        )

        worker = ScryfallWorker(
            text
        )

        worker.signals.finished.connect(
            lambda cards,
                   sid=search_id:
            self._scryfall_search_finished(
                sid,
                cards,
            )
        )

        worker.signals.error.connect(
            lambda error,
                   sid=search_id:
            self._scryfall_search_error(
                sid,
                error,
            )
        )

        self.search_pool.start(
            worker
        )

    # =====================================================
    # SCRYFALL — RESULTADO
    # =====================================================

    def _scryfall_search_finished(
            self,
            search_id,
            cards,
    ):

        if (
                search_id
                != self.current_search_id
        ):
            return

        if not self.isVisible():
            return

        cards = list(
            cards or []
        )

        self.all_cards = cards

        # Aplicar filtros aos resultados
        self.apply_filters()

    # =====================================================
    # SCRYFALL — ERRO
    # =====================================================

    def _scryfall_search_error(
            self,
            search_id,
            error,
    ):

        if (
                search_id
                != self.current_search_id
        ):
            return

        self.results_list.clear()

        self.status_label.setText(
            "Erro ao pesquisar no Scryfall."
        )

        print(
            "[SCRYFALL] Erro:",
            error,
        )
    # =====================================================
    # RENDERIZAR RESULTADOS
    # =====================================================

    def render_cards(
        self,
        cards,
    ):

        self.filtered_cards = list(
            cards or []
        )
        
        self.display_results()

    # =====================================================
    # ITEM DA CARTA
    # =====================================================

    def create_card_item(
        self,
        card,
    ):

        if not isinstance(
            card,
            dict,
        ):
            return None

        name = str(
            card.get(
                "name",
                "Carta",
            )
            or "Carta"
        )

        set_name = str(
            card.get(
                "set_name",
                "",
            )
            or ""
        )

        collector_number = str(
            card.get(
                "collector_number",
                "",
            )
            or ""
        )

        item = QPushButton()

        item.setObjectName(
            "DeckScryfallCardItem"
        )

        item.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        item.setMinimumHeight(
            62
        )

        text = name

        if set_name:

            text += (
                f"\n{set_name}"
            )

        if collector_number:

            text += (
                f" • {collector_number}"
            )

        item.setText(
            text
        )

        item.setToolTip(
            "Adicionar esta carta ao deck"
        )

        item.clicked.connect(
            lambda checked=False,
            card_data=card:
            self.add_card(
                card_data
            )
        )

        return item

    # =====================================================
    # ADICIONAR CARTA
    # =====================================================

    def add_card(
            self,
            card,
    ):

        if not self.deck_id:
            self.status_label.setText(
                "Nenhum deck está aberto."
            )

            return

        if not isinstance(
                card,
                dict,
        ):
            self.status_label.setText(
                "Dados da carta inválidos."
            )

            return

        name = str(
            card.get(
                "name",
                "Carta",
            )
            or "Carta"
        ).strip()

        scryfall_id = str(
            card.get(
                "scryfall_id",
                "",
            )
            or ""
        ).strip()

        if not name:
            self.status_label.setText(
                "A carta não possui um nome válido."
            )

            return

        if not scryfall_id:
            self.status_label.setText(
                "A carta não possui um Scryfall ID válido."
            )

            return

        self.status_label.setText(
            f"Adicionando {name}..."
        )

        # =================================================
        # GARANTIR CARTA NO CATÁLOGO
        # =================================================

        card_id = ensure_card_exists(
            card
        )

        if not card_id:
            self.status_label.setText(
                f"Não foi possível preparar "
                f"{name} para o deck."
            )

            return

        # =================================================
        # DECK
        # =================================================

        deck_success = add_card_to_deck(
            self.deck_id,
            card_id,
            1,
        )

        if not deck_success:
            self.status_label.setText(
                f"Não foi possível adicionar "
                f"{name} ao deck."
            )

            return

        # =================================================
        # SUCESSO
        # =================================================

        self.status_label.setText(
            f"{name} adicionada ao deck."
        )

        print(
            "[SCRYFALL] Carta adicionada ao deck:",
            name,
            "| card_id=",
            card_id,
            "| deck_id=",
            self.deck_id,
        )

        self.cardAdded.emit(
            int(card_id)
        )



    # =====================================================
    # LIMPAR LISTA
    # =====================================================
    # TECLADO
    # =====================================================

    def eventFilter(
        self,
        obj,
        event,
    ):

        if (
            obj
            is self.search_input
            and event.type()
            == QEvent.Type.KeyPress
        ):

            key = event.key()

            if key == Qt.Key.Key_Down:

                self.move_selection(
                    1
                )

                return True

            if key == Qt.Key.Key_Up:

                self.move_selection(
                    -1
                )

                return True

            if key in (
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
            ):

                self.activate_selected()

                return True

            if key == Qt.Key.Key_Escape:

                self.close_panel()

                return True

        return super().eventFilter(
            obj,
            event
        )

    # =====================================================
    # NAVEGAR PELOS RESULTADOS
    # =====================================================

    def move_selection(
        self,
        direction,
    ):

        buttons = []

        for index in range(
            self.list_layout.count()
        ):

            item = self.list_layout.itemAt(
                index
            )

            widget = item.widget()

            if isinstance(
                widget,
                QPushButton,
            ):

                buttons.append(
                    widget
                )

        if not buttons:
            return

        current_index = -1

        for index, button in enumerate(
            buttons
        ):

            if button.hasFocus():

                current_index = index

                break

        if current_index < 0:

            new_index = (
                0
                if direction > 0
                else len(buttons) - 1
            )

        else:

            new_index = (
                current_index
                + direction
            )

            new_index = max(
                0,
                min(
                    new_index,
                    len(buttons) - 1,
                )
            )

        buttons[
            new_index
        ].setFocus()

        self.scroll_area.ensureWidgetVisible(
            buttons[
                new_index
            ]
        )

    # =====================================================
    # ATIVAR SELECIONADO
    # =====================================================

    def activate_selected(
        self,
    ):

        focused = self.focusWidget()

        if isinstance(
            focused,
            QPushButton,
        ):

            focused.click()

    # =====================================================
    # FECHAR
    # =====================================================

    def close_panel(
            self,
    ):

        self.current_search_id += 1

        self.search_timer.stop()

        self.hide()

        self.closed.emit()

    # =====================================================
    # CLOSE EVENT
    # =====================================================

    def closeEvent(
            self,
            event,
    ):

        self.current_search_id += 1

        self.search_timer.stop()

        self.hide()

        self.closed.emit()

        event.ignore()


# =========================================================
# DIALOG — NOME
# =========================================================

class DeckNameDialog(QDialog):

    def __init__(
        self,
        title,
        initial_name="",
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(
            title
        )

        self.setMinimumWidth(
            420
        )

        self.setStyleSheet(
            DARK_THEME
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(
            14
        )

        label = QLabel(
            "Nome do deck"
        )

        label.setObjectName(
            "DeckNameDialogLabel"
        )

        layout.addWidget(
            label
        )

        self.input = QLineEdit()

        self.input.setText(
            initial_name
        )

        self.input.setPlaceholderText(
            "Ex.: Meu Commander"
        )

        self.input.selectAll()

        layout.addWidget(
            self.input
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            |
            QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(
            self.validate
        )

        buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            buttons
        )

        self.input.returnPressed.connect(
            self.validate
        )

    def validate(
        self,
    ):

        if not self.input.text().strip():

            self.input.setFocus()

            return

        self.accept()

    def get_name(
        self,
    ):

        return (
            self.input
            .text()
            .strip()
        )


# =========================================================
# DETALHES DA CARTA
# =========================================================

class DeckCardDetailsDialog(QDialog):

    def __init__(
        self,
        card,
        pixmap=None,
        parent=None,
    ):
        super().__init__(parent)

        self.setWindowTitle(
            card.get(
                "name",
                "Carta",
            )
        )

        self.setMinimumSize(
            760,
            620,
        )

        self.setStyleSheet(
            DARK_THEME
        )

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(
            24
        )

        self.image_label = QLabel()

        self.image_label.setObjectName(
            "CardDetailImage"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setFixedSize(
            320,
            450,
        )

        if (
            pixmap
            and not pixmap.isNull()
        ):

            self.set_image(
                pixmap
            )

        else:

            self.image_label.setText(
                "Imagem indisponível"
            )

        layout.addWidget(
            self.image_label
        )

        info = QWidget()

        info_layout = QVBoxLayout(
            info
        )

        info_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        info_layout.setSpacing(
            10
        )

        name = QLabel(
            card.get(
                "name",
                "—",
            )
        )

        name.setObjectName(
            "CardDetailName"
        )

        name.setWordWrap(
            True
        )

        info_layout.addWidget(
            name
        )

        mana_cost = card.get(
            "mana_cost"
        )

        if mana_cost:

            mana = ManaSymbolsWidget(
                mana_cost,
                symbol_size=26,
            )

            info_layout.addWidget(
                mana
            )

        type_label = QLabel(
            card.get(
                "type_line"
            )
            or "—"
        )

        type_label.setObjectName(
            "CardDetailType"
        )

        type_label.setWordWrap(
            True
        )

        info_layout.addWidget(
            type_label
        )

        set_label = QLabel(
            (
                f"Edição: "
                f"{card.get('set_name') or '—'}\n"
                f"Número: "
                f"{card.get('collector_number') or '—'}"
            )
        )

        set_label.setObjectName(
            "CardDetailSet"
        )

        info_layout.addWidget(
            set_label
        )

        quantity_label = QLabel(
            f"Na coleção: "
            f"{card.get('quantity', 0)}"
        )

        quantity_label.setObjectName(
            "CardDetailQuantity"
        )

        info_layout.addWidget(
            quantity_label
        )

        oracle = QLabel(
            card.get(
                "oracle_text"
            )
            or "Sem texto de regras."
        )

        oracle.setObjectName(
            "CardDetailText"
        )

        oracle.setWordWrap(
            True
        )

        oracle.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )

        oracle.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        info_layout.addWidget(
            oracle
        )

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )

        buttons.rejected.connect(
            self.reject
        )

        buttons.accepted.connect(
            self.accept
        )

        info_layout.addWidget(
            buttons
        )

        layout.addWidget(
            info
        )

    def set_image(
        self,
        pixmap,
    ):

        scaled = pixmap.scaled(
            320,
            450,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(
            scaled
        )

        self.image_label.setText("")


# =========================================================
# PÁGINA DE DECKS
# =========================================================

class DecksPage(QWidget):

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setStyleSheet(
            DARK_THEME
        )

        print("[DECKS PAGE] Inicializando DecksPage...")

        initialize_decks_database()

        self.current_deck_id = None
        self.current_deck_name = ""
        self.current_deck_cards = []

        self.image_pool = QThreadPool()

        self.image_pool.setMaxThreadCount(
            8
        )

        self.image_cache = {}
        self._max_image_cache_size = 300

        self.panel_open = False

        self._rendering_cards = False

        # =====================================================
        # REFRESH AGRUPADO DO DECK
        # =====================================================

        self._render_generation = 0

        self._refresh_timer = QTimer(
            self
        )

        self._refresh_timer.setSingleShot(
            True
        )

        self._refresh_timer.setInterval(
            80
        )

        self._refresh_timer.timeout.connect(
            self._flush_deck_refresh
        )

        self._pending_preview_refresh = False

        self.setup_ui()

        self.show_decks()

    def _cleanup_image_cache(self):
        """Remove entradas mais antigas do cache se exceder o limite."""
        if len(self.image_cache) > self._max_image_cache_size:
            # Remove 20% das entradas mais antigas
            keys_to_remove = list(self.image_cache.keys())[:int(self._max_image_cache_size * 0.2)]
            for key in keys_to_remove:
                del self.image_cache[key]

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(
        self,
    ):

        self.main_layout = QVBoxLayout(
            self
        )

        self.main_layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )

        self.main_layout.setSpacing(
            18
        )

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title_area.setSpacing(
            3
        )

        self.title_label = QLabel(
            "Meus decks"
        )

        self.title_label.setObjectName(
            "SectionTitle"
        )

        title_area.addWidget(
            self.title_label
        )

        self.description_label = QLabel(
            "Crie e organize seus decks."
        )

        self.description_label.setObjectName(
            "SectionDescription"
        )

        title_area.addWidget(
            self.description_label
        )

        header.addLayout(
            title_area
        )

        header.addStretch()

        self.header_action = QPushButton(
            "+ Novo Deck"
        )

        self.header_action.setObjectName(
            "DeckHeaderAction"
        )

        self.header_action.clicked.connect(
            self.create_new_deck
        )

        header.addWidget(
            self.header_action
        )

        self.main_layout.addLayout(
            header
        )

        # -------------------------------------------------
        # STACK
        # -------------------------------------------------

        self.stack = QStackedWidget()

        self.main_layout.addWidget(
            self.stack,
            1,
        )

        # =================================================
        # PÁGINA — LISTA DE DECKS
        # =================================================

        self.decks_page = QWidget()

        decks_layout = QVBoxLayout(
            self.decks_page
        )

        decks_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.decks_scroll = QScrollArea()

        self.decks_scroll.setWidgetResizable(
            True
        )

        self.decks_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.decks_container = QWidget()

        self.decks_grid = QGridLayout(
            self.decks_container
        )

        self.decks_grid.setContentsMargins(
            5,
            5,
            5,
            20,
        )

        self.decks_grid.setHorizontalSpacing(
            18
        )

        self.decks_grid.setVerticalSpacing(
            18
        )

        self.decks_grid.setAlignment(
            Qt.AlignmentFlag.AlignTop
            |
            Qt.AlignmentFlag.AlignLeft
        )

        self.decks_scroll.setWidget(
            self.decks_container
        )

        decks_layout.addWidget(
            self.decks_scroll
        )

        self.stack.addWidget(
            self.decks_page
        )

        # =================================================
        # PÁGINA — DECK
        # =================================================

        self.deck_page = QWidget()

        deck_layout = QVBoxLayout(
            self.deck_page
        )

        deck_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        deck_layout.setSpacing(
            14
        )

        # -------------------------------------------------
        # TOOLBAR
        # -------------------------------------------------

        toolbar = QHBoxLayout()

        self.back_button = QPushButton(
            "←  Decks"
        )

        self.back_button.setObjectName(
            "DeckBackButton"
        )

        self.back_button.clicked.connect(
            self.close_deck
        )

        toolbar.addWidget(
            self.back_button
        )

        toolbar.addSpacing(
            10
        )

        self.deck_name_label = QLabel(
            "Deck"
        )

        self.deck_name_label.setObjectName(
            "DeckNameTitle"
        )

        toolbar.addWidget(
            self.deck_name_label
        )

        toolbar.addStretch()

        self.deck_total_label = QLabel(
            "0 cartas"
        )

        self.deck_total_label.setObjectName(
            "DeckTotalLabel"
        )

        toolbar.addWidget(
            self.deck_total_label
        )

        self.rename_button = QPushButton(
            "Renomear"
        )

        self.rename_button.setObjectName(
            "DeckToolbarButton"
        )

        self.rename_button.clicked.connect(
            self.rename_current_deck
        )

        toolbar.addWidget(
            self.rename_button
        )

        self.delete_button = QPushButton(
            "Excluir"
        )

        self.delete_button.setObjectName(
            "DeckDeleteButton"
        )

        self.delete_button.clicked.connect(
            self.delete_current_deck
        )

        toolbar.addWidget(
            self.delete_button
        )

        deck_layout.addLayout(
            toolbar
        )

        # =================================================
        # CAPA + ADICIONAR CARTAS
        # =================================================

        preview_row = QHBoxLayout()

        preview_row.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        preview_row.setSpacing(
            14
        )

        # =================================================
        # CARD — CAPA DO DECK
        # =================================================

        preview_section = QFrame()

        preview_section.setObjectName(
            "DeckPreviewSection"
        )

        preview_layout = QHBoxLayout(
            preview_section
        )

        preview_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        preview_layout.setSpacing(
            14
        )
        
        # Centralizar o preview_section no container
        preview_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # -------------------------------------------------
        # IMAGEM DA CAPA
        # -------------------------------------------------

        self.deck_cover_label = QLabel()

        self.deck_cover_label.setObjectName(
            "DeckCoverImage"
        )

        self.deck_cover_label.setFixedSize(
            120,
            170,
        )

        self.deck_cover_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.deck_cover_label.setText("")
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    120,
                    170,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.deck_cover_label.setPixmap(scaled)

        preview_layout.addWidget(
            self.deck_cover_label
        )

        # -------------------------------------------------
        # INFORMAÇÕES DA CAPA
        # -------------------------------------------------

        cover_info = QVBoxLayout()

        cover_info.setSpacing(
            6
        )

        cover_title = QLabel(
            "Capa do deck"
        )

        cover_title.setObjectName(
            "DeckCoverTitle"
        )

        cover_info.addWidget(
            cover_title
        )

        cover_description = QLabel(
            "Escolha uma carta do deck "
            "ou uma imagem do computador."
        )

        cover_description.setObjectName(
            "DeckCoverDescription"
        )

        cover_description.setWordWrap(
            True
        )

        cover_info.addWidget(
            cover_description
        )

        cover_info.addSpacing(
            4
        )

        # -------------------------------------------------
        # BOTÕES
        # -------------------------------------------------

        self.choose_card_cover_button = QPushButton(
            "Escolher capa do deck"
        )

        self.choose_card_cover_button.setObjectName(
            "DeckCoverButton"
        )

        self.choose_card_cover_button.clicked.connect(
            self.choose_preview_from_card
        )

        cover_info.addWidget(
            self.choose_card_cover_button
        )

        self.choose_image_cover_button = QPushButton(
            "Imagem do computador"
        )

        self.choose_image_cover_button.setObjectName(
            "DeckCoverButton"
        )

        self.choose_image_cover_button.clicked.connect(
            self.choose_preview_from_pc
        )

        cover_info.addWidget(
            self.choose_image_cover_button
        )

        self.clear_cover_button = QPushButton(
            "Usar padrão"
        )

        self.clear_cover_button.setObjectName(
            "DeckCoverResetButton"
        )

        self.clear_cover_button.clicked.connect(
            self.clear_preview
        )

        cover_info.addWidget(
            self.clear_cover_button
        )

        cover_info.addStretch()

        preview_layout.addLayout(
            cover_info,
            1,
        )

        # =================================================
        # CARD — ADICIONAR CARTAS
        # =================================================

        add_cards_section = QFrame()

        add_cards_section.setObjectName(
            "DeckAddCardsSection"
        )

        add_cards_layout = QHBoxLayout(
            add_cards_section
        )

        add_cards_layout.setContentsMargins(
            14,
            14,
            14,
            14,
        )

        add_cards_layout.setSpacing(
            14
        )
        
        # Centralizar o add_cards_section no container
        add_cards_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # =================================================
        # ÍCONE
        # =================================================

        collection_icon = QLabel()

        collection_icon.setObjectName(
            "DeckCollectionIcon"
        )

        collection_icon.setFixedSize(
            120,
            170,
        )

        collection_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        collection_pixmap = QPixmap(
            str(COLLECTION_ICON_PATH)
        )

        if not collection_pixmap.isNull():

            collection_pixmap = collection_pixmap.scaled(
                82,
                82,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            collection_icon.setPixmap(
                collection_pixmap
            )

        else:

            collection_icon.setText(
                "▦"
            )

        add_cards_layout.addWidget(
            collection_icon
        )

        # =================================================
        # INFORMAÇÕES
        # =================================================

        add_cards_info = QVBoxLayout()

        add_cards_info.setSpacing(
            6
        )

        # =================================================
        # TÍTULO
        # =================================================

        add_cards_title = QLabel(
            "Adicionar cartas"
        )

        add_cards_title.setObjectName(
            "DeckAddCardsTitle"
        )

        add_cards_info.addWidget(
            add_cards_title
        )

        # =================================================
        # DESCRIÇÃO
        # =================================================

        add_cards_description = QLabel(
            "Adicione cartas da sua coleção "
            "ou pesquise cartas do Magic."
        )

        add_cards_description.setObjectName(
            "DeckAddCardsDescription"
        )

        add_cards_description.setWordWrap(
            True
        )

        add_cards_info.addWidget(
            add_cards_description
        )

        add_cards_info.addSpacing(
            4
        )

        # =================================================
        # BOTÃO — COLEÇÃO
        # =================================================

        self.add_cards_button = QPushButton(
            "▦  Da coleção"
        )

        self.add_cards_button.setObjectName(
            "DeckAddCardsButton"
        )

        self.add_cards_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.add_cards_button.setToolTip(
            "Adicionar cartas que estão na sua coleção"
        )

        self.add_cards_button.clicked.connect(
            self.toggle_collection_panel
        )

        add_cards_info.addWidget(
            self.add_cards_button
        )

        # =================================================
        # BOTÃO — MAGIC / SCRYFALL
        # =================================================

        self.add_magic_cards_button = QPushButton(
            "✦  Magic / Scryfall"
        )

        self.add_magic_cards_button.setObjectName(
            "DeckAddCardsButton"
        )

        self.add_magic_cards_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.add_magic_cards_button.setToolTip(
            "Pesquisar cartas do Magic diretamente no Scryfall"
        )

        self.add_magic_cards_button.clicked.connect(
            self.toggle_scryfall_panel
        )

        add_cards_info.addWidget(
            self.add_magic_cards_button
        )

        add_cards_info.addStretch()

        add_cards_layout.addLayout(
            add_cards_info,
            1,
        )

        # =================================================
        # ADICIONA OS CARDS
        # =================================================

        preview_row.addWidget(
            preview_section
        )

        preview_row.addWidget(
            add_cards_section
        )

        preview_row.addStretch()

        deck_layout.addLayout(
            preview_row
        )

        # =================================================
        # CONTEÚDO
        # =================================================

        self.deck_content = QWidget()

        self.deck_content_layout = QHBoxLayout(
            self.deck_content
        )

        self.deck_content_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        self.deck_content_layout.setSpacing(
            14
        )

        # -------------------------------------------------
        # GRID
        # -------------------------------------------------

        self.cards_scroll = QScrollArea()

        self.cards_scroll.setWidgetResizable(
            True
        )

        self.cards_scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.cards_container = QWidget()

        self.cards_grid = QGridLayout(
            self.cards_container
        )

        self.cards_grid.setContentsMargins(
            5,
            5,
            5,
            20,
        )

        self.cards_grid.setHorizontalSpacing(
            14
        )

        self.cards_grid.setVerticalSpacing(
            14
        )

        self.cards_grid.setAlignment(
            Qt.AlignmentFlag.AlignTop
            |
            Qt.AlignmentFlag.AlignLeft
        )

        self.cards_scroll.setWidget(
            self.cards_container
        )

        self.deck_content_layout.addWidget(
            self.cards_scroll,
            1,
        )

        # -------------------------------------------------
        # PAINEL — COLEÇÃO
        # -------------------------------------------------

        self.collection_panel = DeckCollectionPanel(
            self
        )

        self.collection_panel.hide()

        self.collection_panel.closed.connect(
            self.close_collection_panel
        )

        self.collection_panel.cardAdded.connect(
            self._panel_card_changed
        )

        self.deck_content_layout.addWidget(
            self.collection_panel,
            0,
        )

        # -------------------------------------------------
        # PAINEL — SCRYFALL
        # -------------------------------------------------

        self.scryfall_panel = DeckScryfallPanel(
            self
        )

        self.scryfall_panel.hide()

        self.scryfall_panel.closed.connect(
            self.close_scryfall_panel
        )

        self.scryfall_panel.cardAdded.connect(
            self._panel_card_changed
        )

        self.deck_content_layout.addWidget(
            self.scryfall_panel,
            0,
        )

        deck_layout.addWidget(
            self.deck_content,
            1,
        )

        self.stack.addWidget(
            self.deck_page
        )

    # =====================================================
    # REFRESH AGRUPADO
    # =====================================================
    def schedule_deck_refresh(
        self,
        load_preview=False,
    ):

        if load_preview:

            self._pending_preview_refresh = True

        self._refresh_timer.start()

    def _flush_deck_refresh(
        self,
    ):

        load_preview = (
            self._pending_preview_refresh
        )

        self._pending_preview_refresh = False

        self.refresh_current_deck(
            load_preview=load_preview
        )
    # =====================================================
    # CALLBACK PAINEL
    # =====================================================

    def _panel_card_changed(
        self,
        _card_id,
    ):

        self.schedule_deck_refresh(
            load_preview=False
        )

    # =====================================================
    # LIMPAR GRID
    # =====================================================

    def clear_grid(
        self,
        grid,
    ):
        while grid.count():

            item = grid.takeAt(
                0
            )

            widget = item.widget()

            if widget:

                widget.setParent(None)

                widget.deleteLater()

    # =====================================================
    # MOSTRAR DECKS
    # =====================================================

    def show_decks(
        self,
    ):
        try:
            self.clear_grid(
                self.decks_grid
            )

            decks = get_all_decks()

            columns = 4

            for index, deck in enumerate(
                decks
            ):

                preview_pixmap = (
                    self.get_deck_preview_pixmap(
                        deck["id"]
                    )
                )

                frame = DeckPreviewFrame(
                    deck,
                    preview_pixmap,
                    self,
                )

                frame.set_total(
                    get_deck_total_cards(
                        deck["id"]
                    )
                )

                frame.clicked.connect(
                    lambda did=deck["id"]:
                    self.open_deck(did)
                )

                row = index // columns

                column = index % columns

                self.decks_grid.addWidget(
                    frame,
                    row,
                    column,
                )

            new_frame = NewDeckFrame(
                self
            )

            new_frame.clicked.connect(
                self.create_new_deck
            )

            index = len(decks)

            row = index // columns

            column = index % columns

            self.decks_grid.addWidget(
                new_frame,
                row,
                column,
            )

            self.stack.setCurrentWidget(
                self.decks_page
            )
            
        except Exception as error:
            print(f"[DECKS] Erro ao mostrar decks: {error}")
            import traceback
            traceback.print_exc()

    # =====================================================
    # PREVIEW DECK
    # =====================================================

    def get_deck_preview_pixmap(
        self,
        deck_id,
    ):

        preview = get_deck_preview(
            deck_id
        )

        if not preview:
            return None

        image_path = preview.get(
            "preview_image_path"
        )

        if image_path:

            pixmap = _load_pixmap(
                image_path
            )

            if pixmap:
                return pixmap

        card_id = preview.get(
            "preview_card_id"
        )

        if card_id:

            image_path = get_card_image_path(
                card_id
            )

            pixmap = _load_pixmap(
                image_path
            )

            if pixmap:
                return pixmap

            card = get_card_by_id(
                card_id
            )

            if card:

                pixmap = _load_pixmap(
                    _get_card_value(
                        card,
                        "image_path",
                        11,
                    )
                )

                if pixmap:
                    return pixmap

        return None

    # =====================================================
    # CRIAR DECK
    # =====================================================

    def create_new_deck(
        self,
    ):

        dialog = DeckNameDialog(
            "Novo deck",
            parent=self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        name = dialog.get_name()

        deck_id = create_deck(
            name
        )

        if not deck_id:

            QMessageBox.warning(
                self,
                "Erro",
                "Não foi possível criar o deck.",
            )

            return

        self.show_decks()

        self.open_deck(
            deck_id
        )

    # =====================================================
    # ABRIR DECK
    # =====================================================

    def open_deck(
        self,
        deck_id,
    ):

        if not deck_exists(
            deck_id
        ):
            return

        self.current_deck_id = int(
            deck_id
        )

        decks = get_all_decks()

        deck = next(
            (
                item
                for item in decks
                if int(item["id"])
                == self.current_deck_id
            ),
            None,
        )

        if not deck:

            self.current_deck_id = None

            return

        self.current_deck_name = (
            deck["name"]
        )

        self.deck_name_label.setText(
            self.current_deck_name
        )

        self.stack.setCurrentWidget(
            self.deck_page
        )

        self.close_collection_panel()

        self.close_scryfall_panel()

        self.panel_open = False

        self.refresh_current_deck()

    # =====================================================
    # ATUALIZAR DECK
    # =====================================================

    def refresh_current_deck(
        self,
        load_preview=True,
    ):

        if not self.current_deck_id:
            return

        self.current_deck_cards = (
            get_deck_cards(
                self.current_deck_id
            )
        )

        total = get_deck_total_cards(
            self.current_deck_id
        )

        self.deck_total_label.setText(
            f"{total} "
            f"{'carta' if total == 1 else 'cartas'}"
        )

        self.render_deck_cards(
            self.current_deck_cards
        )

        if load_preview:

            self.load_current_preview()

    # =====================================================
    # RENDER DECK
    # =====================================================

    def render_deck_cards(
        self,
        cards=None,
    ):

        if self._rendering_cards:
            return

        self._rendering_cards = True

        self._render_generation += 1

        generation = (
            self._render_generation
        )

        try:

            if cards is None:

                cards = (
                    self.current_deck_cards
                )

            self.clear_grid(
                self.cards_grid
            )

            if not cards:

                empty = QLabel(
                    "Nenhuma carta neste deck."
                )

                empty.setObjectName(
                    "DeckEmptyState"
                )

                empty.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                self.cards_grid.addWidget(
                    empty,
                    0,
                    0,
                    1,
                    1,
                )

                return

            viewport_width = (
                self.cards_scroll
                .viewport()
                .width()
            )

            if viewport_width <= 0:

                viewport_width = (
                    self.cards_scroll.width()
                    or 800
                )

            spacing = 14

            card_width = 160

            columns = max(
                1,
                (
                    viewport_width
                    + spacing
                )
                //
                (
                    card_width
                    + spacing
                ),
            )

            for index, card in enumerate(
                cards
            ):

                card_id = int(
                    _get_card_value(
                        card,
                        "id",
                        0,
                        0,
                    )
                    or 0
                )

                quantity = int(
                    _get_card_value(
                        card,
                        "deck_quantity",
                        14,
                        0,
                    )
                    or 0
                )

                frame = DeckCardFrame()

                frame.set_quantity(
                    quantity
                )

                frame.doubleClicked.connect(
                    lambda c=card:
                    self.show_card_details(c)
                )

                frame.minus_button.clicked.connect(
                    lambda checked=False,
                    cid=card_id:
                    self.change_card_quantity(
                        cid,
                        -1,
                    )
                )

                frame.plus_button.clicked.connect(
                    lambda checked=False,
                    cid=card_id:
                    self.change_card_quantity(
                        cid,
                        1,
                    )
                )

                row = index // columns

                column = index % columns

                self.cards_grid.addWidget(
                    frame,
                    row,
                    column,
                    Qt.AlignmentFlag.AlignTop,
                )

                self.load_deck_card_image(
                    frame.image_label,
                    card,
                    generation,
                )

        finally:

            self._rendering_cards = False

    # =====================================================
    # CARREGAR IMAGEM DA CARTA DO DECK
    # =====================================================

    def load_deck_card_image(
        self,
        label,
        card,
        generation,
    ):

        image_path = _get_card_value(
            card,
            "image_path",
            11,
        )

        pixmap = _load_pixmap(
            image_path
        )

        if pixmap:

            scaled = pixmap.scaled(
                156,
                226,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            label.setPixmap(
                scaled
            )

            label.setText("")

            return

        image_url = _get_card_value(
            card,
            "image_url",
            9,
        )

        if not image_url:
            return

        card_id = _get_card_value(
            card,
            "id",
            0,
        )

        cache_dir = (
            BASE_DIR
            / "cache"
            / "cards"
        )

        cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        local_path = (
            cache_dir
            / f"{card_id}.jpg"
        )

        cached_pixmap = _load_pixmap(
            local_path
        )

        if cached_pixmap:

            scaled = cached_pixmap.scaled(
                156,
                226,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            label.setPixmap(
                scaled
            )

            label.setText("")

            return

        task = ImageTask(
            image_url,
            local_path,
            generation,
        )

        task.signals.finished.connect(
            self._image_download_finished,
        )

        task.signals.failed.connect(
            lambda url, error:
            print(
                "[DECK IMAGE] Falha:",
                url,
                error,
            )
        )

        self.image_pool.start(
            task
        )

    # =====================================================
    # IMAGEM BAIXADA
    # =====================================================

    def _image_download_finished(
        self,
        url,
        path,
        data,
        label,
        generation,
    ):

        if generation != self._render_generation:
            return

        if not self.isVisible():
            return

        if not label:
            return

        try:

            pixmap = QPixmap()

            if not pixmap.loadFromData(
                data
            ):

                pixmap = _load_pixmap(
                    path
                )

            if (
                not pixmap
                or pixmap.isNull()
            ):
                return

            self.image_cache[
                str(path)
            ] = pixmap
            
            # Limpar cache se necessário
            self._cleanup_image_cache()

            scaled = pixmap.scaled(
                156,
                226,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            if label:

                label.setPixmap(
                    scaled
                )

                label.setText("")

        except Exception as error:

            print(
                "[DECK IMAGE] Erro ao aplicar imagem:",
                error,
            )

    # =====================================================
    # ALTERAR QUANTIDADE
    # =====================================================

    def change_card_quantity(
        self,
        card_id,
        amount,
    ):

        if not self.current_deck_id:
            return

        success = change_deck_card_quantity(
            self.current_deck_id,
            card_id,
            amount,
        )

        if not success:
            return

        self.schedule_deck_refresh()

        if self.collection_panel.isVisible():

            self.collection_panel.load_cards()

    # =====================================================
    # ABRIR PAINEL — COLEÇÃO
    # =====================================================

    def open_collection_panel(
        self,
    ):

        if not self.current_deck_id:
            return

        self.close_scryfall_panel()

        self.collection_panel.open(
            self.current_deck_id
        )

        self.panel_open = True

    # =====================================================
    # TOGGLE PAINEL — COLEÇÃO
    # =====================================================

    def toggle_collection_panel(
        self,
    ):

        if not self.current_deck_id:
            return

        if self.collection_panel.isVisible():

            self.close_collection_panel()

        else:

            self.open_collection_panel()

    # =====================================================
    # FECHAR PAINEL — COLEÇÃO
    # =====================================================

    def close_collection_panel(
        self,
    ):

        self.panel_open = False

        if self.collection_panel:

            self.collection_panel.search_timer.stop()

            self.collection_panel.hide()

    # =====================================================
    # ABRIR PAINEL — SCRYFALL
    # =====================================================

    def open_scryfall_panel(
        self,
    ):

        if not self.current_deck_id:
            return

        self.close_collection_panel()

        self.scryfall_panel.open(
            self.current_deck_id
        )

        self.panel_open = True

    # =====================================================
    # TOGGLE PAINEL — SCRYFALL
    # =====================================================

    def toggle_scryfall_panel(
        self,
    ):

        if not self.current_deck_id:
            return

        if self.scryfall_panel.isVisible():

            self.close_scryfall_panel()

        else:

            self.open_scryfall_panel()

    # =====================================================
    # FECHAR PAINEL — SCRYFALL
    # =====================================================

    def close_scryfall_panel(
        self,
    ):

        self.panel_open = False

        if self.scryfall_panel:

            self.scryfall_panel.search_timer.stop()

            self.scryfall_panel.hide()
            
            # Não deletar o painel, apenas esconder
            # Isso evita o erro "Internal C++ object already deleted"

    # =====================================================
    # FECHAR DECK
    # =====================================================

    def close_deck(
        self,
    ):

        self.close_collection_panel()

        self.close_scryfall_panel()

        self.current_deck_id = None

        self.current_deck_name = ""

        self.current_deck_cards = []

        self.show_decks()

    # =====================================================
    # RENOMEAR
    # =====================================================

    def rename_current_deck(
        self,
    ):

        if not self.current_deck_id:
            return

        dialog = DeckNameDialog(
            "Renomear deck",
            self.current_deck_name,
            self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        name = dialog.get_name()

        if rename_deck(
            self.current_deck_id,
            name,
        ):

            self.current_deck_name = name

            self.deck_name_label.setText(
                name
            )

            self.show_decks()

            self.stack.setCurrentWidget(
                self.deck_page
            )

    # =====================================================
    # EXCLUIR
    # =====================================================

    def delete_current_deck(
        self,
    ):

        if not self.current_deck_id:
            return

        answer = QMessageBox.question(
            self,
            "Excluir deck",
            (
                "Tem certeza que deseja excluir "
                f'"{self.current_deck_name}"?'
            ),
            QMessageBox.StandardButton.Yes
            |
            QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):
            return

        deck_id = self.current_deck_id

        if delete_deck(
            deck_id
        ):

            self.close_collection_panel()

            self.close_scryfall_panel()

            self.current_deck_id = None

            self.current_deck_name = ""

            self.current_deck_cards = []

            self.show_decks()

    # =====================================================
    # ESCOLHER CAPA — CARTA
    # =====================================================

    def choose_preview_from_card(
        self,
    ):

        if not self.current_deck_id:
            return

        cards = get_deck_cards(
            self.current_deck_id
        )

        if not cards:

            QMessageBox.information(
                self,
                "Deck vazio",
                (
                    "Adicione pelo menos uma carta "
                    "ao deck antes de escolher uma capa."
                ),
            )

            return

        dialog = DeckPreviewCardDialog(
            cards,
            self,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):
            return

        card_id = dialog.selected_card_id

        if not card_id:
            return

        if set_deck_preview_card(
            self.current_deck_id,
            card_id,
        ):

            self.load_current_preview()

            self.show_decks()

            self.stack.setCurrentWidget(
                self.deck_page
            )

    # =====================================================
    # ESCOLHER CAPA — PC
    # =====================================================

    def choose_preview_from_pc(
        self,
    ):

        if not self.current_deck_id:
            return

        file_path, _ = (
            QFileDialog.getOpenFileName(
                self,
                "Escolher imagem",
                "",
                (
                    "Imagens "
                    "(*.png *.jpg *.jpeg "
                    "*.webp *.bmp)"
                ),
            )
        )

        if not file_path:
            return

        if set_deck_preview_image(
            self.current_deck_id,
            file_path,
        ):

            self.load_current_preview()

            self.show_decks()

            self.stack.setCurrentWidget(
                self.deck_page
            )

    # =====================================================
    # LIMPAR CAPA
    # =====================================================

    def clear_preview(
        self,
    ):

        if not self.current_deck_id:
            return

        if clear_deck_preview(
            self.current_deck_id
        ):

            self.load_current_preview()

            self.show_decks()

            self.stack.setCurrentWidget(
                self.deck_page
            )

    # =====================================================
    # CARREGAR PREVIEW ATUAL
    # =====================================================

    def load_current_preview(
        self,
    ):

        self.deck_cover_label.clear()

        self.deck_cover_label.setText("")
        
        # Usar card.png como placeholder
        if CARD_ICON_PATH.exists():
            pixmap = QPixmap(str(CARD_ICON_PATH))
            if not pixmap.isNull():
                scaled = pixmap.scaled(
                    120,
                    170,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self.deck_cover_label.setPixmap(scaled)

        if not self.current_deck_id:
            return

        preview = get_deck_preview(
            self.current_deck_id
        )

        if not preview:
            return

        # -------------------------------------------------
        # IMAGEM PERSONALIZADA
        # -------------------------------------------------

        image_path = preview.get(
            "preview_image_path"
        )

        if image_path:

            pixmap = _load_pixmap(
                image_path
            )

            if pixmap:

                self.set_cover_pixmap(
                    pixmap
                )

                return

        # -------------------------------------------------
        # CARTA
        # -------------------------------------------------

        card_id = preview.get(
            "preview_card_id"
        )

        if card_id:

            image_path = get_card_image_path(
                card_id
            )

            pixmap = _load_pixmap(
                image_path
            )

            if pixmap:

                self.set_cover_pixmap(
                    pixmap
                )

                return

            card = get_card_by_id(
                card_id
            )

            if card:

                pixmap = _load_pixmap(
                    _get_card_value(
                        card,
                        "image_path",
                        11,
                    )
                )

                if pixmap:

                    self.set_cover_pixmap(
                        pixmap
                    )

    # =====================================================
    # DEFINIR IMAGEM DA CAPA
    # =====================================================

    def set_cover_pixmap(
        self,
        pixmap,
    ):

        if (
            not pixmap
            or pixmap.isNull()
        ):
            return

        scaled = pixmap.scaled(
            120,
            170,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.deck_cover_label.setPixmap(
            scaled
        )

        self.deck_cover_label.setText("")

    # =====================================================
    # DETALHES DA CARTA
    # =====================================================

    def show_card_details(
        self,
        card,
    ):

        card_dict = _card_to_dict(
            card
        )

        if not card_dict:
            return

        pixmap = None

        image_path = card_dict.get(
            "image_path"
        )

        if image_path:

            pixmap = _load_pixmap(
                image_path
            )

        dialog = DeckCardDetailsDialog(
            card_dict,
            pixmap,
            self,
        )

        dialog.exec()

    def open_card_details(
        self,
        card_id,
    ):

        card_data = get_card_by_id(
            card_id
        )

        if not card_data:
            return

        self.show_card_details(
            card_data
        )

    # =====================================================
    # RESIZE
    # =====================================================

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        if (
            self.current_deck_id
            and self.stack.currentWidget()
            == self.deck_page
        ):

            QTimer.singleShot(
                0,
                self._refresh_grid_after_resize,
            )

    def _refresh_grid_after_resize(
        self,
    ):

        if (
            not self.current_deck_id
            or self._rendering_cards
        ):
            return

        if (
            self.stack.currentWidget()
            != self.deck_page
        ):
            return

        self.render_deck_cards(
            self.current_deck_cards
        )

    # =====================================================
    # FECHAMENTO
    # =====================================================

    def closeEvent(
        self,
        event,
    ):

        try:

            if self.collection_panel:

                self.collection_panel.search_timer.stop()

                self.collection_panel.hide()

            if self.scryfall_panel:

                self.scryfall_panel.search_timer.stop()

                self.scryfall_panel.hide()

            if self.image_pool:

                self.image_pool.clear()

        except Exception as error:

            print(
                "[DECK] Erro ao fechar:",
                error,
            )

        super().closeEvent(
            event
        )
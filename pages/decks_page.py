from pathlib import Path
import sqlite3
import requests

from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QTimer,
    QRunnable,
    QThreadPool,
    QSize,
)

from PySide6.QtGui import (
    QPixmap,
    QIcon,
)

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
)

from database import (
    get_connection,
    get_all_cards,
    get_card_by_id,
    get_card_image_path,
)

from services.scryfall_symbols import (
    ManaSymbolsWidget,
)

from ui.theme import DARK_THEME


# =========================================================
# CONFIGURAÇÃO
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_FILE = BASE_DIR / "collection.db"


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

def change_deck_card_quantity(
    deck_id,
    card_id,
    amount,
):
    try:
        deck_id = int(deck_id)
        card_id = int(card_id)
        amount = int(amount)
    except (TypeError, ValueError):
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

        cursor.execute(
            """
            SELECT quantity
            FROM cards
            WHERE id = ?
            """,
            (card_id,),
        )

        collection_row = cursor.fetchone()

        if not collection_row:
            return False

        collection_quantity = max(
            0,
            int(collection_row["quantity"] or 0),
        )

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

        deck_row = cursor.fetchone()

        current_quantity = (
            int(deck_row["quantity"] or 0)
            if deck_row
            else 0
        )

        new_quantity = current_quantity + amount

        new_quantity = max(
            0,
            min(
                new_quantity,
                collection_quantity,
            ),
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

        else:

            cursor.execute(
                """
                UPDATE deck_cards
                SET quantity = ?
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

        cursor.execute(
            """
            UPDATE decks
            SET updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (deck_id,),
        )

        connection.commit()

        return True

    except Exception as error:

        connection.rollback()

        print(
            "[DECK] Erro ao alterar carta:",
            error,
        )

        return False

    finally:
        connection.close()


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

    except Exception as error:

        connection.rollback()

        print(
            "[DECK] Erro ao remover carta:",
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
        str,
        str,
        bytes,
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
    ):
        super().__init__()

        self.url = str(url or "")
        self.local_path = str(local_path)
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
                    self.url,
                    str(path),
                    data,
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

        self.image_label.setText("🃏")

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
            5,
            5,
            5,
            5,
        )

        controls_layout.setSpacing(5)

        self.minus_button = QPushButton(
            "−",
            self.controls,
        )

        self.minus_button.setObjectName(
            "DeckQuantityButton"
        )

        self.minus_button.setFixedSize(
            34,
            34,
        )

        controls_layout.addWidget(
            self.minus_button
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

        self.control_quantity.setFixedWidth(36)

        controls_layout.addWidget(
            self.control_quantity
        )

        self.plus_button = QPushButton(
            "+",
            self.controls,
        )

        self.plus_button.setObjectName(
            "DeckQuantityButton"
        )

        self.plus_button.setFixedSize(
            34,
            34,
        )

        controls_layout.addWidget(
            self.plus_button
        )

        self.controls.adjustSize()

        self.controls.move(
            160 - self.controls.width() - 6,
            230 - self.controls.height() - 6,
        )

        self.controls.hide()

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

        super().resizeEvent(event)

        self.image_label.setGeometry(
            0,
            0,
            self.width(),
            self.height(),
        )

        self.controls.adjustSize()

        self.controls.move(
            self.width()
            - self.controls.width()
            - 6,
            self.height()
            - self.controls.height()
            - 6,
        )

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
            235
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

        self.image_label.setObjectName(
            "DeckPreviewCard"
        )

        self.image_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self.image_label.setText("🃏")

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

        scaled = pixmap.scaled(
            150,
            220,
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

        self.image_label.setText("🃏")

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

        name = QLabel(
            str(
                _get_card_value(
                    card,
                    "name",
                    1,
                    "Carta",
                )
            )
        )

        name.setObjectName(
            "CollectionDeckCardName"
        )

        name.setWordWrap(True)

        info_layout.addWidget(name)

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

        success = change_deck_card_quantity(
            self.deck_id,
            card_id,
            1,
        )

        if not success:
            return

        self.deck_quantities[card_id] = (
            self.deck_quantities.get(
                card_id,
                0,
            )
            + 1
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

        self.setWindowTitle(title)

        self.setMinimumWidth(420)

        self.setStyleSheet(
            DARK_THEME
        )

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(14)

        label = QLabel(
            "Nome do deck"
        )

        label.setObjectName(
            "DeckNameDialogLabel"
        )

        layout.addWidget(label)

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

    def validate(self):

        if not self.input.text().strip():

            self.input.setFocus()

            return

        self.accept()

    def get_name(self):

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

        layout = QHBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(24)

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

        info_layout = QVBoxLayout(info)

        info_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        info_layout.setSpacing(10)

        name = QLabel(
            card.get(
                "name",
                "—",
            )
        )

        name.setObjectName(
            "CardDetailName"
        )

        name.setWordWrap(True)

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

        type_label.setWordWrap(True)

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

        oracle.setWordWrap(True)

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

        initialize_decks_database()

        self.current_deck_id = None
        self.current_deck_name = ""
        self.current_deck_cards = []

        self.image_pool = QThreadPool()

        self.image_pool.setMaxThreadCount(
            4
        )

        self.image_cache = {}

        self.panel_open = False

        self._rendering_cards = False

        self.setup_ui()

        self.show_decks()

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(self):

        self.main_layout = QVBoxLayout(
            self
        )

        self.main_layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )

        self.main_layout.setSpacing(18)

        # -------------------------------------------------
        # HEADER
        # -------------------------------------------------

        header = QHBoxLayout()

        title_area = QVBoxLayout()

        title_area.setSpacing(3)

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

        deck_layout.setSpacing(14)

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

        toolbar.addSpacing(10)

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

        preview_row.setSpacing(14)

        # =================================================
        # CARD — CAPA DO DECK
        # =================================================

        preview_section = QFrame()

        preview_section.setObjectName(
            "DeckPreviewSection"
        )

        # IMPORTANTE:
        # limita o tamanho do card da capa
        preview_section.setMaximumWidth(
            430
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

        preview_layout.setSpacing(14)

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

        self.deck_cover_label.setText(
            "🃏"
        )

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

        add_cards_section.setMaximumWidth(
            430
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

        # -------------------------------------------------
        # ÍCONE DA COLEÇÃO
        # -------------------------------------------------

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
            "assets/icons/collection_icon.png"
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

        # -------------------------------------------------
        # INFORMAÇÕES
        # -------------------------------------------------

        add_cards_info = QVBoxLayout()

        add_cards_info.setSpacing(
            6
        )

        # -------------------------------------------------
        # TÍTULO
        # -------------------------------------------------

        add_cards_title = QLabel(
            "Adicionar cartas"
        )

        add_cards_title.setObjectName(
            "DeckAddCardsTitle"
        )

        add_cards_info.addWidget(
            add_cards_title
        )

        # -------------------------------------------------
        # DESCRIÇÃO
        # -------------------------------------------------

        add_cards_description = QLabel(
            "Adicione cartas vindas da "
            "sua coleção ao deck."
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

        # -------------------------------------------------
        # BOTÃO
        # -------------------------------------------------

        self.add_cards_button = QPushButton(
            "+ Adicionar cartas"
        )

        self.add_cards_button.setObjectName(
            "DeckAddCardsButton"
        )

        self.add_cards_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.add_cards_button.clicked.connect(
            self.toggle_collection_panel
        )

        add_cards_info.addWidget(
            self.add_cards_button
        )

        add_cards_info.addStretch()

        add_cards_layout.addLayout(
            add_cards_info,
            1,
        )

        # =================================================
        # ADICIONA OS DOIS CARDS
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
        # PAINEL
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

        deck_layout.addWidget(
            self.deck_content,
            1,
        )

        self.stack.addWidget(
            self.deck_page
        )

    # =====================================================
    # CALLBACK PAINEL
    # =====================================================

    def _panel_card_changed(
        self,
        _card_id,
    ):

        self.refresh_current_deck(
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

            item = grid.takeAt(0)

            widget = item.widget()

            if widget:

                widget.setParent(None)
                widget.deleteLater()

    # =====================================================
    # MOSTRAR DECKS
    # =====================================================

    def show_decks(self):

        self.clear_grid(
            self.decks_grid
        )

        decks = get_all_decks()

        columns = 4

        for index, deck in enumerate(decks):

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

    def create_new_deck(self):

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

        if not deck_exists(deck_id):
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

        self.collection_panel.hide()

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

        try:

            if cards is None:
                cards = self.current_deck_cards

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
        )

        task.signals.finished.connect(
            lambda url, path, data,
            lbl=label:
            self._image_download_finished(
                url,
                path,
                data,
                lbl,
            )
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
    ):

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

        if change_deck_card_quantity(
            self.current_deck_id,
            card_id,
            amount,
        ):

            self.refresh_current_deck()

            if (
                self.collection_panel.isVisible()
            ):
                self.collection_panel.load_cards()

    # =====================================================
    # ABRIR PAINEL
    # =====================================================

    def open_collection_panel(self):

        if not self.current_deck_id:
            return

        self.collection_panel.open(
            self.current_deck_id
        )

        self.panel_open = True

    # =====================================================
    # TOGGLE PAINEL
    # =====================================================

    def toggle_collection_panel(self):

        if not self.current_deck_id:
            return

        if self.collection_panel.isVisible():

            self.close_collection_panel()

        else:

            self.open_collection_panel()

    # =====================================================
    # FECHAR PAINEL
    # =====================================================

    def close_collection_panel(self):

        self.panel_open = False

        if self.collection_panel:

            self.collection_panel.search_timer.stop()
            self.collection_panel.hide()

    # =====================================================
    # FECHAR DECK
    # =====================================================

    def close_deck(self):

        self.close_collection_panel()

        self.current_deck_id = None
        self.current_deck_name = ""
        self.current_deck_cards = []

        self.show_decks()

    # =====================================================
    # RENOMEAR
    # =====================================================

    def rename_current_deck(self):

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

    def delete_current_deck(self):

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

        self.deck_cover_label.setText(
            "🃏"
        )

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

        super().resizeEvent(event)

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
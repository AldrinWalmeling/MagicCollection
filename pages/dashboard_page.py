import json
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    Signal,
)
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
)

from database import get_connection
from services.scryfall_symbols import ManaSymbolsWidget

# =========================================================
# CARD DE DECK DO DASHBOARD
# =========================================================

class DashboardDeckCard(QFrame):

    clicked = Signal(int)

    def __init__(
        self,
        deck_id,
        parent=None,
    ):
        super().__init__(
            parent
        )

        self.deck_id = int(
            deck_id
        )

        self.setObjectName(
            "DashboardDeckCard"
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
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
                self.deck_id
            )

            event.accept()

            return

        super().mousePressEvent(
            event
        )


# =========================================================
# DASHBOARD
# =========================================================

class DashboardPage(QWidget):

    deck_clicked = Signal(int)

    def __init__(
        self,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "DashboardPage"
        )

        self.setup_ui()

        self.refresh()


    # =====================================================
    # SETUP UI
    # =====================================================

    def setup_ui(
        self,
    ):

        root_layout = QVBoxLayout(
            self
        )

        root_layout.setContentsMargins(
            28,
            24,
            28,
            24,
        )

        root_layout.setSpacing(
            16
        )

        # =================================================
        # HEADER
        # =================================================

        header = QHBoxLayout()

        header.setSpacing(
            12
        )

        title_column = QVBoxLayout()

        title_column.setSpacing(
            3
        )

        self.title_label = QLabel(
            "Dashboard"
        )

        self.title_label.setObjectName(
            "DashboardTitle"
        )

        self.subtitle_label = QLabel(
            "Visão geral da sua coleção e dos seus decks."
        )

        self.subtitle_label.setObjectName(
            "DashboardSubtitle"
        )

        title_column.addWidget(
            self.title_label
        )

        title_column.addWidget(
            self.subtitle_label
        )

        header.addLayout(
            title_column
        )

        header.addStretch()

        self.updated_label = QLabel(
            "Dados da coleção"
        )

        self.updated_label.setObjectName(
            "DashboardUpdated"
        )

        header.addWidget(
            self.updated_label,
            0,
            Qt.AlignmentFlag.AlignTop
        )

        root_layout.addLayout(
            header
        )

        # =================================================
        # SCROLL
        # =================================================

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "DashboardScroll"
        )

        self.scroll.setWidgetResizable(
            True
        )

        self.scroll.setFrameShape(
            QFrame.Shape.NoFrame
        )

        self.scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        content = QWidget()

        content.setObjectName(
            "DashboardContent"
        )

        self.content_layout = QVBoxLayout(
            content
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            4,
            0
        )

        self.content_layout.setSpacing(
            14
        )

        self.scroll.setWidget(
            content
        )

        root_layout.addWidget(
            self.scroll,
            1
        )


    # =====================================================
    # REFRESH
    # =====================================================

    def refresh(
        self,
    ):

        stats = self._load_statistics()

        self._clear_content()

        # =================================================
        # STAT CARDS
        # =================================================

        stats_grid = QGridLayout()

        stats_grid.setHorizontalSpacing(
            10
        )

        stats_grid.setVerticalSpacing(
            10
        )

        cards = [
            (
                "CARTAS",
                self._format_number(
                    stats["total_cards"]
                ),
                "quantidade na coleção",
                "collection",
            ),
            (
                "DIFERENTES",
                self._format_number(
                    stats["unique_cards"]
                ),
                "impressões diferentes",
                "unique",
            ),
            (
                "DECKS",
                self._format_number(
                    stats["total_decks"]
                ),
                "decks criados",
                "decks",
            ),
            (
                "VALOR ESTIMADO",
                self._format_money(
                    stats["collection_value"]
                ),
                "valor em USD",
                "value",
            ),
        ]

        for index, data in enumerate(
            cards
        ):

            card = self._create_stat_card(
                *data
            )

            stats_grid.addWidget(
                card,
                0,
                index
            )

            stats_grid.setColumnStretch(
                index,
                1
            )

        self.content_layout.addLayout(
            stats_grid
        )

        # =================================================
        # DISTRIBUIÇÕES
        # =================================================

        distribution_row = QHBoxLayout()

        distribution_row.setSpacing(
            10
        )

        colors_panel = (
            self._create_colors_panel(
                stats["colors"]
            )
        )

        rarities_panel = (
            self._create_rarity_panel(
                stats["rarities"]
            )
        )

        distribution_row.addWidget(
            colors_panel,
            1
        )

        distribution_row.addWidget(
            rarities_panel,
            1
        )

        self.content_layout.addLayout(
            distribution_row
        )

        # =================================================
        # MANA CURVE
        # =================================================

        self.content_layout.addWidget(
            self._create_mana_curve_panel(
                stats["mana_curve"]
            )
        )

        # =================================================
        # EDIÇÕES + RECENTES
        # =================================================

        middle_row = QHBoxLayout()

        middle_row.setSpacing(
            10
        )

        middle_row.addWidget(
            self._create_sets_panel(
                stats["sets"]
            ),
            1
        )

        middle_row.addWidget(
            self._create_recent_panel(
                stats["recent"]
            ),
            1
        )

        self.content_layout.addLayout(
            middle_row
        )

        # =================================================
        # DECKS
        # =================================================

        self.content_layout.addWidget(
            self._create_decks_panel(
                stats
            )
        )

        self.content_layout.addStretch()


    # =====================================================
    # LOAD DATABASE
    # =====================================================

    def _load_statistics(
        self,
    ):

        result = {
            "total_cards": 0,
            "unique_cards": 0,
            "total_decks": 0,
            "deck_cards": 0,
            "collection_value": 0.0,

            "colors": {
                "Branco": 0,
                "Azul": 0,
                "Preto": 0,
                "Vermelho": 0,
                "Verde": 0,
                "Incolor": 0,
                "Multicolor": 0,
            },

            "rarities": {},

            "mana_curve": {
                "0": 0,
                "1": 0,
                "2": 0,
                "3": 0,
                "4": 0,
                "5": 0,
                "6": 0,
                "7+": 0,
            },

            "sets": [],

            "recent": [],

            "deck_list": [],
        }

        connection = None

        try:

            connection = get_connection()

            cursor = connection.cursor()

            # =================================================
            # ESTATÍSTICAS PRINCIPAIS
            # =================================================

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

                    COALESCE(
                        SUM(
                            quantity *
                            COALESCE(
                                price_usd,
                                0
                            )
                        ),
                        0
                    ) AS collection_value

                FROM cards

                WHERE quantity > 0
                """
            )

            row = cursor.fetchone()

            if row:

                result["total_cards"] = int(
                    row["total_cards"]
                    or 0
                )

                result["unique_cards"] = int(
                    row["unique_cards"]
                    or 0
                )

                result["collection_value"] = float(
                    row["collection_value"]
                    or 0
                )

            # =================================================
            # DECKS
            # =================================================

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_decks
                FROM decks
                """
            )

            row = cursor.fetchone()

            if row:

                result["total_decks"] = int(
                    row["total_decks"]
                    or 0
                )

            # =================================================
            # CARTAS NOS DECKS
            # =================================================

            cursor.execute(
                """
                SELECT
                    COALESCE(
                        SUM(quantity),
                        0
                    ) AS total

                FROM deck_cards
                """
            )

            row = cursor.fetchone()

            if row:

                result["deck_cards"] = int(
                    row["total"]
                    or 0
                )

            # =================================================
            # CORES
            # =================================================

            cursor.execute(
                """
                SELECT
                    colors,
                    quantity

                FROM cards

                WHERE quantity > 0
                """
            )

            for row in cursor.fetchall():

                quantity = int(
                    row["quantity"]
                    or 0
                )

                raw_colors = row["colors"]

                parsed_colors = []

                if raw_colors:

                    try:

                        parsed_colors = json.loads(
                            raw_colors
                        )

                    except (
                        TypeError,
                        ValueError,
                        json.JSONDecodeError,
                    ):

                        parsed_colors = []

                if not isinstance(
                    parsed_colors,
                    list
                ):

                    parsed_colors = []

                # -----------------------------------------
                # INCOLOR
                # -----------------------------------------

                if len(
                    parsed_colors
                ) == 0:

                    result["colors"][
                        "Incolor"
                    ] += quantity

                # -----------------------------------------
                # MULTICOLOR
                # -----------------------------------------

                elif len(
                    parsed_colors
                ) > 1:

                    result["colors"][
                        "Multicolor"
                    ] += quantity

                # -----------------------------------------
                # MONOCOLOR
                # -----------------------------------------

                else:

                    symbol = str(
                        parsed_colors[0]
                    ).upper()

                    mapping = {
                        "W": "Branco",
                        "U": "Azul",
                        "B": "Preto",
                        "R": "Vermelho",
                        "G": "Verde",
                    }

                    color_name = mapping.get(
                        symbol,
                        "Incolor"
                    )

                    result["colors"][
                        color_name
                    ] += quantity

            # =================================================
            # RARIDADES
            # =================================================

            cursor.execute(
                """
                SELECT
                    rarity,
                    SUM(quantity) AS total

                FROM cards

                WHERE quantity > 0

                GROUP BY rarity

                ORDER BY
                    total DESC
                """
            )

            for row in cursor.fetchall():

                rarity = (
                    self._rarity_label(
                        row["rarity"]
                    )
                )

                result["rarities"][
                    rarity
                ] = int(
                    row["total"]
                    or 0
                )

            # =================================================
            # CURVA DE MANA
            # =================================================

            cursor.execute(
                """
                SELECT
                    cmc,
                    quantity

                FROM cards

                WHERE quantity > 0
                """
            )

            for row in cursor.fetchall():

                quantity = int(
                    row["quantity"]
                    or 0
                )

                try:

                    cmc = float(
                        row["cmc"]
                        or 0
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    cmc = 0

                if cmc >= 7:

                    key = "7+"

                else:

                    key = str(
                        max(
                            0,
                            int(cmc)
                        )
                    )

                result["mana_curve"][
                    key
                ] += quantity

            # =================================================
            # EDIÇÕES
            # =================================================

            cursor.execute(
                """
                SELECT
                    COALESCE(
                        set_name,
                        'Sem edição'
                    ) AS set_name,

                    SUM(quantity) AS total

                FROM cards

                WHERE quantity > 0

                GROUP BY set_name

                ORDER BY
                    total DESC

                LIMIT 8
                """
            )

            for row in cursor.fetchall():

                result["sets"].append(
                    (
                        str(
                            row["set_name"]
                            or "Sem edição"
                        ),
                        int(
                            row["total"]
                            or 0
                        ),
                    )
                )

            # =================================================
            # CARTAS RECENTES
            # =================================================

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    printed_name,
                    quantity,
                    rarity,
                    image_path,
                    set_name,
                    updated_at

                FROM cards

                WHERE quantity > 0

                ORDER BY
                    updated_at DESC

                LIMIT 5
                """
            )

            for row in cursor.fetchall():

                result["recent"].append(
                    {
                        "id": row["id"],
                        "name": (
                            row["printed_name"]
                            or row["name"]
                            or "Carta"
                        ),
                        "quantity": int(
                            row["quantity"]
                            or 0
                        ),
                        "rarity": self._rarity_label(
                            row["rarity"]
                        ),
                        "image_path": row[
                            "image_path"
                        ],
                        "set_name": (
                            row["set_name"]
                            or ""
                        ),
                        "updated_at": (
                            row["updated_at"]
                            or ""
                        ),
                    }
                )

            # =================================================
            # DECKS
            # =================================================

            cursor.execute(
                """
                SELECT
                    d.id,
                    d.name,
                    d.preview_image_path,

                    COALESCE(
                        SUM(
                            dc.quantity
                        ),
                        0
                    ) AS total_cards

                FROM decks d

                LEFT JOIN deck_cards dc
                    ON dc.deck_id = d.id

                GROUP BY
                    d.id

                ORDER BY
                    d.updated_at DESC,
                    d.id DESC
                """
            )

            for row in cursor.fetchall():

                result["deck_list"].append(
                    {
                        "id": row["id"],
                        "name": (
                            row["name"]
                            or "Deck"
                        ),
                        "preview_image_path": (
                            row[
                                "preview_image_path"
                            ]
                        ),
                        "total_cards": int(
                            row["total_cards"]
                            or 0
                        ),
                    }
                )

        except Exception as error:

            print(
                "[DASHBOARD] Erro ao carregar dados:",
                error,
            )

        finally:

            if connection is not None:

                connection.close()

        return result


    # =====================================================
    # STAT CARD
    # =====================================================

    def _create_stat_card(
        self,
        title,
        value,
        description,
        variant,
    ):

        frame = QFrame()

        frame.setObjectName(
            "DashboardStatCard"
        )

        frame.setMinimumHeight(
            96
        )

        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        frame.setProperty(
            "variant",
            variant
        )

        layout = QVBoxLayout(
            frame
        )

        layout.setContentsMargins(
            17,
            15,
            17,
            15,
        )

        layout.setSpacing(
            4
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "DashboardStatTitle"
        )

        value_label = QLabel(
            value
        )

        value_label.setMinimumHeight(
            30
        )

        value_label.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        value_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        value_label.setObjectName(
            "DashboardStatValue"
        )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "DashboardStatDescription"
        )

        layout.addWidget(
            title_label
        )

        layout.addWidget(
            value_label
        )

        layout.addWidget(
            description_label
        )

        return frame


    # =====================================================
    # COLORS
    # =====================================================

    def _create_colors_panel(
            self,
            values,
    ):

        panel = self._create_panel(
            "Distribuição por cor",
            "Cartas da coleção por identidade de cor."
        )

        layout = panel.layout()

        total = sum(
            values.values()
        )

        color_objects = {
            "Branco": "White",
            "Azul": "Blue",
            "Preto": "Black",
            "Vermelho": "Red",
            "Verde": "Green",
            "Incolor": "Colorless",
            "Multicolor": "Multi",
        }

        mana_symbols = {
            "Branco": "{W}",
            "Azul": "{U}",
            "Preto": "{B}",
            "Vermelho": "{R}",
            "Verde": "{G}",
            "Incolor": "{C}",
        }

        for name, value in values.items():

            row = QHBoxLayout()

            row.setSpacing(
                9
            )

            # =================================================
            # SÍMBOLO DE MANA
            # =================================================

            if name in mana_symbols:

                mana_symbol = ManaSymbolsWidget(
                    mana_symbols[name],
                    symbol_size=22
                )

                mana_symbol.setObjectName(
                    "DashboardManaSymbol"
                )

                mana_symbol.setProperty(
                    "color",
                    color_objects.get(
                        name,
                        "Colorless"
                    )
                )

                mana_symbol.setFixedSize(
                    22,
                    22
                )

            else:

                mana_symbol = QLabel(
                    "✦"
                )

                mana_symbol.setObjectName(
                    "DashboardManaSymbol"
                )

                mana_symbol.setProperty(
                    "color",
                    "Multi"
                )

                mana_symbol.setFixedSize(
                    22,
                    22
                )

                mana_symbol.setAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

            # =================================================
            # NOME
            # =================================================

            label = QLabel(
                name
            )

            label.setObjectName(
                "DashboardRowLabel"
            )

            label.setFixedWidth(
                82
            )

            # =================================================
            # BARRA
            # =================================================

            bar = QProgressBar()

            bar.setObjectName(
                "DashboardColorBar"
            )

            bar.setProperty(
                "color",
                color_objects.get(
                    name,
                    "Colorless"
                )
            )

            bar.setRange(
                0,
                max(
                    total,
                    1
                )
            )

            bar.setValue(
                value
            )

            bar.setTextVisible(
                False
            )

            bar.setFixedHeight(
                8
            )

            # =================================================
            # QUANTIDADE
            # =================================================

            count = QLabel(
                self._format_number(
                    value
                )
            )

            count.setObjectName(
                "DashboardRowValue"
            )

            count.setFixedWidth(
                42
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            # =================================================
            # LINHA
            # =================================================

            row.addWidget(
                mana_symbol
            )

            row.addWidget(
                label
            )

            row.addWidget(
                bar,
                1
            )

            row.addWidget(
                count
            )

            layout.addLayout(
                row
            )

        layout.addStretch()

        return panel

    # =====================================================
    # RARITIES
    # =====================================================

    def _create_rarity_panel(
        self,
        values,
    ):

        panel = self._create_panel(
            "Raridades",
            "Distribuição das cartas por raridade."
        )

        layout = panel.layout()

        ordered = [
            "Comum",
            "Incomum",
            "Rara",
            "Mítica",
            "Sem raridade",
        ]

        data = []

        for name in ordered:

            value = values.get(
                name,
                0
            )

            if value > 0:

                data.append(
                    (
                        name,
                        value
                    )
                )

        # ---------------------------------------------
        # Caso existam raridades não previstas
        # ---------------------------------------------

        known = set(
            ordered
        )

        for name, value in values.items():

            if (
                name not in known
                and value > 0
            ):

                data.append(
                    (
                        name,
                        value
                    )
                )

        total = sum(
            value
            for _, value in data
        )

        for name, value in data:

            row = QHBoxLayout()

            row.setSpacing(
                10
            )

            label = QLabel(
                name
            )

            label.setObjectName(
                "DashboardRowLabel"
            )

            label.setFixedWidth(
                88
            )

            bar = QProgressBar()

            bar.setObjectName(
                "DashboardRarityBar"
            )

            bar.setProperty(
                "rarity",
                name
            )

            bar.setRange(
                0,
                max(
                    total,
                    1
                )
            )

            bar.setValue(
                value
            )

            bar.setTextVisible(
                False
            )

            bar.setFixedHeight(
                8
            )

            count = QLabel(
                self._format_number(
                    value
                )
            )

            count.setObjectName(
                "DashboardRowValue"
            )

            count.setFixedWidth(
                42
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            row.addWidget(
                label
            )

            row.addWidget(
                bar,
                1
            )

            row.addWidget(
                count
            )

            layout.addLayout(
                row
            )

        if not data:

            empty = QLabel(
                "Nenhuma carta disponível."
            )

            empty.setObjectName(
                "DashboardMuted"
            )

            layout.addWidget(
                empty
            )

        layout.addStretch()

        return panel




    # =====================================================
    # MANA CURVE
    # =====================================================

    def _create_mana_curve_panel(
            self,
            values,
    ):

        values = {
            mana_value: value
            for mana_value, value in values.items()
            if str(mana_value) != "0"
        }

        panel = self._create_panel(
            "Curva de mana",
            "Distribuição das cartas por valor de mana."
        )

        layout = panel.layout()

        graph = QHBoxLayout()

        graph.setContentsMargins(
            4,
            8,
            4,
            4,
        )

        graph.setSpacing(
            12
        )

        maximum = max(
            values.values()
        ) if values else 1

        maximum = max(
            maximum,
            1
        )

        for mana_value, value in values.items():
            column = QVBoxLayout()

            column.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            column.setSpacing(
                6
            )

            # -------------------------------------------------
            # VALOR
            # -------------------------------------------------

            count = QLabel(
                self._format_number(
                    value
                )
            )

            count.setObjectName(
                "DashboardManaValue"
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            column.addWidget(
                count
            )

            # -------------------------------------------------
            # ÁREA DA BARRA
            # -------------------------------------------------

            track = QFrame()

            track.setObjectName(
                "DashboardManaTrack"
            )

            track.setFixedHeight(
                108
            )

            track.setMinimumWidth(
                34
            )

            track.setMaximumWidth(
                48
            )

            track_layout = QVBoxLayout(
                track
            )

            track_layout.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            track_layout.setSpacing(
                0
            )

            # -------------------------------------------------
            # BARRA PREENCHIDA
            # -------------------------------------------------

            ratio = (
                value / maximum
                if maximum > 0
                else 0
            )

            fill_height = int(
                108 * ratio
            )

            fill_height = max(
                fill_height,
                0
            )

            fill = QFrame()

            fill.setObjectName(
                "DashboardManaFill"
            )

            fill.setFixedHeight(
                fill_height
            )

            track_layout.addStretch()

            track_layout.addWidget(
                fill,
                0,
                Qt.AlignmentFlag.AlignBottom
            )

            column.addWidget(
                track,
                0,
                Qt.AlignmentFlag.AlignHCenter
            )

            # -------------------------------------------------
            # LABEL
            # -------------------------------------------------

            mana_label = QLabel(
                mana_value
            )

            mana_label.setObjectName(
                "DashboardManaLabel"
            )

            mana_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            column.addWidget(
                mana_label
            )

            graph.addLayout(
                column,
                1
            )

        layout.addLayout(
            graph
        )

        return panel

    # =====================================================
    # SETS
    # =====================================================

    # =====================================================
    # SETS
    # =====================================================

    def _create_sets_panel(
            self,
            sets,
    ):

        panel = self._create_panel(
            "Principais edições",
            "Onde estão concentradas as cartas da coleção."
        )

        layout = panel.layout()

        if not sets:
            empty = QLabel(
                "Nenhuma edição disponível."
            )

            empty.setObjectName(
                "DashboardMuted"
            )

            layout.addWidget(
                empty
            )

            return panel

        maximum = max(
            value
            for _, value in sets
        )

        for name, value in sets:
            row = QVBoxLayout()

            row.setSpacing(
                4
            )

            # -------------------------------------------------
            # CABEÇALHO
            # -------------------------------------------------

            header = QHBoxLayout()

            label = QLabel(
                name
            )

            label.setObjectName(
                "DashboardSetName"
            )

            count = QLabel(
                self._format_number(
                    value
                )
            )

            count.setObjectName(
                "DashboardRowValue"
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            header.addWidget(
                label,
                1
            )

            header.addWidget(
                count
            )

            # -------------------------------------------------
            # BARRA
            # -------------------------------------------------

            bar = QProgressBar()

            bar.setObjectName(
                "DashboardSetBar"
            )

            bar.setRange(
                0,
                max(
                    maximum,
                    1
                )
            )

            bar.setValue(
                value
            )

            bar.setTextVisible(
                False
            )

            bar.setFixedHeight(
                5
            )

            # -------------------------------------------------
            # ADICIONAR
            # -------------------------------------------------

            row.addLayout(
                header
            )

            row.addWidget(
                bar
            )

            layout.addLayout(
                row
            )

        layout.addStretch()

        return panel

    # =====================================================
    # RECENT CARDS
    # =====================================================

    def _create_recent_panel(
        self,
        cards,
    ):

        panel = self._create_panel(
            "Cartas atualizadas recentemente",
            "Últimos registros modificados na coleção."
        )

        layout = panel.layout()

        if not cards:

            empty = QLabel(
                "Nenhuma carta disponível."
            )

            empty.setObjectName(
                "DashboardMuted"
            )

            layout.addWidget(
                empty
            )

            return panel

        for card in cards:

            row_frame = QFrame()

            row_frame.setObjectName(
                "DashboardRecentCard"
            )

            row_layout = QHBoxLayout(
                row_frame
            )

            row_layout.setContentsMargins(
                7,
                6,
                8,
                6
            )

            row_layout.setSpacing(
                10
            )

            image = QLabel()

            image.setObjectName(
                "DashboardRecentImage"
            )

            image.setFixedSize(
                42,
                58
            )

            image.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self._set_card_image(
                image,
                card.get(
                    "image_path"
                )
            )

            row_layout.addWidget(
                image
            )

            info = QVBoxLayout()

            info.setSpacing(
                2
            )

            name = QLabel(
                card["name"]
            )

            name.setObjectName(
                "DashboardRecentName"
            )

            name.setWordWrap(
                False
            )

            set_name = QLabel(
                card["set_name"]
                or card["rarity"]
            )

            set_name.setObjectName(
                "DashboardRecentMeta"
            )

            info.addWidget(
                name
            )

            info.addWidget(
                set_name
            )

            row_layout.addLayout(
                info,
                1
            )

            quantity = QLabel(
                f'x{card["quantity"]}'
            )

            quantity.setObjectName(
                "DashboardRecentQuantity"
            )

            quantity.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            row_layout.addWidget(
                quantity
            )

            layout.addWidget(
                row_frame
            )

        layout.addStretch()

        return panel


    # =====================================================
    # DECKS
    # =====================================================

    def _create_decks_panel(
        self,
        stats,
    ):

        frame = QFrame()

        frame.setObjectName(
            "DashboardDeckPanel"
        )

        layout = QVBoxLayout(
            frame
        )

        layout.setContentsMargins(
            18,
            15,
            18,
            15
        )

        layout.setSpacing(
            12
        )

        # =================================================
        # HEADER
        # =================================================

        header = QHBoxLayout()

        title_column = QVBoxLayout()

        title_column.setSpacing(
            2
        )

        title = QLabel(
            "Meus decks"
        )

        title.setObjectName(
            "DashboardPanelTitle"
        )

        subtitle = QLabel(
            f'{stats["total_decks"]} decks · '
            f'{self._format_number(stats["deck_cards"])} '
            f'cartas utilizadas'
        )

        subtitle.setObjectName(
            "DashboardDeckSubtitle"
        )

        title_column.addWidget(
            title
        )

        title_column.addWidget(
            subtitle
        )

        header.addLayout(
            title_column
        )

        header.addStretch()

        layout.addLayout(
            header
        )

        # =================================================
        # DECK LIST
        # =================================================

        decks = stats["deck_list"]

        if not decks:

            empty = QLabel(
                "Você ainda não criou nenhum deck."
            )

            empty.setObjectName(
                "DashboardMuted"
            )

            layout.addWidget(
                empty
            )

            return frame

        deck_row = QHBoxLayout()

        deck_row.setContentsMargins(
            0,
            0,
            0,
            0
        )

        deck_row.setSpacing(
            10
        )

        for deck in decks[:3]:
            card = DashboardDeckCard(
                deck["id"]
            )

            card.setObjectName(
                "DashboardDeckCard"
            )

            card.clicked.connect(
                self.deck_clicked.emit
            )

            card_layout = QHBoxLayout(
                card
            )

            card_layout.setContentsMargins(
                8,
                7,
                10,
                7
            )

            card_layout.setSpacing(
                9
            )

            image = QLabel()

            image.setObjectName(
                "DashboardDeckImage"
            )

            image.setFixedSize(
                48,
                66
            )

            image.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self._set_card_image(
                image,
                deck.get(
                    "preview_image_path"
                )
            )

            card_layout.addWidget(
                image
            )

            info = QVBoxLayout()

            info.setSpacing(
                2
            )

            name = QLabel(
                deck["name"]
            )

            name.setObjectName(
                "DashboardDeckName"
            )

            name.setWordWrap(
                False
            )

            total = QLabel(
                f'{self._format_number(deck["total_cards"])} '
                f'cartas'
            )

            total.setObjectName(
                "DashboardDeckCards"
            )

            info.addWidget(
                name
            )

            info.addWidget(
                total
            )

            card_layout.addLayout(
                info,
                1
            )

            deck_row.addWidget(
                card,
                1
            )

        layout.addLayout(
            deck_row
        )

        return frame


    # =====================================================
    # PANEL BASE
    # =====================================================

    def _create_panel(
        self,
        title,
        subtitle=None,
    ):

        panel = QFrame()

        panel.setObjectName(
            "DashboardPanel"
        )

        layout = QVBoxLayout(
            panel
        )

        layout.setContentsMargins(
            17,
            15,
            17,
            16
        )

        layout.setSpacing(
            10
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "DashboardPanelTitle"
        )

        layout.addWidget(
            title_label
        )

        if subtitle:

            subtitle_label = QLabel(
                subtitle
            )

            subtitle_label.setObjectName(
                "DashboardPanelSubtitle"
            )

            layout.addWidget(
                subtitle_label
            )

        return panel


    # =====================================================
    # IMAGEM
    # =====================================================

    def _set_card_image(
        self,
        label,
        image_path,
    ):

        if not image_path:

            label.setText(
                "◇"
            )

            label.setObjectName(
                "DashboardImageFallback"
            )

            return

        try:

            path = Path(
                str(
                    image_path
                )
            )

            if not path.exists():

                label.setText(
                    "◇"
                )

                return

            pixmap = QPixmap(
                str(path)
            )

            if pixmap.isNull():

                label.setText(
                    "◇"
                )

                return

            pixmap = pixmap.scaled(
                label.width(),
                label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            label.setPixmap(
                pixmap
            )

        except Exception:

            label.setText(
                "◇"
            )


    # =====================================================
    # CLEAR
    # =====================================================

    def _clear_content(
        self,
    ):

        while (
            self.content_layout.count()
        ):

            item = (
                self.content_layout.takeAt(
                    0
                )
            )

            widget = item.widget()

            child_layout = item.layout()

            if widget:

                widget.deleteLater()

            elif child_layout:

                self._clear_layout(
                    child_layout
                )


    def _clear_layout(
        self,
        layout,
    ):

        while layout.count():

            item = layout.takeAt(
                0
            )

            widget = item.widget()

            child_layout = item.layout()

            if widget:

                widget.deleteLater()

            elif child_layout:

                self._clear_layout(
                    child_layout
                )


    # =====================================================
    # FORMAT
    # =====================================================

    @staticmethod
    def _format_number(
        value,
    ):

        return (
            f"{int(value):,}"
            .replace(
                ",",
                "."
            )
        )


    @staticmethod
    def _format_money(
        value,
    ):

        return (
            f"$ {float(value):,.2f}"
            .replace(
                ",",
                "X"
            )
            .replace(
                ".",
                ","
            )
            .replace(
                "X",
                "."
            )
        )


    @staticmethod
    def _rarity_label(
        rarity,
    ):

        value = str(
            rarity
            or ""
        ).strip().casefold()

        mapping = {
            "common": "Comum",
            "uncommon": "Incomum",
            "rare": "Rara",
            "mythic": "Mítica",
            "mythic rare": "Mítica",
            "unknown": "Sem raridade",
            "": "Sem raridade",
        }

        return mapping.get(
            value,
            str(
                rarity
                or "Sem raridade"
            ).capitalize()
        )
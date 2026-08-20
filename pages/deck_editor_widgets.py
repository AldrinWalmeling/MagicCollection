"""
Widgets do editor de decks.

Contém:

    - ``CardBorderOverlay``  → borda de hover pela cor da carta
    - ``ManaCurveWidget``    → curva de mana
    - ``DeckStatsSidebar``   → estatísticas, formato e validação
    - ``DeckFilterBar``      → busca e filtros do deck
"""

from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import (
    QEasingCurve,
    QRectF,
    QSize,
    QTimer,
    QVariantAnimation,
    Qt,
    Signal,
)

from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPen,
    QPixmap,
)

from PySide6.QtSvg import QSvgRenderer

from PySide6.QtCore import QByteArray

from services.deck_formats import (
    card_color_identity,
    format_choices,
    normalize_format,
)

from services.deck_stats import (
    CURVE_BUCKETS,
    GROUP_LABELS,
    TYPE_LABELS,
    TYPE_ORDER,
    card_cmc,
    card_type_key,
    format_usd,
)


# =========================================================
# CORES
# =========================================================

COLOR_HEX = {
    "W": "#f2e6c8",
    "U": "#4a86c8",
    "B": "#6f5f80",
    "R": "#d4574a",
    "G": "#4f9d68",
    "C": "#8b93a3",
}

COLOR_LABELS = {
    "W": "Branco",
    "U": "Azul",
    "B": "Preto",
    "R": "Vermelho",
    "G": "Verde",
    "C": "Incolor",
}

COLOR_ORDER = ("W", "U", "B", "R", "G", "C")


# =========================================================
# ÍCONE DE MANA
# =========================================================

_MANA_SYMBOL_CACHE = {}


def _mana_symbol_pixmap(color, size=22):
    """
    Gera o ícone do símbolo de mana (W/U/B/R/G/C).

    Usa o SVG baixado do Scryfall quando disponível;
    caso contrário desenha um círculo na cor da carta.
    """
    key = (color, size)

    if key in _MANA_SYMBOL_CACHE:
        return _MANA_SYMBOL_CACHE[key]

    from services.scryfall_symbols import load_local_symbol

    pixmap = None

    if color in COLOR_HEX:
        local = load_local_symbol(
            "{" + color + "}"
        )

        if local:

            try:
                renderer = QSvgRenderer(
                    QByteArray(local["data"])
                )

                if renderer.isValid():

                    pm = QPixmap(
                        size,
                        size,
                    )

                    pm.fill(
                        Qt.GlobalColor.transparent
                    )

                    painter = QPainter(pm)

                    renderer.render(painter)

                    painter.end()

                    if not pm.isNull():
                        pixmap = pm

            except Exception:
                pixmap = None

    # -------------------------------------------------
    # FALLBACK: círculo colorido
    # -------------------------------------------------

    if pixmap is None:

        pm = QPixmap(
            size,
            size,
        )

        pm.fill(
            Qt.GlobalColor.transparent
        )

        painter = QPainter(pm)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True
        )

        hex_color = COLOR_HEX.get(
            color,
            "#8b93a3",
        )

        color_q = QColor(hex_color)

        painter.setBrush(color_q)
        painter.setPen(
            QPen(
                QColor("#ffffff"),
                2,
            )
        )

        painter.drawEllipse(
            2,
            2,
            size - 4,
            size - 4,
        )

        painter.end()

        pixmap = pm

    _MANA_SYMBOL_CACHE[key] = pixmap

    return pixmap


def _mana_symbol_icon(color, size=22):
    return QIcon(
        _mana_symbol_pixmap(
            color,
            size,
        )
    )


def identity_colors(card):
    """Lista de cores de identidade da carta (``["C"]`` se incolor)."""

    identity = card_color_identity(card)

    return identity or ["C"]


# =========================================================
# BORDA DE HOVER PELA COR DA CARTA
# =========================================================

class CardBorderOverlay(QWidget):
    """Desenha uma borda colorida sobre a carta durante o hover."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(
            Qt.WidgetAttribute.WA_TransparentForMouseEvents,
            True,
        )

        self.setAttribute(
            Qt.WidgetAttribute.WA_NoSystemBackground,
            True,
        )

        self._colors = [COLOR_HEX["C"]]

        self._progress = 0.0

        self._animation = QVariantAnimation(self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.valueChanged.connect(self._on_animation_value)

    # -----------------------------------------------------

    def set_identity(self, colors):
        colors = [
            COLOR_HEX[color]
            for color in (colors or [])
            if color in COLOR_HEX
        ]

        self._colors = colors or [COLOR_HEX["C"]]

        self.update()

    def set_active(self, active):
        target = 1.0 if active else 0.0

        if abs(target - self._progress) < 0.01:
            return

        self._animation.stop()
        self._animation.setStartValue(float(self._progress))
        self._animation.setEndValue(target)
        self._animation.start()

    def _on_animation_value(self, value):
        self._progress = float(value)
        self.update()

    # -----------------------------------------------------

    def paintEvent(self, event):
        if self._progress <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = 3.0 * self._progress
        half_w = width / 2.0

        rect = QRectF(self.rect()).adjusted(half_w, half_w, -half_w, -half_w)

        if len(self._colors) == 1:
            color = QColor(self._colors[0])
            color.setAlphaF(min(1.0, 0.35 + 0.65 * self._progress))
            pen = QPen(color, width)
        else:
            gradient = QLinearGradient(
                rect.topLeft(),
                rect.bottomRight(),
            )

            steps = max(1, len(self._colors) - 1)

            for index, hex_color in enumerate(self._colors):
                color = QColor(hex_color)
                color.setAlphaF(min(1.0, 0.35 + 0.65 * self._progress))
                gradient.setColorAt(index / steps, color)

            pen = QPen(gradient, width)

        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Borda arredondada suave correspondente aos cantos da carta
        corner_radius = max(6.0, min(12.0, rect.width() * 0.06))
        painter.drawRoundedRect(rect, corner_radius, corner_radius)
        painter.end()


# =========================================================
# CURVA DE MANA
# =========================================================

class ManaCurveWidget(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._counts = [0] * CURVE_BUCKETS

        self.setMinimumHeight(120)

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

    def set_counts(self, counts):
        counts = list(counts or [])

        counts = (counts + [0] * CURVE_BUCKETS)[:CURVE_BUCKETS]

        self._counts = [max(0, int(value or 0)) for value in counts]

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        width = self.width()
        height = self.height()

        label_height = 16
        value_height = 14

        chart_height = max(10, height - label_height - value_height - 4)

        columns = len(self._counts)

        gap = 6

        bar_width = max(
            6,
            (width - gap * (columns - 1)) / columns,
        )

        maximum = max(self._counts) or 1

        painter.setFont(self.font())

        for index, count in enumerate(self._counts):
            x = index * (bar_width + gap)

            bar_height = int(chart_height * (count / maximum)) if count else 2

            y = value_height + (chart_height - bar_height)

            painter.setPen(Qt.PenStyle.NoPen)

            painter.setBrush(QColor("#12161f"))
            painter.drawRoundedRect(
                int(x),
                value_height,
                int(bar_width),
                chart_height,
                4,
                4,
            )

            painter.setBrush(
                QColor("#d4a84b") if count else QColor("#262d3b")
            )

            painter.drawRoundedRect(
                int(x),
                int(y),
                int(bar_width),
                int(bar_height),
                4,
                4,
            )

            painter.setPen(QColor("#eef0f5" if count else "#4a5160"))

            painter.drawText(
                int(x),
                0,
                int(bar_width),
                value_height,
                Qt.AlignmentFlag.AlignCenter,
                str(count),
            )

            painter.setPen(QColor("#7b8394"))

            label = (
                f"{index}+"
                if index == CURVE_BUCKETS - 1
                else str(index)
            )

            painter.drawText(
                int(x),
                height - label_height,
                int(bar_width),
                label_height,
                Qt.AlignmentFlag.AlignCenter,
                label,
            )

        painter.end()


# =========================================================
# CAIXA DE ESTATÍSTICA
# =========================================================

class StatBox(QFrame):

    def __init__(self, label, accent=False, parent=None):
        super().__init__(parent)

        self.setObjectName("StatBox")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(2)

        self.value_label = QLabel("0")
        self.value_label.setObjectName("StatBoxValue")
        self.value_label.setProperty("accent", "true" if accent else "false")
        layout.addWidget(self.value_label)

        self.name_label = QLabel(label.upper())
        self.name_label.setObjectName("StatBoxLabel")
        layout.addWidget(self.name_label)

    def set_value(self, value):
        self.value_label.setText(str(value))


# =========================================================
# SIDEBAR DE ESTATÍSTICAS
# =========================================================

class DeckStatsSidebar(QScrollArea):

    formatChanged = Signal(str)
    favoriteToggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DeckStatsSidebarScroll")
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setFixedWidth(300)

        self.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        container = QWidget()

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 0)
        layout.setSpacing(8)

        # -------------------------------------------------
        # FORMATO
        # -------------------------------------------------

        format_panel = QFrame()
        format_panel.setObjectName("DeckStatsPanel")

        format_layout = QVBoxLayout(format_panel)
        format_layout.setContentsMargins(14, 10, 14, 12)
        format_layout.setSpacing(8)

        format_header = QHBoxLayout()

        format_title = QLabel("Formato")
        format_title.setObjectName("PanelTitle")
        format_header.addWidget(format_title)

        format_header.addStretch()

        self.favorite_button = QPushButton("★")
        self.favorite_button.setObjectName("DeckFavoriteButton")
        self.favorite_button.setCheckable(True)
        self.favorite_button.setToolTip("Marcar deck como favorito")
        self.favorite_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.favorite_button.toggled.connect(self.favoriteToggled.emit)
        format_header.addWidget(self.favorite_button)

        format_layout.addLayout(format_header)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("DeckFormatCombo")

        for key, label in format_choices():
            self.format_combo.addItem(label, key)

        self.format_combo.currentIndexChanged.connect(
            self._on_format_changed
        )

        format_layout.addWidget(self.format_combo)

        self.validation_label = QLabel("Sem regras aplicadas.")
        self.validation_label.setObjectName("DeckValidationLabel")
        self.validation_label.setWordWrap(True)
        self.validation_label.setProperty("state", "neutral")
        format_layout.addWidget(self.validation_label)

        layout.addWidget(format_panel)

        # -------------------------------------------------
        # NÚMEROS
        # -------------------------------------------------

        stats_panel = QFrame()
        stats_panel.setObjectName("DeckStatsPanel")

        stats_layout = QGridLayout(stats_panel)
        stats_layout.setContentsMargins(14, 10, 14, 12)
        stats_layout.setSpacing(8)

        self.total_box = StatBox("Cartas")
        self.unique_box = StatBox("Únicas")
        self.avg_box = StatBox("CMC médio")
        self.value_box = StatBox("Valor", accent=True)

        stats_layout.addWidget(self.total_box, 0, 0)
        stats_layout.addWidget(self.unique_box, 0, 1)
        stats_layout.addWidget(self.avg_box, 1, 0)
        stats_layout.addWidget(self.value_box, 1, 1)

        layout.addWidget(stats_panel)

        # -------------------------------------------------
        # IDENTIDADE DE COR
        # -------------------------------------------------

        colors_panel = QFrame()
        colors_panel.setObjectName("DeckStatsPanel")

        colors_layout = QVBoxLayout(colors_panel)
        colors_layout.setContentsMargins(14, 12, 14, 14)
        colors_layout.setSpacing(8)

        colors_title = QLabel("Identidade de cor")
        colors_title.setObjectName("PanelTitle")
        colors_layout.addWidget(colors_title)

        self.color_row = QHBoxLayout()
        self.color_row.setSpacing(8)
        colors_layout.addLayout(self.color_row)

        self.color_pips = {}

        for color in COLOR_ORDER:
            pip = QLabel("0")
            pip.setObjectName("DeckColorPip")
            pip.setProperty("pip", color.lower())
            pip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pip.setFixedSize(QSize(38, 30))
            pip.setToolTip(COLOR_LABELS[color])
            self.color_row.addWidget(pip)
            self.color_pips[color] = pip

        self.color_row.addStretch()

        layout.addWidget(colors_panel)

        # -------------------------------------------------
        # CURVA DE MANA
        # -------------------------------------------------

        curve_panel = QFrame()
        curve_panel.setObjectName("ManaCurvePanel")

        curve_layout = QVBoxLayout(curve_panel)
        curve_layout.setContentsMargins(14, 12, 14, 14)
        curve_layout.setSpacing(8)

        curve_title = QLabel("Curva de mana")
        curve_title.setObjectName("PanelTitle")
        curve_layout.addWidget(curve_title)

        self.curve_widget = ManaCurveWidget()
        curve_layout.addWidget(self.curve_widget)

        layout.addWidget(curve_panel)

        # -------------------------------------------------
        # TIPOS
        # -------------------------------------------------

        types_panel = QFrame()
        types_panel.setObjectName("DeckTypeBreakdownPanel")

        types_layout = QVBoxLayout(types_panel)
        types_layout.setContentsMargins(14, 12, 14, 14)
        types_layout.setSpacing(6)

        types_title = QLabel("Cartas por tipo")
        types_title.setObjectName("PanelTitle")
        types_layout.addWidget(types_title)

        self.type_labels = {}

        for key in TYPE_ORDER:
            row = QHBoxLayout()

            name = QLabel(TYPE_LABELS[key])
            name.setObjectName("TypeBreakdownName")
            row.addWidget(name)

            row.addStretch()

            value = QLabel("0")
            value.setObjectName("TypeBreakdownValue")
            row.addWidget(value)

            types_layout.addLayout(row)

            self.type_labels[key] = (name, value)

        layout.addWidget(types_panel)

        layout.addStretch()

        self.setWidget(container)

    # -----------------------------------------------------

    def _on_format_changed(self, _index):
        key = self.format_combo.currentData()

        if key:
            self.formatChanged.emit(str(key))

    def set_format(self, format_key):
        key = normalize_format(format_key)

        index = self.format_combo.findData(key)

        if index < 0:
            return

        self.format_combo.blockSignals(True)
        self.format_combo.setCurrentIndex(index)
        self.format_combo.blockSignals(False)

    def set_favorite(self, favorite):
        self.favorite_button.blockSignals(True)
        self.favorite_button.setChecked(bool(favorite))
        self.favorite_button.blockSignals(False)

    # -----------------------------------------------------

    def update_stats(self, stats, cards):
        self.total_box.set_value(stats["total"])
        self.unique_box.set_value(stats["unique"])
        self.value_box.set_value(format_usd(stats["value_usd"]))

        non_land = [
            card
            for card in cards
            if card_type_key(card.get("type_line")) != "land"
            and int(card.get("deck_quantity") or 0) > 0
        ]

        quantity = sum(
            int(card.get("deck_quantity") or 0)
            for card in non_land
        )

        if quantity:
            average = sum(
                card_cmc(card) * int(card.get("deck_quantity") or 0)
                for card in non_land
            ) / quantity
        else:
            average = 0.0

        self.avg_box.set_value(f"{average:.2f}".replace(".", ","))

        self.curve_widget.set_counts(stats["curve"])

        for color, pip in self.color_pips.items():
            count = stats["colors"].get(color, 0)
            pip.setText(str(count))
            pip.setProperty("empty", "true" if not count else "false")
            pip.style().unpolish(pip)
            pip.style().polish(pip)

        for key, (name, value) in self.type_labels.items():
            count = stats["types"].get(key, 0)
            value.setText(str(count))
            name.setEnabled(bool(count))
            value.setEnabled(bool(count))

    def update_validation(self, result):
        problems = list(result.get("errors") or [])

        warnings = list(result.get("warnings") or [])

        if problems:
            state = "error"
            text = "⚠ " + "\n⚠ ".join(problems)

        elif warnings:
            state = "warning"
            text = "• " + "\n• ".join(warnings)

        else:
            state = "ok"
            text = f"Deck válido para {result.get('label', 'o formato')}."

        self.validation_label.setText(text)
        self.validation_label.setProperty("state", state)
        self.validation_label.style().unpolish(self.validation_label)
        self.validation_label.style().polish(self.validation_label)


# =========================================================
# BARRA DE FILTROS DO DECK
# =========================================================

CMC_CHOICES = (
    ("Qualquer custo", None),
    ("0", 0),
    ("1", 1),
    ("2", 2),
    ("3", 3),
    ("4", 4),
    ("5", 5),
    ("6", 6),
    ("7 ou mais", 7),
)


RARITY_CHOICES = (
    ("Todas as raridades", None),
    ("Comum", "common"),
    ("Incomum", "uncommon"),
    ("Rara", "rare"),
    ("Mítica", "mythic"),
)


class DeckFilterBar(QFrame):

    filtersChanged = Signal()
    groupingChanged = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DeckFilterBar")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        self.search_input = QLineEdit()
        self.search_input.setObjectName("DeckFilterSearch")
        self.search_input.setPlaceholderText("Buscar carta no deck...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setMinimumWidth(180)
        layout.addWidget(self.search_input, 1)

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self.filtersChanged.emit)

        self.search_input.textChanged.connect(
            lambda _text: self._search_timer.start()
        )

        self.color_buttons = {}

        for color in COLOR_ORDER:
            button = QPushButton()
            button.setObjectName("DeckColorFilterButton")
            button.setProperty("pip", color.lower())
            button.setCheckable(True)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setToolTip(COLOR_LABELS[color])
            button.setFixedSize(QSize(32, 30))
            button.setIcon(_mana_symbol_icon(color, 20))
            button.setIconSize(QSize(20, 20))
            button.toggled.connect(lambda _c: self.filtersChanged.emit())
            layout.addWidget(button)
            self.color_buttons[color] = button

        self.cmc_combo = QComboBox()
        self.cmc_combo.setObjectName("DeckFilterCombo")

        for label, value in CMC_CHOICES:
            self.cmc_combo.addItem(label, value)

        self.cmc_combo.currentIndexChanged.connect(
            lambda _i: self.filtersChanged.emit()
        )

        layout.addWidget(self.cmc_combo)

        self.type_combo = QComboBox()
        self.type_combo.setObjectName("DeckFilterCombo")
        self.type_combo.addItem("Todos os tipos", None)

        for key in TYPE_ORDER:
            self.type_combo.addItem(TYPE_LABELS[key], key)

        self.type_combo.currentIndexChanged.connect(
            lambda _i: self.filtersChanged.emit()
        )

        layout.addWidget(self.type_combo)

        self.rarity_combo = QComboBox()
        self.rarity_combo.setObjectName("DeckFilterCombo")

        for label, value in RARITY_CHOICES:
            self.rarity_combo.addItem(label, value)

        self.rarity_combo.currentIndexChanged.connect(
            lambda _i: self.filtersChanged.emit()
        )

        layout.addWidget(self.rarity_combo)

        self.group_button = QPushButton("Agrupar por tipo")
        self.group_button.setObjectName("DeckToolbarButton")
        self.group_button.setCheckable(True)
        self.group_button.setChecked(True)
        self.group_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.group_button.toggled.connect(self.groupingChanged.emit)
        layout.addWidget(self.group_button)

        self.clear_button = QPushButton("Limpar")
        self.clear_button.setObjectName("DeckToolbarButton")
        self.clear_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_button.clicked.connect(self.clear_filters)
        layout.addWidget(self.clear_button)

    # -----------------------------------------------------

    @property
    def group_by_type(self):
        return self.group_button.isChecked()

    def selected_colors(self):
        return [
            color
            for color, button in self.color_buttons.items()
            if button.isChecked()
        ]

    def clear_filters(self):
        blocked = []

        for button in self.color_buttons.values():
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)
            blocked.append(button)

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)

        for combo in (self.cmc_combo, self.type_combo, self.rarity_combo):
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

        self.filtersChanged.emit()

    # -----------------------------------------------------

    def matches(self, card):
        text = self.search_input.text().strip().casefold()

        if text:
            haystack = " ".join(
                str(card.get(key) or "")
                for key in (
                    "name",
                    "printed_name",
                    "type_line",
                    "oracle_text",
                )
            ).casefold()

            if text not in haystack:
                return False

        colors = self.selected_colors()

        if colors:
            card_identity = set(identity_colors(card))

            if not card_identity.intersection(colors):
                return False

        cmc = self.cmc_combo.currentData()

        if cmc is not None:
            value = card_cmc(card)

            if cmc == 7:
                if value < 7:
                    return False
            elif value != cmc:
                return False

        type_key = self.type_combo.currentData()

        if type_key and card_type_key(card.get("type_line")) != type_key:
            return False

        rarity = self.rarity_combo.currentData()

        if rarity:
            if str(card.get("rarity") or "").lower() != rarity:
                return False

        return True


# =========================================================
# CABEÇALHO DE GRUPO
# =========================================================

class DeckGroupHeader(QFrame):

    def __init__(self, title, count, parent=None):
        super().__init__(parent)

        self.setObjectName("DeckGroupHeader")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        label = QLabel(title)
        label.setObjectName("DeckGroupTitle")
        layout.addWidget(label)

        badge = QLabel(str(count))
        badge.setObjectName("DeckGroupCount")
        layout.addWidget(badge)

        layout.addStretch()


def group_label(key):
    return GROUP_LABELS.get(key, TYPE_LABELS.get(key, key))
import json
from pathlib import Path

from PySide6.QtCore import (
    Qt,
    Signal,
    QObject,
    QEvent,
    QSettings,
    QRect,
)
from PySide6.QtGui import (
    QPixmap,
    QPainter,
    QColor,
    QPen,
    QFont,
    QAction,
    QActionGroup,
)
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QMenu,
    QButtonGroup,
)

from database import get_connection
from services.scryfall_symbols import ManaSymbolsWidget
from pages.decks_widgets import _format_brl
from components.card_details_dialog import (
    CACHED_USD_BRL,
)
from services.currency_service import (
    CurrencyService,
    CURRENCY_SYMBOLS,
)
from services.price_reference import (
    get_pricing_mode,
    set_pricing_mode,
    pricing_mode_label,
    price_column_expression,
    PRICING_MODE_ORIGINAL,
    PRICING_MODE_IMPRINT,
)

# =========================================================
# CORES DE MANA (pips do painel de decks)
# =========================================================

DECK_COLOR_HEX = {
    "W": "#f2e6c8",
    "U": "#4a86c8",
    "B": "#6f5f80",
    "R": "#d4574a",
    "G": "#4f9d68",
}

# =========================================================
# CORES DOS DONUTS (distribuição por cor)
# =========================================================
#
# Cores suaves que combinam com o tema dark.
# Nada de neon / cores extremamente saturadas.

DONUT_COLOR_HEX = {
    "Branco": "#cbbfa1",
    "Azul": "#4a86c8",
    "Preto": "#6f5f80",
    "Vermelho": "#c45a4c",
    "Verde": "#4f9d68",
    "Incolor": "#8a94a6",
    "Multicolor": "#d4a84b",
}

# =========================================================
# CORES DOS DONUTS (raridades)
# =========================================================

RARITY_DONUT_HEX = {
    "Comum": "#6b7c93",
    "Incomum": "#4a86c8",
    "Rara": "#d4a84b",
    "Mítica": "#c0453e",
    "Sem raridade": "#343b49",
}

# =========================================================
# GRÁFICO DE PIZZA / DONUT (QPainter)
# =========================================================

class DonutChart(QWidget):
    """
    Gráfico de donut desenhado com QPainter.

    Recebe uma lista de segmentos:

        (label, value, hex_color)

    O centro exibe um resumo (valor + legenda curta).

    O gráfico é sempre desenhado como um círculo completo.
    As proporções dos segmentos representam exatamente os
    valores recebidos.
    """

    def __init__(
        self,
        center_value="",
        center_caption="",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "dashboardDonut"
        )

        # -------------------------------------------------
        # DADOS
        # -------------------------------------------------

        self._data = []

        # -------------------------------------------------
        # PROGRESSO
        #
        # Mantemos a propriedade para compatibilidade com
        # o código existente do Dashboard.
        #
        # Porém o donut não depende dela para ficar completo.
        # -------------------------------------------------

        self._progress = 1.0

        self._animation = None

        # -------------------------------------------------
        # TEXTO CENTRAL
        # -------------------------------------------------

        self._center_value = str(
            center_value
        )

        self._center_caption = str(
            center_caption
        )

        # -------------------------------------------------
        # TAMANHO
        # -------------------------------------------------

        self.setMinimumSize(
            120,
            120,
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

    # =====================================================
    # DADOS
    # =====================================================

    def set_data(
        self,
        data,
    ):
        """
        data: lista de

            (label, value, hex_color)

        Os valores são usados diretamente para calcular
        a proporção de cada segmento.
        """

        self._data = list(
            data
            or []
        )

        # -------------------------------------------------
        # SEMPRE COMEÇAR COMPLETO
        # -------------------------------------------------

        self._progress = 1.0

        # -------------------------------------------------
        # CANCELAR EVENTUAL ANIMAÇÃO ANTERIOR
        # -------------------------------------------------

        if self._animation is not None:

            try:

                self._animation.stop()

            except RuntimeError:

                pass

            self._animation = None

        self.update()

    # =====================================================
    # CENTRO
    # =====================================================

    def set_center(
        self,
        value,
        caption,
    ):

        self._center_value = str(
            value
        )

        self._center_caption = str(
            caption
        )

        self.update()

    # =====================================================
    # ANIMAÇÃO
    # =====================================================

    def animate(
        self,
        duration=720,
        delay=0,
    ):
        """
        Mantém compatibilidade com o Dashboard.

        O donut não usa mais animação de preenchimento,
        pois isso fazia o gráfico aparecer parcialmente
        durante a entrada da página.

        O gráfico é colocado imediatamente em 100%.
        """

        from PySide6.QtCore import (
            QTimer,
        )

        # -------------------------------------------------
        # PARAR ANIMAÇÃO ANTERIOR
        # -------------------------------------------------

        if self._animation is not None:

            try:

                self._animation.stop()

            except RuntimeError:

                pass

            self._animation = None

        # -------------------------------------------------
        # SEMPRE COMPLETO
        # -------------------------------------------------

        self._progress = 1.0

        # -------------------------------------------------
        # ATUALIZAR DEPOIS DO EVENT LOOP
        #
        # O delay é mantido apenas para compatibilidade
        # com quem chama animate(delay=...).
        # -------------------------------------------------

        def _finish(
            chart=self,
        ):

            try:

                chart._progress = 1.0
                chart.update()

            except RuntimeError:

                pass

        QTimer.singleShot(
            max(
                int(delay),
                0,
            ),
            _finish,
        )

        # -------------------------------------------------
        # RETORNAR NONE É SEGURO PARA O CÓDIGO ATUAL?
        #
        # Não. O Dashboard guarda o retorno em uma lista.
        #
        # Então criamos um pequeno objeto compatível.
        # -------------------------------------------------

        class _ImmediateAnimation:
            """
            Objeto mínimo compatível com o uso atual
            do Dashboard.

            Não executa animação visual.
            """

            def stop(
                self,
            ):
                pass

        animation = _ImmediateAnimation()

        self._animation = animation

        return animation

    # =====================================================
    # TAMANHO
    # =====================================================

    def sizeHint(
        self,
    ):

        return self.minimumSize()

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

        self.update()

    # =====================================================
    # PAINT
    # =====================================================

    def paintEvent(
        self,
        event,
    ):

        painter = QPainter(
            self
        )

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing,
            True,
        )

        rect = self.rect()

        # -------------------------------------------------
        # TAMANHO DO DONUT
        # -------------------------------------------------

        side = min(
            rect.width(),
            rect.height(),
        )

        donut_rect = QRect(
            0,
            0,
            side,
            side,
        )

        donut_rect.moveCenter(
            rect.center()
        )

        donut_rect.adjust(
            2,
            2,
            -2,
            -2,
        )

        # -------------------------------------------------
        # TOTAL
        # -------------------------------------------------

        total = sum(
            value
            for _, value, _ in self._data
            if value is not None
            and value > 0
        )

        # =================================================
        # SEM DADOS
        # =================================================

        if (
            total <= 0
            or not self._data
        ):

            painter.setPen(
                Qt.PenStyle.NoPen
            )

            painter.setBrush(
                QColor(
                    "#232a37"
                )
            )

            painter.drawEllipse(
                donut_rect
            )

            painter.setPen(
                QPen(
                    QColor(
                        "#8b93a3"
                    )
                )
            )

            painter.drawText(
                donut_rect,
                Qt.AlignmentFlag.AlignCenter,
                "—",
            )

            return

        # =================================================
        # SEGMENTOS
        # =================================================

        # -------------------------------------------------
        # Círculo completo:
        #
        # Qt usa 1/16 de grau.
        #
        # 360 * 16 = 5760
        # -------------------------------------------------

        full_circle = (
            360 * 16
        )

        start_angle = (
            90 * 16
        )

        # -------------------------------------------------
        # PROGRESSO
        #
        # Mantido por compatibilidade.
        #
        # Na prática esta classe trabalha sempre com 1.0.
        # -------------------------------------------------

        progress = max(
            0.0,
            min(
                float(
                    self._progress
                ),
                1.0,
            ),
        )

        # -------------------------------------------------
        # CALCULAR SPANS
        #
        # NÃO existe mais min_span.
        #
        # Cada segmento recebe exatamente sua proporção.
        # -------------------------------------------------

        spans = []

        for (
            _,
            value,
            _,
        ) in self._data:

            if (
                value is None
                or value <= 0
            ):

                spans.append(
                    0
                )

                continue

            span = int(
                round(
                    (
                        float(value)
                        / float(total)
                    )
                    * full_circle
                    * progress
                )
            )

            spans.append(
                max(
                    0,
                    span,
                )
            )

        # -------------------------------------------------
        # GARANTIR QUE O DONUT TERMINE EXATAMENTE EM
        # 360 GRAUS
        #
        # Arredondamentos de inteiros podem fazer a soma
        # ficar em 5759 ou 5761.
        #
        # Quando estamos em 100%, corrigimos a diferença
        # no último segmento válido.
        # -------------------------------------------------

        if (
            progress >= 1.0
            and spans
        ):

            total_span = sum(
                spans
            )

            difference = (
                full_circle
                - total_span
            )

            if difference != 0:

                last_valid_index = None

                for index in range(
                    len(spans) - 1,
                    -1,
                    -1,
                ):

                    if spans[index] > 0:

                        last_valid_index = (
                            index
                        )

                        break

                if (
                    last_valid_index
                    is not None
                ):

                    spans[
                        last_valid_index
                    ] += difference

        # =================================================
        # DESENHAR SEGMENTOS
        # =================================================

        for (
            index,
            (
                _,
                _,
                color,
            ),
        ) in enumerate(
            self._data
        ):

            if index >= len(
                spans
            ):

                break

            span = spans[
                index
            ]

            if span <= 0:

                continue

            painter.setPen(
                Qt.PenStyle.NoPen
            )

            painter.setBrush(
                QColor(
                    color
                )
            )

            painter.drawPie(
                donut_rect,
                start_angle,
                span,
            )

            start_angle -= span

        # =================================================
        # BURACO CENTRAL
        # =================================================

        hole_side = max(
            10,
            int(
                donut_rect.width()
                * 0.56
            ),
        )

        hole_rect = QRect(
            0,
            0,
            hole_side,
            hole_side,
        )

        hole_rect.moveCenter(
            donut_rect.center()
        )

        painter.setPen(
            Qt.PenStyle.NoPen
        )

        painter.setBrush(
            QColor(
                "#181c25"
            )
        )

        painter.drawEllipse(
            hole_rect
        )

        # =================================================
        # VALOR CENTRAL
        # =================================================

        value_font = QFont()

        value_font.setPixelSize(
            max(
                13,
                int(
                    hole_rect.width()
                    * 0.16
                ),
            )
        )

        value_font.setBold(
            True
        )

        painter.setFont(
            value_font
        )

        painter.setPen(
            QColor(
                "#E8E9EC"
            )
        )

        value_rect = QRect(
            hole_rect
        )

        value_rect.adjust(
            0,
            0,
            0,
            -int(
                hole_rect.height()
                * 0.10
            ),
        )

        painter.drawText(
            value_rect,
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignBottom,
            self._center_value,
        )

        # =================================================
        # LEGENDA CENTRAL
        # =================================================

        caption_font = QFont()

        caption_font.setPixelSize(
            max(
                8,
                int(
                    hole_rect.width()
                    * 0.09
                ),
            )
        )

        painter.setFont(
            caption_font
        )

        painter.setPen(
            QColor(
                "#8b93a3"
            )
        )

        caption_rect = QRect(
            hole_rect
        )

        caption_rect.adjust(
            0,
            int(
                hole_rect.height()
                * 0.10
            ),
            0,
            0,
        )

        painter.drawText(
            caption_rect,
            Qt.AlignmentFlag.AlignHCenter
            | Qt.AlignmentFlag.AlignTop,
            self._center_caption,
        )

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
# CLIQUE NAS CARTAS MAIS VALIOSAS
# =========================================================

class _CardClickFilter(QObject):

    def __init__(
        self,
        card_data,
        on_click,
        parent=None,
    ):
        super().__init__(parent)

        self._card_data = card_data

        self._on_click = on_click

    def eventFilter(
        self,
        obj,
        event,
    ):

        if (
            event.type()
            == QEvent.Type.MouseButtonPress
            and event.button()
            == Qt.MouseButton.LeftButton
        ):

            try:

                self._on_click(
                    self._card_data
                )

            except (
                RuntimeError,
                TypeError,
            ):

                pass

            return True

        return super().eventFilter(
            obj,
            event
        )


# =========================================================
# RANKING DAS CARTAS MAIS VALIOSAS
# =========================================================

class _ValuableNameLabel(QLabel):

    def __init__(
        self,
        full_text,
        parent=None,
    ):
        super().__init__(parent)

        self._full_text = full_text

        self.setText(
            full_text
        )

        self.setWordWrap(
            False
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Preferred,
        )

    def resizeEvent(
        self,
        event,
    ):

        super().resizeEvent(
            event
        )

        try:

            fm = self.fontMetrics()

            self.setText(
                fm.elidedText(
                    self._full_text,
                    Qt.TextElideMode.ElideRight,
                    self.width(),
                )
            )

        except RuntimeError:

            pass


class ValuableCardsWidget(QFrame):

    row_clicked = Signal(object)

    view_all_clicked = Signal()

    MODE_COLLECTION = "collection"

    MODE_INDIVIDUAL = "individual"

    def __init__(
        self,
        cards,
        currency="BRL",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(
            "valuableCardsCard"
        )

        self._cards = list(
            cards
        )

        self._currency = (
            str(
                currency
                or "BRL"
            ).upper()
        )

        self._mode = (
            self.MODE_COLLECTION
        )

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            14,
            15,
            14,
            12
        )

        layout.setSpacing(
            8
        )

        # ---------------------------------------------
        # CABEÇALHO — TÍTULO + ALTERNÂNCIA DE MODO
        # ---------------------------------------------

        header = QHBoxLayout()

        header.setSpacing(
            8
        )

        title = QLabel(
            "Top 6 cartas mais valiosas"
        )

        title.setObjectName(
            "valuableCardsTitle"
        )

        header.addWidget(
            title,
            1
        )

        self._mode_group = QButtonGroup(
            self
        )

        self._mode_group.setExclusive(
            True
        )

        self._individual_button = QPushButton(
            "Individual"
        )

        self._individual_button.setObjectName(
            "valuableCardModeButton"
        )

        self._individual_button.setCheckable(
            True
        )

        self._individual_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self._individual_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self._collection_button = QPushButton(
            "Coleção"
        )

        self._collection_button.setObjectName(
            "valuableCardModeButton"
        )

        self._collection_button.setCheckable(
            True
        )

        self._collection_button.setChecked(
            True
        )

        self._collection_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self._collection_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        self._mode_group.addButton(
            self._individual_button
        )

        self._mode_group.addButton(
            self._collection_button
        )

        self._individual_button.clicked.connect(
            lambda: self._set_mode(
                self.MODE_INDIVIDUAL
            )
        )

        self._collection_button.clicked.connect(
            lambda: self._set_mode(
                self.MODE_COLLECTION
            )
        )

        header.addWidget(
            self._individual_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        header.addWidget(
            self._collection_button,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        layout.addLayout(
            header
        )

        self._subtitle = QLabel(
            "Valor de 1 unidade de cada carta."
        )

        self._subtitle.setObjectName(
            "valuableCardsSubtitle"
        )

        self._subtitle.setWordWrap(
            True
        )

        layout.addWidget(
            self._subtitle
        )

        self._rows_layout = QVBoxLayout()

        self._rows_layout.setSpacing(
            5
        )

        layout.addLayout(
            self._rows_layout
        )

        self._empty_label = QLabel(
            "Nenhuma carta com valor disponível."
        )

        self._empty_label.setObjectName(
            "valuableCardsEmpty"
        )

        self._empty_label.setVisible(
            False
        )

        layout.addWidget(
            self._empty_label
        )

        layout.addStretch(
            1
        )

        view_all = QPushButton(
            "Ver todas as cartas →"
        )

        view_all.setObjectName(
            "valuableCardsViewAll"
        )

        view_all.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        view_all.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        view_all.clicked.connect(
            self.view_all_clicked.emit
        )

        button_row = QHBoxLayout()

        button_row.addStretch(
            1
        )

        button_row.addWidget(
            view_all
        )

        button_row.addStretch(
            1
        )

        layout.addLayout(
            button_row
        )

        self._rebuild_rows()

    def _refresh_card_images(
            self,
    ):
        """
        Recalcula as imagens do Top 6 depois que o layout
        inicial do Qt terminou de ser calculado.

        Isso evita depender do hover para corrigir a
        primeira renderização.
        """

        try:

            self.layout().activate()

            for image in self.findChildren(
                    QLabel
            ):

                if image.objectName() != (
                        "valuableCardImage"
                ):
                    continue

                path = image.property(
                    "dashboard_image_path"
                )

                if not path:
                    continue

                self._load_image(
                    image,
                    path,
                )

        except RuntimeError:
            pass



    def _set_mode(
        self,
        mode,
    ):

        if mode not in (
            self.MODE_COLLECTION,
            self.MODE_INDIVIDUAL,
        ):
            return

        if mode == self._mode:
            return

        self._mode = mode

        self._collection_button.setChecked(
            mode == self.MODE_COLLECTION
        )

        self._individual_button.setChecked(
            mode == self.MODE_INDIVIDUAL
        )

        self._rebuild_rows()

    def _rebuild_rows(
        self,
    ):

        while (
            self._rows_layout.count()
        ):

            item = (
                self._rows_layout.takeAt(
                    0
                )
            )

            widget = item.widget()

            if widget is not None:

                widget.deleteLater()

        if not self._cards:

            self._empty_label.setVisible(
                True
            )

            return

        self._empty_label.setVisible(
            False
        )

        individual = (
            self._mode
            == self.MODE_INDIVIDUAL
        )

        self._subtitle.setText(
            (
                "Valor de 1 unidade de cada carta."
                if individual
                else (
                    "Valor total considerando a "
                    "quantidade de cada carta."
                )
            )
        )

        rows = []

        for card in self._cards:

            row = self._build_row(
                card
            )

            self._rows_layout.addWidget(
                row
            )

            rows.append(
                row
            )

        self._fade_in_rows(
            rows
        )

        # -------------------------------------------------
        # CORREÇÃO DO PRIMEIRO LAYOUT DAS IMAGENS
        #
        # O layout pode ainda não ter terminado de calcular
        # os tamanhos quando _build_row() carrega o pixmap.
        #
        # O hover atualmente acaba forçando esse recálculo
        # indiretamente. Fazemos isso automaticamente aqui.
        # -------------------------------------------------

        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            0,
            self._refresh_card_images,
        )

    def _fade_in_rows(
        self,
        rows,
    ):

        from PySide6.QtCore import (
            QPropertyAnimation,
            QEasingCurve,
            QTimer,
        )

        from PySide6.QtWidgets import (
            QGraphicsOpacityEffect,
        )

        for index, row in enumerate(
            rows
        ):

            effect = QGraphicsOpacityEffect(
                row
            )

            row.setGraphicsEffect(
                effect
            )

            effect.setOpacity(
                0.0
            )

            animation = QPropertyAnimation(
                effect,
                b"opacity",
                row,
            )

            animation.setStartValue(
                0.0
            )

            animation.setEndValue(
                1.0
            )

            animation.setDuration(
                360
            )

            animation.setEasingCurve(
                QEasingCurve.OutCubic
            )

            def _start(
                animation=animation,
            ):

                try:

                    animation.start()

                except RuntimeError:

                    pass

            QTimer.singleShot(
                80 + index * 110,
                _start,
            )

    def _build_row(
        self,
        card,
    ):

        row = QFrame()

        row.setObjectName(
            "valuableCardRow"
        )

        row.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        row.installEventFilter(
            _CardClickFilter(
                card,
                self.row_clicked.emit,
                self,
            )
        )

        row_layout = QHBoxLayout(
            row
        )

        row_layout.setContentsMargins(
            6,
            5,
            6,
            5
        )

        row_layout.setSpacing(
            6
        )

        rank = QLabel(
            str(
                self._cards.index(
                    card
                ) + 1
            )
        )

        rank.setObjectName(
            "valuableCardRank"
        )

        rank.setFixedSize(
            22,
            22
        )

        rank.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        row_layout.addWidget(
            rank,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        image = QLabel()

        image.setObjectName(
            "valuableCardImage"
        )

        image.setFixedSize(
            40,
            56
        )

        image.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        image.setProperty(
            "dashboard_image_path",
            card.get("image_path"),
        )

        self._load_image(
            image,
            card.get("image_path"),
        )

        row_layout.addWidget(
            image,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        name = _ValuableNameLabel(
            card.get("name") or "Carta"
        )

        name.setObjectName(
            "valuableCardName"
        )

        row_layout.addWidget(
            name,
            1,
        )

        rarity = QLabel(
            card.get("rarity") or "Sem raridade"
        )

        rarity.setObjectName(
            "valuableCardRarity"
        )

        rarity.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        rarity.setFixedWidth(
            56
        )

        row_layout.addWidget(
            rarity,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        individual = (
            self._mode
            == self.MODE_INDIVIDUAL
        )

        if not individual:

            quantity = QLabel(
                f'x{card.get("quantity") or 0}'
            )

            quantity.setObjectName(
                "valuableCardQuantity"
            )

            quantity.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            quantity.setFixedWidth(
                28
            )

            row_layout.addWidget(
                quantity,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        price = QLabel(
            self._format_value(
                card.get("price") or 0,
                card.get("price_eur"),
                card.get("price_tix"),
            )
        )

        price.setObjectName(
            "valuableCardPrice"
        )

        price.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        price.setFixedWidth(
            60
        )

        row_layout.addWidget(
            price,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        if not individual:

            total = QLabel(
                self._format_value(
                    card.get("total_value") or 0,
                    card.get("total_eur"),
                    card.get("total_tix"),
                )
            )

            total.setObjectName(
                "valuableCardTotal"
            )

            total.setAlignment(
                Qt.AlignmentFlag.AlignRight
                | Qt.AlignmentFlag.AlignVCenter
            )

            total.setFixedWidth(
                62
            )

            row_layout.addWidget(
                total,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        return row

    def _format_brl(
        self,
        value,
    ):

        try:

            return _format_brl(
                float(value) * self._usd_brl
            )

        except (TypeError, ValueError):

            return "N/D"

    def _format_value(
        self,
        price_usd,
        price_eur=None,
        price_tix=None,
    ):

        try:

            price_usd = float(
                price_usd
                or 0
            )

        except (
            TypeError,
            ValueError,
        ):

            price_usd = 0.0

        currency = self._currency

        if (
            currency == "EUR"
            and price_eur is not None
        ):

            try:

                return CurrencyService.format_value(
                    float(price_eur),
                    "EUR",
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

        if (
            currency == "TIX"
            and price_tix is not None
        ):

            try:

                return CurrencyService.format_value(
                    float(price_tix),
                    "TIX",
                )

            except (
                TypeError,
                ValueError,
            ):

                pass

        converted = CurrencyService.convert_usd(
            price_usd,
            currency,
        )

        return CurrencyService.format_value(
            converted,
            currency,
        )

    def _load_image(
        self,
        label,
        image_path,
    ):

        if not image_path:

            label.setText(
                "◇"
            )

            return

        try:

            path = Path(
                str(image_path)
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

            scaled = pixmap.scaled(
                label.width(),
                label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            label.setPixmap(
                scaled
            )

        except Exception:

            label.setText(
                "◇"
            )


# =========================================================
# ZOOM SUAVE NO HOVER DAS IMAGENS
# =========================================================

class _HoverZoomFilter(QObject):

    def __init__(
        self,
        label,
    ):
        super().__init__(label)

        self._label = label

        self._source = None

        self._base_w = label.width()

        self._base_h = label.height()

        self._anim = None

        pixmap = label.pixmap()

        if (
            pixmap is not None
            and not pixmap.isNull()
        ):

            self._source = pixmap

    def eventFilter(
        self,
        obj,
        event,
    ):

        event_type = event.type()

        if (
            event_type
            == QEvent.Type.Enter
        ):

            self._animate(1.07)

        elif (
            event_type
            == QEvent.Type.Leave
        ):

            self._animate(1.0)

        return super().eventFilter(
            obj,
            event,
        )

    def _animate(
        self,
        factor,
    ):

        if (
            self._source is None
            or self._base_w <= 0
            or self._base_h <= 0
        ):
            return

        from PySide6.QtCore import (
            QVariantAnimation,
            QEasingCurve,
        )

        if self._anim is not None:

            self._anim.stop()

        animation = QVariantAnimation(
            self
        )

        animation.setDuration(
            180
        )

        animation.setStartValue(
            1.0
        )

        animation.setEndValue(
            factor
        )

        animation.setEasingCurve(
            QEasingCurve.OutCubic
        )

        animation.valueChanged.connect(
            self._apply
        )

        self._anim = animation

        animation.start()

    def _apply(
        self,
        scale,
    ):

        if self._source is None:
            return

        try:

            scaled = self._source.scaled(
                max(
                    1,
                    int(
                        self._base_w * scale
                    ),
                ),
                max(
                    1,
                    int(
                        self._base_h * scale
                    ),
                ),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self._label.setPixmap(
                scaled
            )

        except RuntimeError:
            pass


# =========================================================
# DASHBOARD
# =========================================================

class DashboardPage(QWidget):

    deck_clicked = Signal(int)

    card_clicked = Signal(object)

    view_all_cards = Signal()

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

        # ---------------------------------------------
        # CARD DE VALOR ESTIMADO (com seletor de moeda)
        # ---------------------------------------------

        currency = stats.get(
            "currency",
            "BRL",
        )

        value_amount = CurrencyService.format_value(
            stats["collection_value"],
            currency,
        )

        secondary_target = (
            CurrencyService.secondary_currency(
                currency
            )
        )

        if secondary_target == "USD":

            secondary_value = (
                stats["collection_value_usd"]
            )

        else:

            secondary_value = (
                CurrencyService.convert_usd(
                    stats["collection_value_usd"],
                    secondary_target,
                )
            )

        secondary = CurrencyService.format_value(
            secondary_value,
            secondary_target,
        )

        value_card = self._create_stat_card(
            "VALOR ESTIMADO",
            value_amount,
            "valor estimado da coleção",
            "value",
            secondary=secondary,
            right_widget=self._build_currency_button(
                currency
            ),
        )

        stats_grid.addWidget(
            value_card,
            0,
            3
        )

        stats_grid.setColumnStretch(
            3,
            1
        )

        self.content_layout.addLayout(
            stats_grid
        )

        # =================================================
        # BARRA DISCRETA — REFERÊNCIA DE PREÇOS
        # =================================================

        self.content_layout.addWidget(
            self._create_pricing_bar(
                get_pricing_mode()
            )
        )

        # =================================================
        # ÁREA PRINCIPAL — TOP 3 + DISTRIBUIÇÕES + MANA
        # =================================================

        main_row = QHBoxLayout()

        main_row.setSpacing(
            10
        )

        # -----------------------------------------
        # COLUNA ESQUERDA — CARTAS MAIS VALIOSAS
        # (ocupa toda a altura da área principal)
        # -----------------------------------------

        left_col = QVBoxLayout()

        left_col.setSpacing(
            0
        )

        top_cards_panel = (
            self._create_top_cards_panel(
                stats["top_cards"]
            )
        )

        left_col.addWidget(
            top_cards_panel,
            1
        )

        main_row.addLayout(
            left_col,
            2
        )

        # -----------------------------------------
        # COLUNA DIREITA — DISTRIBUIÇÕES + MANA
        # -----------------------------------------

        right_col = QVBoxLayout()

        right_col.setSpacing(
            10
        )

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

        colors_panel.setObjectName(
            "DashboardDistributionPanel"
        )

        colors_panel.setProperty(
            "panel_name",
            "colors",
        )

        rarities_panel.setObjectName(
            "DashboardDistributionPanel"
        )

        rarities_panel.setProperty(
            "panel_name",
            "rarities",
        )

        distribution_row.addWidget(
            colors_panel,
            1
        )

        distribution_row.addWidget(
            rarities_panel,
            1
        )

        right_col.addLayout(
            distribution_row,
            2
        )

        types_panel = (
            self._create_types_panel(
                stats["types"]
            )
        )

        types_panel.setObjectName(
            "DashboardDistributionPanel"
        )

        types_panel.setProperty(
            "panel_name",
            "types",
        )

        mana_curve_panel = (
            self._create_mana_curve_panel(
                stats["mana_curve"]
            )
        )

        mana_curve_panel.setObjectName(
            "DashboardManaCurvePanel"
        )

        types_mana_row = QHBoxLayout()

        types_mana_row.setSpacing(
            10
        )

        types_mana_row.addWidget(
            types_panel,
            1
        )

        types_mana_row.addWidget(
            mana_curve_panel,
            1
        )

        right_col.addLayout(
            types_mana_row,
            2
        )

        main_row.addLayout(
            right_col,
            3
        )

        self.content_layout.addLayout(
            main_row
        )

        # =================================================
        # RODAPÉ — EDIÇÕES + DECKS + RECENTES
        # =================================================

        sets_panel = (
            self._create_sets_panel(
                stats["sets"]
            )
        )

        sets_panel.setObjectName(
            "DashboardBottomPanel"
        )

        sets_panel.setProperty(
            "panel_name",
            "sets",
        )

        decks_panel = (
            self._create_decks_panel(
                stats
            )
        )

        decks_panel.setObjectName(
            "DashboardBottomPanel"
        )

        decks_panel.setProperty(
            "panel_name",
            "decks",
        )

        recent_panel = (
            self._create_recent_panel(
                stats["recent"]
            )
        )

        recent_panel.setObjectName(
            "DashboardBottomPanel"
        )

        recent_panel.setProperty(
            "panel_name",
            "recent",
        )

        bottom_row = QHBoxLayout()

        bottom_row.setSpacing(
            10
        )

        bottom_row.addWidget(
            sets_panel,
            1
        )

        bottom_row.addWidget(
            decks_panel,
            1
        )

        bottom_row.addWidget(
            recent_panel,
            1
        )

        self.content_layout.addLayout(
            bottom_row
        )

        self.content_layout.addStretch()

        # =================================================
        # ANIMAÇÃO DE ENTRADA
        # =================================================

        self._schedule_entrance_animation()

    # =====================================================
    # ANIMAÇÃO DE ENTRADA
    # =====================================================

    def _schedule_entrance_animation(
        self,
    ):

        self._stop_entrance_animations()

        self._entrance_animations = []

        self._entrance_running = False

        from PySide6.QtCore import QTimer

        QTimer.singleShot(
            80,
            self._run_entrance_animation,
        )

    def _stop_entrance_animations(
        self,
    ):

        animations = getattr(
            self,
            "_entrance_animations",
            None,
        )

        if not animations:
            return

        for animation in animations:

            try:

                animation.stop()

            except (
                RuntimeError,
                AttributeError,
            ):
                pass

    def _run_entrance_animation(
        self,
    ):

        if self._entrance_running:
            return

        if not self.isVisible():
            return

        self._entrance_running = True

        from PySide6.QtWidgets import (
            QProgressBar as _QProgressBar,
            QFrame as _QFrame,
        )

        content = (
            self.content_layout.parentWidget()
        )

        if content is None:
            return

        # ---------------------------------------------
        # FASE 1 — CARDS DE ESTATÍSTICA
        # ---------------------------------------------

        stat_cards = [
            child
            for child in content.findChildren(
                _QFrame
            )
            if child.objectName()
            == "DashboardStatCard"
        ]

        for index, card in enumerate(
            stat_cards
        ):

            self._animate_enter(
                card,
                delay=index * 70,
                duration=380,
            )

        # ---------------------------------------------
        # FASE 2 — CARTAS MAIS VALIOSAS
        # ---------------------------------------------

        top_cards = [
            child
            for child in content.findChildren(
                _QFrame
            )
            if child.objectName()
            == "valuableCardsCard"
        ]

        for panel in top_cards:

            self._animate_enter(
                panel,
                delay=360,
                duration=420,
                animate_opacity=False,
            )

        # ---------------------------------------------
        # FASE 3 — DISTRIBUIÇÕES + BARRAS
        # ---------------------------------------------

        dist_panels = []

        for name in (
            "colors",
            "rarities",
            "types",
        ):

            for child in content.findChildren(
                _QFrame
            ):

                if (
                    child.objectName()
                    == "DashboardDistributionPanel"
                    and child.property(
                        "panel_name"
                    )
                    == name
                ):

                    dist_panels.append(
                        child
                    )

        for index, panel in enumerate(
            dist_panels
        ):

            self._animate_enter(
                panel,
                delay=620 + index * 90,
                duration=420,
            )

        # ---------------------------------------------
        # FASE 4 — CURVA DE MANA + BARRAS
        # ---------------------------------------------

        mana_panels = [
            child
            for child in content.findChildren(
                _QFrame
            )
            if child.objectName()
            == "DashboardManaCurvePanel"
        ]

        for panel in mana_panels:

            self._animate_enter(
                panel,
                delay=990,
                duration=440,
            )

        # ---------------------------------------------
        # FASE 5 — RODAPÉ
        # ---------------------------------------------

        bottom_panels = []

        for name in (
            "sets",
            "decks",
            "recent",
        ):

            for child in content.findChildren(
                _QFrame
            ):

                if (
                    child.objectName()
                    == "DashboardBottomPanel"
                    and child.property(
                        "panel_name"
                    )
                    == name
                ):

                    bottom_panels.append(
                        child
                    )

        for index, panel in enumerate(
            bottom_panels
        ):

            self._animate_enter(
                panel,
                delay=1260 + index * 100,
                duration=420,
            )

        # ---------------------------------------------
        # CRESCIMENTO DAS BARRAS
        # ---------------------------------------------

        self._grow_all_bars(
            content,
            base_delay=700,
        )

        # ---------------------------------------------
        # PREENCHIMENTO DO DONUT (raridades)
        # ---------------------------------------------

        donut_delay = 900

        # ---------------------------------------------
        # DONUTS
        #
        # Os donuts devem aparecer completos.
        # A animação de progresso fazia o gráfico
        # ficar visualmente "aberto" durante a entrada.
        # ---------------------------------------------

        for chart in content.findChildren(
                DonutChart
        ):

            try:

                chart._progress = 1.0
                chart.update()

            except RuntimeError:
                pass

            donut_delay += 60

    def _animate_enter(
        self,
        widget,
        delay,
        duration=400,
        dy=16,
        animate_opacity=True,
    ):

        from PySide6.QtCore import (
            QPoint,
            QEasingCurve,
            QParallelAnimationGroup,
            QPropertyAnimation,
            QTimer,
        )

        from PySide6.QtWidgets import (
            QGraphicsOpacityEffect,
        )

        try:

            if widget is None:
                return

            effect = None

            if animate_opacity:

                effect = QGraphicsOpacityEffect(
                    widget
                )

                widget.setGraphicsEffect(
                    effect
                )

                effect.setOpacity(0.0)

            final_pos = widget.geometry().topLeft()

            if (
                widget.width() <= 0
                or widget.height() <= 0
            ):

                final_pos = QPoint(
                    0,
                    0,
                )

            start_pos = QPoint(
                final_pos.x(),
                final_pos.y() + dy,
            )

            widget.move(
                start_pos
            )

            fade = None

            if effect is not None:

                fade = QPropertyAnimation(
                    effect,
                    b"opacity",
                    widget,
                )

                fade.setStartValue(
                    0.0
                )

                fade.setEndValue(
                    1.0
                )

                fade.setDuration(
                    duration
                )

                fade.setEasingCurve(
                    QEasingCurve.OutCubic
                )

            slide = QPropertyAnimation(
                widget,
                b"pos",
                widget,
            )

            slide.setStartValue(
                start_pos
            )

            slide.setEndValue(
                final_pos
            )

            group = QParallelAnimationGroup(
                widget
            )

            if fade is not None:

                group.addAnimation(
                    fade
                )

            group.addAnimation(
                slide
            )

            slide.setDuration(
                duration
            )

            slide.setEasingCurve(
                QEasingCurve.OutCubic
            )

            self._entrance_animations.append(
                group
            )

            def _start(
                group=group,
            ):

                try:
                    group.start()
                except RuntimeError:
                    pass

            QTimer.singleShot(
                max(
                    delay,
                    0
                ),
                _start,
            )

        except Exception as error:

            print(
                "[DASHBOARD] Erro no fade:",
                error,
            )

    def _grow_all_bars(
        self,
        content,
        base_delay,
    ):

        from PySide6.QtCore import (
            QVariantAnimation,
            QTimer,
        )

        from PySide6.QtCore import (
            QEasingCurve as _QEasingCurve,
        )

        bars = [
            bar
            for bar in content.findChildren(
                QProgressBar
            )
            if str(
                bar.objectName()
            ).startswith(
                "Dashboard"
            )
        ]

        index = 0

        for bar in bars:

            target = int(
                bar.value()
            )

            if target <= 0:
                continue

            bar.setValue(
                0
            )

            delay = (
                base_delay + index * 55
            )

            index += 1

            animation = QVariantAnimation(
                bar
            )

            animation.setDuration(
                520
            )

            animation.setStartValue(
                0
            )

            animation.setEndValue(
                target
            )

            animation.setEasingCurve(
                _QEasingCurve.OutCubic
            )

            def _apply_value(
                value,
                bar=bar,
            ):

                try:
                    bar.setValue(
                        int(value)
                    )
                except RuntimeError:
                    pass

            animation.valueChanged.connect(
                _apply_value
            )

            self._entrance_animations.append(
                animation
            )

            def _start(
                animation=animation,
            ):

                try:
                    animation.start()
                except RuntimeError:
                    pass

            QTimer.singleShot(
                delay,
                _start,
            )

        # ---------------------------------------------
        # BARRAS VERTICAIS DA CURVA DE MANA
        # ---------------------------------------------

        fills = [
            fill
            for fill in content.findChildren(
                QFrame
            )
            if fill.objectName()
            == "DashboardManaFill"
        ]

        fill_index = 0

        for fill in fills:

            target = int(
                fill.height()
            )

            if target <= 0:
                continue

            fill.setFixedHeight(
                0
            )

            delay = (
                base_delay
                + 120
                + fill_index * 65
            )

            fill_index += 1

            animation = QVariantAnimation(
                fill
            )

            animation.setDuration(
                540
            )

            animation.setStartValue(
                0
            )

            animation.setEndValue(
                target
            )

            animation.setEasingCurve(
                _QEasingCurve.OutCubic
            )

            def _apply_height(
                value,
                fill=fill,
            ):

                try:
                    fill.setFixedHeight(
                        max(
                            0,
                            int(value),
                        )
                    )
                except RuntimeError:
                    pass

            animation.valueChanged.connect(
                _apply_height
            )

            self._entrance_animations.append(
                animation
            )

            def _start_fill(
                animation=animation,
            ):

                try:
                    animation.start()
                except RuntimeError:
                    pass

            QTimer.singleShot(
                delay,
                _start_fill,
            )


    # =====================================================
    # LOAD DATABASE
    # =====================================================

    def _load_statistics(
        self,
    ):

        currency = (
            CurrencyService
            .get_selected_currency()
        )

        result = {
            "total_cards": 0,
            "unique_cards": 0,
            "total_decks": 0,
            "deck_cards": 0,
            "collection_value": 0.0,
            "collection_value_usd": 0.0,
            "collection_value_eur": 0.0,
            "collection_value_tix": 0.0,
            "currency": currency,

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

            "types": {},

            "top_cards": [],

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

            usd_value_expr = price_column_expression(
                "usd",
            )

            eur_value_expr = price_column_expression(
                "eur",
            )

            tix_value_expr = price_column_expression(
                "tix",
            )

            cursor.execute(
                f"""
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
                            {usd_value_expr}
                        ),
                        0
                    ) AS value_usd,

                    COALESCE(
                        SUM(
                            quantity *
                            {eur_value_expr}
                        ),
                        0
                    ) AS value_eur,

                    COALESCE(
                        SUM(
                            quantity *
                            {tix_value_expr}
                        ),
                        0
                    ) AS value_tix

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

                value_usd = float(
                    row["value_usd"]
                    or 0
                )

                value_eur = float(
                    row["value_eur"]
                    or 0
                )

                value_tix = float(
                    row["value_tix"]
                    or 0
                )

                result["collection_value_usd"] = value_usd
                result["collection_value_eur"] = value_eur
                result["collection_value_tix"] = value_tix

                if currency == "EUR":

                    result["collection_value"] = value_eur

                elif currency == "TIX":

                    result["collection_value"] = value_tix

                elif currency == "BRL":

                    result["collection_value"] = (
                        value_usd
                        * CurrencyService.rate("BRL")
                    )

                else:

                    result["collection_value"] = value_usd

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
                    COALESCE(
                        NULLIF(rarity, ''),
                        price_ref_rarity,
                        ''
                    ) AS effective_rarity,
                    SUM(quantity) AS total

                FROM cards

                WHERE quantity > 0

                GROUP BY
                    COALESCE(
                        NULLIF(rarity, ''),
                        price_ref_rarity,
                        ''
                    )

                ORDER BY
                    total DESC
                """
            )

            for row in cursor.fetchall():

                rarity = (
                    self._rarity_label(
                        row["effective_rarity"]
                    )
                )

                result["rarities"][
                    rarity
                ] = int(
                    row["total"]
                    or 0
                )

            # =================================================
            # TIPOS DE CARTA
            # =================================================

            cursor.execute(
                """
                SELECT
                    type_line,
                    quantity

                FROM cards

                WHERE quantity > 0
                """
            )

            type_counts = {
                "Criaturas": 0,
                "Mágicas": 0,
                "Artefatos": 0,
                "Encantamentos": 0,
                "Planeswalkers": 0,
                "Terrenos": 0,
                "Outros": 0,
            }

            for row in cursor.fetchall():

                quantity = int(
                    row["quantity"]
                    or 0
                )

                type_line = str(
                    row["type_line"]
                    or ""
                ).casefold()

                key = "Outros"

                if "criatura" in type_line or "creature" in type_line:
                    key = "Criaturas"
                elif "terreno" in type_line or "land" in type_line:
                    key = "Terrenos"
                elif "planeswalker" in type_line:
                    key = "Planeswalkers"
                elif "feitiço" in type_line or "sorcery" in type_line or "instantânea" in type_line or "instant" in type_line:
                    key = "Mágicas"
                elif "artefato" in type_line or "artifact" in type_line:
                    key = "Artefatos"
                elif "encantamento" in type_line or "enchantment" in type_line:
                    key = "Encantamentos"

                type_counts[key] += quantity

            result["types"] = type_counts

            # =================================================
            # CARTAS MAIS CARAS
            # =================================================

            top_usd_expr = price_column_expression(
                "usd",
                alias="price_usd",
            )

            top_eur_expr = price_column_expression(
                "eur",
                alias="price_eur",
            )

            top_tix_expr = price_column_expression(
                "tix",
                alias="price_tix",
            )

            cursor.execute(
                f"""
                SELECT
                    id,
                    name,
                    printed_name,
                    rarity,
                    set_name,
                    image_path,
                    price_usd_foil,
                    quantity,
                    mana_cost,
                    type_line,
                    {top_usd_expr},
                    {top_eur_expr},
                    {top_tix_expr}

                FROM cards

                WHERE
                    quantity > 0
                    AND {price_column_expression("usd")} > 0

                ORDER BY
                    quantity * {price_column_expression("usd")} DESC,
                    {price_column_expression("usd")} DESC

                LIMIT 6
                """
            )

            for row in cursor.fetchall():

                price = float(
                    row["price_usd"]
                    or 0
                )

                price_eur = row["price_eur"]

                price_tix = row["price_tix"]

                foil_price = float(
                    row["price_usd_foil"]
                    or 0
                )

                foil_premium = None

                if (
                    foil_price > 0
                    and price > 0
                ):

                    foil_premium = (
                        (foil_price - price)
                        / price
                        * 100
                    )

                quantity = int(
                    row["quantity"]
                    or 0
                )

                result["top_cards"].append(
                    {
                        "id": row["id"],
                        "name": (
                            row["printed_name"]
                            or row["name"]
                            or "Carta"
                        ),
                        "rarity": self._rarity_label(
                            row["rarity"]
                        ),
                        "set_name": (
                            row["set_name"]
                            or "Sem edição"
                        ),
                        "image_path": row[
                            "image_path"
                        ],
                        "price": price,
                        "price_eur": (
                            float(price_eur)
                            if price_eur is not None
                            else None
                        ),
                        "price_tix": (
                            float(price_tix)
                            if price_tix is not None
                            else None
                        ),
                        "foil_price": foil_price,
                        "foil_premium": foil_premium,
                        "quantity": quantity,
                        "total_value": float(
                            price
                            * quantity
                        ),
                        "total_eur": (
                            float(price_eur) * quantity
                            if price_eur is not None
                            else None
                        ),
                        "total_tix": (
                            float(price_tix) * quantity
                            if price_tix is not None
                            else None
                        ),
                        "mana_cost": (
                            row["mana_cost"]
                            or ""
                        ),
                        "type_line": (
                            row["type_line"]
                            or ""
                        ),
                    }
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

                deck = {
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

                fallback_image = deck[
                    "preview_image_path"
                ]

                if fallback_image:

                    fb = Path(
                        str(fallback_image)
                    )

                    if not fb.exists():
                        fallback_image = None

                deck["fallback_image_path"] = fallback_image

                deck["mana_curve"] = {
                    "0": 0,
                    "1": 0,
                    "2": 0,
                    "3": 0,
                    "4": 0,
                    "5": 0,
                    "6": 0,
                    "7+": 0,
                }

                result["deck_list"].append(
                    deck
                )

            # -------------------------------------------------
            # IMAGEM E CURVA DE MANA POR DECK
            # -------------------------------------------------

            for deck in result["deck_list"]:

                deck_id = deck["id"]

                # ---------- IMAGEM FALLBACK ----------

                if not deck["fallback_image_path"]:

                    cursor.execute(
                        """
                        SELECT
                            c.image_path

                        FROM deck_cards dc

                        INNER JOIN cards c
                            ON c.id = dc.card_id

                        WHERE
                            dc.deck_id = ?
                            AND c.image_path IS NOT NULL
                            AND c.image_path != ''

                        ORDER BY
                            dc.quantity DESC,
                            dc.updated_at DESC

                        LIMIT 1
                        """,
                        (deck_id,),
                    )

                    fb_row = cursor.fetchone()

                    if fb_row:
                        deck["fallback_image_path"] = (
                            fb_row["image_path"]
                        )

                # ---------- CURVA DE MANA ----------

                cursor.execute(
                    """
                    SELECT
                        dc.quantity,
                        c.cmc,
                        c.type_line,
                        c.color_identity

                    FROM deck_cards dc

                    INNER JOIN cards c
                        ON c.id = dc.card_id

                    WHERE dc.deck_id = ?
                    """,
                    (deck_id,),
                )

                deck["colors"] = set()

                for dc_row in cursor.fetchall():

                    qty = int(
                        dc_row["quantity"]
                        or 0
                    )

                    if qty <= 0:
                        continue

                    identity = dc_row["color_identity"]

                    if identity:

                        for letter in str(
                            identity
                        ):

                            if (
                                letter.upper()
                                in "WUBRG"
                            ):

                                deck["colors"].add(
                                    letter.upper()
                                )

                    type_line = str(
                        dc_row["type_line"]
                        or ""
                    ).casefold()

                    if (
                        "land" in type_line
                        or "terreno" in type_line
                    ):
                        continue

                    try:
                        cmc = float(
                            dc_row["cmc"]
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
                            int(max(0, cmc))
                        )

                    deck["mana_curve"][
                        key
                    ] += qty

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
        secondary=None,
        right_widget=None,
    ):

        icons = {
            "collection": "♠",
            "unique": "◆",
            "decks": "▣",
            "value": "$",
        }

        frame = QFrame()

        frame.setObjectName(
            "DashboardStatCard"
        )

        frame.setMinimumHeight(
            112
        )

        frame.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        frame.setProperty(
            "variant",
            variant
        )

        row = QHBoxLayout(
            frame
        )

        row.setContentsMargins(
            17,
            15,
            17,
            15,
        )

        row.setSpacing(
            14
        )

        # ---------------------------------------------
        # INFORMAÇÕES
        # ---------------------------------------------

        info = QVBoxLayout()

        info.setSpacing(
            4
        )

        title_row = QHBoxLayout()

        title_row.setSpacing(
            8
        )

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "DashboardStatTitle"
        )

        title_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        title_row.addWidget(
            title_label,
            1
        )

        if right_widget is not None:

            title_row.addWidget(
                right_widget,
                0,
                Qt.AlignmentFlag.AlignVCenter,
            )

        info.addLayout(
            title_row
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

        value_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        info.addWidget(
            value_label
        )

        if secondary:

            secondary_label = QLabel(
                secondary
            )

            secondary_label.setObjectName(
                "DashboardStatSecondary"
            )

            secondary_label.setSizePolicy(
                QSizePolicy.Policy.Ignored,
                QSizePolicy.Policy.Fixed,
            )

            info.addWidget(
                secondary_label
            )

        description_label = QLabel(
            description
        )

        description_label.setObjectName(
            "DashboardStatDescription"
        )

        description_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Fixed,
        )

        info.addWidget(
            description_label
        )

        info.addStretch(
            1
        )

        row.addLayout(
            info,
            1
        )

        # ---------------------------------------------
        # ÍCONE CIRCULAR
        # ---------------------------------------------

        icon_frame = QFrame()

        icon_frame.setObjectName(
            "DashboardStatIcon"
        )

        icon_frame.setProperty(
            "variant",
            variant
        )

        icon_frame.setFixedSize(
            58,
            58
        )

        icon_layout = QVBoxLayout(
            icon_frame
        )

        icon_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        icon_label = QLabel(
            icons.get(
                variant,
                "◆",
            )
        )

        icon_label.setObjectName(
            "DashboardStatIconGlyph"
        )

        icon_label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        icon_layout.addWidget(
            icon_label
        )

        row.addWidget(
            icon_frame,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        return frame

    # =====================================================
    # SELETOR DE MOEDA (card Valor Estimado)
    # =====================================================

    def _build_currency_button(
        self,
        currency,
    ):

        button = QPushButton(
            f"{currency} ▾"
        )

        button.setObjectName(
            "currencySelectorButton"
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        button.clicked.connect(
            lambda: self._show_currency_menu(
                button
            )
        )

        return button

    def _show_currency_menu(
        self,
        button,
    ):

        current = (
            CurrencyService
            .get_selected_currency()
        )

        menu = QMenu(
            button
        )

        menu.setObjectName(
            "currencyMenu"
        )

        group = QActionGroup(
            menu
        )

        group.setExclusive(
            True
        )

        from services.currency_service import (
            CURRENCIES,
        )

        for code, symbol, name in CURRENCIES:

            action = QAction(
                f"{code}   {symbol}",
                menu,
            )

            action.setCheckable(
                True
            )

            action.setChecked(
                code == current
            )

            action.setData(
                code
            )

            group.addAction(
                action
            )

            menu.addAction(
                action
            )

        selected = menu.exec(
            button.mapToGlobal(
                button.rect().bottomLeft()
            )
        )

        if selected is None:
            return

        code = str(
            selected.data()
            or ""
        )

        if not code:
            return

        if code == current:
            return

        CurrencyService.set_selected_currency(
            code
        )

        CurrencyService.start_background_refresh()

        self.refresh()

    # =====================================================
    # BARRA — REFERÊNCIA DE PREÇOS
    # =====================================================

    def _create_pricing_bar(
        self,
        mode,
    ):

        bar = QFrame()

        bar.setObjectName(
            "dashboardPricingBar"
        )

        row = QHBoxLayout(
            bar
        )

        row.setContentsMargins(
            14,
            8,
            12,
            8,
        )

        row.setSpacing(
            10
        )

        title = QLabel(
            "🌐 Referência de preços"
        )

        title.setObjectName(
            "pricingBarTitle"
        )

        row.addWidget(
            title
        )

        status = QLabel(
            f"Atualmente: {pricing_mode_label(mode)}"
        )

        status.setObjectName(
            "pricingBarValue"
        )

        row.addWidget(
            status
        )

        row.addStretch(
            1
        )

        change_button = QPushButton(
            "Alterar ↻"
        )

        change_button.setObjectName(
            "pricingBarButton"
        )

        change_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        change_button.setFocusPolicy(
            Qt.FocusPolicy.NoFocus
        )

        change_button.clicked.connect(
            lambda: self._toggle_pricing_mode()
        )

        row.addWidget(
            change_button
        )

        return bar

    def _toggle_pricing_mode(
        self,
    ):

        current = get_pricing_mode()

        new_mode = (
            PRICING_MODE_IMPRINT
            if current == PRICING_MODE_ORIGINAL
            else PRICING_MODE_ORIGINAL
        )

        set_pricing_mode(
            new_mode
        )

        self.refresh()

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

        data = [
            (
                name,
                value,
            )
            for name, value in values.items()
            if value > 0
        ]

        total = sum(
            value
            for _, value in data
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

        for name, value in data:

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

            row.addWidget(
                mana_symbol
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
                62
            )

            row.addWidget(
                label
            )

            # =================================================
            # BARRA COLORIDA
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
                9
            )

            bar.setMinimumWidth(
                24
            )

            row.addWidget(
                bar,
                1
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
                38
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignRight
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
    # LEGENDA DO DONUT
    # =====================================================

    def _build_legend_row(
        self,
        name,
        value,
        total,
        color,
    ):

        row = QHBoxLayout()

        row.setSpacing(
            8
        )

        dot = QLabel()

        dot.setFixedSize(
            12,
            12
        )

        dot.setObjectName(
            "DashboardDonutLegendDot"
        )

        dot.setStyleSheet(
            (
                f"background-color: {color};"
                "border-radius: 3px;"
            )
        )

        row.addWidget(
            dot,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        label = QLabel(
            name
        )

        label.setObjectName(
            "DashboardDonutLegendName"
        )

        row.addWidget(
            label,
            1,
            Qt.AlignmentFlag.AlignVCenter,
        )

        count = QLabel(
            self._format_number(
                value
            )
        )

        count.setObjectName(
            "DashboardDonutLegendValue"
        )

        count.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        count.setFixedWidth(
            40
        )

        row.addWidget(
            count,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        percentage = (
            round(
                value / total * 100
            )
            if total > 0
            else 0
        )

        percent = QLabel(
            f"{percentage}%"
        )

        percent.setObjectName(
            "DashboardDonutLegendPercent"
        )

        percent.setAlignment(
            Qt.AlignmentFlag.AlignRight
            | Qt.AlignmentFlag.AlignVCenter
        )

        percent.setFixedWidth(
            36
        )

        row.addWidget(
            percent,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        return row

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

        donut_data = [
            (
                name,
                value,
                RARITY_DONUT_HEX.get(
                    name,
                    "#8a94a6",
                ),
            )
            for name, value in data
        ]

        content = QHBoxLayout()

        content.setSpacing(
            16
        )

        donut = DonutChart(
            center_value=self._format_number(
                total
            ),
            center_caption="cartas",
        )

        donut.set_data(
            donut_data
        )

        donut.setFixedSize(
            128,
            128
        )

        content.addWidget(
            donut,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        legend = QVBoxLayout()

        legend.setSpacing(
            7
        )

        legend.addStretch(
            1
        )

        for name, value, color in donut_data:
            legend.addLayout(
                self._build_legend_row(
                    name,
                    value,
                    total,
                    color,
                )
            )

        legend.addStretch(
            1
        )

        content.addLayout(
            legend,
            1,
        )

        layout.addLayout(
            content
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

        return panel


    # =====================================================
    # TIPOS DE CARTA
    # =====================================================

    def _create_types_panel(
        self,
        values,
    ):

        panel = self._create_panel(
            "Tipos de carta",
            "Distribuição das cartas por tipo."
        )

        layout = panel.layout()

        ordered = [
            "Criaturas",
            "Mágicas",
            "Artefatos",
            "Encantamentos",
            "Planeswalkers",
            "Terrenos",
            "Outros",
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

        total = sum(
            value
            for _, value in data
        )

        icons = {
            "Criaturas": "⚔",
            "Mágicas": "✦",
            "Artefatos": "⚙",
            "Encantamentos": "✦",
            "Planeswalkers": "✚",
            "Terrenos": "⬢",
            "Outros": "•",
        }

        for name, value in data:

            row = QHBoxLayout()

            row.setSpacing(
                10
            )

            icon_label = QLabel(
                icons.get(
                    name,
                    "•"
                )
            )

            icon_label.setObjectName(
                "DashboardTypeIcon"
            )

            icon_label.setProperty(
                "type",
                name,
            )

            icon_label.setFixedWidth(
                20
            )

            icon_label.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            label = QLabel(
                name
            )

            label.setObjectName(
                "DashboardRowLabel"
            )

            label.setFixedWidth(
                82
            )

            bar = QProgressBar()

            bar.setObjectName(
                "DashboardRarityBar"
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

            bar.setMinimumWidth(
                24
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
                38
            )

            count.setAlignment(
                Qt.AlignmentFlag.AlignRight
            )

            row.addWidget(
                icon_label
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
    # CARTAS MAIS CARAS
    # =====================================================

    def _create_top_cards_panel(
        self,
        cards,
    ):

        widget = ValuableCardsWidget(
            cards,
            CurrencyService.get_selected_currency(),
            self,
        )

        widget.row_clicked.connect(
            self.card_clicked.emit
        )

        widget.view_all_clicked.connect(
            self.view_all_cards.emit
        )

        return widget

    def _attach_hover_zoom(
        self,
        card,
        image_label,
    ):

        if (
            image_label is None
            or image_label.pixmap()
            is None
        ):

            return

        card.installEventFilter(
            _HoverZoomFilter(
                image_label
            )
        )


    # =====================================================
    # MANA CURVE
    # =====================================================

    def _create_mana_curve_panel(
            self,
            values,
    ):

        order = [
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7+",
        ]

        panel = self._create_panel(
            "Curva de mana",
            "Distribuição das cartas por custo de mana."
        )

        layout = panel.layout()

        graph = QHBoxLayout()

        graph.setContentsMargins(
            4,
            6,
            4,
            2,
        )

        graph.setSpacing(
            10
        )

        maximum = max(
            values.values()
        ) if values else 1

        maximum = max(
            maximum,
            1
        )

        for mana_value in order:

            value = int(
                values.get(
                    mana_value,
                    0,
                )
            )

            column = QVBoxLayout()

            column.setContentsMargins(
                0,
                0,
                0,
                0,
            )

            column.setSpacing(
                4
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
                92
            )

            track.setMinimumWidth(
                30
            )

            track.setMaximumWidth(
                44
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
                92 * ratio
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

        for index, (name, value) in enumerate(
            sets
        ):

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

            bar.setProperty(
                "setIndex",
                str(index),
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

            row_frame.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            row_frame.installEventFilter(
                _CardClickFilter(
                    card,
                    self.card_clicked.emit,
                    self,
                )
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
                True
            )

            set_name = QLabel(
                card["set_name"]
                or card["rarity"]
            )

            set_name.setObjectName(
                "DashboardRecentMeta"
            )

            set_name.setWordWrap(
                True
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

        deck_row = QVBoxLayout()

        deck_row.setContentsMargins(
            0,
            0,
            0,
            0
        )

        deck_row.setSpacing(
            8
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
                10,
                7,
                10,
                7
            )

            card_layout.setSpacing(
                10
            )

            image = QLabel()

            image.setObjectName(
                "DashboardDeckImage"
            )

            image.setFixedSize(
                52,
                72
            )

            image.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self._set_card_image(
                image,
                deck.get(
                    "fallback_image_path"
                )
                or deck.get(
                    "preview_image_path"
                ),
            )

            card_layout.addWidget(
                image
            )

            info = QVBoxLayout()

            info.setSpacing(
                3
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

            meta_row = QHBoxLayout()

            meta_row.setSpacing(
                8
            )

            total = QLabel(
                f'{self._format_number(deck["total_cards"])} '
                f'cartas'
            )

            total.setObjectName(
                "DashboardDeckCards"
            )

            meta_row.addWidget(
                total
            )

            # ---------------------------------------------
            # CORES DO DECK
            # ---------------------------------------------

            colors = deck.get(
                "colors",
                set(),
            )

            if colors:

                color_row = QHBoxLayout()

                color_row.setSpacing(
                    3
                )

                for letter in "WUBRG":

                    pip = QLabel(
                        "●"
                    )

                    pip.setObjectName(
                        "DashboardDeckColor"
                    )

                    pip.setProperty(
                        "color",
                        letter,
                    )

                    pip.setFixedSize(
                        10,
                        10
                    )

                    pip.setAlignment(
                        Qt.AlignmentFlag.AlignCenter
                    )

                    if letter in colors:

                        pip.setStyleSheet(
                            f'color: {DECK_COLOR_HEX.get(letter, "#8b93a3")};'
                        )

                    else:

                        pip.setStyleSheet(
                            "color: #333a47;"
                        )

                    color_row.addWidget(
                        pip
                    )

                meta_row.addLayout(
                    color_row
                )

            meta_row.addStretch()

            info.addLayout(
                meta_row
            )

            # ---------------------------------------------
            # CURVA DE MANA DO DECK
            # ---------------------------------------------

            curve_row = QHBoxLayout()

            curve_row.setSpacing(
                3
            )

            curve = deck.get(
                "mana_curve",
                {},
            )

            max_curve = max(
                curve.values() or [1],
            )

            max_curve = max(
                max_curve,
                1,
            )

            for mana_key in (
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7+",
            ):

                value = int(
                    curve.get(
                        mana_key,
                        0,
                    )
                )

                bar_frame = QFrame()

                bar_frame.setObjectName(
                    "DashboardDeckCurveBar"
                )

                bar_frame.setFixedWidth(
                    9
                )

                bar_frame.setMinimumHeight(
                    3
                )

                bar_frame.setMaximumHeight(
                    26
                )

                bar_layout = QVBoxLayout(
                    bar_frame
                )

                bar_layout.setContentsMargins(
                    0,
                    0,
                    0,
                    0,
                )

                bar_layout.setSpacing(
                    0
                )

                fill = QFrame()

                fill.setObjectName(
                    "DashboardDeckCurveFill"
                )

                fill_height = int(
                    max(
                        1,
                        round(
                            26 * value / max_curve
                        ),
                    )
                ) if value > 0 else 0

                fill.setFixedHeight(
                    fill_height
                )

                bar_layout.addStretch()

                if fill_height > 0:
                    bar_layout.addWidget(
                        fill,
                        0,
                        Qt.AlignmentFlag.AlignBottom,
                    )

                curve_row.addWidget(
                    bar_frame
                )

            curve_row.addStretch()

            info.addLayout(
                curve_row
            )

            card_layout.addLayout(
                info,
                1
            )

            deck_row.addWidget(
                card,
                0,
                Qt.AlignmentFlag.AlignTop,
            )

        layout.addLayout(
            deck_row
        )

        layout.addStretch(
            1
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

        title_label.setWordWrap(
            True
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

            subtitle_label.setWordWrap(
                True
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
    def _usd_brl_rate(
        value=None,
    ):

        return float(
            CACHED_USD_BRL
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
            "common rarity": "Comum",

            "uncommon": "Incomum",
            "uncommon rarity": "Incomum",

            "rare": "Rara",
            "rare rarity": "Rara",

            "mythic": "Mítica",
            "mythic rare": "Mítica",
            "mythic rarity": "Mítica",

            "special": "Especial",
            "bonus": "Bônus",

            "timeshifted": "Timeshifted",
            "masterpiece": "Masterpiece",

            "unknown": "Sem raridade",
            "": "Sem raridade",
        }

        return mapping.get(
            value,
            str(
                rarity
                or "Sem raridade"
            ).strip().capitalize()
        )
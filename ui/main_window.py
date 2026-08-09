
from pathlib import Path

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
)

from pages.collection_page import CollectionPage
from pages.decks_page import DecksPage

from ui.theme import DARK_THEME


# =========================================================
# CAMINHOS DOS ASSETS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ICONS_DIR = (
    BASE_DIR
    / "assets"
    / "icons"
)

APP_ICON_PATH = (
    ICONS_DIR
    / "icon_app.png"
)

COLLECTION_ICON_PATH = (
    ICONS_DIR
    / "collection_icon.png"
)

DECKS_ICON_PATH = (
    ICONS_DIR
    / "decks_icon.png"
)

CARD_ICON_PATH = (
    ICONS_DIR
    / "card_icon.png"
)


# =========================================================
# MAIN WINDOW
# =========================================================

class MainWindow(QMainWindow):

    def __init__(self):

        super().__init__()

        # =================================================
        # CONFIGURAÇÃO DA JANELA
        # =================================================

        self.setWindowTitle(
            "Magic Collection"
        )

        self.resize(
            1400,
            920
        )

        self.setMinimumSize(
            900,
            600
        )

        # =================================================
        # ÍCONE DO APLICATIVO
        # =================================================

        if APP_ICON_PATH.exists():

            self.setWindowIcon(
                QIcon(
                    str(APP_ICON_PATH)
                )
            )

        # =================================================
        # TEMA
        # =================================================

        self.setStyleSheet(
            DARK_THEME
        )

        # =================================================
        # UI
        # =================================================

        self.setup_ui()

        self.show_collection()


    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(self):

        central_widget = QWidget()

        self.setCentralWidget(
            central_widget
        )

        main_layout = QHBoxLayout(
            central_widget
        )

        main_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        main_layout.setSpacing(
            0
        )


        # =================================================
        # SIDEBAR
        # =================================================

        sidebar = QFrame()

        sidebar.setObjectName(
            "Sidebar"
        )

        sidebar.setFixedWidth(
            265
        )

        sidebar_layout = QVBoxLayout(
            sidebar
        )

        sidebar_layout.setContentsMargins(
            18,
            22,
            18,
            16
        )

        sidebar_layout.setSpacing(
            8
        )


        # =================================================
        # HEADER DA SIDEBAR
        # =================================================

        app_header = QWidget()

        app_header.setObjectName(
            "AppHeader"
        )

        app_header_layout = QHBoxLayout(
            app_header
        )

        app_header_layout.setContentsMargins(
            4,
            0,
            4,
            18
        )

        app_header_layout.setSpacing(
            10
        )


        # =================================================
        # ÍCONE DO APP
        # =================================================

        app_icon = QLabel()

        app_icon.setObjectName(
            "AppIcon"
        )

        # Aumente estes valores para aumentar
        # o ícone do aplicativo.
        app_icon.setFixedSize(
            42,
            42
        )

        app_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        if APP_ICON_PATH.exists():

            pixmap = QPixmap(
                str(APP_ICON_PATH)
            )

            if not pixmap.isNull():

                pixmap = pixmap.scaled(
                    42,
                    42,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

                app_icon.setPixmap(
                    pixmap
                )

        app_header_layout.addWidget(
            app_icon,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )


        # =================================================
        # TÍTULO
        # =================================================

        app_title = QLabel(
            "Magic Collection"
        )

        app_title.setObjectName(
            "AppTitle"
        )

        app_title.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )

        app_title.setMinimumWidth(
            155
        )

        app_header_layout.addWidget(
            app_title,
            1
        )

        sidebar_layout.addWidget(
            app_header
        )


        # =================================================
        # COLEÇÃO
        # =================================================

        self.collection_button = QPushButton(
            "COLEÇÃO"
        )

        self.collection_button.setObjectName(
            "SidebarButton"
        )

        self.collection_button.setCheckable(
            True
        )

        self.collection_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.collection_button.setMinimumHeight(
            68
        )

        # -------------------------------------------------
        # ÍCONE DA COLEÇÃO
        # -------------------------------------------------

        if COLLECTION_ICON_PATH.exists():

            self.collection_button.setIcon(
                QIcon(
                    str(COLLECTION_ICON_PATH)
                )
            )

        # TAMANHO DO ÍCONE DA COLEÇÃO
        self.collection_button.setIconSize(
            QSize(
                64,
                64
            )
        )

        self.collection_button.clicked.connect(
            self.show_collection
        )

        sidebar_layout.addWidget(
            self.collection_button
        )


        # =================================================
        # DECKS
        # =================================================

        # PRIMEIRO criamos o botão.
        self.decks_button = QPushButton(
            "DECKS"
        )

        self.decks_button.setObjectName(
            "SidebarButton"
        )

        self.decks_button.setCheckable(
            True
        )

        self.decks_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.decks_button.setMinimumHeight(
            68
        )

        # -------------------------------------------------
        # ÍCONE DOS DECKS
        # -------------------------------------------------

        if DECKS_ICON_PATH.exists():

            self.decks_button.setIcon(
                QIcon(
                    str(DECKS_ICON_PATH)
                )
            )

        # TAMANHO DO ÍCONE DOS DECKS
        self.decks_button.setIconSize(
            QSize(
                64,
                64
            )
        )

        self.decks_button.clicked.connect(
            self.show_decks
        )

        sidebar_layout.addWidget(
            self.decks_button
        )


        # =================================================
        # ESPAÇAMENTO
        # =================================================

        sidebar_layout.addStretch()


        # =================================================
        # STATUS
        # =================================================

        self.sidebar_status = QLabel(
            "Coleção"
        )

        self.sidebar_status.setObjectName(
            "SidebarStatus"
        )

        self.sidebar_status.setWordWrap(
            True
        )

        self.sidebar_status.setAlignment(
            Qt.AlignmentFlag.AlignLeft
            | Qt.AlignmentFlag.AlignVCenter
        )

        sidebar_layout.addWidget(
            self.sidebar_status
        )


        # =================================================
        # ADICIONAR SIDEBAR
        # =================================================

        main_layout.addWidget(
            sidebar
        )


        # =================================================
        # CONTEÚDO
        # =================================================

        self.content_widget = QWidget()

        self.content_widget.setObjectName(
            "ContentWidget"
        )

        self.content_layout = QVBoxLayout(
            self.content_widget
        )

        self.content_layout.setContentsMargins(
            0,
            0,
            0,
            0
        )

        self.content_layout.setSpacing(
            0
        )

        main_layout.addWidget(
            self.content_widget,
            1
        )


    # =====================================================
    # COLEÇÃO
    # =====================================================

    def show_collection(self):

        self.collection_button.setChecked(
            True
        )

        self.decks_button.setChecked(
            False
        )

        self.clear_content()

        self.collection_page = CollectionPage(
            self
        )

        self.content_layout.addWidget(
            self.collection_page
        )

        self.sidebar_status.setText(
            "Coleção"
        )


    # =====================================================
    # DECKS
    # =====================================================

    def show_decks(self):

        self.collection_button.setChecked(
            False
        )

        self.decks_button.setChecked(
            True
        )

        self.clear_content()

        self.decks_page = DecksPage(
            self
        )

        self.content_layout.addWidget(
            self.decks_page
        )

        self.sidebar_status.setText(
            "Decks"
        )


    # =====================================================
    # LIMPAR CONTEÚDO
    # =====================================================

    def clear_content(self):

        while self.content_layout.count():

            item = (
                self.content_layout.takeAt(0)
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()

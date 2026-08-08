from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QSizePolicy,
)

from pages.collection_page import (
    CollectionPage,
)

from ui.theme import DARK_THEME


# =========================================================
# MAIN WINDOW
# =========================================================

class MainWindow(QMainWindow):

    def __init__(
        self
    ):

        super().__init__()

        self.setWindowTitle(
            "Magic Collection"
        )

        self.resize(
            1100,
            720
        )

        self.setMinimumSize(
            900,
            600
        )

        self.setStyleSheet(
            DARK_THEME
        )

        self.setup_ui()

        self.show_collection()

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(
        self
    ):

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
            220
        )

        sidebar_layout = QVBoxLayout(
            sidebar
        )

        sidebar_layout.setContentsMargins(
            16,
            22,
            16,
            16
        )

        sidebar_layout.setSpacing(
            8
        )

        app_title = QLabel(
            "🃏  Magic Collection"
        )

        app_title.setObjectName(
            "AppTitle"
        )

        app_title.setContentsMargins(
            4,
            0,
            0,
            18
        )

        sidebar_layout.addWidget(
            app_title
        )

        # =================================================
        # COLEÇÃO
        # =================================================

        self.collection_button = QPushButton(
            "📦   Coleção"
        )

        self.collection_button.setObjectName(
            "SidebarButton"
        )

        self.collection_button.setCheckable(
            True
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

        self.decks_button = QPushButton(
            "🎴   Decks"
        )

        self.decks_button.setObjectName(
            "SidebarButton"
        )

        self.decks_button.setCheckable(
            True
        )

        self.decks_button.clicked.connect(
            self.show_decks
        )

        sidebar_layout.addWidget(
            self.decks_button
        )

        sidebar_layout.addStretch()

        # =================================================
        # STATUS
        # =================================================

        self.sidebar_status = QLabel(
            "Magic Collection"
        )

        self.sidebar_status.setObjectName(
            "SidebarStatus"
        )

        self.sidebar_status.setWordWrap(
            True
        )

        sidebar_layout.addWidget(
            self.sidebar_status
        )

        main_layout.addWidget(
            sidebar
        )

        # =================================================
        # CONTEÚDO
        # =================================================

        self.content_widget = QWidget()

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
            self.content_widget
        )

    # =====================================================
    # COLEÇÃO
    # =====================================================

    def show_collection(
        self
    ):

        self.collection_button.setChecked(
            True
        )

        self.decks_button.setChecked(
            False
        )

        self.clear_content()

        self.collection_page = (
            CollectionPage(
                self
            )
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

    def show_decks(
        self
    ):

        self.collection_button.setChecked(
            False
        )

        self.decks_button.setChecked(
            True
        )

        self.clear_content()

        title = QLabel(
            "Meus Decks"
        )

        title.setObjectName(
            "SectionTitle"
        )

        self.content_layout.addWidget(
            title
        )

        description = QLabel(
            "Aqui você poderá criar e organizar seus decks."
        )

        description.setObjectName(
            "SectionDescription"
        )

        self.content_layout.addWidget(
            description
        )

        coming_soon = QLabel(
            "🎴\n\nConstrutor de decks em breve."
        )

        coming_soon.setObjectName(
            "ComingSoon"
        )

        coming_soon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        coming_soon.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.content_layout.addWidget(
            coming_soon
        )

        self.sidebar_status.setText(
            "Decks"
        )

    # =====================================================
    # LIMPAR
    # =====================================================

    def clear_content(
        self
    ):

        while self.content_layout.count():

            item = (
                self.content_layout.takeAt(0)
            )

            widget = item.widget()

            if widget:

                widget.deleteLater()
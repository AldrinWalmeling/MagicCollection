from pathlib import Path

from PySide6.QtCore import (
    Qt,
    QSize,
    Signal,
)
from PySide6.QtGui import (
    QIcon,
    QPixmap,
)
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
from pages.dashboard_page import DashboardPage
from pages.settings_page import SettingsPage
from pages.profiles_page import ProfilesPage

from profile_manager import ProfileManager

from ui.theme import DARK_THEME


# =========================================================
# CAMINHOS DOS ASSETS
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ICONS_DIR = (
    BASE_DIR
    / "assets"
    / "icons"
)

APP_ICON_PATH = (
    ICONS_DIR
    / "mcollection.png"
)

COLLECTION_ICON_PATH = (
    ICONS_DIR
    / "collection.png"
)

DECKS_ICON_PATH = (
    ICONS_DIR
    / "deck.png"
)

DASHBOARD_ICON_PATH = (
    ICONS_DIR
    / "dashboard.png"
)

EXPLORAR_ICON_PATH = (
    ICONS_DIR
    / "analise.png"
)


# =========================================================
# PERFIL DA SIDEBAR
# =========================================================

class SidebarProfile(QFrame):

    clicked = Signal()

    def __init__(
        self,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.setObjectName(
            "SidebarProfile"
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setup_ui()

    # =====================================================
    # SETUP
    # =====================================================

    def setup_ui(
        self,
    ):

        layout = QHBoxLayout(
            self
        )

        layout.setContentsMargins(
            10,
            10,
            10,
            10,
        )

        layout.setSpacing(
            10
        )

        # =================================================
        # AVATAR
        # =================================================

        self.avatar = QLabel(
            "U"
        )

        self.avatar.setObjectName(
            "SidebarAvatar"
        )

        self.avatar.setFixedSize(
            36,
            36,
        )

        self.avatar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            self.avatar
        )

        # =================================================
        # INFORMAÇÕES
        # =================================================

        info = QVBoxLayout()

        info.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        info.setSpacing(
            1
        )

        self.profile_name = QLabel(
            "Usuário"
        )

        self.profile_name.setObjectName(
            "SidebarProfileName"
        )

        info.addWidget(
            self.profile_name
        )

        self.profile_hint = QLabel(
            "Selecionar perfil"
        )

        self.profile_hint.setObjectName(
            "SidebarProfileHint"
        )

        info.addWidget(
            self.profile_hint
        )

        layout.addLayout(
            info,
            1
        )

    # =====================================================
    # ATUALIZAR PERFIL
    # =====================================================

    def set_profile(
        self,
        profile,
    ):

        if profile is None:

            self.profile_name.setText(
                "Usuário"
            )

            self.profile_hint.setText(
                "Selecionar perfil"
            )

            self.avatar.clear()

            self.avatar.setText(
                "U"
            )

            return

        # =================================================
        # NOME
        # =================================================

        name = str(
            getattr(
                profile,
                "name",
                "Usuário",
            )
            or "Usuário"
        ).strip()

        self.profile_name.setText(
            name
        )

        self.profile_hint.setText(
            "Perfil ativo"
        )

        # =================================================
        # AVATAR
        # =================================================

        avatar_path = getattr(
            profile,
            "avatar_path",
            None,
        )

        if avatar_path:

            try:

                path = Path(
                    avatar_path
                )

                if path.exists():

                    pixmap = QPixmap(
                        str(path)
                    )

                    if not pixmap.isNull():

                        pixmap = pixmap.scaled(
                            36,
                            36,
                            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                            Qt.TransformationMode.SmoothTransformation,
                        )

                        self.avatar.setPixmap(
                            pixmap
                        )

                        return

            except Exception:

                pass

        # =================================================
        # INICIAIS
        # =================================================

        words = [
            word
            for word in name.split()
            if word
        ]

        if len(words) >= 2:

            initials = (
                words[0][0]
                + words[-1][0]
            ).upper()

        elif len(words) == 1:

            initials = (
                words[0][0]
                .upper()
            )

        else:

            initials = "U"

        self.avatar.clear()

        self.avatar.setText(
            initials
        )

    # =====================================================
    # CLICK
    # =====================================================

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

        super().mousePressEvent(
            event
        )


# =========================================================
# MAIN WINDOW
# =========================================================

class MainWindow(QMainWindow):

    def __init__(
        self,
    ):

        super().__init__()

        # =================================================
        # CONFIGURAÇÃO DA JANELA
        # =================================================

        self.setWindowTitle(
            "Magic Collection"
        )

        self.resize(
            1440,
            920,
        )

        self.setMinimumSize(
            1360,
            880,
        )

        # =================================================
        # ÍCONE
        # =================================================

        if APP_ICON_PATH.exists():

            self.setWindowIcon(
                QIcon(
                    str(
                        APP_ICON_PATH
                    )
                )
            )

        # =================================================
        # TEMA
        # =================================================

        self.setStyleSheet(
            DARK_THEME
        )

        # =================================================
        # PROFILE MANAGER
        # =================================================

        self.profile_manager = (
            ProfileManager()
        )

        self.active_profile = (
            self.profile_manager
            .get_active_profile()
        )

        # =================================================
        # PÁGINAS
        # =================================================

        self.profiles_page = None

        self.collection_page = None
        self.decks_page = None
        self.dashboard_page = None
        self.settings_page = None

        self.explore_page = None
        self.export_page = None
        self.reports_page = None

        self._dashboard_deck_signal_connected = False

        # =================================================
        # UI
        # =================================================

        self.setup_ui()

        # =================================================
        # PERFIL
        # =================================================

        self.update_sidebar_profile()

        # =================================================
        # PÁGINA INICIAL
        # =================================================

        self._open_initial_page()

    # =====================================================
    # SETUP DA INTERFACE
    # =====================================================

    def setup_ui(
        self,
    ):

        # =================================================
        # CENTRAL
        # =================================================

        central_widget = QWidget()

        central_widget.setObjectName(
            "MainCentralWidget"
        )

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
            0,
        )

        main_layout.setSpacing(
            0
        )

        self.main_layout = (
            main_layout
        )

        # =================================================
        # SIDEBAR
        # =================================================

        self.sidebar = QFrame()

        self.sidebar.setObjectName(
            "Sidebar"
        )

        self.sidebar.setFixedWidth(
            240
        )

        sidebar_layout = QVBoxLayout(
            self.sidebar
        )

        sidebar_layout.setContentsMargins(
            14,
            18,
            14,
            14,
        )

        sidebar_layout.setSpacing(
            6
        )

        # =================================================
        # HEADER
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
            16,
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

        app_icon.setFixedSize(
            40,
            40,
        )

        app_icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        if APP_ICON_PATH.exists():

            pixmap = QPixmap(
                str(
                    APP_ICON_PATH
                )
            )

            if not pixmap.isNull():

                pixmap = pixmap.scaled(
                    35,
                    35,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                app_icon.setPixmap(
                    pixmap
                )

        app_header_layout.addWidget(
            app_icon,
            0,
            Qt.AlignmentFlag.AlignVCenter,
        )

        # =================================================
        # NOME
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

        app_header_layout.addWidget(
            app_title,
            1,
        )

        sidebar_layout.addWidget(
            app_header
        )



        # =================================================
        # SEÇÃO COLEÇÃO
        # =================================================

        sidebar_layout.addWidget(
            self._section_label(
                "MENU"
            )
        )

        # =================================================
        # DASHBOARD
        # =================================================

        self.dashboard_button = (
            self._sidebar_button(
                "Dashboard"
            )
        )

        self.dashboard_button.clicked.connect(
            self.show_dashboard
        )

        sidebar_layout.addWidget(
            self.dashboard_button
        )

        # =================================================
        # COLEÇÃO
        # =================================================

        self.collection_button = (
            self._sidebar_button(
                "Coleção"
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

        self.decks_button = (
            self._sidebar_button(
                "Decks"
            )
        )

        self.decks_button.clicked.connect(
            self.show_decks
        )

        sidebar_layout.addWidget(
            self.decks_button
        )

        # =================================================
        # EXPLORAR
        # =================================================

        self.explore_button = (
            self._sidebar_button(
                "Explorar"
            )
        )

        self.explore_button.clicked.connect(
            self.show_explore
        )

        sidebar_layout.addWidget(
            self.explore_button
        )

        # =================================================
        # DIVISOR
        # =================================================

        sidebar_layout.addWidget(
            self._divider()
        )

        # =================================================
        # FERRAMENTAS
        # =================================================

        sidebar_layout.addWidget(
            self._section_label(
                "FERRAMENTAS"
            )
        )

        # =================================================
        # EXPORTAR
        # =================================================

        self.export_button = (
            self._sidebar_button(
                "Exportar"
            )
        )

        self.export_button.clicked.connect(
            self.show_export
        )

        sidebar_layout.addWidget(
            self.export_button
        )

        # =================================================
        # RELATÓRIOS
        # =================================================

        self.reports_button = (
            self._sidebar_button(
                "Relatórios"
            )
        )

        self.reports_button.clicked.connect(
            self.show_reports
        )

        sidebar_layout.addWidget(
            self.reports_button
        )

        # =================================================
        # CONFIGURAÇÕES
        # =================================================

        self.settings_button = (
            self._sidebar_button(
                "Configurações"
            )
        )

        self.settings_button.clicked.connect(
            self.show_settings
        )

        sidebar_layout.addWidget(
            self.settings_button
        )

        # =================================================
        # ESPAÇO
        # =================================================

        sidebar_layout.addStretch()

        # =================================================
        # STATUS
        # =================================================

        self.sidebar_status_label = QLabel(
            "Dashboard"
        )

        self.sidebar_status_label.setObjectName(
            "SidebarStatus"
        )

        self.sidebar_status_label.setContentsMargins(
            6,
            2,
            6,
            2,
        )

        sidebar_layout.addWidget(
            self.sidebar_status_label
        )

        # =================================================
        # PERFIL
        # =================================================

        self.profile_widget = (
            SidebarProfile()
        )

        self.profile_widget.clicked.connect(
            self.show_profiles
        )

        sidebar_layout.addWidget(
            self.profile_widget
        )

        # =================================================
        # BOTÕES
        # =================================================

        self.sidebar_buttons = [
            self.collection_button,
            self.dashboard_button,
            self.decks_button,
            self.explore_button,
            self.export_button,
            self.reports_button,
            self.settings_button,
        ]

        # =================================================
        # ADICIONAR SIDEBAR
        # =================================================

        main_layout.addWidget(
            self.sidebar
        )

        # =================================================
        # ÁREA DE CONTEÚDO
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
            0,
        )

        self.content_layout.setSpacing(
            0
        )

        main_layout.addWidget(
            self.content_widget,
            1,
        )

    # =====================================================
    # PRIMEIRA PÁGINA
    # =====================================================

    def _open_initial_page(
        self,
    ):

        profile = (
            self.profile_manager
            .get_active_profile()
        )

        self.active_profile = (
            profile
        )

        # =================================================
        # NÃO EXISTE PERFIL
        # =================================================

        if profile is None:

            self._enter_profile_setup()

            return

        # =================================================
        # EXISTE PERFIL
        # =================================================

        self._enter_normal_mode()

        self.show_dashboard()

    # =====================================================
    # MODO DE CONFIGURAÇÃO INICIAL
    # =====================================================

    def _enter_profile_setup(
        self,
    ):

        # =================================================
        # ESCONDER SIDEBAR
        # =================================================

        self.sidebar.hide()

        # =================================================
        # GARANTIR QUE O CONTEÚDO OCUPE A JANELA TODA
        # =================================================

        self.content_widget.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        # =================================================
        # PERFIS
        # =================================================

        page = self._get_profiles_page()

        # =================================================
        # MOSTRAR SOMENTE PERFIS
        # =================================================

        self._switch_page(
            page
        )

    # =====================================================
    # MODO NORMAL
    # =====================================================

    def _enter_normal_mode(
        self,
    ):

        self.sidebar.show()

        self.content_widget.setContentsMargins(
            0,
            0,
            0,
            0,
        )

    # =====================================================
    # CRIAR / OBTER PROFILES PAGE
    # =====================================================

    def _get_profiles_page(
        self,
    ):

        if self.profiles_page is None:

            try:

                self.profiles_page = (
                    ProfilesPage(
                        self,
                        self.profile_manager,
                    )
                )

            except TypeError:

                # Compatibilidade caso sua
                # ProfilesPage atual aceite
                # somente parent.

                self.profiles_page = (
                    ProfilesPage(
                        self
                    )
                )

            self.content_layout.addWidget(
                self.profiles_page
            )

            self._connect_profile_signals()

        return self.profiles_page

    # =====================================================
    # SINAIS DOS PERFIS
    # =====================================================

    def _connect_profile_signals(
        self,
    ):

        page = (
            self.profiles_page
        )

        if page is None:

            return

        # =================================================
        # PERFIL ATIVADO
        # =================================================

        signal = getattr(
            page,
            "profile_activated",
            None,
        )

        if signal is not None:

            try:

                signal.connect(
                    self._on_profile_activated
                )

            except (
                TypeError,
                RuntimeError,
            ):

                pass

        # =================================================
        # PERFIL CRIADO
        # =================================================

        signal = getattr(
            page,
            "profile_created",
            None,
        )

        if signal is not None:

            try:

                signal.connect(
                    self._on_profile_created
                )

            except (
                TypeError,
                RuntimeError,
            ):

                pass

        # =================================================
        # PERFIL ALTERADO
        # =================================================

        signal = getattr(
            page,
            "profile_changed",
            None,
        )

        if signal is not None:

            try:

                signal.connect(
                    self._on_profile_changed
                )

            except (
                TypeError,
                RuntimeError,
            ):

                pass

        # =================================================
        # PERFIL EXCLUÍDO
        # =================================================

        signal = getattr(
            page,
            "profile_deleted",
            None,
        )

        if signal is not None:

            try:

                signal.connect(
                    self._on_profile_deleted
                )

            except (
                TypeError,
                RuntimeError,
            ):

                pass

    # =====================================================
    # PERFIL ATIVADO
    # =====================================================

    def _on_profile_activated(
        self,
        profile,
    ):

        self.active_profile = (
            profile
        )

        self.update_sidebar_profile()

        # =================================================
        # SAIR DO PRIMEIRO LANÇAMENTO
        # =================================================

        self._enter_normal_mode()

        # =================================================
        # DASHBOARD
        # =================================================

        self.show_dashboard()

    # =====================================================
    # PERFIL CRIADO
    # =====================================================

    def _on_profile_created(
        self,
        profile,
    ):

        self.active_profile = (
            profile
        )

        self.update_sidebar_profile()

        # =================================================
        # SE FOI O PRIMEIRO PERFIL
        # =================================================

        self._enter_normal_mode()

        self.show_dashboard()

    # =====================================================
    # PERFIL ALTERADO
    # =====================================================

    # =====================================================
    # PERFIL ALTERADO
    # =====================================================

    def _on_profile_changed(
        self,
        profile,
    ):

        self.active_profile = (
            profile
        )

        self.update_sidebar_profile()

        print(
            "[MAIN WINDOW] "
            "Perfil alterado:"
        )

        print(
            f"  Nome: {profile.name}"
        )

        print(
            f"  Banco: "
            f"{profile.database_path}"
        )

        # =================================================
        # RECARREGAR PÁGINAS DEPENDENTES DO BANCO
        # =================================================

        self._reset_profile_pages()

        # =================================================
        # GARANTIR MODO NORMAL
        # =================================================

        self._enter_normal_mode()

        # =================================================
        # ABRIR DASHBOARD DO NOVO PERFIL
        # =================================================

        self.show_dashboard()

    # =====================================================
    # RESET DAS PÁGINAS DO PERFIL
    # =====================================================

    def _reset_profile_pages(
        self,
    ):

        profile_pages = (
            (
                "collection_page",
                self.collection_page,
            ),
            (
                "decks_page",
                self.decks_page,
            ),
            (
                "dashboard_page",
                self.dashboard_page,
            ),
            (
                "explore_page",
                self.explore_page,
            ),
            (
                "export_page",
                self.export_page,
            ),
            (
                "reports_page",
                self.reports_page,
            ),
        )

        for (
            attribute,
            page,
        ) in profile_pages:

            if page is None:
                continue

            try:
                page.hide()

            except Exception:
                pass

            try:
                page.setParent(
                    None
                )

            except Exception:
                pass

            try:
                page.deleteLater()

            except Exception:
                pass

            setattr(
                self,
                attribute,
                None,
            )

        self._dashboard_deck_signal_connected = False

        print(
            "[MAIN WINDOW] "
            "Páginas dependentes do perfil "
            "foram reinicializadas."
        )
    # =====================================================
    # PERFIL EXCLUÍDO
    # =====================================================

    def _on_profile_deleted(
        self,
        profile=None,
    ):

        active = (
            self.profile_manager
            .get_active_profile()
        )

        self.active_profile = (
            active
        )

        self.update_sidebar_profile()

        # =================================================
        # AINDA EXISTE PERFIL
        # =================================================

        if active is not None:

            self._enter_normal_mode()

            self.show_dashboard()

            return

        # =================================================
        # NÃO EXISTE MAIS PERFIL
        # =================================================

        self._enter_profile_setup()

    # =====================================================
    # ATUALIZAR PERFIL DA SIDEBAR
    # =====================================================

    def update_sidebar_profile(
        self,
    ):

        profile = (
            self.profile_manager
            .get_active_profile()
        )

        self.active_profile = (
            profile
        )

        self.profile_widget.set_profile(
            profile
        )

    # =====================================================
    # ATUALIZAR PÁGINAS EXISTENTES
    # =====================================================

    def _refresh_existing_pages(
        self,
    ):

        pages = [
            self.collection_page,
            self.decks_page,
            self.dashboard_page,
            self.profiles_page,
        ]

        for page in pages:

            if page is None:

                continue

            refresh = getattr(
                page,
                "refresh",
                None,
            )

            if not callable(
                refresh
            ):

                continue

            try:

                refresh()

            except Exception as error:

                print(
                    "[MAIN WINDOW] "
                    "Erro ao atualizar página:",
                    error,
                )

    # =====================================================
    # HELPERS SIDEBAR
    # =====================================================

    def _section_label(
        self,
        text,
    ):

        label = QLabel(
            text
        )

        label.setObjectName(
            "SidebarSectionLabel"
        )

        return label

    # =====================================================

    def _divider(
        self,
    ):

        divider = QFrame()

        divider.setObjectName(
            "SidebarDivider"
        )

        divider.setFixedHeight(
            1
        )

        return divider

    # =====================================================

    def _sidebar_button(
        self,
        text,
    ):

        button = QPushButton(
            text
        )

        button.setObjectName(
            "SidebarButton"
        )

        button.setCheckable(
            True
        )

        button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        # =================================================
        # COLEÇÃO
        # =================================================

        if (
            text == "Coleção"
            and COLLECTION_ICON_PATH.exists()
        ):

            button.setIcon(
                QIcon(
                    str(
                        COLLECTION_ICON_PATH
                    )
                )
            )

            button.setIconSize(
                QSize(
                    38,
                    38,
                )
            )

        if (
            text == "Dashboard"
            and DASHBOARD_ICON_PATH.exists()
        ):

            button.setIcon(
                QIcon(
                    str(
                        DASHBOARD_ICON_PATH
                    )
                )
            )

            button.setIconSize(
                QSize(
                    38,
                    38,
                )
            )

        if (
            text == "Explorar"
            and EXPLORAR_ICON_PATH.exists()
        ):

            button.setIcon(
                QIcon(
                    str(
                        EXPLORAR_ICON_PATH
                    )
                )
            )

            button.setIconSize(
                QSize(
                    38,
                    38,
                )
            )



        # =================================================
        # DECKS
        # =================================================

        elif (
            text == "Decks"
            and DECKS_ICON_PATH.exists()
        ):

            button.setIcon(
                QIcon(
                    str(
                        DECKS_ICON_PATH
                    )
                )
            )

            button.setIconSize(
                QSize(
                    38,
                    38,
                )
            )

        return button



    # =====================================================
    # NAVEGAÇÃO
    # =====================================================

    def _check_button(
        self,
        active,
    ):

        for button in (
            self.sidebar_buttons
        ):

            button.setChecked(
                button is active
            )

    # =====================================================

    def _switch_page(
        self,
        page,
    ):

        if page is None:

            return

        # =================================================
        # MOSTRAR
        # =================================================

        page.show()

        page.raise_()

        # =================================================
        # ESCONDER OUTRAS
        # =================================================

        pages = (
            self.profiles_page,

            self.collection_page,
            self.decks_page,
            self.dashboard_page,
            self.settings_page,

            self.explore_page,
            self.export_page,
            self.reports_page,
        )

        for widget in pages:

            if (
                widget is not None
                and widget is not page
            ):

                widget.hide()

    # =====================================================

    def _get_page(
        self,
        attribute,
        factory,
    ):

        page = getattr(
            self,
            attribute,
            None,
        )

        if page is None:

            page = factory(
                self
            )

            setattr(
                self,
                attribute,
                page,
            )

            self.content_layout.addWidget(
                page
            )

        return page

    # =====================================================
    # PERFIS
    # =====================================================

    def show_profiles(
        self,
    ):

        page = (
            self._get_profiles_page()
        )

        # =================================================
        # ATUALIZAR
        # =================================================

        refresh = getattr(
            page,
            "refresh",
            None,
        )

        if callable(
            refresh
        ):

            try:

                refresh()

            except Exception as error:

                print(
                    "[PROFILES] "
                    "Erro ao atualizar:",
                    error,
                )

        # =================================================
        # NÃO É PRIMEIRO LANÇAMENTO
        # =================================================

        if self.active_profile is not None:

            self._enter_normal_mode()

            self._check_button(
                None
            )

            self.sidebar_status_label.setText(
                "Perfis"
            )

        # =================================================
        # MOSTRAR
        # =================================================

        self._switch_page(
            page
        )

    # =====================================================
    # VERIFICAR PERFIL
    # =====================================================

    def _require_profile(
        self,
    ):

        profile = (
            self.profile_manager
            .get_active_profile()
        )

        if profile is not None:

            self.active_profile = (
                profile
            )

            return True

        # =================================================
        # SEM PERFIL
        # =================================================

        self._enter_profile_setup()

        return False

    # =====================================================
    # COLEÇÃO
    # =====================================================

    def show_collection(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.collection_button
        )

        self.sidebar_status_label.setText(
            "Coleção"
        )

        self._get_page(
            "collection_page",
            CollectionPage,
        )

        self._switch_page(
            self.collection_page
        )

    # =====================================================
    # DASHBOARD
    # =====================================================

    def show_dashboard(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.dashboard_button
        )

        self.sidebar_status_label.setText(
            "Dashboard"
        )

        self._get_page(
            "dashboard_page",
            DashboardPage,
        )

        # =================================================
        # CONECTAR SINAL DO DASHBOARD
        # =================================================

        if not self._dashboard_deck_signal_connected:

            try:

                self.dashboard_page.deck_clicked.connect(
                    self._open_dashboard_deck
                )

                self._dashboard_deck_signal_connected = True

            except (
                    TypeError,
                    RuntimeError,
            ):

                pass

        # =================================================
        # ATUALIZAR DASHBOARD
        # =================================================

        refresh = getattr(
            self.dashboard_page,
            "refresh",
            None,
        )

        if callable(
            refresh
        ):

            try:

                refresh()

            except Exception as error:

                print(
                    "[DASHBOARD] "
                    "Erro ao atualizar:",
                    error,
                )

        self._switch_page(
            self.dashboard_page
        )

    # =====================================================
    # ABRIR DECK PELO DASHBOARD
    # =====================================================

    def _open_dashboard_deck(
            self,
            deck_id,
    ):

        if not self._require_profile():
            return

        self.show_decks()

        try:

            self.decks_page.open_deck(
                int(deck_id)
            )

        except Exception as error:

            print(
                "[DASHBOARD] "
                "Erro ao abrir deck:",
                error,
            )

    # =====================================================
    # DECKS
    # =====================================================

    def show_decks(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.decks_button
        )

        self.sidebar_status_label.setText(
            "Decks"
        )

        self._get_page(
            "decks_page",
            DecksPage,
        )

        self._switch_page(
            self.decks_page
        )

    # =====================================================
    # EXPLORAR
    # =====================================================

    def show_explore(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.explore_button
        )

        self.sidebar_status_label.setText(
            "Explorar"
        )

        self._get_page(
            "explore_page",
            self._make_placeholder,
        )

        self._switch_page(
            self.explore_page
        )

    # =====================================================
    # EXPORTAR
    # =====================================================

    def show_export(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.export_button
        )

        self.sidebar_status_label.setText(
            "Exportar"
        )

        self._get_page(
            "export_page",
            self._make_placeholder,
        )

        self._switch_page(
            self.export_page
        )

    # =====================================================
    # RELATÓRIOS
    # =====================================================

    def show_reports(
        self,
    ):

        if not self._require_profile():

            return

        self._check_button(
            self.reports_button
        )

        self.sidebar_status_label.setText(
            "Relatórios"
        )

        self._get_page(
            "reports_page",
            self._make_placeholder,
        )

        self._switch_page(
            self.reports_page
        )

    # =====================================================
    # CONFIGURAÇÕES
    # =====================================================

    def show_settings(
        self,
    ):

        # Configurações pode ser aberta
        # mesmo sem perfil.

        self._check_button(
            self.settings_button
        )

        self.sidebar_status_label.setText(
            "Configurações"
        )

        self._get_page(
            "settings_page",
            SettingsPage,
        )

        self._switch_page(
            self.settings_page
        )

    # =====================================================
    # PLACEHOLDER
    # =====================================================

    def _make_placeholder(
        self,
        parent=None,
    ):

        page = QWidget(
            parent
        )

        layout = QVBoxLayout(
            page
        )

        layout.setContentsMargins(
            32,
            28,
            32,
            28,
        )

        label = QLabel(
            "Em breve."
        )

        label.setObjectName(
            "DeckEmptyState"
        )

        label.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            label
        )

        return page
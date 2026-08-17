"""
PROFILES PAGE
=============

Página de gerenciamento dos perfis do Magic Collection.

Responsabilidades:

- Exibir os perfis existentes.
- Mostrar o perfil ativo.
- Criar novos perfis.
- Renomear perfis.
- Alterar avatar.
- Excluir perfis.
- Trocar de perfil.
- Detectar save antigo.
- Permitir registrar o save antigo como perfil.
- Tela especial para primeiro lançamento.

IMPORTANTE:

Esta página NÃO acessa collection.db diretamente.

Toda comunicação com os dados dos perfis acontece através de:

    profile_manager.py

O banco da coleção continua intocado nesta etapa.
"""

from __future__ import annotations


# =========================================================
# IMPORTS
# =========================================================

from pathlib import Path
from typing import Optional


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
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QSizePolicy,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
)


# =========================================================
# PROFILE MANAGER
# =========================================================

from profile_manager import (
    Profile,
    ProfileManager,
    ProfileManagerError,
    ProfileAlreadyExistsError,
    InvalidProfileNameError,
)


# =========================================================
# TEMA
# =========================================================

try:

    from ui.theme import DARK_THEME

except Exception:

    DARK_THEME = ""


# =========================================================
# CAMINHOS
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
    / "icon_app.png"
)


# =========================================================
# ESTILO ESPECÍFICO DOS PERFIS
# =========================================================
#
# O tema geral continua vindo do theme.py.
#
# Este bloco existe apenas para garantir que a página
# mantenha a identidade visual mesmo antes de adicionarmos
# todos os seletores ao theme.qss.
#
# =========================================================

PROFILE_PAGE_STYLE = """

/* ===================================================== */
/* BASE                                                   */
/* ===================================================== */

QWidget#ProfilesPage {
    background: #0D0F14;
    color: #F1F3F5;
}

QScrollArea#ProfilesScroll {
    background: transparent;
    border: none;
}

QWidget#ProfilesScrollContent {
    background: transparent;
}


/* ===================================================== */
/* CABEÇALHO                                              */
/* ===================================================== */

QLabel#ProfilesTitle {
    color: #F3F4F6;
    font-size: 27px;
    font-weight: 700;
}

QLabel#ProfilesSubtitle {
    color: #7F8794;
    font-size: 12px;
}

QLabel#ProfilesSectionTitle {
    color: #E7E9ED;
    font-size: 14px;
    font-weight: 700;
}

QLabel#ProfilesSectionHint {
    color: #737B88;
    font-size: 11px;
}


/* ===================================================== */
/* BOTÕES                                                 */
/* ===================================================== */

QPushButton#PrimaryButton {
    background: #C9A84E;
    color: #101116;
    border: none;
    border-radius: 7px;
    padding: 9px 16px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#PrimaryButton:hover {
    background: #D8B961;
}

QPushButton#PrimaryButton:pressed {
    background: #B99743;
}


QPushButton#SecondaryButton {
    background: #1A1D23;
    color: #D8DCE3;
    border: 1px solid #2B3039;
    border-radius: 7px;
    padding: 8px 14px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#SecondaryButton:hover {
    background: #22262E;
    border-color: #3A414D;
}

QPushButton#SecondaryButton:pressed {
    background: #181B20;
}


QPushButton#DangerButton {
    background: #20171A;
    color: #D98B91;
    border: 1px solid #43252A;
    border-radius: 7px;
    padding: 8px 14px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#DangerButton:hover {
    background: #2A1B1F;
    border-color: #66343B;
}


/* ===================================================== */
/* CARD DO PERFIL ATIVO                                   */
/* ===================================================== */

QFrame#ActiveProfileCard {
    background: #15181D;
    border: 1px solid #3A3430;
    border-radius: 12px;
}


QFrame#ActiveProfileAccent {
    background: #C9A84E;
    border-radius: 2px;
}


QLabel#ActiveBadge {
    background: #302918;
    color: #D9B75C;
    border: 1px solid #5B4A27;
    border-radius: 5px;
    padding: 4px 8px;
    font-size: 9px;
    font-weight: 700;
}


QLabel#ActiveProfileName {
    color: #F5F5F5;
    font-size: 20px;
    font-weight: 700;
}


QLabel#ActiveProfileInfo {
    color: #7F8794;
    font-size: 11px;
}


QLabel#ActiveProfileDatabase {
    color: #626A77;
    font-size: 9px;
}


/* ===================================================== */
/* AVATAR                                                 */
/* ===================================================== */

QLabel#ProfileAvatar {
    background: #242932;
    color: #D5B45C;
    border: 1px solid #3A414C;
    border-radius: 38px;
    font-size: 22px;
    font-weight: 700;
}


QLabel#ProfileAvatarLarge {
    background: #242932;
    color: #D5B45C;
    border: 1px solid #4A4335;
    border-radius: 48px;
    font-size: 28px;
    font-weight: 700;
}


/* ===================================================== */
/* CARDS DOS OUTROS PERFIS                                */
/* ===================================================== */

QFrame#ProfileCard {
    background: #14171C;
    border: 1px solid #272C34;
    border-radius: 10px;
}


QFrame#ProfileCard:hover {
    background: #191D23;
    border-color: #3B424D;
}


QLabel#ProfileCardName {
    color: #E7E9ED;
    font-size: 13px;
    font-weight: 700;
}


QLabel#ProfileCardInfo {
    color: #747C89;
    font-size: 10px;
}


QLabel#LegacyBadge {
    background: #252116;
    color: #C9A84E;
    border: 1px solid #4B4026;
    border-radius: 4px;
    padding: 3px 6px;
    font-size: 8px;
    font-weight: 700;
}


/* ===================================================== */
/* SAVE ANTIGO                                            */
/* ===================================================== */

QFrame#LegacyBanner {
    background: #15181D;
    border: 1px solid #3D3524;
    border-radius: 10px;
}


QLabel#LegacyTitle {
    color: #E4C66D;
    font-size: 13px;
    font-weight: 700;
}


QLabel#LegacyText {
    color: #858C97;
    font-size: 10px;
}


QLabel#LegacyPath {
    color: #626A76;
    font-size: 9px;
}


/* ===================================================== */
/* PRIMEIRO LANÇAMENTO                                    */
/* ===================================================== */

QFrame#WelcomeCard {
    background: #15181D;
    border: 1px solid #2A3039;
    border-radius: 14px;
}


QLabel#WelcomeTitle {
    color: #F2F3F5;
    font-size: 25px;
    font-weight: 700;
}


QLabel#WelcomeSubtitle {
    color: #7E8793;
    font-size: 12px;
}


QLabel#WelcomeIcon {
    background: #242932;
    color: #D1B25A;
    border: 1px solid #3C414B;
    border-radius: 42px;
    font-size: 28px;
    font-weight: 700;
}


/* ===================================================== */
/* ESTADO VAZIO                                           */
/* ===================================================== */

QLabel#EmptyTitle {
    color: #DDE1E6;
    font-size: 16px;
    font-weight: 700;
}


QLabel#EmptyText {
    color: #737B87;
    font-size: 11px;
}


/* ===================================================== */
/* INPUT                                                  */
/* ===================================================== */

QLineEdit#ProfileNameInput {
    background: #101318;
    color: #E8EAED;
    border: 1px solid #303640;
    border-radius: 7px;
    padding: 9px 11px;
    selection-background-color: #6C5A2B;
}

QLineEdit#ProfileNameInput:focus {
    border-color: #C9A84E;
}


/* ===================================================== */
/* DIÁLOGOS                                               */
/* ===================================================== */

QDialog#ProfileDialog {
    background: #12151A;
}

QLabel#DialogTitle {
    color: #F0F2F4;
    font-size: 17px;
    font-weight: 700;
}

QLabel#DialogSubtitle {
    color: #7B838F;
    font-size: 10px;
}

"""


# =========================================================
# HELPERS
# =========================================================

def _initials(
    name: str,
) -> str:
    """
    Cria iniciais para o avatar.

    Exemplos:

        Minha Coleção -> MC
        Aldrin -> A
        Magic Collection -> MC
    """

    words = [
        word.strip()
        for word in str(
            name
        ).split()
        if word.strip()
    ]

    if not words:

        return "?"

    if len(words) == 1:

        return words[0][0].upper()

    return (
        words[0][0]
        + words[-1][0]
    ).upper()


def _format_date(
    value: Optional[str],
) -> str:

    if not value:

        return "Nunca utilizado"

    try:

        from datetime import datetime

        date = datetime.fromisoformat(
            value
        )

        return date.strftime(
            "%d/%m/%Y às %H:%M"
        )

    except Exception:

        return str(value)


def _format_database_size(
    path: Path,
) -> str:

    try:

        if not path.exists():

            return "Banco não encontrado"

        size = path.stat().st_size

        if size < 1024:

            return f"{size} B"

        if size < 1024 * 1024:

            return f"{size / 1024:.1f} KB"

        return (
            f"{size / (1024 * 1024):.1f} MB"
        )

    except OSError:

        return "Tamanho indisponível"


# =========================================================
# PROFILE DIALOG
# =========================================================

class ProfileDialog(
    QDialog
):
    """
    Dialog reutilizável para criação/edição de perfil.
    """

    def __init__(
        self,
        parent=None,
        title="Novo perfil",
        subtitle=(
            "Crie um perfil para organizar "
            "uma coleção separadamente."
        ),
        initial_name="",
    ):

        super().__init__(
            parent
        )

        self.setObjectName(
            "ProfileDialog"
        )

        self.setWindowTitle(
            title
        )

        self.setModal(
            True
        )

        self.setMinimumWidth(
            430
        )

        self.setStyleSheet(
            PROFILE_PAGE_STYLE
        )

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        layout = QVBoxLayout(
            self
        )

        layout.setContentsMargins(
            24,
            24,
            24,
            20,
        )

        layout.setSpacing(
            14
        )

        # -------------------------------------------------
        # Título
        # -------------------------------------------------

        title_label = QLabel(
            title
        )

        title_label.setObjectName(
            "DialogTitle"
        )

        layout.addWidget(
            title_label
        )

        # -------------------------------------------------
        # Subtítulo
        # -------------------------------------------------

        subtitle_label = QLabel(
            subtitle
        )

        subtitle_label.setObjectName(
            "DialogSubtitle"
        )

        subtitle_label.setWordWrap(
            True
        )

        layout.addWidget(
            subtitle_label
        )

        # -------------------------------------------------
        # Nome
        # -------------------------------------------------

        form = QFormLayout()

        form.setSpacing(
            8
        )

        self.name_input = QLineEdit()

        self.name_input.setObjectName(
            "ProfileNameInput"
        )

        self.name_input.setPlaceholderText(
            "Ex.: Minha Coleção"
        )

        self.name_input.setText(
            initial_name
        )

        self.name_input.setMaxLength(
            15
        )

        form.addRow(
            "Nome:",
            self.name_input
        )

        layout.addLayout(
            form
        )

        # -------------------------------------------------
        # Botões
        # -------------------------------------------------

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )

        buttons.accepted.connect(
            self._validate_and_accept
        )

        buttons.rejected.connect(
            self.reject
        )

        ok_button = buttons.button(
            QDialogButtonBox.StandardButton.Ok
        )

        if ok_button:

            ok_button.setObjectName(
                "PrimaryButton"
            )

        cancel_button = buttons.button(
            QDialogButtonBox.StandardButton.Cancel
        )

        if cancel_button:

            cancel_button.setObjectName(
                "SecondaryButton"
            )

        layout.addWidget(
            buttons
        )

        self.name_input.selectAll()

    # =====================================================
    # VALIDAR
    # =====================================================

    def _validate_and_accept(
        self,
    ):

        name = (
            self.name_input
            .text()
            .strip()
        )

        if not name:

            QMessageBox.warning(
                self,
                "Nome inválido",
                "Digite um nome para o perfil.",
            )

            self.name_input.setFocus()

            return

        self.accept()

    # =====================================================
    # NOME
    # =====================================================

    def get_name(
        self,
    ) -> str:

        return (
            self.name_input
            .text()
            .strip()
        )


# =========================================================
# PROFILE CARD
# =========================================================

class ProfileCard(
    QFrame
):
    """
    Card de um perfil não ativo.
    """

    clicked = Signal(object)

    rename_requested = Signal(object)

    avatar_requested = Signal(object)

    delete_requested = Signal(object)

    def __init__(
        self,
        profile: Profile,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.profile = profile

        self.setObjectName(
            "ProfileCard"
        )

        self.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.setMinimumHeight(
            105
        )

        self.setMaximumHeight(
            120
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # -------------------------------------------------
        # Layout principal
        # -------------------------------------------------

        main_layout = QVBoxLayout(
            self
        )

        main_layout.setContentsMargins(
            12,
            10,
            12,
            10,
        )

        main_layout.setSpacing(
            8
        )

        # -------------------------------------------------
        # Topo
        # -------------------------------------------------

        top = QHBoxLayout()

        top.setSpacing(
            12
        )

        # Avatar
        self.avatar = QLabel(
            _initials(
                profile.name
            )
        )

        self.avatar.setObjectName(
            "ProfileAvatar"
        )

        self.avatar.setFixedSize(
            58,
            58
        )

        self.avatar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._set_avatar(
            profile.avatar_path
        )

        top.addWidget(
            self.avatar
        )

        # Informações
        info = QVBoxLayout()

        info.setSpacing(
            3
        )

        # -------------------------------------------------
        # Nome + badge
        # -------------------------------------------------

        name_row = QHBoxLayout()

        name_row.setSpacing(
            8
        )

        name = QLabel(
            profile.name
        )

        name.setObjectName(
            "ProfileCardName"
        )

        name.setWordWrap(
            True
        )

        name_row.addWidget(
            name
        )

        if profile.is_legacy:
            legacy = QLabel(
                "SAVE EXISTENTE"
            )

            legacy.setObjectName(
                "LegacyBadge"
            )

            legacy.setSizePolicy(
                QSizePolicy.Policy.Maximum,
                QSizePolicy.Policy.Fixed,
            )

            name_row.addWidget(
                legacy,
                0,
                Qt.AlignmentFlag.AlignVCenter
            )

        name_row.addStretch()

        info.addLayout(
            name_row
        )

        self.info_label = QLabel()

        self.info_label.setObjectName(
            "ProfileCardInfo"
        )

        info.addWidget(
            self.info_label
        )



        top.addLayout(
            info,
            1
        )

        main_layout.addLayout(
            top
        )



        # -------------------------------------------------
        # Botões
        # -------------------------------------------------

        buttons = QHBoxLayout()

        buttons.setContentsMargins(
            0,
            0,
            0,
            0
        )

        buttons.setSpacing(
            6
        )



        buttons.addStretch()

        avatar_button = QPushButton(
            "Avatar"
        )

        avatar_button.setObjectName(
            "SecondaryButton"
        )

        avatar_button.clicked.connect(
            lambda:
            self.avatar_requested.emit(
                self.profile
            )
        )

        buttons.addWidget(
            avatar_button
        )

        rename_button = QPushButton(
            "Renomear"
        )

        rename_button.setObjectName(
            "SecondaryButton"
        )

        rename_button.clicked.connect(
            lambda:
            self.rename_requested.emit(
                self.profile
            )
        )

        buttons.addWidget(
            rename_button
        )

        delete_button = QPushButton(
            "Excluir"
        )

        delete_button.setObjectName(
            "DangerButton"
        )

        delete_button.clicked.connect(
            lambda:
            self.delete_requested.emit(
                self.profile
            )
        )

        buttons.addWidget(
            delete_button
        )

        main_layout.addLayout(
            buttons
        )

        self._refresh_info()

    # =====================================================
    # AVATAR
    # =====================================================

    def _set_avatar(
        self,
        avatar_path: Optional[Path],
    ):

        if (
            avatar_path
            and avatar_path.exists()
        ):

            pixmap = QPixmap(
                str(
                    avatar_path
                )
            )

            if not pixmap.isNull():

                pixmap = pixmap.scaled(
                    58,
                    58,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self.avatar.setPixmap(
                    pixmap
                )

                return

        self.avatar.setText(
            _initials(
                self.profile.name
            )
        )

    # =====================================================
    # INFO
    # =====================================================

    def _refresh_info(
        self,
    ):

        size = _format_database_size(
            self.profile.database_path
        )

        last_opened = _format_date(
            self.profile.last_opened_at
        )

        self.info_label.setText(
            f"{size}  •  {last_opened}"
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

            self.clicked.emit(
                self.profile
            )

        super().mousePressEvent(
            event
        )


# =========================================================
# ACTIVE PROFILE CARD
# =========================================================

class ActiveProfileCard(
    QFrame
):
    """
    Card maior do perfil atualmente ativo.
    """

    rename_requested = Signal(object)

    avatar_requested = Signal(object)

    def __init__(
        self,
        profile: Profile,
        parent=None,
    ):

        super().__init__(
            parent
        )

        self.profile = profile

        self.setObjectName(
            "ActiveProfileCard"
        )

        self.setFixedHeight(
            180
        )

        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        # -------------------------------------------------
        # Layout
        # -------------------------------------------------

        main = QHBoxLayout(
            self
        )

        main.setContentsMargins(
            18,
            18,
            18,
            18,
        )

        main.setSpacing(
            16
        )

        # -------------------------------------------------
        # Avatar
        # -------------------------------------------------

        self.avatar = QLabel(
            _initials(
                profile.name
            )
        )

        self.avatar.setObjectName(
            "ProfileAvatarLarge"
        )

        self.avatar.setFixedSize(
            96,
            96
        )

        self.avatar.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self._set_avatar(
            profile.avatar_path
        )

        main.addWidget(
            self.avatar,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        # -------------------------------------------------
        # Informações
        # -------------------------------------------------

        info = QVBoxLayout()

        info.setSpacing(
            5
        )

        badge = QLabel(
            "PERFIL ATIVO"
        )

        badge.setObjectName(
            "ActiveBadge"
        )

        badge.setSizePolicy(
            QSizePolicy.Policy.Maximum,
            QSizePolicy.Policy.Fixed,
        )

        info.addWidget(
            badge
        )

        name = QLabel(
            profile.name
        )

        name.setObjectName(
            "ActiveProfileName"
        )

        name.setWordWrap(
            True
        )

        info.addWidget(
            name
        )

        info_label = QLabel(
            "Este é o perfil utilizado atualmente."
        )

        info_label.setObjectName(
            "ActiveProfileInfo"
        )

        info.addWidget(
            info_label
        )

        database_label = QLabel(
            str(
                profile.database_path
            )
        )

        database_label.setObjectName(
            "ActiveProfileDatabase"
        )

        database_label.setWordWrap(
            True
        )

        info.addWidget(
            database_label
        )

        info.addStretch()

        # -------------------------------------------------
        # Botões
        # -------------------------------------------------

        buttons = QHBoxLayout()

        buttons.setSpacing(
            7
        )

        avatar_button = QPushButton(
            "Alterar avatar"
        )

        avatar_button.setObjectName(
            "SecondaryButton"
        )

        avatar_button.clicked.connect(
            lambda:
            self.avatar_requested.emit(
                self.profile
            )
        )

        buttons.addWidget(
            avatar_button
        )

        rename_button = QPushButton(
            "Renomear"
        )

        rename_button.setObjectName(
            "SecondaryButton"
        )

        rename_button.clicked.connect(
            lambda:
            self.rename_requested.emit(
                self.profile
            )
        )

        buttons.addWidget(
            rename_button
        )

        buttons.addStretch()

        info.addLayout(
            buttons
        )

        main.addLayout(
            info,
            1
        )

    # =====================================================
    # AVATAR
    # =====================================================

    def _set_avatar(
        self,
        avatar_path: Optional[Path],
    ):

        if (
            avatar_path
            and avatar_path.exists()
        ):

            pixmap = QPixmap(
                str(
                    avatar_path
                )
            )

            if not pixmap.isNull():

                pixmap = pixmap.scaled(
                    96,
                    96,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                )

                self.avatar.setPixmap(
                    pixmap
                )

                return

        self.avatar.setText(
            _initials(
                self.profile.name
            )
        )


# =========================================================
# PROFILES PAGE
# =========================================================

class ProfilesPage(
    QWidget
):
    """
    Página principal dos perfis.
    """

    # -----------------------------------------------------
    # Sinais
    # -----------------------------------------------------

    profile_activated = Signal(object)

    profile_created = Signal(object)

    profile_changed = Signal(object)

    profile_deleted = Signal(object)

    profiles_updated = Signal()

    # =====================================================
    # INIT
    # =====================================================

    def __init__(
        self,
        parent=None,
        profile_manager=None,
    ):

        super().__init__(
            parent
        )

        self.setObjectName(
            "ProfilesPage"
        )

        # -------------------------------------------------
        # Manager
        # -------------------------------------------------

        if profile_manager is None:

            self.manager = ProfileManager()

        else:

            self.manager = (
                profile_manager
            )

        # -------------------------------------------------
        # Estado
        # -------------------------------------------------

        self.active_profile = None

        self.profile_cards = []

        # -------------------------------------------------
        # Estilo
        # -------------------------------------------------

        self.setStyleSheet(
            PROFILE_PAGE_STYLE
        )

        # -------------------------------------------------
        # UI
        # -------------------------------------------------

        self._build_ui()

        self.refresh()

    # =====================================================
    # BUILD UI
    # =====================================================

    def _build_ui(
        self,
    ):

        root = QVBoxLayout(
            self
        )

        root.setContentsMargins(
            26,
            24,
            26,
            20,
        )

        root.setSpacing(
            18
        )

        # =================================================
        # CABEÇALHO
        # =================================================

        self.header_widget = QWidget()

        header = QHBoxLayout(
            self.header_widget
        )

        header.setSpacing(
            12
        )

        # -------------------------------------------------
        # Títulos
        # -------------------------------------------------

        title_container = QVBoxLayout()

        title_container.setSpacing(
            3
        )

        title = QLabel(
            "Perfis"
        )

        title.setObjectName(
            "ProfilesTitle"
        )

        title_container.addWidget(
            title
        )

        subtitle = QLabel(
            "Gerencie suas coleções e seus saves."
        )

        subtitle.setObjectName(
            "ProfilesSubtitle"
        )

        title_container.addWidget(
            subtitle
        )

        header.addLayout(
            title_container,
            1
        )

        # -------------------------------------------------
        # Novo perfil
        # -------------------------------------------------

        self.new_profile_button = QPushButton(
            "+ Novo perfil"
        )

        self.new_profile_button.setObjectName(
            "PrimaryButton"
        )

        self.new_profile_button.setCursor(
            Qt.CursorShape.PointingHandCursor
        )

        self.new_profile_button.clicked.connect(
            self.create_profile
        )

        header.addWidget(
            self.new_profile_button,
            0,
            Qt.AlignmentFlag.AlignTop
        )

        root.addWidget(
            self.header_widget
        )

        # =================================================
        # SCROLL
        # =================================================

        self.scroll = QScrollArea()

        self.scroll.setObjectName(
            "ProfilesScroll"
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

        self.scroll_content = QWidget()

        self.scroll_content.setObjectName(
            "ProfilesScrollContent"
        )

        self.scroll_content.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        self.scroll_layout = QVBoxLayout(
            self.scroll_content
        )

        self.scroll_layout.setContentsMargins(
            0,
            0,
            8,
            20,
        )

        self.scroll_layout.setSpacing(
            18
        )

        self.scroll_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        self.scroll.setWidget(
            self.scroll_content
        )

        root.addWidget(
            self.scroll,
            1
        )

    # =====================================================
    # REFRESH
    # =====================================================

    def refresh(
        self,
    ):

        self._clear_content()

        state = (
            self.manager.get_startup_state()
        )

        profiles = (
            state.get(
                "profiles",
                []
            )
        )

        active = (
            state.get(
                "active_profile"
            )
        )

        legacy_database = (
            state.get(
                "legacy_database"
            )
        )

        self.active_profile = active

        # -------------------------------------------------
        # PRIMEIRO LANÇAMENTO
        # -------------------------------------------------

        if not profiles:
            self.header_widget.hide()

            self.scroll_layout.setAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self._build_first_launch(
                legacy_database
            )

            return

        self.header_widget.show()

        self.scroll_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop
        )
        # -------------------------------------------------
        # PERFIL ATIVO
        # -------------------------------------------------

        if active:

            self._build_active_profile(
                active
            )

        # -------------------------------------------------
        # SAVE ANTIGO
        # -------------------------------------------------

        if legacy_database:

            # Só mostramos o aviso se ainda houver
            # um save legado que não foi registrado.

            legacy_registered = any(
                profile.is_legacy
                and (
                    Path(
                        profile.database_path
                    ).resolve()
                    == Path(
                        legacy_database
                    ).resolve()
                )
                for profile in profiles
            )

            if not legacy_registered:

                self._build_legacy_banner(
                    legacy_database
                )

        # -------------------------------------------------
        # OUTROS PERFIS
        # -------------------------------------------------

        others = [
            profile
            for profile in profiles
            if (
                active is None
                or profile.id
                != active.id
            )
        ]

        if others:

            self._build_other_profiles(
                others
            )

    # =====================================================
    # LIMPAR
    # =====================================================

    def _clear_content(
        self,
    ):

        while (
            self.scroll_layout.count()
        ):

            item = (
                self.scroll_layout.takeAt(
                    0
                )
            )

            widget = (
                item.widget()
            )

            if widget:

                widget.deleteLater()

        self.profile_cards.clear()

    # =====================================================
    # PRIMEIRO LANÇAMENTO
    # =====================================================

    def _build_first_launch(
        self,
        legacy_database: Optional[Path],
    ):

        container = QFrame()

        container.setObjectName(
            "WelcomeCard"
        )

        container.setFixedSize(
            720,
            330
        )

        container.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )

        container_layout = QVBoxLayout(
            container
        )

        container_layout.setContentsMargins(
            40,
            40,
            40,
            40,
        )

        container_layout.setSpacing(
            14
        )

        container_layout.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        # -------------------------------------------------
        # Ícone
        # -------------------------------------------------

        icon = QLabel(
            "M"
        )

        icon.setObjectName(
            "WelcomeIcon"
        )

        icon.setFixedSize(
            84,
            84
        )

        icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        container_layout.addWidget(
            icon,
            0,
            Qt.AlignmentFlag.AlignCenter
        )

        # -------------------------------------------------
        # Título
        # -------------------------------------------------

        title = QLabel(
            "Bem-vindo ao Magic Collection"
        )

        title.setObjectName(
            "WelcomeTitle"
        )

        title.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        container_layout.addWidget(
            title
        )

        # -------------------------------------------------
        # Texto
        # -------------------------------------------------

        if legacy_database:

            text = QLabel(
                "Encontramos uma coleção existente "
                "neste computador."
            )

        else:

            text = QLabel(
                "Crie seu primeiro perfil para começar "
                "a organizar sua coleção."
            )

        text.setObjectName(
            "WelcomeSubtitle"
        )

        text.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        text.setWordWrap(
            True
        )

        container_layout.addWidget(
            text
        )

        container_layout.addSpacing(
            8
        )

        # -------------------------------------------------
        # Botões
        # -------------------------------------------------

        buttons = QHBoxLayout()

        buttons.setSpacing(
            8
        )

        buttons.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        if legacy_database:

            use_old_button = QPushButton(
                "Usar coleção existente"
            )

            use_old_button.setObjectName(
                "PrimaryButton"
            )

            use_old_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            use_old_button.clicked.connect(
                lambda:
                self.register_legacy_profile(
                    legacy_database
                )
            )

            buttons.addWidget(
                use_old_button
            )

            new_button = QPushButton(
                "Criar novo perfil"
            )

            new_button.setObjectName(
                "SecondaryButton"
            )

            new_button.clicked.connect(
                self.create_profile
            )

            buttons.addWidget(
                new_button
            )

        else:

            new_button = QPushButton(
                "+ Criar meu primeiro perfil"
            )

            new_button.setObjectName(
                "PrimaryButton"
            )

            new_button.setCursor(
                Qt.CursorShape.PointingHandCursor
            )

            new_button.clicked.connect(
                self.create_profile
            )

            buttons.addWidget(
                new_button
            )

        container_layout.addLayout(
            buttons
        )

        self.scroll_layout.addStretch(
            1
        )

        self.scroll_layout.addWidget(
            container,
            0,
            Qt.AlignmentFlag.AlignCenter
        )

        self.scroll_layout.addStretch(
            1
        )

    # =====================================================
    # PERFIL ATIVO
    # =====================================================

    def _build_active_profile(
        self,
        profile: Profile,
    ):

        title = QLabel(
            "Perfil atual"
        )

        title.setObjectName(
            "ProfilesSectionTitle"
        )

        self.scroll_layout.addWidget(
            title
        )

        card = ActiveProfileCard(
            profile
        )

        card.rename_requested.connect(
            self.rename_profile
        )

        card.avatar_requested.connect(
            self.change_avatar
        )

        self.scroll_layout.addWidget(
            card
        )

    # =====================================================
    # SAVE LEGADO
    # =====================================================

    def _build_legacy_banner(
        self,
        database_path: Path,
    ):

        banner = QFrame()

        banner.setObjectName(
            "LegacyBanner"
        )


        layout = QHBoxLayout(
            banner
        )

        layout.setContentsMargins(
            16,
            14,
            16,
            14,
        )

        layout.setSpacing(
            12
        )

        # -------------------------------------------------
        # Ícone
        # -------------------------------------------------

        icon = QLabel(
            "!"
        )

        icon.setObjectName(
            "WelcomeIcon"
        )

        icon.setFixedSize(
            42,
            42
        )

        icon.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )

        layout.addWidget(
            icon
        )

        # -------------------------------------------------
        # Informações
        # -------------------------------------------------

        info = QVBoxLayout()

        info.setSpacing(
            3
        )

        title = QLabel(
            "Coleção antiga encontrada"
        )

        title.setObjectName(
            "LegacyTitle"
        )

        info.addWidget(
            title
        )

        text = QLabel(
            "Seu save antigo ainda não está associado "
            "a um perfil."
        )

        text.setObjectName(
            "LegacyText"
        )

        info.addWidget(
            text
        )

        path_label = QLabel(
            str(
                database_path
            )
        )

        path_label.setObjectName(
            "LegacyPath"
        )

        path_label.setWordWrap(
            True
        )

        info.addWidget(
            path_label
        )

        layout.addLayout(
            info,
            1
        )

        # -------------------------------------------------
        # Botão
        # -------------------------------------------------

        button = QPushButton(
            "Usar este save"
        )

        button.setObjectName(
            "PrimaryButton"
        )

        button.clicked.connect(
            lambda:
            self.register_legacy_profile(
                database_path
            )
        )

        layout.addWidget(
            button,
            0,
            Qt.AlignmentFlag.AlignVCenter
        )

        self.scroll_layout.addWidget(
            banner
        )

    # =====================================================
    # OUTROS PERFIS
    # =====================================================

    def _build_other_profiles(
        self,
        profiles: list[Profile],
    ):

        title = QLabel(
            "Seus perfis"
        )

        title.setObjectName(
            "ProfilesSectionTitle"
        )

        self.scroll_layout.addWidget(
            title
        )

        hint = QLabel(
            "Selecione um perfil para abrir sua coleção."
        )

        hint.setObjectName(
            "ProfilesSectionHint"
        )

        self.scroll_layout.addWidget(
            hint
        )

        grid_container = QWidget()

        grid = QGridLayout(
            grid_container
        )

        grid.setContentsMargins(
            0,
            0,
            0,
            0,
        )

        grid.setHorizontalSpacing(
            12
        )

        grid.setVerticalSpacing(
            12
        )

        columns = 3

        for index, profile in enumerate(
            profiles
        ):

            card = ProfileCard(
                profile
            )

            card.clicked.connect(
                self.activate_profile
            )

            card.rename_requested.connect(
                self.rename_profile
            )

            card.avatar_requested.connect(
                self.change_avatar
            )

            card.delete_requested.connect(
                self.delete_profile
            )

            self.profile_cards.append(
                card
            )

            row = (
                index
                // columns
            )

            column = (
                index
                % columns
            )

            grid.addWidget(
                card,
                row,
                column
            )

        for column in range(
            columns
        ):

            grid.setColumnStretch(
                column,
                1
            )

        self.scroll_layout.addWidget(
            grid_container
        )

        self.scroll_layout.addStretch()

    # =====================================================
    # CRIAR PERFIL
    # =====================================================

    def create_profile(
        self,
    ):

        dialog = ProfileDialog(
            self,
            title="Novo perfil",
            subtitle=(
                "Cada perfil possui sua própria coleção, "
                "decks e configurações."
            ),
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):

            return

        name = (
            dialog.get_name()
        )

        try:

            profile = (
                self.manager.create_profile(
                    name
                )
            )

            # O primeiro perfil criado vira automaticamente
            # o perfil ativo.

            # -------------------------------------------------
            # NOVO PERFIL VIRA O PERFIL ATIVO IMEDIATAMENTE
            # -------------------------------------------------

            profile = (
                self.manager.set_active_profile(
                    profile.id
                )
            )

            self.profile_created.emit(
                profile
            )

            self.profile_changed.emit(
                profile
            )

            self.profiles_updated.emit()

            self.refresh()

        except ProfileAlreadyExistsError as error:

            QMessageBox.warning(
                self,
                "Perfil existente",
                str(error),
            )

        except InvalidProfileNameError as error:

            QMessageBox.warning(
                self,
                "Nome inválido",
                str(error),
            )

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao criar perfil",
                str(error),
            )

    # =====================================================
    # REGISTRAR SAVE ANTIGO
    # =====================================================

    def register_legacy_profile(
        self,
        database_path: Optional[Path] = None,
    ):

        if database_path is None:

            database_path = (
                self.manager.find_legacy_database()
            )

        if database_path is None:

            QMessageBox.warning(
                self,
                "Save não encontrado",
                "Não foi possível localizar o save antigo.",
            )

            return

        dialog = ProfileDialog(
            self,
            title="Nomear sua coleção existente",
            subtitle=(
                "Seu save antigo será apenas associado "
                "a um perfil. Os dados não serão movidos "
                "nem modificados."
            ),
            initial_name="Minha Coleção",
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):

            return

        name = (
            dialog.get_name()
        )

        # -------------------------------------------------
        # Confirmação explícita
        # -------------------------------------------------

        confirmation = QMessageBox(
            self
        )

        confirmation.setIcon(
            QMessageBox.Icon.Information
        )

        confirmation.setWindowTitle(
            "Importar coleção existente?"
        )

        confirmation.setText(
            (
                f'A coleção "{name}" será '
                "importada para um novo perfil."
            )
        )

        confirmation.setInformativeText(
            (
                "Uma cópia independente do save "
                "será criada dentro deste perfil. "
                "O save original continuará intacto."
            )
        )

        confirmation.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )

        confirmation.setDefaultButton(
            QMessageBox.StandardButton.Yes
        )

        if (
            confirmation.exec()
            != QMessageBox.StandardButton.Yes
        ):

            return

        try:

            profile = (
                self.manager.register_legacy_profile(
                    name=name,
                    database_path=database_path,
                )
            )

            profile = (
                self.manager.set_active_profile(
                    profile.id
                )
            )

            self.profile_created.emit(
                profile
            )

            self.profile_changed.emit(
                profile
            )

            self.profiles_updated.emit()

            self.refresh()

        except ProfileAlreadyExistsError as error:

            QMessageBox.warning(
                self,
                "Perfil existente",
                str(error),
            )

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao registrar coleção",
                str(error),
            )

    # =====================================================
    # ATIVAR PERFIL
    # =====================================================

    def activate_profile(
        self,
        profile: Profile,
    ):

        if not profile:

            return

        if (
            self.active_profile
            and profile.id
            == self.active_profile.id
        ):

            return

        try:

            profile = (
                self.manager.set_active_profile(
                    profile.id
                )
            )

            self.active_profile = (
                profile
            )

            self.profile_activated.emit(
                profile
            )

            self.profile_changed.emit(
                profile
            )

            self.profiles_updated.emit()

            self.refresh()

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao trocar perfil",
                str(error),
            )

    # =====================================================
    # RENOMEAR
    # =====================================================

    def rename_profile(
        self,
        profile: Profile,
    ):

        if not profile:

            return

        dialog = ProfileDialog(
            self,
            title="Renomear perfil",
            subtitle=(
                "O banco de dados continuará sendo "
                "o mesmo."
            ),
            initial_name=profile.name,
        )

        if (
            dialog.exec()
            != QDialog.DialogCode.Accepted
        ):

            return

        new_name = (
            dialog.get_name()
        )

        try:

            updated = (
                self.manager.rename_profile(
                    profile.id,
                    new_name,
                )
            )

            self.profile_changed.emit(
                updated
            )

            self.profiles_updated.emit()

            self.refresh()

        except ProfileAlreadyExistsError as error:

            QMessageBox.warning(
                self,
                "Nome já utilizado",
                str(error),
            )

        except InvalidProfileNameError as error:

            QMessageBox.warning(
                self,
                "Nome inválido",
                str(error),
            )

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao renomear",
                str(error),
            )

    # =====================================================
    # AVATAR
    # =====================================================

    def change_avatar(
        self,
        profile: Profile,
    ):

        if not profile:

            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Escolher avatar",
            "",
            (
                "Imagens (*.png *.jpg *.jpeg *.webp *.bmp);;"
                "Todos os arquivos (*)"
            ),
        )

        if not path:

            return

        try:

            updated = (
                self.manager.set_avatar(
                    profile.id,
                    path,
                )
            )

            self.profile_changed.emit(
                updated
            )

            self.profiles_updated.emit()

            self.refresh()

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao alterar avatar",
                str(error),
            )

    # =====================================================
    # EXCLUIR
    # =====================================================

    def delete_profile(
        self,
        profile: Profile,
    ):

        if not profile:

            return

        profiles = (
            self.manager.get_profiles()
        )

        if len(profiles) <= 1:

            QMessageBox.information(
                self,
                "Último perfil",
                (
                    "Você não pode excluir o último "
                    "perfil existente."
                ),
            )

            return

        # -------------------------------------------------
        # Texto especial para legacy
        # -------------------------------------------------

        if profile.is_legacy:

            info = (
                "Este perfil está associado ao seu "
                "save antigo.\n\n"
                "Excluir o perfil NÃO excluirá "
                "o save antigo."
            )

        else:

            info = (
                "O perfil será removido da lista.\n\n"
                "Por segurança, o banco do perfil "
                "não será apagado automaticamente."
            )

        answer = QMessageBox.question(
            self,
            "Excluir perfil?",
            (
                f'Excluir o perfil "{profile.name}"?\n\n'
                f"{info}"
            ),
            (
                QMessageBox.StandardButton.Yes
                | QMessageBox.StandardButton.No
            ),
            QMessageBox.StandardButton.No,
        )

        if (
            answer
            != QMessageBox.StandardButton.Yes
        ):

            return

        was_active = (
            profile.last_opened_at
            is not None
        )

        try:

            self.manager.delete_profile(
                profile.id,
                delete_database=False,
            )

            self.profile_deleted.emit(
                profile
            )

            self.profiles_updated.emit()

            # -------------------------------------------------
            # Se removemos o ativo, escolhe o primeiro
            # restante.
            # -------------------------------------------------

            if was_active:

                new_active = (
                    self.manager.get_active_profile()
                )

                if new_active:

                    self.profile_activated.emit(
                        new_active
                    )

                    self.profile_changed.emit(
                        new_active
                    )

            self.refresh()

        except ProfileManagerError as error:

            QMessageBox.critical(
                self,
                "Erro ao excluir perfil",
                str(error),
            )

    # =====================================================
    # PERFIL ATIVO ATUAL
    # =====================================================

    def get_active_profile(
        self,
    ) -> Optional[Profile]:

        return (
            self.manager.get_active_profile()
        )

    # =====================================================
    # RELOAD
    # =====================================================

    def reload_profiles(
        self,
    ):

        self.refresh()

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from database import (
    initialize_database,
    initialize_decks_database,
    rebuild_missing_image_paths,
)

from ui.main_window import MainWindow


# =========================================================
# CAMINHOS
# =========================================================

def resource_path(*parts):
    """
    Retorna o caminho correto dos recursos tanto em
    desenvolvimento quanto no executável PyInstaller.
    """

    if getattr(sys, "frozen", False):
        base_dir = Path(sys._MEIPASS)
    else:
        base_dir = Path(__file__).resolve().parent

    return base_dir.joinpath(*parts)


APP_ICON_PATH = resource_path(
    "assets",
    "icons",
    "icon_app.png",
)


# =========================================================
# MAIN
# =========================================================

def main():

    # =====================================================
    # BANCO
    # =====================================================

    initialize_database()

    initialize_decks_database()

    rebuild_missing_image_paths()


    # =====================================================
    # QT
    # =====================================================

    app = QApplication(
        sys.argv
    )

    app.setApplicationName(
        "Magic Collection"
    )

    app.setApplicationDisplayName(
        "Magic Collection"
    )


    # =====================================================
    # ÍCONE GLOBAL DO APLICATIVO
    # =====================================================

    if APP_ICON_PATH.exists():

        app.setWindowIcon(
            QIcon(
                str(APP_ICON_PATH)
            )
        )


    # =====================================================
    # JANELA
    # =====================================================

    window = MainWindow()

    window.show()


    # =====================================================
    # EXECUÇÃO
    # =====================================================

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":

    main()

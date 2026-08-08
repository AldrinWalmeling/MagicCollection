import sys

from PySide6.QtWidgets import QApplication

from database import (
    initialize_database,
    initialize_decks_database,
    rebuild_missing_image_paths,
)

from ui.main_window import MainWindow


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

    window = MainWindow()

    window.show()

    sys.exit(
        app.exec()
    )


if __name__ == "__main__":
    main()
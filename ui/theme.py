"""
Carregador do tema da interface.

O arquivo ``theme.qss`` contém a folha de estilos (QSS).
Este módulo carrega esse conteúdo e o expõe como a constante
``DARK_THEME`` usada em todo o projeto.
"""

from pathlib import Path

_QSS_PATH = Path(__file__).resolve().parent / "theme.qss"


def _load_theme() -> str:
    try:
        return _QSS_PATH.read_text(encoding="utf-8")
    except OSError:
        return ""


DARK_THEME = _load_theme()

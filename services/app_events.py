from PySide6.QtCore import (
    QObject,
    Signal,
)


# =========================================================
# EVENTOS GLOBAIS DA APLICAÇÃO
# =========================================================
#
# Este módulo NÃO acessa banco.
# Este módulo NÃO cria widgets.
#
# Ele somente comunica que alguma coisa mudou.
#
# Exemplo:
#
# Collection altera quantidade
#       ↓
# banco atualizado
#       ↓
# collection_changed.emit(...)
#       ↓
# Collection / Decks / outros interessados
# atualizam somente o necessário.
#
# =========================================================


class AppEvents(QObject):

    # -----------------------------------------------------
    # CARTA DA COLEÇÃO ALTERADA
    # -----------------------------------------------------
    #
    # card_id
    # new_quantity
    #
    collection_card_changed = Signal(
        int,
        int,
    )

    # -----------------------------------------------------
    # CARTA DO DECK ALTERADA
    # -----------------------------------------------------
    #
    # deck_id
    # card_id
    # new_quantity
    #
    deck_card_changed = Signal(
        int,
        int,
        int,
    )

    # -----------------------------------------------------
    # DADOS DA CARTA ALTERADOS
    # -----------------------------------------------------
    #
    # Usaremos depois para:
    #
    # idioma
    # arte
    # preferência
    # face
    # imagem
    # etc.
    #
    card_data_changed = Signal(
        int,
    )


# =========================================================
# INSTÂNCIA GLOBAL
# =========================================================

app_events = AppEvents()
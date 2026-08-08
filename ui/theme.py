DARK_THEME = """

* {
    font-family: "Segoe UI";
}

/* ===================================================== */
/* BASE */
/* ===================================================== */

QMainWindow {
    background-color: #0D0E10;
}

QWidget {
    background-color: #0D0E10;
    color: #E8E8EA;
    font-size: 14px;
}

/* ===================================================== */
/* SIDEBAR */
/* ===================================================== */

QFrame#Sidebar {
    background-color: #141518;
    border-right: 1px solid #25272B;
}

QLabel#AppTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 21px;
    font-weight: bold;
}

QLabel#SidebarStatus {
    background-color: transparent;
    color: #5F6268;
    font-size: 11px;
    padding: 5px;
}

QPushButton#SidebarButton {
    background-color: transparent;
    border: none;
    border-radius: 8px;
    color: #96999F;
    text-align: left;
    padding: 11px 14px;
    font-size: 14px;
}

QPushButton#SidebarButton:hover {
    background-color: #202226;
    color: #FFFFFF;
}

QPushButton#SidebarButton:checked {
    background-color: #292C31;
    color: #FFFFFF;
    font-weight: bold;
}

/* ===================================================== */
/* TÍTULOS */
/* ===================================================== */

QLabel#SectionTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 26px;
    font-weight: bold;
}

QLabel#SectionDescription {
    background-color: transparent;
    color: #777A80;
    font-size: 13px;
}

/* ===================================================== */
/* CAMPOS */
/* ===================================================== */

QLineEdit {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 9px;
    padding: 11px 13px;
    color: #FFFFFF;
    selection-background-color: #3B3E44;
}

QLineEdit:hover {
    border: 1px solid #383B41;
}

QLineEdit:focus {
    border: 1px solid #555961;
}

/* ===================================================== */
/* PESQUISA / ADIÇÃO */
/* ===================================================== */

QFrame#SearchFrame,
QFrame#AddFrame {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 10px;
}

QFrame#SearchFrame:hover,
QFrame#AddFrame:hover {
    border: 1px solid #383B41;
}

QLabel#SearchIcon,
QLabel#AddIcon {
    background-color: transparent;
    color: #777A80;
    font-size: 16px;
}

QLabel#SearchStatus {
    background-color: transparent;
    color: #A7AAB0;
    font-size: 14px;
}

/* ===================================================== */
/* BOTÃO ADICIONAR */
/* ===================================================== */

QPushButton#AddButton {
    background-color: #E8E8EA;
    color: #111214;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: bold;
}

QPushButton#AddButton:hover {
    background-color: #FFFFFF;
}

QPushButton#AddButton:pressed {
    background-color: #C8C9CC;
}

QPushButton#AddButton:disabled {
    background-color: #4A4C50;
    color: #85878B;
}

/* ===================================================== */
/* BOTÃO EXPORTAR */
/* ===================================================== */

QPushButton#ExportButton {
    background-color: #1D1F23;
    color: #E3E4E7;
    border: 1px solid #303339;
    border-radius: 8px;
    padding: 9px 15px;
    font-weight: bold;
}

QPushButton#ExportButton:hover {
    background-color: #272A2F;
    border: 1px solid #41444A;
    color: #FFFFFF;
}

QPushButton#ExportButton:pressed {
    background-color: #181A1D;
}

/* ===================================================== */
/* CARTAS */
/* ===================================================== */

QFrame#CardFrame {
    background-color: #15171A;
    border: 1px solid #272A2E;
    border-radius: 12px;
}

QFrame#CardFrame:hover {
    background-color: #191B1F;
    border: 1px solid #3A3D43;
}

QWidget#CardInfo {
    background-color: transparent;
}

/* ===================================================== */
/* MINIATURA */
/* ===================================================== */

QLabel#CardThumbnail {
    background-color: #101114;
    border: 1px solid #292C31;
    border-radius: 7px;
    color: #55585E;
    font-size: 21px;
}

/* ===================================================== */
/* NOME */
/* ===================================================== */

QLabel#CardName {
    background-color: transparent;
    color: #F2F2F3;
    font-size: 15px;
    font-weight: 600;
}

/* ===================================================== */
/* TIPO */
/* ===================================================== */

QLabel#CardType {
    background-color: transparent;
    color: #B0B2B7;
    font-size: 12px;
}

/* ===================================================== */
/* EDIÇÃO */
/* ===================================================== */

QLabel#CardSet {
    background-color: transparent;
    color: #686B71;
    font-size: 11px;
}

/* ===================================================== */
/* MANA + POWER / TOUGHNESS */
/* ===================================================== */

/*
Container que agrupa:

[ MANA ] | [ P/T ]

Tudo fica transparente para não aparecer
o fundo global #0D0E10.
*/

QWidget#CardSideWidget {
    background-color: transparent;
    border: none;
}

/* ===================================================== */
/* MANA */
/* ===================================================== */

QWidget#CardMana {
    background-color: transparent;
    border: none;
}

QWidget#CardMana QLabel,
QWidget#CardMana QWidget,
QWidget#CardMana QFrame {
    background-color: transparent;
    border: none;
}

/* ===================================================== */
/* SEPARADORES */
/* ===================================================== */

/*
Todos os separadores CardMetaSeparator
possuem exatamente o mesmo tamanho.

1px de largura
24px de altura
*/

QFrame#CardMetaSeparator {
    background-color: #383B41;
    border: none;

    min-width: 1px;
    max-width: 1px;

    min-height: 80px;
    max-height: 64px;
}

/* ===================================================== */
/* META DA CARTA */
/* ===================================================== */

QWidget#CardMeta {
    background-color: transparent;
    border: none;
}

/* ===================================================== */
/* POWER / TOUGHNESS */
/* ===================================================== */

QLabel#CardPT {
    background-color: #202328;
    border: 1px solid #32353B;
    border-radius: 6px;

    color: #E8E9EB;

    font-size: 12px;
    font-weight: bold;

    padding: 3px 7px;

    min-width: 64px;
    max-width: 80px;

    min-height: 26px;
    max-height: 32px;
}

/* ===================================================== */
/* ÁREA DE QUANTIDADE */
/* ===================================================== */

QFrame#QuantityFrame {
    background-color: transparent;
    border: none;
}

/* ===================================================== */
/* QUANTIDADE */
/* ===================================================== */

QLabel#Quantity {
    background-color: transparent;
    border: none;

    color: #FFFFFF;

    font-size: 14px;
    font-weight: bold;
}

/* ===================================================== */
/* BOTÕES DE QUANTIDADE */
/* ===================================================== */

QPushButton#QuantityButton {
    background-color: transparent;
    border: none;
    border-radius: 6px;

    min-width: 30px;
    max-width: 30px;

    min-height: 30px;
    max-height: 30px;

    padding: 0;

    color: #BFC1C5;

    font-size: 17px;
    font-weight: bold;
}

QPushButton#QuantityButton:hover {
    background-color: #25282D;
    color: #FFFFFF;
}

QPushButton#QuantityButton:pressed {
    background-color: #303339;
    color: #FFFFFF;
}

/* ===================================================== */
/* SCROLL */
/* ===================================================== */

/*
Área inteira transparente.
*/

QScrollArea#CardsScrollArea {
    background-color: transparent;
    border: none;
    padding: 0;
}

/*
Viewport interno.
*/

QScrollArea#CardsScrollArea > QWidget {
    background-color: transparent;
    border: none;
}

QScrollArea#CardsScrollArea > QWidget > QWidget {
    background-color: transparent;
    border: none;
}

/* ===================================================== */
/* SCROLLBAR VERTICAL */
/* ===================================================== */

QScrollBar:vertical {
    background-color: transparent;

    width: 10px;

    border: none;

    margin: 2px 1px 2px 2px;
}

QScrollBar::handle:vertical {
    background-color: #303339;

    border: none;
    border-radius: 5px;

    min-height: 45px;

    margin: 0;
}

QScrollBar::handle:vertical:hover {
    background-color: #4A4D54;
}

QScrollBar::handle:vertical:pressed {
    background-color: #5A5E66;
}

/* Remove setas */

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    background: none;
    border: none;

    height: 0px;
    width: 0px;
}

/* Remove espaço extra */

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

/* ===================================================== */
/* SCROLLBAR HORIZONTAL */
/* ===================================================== */

QScrollBar:horizontal {
    background-color: transparent;

    height: 10px;

    border: none;

    margin: 1px 2px 1px 2px;
}

QScrollBar::handle:horizontal {
    background-color: #303339;

    border: none;
    border-radius: 5px;

    min-width: 45px;

    margin: 0;
}

QScrollBar::handle:horizontal:hover {
    background-color: #4A4D54;
}

QScrollBar::handle:horizontal:pressed {
    background-color: #5A5E66;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    background: none;
    border: none;

    width: 0px;
    height: 0px;
}

QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {
    background: transparent;
}

/* ===================================================== */
/* AUTOCOMPLETE */
/* ===================================================== */

QListWidget#SuggestionList {
    background-color: #181A1E;
    color: #EEEEF0;
    border: 1px solid #363940;
    border-radius: 8px;
    padding: 4px;
    outline: none;
}

QListWidget#SuggestionList::item {
    background-color: transparent;
    padding: 9px 12px;
    border-radius: 5px;
}

QListWidget#SuggestionList::item:hover {
    background-color: #282B30;
}

QListWidget#SuggestionList::item:selected {
    background-color: #33363C;
    color: #FFFFFF;
}

/* ===================================================== */
/* MENU EXPORTAR */
/* ===================================================== */

QMenu#ExportMenu {
    background-color: #181A1E;
    color: #EEEEF0;
    border: 1px solid #363940;
    padding: 5px;
}

QMenu#ExportMenu::item {
    background-color: transparent;
    padding: 9px 20px;
    border-radius: 5px;
}

QMenu#ExportMenu::item:selected {
    background-color: #2A2D33;
    color: #FFFFFF;
}

QMenu#ExportMenu::separator {
    height: 1px;
    background-color: #303339;
    margin: 5px 8px;
}

/* ===================================================== */
/* DETALHES DA CARTA */
/* ===================================================== */

QLabel#CardDetailImage {
    background-color: #101114;
    border: 1px solid #30343A;
    border-radius: 10px;
    color: #666970;
    font-size: 14px;
}

QLabel#CardDetailName {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 25px;
    font-weight: bold;
}

QLabel#CardDetailManaTitle {
    background-color: transparent;
    color: #777A80;
    font-size: 12px;
    font-weight: bold;
}

QLabel#CardDetailType {
    background-color: transparent;
    color: #D0D1D4;
    font-size: 14px;
}

QLabel#CardDetailPT {
    background-color: #202328;
    border: 1px solid #34373D;
    border-radius: 6px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: bold;
    padding: 5px 9px;
}

QLabel#CardDetailSet {
    background-color: transparent;
    color: #85888E;
    font-size: 13px;
}

QLabel#CardDetailQuantity {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 14px;
    font-weight: bold;
}

QLabel#CardDetailText {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 8px;
    color: #D0D1D4;
    padding: 12px;
    font-size: 13px;
}

QFrame#CardDetailSeparator {
    background-color: #30343A;
    border: none;
    max-height: 1px;
}

/* ===================================================== */
/* DIALOG BUTTONS */
/* ===================================================== */

QDialogButtonBox QPushButton {
    background-color: #202328;
    color: #EEEEF0;
    border: 1px solid #34373D;
    border-radius: 7px;
    padding: 8px 16px;
    min-width: 80px;
}

QDialogButtonBox QPushButton:hover {
    background-color: #2C2F35;
    border: 1px solid #454850;
}

QDialogButtonBox QPushButton:pressed {
    background-color: #191B1F;
}

/* ===================================================== */
/* DECKS */
/* ===================================================== */

QLabel#ComingSoon {
    background-color: transparent;
    color: #666970;
    font-size: 16px;
}

/* ===================================================== */
/* SELEÇÃO */
/* ===================================================== */

QAbstractItemView {
    selection-background-color: #33363C;
    selection-color: #FFFFFF;
}

"""
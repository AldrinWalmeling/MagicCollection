
DARK_THEME = """

/* =========================================================
BASE
========================================================= */

* {
    font-family: "Segoe UI";
}

QMainWindow {
    background-color: #0D0E10;
}

QWidget {
    background-color: #0D0E10;
    color: #E8E8EA;
    font-size: 14px;
}

/* =========================================================
SIDEBAR
========================================================= */

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

QPushButton#SidebarButton:pressed {
    background-color: #303339;
}

/* =========================================================
TÍTULOS
========================================================= */

QLabel#DecksTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 26px;
    font-weight: bold;
}

QLabel#DecksDescription {
    background-color: transparent;
    color: #777A80;
    font-size: 13px;
}

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

/* =========================================================
CAMPOS
========================================================= */

QLineEdit {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 9px;
    padding: 11px 13px;
    color: #FFFFFF;
    selection-background-color: #3B3E44;
    selection-color: #FFFFFF;
}

QLineEdit:hover {
    border: 1px solid #383B41;
}

QLineEdit:focus {
    border: 1px solid #555961;
}

QLineEdit:disabled {
    background-color: #111316;
    color: #55585E;
    border: 1px solid #25272B;
}

/* =========================================================
TEXT EDIT
========================================================= */

QTextEdit,
QPlainTextEdit {
    background-color: #15171A;
    color: #E8E8EA;
    border: 1px solid #292C31;
    border-radius: 9px;
    padding: 10px 12px;
    selection-background-color: #3B3E44;
    selection-color: #FFFFFF;
}

QTextEdit:hover,
QPlainTextEdit:hover {
    border: 1px solid #383B41;
}

QTextEdit:focus,
QPlainTextEdit:focus {
    border: 1px solid #555961;
}

/* =========================================================
PESQUISA / ADIÇÃO
========================================================= */

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

/* =========================================================
BOTÃO ADICIONAR
========================================================= */

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

/* =========================================================
BOTÃO EXPORTAR
========================================================= */

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

/* =========================================================
MENU DE LAYOUT
========================================================= */

QMenu#LayoutMenu {
    background-color: #181A1E;
    color: #E8E8EA;
    border: 1px solid #303339;
    border-radius: 9px;
    padding: 5px;
}

QMenu#LayoutMenu::item {
    background-color: transparent;
    color: #BFC1C5;
    padding: 9px 22px 9px 10px;
    margin: 1px;
    border-radius: 6px;
}

QMenu#LayoutMenu::item:selected {
    background-color: #272A2F;
    color: #FFFFFF;
}

QMenu#LayoutMenu::item:checked {
    color: #FFFFFF;
    font-weight: 600;
}

QMenu#LayoutMenu::item:checked:selected {
    background-color: #303339;
    color: #FFFFFF;
}

/* =========================================================
CARTA — GRADE
========================================================= */

QFrame#GridCardFrame {
    background-color: #15171A;
    border: 1px solid #272A2E;
    border-radius: 10px;
}

QFrame#GridCardFrame:hover {
    background-color: #191B1F;
    border: 1px solid #3A3D43;
}

/* =========================================================
IMAGEM DA CARTA — GRADE
========================================================= */

QLabel#GridCardImage {
    background-color: #101114;
    border: none;
    border-radius: 9px;
    color: #55585E;
    font-size: 21px;
}

/* =========================================================
OVERLAY DE QUANTIDADE — GRADE
========================================================= */

QFrame#GridQuantityOverlay {
    background-color: rgba(13, 14, 16, 235);
    border: none;
    border-top: 1px solid #303339;
    border-bottom-left-radius: 9px;
    border-bottom-right-radius: 9px;
}

/* =========================================================
BOTÕES DE QUANTIDADE — GRADE
========================================================= */

QPushButton#GridQuantityButton {
    background-color: #24272C;
    color: #D9DADF;
    border: 1px solid #34373D;
    border-radius: 7px;

    min-width: 34px;
    max-width: 34px;

    min-height: 34px;
    max-height: 34px;

    padding: 0;

    font-size: 18px;
    font-weight: 600;
}

QPushButton#GridQuantityButton:hover {
    background-color: #303339;
    border: 1px solid #454850;
    color: #FFFFFF;
}

QPushButton#GridQuantityButton:pressed {
    background-color: #1C1E22;
    border: 1px solid #383B41;
    color: #FFFFFF;
}

/* =========================================================
QUANTIDADE — GRADE
========================================================= */

QLabel#GridQuantityLabel {
    background-color: transparent;
    color: #FFFFFF;
    border: none;

    font-size: 14px;
    font-weight: bold;
}

/* =========================================================
BOTÃO DE LAYOUT
========================================================= */

QPushButton#LayoutButton {
    background-color: #181A1E;
    color: #C9CBD0;
    border: 1px solid #303339;
    border-radius: 8px;
    padding: 9px 14px;
    font-weight: 600;
}

QPushButton#LayoutButton:hover {
    background-color: #22252A;
    border: 1px solid #41444A;
    color: #FFFFFF;
}

QPushButton#LayoutButton:pressed {
    background-color: #15171A;
    border: 1px solid #383B41;
}

/* =========================================================
CARTAS
========================================================= */

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

/* =========================================================
MINIATURA
========================================================= */

QLabel#CardThumbnail {
    background-color: #101114;
    border: 1px solid #292C31;
    border-radius: 7px;
    color: #55585E;
    font-size: 21px;
}

/* =========================================================
NOME
========================================================= */

QLabel#CardName {
    background-color: transparent;
    color: #F2F2F3;
    font-size: 15px;
    font-weight: 600;
}

/* =========================================================
TIPO
========================================================= */

QLabel#CardType {
    background-color: transparent;
    color: #B0B2B7;
    font-size: 12px;
}

/* =========================================================
EDIÇÃO
========================================================= */

QLabel#CardSet {
    background-color: transparent;
    color: #686B71;
    font-size: 11px;
}

/* =========================================================
MANA + POWER / TOUGHNESS
========================================================= */

QWidget#CardSideWidget {
    background-color: transparent;
    border: none;
}

/* =========================================================
MANA
========================================================= */

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

/* =========================================================
SEPARADORES
========================================================= */

QFrame#CardMetaSeparator {
    background-color: #383B41;
    border: none;

    min-width: 1px;
    max-width: 1px;

    min-height: 80px;
    max-height: 64px;
}

/* =========================================================
META DA CARTA
========================================================= */

QWidget#CardMeta {
    background-color: transparent;
    border: none;
}

/* =========================================================
POWER / TOUGHNESS
========================================================= */

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

/* =========================================================
ÁREA DE QUANTIDADE
========================================================= */

QFrame#QuantityFrame {
    background-color: transparent;
    border: none;
}

/* =========================================================
QUANTIDADE
========================================================= */

QLabel#Quantity {
    background-color: transparent;
    border: none;

    color: #FFFFFF;

    font-size: 14px;
    font-weight: bold;
}

/* =========================================================
BOTÕES DE QUANTIDADE
========================================================= */

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

/* =========================================================
SCROLL
========================================================= */

QScrollArea#CardsScrollArea {
    background-color: transparent;
    border: none;
    padding: 0;
}

QScrollArea#CardsScrollArea > QWidget {
    background-color: transparent;
    border: none;
}

QScrollArea#CardsScrollArea > QWidget > QWidget {
    background-color: transparent;
    border: none;
}

/* =========================================================
SCROLLBAR VERTICAL
========================================================= */

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

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    background: none;
    border: none;

    height: 0px;
    width: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}

/* =========================================================
SCROLLBAR HORIZONTAL
========================================================= */

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

/* =========================================================
AUTOCOMPLETE
========================================================= */

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

/* =========================================================
MENU EXPORTAR
========================================================= */

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

/* =========================================================
DETALHES DA CARTA
========================================================= */

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

/* =========================================================
DIALOG BUTTONS
========================================================= */

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

/* =========================================================
DECKS
========================================================= */

/* =========================================================
TÍTULOS
========================================================= */

QLabel#DecksTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 26px;
    font-weight: bold;
}

QLabel#DecksDescription {
    background-color: transparent;
    color: #777A80;
    font-size: 13px;
}

/* =========================================================
ÁREA DOS DECKS
========================================================= */

QScrollArea#DecksScrollArea {
    background-color: transparent;
    border: none;
    padding: 0;
}

QScrollArea#DecksScrollArea > QWidget {
    background-color: transparent;
    border: none;
}

QScrollArea#DecksScrollArea > QWidget > QWidget {
    background-color: transparent;
    border: none;
}

/* =========================================================
CARD DO DECK
========================================================= */

QFrame#DeckCard {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 12px;
}

QFrame#DeckCard:hover {
    background-color: #191B1F;
    border: 1px solid #41444A;
}

/* =========================================================
CAPA DO DECK
========================================================= */

QFrame#DeckCover {
    background-color: #101114;
    border: 1px solid #292C31;
    border-radius: 10px;
}

QLabel#DeckCoverImage {
    background-color: #111318;
    border: 1px solid #30343c;
    border-radius: 9px;
    font-size: 32px;
}

QLabel#DeckCoverTitle {
    color: #f0f2f5;
    font-size: 16px;
    font-weight: 600;
}

QLabel#DeckCoverDescription {
    color: #858c98;
    font-size: 12px;
}

QPushButton#DeckCoverButton {
    background-color: #252a32;
    color: #e5e8ed;
    border: 1px solid #343a44;
    border-radius: 7px;
    padding: 7px 12px;
}

QPushButton#DeckCoverButton:hover {
    background-color: #303640;
    border: 1px solid #555e6d;
}

QPushButton#DeckCoverResetButton {
    background-color: transparent;
    color: #858c98;
    border: none;
    padding: 5px;
}

QPushButton#DeckCoverResetButton:hover {
    color: #c5cad2;
}

QLabel#DeckPreviewSelectorTitle {
    color: #f0f2f5;
    font-size: 18px;
    font-weight: 600;
}

QPushButton#DeckPreviewSelectorCard {
    background-color: #181a1f;
    border: 1px solid #30343c;
    border-radius: 8px;
}

QPushButton#DeckPreviewSelectorCard:hover {
    background-color: #252a32;
    border: 1px solid #687386;
}

/* =========================================================
INFORMAÇÕES DO DECK
========================================================= */

QLabel#DeckName {
    background-color: transparent;
    color: #F2F2F3;
    font-size: 15px;
    font-weight: 600;
}

/* QUANTIDADE — reforçada para permanecer visível */

QLabel#DeckQuantityBadge {
    color: white;
    background-color: rgba(0, 0, 0, 190);
    border: 1px solid rgba(255, 255, 255, 180);
    border-radius: 8px;
    padding-left: 7px;
    padding-right: 7px;
    font-weight: bold;
}

QLabel#DeckControlQuantity {
    color: white;
    background-color: rgba(0, 0, 0, 210);
    border: 1px solid rgba(255, 255, 255, 180);
    border-radius: 6px;
    font-weight: bold;
}

QLabel#DeckCardCount {
    background-color: #2A2D33;
    color: #FFFFFF;
    border: 1px solid #454850;
    border-radius: 6px;
    padding: 4px 9px;
    font-size: 12px;
    font-weight: bold;
}

/* =========================================================
AÇÕES DO CARD DO DECK
========================================================= */

QPushButton#DeckActionButton {
    background-color: #1D1F23;
    color: #D9DADF;
    border: 1px solid #303339;
    border-radius: 7px;
    padding: 7px 11px;
    font-weight: 600;
}

QPushButton#DeckActionButton:hover {
    background-color: #272A2F;
    border: 1px solid #41444A;
    color: #FFFFFF;
}

QPushButton#DeckActionButton:pressed {
    background-color: #181A1D;
}

/* =========================================================
EXCLUIR
========================================================= */

QPushButton#DeckDeleteButton {
    background-color: transparent;
    color: #85888E;
    border: 1px solid #303339;
    border-radius: 7px;
    padding: 7px 11px;
    font-weight: 600;
}

QPushButton#DeckDeleteButton:hover {
    background-color: #292023;
    border: 1px solid #554044;
    color: #E3BFC3;
}

QPushButton#DeckDeleteButton:pressed {
    background-color: #21191B;
}

/* =========================================================
NOVO DECK — CARD
========================================================= */

QFrame#NewDeckCard {
    background-color: #15171A;
    border: 1px dashed #3A3D43;
    border-radius: 12px;
}

QFrame#NewDeckCard:hover {
    background-color: #181A1E;
    border: 1px dashed #5A5E66;
}

QLabel#NewDeckPlus {
    background-color: transparent;
    color: #8B8E94;
    font-size: 36px;
    font-weight: 300;
}

QLabel#NewDeckText {
    background-color: transparent;
    color: #C4C6CA;
    font-size: 13px;
    font-weight: 600;
}

QFrame#NewDeckFrame {
    border: 1px dashed #555b66;
    border-radius: 14px;
    background-color: transparent;
}

QFrame#NewDeckFrame:hover {
    border: 1px solid #7c8491;
    background-color: rgba(255, 255, 255, 0.04);
}

QLabel#NewDeckPlus {
    color: #8f96a3;
    font-size: 52px;
    font-weight: 300;
}

QLabel#NewDeckText {
    color: #aeb4bf;
    font-size: 15px;
    font-weight: 500;
}

QFrame#NewDeckFrame:hover QLabel#NewDeckPlus {
    color: #d5d9df;
}

QFrame#NewDeckFrame:hover QLabel#NewDeckText {
    color: #e1e4e8;
}


QFrame#DeckPreviewFrame {
    border: 1px solid #3f444d;
    border-radius: 14px;
    background-color: transparent;
}

QFrame#DeckPreviewFrame:hover {
    border: 1px solid #707783;
    background-color: rgba(255, 255, 255, 0.04);
}

QLabel#DeckPreviewName {
    color: #e1e4e8;
    font-size: 15px;
    font-weight: 600;
}

QLabel#DeckPreviewTotal {
    color: #9299a5;
    font-size: 13px;
}

QFrame#DeckPreviewSection {
    background-color: #181a1f;
    border: 1px solid #292d34;
    border-radius: 12px;
}

QFrame#DeckPreviewFrame:hover QLabel#DeckPreviewName {
    color: #ffffff;
}

QFrame#DeckPreviewFrame:hover QLabel#DeckPreviewTotal {
    color: #b8bec8;
}

QLabel#DeckPreviewCard {
    background-color: transparent;
    border: none;
}


QFrame#DeckPreviewImageArea {
    background-color: #111318;
    border: 1px solid #292d34;
    border-radius: 10px;
}

QFrame#DeckCollectionPanel {
    border: 1px solid #505050;
    border-radius: 12px;
}

QFrame#CollectionDeckCard {
    border: 1px solid #3f3f3f;
    border-radius: 8px;
}

QPushButton#DeckAddCardsButton {
    border: 1px solid #505050;
    border-radius: 8px;
    padding: 8px 14px;
}
/* =========================================================
BOTÃO + NOVO DECK — CABEÇALHO
========================================================= */

QPushButton#NewDeckButton {
    background-color: #E8E8EA;
    color: #111214;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: bold;
}

QPushButton#NewDeckButton:hover {
    background-color: #FFFFFF;
}

QPushButton#NewDeckButton:pressed {
    background-color: #C8C9CC;
}

/* =========================================================
EDITOR DO DECK
========================================================= */

QFrame#DeckEditor {
    background-color: transparent;
    border: none;
}

/* =========================================================
CABEÇALHO DO EDITOR
========================================================= */

QFrame#DeckHeader {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 10px;
}

QLabel#DeckEditorTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 22px;
    font-weight: bold;
}

QLabel#DeckEditorCount {
    background-color: transparent;
    color: #777A80;
    font-size: 13px;
}

/* =========================================================
BOTÕES DO EDITOR
========================================================= */

QPushButton#AddCardsButton {
    background-color: #E8E8EA;
    color: #111214;
    border: none;
    border-radius: 8px;
    padding: 9px 16px;
    font-weight: bold;
}

QPushButton#AddCardsButton:hover {
    background-color: #FFFFFF;
}

QPushButton#AddCardsButton:pressed {
    background-color: #C8C9CC;
}

/* =========================================================
GRADE DE CARTAS DO DECK
========================================================= */

QFrame#DeckCardItem {
    background-color: #15171A;
    border: 1px solid #272A2E;
    border-radius: 10px;
}

QFrame#DeckCardItem:hover {
    background-color: #191B1F;
    border: 1px solid #3A3D43;
}

/* =========================================================
CARTA PRINCIPAL / CAPA SELECIONADA
========================================================= */

QFrame#DeckCardItem[selected="true"] {
    border: 1px solid #777A80;
    background-color: #191B1F;
}

QFrame#DeckCardItem[isPrimary="true"] {
    border: 1px solid #8A8D93;
    background-color: #191B1F;
}

/* =========================================================
IMAGEM DA CARTA
========================================================= */

QLabel#DeckCardImage {
    background-color: #101114;
    border: none;
    border-radius: 8px;
    color: #55585E;
}

/* =========================================================
NOME
========================================================= */

QLabel#DeckCardName {
    background-color: transparent;
    color: #E8E8EA;
    font-size: 13px;
    font-weight: 600;
}

/* =========================================================
QUANTIDADE
========================================================= */

QLabel#DeckCardQuantity {
    background-color: #202328;
    color: #FFFFFF;
    border: 1px solid #34373D;
    border-radius: 6px;
    padding: 3px 7px;
    font-size: 11px;
    font-weight: bold;
}

/* =========================================================
BOTÕES + / -
========================================================= */

QPushButton#DeckQuantityButton {
    background-color: #24272C;
    color: #D9DADF;
    border: 1px solid #34373D;
    border-radius: 6px;

    min-width: 28px;
    max-width: 28px;

    min-height: 28px;
    max-height: 28px;

    padding: 0;

    font-size: 16px;
    font-weight: 600;
}

QPushButton#DeckQuantityButton:hover {
    background-color: #303339;
    border: 1px solid #454850;
    color: #FFFFFF;
}

QPushButton#DeckQuantityButton:pressed {
    background-color: #1C1E22;
    border: 1px solid #383B41;
}

/* =========================================================
PAINEL — ADICIONAR CARTAS
========================================================= */

QFrame#CardSelectionPanel {
    background-color: #141518;
    border-left: 1px solid #292C31;
}

QLabel#CardSelectionTitle {
    background-color: transparent;
    color: #FFFFFF;
    font-size: 19px;
    font-weight: bold;
}

QLabel#CardSelectionCount {
    background-color: transparent;
    color: #777A80;
    font-size: 12px;
}

/* =========================================================
BUSCA
========================================================= */

QLineEdit#CardSelectionSearch {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 8px;
    padding: 9px 11px;
    color: #FFFFFF;
    selection-background-color: #3B3E44;
}

QLineEdit#CardSelectionSearch:hover {
    border: 1px solid #383B41;
}

QLineEdit#CardSelectionSearch:focus {
    border: 1px solid #555961;
}

/* =========================================================
CARTA DISPONÍVEL
========================================================= */

QFrame#AvailableCard {
    background-color: #181A1E;
    border: 1px solid #292C31;
    border-radius: 8px;
}

QFrame#AvailableCard:hover {
    background-color: #22252A;
    border: 1px solid #41444A;
}

QLabel#AvailableCardName {
    background-color: transparent;
    color: #E8E8EA;
    font-size: 12px;
    font-weight: 600;
}

QLabel#AvailableCardQuantity {
    background-color: transparent;
    color: #777A80;
    font-size: 11px;
}

/* =========================================================
ADICIONAR CARTA
========================================================= */

QPushButton#AvailableCardAddButton {
    background-color: #24272C;
    color: #D9DADF;
    border: 1px solid #34373D;
    border-radius: 6px;

    min-width: 28px;
    max-width: 28px;

    min-height: 28px;
    max-height: 28px;

    padding: 0;

    font-size: 16px;
    font-weight: bold;
}

QPushButton#AvailableCardAddButton:hover {
    background-color: #303339;
    border: 1px solid #454850;
    color: #FFFFFF;
}

QPushButton#AvailableCardAddButton:pressed {
    background-color: #1C1E22;
}

/* =========================================================
RENOMEAR DECK
========================================================= */

QLineEdit#DeckNameEdit {
    background-color: #15171A;
    border: 1px solid #34373D;
    border-radius: 7px;
    padding: 8px 10px;
    color: #FFFFFF;
    font-size: 16px;
    font-weight: 600;
    selection-background-color: #3B3E44;
}

QLineEdit#DeckNameEdit:hover {
    border: 1px solid #41444A;
}

QLineEdit#DeckNameEdit:focus {
    border: 1px solid #666970;
}

/* =========================================================
ESTADO VAZIO
========================================================= */

QLabel#EmptyDeck {
    background-color: transparent;
    color: #666970;
    font-size: 15px;
}

/* =========================================================
SEPARADOR
========================================================= */

QFrame#DeckSeparator {
    background-color: #292C31;
    border: none;
    max-height: 1px;
}

/* =========================================================
BOTÃO — ESCOLHER CARTA PRINCIPAL
========================================================= */

QPushButton#SetPrimaryCardButton {
    background-color: transparent;
    color: #A7AAB0;
    border: 1px solid #303339;
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
}

QPushButton#SetPrimaryCardButton:hover {
    background-color: #25282D;
    border: 1px solid #454850;
    color: #FFFFFF;
}

QPushButton#SetPrimaryCardButton:checked {
    background-color: #303339;
    border: 1px solid #666970;
    color: #FFFFFF;
}

/* =========================================================
INDICADOR DE CARTA PRINCIPAL
========================================================= */

QLabel#PrimaryCardLabel {
    background-color: #202328;
    color: #E8E8EA;
    border: 1px solid #41444A;
    border-radius: 5px;
    padding: 3px 7px;
    font-size: 10px;
    font-weight: bold;
}

/* =========================================================
COMBOBOX
========================================================= */

QComboBox {
    background-color: #15171A;
    color: #E8E8EA;
    border: 1px solid #292C31;
    border-radius: 8px;
    padding: 9px 12px;
    min-height: 18px;
}

QComboBox:hover {
    background-color: #191B1F;
    border: 1px solid #383B41;
}

QComboBox:focus {
    border: 1px solid #555961;
}

QComboBox:disabled {
    background-color: #111316;
    color: #55585E;
    border: 1px solid #25272B;
}

QComboBox::drop-down {
    background-color: transparent;
    border: none;
    width: 30px;
}

QComboBox QAbstractItemView {
    background-color: #181A1E;
    color: #E8E8EA;
    border: 1px solid #363940;
    selection-background-color: #2A2D33;
    selection-color: #FFFFFF;
    outline: none;
    padding: 4px;
}

/* =========================================================
SPINBOX
========================================================= */

QSpinBox,
QDoubleSpinBox {
    background-color: #15171A;
    color: #FFFFFF;
    border: 1px solid #292C31;
    border-radius: 8px;
    padding: 8px 10px;
}

QSpinBox:hover,
QDoubleSpinBox:hover {
    border: 1px solid #383B41;
}

QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 1px solid #555961;
}

QSpinBox::up-button,
QSpinBox::down-button,
QDoubleSpinBox::up-button,
QDoubleSpinBox::down-button {
    background-color: #202328;
    border: none;
    width: 22px;
}

QSpinBox::up-button:hover,
QSpinBox::down-button:hover,
QDoubleSpinBox::up-button:hover,
QDoubleSpinBox::down-button:hover {
    background-color: #303339;
}

/* =========================================================
CHECKBOX
========================================================= */

QCheckBox {
    background-color: transparent;
    color: #D9DADF;
    spacing: 8px;
}

QCheckBox:hover {
    color: #FFFFFF;
}

QCheckBox::indicator {
    width: 17px;
    height: 17px;
    background-color: #15171A;
    border: 1px solid #383B41;
    border-radius: 5px;
}

QCheckBox::indicator:hover {
    background-color: #202328;
    border: 1px solid #555961;
}

QCheckBox::indicator:checked {
    background-color: #E8E8EA;
    border: 1px solid #E8E8EA;
}

QCheckBox::indicator:disabled {
    background-color: #202226;
    border: 1px solid #303339;
}

/* =========================================================
RADIO BUTTON
========================================================= */

QRadioButton {
    background-color: transparent;
    color: #D9DADF;
    spacing: 8px;
}

QRadioButton:hover {
    color: #FFFFFF;
}

QRadioButton::indicator {
    width: 17px;
    height: 17px;
    background-color: #15171A;
    border: 1px solid #383B41;
    border-radius: 9px;
}

QRadioButton::indicator:hover {
    border: 1px solid #555961;
}

QRadioButton::indicator:checked {
    background-color: #E8E8EA;
    border: 4px solid #15171A;
}

/* =========================================================
TOOL BUTTON
========================================================= */

QToolButton {
    background-color: transparent;
    color: #A7AAB0;
    border: 1px solid transparent;
    border-radius: 7px;
    padding: 7px 9px;
}

QToolButton:hover {
    background-color: #202328;
    border: 1px solid #303339;
    color: #FFFFFF;
}

QToolButton:pressed {
    background-color: #181A1D;
    border: 1px solid #383B41;
}

QToolButton:checked {
    background-color: #292C31;
    border: 1px solid #41444A;
    color: #FFFFFF;
}

QToolButton:disabled {
    background-color: transparent;
    color: #55585E;
}

/* =========================================================
TABELAS
========================================================= */

QTableWidget,
QTableView {
    background-color: #15171A;
    alternate-background-color: #181A1E;
    color: #E8E8EA;
    border: 1px solid #292C31;
    border-radius: 9px;
    gridline-color: #292C31;
    outline: none;
}

QTableWidget::item,
QTableView::item {
    padding: 7px;
    border: none;
}

QTableWidget::item:hover,
QTableView::item:hover {
    background-color: #202328;
}

QTableWidget::item:selected,
QTableView::item:selected {
    background-color: #303339;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #1D1F23;
    color: #BFC1C5;
    border: none;
    border-bottom: 1px solid #303339;
    padding: 9px 10px;
    font-weight: 600;
}

QHeaderView::section:hover {
    background-color: #25282D;
    color: #FFFFFF;
}

/* =========================================================
LISTAS GERAIS
========================================================= */

QListWidget,
QListView {
    background-color: #15171A;
    color: #E8E8EA;
    border: 1px solid #292C31;
    border-radius: 9px;
    outline: none;
    padding: 4px;
}

QListWidget::item,
QListView::item {
    padding: 8px 10px;
    border-radius: 6px;
}

QListWidget::item:hover,
QListView::item:hover {
    background-color: #202328;
}

QListWidget::item:selected,
QListView::item:selected {
    background-color: #303339;
    color: #FFFFFF;
}

/* =========================================================
PROGRESS BAR
========================================================= */

QProgressBar {
    background-color: #15171A;
    color: #E8E8EA;
    border: 1px solid #292C31;
    border-radius: 7px;
    text-align: center;
    min-height: 14px;
}

QProgressBar::chunk {
    background-color: #777A80;
    border-radius: 5px;
}

/* =========================================================
SLIDER
========================================================= */

QSlider::groove:horizontal {
    height: 5px;
    background-color: #292C31;
    border-radius: 3px;
}

QSlider::handle:horizontal {
    width: 14px;
    height: 14px;
    margin: -5px 0;
    background-color: #D9DADF;
    border: 1px solid #FFFFFF;
    border-radius: 7px;
}

QSlider::handle:horizontal:hover {
    background-color: #FFFFFF;
}

QSlider::sub-page:horizontal {
    background-color: #666970;
    border-radius: 3px;
}

/* =========================================================
TOOLTIP
========================================================= */

QToolTip {
    background-color: #181A1E;
    color: #EEEEF0;
    border: 1px solid #363940;
    border-radius: 6px;
    padding: 6px 9px;
}

/* =========================================================
DIALOG
========================================================= */

QDialog {
    background-color: #0D0E10;
    color: #E8E8EA;
}

QDialog QLabel {
    background-color: transparent;
    color: #D9DADF;
}

/* =========================================================
LABELS DESABILITADOS
========================================================= */

QLabel:disabled {
    color: #55585E;
}

/* =========================================================
BOTÕES GENÉRICOS DESABILITADOS
========================================================= */

QPushButton:disabled,
QToolButton:disabled {
    background-color: #181A1D;
    color: #55585E;
    border-color: #25272B;
}

/* =========================================================
BOTÃO GENÉRICO
========================================================= */

QPushButton {
    background-color: #202328;
    color: #D9DADF;
    border: 1px solid #34373D;
    border-radius: 7px;
    padding: 8px 14px;
}

QPushButton:hover {
    background-color: #2C2F35;
    border: 1px solid #454850;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #191B1F;
    border: 1px solid #383B41;
}

QPushButton:disabled {
    background-color: #181A1D;
    color: #55585E;
    border: 1px solid #25272B;
}

/* =========================================================
MENUS GERAIS
========================================================= */

QMenu {
    background-color: #181A1E;
    color: #EEEEF0;
    border: 1px solid #363940;
    padding: 5px;
}

QMenu::item {
    background-color: transparent;
    color: #BFC1C5;
    padding: 9px 20px 9px 10px;
    margin: 1px;
    border-radius: 5px;
}

QMenu::item:selected {
    background-color: #2A2D33;
    color: #FFFFFF;
}

QMenu::item:disabled {
    color: #55585E;
}

QMenu::separator {
    height: 1px;
    background-color: #303339;
    margin: 5px 8px;
}

/* =========================================================
GROUP BOX
========================================================= */

QGroupBox {
    background-color: #15171A;
    color: #D9DADF;
    border: 1px solid #292C31;
    border-radius: 9px;
    margin-top: 12px;
    padding: 12px;
}

QGroupBox::title {
    background-color: #15171A;
    color: #BFC1C5;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}

/* =========================================================
TAB WIDGET
========================================================= */

QTabWidget::pane {
    background-color: #15171A;
    border: 1px solid #292C31;
    border-radius: 8px;
}

QTabBar::tab {
    background-color: #181A1E;
    color: #777A80;
    border: 1px solid #292C31;
    padding: 8px 14px;
    margin-right: 2px;
}

QTabBar::tab:hover {
    background-color: #22252A;
    color: #D9DADF;
}

QTabBar::tab:selected {
    background-color: #292C31;
    color: #FFFFFF;
    border-color: #41444A;
}

/* =========================================================
FRAME GENÉRICO
========================================================= */

QFrame {
    background-color: transparent;
}

/* =========================================================
STATUS BAR
========================================================= */

QStatusBar {
    background-color: #141518;
    color: #777A80;
    border-top: 1px solid #25272B;
}

QStatusBar::item {
    border: none;
}

/* =========================================================
TOOLBAR
========================================================= */

QToolBar {
    background-color: #141518;
    border: none;
    spacing: 5px;
    padding: 4px;
}

QToolBar::separator {
    background-color: #303339;
    width: 1px;
    margin: 5px 4px;
}

"""

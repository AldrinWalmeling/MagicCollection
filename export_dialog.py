from PySide6.QtCore import Qt

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMenu,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QMessageBox,
    QGroupBox,
    QFormLayout,
    QComboBox,
    QInputDialog,
)

from services.collection_export import (
    ExportConfig,
    export_collection_custom,
    get_all_export_presets,
    config_from_preset,
    save_export_preset,
    delete_export_preset,
    EXPORT_FIELDS,
)


class CollectionExportDialog(QDialog):
    """
    Janela para escolher exatamente quais campos serão exportados.

    Uso:

        dialog = CollectionExportDialog(cards, self)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            dialog.export_cards()
    """

    def __init__(
        self,
        cards,
        parent=None,
    ):
        super().__init__(parent)

        self.cards = list(cards or [])

        self.setWindowTitle(
            "Exportar coleção"
        )

        self.setMinimumSize(
            760,
            620,
        )

        self.setup_ui()
        self.load_preset(
            "Essencial"
        )

    # =====================================================
    # UI
    # =====================================================

    def setup_ui(self):

        layout = QVBoxLayout(self)

        layout.setContentsMargins(
            24,
            24,
            24,
            24,
        )

        layout.setSpacing(14)

        title = QLabel(
            "Exportar coleção"
        )

        title.setObjectName(
            "SectionTitle"
        )

        layout.addWidget(title)

        description = QLabel(
            "Escolha o formato e selecione exatamente "
            "quais informações deseja incluir."
        )

        description.setWordWrap(True)

        layout.addWidget(
            description
        )

        # =================================================
        # CONFIGURAÇÃO
        # =================================================

        config_group = QGroupBox(
            "Configuração"
        )

        form = QFormLayout(
            config_group
        )

        self.format_combo = QComboBox()

        self.format_combo.addItem(
            "CSV",
            "csv",
        )

        self.format_combo.addItem(
            "JSON",
            "json",
        )

        self.format_combo.addItem(
            "TXT",
            "txt",
        )

        form.addRow(
            "Formato:",
            self.format_combo,
        )

        self.preset_combo = QComboBox()

        self.reload_presets()

        self.preset_combo.currentTextChanged.connect(
            self._preset_changed
        )

        form.addRow(
            "Modelo:",
            self.preset_combo,
        )

        layout.addWidget(
            config_group
        )

        # =================================================
        # CAMPOS
        # =================================================

        fields_group = QGroupBox(
            "Campos da exportação"
        )

        fields_layout = QVBoxLayout(
            fields_group
        )

        fields_help = QLabel(
            "Marque os campos que deseja exportar. "
            "A ordem da lista será mantida."
        )

        fields_help.setWordWrap(True)

        fields_layout.addWidget(
            fields_help
        )

        self.fields_list = QListWidget()

        self.fields_list.setDragDropMode(
            QListWidget.DragDropMode.InternalMove
        )

        self.fields_list.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
        )

        for field_name, label in EXPORT_FIELDS.items():

            item = QListWidgetItem(
                label
            )

            item.setData(
                Qt.ItemDataRole.UserRole,
                field_name,
            )

            item.setCheckState(
                Qt.CheckState.Unchecked
            )

            self.fields_list.addItem(
                item
            )

        fields_layout.addWidget(
            self.fields_list,
            1,
        )

        buttons_row = QHBoxLayout()

        select_all = QPushButton(
            "Selecionar tudo"
        )

        select_all.clicked.connect(
            self.select_all
        )

        buttons_row.addWidget(
            select_all
        )

        clear_all = QPushButton(
            "Limpar"
        )

        clear_all.clicked.connect(
            self.clear_all
        )

        buttons_row.addWidget(
            clear_all
        )

        buttons_row.addStretch()

        save_preset = QPushButton(
            "Salvar como modelo"
        )

        save_preset.clicked.connect(
            self.save_current_preset
        )

        buttons_row.addWidget(
            save_preset
        )

        fields_layout.addLayout(
            buttons_row
        )

        layout.addWidget(
            fields_group,
            1,
        )

        # =================================================
        # RESUMO
        # =================================================

        self.summary_label = QLabel()

        self.summary_label.setWordWrap(True)

        layout.addWidget(
            self.summary_label
        )

        self.fields_list.itemChanged.connect(
            self.update_summary
        )

        # =================================================
        # BOTÕES
        # =================================================

        dialog_buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel
            |
            QDialogButtonBox.StandardButton.Ok
        )

        dialog_buttons.button(
            QDialogButtonBox.StandardButton.Ok
        ).setText(
            "Exportar"
        )

        dialog_buttons.accepted.connect(
            self.validate
        )

        dialog_buttons.rejected.connect(
            self.reject
        )

        layout.addWidget(
            dialog_buttons
        )

        self.update_summary()

    # =====================================================
    # PRESETS
    # =====================================================

    def reload_presets(self):

        current = self.preset_combo.currentText() \
            if hasattr(self, "preset_combo") \
            else ""

        self.preset_combo.clear()

        for name in get_all_export_presets():

            self.preset_combo.addItem(
                name
            )

        if current:

            index = self.preset_combo.findText(
                current
            )

            if index >= 0:
                self.preset_combo.setCurrentIndex(
                    index
                )

    def _preset_changed(
        self,
        preset_name,
    ):

        if not preset_name:
            return

        self.load_preset(
            preset_name
        )

    def load_preset(
        self,
        preset_name,
    ):

        config = config_from_preset(
            preset_name
        )

        wanted = set(
            config.fields
        )

        self.fields_list.blockSignals(
            True
        )

        for index in range(
            self.fields_list.count()
        ):

            item = self.fields_list.item(
                index
            )

            field_name = item.data(
                Qt.ItemDataRole.UserRole
            )

            item.setCheckState(
                Qt.CheckState.Checked
                if field_name in wanted
                else Qt.CheckState.Unchecked
            )

        self.fields_list.blockSignals(
            False
        )

        self.update_summary()

    # =====================================================
    # CAMPOS
    # =====================================================

    def select_all(self):

        self.fields_list.blockSignals(
            True
        )

        for index in range(
            self.fields_list.count()
        ):

            self.fields_list.item(
                index
            ).setCheckState(
                Qt.CheckState.Checked
            )

        self.fields_list.blockSignals(
            False
        )

        self.update_summary()

    def clear_all(self):

        self.fields_list.blockSignals(
            True
        )

        for index in range(
            self.fields_list.count()
        ):

            self.fields_list.item(
                index
            ).setCheckState(
                Qt.CheckState.Unchecked
            )

        self.fields_list.blockSignals(
            False
        )

        self.update_summary()

    def selected_fields(self):

        fields = []

        for index in range(
            self.fields_list.count()
        ):

            item = self.fields_list.item(
                index
            )

            if (
                item.checkState()
                == Qt.CheckState.Checked
            ):

                fields.append(
                    item.data(
                        Qt.ItemDataRole.UserRole
                    )
                )

        return fields

    # =====================================================
    # RESUMO
    # =====================================================

    def update_summary(self):

        fields = self.selected_fields()

        self.summary_label.setText(
            f"{len(fields)} campo(s) selecionado(s) "
            f"• {len(self.cards)} carta(s)"
        )

    # =====================================================
    # SALVAR MODELO
    # =====================================================

    def save_current_preset(self):



        fields = self.selected_fields()

        if not fields:

            QMessageBox.warning(
                self,
                "Nenhum campo",
                "Selecione pelo menos um campo.",
            )

            return

        name, ok = QInputDialog.getText(
            self,
            "Salvar modelo",
            "Nome do modelo:",
        )

        if not ok:
            return

        name = name.strip()

        if not name:
            return

        config = ExportConfig(
            format=self.format_combo.currentData(),
            fields=fields,
        )

        if not save_export_preset(
            name,
            config,
        ):

            QMessageBox.warning(
                self,
                "Erro",
                "Não foi possível salvar o modelo.",
            )

            return

        self.reload_presets()

        index = self.preset_combo.findText(
            name
        )

        if index >= 0:
            self.preset_combo.setCurrentIndex(
                index
            )

        QMessageBox.information(
            self,
            "Modelo salvo",
            f'O modelo "{name}" foi salvo.',
        )

    # =====================================================
    # VALIDAR
    # =====================================================

    def validate(self):

        fields = self.selected_fields()

        if not fields:

            QMessageBox.warning(
                self,
                "Nenhum campo selecionado",
                "Selecione pelo menos um campo.",
            )

            return

        self.accept()

    # =====================================================
    # CONFIG FINAL
    # =====================================================

    def get_config(self):

        return ExportConfig(
            format=self.format_combo.currentData(),
            fields=self.selected_fields(),
        )

    # =====================================================
    # EXPORTAR
    # =====================================================

    def export_cards(
        self,
        filepath=None,
    ):

        from services.collection_export import (
            export_collection_custom,
        )

        config = self.get_config()

        if not filepath:

            extension = config.format

            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar exportação",
                f"minha_colecao.{extension}",
                (
                    "CSV (*.csv)"
                    if extension == "csv"
                    else
                    "JSON (*.json)"
                    if extension == "json"
                    else
                    "Texto (*.txt)"
                ),
            )

        if not filepath:
            return False

        try:

            export_collection_custom(
                filepath,
                self.cards,
                config,
            )

        except Exception as error:

            QMessageBox.critical(
                self,
                "Erro na exportação",
                str(error),
            )

            return False

        QMessageBox.information(
            self,
            "Exportação concluída",
            "A coleção foi exportada com sucesso.",
        )

        return True


def open_collection_export_dialog(
    cards,
    parent=None,
):
    dialog = CollectionExportDialog(
        cards,
        parent,
    )

    if (
        dialog.exec()
        != QDialog.DialogCode.Accepted
    ):
        return False

    return dialog.export_cards()

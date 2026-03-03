import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Set, Optional, Tuple, Any

# =============================================================================
# 1. MÓDULO DE LÓGICA (BACKEND)
# =============================================================================
# -- Constantes --
KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NAMESPACE)
NS_MAP = {"kml": KML_NAMESPACE}


def extract_placemark_data(placemark: ET.Element) -> Dict[str, str]:
    """Extrai dados de um Placemark, suportando os formatos <Data> e <SimpleData>."""
    data_values: Dict[str, str] = {}
    for data in placemark.findall(".//kml:Data[@name]", NS_MAP):
        name = data.get("name")
        value_element = data.find("kml:value", NS_MAP)
        if name and value_element is not None and value_element.text:
            data_values[name] = value_element.text.strip()
    for simple_data in placemark.findall(".//kml:SchemaData/kml:SimpleData[@name]", NS_MAP):
        name = simple_data.get("name")
        if name and simple_data.text:
            data_values[name] = simple_data.text.strip()
    return data_values


def discover_and_group_models(root: ET.Element) -> Dict[Tuple[str, ...], List[ET.Element]]:
    """Analisa todos os Placemarks e os agrupa por "modelo" (conjunto de campos)."""
    models: Dict[Tuple[str, ...], List[ET.Element]] = {}
    for placemark in root.findall(".//kml:Placemark", NS_MAP):
        fields = extract_placemark_data(placemark)
        if not fields:
            continue
        model_signature = tuple(sorted(fields.keys()))
        models.setdefault(model_signature, []).append(placemark)
    return models


def rename_placemarks(placemarks: List[ET.Element], fields: List[str], separator: str, prefix: str, suffix: str) -> int:
    """
    Renomeia uma lista de Placemarks com base nos campos, separador, prefixo e sufixo.

    Args:
        placemarks: Lista de elementos ET.Element a serem renomeados.
        fields: Lista ordenada dos nomes dos campos a serem usados.
        separator: String para unir os valores dos campos.
        prefix: String a ser adicionada no início do novo nome.
        suffix: String a ser adicionada no final do novo nome.

    Returns:
        O número de marcadores que foram renomeados.
    """
    count = 0
    for placemark in placemarks:
        data_values = extract_placemark_data(placemark)
        new_name_parts: List[str] = [data_values.get(field, "") for field in fields]

        base_name = separator.join(new_name_parts)

        # Constrói o nome final com prefixo, nome base e sufixo
        new_name = f"{prefix}{base_name}{suffix}"

        name_element = placemark.find("kml:name", NS_MAP)
        if name_element is not None:
            name_element.text = new_name
        else:
            new_name_element = ET.Element(f"{{{KML_NAMESPACE}}}name")
            new_name_element.text = new_name
            placemark.insert(0, new_name_element)
        count += 1
    return count


# =============================================================================
# 2. INTERFACE GRÁFICA (FRONTEND)
# =============================================================================
try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
        QLabel, QListWidget, QListWidgetItem, QLineEdit, QGroupBox, QFormLayout,
        QCheckBox, QMessageBox
    )
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QFont
except ImportError:
    print("Erro: A biblioteca PyQt6 não está instalada.")
    print("Por favor, instale usando: pip install PyQt6")
    sys.exit(1)


class KMLRenamerApp(QWidget):
    """
    Interface gráfica para a ferramenta de renomeação de marcadores KML.
    """

    def __init__(self):
        super().__init__()
        self.kml_tree: Optional[ET.ElementTree] = None
        self.models: Dict[Tuple[str, ...], List[ET.Element]] = {}
        self.renaming_rules: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        self.input_path: Optional[str] = None
        self.output_path: Optional[str] = None
        self.current_model_signature: Optional[Tuple[str, ...]] = None
        self.current_selection_order: List[str] = []
        self.init_ui()

    def init_ui(self):
        """Inicializa e configura a interface do usuário."""
        self.setWindowTitle("Ferramenta de Renomeação de Marcadores KML v1.4")
        self.setGeometry(100, 100, 800, 650) # Aumentei a altura para caber o novo campo
        main_layout = QVBoxLayout(self)
        files_group = QGroupBox("1. Seleção de Arquivos")
        files_layout = QFormLayout()
        self.input_label = QLineEdit("Nenhum arquivo selecionado", readOnly=True)
        self.output_label = QLineEdit("Marcadores_Renomeados.kml")
        input_btn = QPushButton("Selecionar KML de Entrada...")
        output_btn = QPushButton("Definir KML de Saída...")
        input_btn.clicked.connect(self.select_input_file)
        output_btn.clicked.connect(self.select_output_file)
        files_layout.addRow(input_btn, self.input_label)
        files_layout.addRow(output_btn, self.output_label)
        files_group.setLayout(files_layout)
        content_layout = QHBoxLayout()
        models_group = QGroupBox("2. Modelos Encontrados")
        models_vbox = QVBoxLayout()
        self.models_list_widget = QListWidget()
        self.models_list_widget.currentItemChanged.connect(self.display_model_config)
        models_vbox.addWidget(self.models_list_widget)
        models_group.setLayout(models_vbox)
        config_group = QGroupBox("Configurar Novo Nome")
        self.config_layout = QVBoxLayout()
        self.config_placeholder = QLabel("Selecione um modelo da lista para configurar.")
        self.config_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.config_layout.addWidget(self.config_placeholder)
        config_group.setLayout(self.config_layout)
        content_layout.addWidget(models_group, 1)
        content_layout.addWidget(config_group, 2)
        self.process_btn = QPushButton("Renomear Marcadores")
        self.process_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.process_btn.clicked.connect(self.process_files)
        self.process_btn.setEnabled(False)
        main_layout.addWidget(files_group)
        main_layout.addLayout(content_layout)
        main_layout.addWidget(self.process_btn)

    def select_input_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Selecionar Arquivo KML", "", "KML Files (*.kml)")
        if path:
            self.input_path = path
            self.input_label.setText(path)
            self.load_and_discover_models()

    def select_output_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Salvar Arquivo KML Como...", self.output_label.text(),
                                              "KML Files (*.kml)")
        if path:
            self.output_path = path
            self.output_label.setText(path)

    def load_and_discover_models(self):
        if not self.input_path: return
        try:
            self.kml_tree = ET.parse(self.input_path)
            root = self.kml_tree.getroot()
            self.models = discover_and_group_models(root)
            self.models_list_widget.clear()
            self.renaming_rules.clear()
            self.process_btn.setEnabled(False)
            if not self.models:
                QMessageBox.information(self, "Informação", "Nenhum marcador com campos de dados foi encontrado.")
                return
            for i, (signature, placemarks) in enumerate(self.models.items()):
                item_text = f"Modelo {i + 1} ({len(placemarks)} marcadores)"
                item = QListWidgetItem(item_text)
                item.setData(Qt.ItemDataRole.UserRole, signature)
                self.models_list_widget.addItem(item)
            self.process_btn.setEnabled(True)
        except FileNotFoundError:
            QMessageBox.critical(self, "Erro", f"O arquivo '{self.input_path}' não foi encontrado.")
        except ET.ParseError:
            QMessageBox.critical(self, "Erro", f"O arquivo '{self.input_path}' não é um XML/KML válido.")

    def clear_config_layout(self):
        while self.config_layout.count():
            child = self.config_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def display_model_config(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        if not current_item:
            self.current_model_signature = None
            return
        self.clear_config_layout()
        self.current_model_signature = current_item.data(Qt.ItemDataRole.UserRole)
        self.current_selection_order = []
        placemarks_for_model = self.models.get(self.current_model_signature, [])
        example_data = {}
        if placemarks_for_model:
            example_data = extract_placemark_data(placemarks_for_model[0])

        # Bloco 3: Campos
        fields_group = QGroupBox("3. Campos Disponíveis (selecione na ordem desejada)")
        fields_vbox = QVBoxLayout()
        for field in self.current_model_signature:
            example_value = example_data.get(field, "...")
            checkbox_text = f"{field} (ex: {example_value})"
            checkbox = QCheckBox(checkbox_text)
            checkbox.setProperty("fieldName", field)
            checkbox.stateChanged.connect(self.on_checkbox_changed)
            fields_vbox.addWidget(checkbox)
        fields_group.setLayout(fields_vbox)

        # Bloco 4: Prefixo
        prefix_group = QGroupBox("4. Adicionar Texto Fixo (Prefixo)")
        prefix_layout = QFormLayout()
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("Ex: SEM IDENTIFICAÇÃO - ")
        self.prefix_input.textChanged.connect(self.update_rule)
        prefix_layout.addRow(QLabel("Texto a ser inserido ANTES:"), self.prefix_input)
        prefix_group.setLayout(prefix_layout)

        # NOVO: Bloco 5 para adicionar texto/sufixo
        suffix_group = QGroupBox("5. Adicionar Texto Fixo (Sufixo)")
        suffix_layout = QFormLayout()
        self.suffix_input = QLineEdit()
        self.suffix_input.setPlaceholderText("Ex: - OC03 - ")
        self.suffix_input.textChanged.connect(self.update_rule)
        suffix_layout.addRow(QLabel("Texto a ser inserido DEPOIS:"), self.suffix_input)
        suffix_group.setLayout(suffix_layout)

        # Bloco 6: Separador
        separator_group = QGroupBox("6. Separador")
        separator_layout = QFormLayout()
        self.separator_input = QLineEdit("/")
        self.separator_input.textChanged.connect(self.update_rule)
        separator_layout.addRow(QLabel("Separador a ser usado ENTRE os campos:"), self.separator_input)
        separator_group.setLayout(separator_layout)

        self.config_layout.addWidget(fields_group)
        self.config_layout.addWidget(prefix_group)
        self.config_layout.addWidget(suffix_group) # NOVO
        self.config_layout.addWidget(separator_group)
        self.config_layout.addStretch()
        self.update_rule()

    def on_checkbox_changed(self, state: int):
        checkbox = self.sender()
        field_name = checkbox.property("fieldName")
        if state == Qt.CheckState.Checked.value and field_name not in self.current_selection_order:
            self.current_selection_order.append(field_name)
        elif state == Qt.CheckState.Unchecked.value and field_name in self.current_selection_order:
            self.current_selection_order.remove(field_name)
        self.update_rule()

    def update_rule(self):
        if not self.current_model_signature:
            return

        # Usando try-except para evitar erros durante a inicialização da UI
        try:
            selected_fields = self.current_selection_order
            separator = self.separator_input.text()
            prefix = self.prefix_input.text()
            suffix = self.suffix_input.text() # NOVO
        except AttributeError:
            # Ocorre se a função for chamada antes dos widgets serem criados
            return

        if selected_fields:
            self.renaming_rules[self.current_model_signature] = {
                "fields": selected_fields,
                "separator": separator,
                "prefix": prefix,
                "suffix": suffix # NOVO
            }
        elif self.current_model_signature in self.renaming_rules:
            del self.renaming_rules[self.current_model_signature]

    def process_files(self):
        if not self.input_path or self.kml_tree is None:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um arquivo KML de entrada primeiro.")
            return
        self.output_path = self.output_label.text()
        if not self.output_path:
            QMessageBox.warning(self, "Aviso", "Por favor, defina um nome para o arquivo de saída.")
            return
        if not self.renaming_rules:
            QMessageBox.warning(self, "Aviso", "Nenhuma regra de renomeação foi configurada.")
            return
        total_renamed = 0
        for model_signature, rule in self.renaming_rules.items():
            placemarks_to_process = self.models[model_signature]

            # Obtém o prefixo e o novo sufixo da regra
            prefix = rule.get("prefix", "")
            suffix = rule.get("suffix", "") # NOVO
            renamed_count = rename_placemarks(
                placemarks_to_process, rule["fields"], rule["separator"], prefix, suffix
            )
            total_renamed += renamed_count
        try:
            self.kml_tree.write(self.output_path, encoding="utf-8", xml_declaration=True)
            QMessageBox.information(self, "Sucesso",
                                    f"{total_renamed} marcadores foram renomeados com sucesso!\n"
                                    f"Arquivo salvo como: {self.output_path}")
        except Exception as e:
            QMessageBox.critical(self, "Erro ao Salvar", f"Ocorreu um erro ao salvar o arquivo:\n{e}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ex = KMLRenamerApp()
    ex.show()
    sys.exit(app.exec())
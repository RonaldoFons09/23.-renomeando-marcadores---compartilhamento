# main_app.py
import sys
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any

try:
    from PyQt6.QtWidgets import (
        QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
        QLabel, QListWidget, QListWidgetItem, QLineEdit, QGroupBox, QFormLayout,
        QCheckBox, QMessageBox, QProgressDialog
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont
except ImportError:  # pragma: no cover
    print("Erro: A biblioteca PyQt6 não está instalada.")
    print("Por favor, instale usando: pip install PyQt6")
    sys.exit(1)

import kml_logic
from kml_logic import (
    discover_and_group_models,
    extract_placemark_data
)

# =============================================================================
# CLASSES WORKER PARA QTHREAD (ASSÍNCRONO)
# =============================================================================

class KMLProcessorWorker(QThread):
    """
    Worker que processa o arquivo KML em background.
    Emite sinais para desenhar barra de progresso e repassar erros ou sucesso para a Thread principal.
    """
    progress = pyqtSignal(int)
    finished = pyqtSignal(int, int)  # total_validos, total_reprovados
    error = pyqtSignal(str)

    def __init__(self, kml_tree, renaming_rules, models, output_path):
        super().__init__()
        self.kml_tree = kml_tree
        self.renaming_rules = renaming_rules
        self.models = models
        self.output_path = output_path
        self._is_running = True

    def run(self):
        try:
            total_validos = 0
            total_reprovados = 0
            
            # Limpa os Placemarks da raiz original localizando o <Folder> original
            parent_map = {c: p for p in self.kml_tree.getroot().iter() for c in p}
            placemarks = self.kml_tree.getroot().findall(f".//{{{kml_logic.KML_NAMESPACE}}}Placemark")
            for pm in placemarks:
                if not self._is_running: return
                if pm in parent_map:
                    parent_map[pm].remove(pm)

            # Encontra o <Document> principal
            document_element = self.kml_tree.getroot().find(f".//{{{kml_logic.KML_NAMESPACE}}}Document")
            if document_element is None:
                document_element = self.kml_tree.getroot()

            folder_validos = ET.SubElement(document_element, f"{{{kml_logic.KML_NAMESPACE}}}Folder")
            name_v = ET.SubElement(folder_validos, f"{{{kml_logic.KML_NAMESPACE}}}name")
            name_v.text = "Aprovados"

            folder_reprovados = ET.SubElement(document_element, f"{{{kml_logic.KML_NAMESPACE}}}Folder")
            name_r = ET.SubElement(folder_reprovados, f"{{{kml_logic.KML_NAMESPACE}}}name")
            name_r.text = "Reprovados"

            # Quantos grupos de modelos serão iterados pra o progresso?
            total_rules = sum(1 for rule in self.renaming_rules.values() if rule.get("fields") or rule.get("prefix") or rule.get("suffix"))
            current_rule_idx = 0

            for model_signature, rule in self.renaming_rules.items():
                if not self._is_running: return

                prefix = rule.get("prefix", "")
                suffix = rule.get("suffix", "")
                fields = rule.get("fields", [])

                if not fields and not prefix and not suffix:
                    continue

                placemarks_to_process = self.models[model_signature]

                # Renomeia (a lógica central pesada)
                validos, reprovados = kml_logic.rename_placemarks(
                    placemarks_to_process, fields, rule["separator"], prefix, suffix
                )
                
                for pm in validos: 
                    folder_validos.append(pm)
                for pm in reprovados: 
                    folder_reprovados.append(pm)
                    
                total_validos += len(validos)
                total_reprovados += len(reprovados)

                current_rule_idx += 1
                prog_pct = int((current_rule_idx / total_rules) * 90)  # 90% é processar os nos
                self.progress.emit(prog_pct)

            # Restantes 10% é do XML parser realizando I/O de disco
            if self._is_running:
                self.kml_tree.write(self.output_path, encoding="utf-8", xml_declaration=True)
                self.progress.emit(100)
                self.finished.emit(total_validos, total_reprovados)

        except Exception as e:
            self.error.emit(str(e))
            
    def stop(self):
        self._is_running = False

# =============================================================================
# INTERFACE GRÁFICA (PRINCIPAL)
# =============================================================================
class KMLRenamerApp(QWidget):
    """
    Interface gráfica para a ferramenta de renomeação de marcadores KML.
    (Seu código original)
    """

    def __init__(self):
        super().__init__()
        self.kml_tree: Optional[ET.ElementTree] = None
        self.models: Dict[Tuple[str, ...], List[ET.Element]] = {}
        self.renaming_rules: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        self.input_path: Optional[str] = None
        self.output_path: Optional[str] = None

        # --- Atributos de Estado da UI ---
        self.current_model_signature: Optional[Tuple[str, ...]] = None
        self.current_list_item: Optional[QListWidgetItem] = None  # <-- NOVO
        self.current_selection_order: List[str] = []
        self.field_checkboxes: List[QCheckBox] = []

        # Widgets do painel de configuração
        self.config_placeholder: QLabel = QLabel("Selecione um modelo da lista para configurar.")
        self.config_controls_widget: Optional[QWidget] = None
        self.fields_vbox: Optional[QVBoxLayout] = None
        self.prefix_input: QLineEdit = QLineEdit()
        self.suffix_input: QLineEdit = QLineEdit()
        self.separator_input: QLineEdit = QLineEdit()

        self.init_ui()

    def init_ui(self):
        """Inicializa e configura a interface do usuário."""
        self.setWindowTitle("Ferramenta de Renomeação de Marcadores KML")
        self.setGeometry(100, 100, 800, 650)
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

        # --- Painel de Configuração (Lado Direito) ---
        config_group = QGroupBox("Configurar Novo Nome")
        self.config_layout = QVBoxLayout()  # Layout principal do painel direito

        # 1. Placeholder (visível por padrão)
        self.config_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.config_layout.addWidget(self.config_placeholder)

        # 2. Contêiner de Controles (criado, mas oculto por padrão)
        self.config_controls_widget = QWidget()
        controls_layout = QVBoxLayout(self.config_controls_widget)
        controls_layout.setContentsMargins(0, 0, 0, 0)

        # 3. Campos Disponíveis (Dinâmico)
        fields_group = QGroupBox("3. Campos Disponíveis (selecione na ordem desejada)")
        self.fields_vbox = QVBoxLayout()
        fields_group.setLayout(self.fields_vbox)

        # 4. Prefixo (Estático)
        prefix_group = QGroupBox("4. Adicionar Texto Fixo (Prefixo)")
        prefix_layout = QFormLayout()
        self.prefix_input.setPlaceholderText("Ex: SEM IDENTIFICAÇÃO - ")
        self.prefix_input.textChanged.connect(self.update_rule)
        prefix_layout.addRow(QLabel("Texto a ser inserido ANTES:"), self.prefix_input)
        prefix_group.setLayout(prefix_layout)

        # 5. Sufixo (Estático)
        suffix_group = QGroupBox("5. Adicionar Texto Fixo (Sufixo)")
        suffix_layout = QFormLayout()
        self.suffix_input.setPlaceholderText("Ex: - OC03 - ")
        self.suffix_input.textChanged.connect(self.update_rule)
        suffix_layout.addRow(QLabel("Texto a ser inserido DEPOIS:"), self.suffix_input)
        suffix_group.setLayout(suffix_layout)

        # 6. Separador (Estático)
        separator_group = QGroupBox("6. Separador")
        separator_layout = QFormLayout()
        self.separator_input.textChanged.connect(self.update_rule)
        separator_layout.addRow(QLabel("Separador a ser usado ENTRE os campos:"), self.separator_input)
        separator_group.setLayout(separator_layout)

        # Adiciona os grupos estáticos ao contêiner de controles
        controls_layout.addWidget(fields_group)
        controls_layout.addWidget(prefix_group)
        controls_layout.addWidget(suffix_group)
        controls_layout.addWidget(separator_group)
        controls_layout.addStretch()

        # Adiciona o contêiner ao layout principal e o esconde
        self.config_layout.addWidget(self.config_controls_widget)
        self.config_controls_widget.hide()

        config_group.setLayout(self.config_layout)
        # --- Fim do Painel de Configuração ---

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
        """Carrega o KML, descobre modelos e reseta a UI de configuração."""
        if not self.input_path: return
        try:
            self.kml_tree = ET.parse(self.input_path)
            root = self.kml_tree.getroot()
            self.models = discover_and_group_models(root)
            self.models_list_widget.clear()
            self.renaming_rules.clear()

            # Reseta o painel de configuração para o estado inicial
            self.config_controls_widget.hide()
            self.config_placeholder.show()
            self.clear_dynamic_fields()  # Limpa checkboxes antigos
            self.current_model_signature = None
            self.current_list_item = None  # <-- NOVO

            self.process_btn.setEnabled(False)

            if not self.models:
                QMessageBox.information(self, "Informação", "Nenhum marcador com campos de dados foi encontrado.")
                return

            for i, (signature, placemarks) in enumerate(self.models.items()):
                item_text = f"Modelo {i + 1} ({len(placemarks)} marcadores)"
                item = QListWidgetItem(item_text)

                # Armazena dados no item
                item.setData(Qt.ItemDataRole.UserRole, signature)
                item.setData(Qt.ItemDataRole.UserRole + 1, item_text)  # <-- NOVO: Armazena texto original

                self.models_list_widget.addItem(item)

            self.process_btn.setEnabled(True)

        except FileNotFoundError:
            QMessageBox.critical(self, "Erro", f"O arquivo '{self.input_path}' não foi encontrado.")
        except ET.ParseError:
            QMessageBox.critical(self, "Erro", f"O arquivo '{self.input_path}' não é um XML/KML válido.")

    def clear_dynamic_fields(self):
        """Limpa apenas os widgets dinâmicos (checkboxes)."""
        self.field_checkboxes.clear()
        while self.fields_vbox.count():
            child = self.fields_vbox.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def display_model_config(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """Exibe o painel de configuração para o modelo KML selecionado."""

        # Se nenhum item estiver selecionado, reseta para o placeholder
        if not current_item:
            self.current_model_signature = None
            self.current_list_item = None  # <-- NOVO
            self.config_controls_widget.hide()
            self.config_placeholder.show()
            self.clear_dynamic_fields()
            return

        # Limpa os checkboxes do modelo *anterior*
        self.clear_dynamic_fields()

        # Define o estado atual
        self.current_model_signature = current_item.data(Qt.ItemDataRole.UserRole)
        self.current_list_item = current_item  # <-- NOVO

        existing_rule = self.renaming_rules.get(self.current_model_signature)
        self.current_selection_order = list(existing_rule.get("fields", [])) if existing_rule else []
        saved_fields_set = set(self.current_selection_order)

        placemarks_for_model = self.models.get(self.current_model_signature, [])
        example_data = {}
        if placemarks_for_model:
            example_data = extract_placemark_data(placemarks_for_model[0])

        # --- Cria os Checkboxes (Dinâmicos) ---
        for field in self.current_model_signature:
            example_value = example_data.get(field, "...")[:50]
            if len(example_data.get(field, "")) > 50:
                example_value += "..."

            # Traduz para o usuário na interface
            display_field = "Descrição" if field == "description" else field
            
            checkbox_text = f"{display_field} (ex: {example_value})"
            checkbox = QCheckBox(checkbox_text)
            checkbox.setProperty("fieldName", field)
            checkbox.stateChanged.connect(self.on_checkbox_changed)

            self.fields_vbox.addWidget(checkbox)
            self.field_checkboxes.append(checkbox)

        # --- Carrega dados existentes (se houver) nos widgets ESTÁTICOS ---

        # 1. Bloqueia sinais para evitar chamadas MÚLTIPLAS a update_rule
        for checkbox in self.field_checkboxes:
            checkbox.blockSignals(True)
        self.prefix_input.blockSignals(True)
        self.suffix_input.blockSignals(True)
        self.separator_input.blockSignals(True)

        # 2. Popula a UI com os dados salvos (ou define padrões)
        if existing_rule:
            self.prefix_input.setText(existing_rule.get("prefix", ""))
            self.suffix_input.setText(existing_rule.get("suffix", ""))
            self.separator_input.setText(existing_rule.get("separator", "/"))

            for checkbox in self.field_checkboxes:
                if checkbox.property("fieldName") in saved_fields_set:
                    checkbox.setChecked(True)
        else:
            # Define os padrões se for um modelo novo
            self.prefix_input.setText("")
            self.suffix_input.setText("")
            self.separator_input.setText("/")
            # Checkboxes já estão desmarcados por padrão

        # 3. Desbloqueia os sinais
        for checkbox in self.field_checkboxes:
            checkbox.blockSignals(False)
        self.prefix_input.blockSignals(False)
        self.suffix_input.blockSignals(False)
        self.separator_input.blockSignals(False)

        # 4. Exibe o painel de configuração
        self.config_placeholder.hide()
        self.config_controls_widget.show()

    def on_checkbox_changed(self, state: int):
        """Atualiza a ordem de seleção quando um checkbox é (des)marcado."""
        checkbox = self.sender()
        if not isinstance(checkbox, QCheckBox):
            return

        field_name = checkbox.property("fieldName")

        if state == Qt.CheckState.Checked.value and field_name not in self.current_selection_order:
            self.current_selection_order.append(field_name)
        elif state == Qt.CheckState.Unchecked.value and field_name in self.current_selection_order:
            self.current_selection_order.remove(field_name)

        self.update_rule()

    def update_rule(self):
        """Salva a configuração atual da UI na memória (self.renaming_rules)."""
        # <-- MODIFICADO: Verifica se o item da lista também existe
        if not self.current_model_signature or not self.current_list_item:
            return

        selected_fields = self.current_selection_order
        separator = self.separator_input.text()
        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()

        # --- NOVO: Lógica para atualizar o texto do item da lista ---
        original_text = self.current_list_item.data(Qt.ItemDataRole.UserRole + 1)
        configured_suffix = " ✓ Configurado"

        # Salva se *qualquer* campo de texto ou checkbox estiver preenchido.
        if selected_fields or prefix or suffix:
            self.renaming_rules[self.current_model_signature] = {
                "fields": selected_fields,
                "separator": separator,
                "prefix": prefix,
                "suffix": suffix
            }
            # Atualiza o texto se ainda não estiver atualizado
            if not self.current_list_item.text().endswith(configured_suffix):
                self.current_list_item.setText(original_text + configured_suffix)

        # Se tudo estiver vazio e uma regra antiga existir, remove.
        elif self.current_model_signature in self.renaming_rules:
            del self.renaming_rules[self.current_model_signature]
            # Reverte o texto para o original
            self.current_list_item.setText(original_text)

    def process_files(self):
        """Inicia o processo de renomeação com base nas regras configuradas."""
        if not self.input_path or self.kml_tree is None:
            QMessageBox.warning(self, "Aviso", "Por favor, selecione um arquivo KML de entrada primeiro.")
            return
        self.output_path = self.output_label.text()
        if not self.output_path:
            QMessageBox.warning(self, "Aviso", "Por favor, defina um nome para o arquivo de saída.")
            return

        # Garante que a regra visível no momento seja salva antes de processar
        self.update_rule()

        if not self.renaming_rules:
            QMessageBox.warning(self, "Aviso", "Nenhuma regra de renomeação foi configurada.")
            return

        self.process_btn.setEnabled(False)
        
        # Cria e configura a barra de progresso (Diálogo)
        self.progress_dialog = QProgressDialog("Processando arquivos KML...", "Cancelar", 0, 100, self)
        self.progress_dialog.setWindowTitle("Aguarde")
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        
        # Prepara a Thread Dinâmica
        self.worker = KMLProcessorWorker(self.kml_tree, self.renaming_rules, self.models, self.output_path)
        self.worker.progress.connect(self.progress_dialog.setValue)
        self.worker.finished.connect(self._on_processing_finished)
        self.worker.error.connect(self._on_processing_error)
        
        self.progress_dialog.canceled.connect(self.worker.stop)
        
        # Dá inicio
        self.progress_dialog.show()
        self.worker.start()

    def _on_processing_finished(self, total_validos, total_reprovados):
        """Callback acionado na Thread UI quando a QThread de processamento emitir sucesso."""
        self.process_btn.setEnabled(True)
        QMessageBox.information(self, "Sucesso",
                                f"Processamento concluído e salvo em {self.output_path}!\n\n"
                                f"• {total_validos} marcadores (Pasta: Aprovados)\n"
                                f"• {total_reprovados} marcadores (Pasta: Reprovados)")

    def _on_processing_error(self, err_msg):
        """Callback acionado pela QThread se houver quebra (como disco cheio)."""
        self.process_btn.setEnabled(True)
        self.progress_dialog.close()
        QMessageBox.critical(self, "Erro ao Salvar", f"Ocorreu um erro estrutural durante o salvamento:\n{err_msg}")


# =============================================================================
# PONTO DE ENTRADA DA APLICAÇÃO
# =============================================================================

if __name__ == "__main__":  # pragma: no cover
    app = QApplication(sys.argv)
    main_window = KMLRenamerApp()
    main_window.show()
    sys.exit(app.exec())
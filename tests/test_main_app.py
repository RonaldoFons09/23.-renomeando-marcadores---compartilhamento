import os
import xml.etree.ElementTree as ET

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QMessageBox

import kml_logic
from main_app import KMLRenamerApp

@pytest.fixture
def run_app(qapp):
    """Fixture básica pytest-qt"""
    pass


# ---- TESTES DO KMLRenamerApp ----
@pytest.fixture
def kml_app(qtbot):
    app = KMLRenamerApp()
    qtbot.addWidget(app)
    return app

def test_clear_dynamic_fields(kml_app):
    from PyQt6.QtWidgets import QCheckBox
    cb = QCheckBox("T")
    kml_app.fields_vbox.addWidget(cb)
    kml_app.clear_dynamic_fields()
    assert kml_app.fields_vbox.count() == 0

def test_app_init(kml_app):
    assert kml_app.windowTitle() == "Ferramenta de Renomeação de Marcadores KML"
    assert not kml_app.process_btn.isEnabled()

def test_select_input_file(kml_app, mocker):
    mock_file_dialog = mocker.patch('main_app.QFileDialog.getOpenFileName', return_value=("dummy.kml", "KML Files (*.kml)"))
    mock_load = mocker.patch.object(kml_app, 'load_and_discover_models')
    
    kml_app.select_input_file()
    
    assert kml_app.input_path == "dummy.kml"
    assert kml_app.input_label.text() == "dummy.kml"
    mock_load.assert_called_once()
    
def test_select_input_file_cancelado(kml_app, mocker):
    mocker.patch('main_app.QFileDialog.getOpenFileName', return_value=("", ""))
    kml_app.select_input_file()
    assert kml_app.input_path is None

def test_select_output_file(kml_app, mocker):
    mocker.patch('main_app.QFileDialog.getSaveFileName', return_value=("output.kml", ""))
    kml_app.select_output_file()
    assert kml_app.output_path == "output.kml"
    assert kml_app.output_label.text() == "output.kml"
    
def test_select_output_file_cancelado(kml_app, mocker):
    mocker.patch('main_app.QFileDialog.getSaveFileName', return_value=("", ""))
    kml_app.output_path = "velho.kml"
    kml_app.select_output_file()
    assert kml_app.output_path == "velho.kml"

def test_load_and_discover_models_sem_arquivo(kml_app):
    kml_app.input_path = None
    kml_app.load_and_discover_models()
    assert kml_app.kml_tree is None

def test_load_and_discover_models_arquivo_nao_encontrado(kml_app, mocker):
    mock_critical = mocker.patch.object(QMessageBox, 'critical')
    kml_app.input_path = "non_existent.kml"
    kml_app.load_and_discover_models()
    mock_critical.assert_called_once()
    assert "não foi encontrado" in mock_critical.call_args[0][2]

def test_load_and_discover_models_parse_error(kml_app, mocker, tmp_path):
    mock_critical = mocker.patch.object(QMessageBox, 'critical')
    invalid_kml = tmp_path / "invalid.kml"
    invalid_kml.write_text("<nao_fechado><bla>")
    kml_app.input_path = str(invalid_kml)
    kml_app.load_and_discover_models()
    mock_critical.assert_called_once()
    assert "não é um XML/KML válido" in mock_critical.call_args[0][2]

def test_load_and_discover_models_sucesso(kml_app, mocker, tmp_path):
    # Criaremos um arquivo KML válido vazio
    valid_kml = tmp_path / "vazio.kml"
    valid_kml.write_text('<kml xmlns="http://www.opengis.net/kml/2.2"><Document></Document></kml>')
    
    mock_info = mocker.patch.object(QMessageBox, 'information')
    kml_app.input_path = str(valid_kml)
    kml_app.load_and_discover_models()
    
    assert kml_app.kml_tree is not None
    # Deve avisar que não tem modelos
    mock_info.assert_called_once()
    assert "Nenhum marcador com campos de dados foi encontrado" in mock_info.call_args[0][2]

def test_load_and_discover_models_com_modelos(kml_app, tmp_path):
    kml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <kml xmlns="http://www.opengis.net/kml/2.2">
        <Document>
            <Placemark>
                <ExtendedData>
                    <Data name="Key"><value>Val</value></Data>
                </ExtendedData>
            </Placemark>
        </Document>
    </kml>
    """
    valid_kml = tmp_path / "com_modelo.kml"
    valid_kml.write_text(kml)
    
    kml_app.input_path = str(valid_kml)
    kml_app.load_and_discover_models()
    
    assert len(kml_app.models) == 1
    assert kml_app.models_list_widget.count() == 1
    assert kml_app.process_btn.isEnabled()

def test_display_model_config(kml_app, qtbot, mocker):
    sig = ("A", "B", "C")
    pm = ET.Element("Placemark")
    kml_app.models = {sig: [pm]}
    
    # Campo C com > 50 chars
    val_c = "X" * 60
    mocker.patch('main_app.extract_placemark_data', return_value={"A": "1", "B": "2", "C": val_c})
    
    # Pre-cria regra para simular restoring state
    kml_app.renaming_rules = {sig: {"fields": ["A", "B"], "prefix": "P_", "suffix": "_S", "separator": "-"}}

    kml_app.models_list_widget.addItem("Modelo 1")
    item = kml_app.models_list_widget.item(0)
    item.setData(Qt.ItemDataRole.UserRole, sig)
    item.setData(Qt.ItemDataRole.UserRole + 1, "Modelo 1")
    
    kml_app.display_model_config(item, None)
    
    assert kml_app.config_placeholder.isHidden()
    assert not kml_app.config_controls_widget.isHidden()
    assert len(kml_app.field_checkboxes) == 3
    assert kml_app.current_model_signature == sig
    assert kml_app.prefix_input.text() == "P_"
    assert kml_app.suffix_input.text() == "_S"
    assert kml_app.separator_input.text() == "-"

def test_display_model_config_vazio(kml_app):
    kml_app.display_model_config(None, None)
    assert kml_app.current_model_signature is None
    assert not kml_app.config_placeholder.isHidden()
    assert kml_app.config_controls_widget.isHidden()

def test_on_checkbox_changed(kml_app, mocker, qtbot):
    # Configura um item selecionado primeiramente
    sig = ("A", "B")
    pm = ET.Element("Placemark")
    kml_app.models = {sig: [pm]}
    mocker.patch('main_app.extract_placemark_data', return_value={"A": "1", "B": "2"})
    
    kml_app.models_list_widget.addItem("Modelo Teste")
    item = kml_app.models_list_widget.item(0)
    item.setData(Qt.ItemDataRole.UserRole, sig)
    item.setData(Qt.ItemDataRole.UserRole + 1, "Modelo Teste")
    
    kml_app.display_model_config(item, None)
    assert kml_app.current_model_signature == sig
    
    cb_a = kml_app.field_checkboxes[0]
    
    assert "A" not in kml_app.current_selection_order
    # Clica
    cb_a.setChecked(True)
    assert "A" in kml_app.current_selection_order
    assert sig in kml_app.renaming_rules
    assert kml_app.renaming_rules[sig]["fields"] == ["A"]
    
    # Teste de um sender não apropriado (chamada direta = sender é None)
    kml_app.on_checkbox_changed(Qt.CheckState.Checked.value)
    
    cb_a.setChecked(False)
    assert "A" not in kml_app.current_selection_order
    # A regra deve ser deletada se ficar vazia via update_rule
    assert sig not in kml_app.renaming_rules

def test_update_rule_remove_existing(kml_app, mocker):
    sig = ("A",)
    pm = ET.Element("Placemark")
    kml_app.models = {sig: [pm]}
    mocker.patch('main_app.extract_placemark_data', return_value={"A": "1"})
    
    kml_app.models_list_widget.addItem("Modelo 1")
    item = kml_app.models_list_widget.item(0)
    item.setData(Qt.ItemDataRole.UserRole, sig)
    item.setData(Qt.ItemDataRole.UserRole + 1, "Modelo 1")
    
    kml_app.display_model_config(item, None)
    
    kml_app.renaming_rules[sig] = {"fields": ["A"], "prefix": "", "suffix": "", "separator": "-"}
    # simula limpeza
    kml_app.current_selection_order = []
    kml_app.separator_input.setText("-")
    kml_app.prefix_input.setText("")
    kml_app.suffix_input.setText("")
    kml_app.update_rule()
    
    assert sig not in kml_app.renaming_rules
    assert item.text() == "Modelo 1"

def test_process_files_erros(kml_app, mocker):
    mock_warn = mocker.patch.object(QMessageBox, 'warning')
    
    kml_app.process_files()
    mock_warn.assert_called_with(kml_app, "Aviso", "Por favor, selecione um arquivo KML de entrada primeiro.")
    
    kml_app.input_path = "in.kml"
    kml_app.kml_tree = "fake"
    kml_app.output_label.setText("")
    kml_app.process_files()
    mock_warn.assert_called_with(kml_app, "Aviso", "Por favor, defina um nome para o arquivo de saída.")

    kml_app.output_label.setText("out.kml")
    kml_app.renaming_rules = {}
    kml_app.process_files()
    mock_warn.assert_called_with(kml_app, "Aviso", "Nenhuma regra de renomeação foi configurada.")

def test_process_files_sucesso(kml_app, mocker, tmp_path):
    mock_info = mocker.patch.object(QMessageBox, 'information')
    out_file = tmp_path / "out.kml"
    kml_app.input_path = "in.kml"
    kml_app.output_label.setText(str(out_file))
    
    # Prepara mock de arvore
    fake_root = ET.Element(f"{{{kml_logic.KML_NAMESPACE}}}kml")
    kml_tree_mock = mocker.Mock()
    kml_tree_mock.getroot.return_value = fake_root
    kml_app.kml_tree = kml_tree_mock
    
    sig1 = ("A",)
    sig2 = ("B",)
    kml_app.models = {sig1: ["F1"], sig2: ["F2"]}
    
    # sig 1: normal, sig 2: vazio (deve continuar/pular)
    kml_app.renaming_rules = {
        sig1: {"fields": ["A"], "prefix": "", "suffix": "", "separator": "-"},
        sig2: {"fields": [], "prefix": "", "suffix": "", "separator": ""}
    }
    
    fake_pm_v = ET.Element("PlacemarkFake1")
    fake_pm_r = ET.Element("PlacemarkFakeR1")
    mock_rename = mocker.patch('kml_logic.rename_placemarks', return_value=([fake_pm_v], [fake_pm_r]))
    
    kml_app.process_files()
    
    mock_rename.assert_called_once()
    assert "Processamento conclu" in mock_info.call_args[0][2]
    assert "Aprovados" in mock_info.call_args[0][2]

def test_process_files_exception_write(kml_app, mocker, tmp_path):
    mock_crit = mocker.patch.object(QMessageBox, 'critical')
    out_file = tmp_path / "out.kml"
    kml_app.input_path = "in.kml"
    kml_app.output_label.setText(str(out_file))
    
    fake_root = ET.Element(f"{{{kml_logic.KML_NAMESPACE}}}kml")
    kml_tree_mock = mocker.Mock()
    kml_tree_mock.getroot.return_value = fake_root
    
    kml_tree_mock.write.side_effect = Exception("Disco cheio")
    kml_app.kml_tree = kml_tree_mock
    
    sig = ("A",)
    kml_app.models = {sig: ["PlacemarkFake1"]}
    kml_app.renaming_rules = {sig: {"fields": ["A"], "prefix": "", "suffix": "", "separator": "-"}}
    
    fake_pm = ET.Element("valid")
    mocker.patch('kml_logic.rename_placemarks', return_value=([fake_pm], []))
    
    kml_app.process_files()
    
    mock_crit.assert_called_once()
    assert "Disco cheio" in mock_crit.call_args[0][2]

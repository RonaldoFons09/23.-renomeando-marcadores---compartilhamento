import pytest
import xml.etree.ElementTree as ET
from kml_logic import (
    extract_placemark_data,
    discover_and_group_models,
    rename_placemarks,
    KML_NAMESPACE,
    extract_altura_dan,
    clean_only_numbers
)

def criar_placemark_data():
    """Helper para criar um Placemark com dados no formato <Data>."""
    kml = f"""
    <Placemark xmlns="{KML_NAMESPACE}">
        <ExtendedData>
            <Data name="Codigo"><value>123</value></Data>
            <Data name="Tipo"><value>Poste</value></Data>
        </ExtendedData>
    </Placemark>
    """
    return ET.fromstring(kml)

def criar_placemark_schema_data():
    """Helper para criar um Placemark com dados no formato <SchemaData>."""
    kml = f"""
    <Placemark xmlns="{KML_NAMESPACE}">
        <ExtendedData>
            <SchemaData schemaUrl="#Model">
                <SimpleData name="ID">456</SimpleData>
                <SimpleData name="Estado">Ativo</SimpleData>
            </SchemaData>
        </ExtendedData>
    </Placemark>
    """
    return ET.fromstring(kml)

def test_extract_placemark_data_formato_data():
    pm = criar_placemark_data()
    dados = extract_placemark_data(pm)
    assert dados == {"Codigo": "123", "Tipo": "Poste"}

def test_extract_placemark_data_formato_schemadata():
    pm = criar_placemark_schema_data()
    dados = extract_placemark_data(pm)
    assert dados == {"ID": "456", "Estado": "Ativo"}

def test_extract_placemark_data_formato_description():
    kml = f"""
    <Placemark xmlns="{KML_NAMESPACE}">
        <name>Teste</name>
        <description><![CDATA[P-300/12<br>Outro dado]]></description>
    </Placemark>
    """
    pm = ET.fromstring(kml)
    dados = extract_placemark_data(pm)
    assert "description" in dados
    assert "P-300/12" in dados["description"]

def test_extract_placemark_sem_dados():
    kml = f'<Placemark xmlns="{KML_NAMESPACE}"><name>Lixo</name></Placemark>'
    pm = ET.fromstring(kml)
    dados = extract_placemark_data(pm)
    assert dados == {}

def test_discover_and_group_models():
    kml = f"""
    <kml xmlns="{KML_NAMESPACE}">
        <Document>
            <Placemark>
                <ExtendedData>
                    <Data name="CampoA"><value>A1</value></Data>
                    <Data name="CampoB"><value>B1</value></Data>
                </ExtendedData>
            </Placemark>
            <Placemark>
                <ExtendedData>
                    <Data name="CampoB"><value>B2</value></Data>
                    <Data name="CampoA"><value>A2</value></Data>
                </ExtendedData>
            </Placemark>
            <Placemark>
                <ExtendedData>
                    <Data name="CampoC"><value>C1</value></Data>
                </ExtendedData>
            </Placemark>
            <!-- Placemark sem dados, deve ser ignorado -->
            <Placemark></Placemark>
        </Document>
    </kml>
    """
    root = ET.fromstring(kml)
    models = discover_and_group_models(root)

    # Assinaturas devem estar ordenadas alfabeticamente
    sig_ab = ('CampoA', 'CampoB')
    sig_c = ('CampoC',)

    assert len(models) == 2
    assert sig_ab in models
    assert sig_c in models

    assert len(models[sig_ab]) == 2
    assert len(models[sig_c]) == 1

def test_rename_placemarks_sem_nome_existente():
    pm = criar_placemark_data() # Tem Codigo=123 e Tipo=Poste, mas não tem tag <name>
    placemarks = [pm]
    fields = ["Tipo", "Codigo"]
    
    validos, reprovados = rename_placemarks(placemarks, fields, "-", "PRE_", "_POS")
    
    # Sem a tag name original, como o DAN 123 é detectado mas não há altura,
    # ele será tratado como "reprovado".
    assert len(validos) == 0
    assert len(reprovados) == 1
    
    # Verifica o elemento name no reprovado
    name_el = reprovados[0].find("kml:name", {"kml": KML_NAMESPACE})
    assert name_el is not None
    assert name_el.text == "PRE_-123_POS"

def test_rename_placemarks_com_nome_existente():
    kml = f"""
    <Placemark xmlns="{KML_NAMESPACE}">
        <name>NOME_ANTIGO</name>
        <ExtendedData>
            <Data name="Key"><value>Val</value></Data>
        </ExtendedData>
    </Placemark>
    """
    pm = ET.fromstring(kml)
    validos, reprovados = rename_placemarks([pm], ["Key"], " ", "A_", "_B")
    
    assert len(validos) == 0
    assert len(reprovados) == 1
    name_el = reprovados[0].find("kml:name", {"kml": KML_NAMESPACE})
    assert name_el.text == "A_Val_B"

def test_rename_placemarks_campo_inexistente():
    pm = criar_placemark_data() # Tem Codigo=123 e Tipo=Poste
    validos, reprovados = rename_placemarks([pm], ["Tipo", "Inexistente", "Codigo"], "_", "", "")
    
    assert len(validos) == 1
    assert len(reprovados) == 0
    name_el = validos[0].find("kml:name", {"kml": KML_NAMESPACE})
    assert name_el.text == "Poste__123"

def test_extract_altura_dan():
    assert extract_altura_dan("P-300/11") == ("300", "11")
    assert extract_altura_dan("11-300") == ("300", "11") # <- Ordem forçada
    assert extract_altura_dan("P-150/9") == ("150", "9")
    assert extract_altura_dan("nada aqui") == ("", "")
    assert extract_altura_dan("P") == ("", "")
    assert extract_altura_dan("so altura 10") == ("", "")
    assert extract_altura_dan("so_dan 600") == ("", "")

def test_clean_only_numbers():
    assert clean_only_numbers("abc123def456") == "123456"
    assert clean_only_numbers("10-00") == "1000"
    assert clean_only_numbers("texto puro") == ""

def test_rename_placemarks_1_campo_valid():
    pm = criar_placemark_data()
    # Adicionando valor válido de dan/altura
    pm.find(".//kml:Data[@name='Codigo']/kml:value", {"kml": KML_NAMESPACE}).text = "P-600/12"
    validos, reprovados = rename_placemarks([pm], ["Codigo"], "-", "P_", "_S")
    assert len(validos) == 1
    assert len(reprovados) == 0
    assert validos[0].find("kml:name", {"kml": KML_NAMESPACE}).text == "P_600-12_S"

def test_rename_placemarks_1_campo_invalid():
    pm = criar_placemark_data() # Codigo: 123 (só DAN)
    validos, reprovados = rename_placemarks([pm], ["Codigo"], "-", "P_", "_S")
    assert len(validos) == 0
    assert len(reprovados) == 1
    assert reprovados[0].find("kml:name", {"kml": KML_NAMESPACE}).text == "P_123_S"

def test_rename_placemarks_2_campos():
    pm = criar_placemark_data() # Codigo: 123, Tipo: Poste
    pm.find(".//kml:Data[@name='Codigo']/kml:value", {"kml": KML_NAMESPACE}).text = "P-300"
    pm.find(".//kml:Data[@name='Tipo']/kml:value", {"kml": KML_NAMESPACE}).text = "A-11"
    validos, reprovados = rename_placemarks([pm], ["Codigo", "Tipo"], "-", "", "")
    assert len(validos) == 1
    assert len(reprovados) == 0
    assert validos[0].find("kml:name", {"kml": KML_NAMESPACE}).text == "300-11"

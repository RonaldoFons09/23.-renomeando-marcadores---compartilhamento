import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

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
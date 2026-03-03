# -*- coding: utf-8 -*-
"""
Módulo de Lógica KML

Este módulo fornece funções para analisar, processar e modificar
arquivos KML, especificamente para extrair dados de Placemarks e
renomeá-los com base em regras.
"""

import xml.etree.ElementTree as ET
import re
from typing import Dict, List, Tuple

# -- Constantes --
KML_NAMESPACE = "http://www.opengis.net/kml/2.2"
ET.register_namespace("", KML_NAMESPACE)
NS_MAP = {"kml": KML_NAMESPACE}


def extract_placemark_data(placemark: ET.Element) -> Dict[str, str]:
    """Extrai dados de um Placemark, suportando <Data> e <SimpleData>.

    Busca por dados tanto no formato <ExtendedData><Data name="">
    quanto no formato <ExtendedData><SchemaData><SimpleData name="">.

    Args:
        placemark: O elemento ET.Element do Placemark a ser analisado.

    Returns:
        Um dicionário onde as chaves são os 'name' dos campos e os
        valores são os textos contidos neles.
    """
    data_values: Dict[str, str] = {}

    # Formato <Data name="..."><value>...</value></Data>
    for data in placemark.findall(".//kml:Data[@name]", NS_MAP):
        name = data.get("name")
        value_element = data.find("kml:value", NS_MAP)
        if name and value_element is not None and value_element.text:
            data_values[name] = value_element.text.strip()

    # Formato <SchemaData><SimpleData name="...">...</SimpleData></SchemaData>
    for simple_data in placemark.findall(".//kml:SchemaData/kml:SimpleData[@name]", NS_MAP):
        name = simple_data.get("name")
        if name and simple_data.text:
            data_values[name] = simple_data.text.strip()

    # Formato <description>...</description>
    description_element = placemark.find("kml:description", NS_MAP)
    if description_element is not None and description_element.text:
        # Extrai e limpa tags HTML inseridas via CDATA ou texto raw
        clean_desc = re.sub(r'<[^>]+>', ' ', description_element.text)
        # Substitui mltiplos espaos por um s 
        clean_desc = re.sub(r'\s+', ' ', clean_desc).strip()
        data_values["description"] = clean_desc

    return data_values


def discover_and_group_models(root: ET.Element) -> Dict[Tuple[str, ...], List[ET.Element]]:
    """Analisa todos os Placemarks e os agrupa por "modelo" (conjunto de campos).

    Um "modelo" é definido pelo conjunto único de chaves (nomes dos campos)
    presentes nos dados de um Placemark.

    Args:
        root: O elemento raiz (ET.Element) da árvore KML.

    Returns:
        Um dicionário onde as chaves são tuplas ordenadas dos nomes dos campos
        (a "assinatura" do modelo) e os valores são listas de Placemarks
        (ET.Element) que correspondem a esse modelo.
    """
    models: Dict[Tuple[str, ...], List[ET.Element]] = {}
    for placemark in root.findall(".//kml:Placemark", NS_MAP):
        fields = extract_placemark_data(placemark)
        if not fields:
            continue

        # A assinatura do modelo é a tupla ordenada das chaves
        model_signature = tuple(sorted(fields.keys()))
        models.setdefault(model_signature, []).append(placemark)

    return models


def extract_altura_dan(texto: str) -> Tuple[str, str]:
    """
    Busca valores correspondentes a Altura (6-14) e DAN (100-2000).
    Retorna os valores SEMPRE na ordem (DAN, Altura), ignorando a ordem original.
    """
    numeros = [int(n) for n in re.findall(r'\d+', texto)]
    altura = None
    dan = None
    
    for num in numeros:
        if 6 <= num <= 14 and altura is None:
            altura = num
        elif 100 <= num <= 2000 and dan is None:
            dan = num
            
    if altura is not None and dan is not None:
        return str(dan), str(altura) # DAN sempre primeiro
    return "", ""

def clean_only_numbers(texto: str) -> str:
    """Elimina letras e caracteres especiais, mantendo apenas números."""
    return re.sub(r'\D', '', texto)

def rename_placemarks(placemarks: List[ET.Element], fields: List[str], separator: str, prefix: str, suffix: str) -> Tuple[List[ET.Element], List[ET.Element]]:
    """
    Renomeia uma lista de Placemarks com base nos campos, separador, prefixo e sufixo.
    Separa os marcadores em "válidos" (que possuem DAN e Altura) e "reprovados".

    Modifica o elemento <name> de cada Placemark in-loco. Se <name> não
    existir, ele será criado.

    Args:
        placemarks: Lista de elementos ET.Element (Placemark) a serem renomeados.
        fields: Lista ordenada dos nomes dos campos a serem usados no nome.
        separator: String para unir os valores dos campos.
        prefix: String a ser adicionada no início do novo nome.
        suffix: String a ser adicionada no final do novo nome.

    Returns:
        Uma tupla contendo duas listas: (marcadores_validos, marcadores_reprovados)
    """
    validos = []
    reprovados = []

    for placemark in placemarks:
        data_values = extract_placemark_data(placemark)
        is_valid = False

        if len(fields) == 1:
            texto_bruto = data_values.get(fields[0], "")
            dan_val, altura_val = extract_altura_dan(texto_bruto)
            if dan_val and altura_val:
                base_name = f"{dan_val}{separator}{altura_val}"
                is_valid = True
            else:
                base_name = texto_bruto
        elif len(fields) == 2:
            # Tenta extrair combinando os dois campos
            texto_combinado = f"{data_values.get(fields[0], '')} {data_values.get(fields[1], '')}"
            dan_val, altura_val = extract_altura_dan(texto_combinado)
            
            if dan_val and altura_val:
               base_name = f"{dan_val}{separator}{altura_val}"
               is_valid = True
            else:
                valores_limpos = [clean_only_numbers(data_values.get(f, "")) for f in fields]
                base_name = separator.join(valores_limpos)
        else:
            new_name_parts = [data_values.get(field, "") for field in fields]
            base_name = separator.join(new_name_parts)

        # Adiciona prefixo e sufixo
        new_name = f"{prefix}{base_name}{suffix}"

        name_element = placemark.find("kml:name", NS_MAP)
        if name_element is not None:
            name_element.text = new_name
        else:
            # Cria o elemento <name> se não existir
            new_name_element = ET.Element(f"{{{KML_NAMESPACE}}}name")
            new_name_element.text = new_name
            placemark.insert(0, new_name_element)  # Insere como primeiro filho

        if is_valid or len(fields) not in (1, 2): 
             # Se for mais de 2 campos (modo legado), consideramos válido pois não há filtro estrito de dan/altura
             validos.append(placemark)
        else:
             reprovados.append(placemark)

    return validos, reprovados
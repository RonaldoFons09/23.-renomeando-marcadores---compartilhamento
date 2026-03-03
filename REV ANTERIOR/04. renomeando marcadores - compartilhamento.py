import xml.etree.ElementTree as ET

# Função para buscar os valores de 01.altura, 02.esforco e 03.rede e renomear os placemarks
def calcular_total_altura_esforco_rede(root):
    folder = root.find('.//{http://www.opengis.net/kml/2.2}Folder')
    marcadores_a_renomear = []

    for placemark in folder.findall('.//{http://www.opengis.net/kml/2.2}Placemark'):
        # Procurar o valor de 01.altura, 02.esforco e 03.rede
        altura_element = placemark.find('.//{http://www.opengis.net/kml/2.2}Data[@name="1.altura"]')
        esforco_element = placemark.find('.//{http://www.opengis.net/kml/2.2}Data[@name="2.esforco"]')
        rede_element = placemark.find('.//{http://www.opengis.net/kml/2.2}Data[@name="3.rede"]')

        if altura_element is not None and esforco_element is not None and rede_element is not None:
            altura_value_element = altura_element.find('.//{http://www.opengis.net/kml/2.2}value')
            esforco_value_element = esforco_element.find('.//{http://www.opengis.net/kml/2.2}value')
            rede_value_element = rede_element.find('.//{http://www.opengis.net/kml/2.2}value')

            if altura_value_element is not None and esforco_value_element is not None and rede_value_element is not None:
                altura = altura_value_element.text
                esforco = esforco_value_element.text
                rede = rede_value_element.text

                # Adicionar o placemark para renomear se todos os valores estiverem presentes
                if altura and esforco and rede:
                    marcadores_a_renomear.append((placemark, altura, rede, esforco))

    return marcadores_a_renomear

# Função para ler o arquivo KML
def ler_arquivo_kml(arquivo):
    tree = ET.parse(arquivo)
    return tree

# Função para renomear os marcadores com base nos valores de altura, rede e esforço
def renomear_marcadores_altura_rede_esforco(arquivo_kml, arquivo_saida):
    tree = ler_arquivo_kml(arquivo_kml)
    root = tree.getroot()

    marcadores_a_renomear = calcular_total_altura_esforco_rede(root)

    # Renomear os placemarks com o formato "altura / rede / esforço"
    for placemark, altura, rede, esforco in marcadores_a_renomear:
        name_element = placemark.find('.//{http://www.opengis.net/kml/2.2}name')
        if name_element is not None:
            name_element.text = f"{esforco}/{altura}  {rede}"

    # Salvar o arquivo KML modificado em um novo arquivo
    tree.write(arquivo_saida, encoding="utf-8", xml_declaration=True)

    print(f"Arquivo salvo como {arquivo_saida} com os marcadores renomeados.")

# Função principal
def main():
    arquivo_kml = 'Concessionaria.kml'

    # Renomear os marcadores no arquivo original e salvar em um novo arquivo
    renomear_marcadores_altura_rede_esforco(arquivo_kml, 'Concessionária_Renomeada.kml')


if __name__ == "__main__":
    main()

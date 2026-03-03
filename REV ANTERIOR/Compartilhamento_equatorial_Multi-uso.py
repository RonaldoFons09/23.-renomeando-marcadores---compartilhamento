import re
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Optional, Tuple, List

import pyproj
from lxml import etree
from lxml.etree import _Element as LxmlElement

# --- Constantes de Configuração ---

# Projeções geoespaciais
WGS84_CRS = "EPSG:4326"
UTM_23S_CRS = "EPSG:32723"  # SIRGAS 2000 / UTM zone 23S

# Otimização: Criar o transformador de projeção uma única vez
TRANSFORMER = pyproj.Transformer.from_crs(
    pyproj.CRS(WGS84_CRS), pyproj.CRS(UTM_23S_CRS), always_xy=True
)

# Namespace do KML
KML_NAMESPACE = {'kml': 'http://www.opengis.net/kml/2.2'}
KML_NS_URI = KML_NAMESPACE['kml']

# Regras de validação para os marcadores
MIN_ESFORCO_VAL = 100
MAX_ESFORCO_VAL = 1200
MIN_ALTURA_VAL = 9
MAX_ALTURA_VAL = 12

# Nomes padrão para os campos de dados
DEFAULT_ESFORCO_NAMES = ["DESCR_ESF", "Esforco", "esforco"]
DEFAULT_ALTURA_NAMES = ["DESCR_ALT", "Altura", "altura"]

# Nomes das pastas de saída no KML
FORMATTED_FOLDER_NAME = "Marcadores Formatados"
IGNORED_FOLDER_NAME = "Marcadores Ignorados"


# --- Funções de Processamento KML ---

def convert_to_utm(lat: float, lon: float) -> Tuple[float, float]:
    """Converte coordenadas Geográficas (WGS84) para UTM (SIRGAS 2000 / Zona 23S)."""
    return TRANSFORMER.transform(lon, lat)


def find_title_pattern(name: str) -> Optional[str]:
    """Busca por um padrão 'número/número' no nome do marcador e valida seus valores."""
    if not name:
        return None
    match = re.search(r'(\d+)/(\d+)', name)
    if match:
        num1, num2 = int(match.group(1)), int(match.group(2))
        if MIN_ESFORCO_VAL <= num1 <= MAX_ESFORCO_VAL and MIN_ALTURA_VAL <= num2 <= MAX_ALTURA_VAL:
            return match.group(0)
    return None


def _extract_numeric_value(text: Optional[str]) -> Optional[float]:
    """Extrai o primeiro valor numérico de uma string de forma segura."""
    if text is None:
        return None
    # Remove caracteres não numéricos, exceto ponto e sinal de menos
    cleaned_text = re.sub(r'[^\d.-]', '', text.strip())
    try:
        return float(cleaned_text)
    except (ValueError, TypeError):
        return None


def extract_extended_data(
        extended_data_elem: Optional[LxmlElement],
        esforco_tags: List[str],
        altura_tags: List[str]
) -> Tuple[Optional[str], Optional[str]]:
    """Extrai os valores de esforço e altura dos dados estendidos de um Placemark."""
    if extended_data_elem is None:
        return None, None

    esforco = altura = None

    def find_data_in_elements(elements: List[LxmlElement], esforco_keys: List[str], altura_keys: List[str]):
        """Função aninhada para buscar dados em uma lista de elementos."""
        found_esforco = found_altura = None
        for data_elem in elements:
            name_attr = data_elem.get('name')
            if name_attr:
                value_elem = data_elem.find('kml:value', namespaces=KML_NAMESPACE)
                text_content = value_elem.text if value_elem is not None else data_elem.text

                if not found_esforco and name_attr in esforco_keys:
                    found_esforco = text_content
                if not found_altura and name_attr in altura_keys:
                    found_altura = text_content
        return found_esforco, found_altura

    data_elements = extended_data_elem.findall('kml:Data', namespaces=KML_NAMESPACE)
    esforco, altura = find_data_in_elements(data_elements, esforco_tags, altura_tags)

    if esforco is None or altura is None:
        for schema_data in extended_data_elem.findall('kml:SchemaData', namespaces=KML_NAMESPACE):
            simple_data_elements = schema_data.findall('kml:SimpleData', namespaces=KML_NAMESPACE)
            temp_esforco, temp_altura = find_data_in_elements(simple_data_elements, esforco_tags, altura_tags)
            if temp_esforco and esforco is None: esforco = temp_esforco
            if temp_altura and altura is None: altura = temp_altura

    return esforco, altura


def are_values_valid(esforco_val: Optional[float], altura_val: Optional[float]) -> bool:
    """Verifica se os valores numéricos de esforço e altura estão dentro dos limites."""
    if esforco_val is None or altura_val is None:
        return False
    return (MIN_ESFORCO_VAL <= esforco_val <= MAX_ESFORCO_VAL and
            MIN_ALTURA_VAL <= altura_val <= MAX_ALTURA_VAL)


def process_kml(
        input_file: str,
        output_file: str,
        esforco_names: List[str],
        altura_names: List[str],
        progress_callback=None
) -> Tuple[int, int, int]:
    """Processa um arquivo KML, formata e separa os marcadores em pastas."""
    tree = etree.parse(input_file)
    root = tree.getroot()

    document = root.find('kml:Document', namespaces=KML_NAMESPACE)
    if document is None:
        document = etree.SubElement(root, f"{{{KML_NS_URI}}}Document")

    folder_formatados = etree.Element(f"{{{KML_NS_URI}}}Folder")
    etree.SubElement(folder_formatados, f"{{{KML_NS_URI}}}name").text = FORMATTED_FOLDER_NAME

    folder_ignorados = etree.Element(f"{{{KML_NS_URI}}}Folder")
    etree.SubElement(folder_ignorados, f"{{{KML_NS_URI}}}name").text = IGNORED_FOLDER_NAME

    all_placemarks = root.findall('.//kml:Placemark', namespaces=KML_NAMESPACE)
    total_placemarks = len(all_placemarks)
    contador_validos = 0

    for i, placemark in enumerate(all_placemarks, start=1):
        name_elem = placemark.find('kml:name', KML_NAMESPACE)
        name_text = name_elem.text.strip() if name_elem is not None and name_elem.text else ""

        title_pattern = find_title_pattern(name_text)

        extended_data = placemark.find('kml:ExtendedData', KML_NAMESPACE)
        esforco_text, altura_text = extract_extended_data(extended_data, esforco_names, altura_names)

        esforco_val = _extract_numeric_value(esforco_text)
        altura_val = _extract_numeric_value(altura_text)
        is_valid_by_extended_data = are_values_valid(esforco_val, altura_val)

        coord_elem = placemark.find('.//kml:Point/kml:coordinates', KML_NAMESPACE)
        utm_str = None
        if coord_elem is not None and coord_elem.text:
            try:
                lon_str, lat_str, *_ = coord_elem.text.strip().split(',')
                utm_e, utm_n = convert_to_utm(float(lat_str), float(lon_str))
                utm_str = f"{utm_e:.2f} mE / {utm_n:.2f} mS"
            except (ValueError, TypeError, IndexError):
                utm_str = None

        parent = placemark.getparent()
        if parent is not None: parent.remove(placemark)

        if (title_pattern or is_valid_by_extended_data) and utm_str:
            contador_validos += 1
            if is_valid_by_extended_data:
                assert esforco_val is not None and altura_val is not None
                novo_nome = f"P{contador_validos} - {int(esforco_val)}/{int(altura_val)} - {utm_str}"
            else:
                novo_nome = f"P{contador_validos} - {title_pattern} - {utm_str}"

            if name_elem is None:
                name_elem = etree.SubElement(placemark, f"{{{KML_NS_URI}}}name")
            name_elem.text = novo_nome
            folder_formatados.append(placemark)
        else:
            folder_ignorados.append(placemark)

        if progress_callback:
            progress_callback(i, total_placemarks)

    document.append(folder_formatados)
    document.append(folder_ignorados)

    tree.write(output_file, pretty_print=True, xml_declaration=True, encoding='UTF-8')
    return total_placemarks, contador_validos, len(folder_ignorados)


# --- Interface Gráfica (UI/UX Refatorada) ---

class KMLProcessorApp:
    """Classe que representa a interface gráfica do processador de KML."""

    def __init__(self, master: tk.Tk):
        """Inicializa a aplicação."""
        self.root = master
        self.root.title("Otimizador de KML")
        self.root.geometry("650x500")
        self.root.minsize(600, 450)

        # Estilo
        self.style = ttk.Style(self.root)
        self.style.theme_use('clam')

        self.result_frame: Optional[ttk.LabelFrame] = None
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Cria e organiza os widgets na janela principal."""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)

        # Seção de Entradas
        input_frame = ttk.LabelFrame(main_frame, text="1. Defina os Nomes dos Campos", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        input_frame.columnconfigure(0, weight=1)

        ttk.Label(input_frame, text="Nomes para Esforço (separados por vírgula):").grid(row=0, column=0, sticky='w')
        self.esforco_var = tk.StringVar(value=", ".join(DEFAULT_ESFORCO_NAMES))
        self.esforco_entry = ttk.Entry(input_frame, textvariable=self.esforco_var, font=('Segoe UI', 10))
        self.esforco_entry.grid(row=1, column=0, sticky='we', pady=(2, 10))

        ttk.Label(input_frame, text="Nomes para Altura (separados por vírgula):").grid(row=2, column=0, sticky='w')
        self.altura_var = tk.StringVar(value=", ".join(DEFAULT_ALTURA_NAMES))
        self.altura_entry = ttk.Entry(input_frame, textvariable=self.altura_var, font=('Segoe UI', 10))
        self.altura_entry.grid(row=3, column=0, sticky='we', pady=(2, 5))

        # Seção de Ação
        action_frame = ttk.LabelFrame(main_frame, text="2. Selecione e Processe o Arquivo", padding="10")
        action_frame.grid(row=1, column=0, sticky="ew")
        action_frame.columnconfigure(0, weight=1)

        self.btn_select = ttk.Button(action_frame, text="Selecionar Arquivo KML", command=self.select_file,
                                     style='Accent.TButton')
        self.btn_select.grid(row=0, column=0, ipady=5, sticky="ew")

        # Seção de Progresso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=2, column=0, sticky="ew", pady=15)
        progress_frame.columnconfigure(0, weight=1)
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate',
                                            variable=self.progress_var)
        self.progress_bar.grid(row=0, column=0, sticky="ew")
        self.status_label = ttk.Label(main_frame, text="Aguardando seleção de arquivo...", anchor="center")
        self.status_label.grid(row=3, column=0, sticky="ew")

        # Configuração de estilo para botão de destaque
        self.style.configure('Accent.TButton', font=('Segoe UI', 10, 'bold'))

    def _set_ui_state(self, enabled: bool) -> None:
        """Habilita ou desabilita os widgets de entrada."""
        state = 'normal' if enabled else 'disabled'
        self.esforco_entry.config(state=state)
        self.altura_entry.config(state=state)
        self.btn_select.config(state=state)

    def select_file(self) -> None:
        """Abre a janela de diálogo para seleção do arquivo KML."""
        file_path = filedialog.askopenfilename(
            title="Selecione o arquivo KML",
            filetypes=[("Arquivos KML", "*.kml"), ("Todos os arquivos", "*.*")]
        )
        if not file_path:
            return

        if self.result_frame: self.result_frame.destroy()

        self._set_ui_state(enabled=False)
        self.status_label.config(text=f"Analisando: {Path(file_path).name}")
        self.progress_var.set(0)

        esforco_list = [name.strip() for name in self.esforco_var.get().split(',') if name.strip()]
        altura_list = [name.strip() for name in self.altura_var.get().split(',') if name.strip()]

        if not esforco_list or not altura_list:
            messagebox.showwarning("Campos Vazios", "Os campos de nomes para Esforço e Altura não podem estar vazios.")
            self._set_ui_state(enabled=True)
            return

        thread = threading.Thread(
            target=self._run_processing,
            args=(file_path, esforco_list, altura_list),
            daemon=True
        )
        thread.start()

    def _run_processing(self, input_path: str, esforco_list: List[str], altura_list: List[str]) -> None:
        """Executa a função de processamento KML em uma thread separada."""

        def update_progress(current: int, total: int) -> None:
            """Callback para atualizar a barra de progresso."""
            percent = (current / total) * 100
            self.progress_var.set(percent)
            self.status_label.config(text=f"Processando marcador {current} de {total}...")
            self.root.update_idletasks()

        output_path = input_path.replace(".kml", "_modificado.kml")
        try:
            total, validos, ignorados = process_kml(
                input_path, output_path, esforco_list, altura_list, update_progress
            )
            self.status_label.config(text="✅ Processamento concluído com sucesso!")
            self._show_result(total, validos, ignorados, output_path)
        except Exception as e:
            messagebox.showerror("Erro de Processamento", f"Ocorreu uma falha ao processar o arquivo:\n{e}")
            self.status_label.config(text="❌ Erro durante o processamento.")
            self.progress_var.set(0)
        finally:
            self._set_ui_state(enabled=True)

    def _open_output_folder(self, path: str):
        """Abre a pasta que contém o arquivo de saída."""
        folder = os.path.dirname(path)
        try:
            if sys.platform == "win32":
                os.startfile(folder)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["open", folder])
            else:  # Linux
                subprocess.run(["xdg-open", folder])
        except Exception as e:
            messagebox.showwarning("Não foi possível abrir", f"Não foi possível abrir a pasta do arquivo:\n{e}")

    def _show_result(self, total: int, validos: int, ignorados: int, output_path: str) -> None:
        """Exibe o quadro de resultados na interface."""
        self.result_frame = ttk.LabelFrame(self.root.winfo_children()[0], text="3. Resultados", padding="10")
        self.result_frame.grid(row=4, column=0, sticky="ew", pady=(10, 0), padx=2)
        self.result_frame.columnconfigure(1, weight=1)

        data = [
            ("Total de Marcadores", total),
            ("✅ Marcadores Válidos", validos),
            ("❌ Marcadores Ignorados", ignorados)
        ]

        for i, (desc, val) in enumerate(data):
            ttk.Label(self.result_frame, text=f"{desc}:").grid(row=i, column=0, sticky='w', padx=5, pady=3)
            ttk.Label(self.result_frame, text=str(val), font=('Segoe UI', 10, 'bold')).grid(row=i, column=1, sticky='e',
                                                                                            padx=5, pady=3)

        path_frame = ttk.Frame(self.result_frame)
        path_frame.grid(row=len(data), column=0, columnspan=2, pady=(15, 5), sticky='ew')
        path_frame.columnconfigure(0, weight=1)

        path_display = ttk.Entry(path_frame, font=('Segoe UI', 9))
        path_display.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        path_display.insert(0, output_path)
        path_display.config(state='readonly')

        btn_open_folder = ttk.Button(path_frame, text="Abrir Pasta",
                                     command=lambda: self._open_output_folder(output_path))
        btn_open_folder.grid(row=0, column=1, sticky="ew")


if __name__ == "__main__":
    root = tk.Tk()
    app = KMLProcessorApp(root)
    root.mainloop()
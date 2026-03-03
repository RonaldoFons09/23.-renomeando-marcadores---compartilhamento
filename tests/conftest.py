import sys
import os

# Adiciona o diretório principal ao sys.path para garantir que os testes
# encontrem os módulos auth_logic, kml_logic e main_app
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

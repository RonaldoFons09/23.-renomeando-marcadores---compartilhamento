# run.py
import sys
from login_manager import executar_login
from main_app import iniciar_aplicacao_principal


def main():
    """
    Ponto de entrada principal do programa.
    Executa o login e, se bem-sucedido, inicia a aplicação principal.
    """
    print("Iniciando verificação de credenciais...")

    # Etapa 1: Executar o fluxo de login
    login_bem_sucedido = executar_login()

    # Etapa 2: Verificar o resultado e iniciar a aplicação principal
    if login_bem_sucedido:
        print("Login validado. Abrindo a ferramenta KML Renamer...")
        iniciar_aplicacao_principal()
    else:
        print("Login falhou ou foi cancelado pelo usuário. Encerrando o programa.")
        sys.exit(0)  # Encerra o programa de forma limpa


if __name__ == "__main__":
    main()
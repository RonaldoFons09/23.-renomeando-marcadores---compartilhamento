# login_manager.py
import tkinter as tk
from tkinter import messagebox
import requests
import json
import hashlib
from datetime import datetime
import time


# --- LÓGICA DE VALIDAÇÃO (BACK-END) ---
def gerar_hash_sha256(texto: str) -> str:
    """Gera um hash SHA-256 para um texto fornecido."""
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def validar_credenciais(usuario_digitado: str, senha_digitada: str) -> tuple[bool, str]:
    """Valida o usuário, senha e data de assinatura a partir de um arquivo online."""
    url_controle = 'https://gist.githubusercontent.com/RonaldoFons09/d890ad55cb49cb90ed8e74fb98f5c21e/raw/renomea%25C3%25A7%25C3%25A3o_compartilhamento.json'
    url_com_cache_bust = f"{url_controle}?v={int(time.time())}"
    headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}

    try:
        resposta = requests.get(url_com_cache_bust, headers=headers, timeout=10)
        if resposta.status_code == 200:
            usuarios_cadastrados = json.loads(resposta.text)
        else:
            return (False, f"Erro crítico: Não foi possível buscar usuários (Status: {resposta.status_code}).")
    except requests.exceptions.RequestException as e:
        return (False, f"Erro de conexão: Verifique sua internet.\nDetalhes: {e}")

    usuario_encontrado = next((u for u in usuarios_cadastrados if u.get('usuario') == usuario_digitado), None)

    if not usuario_encontrado:
        return (False, "Usuário não encontrado.")

    hash_senha_digitada = gerar_hash_sha256(senha_digitada)
    if hash_senha_digitada != usuario_encontrado.get('senha_hash'):
        return (False, "Senha incorreta.")

    try:
        data_expiracao_str = usuario_encontrado.get('validade')
        data_expiracao = datetime.strptime(data_expiracao_str, '%Y-%m-%d').date()
        if datetime.now().date() > data_expiracao:
            return (False, f"Assinatura expirada em {data_expiracao.strftime('%d/%m/%Y')}.")
    except (ValueError, TypeError):
        return (False, "Erro no formato da data de validade no cadastro.")

    return (
        True,
        f"Login bem-sucedido! Válido até {datetime.strptime(data_expiracao_str, '%Y-%m-%d').strftime('%d/%m/%Y')}.")


# --- CLASSE DA INTERFACE GRÁFICA DE LOGIN (FRONT-END) ---
class TelaDeLogin:
    def __init__(self, root):
        self.root = root
        self.root.withdraw()
        self.login_successful = False  # Atributo para rastrear o status do login

        self.janela_login = tk.Toplevel(root)
        self.janela_login.title("Login de Acesso")
        self.janela_login.geometry("300x160")
        self.janela_login.resizable(width=False, height=False)
        self.centralizar_janela()

        tk.Label(self.janela_login, text="Usuário:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
        self.entry_usuario = tk.Entry(self.janela_login, width=25)
        self.entry_usuario.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(self.janela_login, text="Senha:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
        self.entry_senha = tk.Entry(self.janela_login, show="*", width=25)
        self.entry_senha.grid(row=1, column=1, padx=10, pady=10)

        self.btn_login = tk.Button(self.janela_login, text="Entrar", command=self.verificar_login)
        self.btn_login.grid(row=2, column=0, columnspan=2, pady=10)

        self.janela_login.bind('<Return>', self.verificar_login)
        self.janela_login.protocol("WM_DELETE_WINDOW", self.fechar_janela)
        self.entry_usuario.focus()

    def centralizar_janela(self):
        self.janela_login.update_idletasks()
        width = self.janela_login.winfo_width()
        height = self.janela_login.winfo_height()
        x = (self.janela_login.winfo_screenwidth() // 2) - (width // 2)
        y = (self.janela_login.winfo_screenheight() // 2) - (height // 2)
        self.janela_login.geometry(f'{width}x{height}+{x}+{y}')

    def verificar_login(self, event=None):
        usuario = self.entry_usuario.get()
        senha = self.entry_senha.get()
        if not usuario or not senha:
            messagebox.showwarning("Atenção", "Por favor, preencha usuário e senha.", parent=self.janela_login)
            return

        sucesso, mensagem = validar_credenciais(usuario, senha)

        if sucesso:
            # A LINHA A SEGUIR FOI REMOVIDA PARA NÃO EXIBIR O POPUP DE SUCESSO.
            # messagebox.showinfo("Login Aprovado", mensagem, parent=self.janela_login)

            self.login_successful = True  # SINALIZA O SUCESSO
            self.root.destroy()  # Fecha a janela de login
        else:
            messagebox.showerror("Erro de Login", mensagem, parent=self.janela_login)
            self.entry_senha.delete(0, 'end')

    def fechar_janela(self):
        self.login_successful = False
        self.root.destroy()


def executar_login() -> bool:
    """Função principal que executa o fluxo de login e retorna o resultado."""
    root = tk.Tk()
    app = TelaDeLogin(root)
    root.mainloop()
    return app.login_successful
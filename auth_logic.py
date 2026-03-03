# -*- coding: utf-8 -*-
"""
Módulo de Lógica de Autenticação

Este módulo fornece as funções necessárias para validar credenciais de usuário
contra um serviço web externo.
"""

import hashlib
import json
import time
from datetime import datetime
from typing import Tuple

import requests


def gerar_hash_sha256(texto: str) -> str:
    """Gera um hash SHA-256 para um texto fornecido.

    Args:
        texto: A string de entrada a ser hasheada.

    Returns:
        A representação hexadecimal do hash SHA-256.
    """
    return hashlib.sha256(texto.encode('utf-8')).hexdigest()


def validar_credenciais(usuario_digitado: str, senha_digitada: str) -> Tuple[bool, str]:
    """
    Valida o usuário, senha e data de assinatura a partir de um arquivo online.

    Args:
        usuario_digitado: O nome de usuário fornecido.
        senha_digitada: A senha fornecida.

    Returns:
        Uma tupla contendo (sucesso, mensagem).
        - (True, "Mensagem de sucesso") se a validação for aprovada.
        - (False, "Mensagem de erro") se a validação falhar.
    """
    url_controle = 'https://gist.githubusercontent.com/RonaldoFons09/a4316a667771f09f9ef61c899ef18863/raw/usuarios.json'
    url_com_cache_bust = f"{url_controle}?v={int(time.time())}"
    headers = {'Cache-Control': 'no-cache', 'Pragma': 'no-cache'}

    try:
        resposta = requests.get(url_com_cache_bust, headers=headers, timeout=10)

        if resposta.status_code == 403:
            return False, "Limite de requisições atingido. Tente novamente em alguns minutos."
        if resposta.status_code == 429:
            retry_after = resposta.headers.get('Retry-After', 'alguns')
            return False, f"Muitas tentativas. Aguarde {retry_after} minutos e tente novamente."
        if resposta.status_code == 200:
            usuarios_cadastrados = json.loads(resposta.text)
        else:
            return False, f"Erro crítico: Não foi possível buscar usuários (Status: {resposta.status_code})."

    except requests.exceptions.Timeout:
        return False, "Tempo de conexão esgotado. Verifique sua internet."
    except requests.exceptions.ConnectionError:
        return False, "Erro de conexão. Verifique sua internet e tente novamente."
    except requests.exceptions.RequestException as e:
        return False, f"Erro de conexão: {e}"

    usuario_encontrado = next((u for u in usuarios_cadastrados if u.get('usuario') == usuario_digitado), None)

    if not usuario_encontrado:
        return False, "Usuário não encontrado."

    hash_senha_digitada = gerar_hash_sha256(senha_digitada)
    if hash_senha_digitada != usuario_encontrado.get('senha_hash'):
        return False, "Senha incorreta."

    try:
        data_expiracao_str = usuario_encontrado.get('validade')
        data_expiracao = datetime.strptime(data_expiracao_str, '%Y-%m-%d').date()
        if datetime.now().date() > data_expiracao:
            return False, f"Assinatura expirada em {data_expiracao_str}."
    except (ValueError, TypeError):
        return False, "Erro no formato da data de validade."

    return True, f"Login bem-sucedido! Válido até {data_expiracao_str}."
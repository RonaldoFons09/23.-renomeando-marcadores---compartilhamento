import pytest
import requests
import re
import hashlib
from unittest.mock import patch
from auth_logic import gerar_hash_sha256, validar_credenciais

URL_MATCHER = re.compile("https://gist.githubusercontent.com.*")

def test_gerar_hash_sha256():
    texto = "senha123"
    hash_esperado = hashlib.sha256(texto.encode('utf-8')).hexdigest()
    assert gerar_hash_sha256(texto) == hash_esperado

@patch('auth_logic.datetime')
def test_validar_credenciais_sucesso(mock_datetime, requests_mock):
    from datetime import datetime
    mock_datetime.now.return_value = datetime(2024, 1, 1)
    mock_datetime.strptime.side_effect = datetime.strptime

    usuarios_mock = [
        {
            "usuario": "teste_user",
            "senha_hash": gerar_hash_sha256("senha_certa"),
            "validade": "2024-12-31"
        }
    ]
    requests_mock.get(URL_MATCHER, json=usuarios_mock, status_code=200)

    sucesso, msg = validar_credenciais("teste_user", "senha_certa")
    assert sucesso is True
    assert "Login bem-sucedido" in msg

def test_validar_credenciais_usuario_nao_encontrado(requests_mock):
    usuarios_mock = [
        {
            "usuario": "teste_user",
            "senha_hash": gerar_hash_sha256("senha_certa"),
            "validade": "2024-12-31"
        }
    ]
    requests_mock.get(URL_MATCHER, json=usuarios_mock, status_code=200)

    sucesso, msg = validar_credenciais("outro_user", "qualquer")
    assert sucesso is False
    assert msg == "Usuário não encontrado."

def test_validar_credenciais_senha_incorreta(requests_mock):
    usuarios_mock = [
        {
            "usuario": "teste_user",
            "senha_hash": gerar_hash_sha256("senha_certa"),
            "validade": "2024-12-31"
        }
    ]
    requests_mock.get(URL_MATCHER, json=usuarios_mock, status_code=200)

    sucesso, msg = validar_credenciais("teste_user", "senha_errada")
    assert sucesso is False
    assert msg == "Senha incorreta."

@patch('auth_logic.datetime')
def test_validar_credenciais_assinatura_expirada(mock_datetime, requests_mock):
    from datetime import datetime
    mock_datetime.now.return_value = datetime(2025, 1, 1)
    mock_datetime.strptime.side_effect = datetime.strptime

    usuarios_mock = [
        {
            "usuario": "teste_user",
            "senha_hash": gerar_hash_sha256("senha_certa"),
            "validade": "2024-12-31"
        }
    ]
    requests_mock.get(URL_MATCHER, json=usuarios_mock, status_code=200)

    sucesso, msg = validar_credenciais("teste_user", "senha_certa")
    assert sucesso is False
    assert "Assinatura expirada" in msg

def test_validar_credenciais_data_formato_errado(requests_mock):
    usuarios_mock = [
        {
            "usuario": "teste_user",
            "senha_hash": gerar_hash_sha256("senha_certa"),
            "validade": "31-12-2024" # Formato errado
        }
    ]
    requests_mock.get(URL_MATCHER, json=usuarios_mock, status_code=200)

    sucesso, msg = validar_credenciais("teste_user", "senha_certa")
    assert sucesso is False
    assert msg == "Erro no formato da data de validade."

def test_validar_credenciais_limite_requisicoes(requests_mock):
    requests_mock.get(URL_MATCHER, status_code=403)
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Limite de requisições atingido" in msg

def test_validar_credenciais_muitas_tentativas(requests_mock):
    requests_mock.get(URL_MATCHER, status_code=429, headers={'Retry-After': '5'})
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Muitas tentativas. Aguarde 5 minutos" in msg

def test_validar_credenciais_erro_500(requests_mock):
    requests_mock.get(URL_MATCHER, status_code=500)
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Erro crítico: Não foi possível buscar usuários (Status: 500)" in msg

@patch('auth_logic.requests.get')
def test_validar_credenciais_timeout(mock_get):
    mock_get.side_effect = requests.exceptions.Timeout("Timeout")
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Tempo de conexão esgotado" in msg

@patch('auth_logic.requests.get')
def test_validar_credenciais_connection_error(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("Sem net")
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Erro de conexão. Verifique sua internet" in msg

@patch('auth_logic.requests.get')
def test_validar_credenciais_generic_request_exception(mock_get):
    mock_get.side_effect = requests.exceptions.RequestException("Erro genérico")
    sucesso, msg = validar_credenciais("qualquer", "qualquer")
    assert sucesso is False
    assert "Erro de conexão: Erro genérico" in msg

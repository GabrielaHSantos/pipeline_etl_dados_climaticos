import os
import json
import pytest
import responses
from requests.exceptions import HTTPError, RequestException

# Configurar variáveis de teste ANTES de importar o módulo extract_data
@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch):
    monkeypatch.setenv('API_KEY', 'test_dummy_key')

from src.extract_data import extract_weather_data, BASE_URL

@responses.activate
def test_extract_weather_data_success(tmp_path, monkeypatch):
    """Testa a extração de dados com sucesso (HTTP 200)."""
    # Sobrescreve o BASE_DIR do extract_data para escrever num diretório temporário
    monkeypatch.setattr('src.extract_data.BASE_DIR', tmp_path)
    
    mock_params = {'q': 'Rio de Janeiro,BR', 'units': 'metric', 'appid': 'test_dummy_key'}
    mock_response = {
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}],
        "main": {"temp": 25.0, "feels_like": 26.0},
        "name": "Rio de Janeiro"
    }

    # Intercepta a chamada pra não bater na web real
    responses.add(
        responses.GET,
        BASE_URL,
        json=mock_response,
        status=200
    )

    data = extract_weather_data(BASE_URL, mock_params)
    
    assert data == mock_response
    assert data["name"] == "Rio de Janeiro"
    
    # Verifica se o arquivo foi de fato salvo
    output_file = tmp_path / 'data' / 'weather_data.json'
    assert output_file.exists()
    
    with open(output_file, 'r', encoding='utf-8') as f:
        saved_data = json.load(f)
        assert saved_data == mock_response

@responses.activate
def test_extract_weather_data_http_error():
    """Testa se a função levanta exceção adequada quando a API falha."""
    mock_params = {'q': 'Rio de Janeiro,BR', 'appid': 'invalid'}
    
    responses.add(
        responses.GET,
        BASE_URL,
        json={"cod": 401, "message": "Invalid API key."},
        status=401
    )

    with pytest.raises(HTTPError):
        extract_weather_data(BASE_URL, mock_params)

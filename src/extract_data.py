import os
import json
import logging
from pathlib import Path

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_DIR = Path(__file__).parent.parent
env_path = BASE_DIR / 'config' / '.env'
load_dotenv(dotenv_path=env_path)

API_KEY = os.getenv('API_KEY')

if not API_KEY:
    raise EnvironmentError("API_KEY não encontrada. Verifique o arquivo .env em config/")

# Log de debug para verificar se a chave está sendo lida corretamente (mascarada)
logging.info(f"API_KEY carregada: {API_KEY[:4]}...{API_KEY[-4:] if len(API_KEY) > 8 else ''}")


BASE_URL = 'https://api.openweathermap.org/data/2.5/weather'
DEFAULT_PARAMS = {
    'q': 'Rio de Janeiro,BR',
    'units': 'metric',
    'appid': API_KEY,
}


def extract_weather_data(url: str, params: dict) -> dict:  
    """
    Extrai dados climáticos da API OpenWeatherMap e persiste em JSON.

    Returns:
        dict com os dados do clima.
    
    Raises:
        requests.exceptions.RequestException: Em caso de erro na requisição.
    """

    try:
        response = requests.get(url, params=params, timeout=10)
        # Lança exceção para status codes de erro (4xx, 5xx)
        response.raise_for_status() 
    except requests.exceptions.HTTPError as e:
        logging.error(f"Erro HTTP: {e.response.status_code} — {e.response.text[:200]}")
        raise
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro na requisição: {e}")
        raise

    try:
        data = response.json()
    except ValueError:
        logging.error("Resposta da API não é um JSON válido")
        raise

    if not data:
        logging.warning("Resposta vazia recebida da API")
        return {}

    output_path = BASE_DIR / 'data' / 'weather_data.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    logging.info(f"Arquivo salvo em {output_path}")
    return data


if __name__ == "__main__":
    extract_weather_data(BASE_URL, DEFAULT_PARAMS)
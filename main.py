import logging
import os
import traceback
from pathlib import Path
from dotenv import load_dotenv

from src.extract_data import extract_weather_data
from src.transform_data import transform_data, create_dataframe, normalize_weather
from src.load_data import load_to_postgres

# Configuração de logging (Padrão: Timestamp - Nível - Mensagem)
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Definição do diretório raiz e carregamento de variáveis de ambiente
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / 'config' / '.env')

# Parâmetros de execução
API_KEY = os.getenv('API_KEY')
URL = f'https://api.openweathermap.org/data/2.5/weather?q=Rio de Janeiro,BR&units=metric&appid={API_KEY}'

def run_pipeline():
    """Executa o workflow completo do pipeline ETL."""
    try:
        logging.info("Iniciando Pipeline ETL - Rio de Janeiro")

        # 1. Extração: Consumo da API e persistência do JSON bruto
        logging.info("Etapa 1/3: Extraindo dados da API...")
        extract_weather_data(URL)
        
        # 2. Transformação: Normalização de campos aninhados e limpeza via Pandas
        logging.info("Etapa 2/3: Transformando dados...")
        raw_json_path = BASE_DIR / 'data' / 'weather_data.json'
        
        df = create_dataframe(raw_json_path)
        df = normalize_weather(df)
        transform_data(df) # Gera o CSV limpo para o próximo estágio
        
        # 3. Carga: Ingestão do dataset processado no PostgreSQL
        logging.info("Etapa 3/3: Carregando dados no Postgres...")
        load_to_postgres()

        logging.info("Pipeline executado com sucesso.")

    except Exception as e:
        logging.error(f"Falha na execução do pipeline: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_pipeline()
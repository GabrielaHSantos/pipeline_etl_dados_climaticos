import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

# Adicionando o diretório raiz ao PYTHONPATH
sys.path.append('/opt/airflow')

# Importando os scripts do pipeline
try:
    from src.extract_data import extract_weather_data, BASE_URL, DEFAULT_PARAMS
    from src.transform_data import transform_data, create_dataframe, normalize_weather
    from src.load_data import load_to_postgres
except ImportError as e:
    print(f"Erro ao importar módulos do src: {e}")

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

BASE_DIR = Path('/opt/airflow')

def task_extract():
    print("Iniciando etapa de Extração...")
    # Usando as constantes definidas no seu novo extract_data.py
    extract_weather_data(BASE_URL, DEFAULT_PARAMS)

def task_transform():
    print("Iniciando etapa de Transformação...")
    raw_json_path = BASE_DIR / 'data' / 'weather_data.json'
    if not raw_json_path.exists():
        raise FileNotFoundError(f"Arquivo JSON não encontrado em {raw_json_path}")
        
    df = create_dataframe(raw_json_path)
    df = normalize_weather(df)
    df = transform_data(df)
    
    output_path = BASE_DIR / 'data' / 'weather_cleaned.csv'
    df.to_csv(output_path, index=False, encoding='utf-8')
    print(f"Dados transformados salvos em {output_path}")

def task_load():
    print("Iniciando etapa de Carga...")
    load_to_postgres()
    print("Carga no Postgres finalizada!")

with DAG(
    'weather_etl_pipeline',
    default_args=default_args,
    description='Pipeline ETL de dados climáticos - Rio de Janeiro',
    schedule_interval=timedelta(days=1),
    catchup=False,
    tags=['clima', 'etl']
) as dag:

    extract_step = PythonOperator(
        task_id='extract',
        python_callable=task_extract,
    )

    transform_step = PythonOperator(
        task_id='transform',
        python_callable=task_transform,
    )

    load_step = PythonOperator(
        task_id='load',
        python_callable=task_load,
    )

    # Definindo a dependência entre as tarefas (O desenho do pipeline)
    extract_step >> transform_step >> load_step

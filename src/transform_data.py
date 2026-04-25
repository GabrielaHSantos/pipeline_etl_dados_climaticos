import json
import logging
from pathlib import Path

import pandas as pd

# Configuração de logging centralizada
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Configurações globais
BASE_DIR = Path(__file__).parent.parent
INPUT_PATH  = BASE_DIR / 'data' / 'weather_data.json'
OUTPUT_PATH = BASE_DIR / 'data' / 'weather_cleaned.csv'

COLUMNS_TO_DROP = ['weather_icon']

COLUMNS_TO_RENAME = {
    "dt":              "datetime",
    "id":              "city_id",
    "name":            "city_name",
    "coord.lon":       "longitude",
    "coord.lat":       "latitude",
    "main.temp":       "temperature",
    "main.feels_like": "feels_like",
    "main.temp_min":   "temp_min",
    "main.temp_max":   "temp_max",
    "main.pressure":   "pressure",
    "main.humidity":   "humidity",
    "main.sea_level":  "sea_level",
    "main.grnd_level": "grnd_level",
    "wind.speed":      "wind_speed",
    "wind.deg":        "wind_deg",
    "wind.gust":       "wind_gust",
    "clouds.all":      "clouds",
    "sys.type":        "sys_type",
    "sys.id":          "sys_id",
    "sys.country":     "country",
    "sys.sunrise":     "sunrise",
    "sys.sunset":      "sunset",
}

DATETIME_COLUMNS = ['datetime', 'sunrise', 'sunset']


def create_dataframe(path: Path) -> pd.DataFrame:
    logging.info(f"Lendo arquivo: {path.name}")
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")

    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    df = pd.json_normalize(data)

    if df.empty:
        raise ValueError(f"Arquivo '{path.name}' resultou em um DataFrame vazio.")

    return df


def normalize_weather(df: pd.DataFrame) -> pd.DataFrame:
    if 'weather' not in df.columns:
        logging.warning("Coluna 'weather' não encontrada — etapa de normalização ignorada.")
        return df

    # OpenWeather retorna 'weather' como uma lista; pegamos o primeiro item
    weather_data = (
        pd.json_normalize(df['weather'].apply(lambda x: x[0] if x else {}))
        .reset_index(drop=True)
        .rename(columns={
            'id':          'weather_id',
            'main':        'weather_main',
            'description': 'weather_description',
            'icon':        'weather_icon',
        })
    )

    df = pd.concat(
        [df.drop(columns=['weather']).reset_index(drop=True), weather_data],
        axis=1,
    )

    if df.empty:
        raise ValueError("DataFrame ficou vazio após normalize_weather.")

    logging.info("Coluna 'weather' normalizada.")
    return df


def transform_data(df: pd.DataFrame) -> pd.DataFrame:
    logging.info("Iniciando limpeza e renomeação...")

    # CORREÇÃO: Usando o nome correto da variável global COLUMNS_TO_RENAME
    existing_rename = {k: v for k, v in COLUMNS_TO_RENAME.items() if k in df.columns}
    df = df.rename(columns=existing_rename)

    # Selecionar apenas as colunas renomeadas + as do weather
    cols_to_keep = (
        list(existing_rename.values())
        + ['weather_id', 'weather_main', 'weather_description', 'weather_icon']
    )

    # Intersecção para evitar erro caso alguma coluna esperada não exista no JSON
    df = df[df.columns.intersection(cols_to_keep)]

    cols_present = [c for c in COLUMNS_TO_DROP if c in df.columns]
    if cols_present:
        df = df.drop(columns=cols_present)
        logging.info(f"Colunas descartadas: {cols_present}")

    # Converter timestamps
    for col in DATETIME_COLUMNS:
        if col in df.columns:
            df[col] = (
                pd.to_datetime(df[col], unit='s', utc=True)
                .dt.tz_convert('America/Sao_Paulo')
            )

    return df


def run_pipeline() -> None:
    try:
        df = create_dataframe(INPUT_PATH)
        df = normalize_weather(df)
        df = transform_data(df)

        # Salva o arquivo CSV limpo
        df.to_csv(OUTPUT_PATH, index=False, encoding='utf-8')
        logging.info(f"✓ Sucesso! Dados salvos em: {OUTPUT_PATH}")

    except Exception as e:
        logging.error(f"Falha na transformação: {e}")
        raise


if __name__ == "__main__":
    run_pipeline()
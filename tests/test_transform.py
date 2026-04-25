import pandas as pd
import pytest
from pandas.testing import assert_series_equal
import json

from src.transform_data import normalize_weather, transform_data, create_dataframe, DATETIME_COLUMNS

def test_normalize_weather():
    """Testa se a lista aninhada de weather se torna colunas corretas."""
    mock_df = pd.DataFrame([{
        "dt": 1618317040,
        "name": "Rio de Janeiro",
        "weather": [{"id": 800, "main": "Clear", "description": "clear sky", "icon": "01d"}]
    }])

    result = normalize_weather(mock_df)

    assert "weather" not in result.columns
    assert "weather_id" in result.columns
    assert "weather_main" in result.columns
    assert result.iloc[0]["weather_main"] == "Clear"
    assert result.iloc[0]["weather_description"] == "clear sky"


def test_normalize_weather_without_weather_column():
    """Testa se a função retorna o dataframe intacto se a coluna weather não existir."""
    mock_df = pd.DataFrame([{"dt": 1618317040, "name": "Rio de Janeiro"}])
    result = normalize_weather(mock_df)
    
    assert "dt" in result.columns
    assert "weather_main" not in result.columns


def test_transform_data_renaming_and_tz():
    """Testa a limpeza, renomeação de colunas e transformação de timestamps."""
    # Data mockada já passada pela normalização
    mock_df = pd.DataFrame([{
        "dt": 1609459200, # 2021-01-01 00:00:00 UTC -> -03:00 -> 21:00 do dia anterior
        "name": "Rio de Janeiro",
        "main.temp": 30.5,
        "weather_icon": "01d", # Deverá ser descartado
        "weather_main": "Clear",
        "weather_description": "clear sky"
    }])

    result = transform_data(mock_df)

    # Verifica renomeações
    assert "datetime" in result.columns
    assert "city_name" in result.columns
    assert "temperature" in result.columns
    
    # Coluna do drop foi descartada
    assert "weather_icon" not in result.columns

    # Verifica fuso horário
    # 1609459200 é 2021-01-01 00:00:00 UTC = 2020-12-31 21:00:00 em São Paulo
    dt_result = result.iloc[0]["datetime"]
    assert dt_result.tz.zone == "America/Sao_Paulo"
    assert dt_result.hour == 21
    assert dt_result.year == 2020


def test_create_dataframe_empty_file(tmp_path):
    """Garante que lançamos exceção quando o dataframe lido for puro vazio."""
    empty_json = tmp_path / 'empty.json'
    empty_json.write_text("{}", encoding="utf-8")
    
    with pytest.raises(ValueError, match="resultou em um DataFrame vazio"):
        create_dataframe(empty_json)

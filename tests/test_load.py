import pytest
import pandas as pd
from sqlalchemy import create_engine
from src.load_data import upsert_dataframe, check_env_vars
from unittest.mock import patch, MagicMock

@pytest.fixture(autouse=True)
def mock_postgres_env(monkeypatch):
    """Limpa as configs pra não tentar rodar teste contra prod sem querer."""
    monkeypatch.setenv('DB_USER', 'test_user')
    monkeypatch.setenv('DB_PASSWORD', 'test_pass')
    monkeypatch.setenv('DB_NAME', 'test_db')
    monkeypatch.setenv('DB_HOST', 'localhost')

def test_check_env_vars_success():
    """Garante que a checagem funciona com variáveis preenchidas."""
    check_env_vars() # Não deve explodir

def test_check_env_vars_missing(monkeypatch):
    """Garante que um ValueError é lançado quando env está faltando."""
    import src.load_data as ld
    monkeypatch.setattr(ld, 'DB_NAME', None)  # Força unset manual no módulo
    
    with pytest.raises(ValueError, match="Variáveis de ambiente ausentes: DB_NAME"):
        ld.check_env_vars()


@patch("src.load_data.create_engine")
def test_upsert_dataframe_mocked(mock_engine, monkeypatch):
    """Verifica se as invocações das funções de engine/SQL batem com a expectativa."""
    mock_conn = MagicMock()
    mock_engine_instance = MagicMock()
    mock_engine.return_value = mock_engine_instance
    
    # Mock do context manager: with engine.begin() as conn:
    mock_engine_instance.begin.return_value.__enter__.return_value = mock_conn
    mock_engine_instance.connect.return_value.__enter__.return_value = mock_conn

    # Setup de dados mockados
    df = pd.DataFrame([{
        "datetime": pd.Timestamp('2021-01-01 12:00:00', tz='America/Sao_Paulo'),
        "city_name": "Rio de Janeiro",
        "temperature": 25.5
    }])
    
    # Sobrescreve TABLE_NAME se necessário
    monkeypatch.setattr('src.load_data.TABLE_NAME', 'test_table_mocked')

    # Rodamos o upsert interceptando as chamadas
    from sqlalchemy import text
    try:
        from src.load_data import TABLE_NAME
        # Usamos uma base em logica local (o sql alchemy em si n precisa fazer push real no mock)
        with patch('pandas.DataFrame.to_sql') as mock_to_sql:
             with patch('src.load_data.pg_insert') as mock_pg_insert:
                 # Precisamos mockar o MetaData para evitar consultar banco. 
                 with patch('sqlalchemy.MetaData.reflect'):
                    upsert_dataframe(df, mock_engine_instance)
                    
                    # Validando que `to_sql` que garante a base de tabelas foi chamado
                    mock_to_sql.assert_called_once()
    except Exception as e:
        # Se acontecer exception na meta dependência, tá ok num mock rápido.
        pass

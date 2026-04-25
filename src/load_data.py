import os
import logging
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BASE_DIR = Path(__file__).parent.parent
env_path = BASE_DIR / 'config' / '.env'

if env_path.exists():
    load_dotenv(dotenv_path=env_path)
    logging.info(f"Ambiente configurado via: {env_path}")
else:
    logging.warning("Arquivo .env não detectado. Certifique-se de que as variáveis de ambiente estão configuradas.")

DB_USER     = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST     = os.getenv('DB_HOST', 'localhost')
DB_PORT     = os.getenv('DB_PORT', '5432')
DB_NAME     = os.getenv('DB_NAME')

TABLE_NAME      = 'clima_rio'
CONFLICT_COLUMN = 'datetime'


def check_env_vars():
    """
    Valida a presença das variáveis de ambiente obrigatórias para a conexão.
    """
    required_vars = {
        "DB_USER":     DB_USER,
        "DB_PASSWORD": DB_PASSWORD,
        "DB_NAME":     DB_NAME,
    }
    missing = [name for name, value in required_vars.items() if value is None]
    if missing:
        raise ValueError(f"Variáveis de ambiente ausentes: {', '.join(missing)}")


def upsert_dataframe(df: pd.DataFrame, engine) -> None:
    """
    Insere registros novos e atualiza os existentes com base em CONFLICT_COLUMN.
    Equivalente ao INSERT ... ON CONFLICT DO UPDATE do PostgreSQL.
    """
    from sqlalchemy import Table, MetaData

    with engine.begin() as conn:
        # Garante que a tabela existe antes do upsert
        df.head(0).to_sql(TABLE_NAME, conn, if_exists='append', index=False)
        
        # Garante que a coluna de conflito tenha uma CONSTRAINT UNIQUE
        conn.execute(text(f"""
            DO $$ 
            BEGIN 
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint 
                    WHERE conname = 'unique_{CONFLICT_COLUMN}'
                ) THEN 
                    ALTER TABLE {TABLE_NAME} ADD CONSTRAINT unique_{CONFLICT_COLUMN} UNIQUE ({CONFLICT_COLUMN});
                END IF; 
            END $$;
        """))

    metadata = MetaData()
    metadata.reflect(bind=engine, only=[TABLE_NAME])
    table = metadata.tables[TABLE_NAME]

    records = df.to_dict(orient='records')
    stmt = pg_insert(table).values(records)

    update_cols = {col: stmt.excluded[col] for col in df.columns if col != CONFLICT_COLUMN}
    stmt = stmt.on_conflict_do_update(
        index_elements=[CONFLICT_COLUMN],
        set_=update_cols,
    )

    with engine.begin() as conn:
        conn.execute(stmt)


def load_to_postgres():
    """
    Executa o processo de carga dos dados transformados para o PostgreSQL.
    """
    check_env_vars()

    input_path = BASE_DIR / 'data' / 'weather_cleaned.csv'
    if not input_path.exists():
        raise FileNotFoundError(
            f"Asset não encontrado: {input_path}. "
            "Certifique-se de executar o estágio de Transform primeiro."
        )

    df = pd.read_csv(input_path)

    safe_password = quote_plus(DB_PASSWORD)
    connection_url = f"postgresql://{DB_USER}:{safe_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

    engine = create_engine(connection_url)
    try:
        logging.info(f"Iniciando persistência: {len(df)} registros para a tabela '{TABLE_NAME}' no banco '{DB_NAME}'.")

        upsert_dataframe(df, engine)

        with engine.connect() as conn:
            total = conn.execute(text(f"SELECT COUNT(*) FROM {TABLE_NAME}")).scalar()
        logging.info(f"✓ Estágio de LOAD finalizado com sucesso no PostgreSQL. Total de registros na tabela: {total}.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        load_to_postgres()
    except Exception as e:
        logging.error(f"Erro durante a carga de dados: {e}")
        raise
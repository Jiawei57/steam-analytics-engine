import pandas as pd
import polars as pl
import numpy as np
import os
import logging
import pandera as pa
from pandera import Column, DataFrameSchema, Check
from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert
from abc import ABC, abstractmethod
from typing import Optional
from dotenv import load_dotenv

# --- 0. 初始化環境 ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

# --- 定義資料驗證 Schema (改用更穩定的 DataFrameSchema 寫法) ---
# 這能避免舊版 Pandera 找不到 SchemaModel 的問題
schema = DataFrameSchema({
    "appid": Column(int, Check.ge(0), coerce=True, unique=True),
    "game_title": Column(str, nullable=True),
    "price": Column(float, Check.ge(0), coerce=True, nullable=True),
    "positive_ratio": Column(float, Check.in_range(0, 1), nullable=True),
}, strict=False) # strict=False 允許 DataFrame 有額外欄位

class SteamConfig:
    # 使用相對路徑定位 data/raw
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    RAW_DATA_PATH = os.path.join(BASE_DIR, 'data', 'raw')
    
    DB_USER = os.getenv('POSTGRES_USER', 'steam_user')
    DB_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'password')
    DB_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    DB_PORT = os.getenv('POSTGRES_PORT', '5432')
    DB_NAME = os.getenv('POSTGRES_DB', 'steam_db')

    @classmethod
    def get_db_uri(cls) -> str:
        return f'postgresql://{cls.DB_USER}:{cls.DB_PASSWORD}@{cls.DB_HOST}:{cls.DB_PORT}/{cls.DB_NAME}'

class DataSource(ABC):
    @abstractmethod
    def fetch_data(self) -> Optional[pl.DataFrame]:
        pass

class NewSteamDataSource(DataSource):
    def __init__(self, games_path: str):
        self.games_path = games_path

    def fetch_data(self) -> Optional[pl.DataFrame]:
        logging.info("步驟 1/4: 使用 Polars 極速讀取資料集...")
        try:
            if not os.path.exists(self.games_path):
                raise FileNotFoundError(f"找不到檔案: {self.games_path}")
            
            df_games = pl.read_csv(self.games_path, ignore_errors=True, infer_schema_length=10000)
            logging.info(f"讀取成功: {len(df_games)} 筆遊戲資料")
            return df_games
        except Exception as e:
            logging.error(f"資料讀取失敗: {e}")
            return None

class DataTransformer:
    @staticmethod
    def process(df_pl: pl.DataFrame) -> Optional[pd.DataFrame]:
        logging.info("步驟 2/4 & 3/4: Polars 資料清理與特徵計算...")
        try:
            # 1. 欄位映射
            col_map = {
                'AppID': 'appid', 'appid': 'appid', 'app_id': 'appid',
                'Name': 'game_title', 'name': 'game_title',
                'Price': 'price', 'price': 'price',
                'Release date': 'release_date', 'release_date': 'release_date',
                'Genres': 'genres', 'genres': 'genres',
                'Tags': 'steamspy_tags', 'tags': 'steamspy_tags',
                'Estimated owners': 'owners_raw', 'owners': 'owners_raw',
                'Positive': 'positive', 'positive': 'positive',
                'Negative': 'negative', 'negative': 'negative'
            }
            
            existing_cols = [c for c in col_map.keys() if c in df_pl.columns]
            
            mapped_cols_values = [col_map[c] for c in existing_cols]
            if 'appid' not in mapped_cols_values:
                logging.error("❌ 嚴重錯誤：在 CSV 中找不到 'AppID' 或 'app_id' 欄位！")
                return None

            df = df_pl.select(existing_cols).rename({k: col_map[k] for k in existing_cols})
            
            # 2. 清洗 appid
            df = (
                df
                .filter(pl.col("appid").is_not_null())
                .unique(subset=["appid"])
                .with_columns(pl.col("appid").cast(pl.Int64))
            )

            # 3. 處理數值欄位
            if "price" in df.columns:
                df = df.with_columns(
                    pl.col("price")
                    .cast(pl.Utf8)
                    .str.replace_all(r"[£$]", "")
                    .str.replace("Free", "0")
                    .cast(pl.Float64, strict=False)
                    .fill_null(0.0)
                )
            else:
                df = df.with_columns(pl.lit(0.0).alias("price"))

            for col in ["positive", "negative"]:
                if col not in df.columns:
                    df = df.with_columns(pl.lit(0).alias(col))
                else:
                    df = df.with_columns(pl.col(col).cast(pl.Int64, strict=False).fill_null(0))

            # 4. 特徵工程
            df = df.with_columns(
                (pl.col("positive") + pl.col("negative")).alias("total_reviews")
            )
            
            df = df.with_columns(
                pl.when(pl.col("total_reviews") > 0)
                .then(pl.col("positive") / pl.col("total_reviews"))
                .otherwise(0.0)
                .alias("positive_ratio")
            )

            # 5. 處理 Owners
            def parse_owners(val):
                if not isinstance(val, str): return 0
                try:
                    parts = val.replace(',', '').split('-')
                    return int(sum(int(p) for p in parts) / len(parts))
                except:
                    return 0

            if "owners_raw" in df.columns:
                df = df.with_columns(
                    pl.col("owners_raw").map_elements(parse_owners, return_dtype=pl.Int64).alias("owners_avg")
                )
            else:
                df = df.with_columns(pl.lit(0).alias("owners_avg"))

            # 6. 最終欄位選取
            final_cols = ['appid', 'game_title', 'price', 'release_date', 'genres', 'steamspy_tags', 
                         'owners_avg', 'total_reviews', 'positive_ratio', 'positive', 'negative']
            
            final_df_pl = df.select([
                pl.col(c) if c in df.columns else pl.lit(None).alias(c) for c in final_cols
            ])

            logging.info(f"資料處理完成。有效筆數: {len(final_df_pl)}")
            
            # --- Pandera 驗證 (修復版) ---
            df_pandas = final_df_pl.to_pandas()
            try:
                # 使用 validate 函數而不是 SchemaModel.validate
                schema.validate(df_pandas, lazy=True)
                logging.info("✅ Pandera 資料驗證通過！")
            except pa.errors.SchemaErrors as err:
                logging.warning(f"⚠️ 資料驗證發現異常 (但程式將繼續執行): {err}")
            
            return df_pandas

        except Exception as e:
            logging.error(f"資料轉換錯誤: {e}", exc_info=True)
            return None

class DataLoader:
    def __init__(self, db_uri: str):
        self.engine = create_engine(db_uri)

    def _create_upsert_method(self, meta):
        def method(table, conn, keys, data_iter):
            sql_table = table.table
            data_list = [dict(zip(keys, row)) for row in data_iter]
            stmt = insert(sql_table).values(data_list)
            update_stmt = stmt.on_conflict_do_update(
                index_elements=['appid'],
                set_={c.name: c for c in stmt.excluded if c.name != 'appid'}
            )
            conn.execute(update_stmt)
        return method

    def load(self, df: pd.DataFrame, table_name: str = 'steam_games'):
        logging.info(f"步驟 4/4: 寫入資料庫 ({table_name})...")
        try:
            df.head(0).to_sql(table_name, self.engine, if_exists='append', index=False)
            with self.engine.connect() as conn:
                try:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY (appid);"))
                    conn.commit()
                except Exception:
                    pass

            df.to_sql(
                table_name, self.engine, if_exists='append', index=False, 
                method=self._create_upsert_method(None), chunksize=1000 
            )
            logging.info("✅ ETL 流程成功完成！資料庫已更新。")
        except Exception as e:
            logging.error(f"資料庫寫入失敗: {e}")

def main():
    if not os.path.exists(SteamConfig.RAW_DATA_PATH):
        logging.error(f"資料夾不存在: {SteamConfig.RAW_DATA_PATH}")
        return

    potential_files = [f for f in os.listdir(SteamConfig.RAW_DATA_PATH) if 'games' in f.lower() and f.endswith('.csv')]
    
    if not potential_files:
        logging.error(f"在 {SteamConfig.RAW_DATA_PATH} 找不到任何遊戲數據 CSV")
        return

    games_csv = os.path.join(SteamConfig.RAW_DATA_PATH, potential_files[0])
    logging.info(f"鎖定目標資料檔: {games_csv}")
    
    source = NewSteamDataSource(games_csv)
    df_pl = source.fetch_data()
    
    if df_pl is not None:
        final_df_pandas = DataTransformer.process(df_pl)
        if final_df_pandas is not None:
            try:
                db_uri = SteamConfig.get_db_uri()
                loader = DataLoader(db_uri)
                loader.load(final_df_pandas)
            except ValueError as e:
                logging.error(e)

if __name__ == '__main__':
    main()
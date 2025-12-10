import pytest
import polars as pl
from scripts.process_steam_data import DataTransformer

# 測試用假資料
@pytest.fixture
def sample_raw_df():
    return pl.DataFrame({
        "AppID": [1, 2],
        "Name": ["Game A", "Game B"],
        "Price": ["$10.00", "Free"],
        "Positive": [100, 50],
        "Negative": [10, 50],
        "Estimated owners": ["0-20,000", "50,000-100,000"]
    })

def test_price_cleaning(sample_raw_df):
    """測試價格是否有被正確轉為浮點數"""
    df_result = DataTransformer.process(sample_raw_df)
    assert df_result is not None
    assert df_result.iloc[0]['price'] == 10.0
    assert df_result.iloc[1]['price'] == 0.0

def test_positive_ratio(sample_raw_df):
    """測試好評率計算"""
    df_result = DataTransformer.process(sample_raw_df)
    # Game A: 100 / (100+10) = 0.909
    assert round(df_result.iloc[0]['positive_ratio'], 2) == 0.91
    # Game B: 50 / (50+50) = 0.5
    assert df_result.iloc[1]['positive_ratio'] == 0.5

def test_owners_parsing(sample_raw_df):
    """測試擁有者區間平均值"""
    df_result = DataTransformer.process(sample_raw_df)
    # "0-20,000" avg = 10000
    assert df_result.iloc[0]['owners_avg'] == 10000
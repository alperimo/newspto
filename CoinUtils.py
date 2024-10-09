from binance.client import Client
from typing import Any
import pandas as pd

import Globals

@staticmethod
def GetHistoricalData(symbol: str, interval: str, start_str: str | int, end_str: str | int) -> pd.DataFrame:
    klines = Client.get_historical_klines(symbol, interval, start_str, end_str)
    
    df = pd.DataFrame(klines)
    df.drop(df.columns[[6, 7, 8, 9, 10, 11]], axis=1, inplace=True)
    df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
    df['datetime'] = df['datetime'].values.astype(dtype='datetime64[ms]')
    df['open'] = df['open'].values.astype(float)
    df['high'] = df['high'].values.astype(float)
    df['low'] = df['low'].values.astype(float)
    df['close'] = df['close'].values.astype(float)
    df['volume'] = df['volume'].values.astype(float)
    
    validIntervals = ['1h', '1d']
    if interval not in validIntervals:
        raise ValueError(f"Invalid interval: {interval}")
    
    print(f"Created DataFrame for {symbol} in {interval} interval: {df}")
    
    Globals.coinHistoricalDataByInterval[interval][symbol] = pd.concat(
        [Globals.coinHistoricalDataByInterval[interval].get(symbol, pd.DataFrame()), df]
    ).drop_duplicates(subset=['datetime'], keep='last')
    
    return df
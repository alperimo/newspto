from collections import defaultdict, deque
from datetime import datetime
from typing import Any
from binance.exceptions import BinanceAPIException
import pandas as pd
import ccxt, time

import Globals

# Limits
MAX_ORDERS_10_SEC = 50
MAX_ORDERS_24_HR = 160_000

# Track timestamps of recent orders
order_timestamps_10_sec = deque()
order_timestamps_24_hr = deque()

# Initialize ccxt exchanges for fallback
CCXT_EXCHANGES = {
    'kucoin': ccxt.kucoin(),
    'kraken': ccxt.kraken({'enableRateLimit': True, 'rateLimit': 6000}),
    'mexc': ccxt.mexc()
    #'cryptocom': ccxt.cryptocom({'fetchMarkOHLCV': True}),
}

COIN_EXCHANGE: dict[str, str] = defaultdict()

@staticmethod
def CalculateAvgPrice(row) -> float:
    return (row['open'] + row['high'] + row['low'] + row['close']) / 4

@staticmethod
def GetAvgHistoricalData(historicalData: pd.DataFrame) -> list[float] | float | None:
    if historicalData.empty:
        return None

    if len(historicalData) == 1:
        return CalculateAvgPrice(historicalData.iloc[0])

    avg_ohlc_list: list[float] = [CalculateAvgPrice(row) for _, row in historicalData.iterrows()]
    return avg_ohlc_list

@staticmethod
def GetCorrectExchangeSymbol(exchange: str, symbol: str) -> str:
    if exchange == "kucoin" and not symbol.endswith("/USDT"):
        return symbol.replace("USDT", "/USDT")
    elif exchange == "kraken":
        symbol = symbol.replace("USDT", "USD").replace("/", "")
    elif exchange == "mexc":
        symbol = symbol.replace("USDT", "_USDT")
    elif exchange == "cryptocom":
        symbol = symbol.replace("USDT", "_USDC")
    
    return symbol

@staticmethod
def GetHistoricalData(symbol: str, interval: str, start_str: str | int, end_str: str | int = None) -> pd.DataFrame:
    print(f"Fetching historical data for {symbol} in {interval} interval from {start_str} to {end_str}...")
    def TryFromBinance():
        now = time.time()
    
        # Remove timestamps that are older than 10 seconds or 24 hours
        while order_timestamps_10_sec and now - order_timestamps_10_sec[0] > 10:
            order_timestamps_10_sec.popleft()
        while order_timestamps_24_hr and now - order_timestamps_24_hr[0] > 86400:
            order_timestamps_24_hr.popleft()
            
        # Check if we're close to limits
        if len(order_timestamps_10_sec) >= MAX_ORDERS_10_SEC:
            print("10-second order limit reached. Waiting...")
            time.sleep(12 - (now - order_timestamps_10_sec[0])) 
        elif len(order_timestamps_24_hr) >= MAX_ORDERS_24_HR:
            print("24-hour order limit reached. Exiting to avoid IP ban.")
            return None
        
        validIntervals = ['1h', '1d']
        if interval not in validIntervals:
            raise ValueError(f"Invalid interval: {interval}")

        # Fetch OHLCV data from Binance
        klines = Globals.binanceClient.get_historical_klines(symbol, interval, str(start_str), str(end_str))
        
        if not klines:
            raise Exception(f"No kline data found for symbol {symbol} in the interval {interval} between {start_str} and {end_str} from Binance.")
        
        order_timestamps_10_sec.append(now)
        order_timestamps_24_hr.append(now)
        
        df = pd.DataFrame(klines)
        df.drop(df.columns[[6, 7, 8, 9, 10, 11]], axis=1, inplace=True)
        df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
        df['datetime'] = df['datetime'].values.astype(dtype='datetime64[ms]')
        df['open'] = df['open'].values.astype(float)
        df['high'] = df['high'].values.astype(float)
        df['low'] = df['low'].values.astype(float)
        df['close'] = df['close'].values.astype(float)
        df['volume'] = df['volume'].values.astype(float)
        
        #print(f"Created DataFrame for {symbol} in {interval} interval: {df}")
        
        Globals.coinHistoricalDataByInterval[interval][symbol] = pd.concat(
            [Globals.coinHistoricalDataByInterval[interval].get(symbol, pd.DataFrame()), df]
        ).drop_duplicates(subset=['datetime'], keep='last')
        
        return df
    
    def TryExchange(exchange: str):
        ex = CCXT_EXCHANGES[exchange]
        try:
            formattedSymbol = GetCorrectExchangeSymbol(exchange, symbol)
            
            # Fetch OHLCV data from alternative exchange
            candleLimit = 1 if interval == '1d' else 24
            ohlcv = ex.fetch_ohlcv(formattedSymbol, interval, since=start_str, limit=candleLimit)
            
            # Wait for rate limit
            time.sleep(ex.rateLimit / 1000)
            
            if not ohlcv:
                raise ccxt.BaseError(f"No data found for {formattedSymbol} in {interval} interval from {exchange}.")
                
            # Convert ccxt data to DataFrame
            df = pd.DataFrame(ohlcv, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
            df['datetime'] = pd.to_datetime(df['datetime'], unit='ms')
            df[['open', 'high', 'low', 'close', 'volume']] = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
            
            Globals.coinHistoricalDataByInterval[interval][formattedSymbol] = pd.concat(
                [Globals.coinHistoricalDataByInterval[interval].get(formattedSymbol, pd.DataFrame()), df]
            ).drop_duplicates(subset=['datetime'], keep='last')
            
            if COIN_EXCHANGE.get(symbol, "") == "":
                COIN_EXCHANGE[symbol] = exchange
            
            return df
        except ccxt.RequestTimeout as e:
            time.sleep(ex.rateLimit / 1000)
            raise ccxt.RequestTimeout(f"[{datetime.now()}] Request timeout: {type(e).__name__, str(e)}")
        except ccxt.DDoSProtection as e:
            time.sleep(ex.rateLimit / 1000)
            raise ccxt.DDoSProtection(f"[{datetime.now()}] DDoS Protection triggered: {type(e).__name__, str(e)}")
        except ccxt.ExchangeNotAvailable as e:
            time.sleep(60)
            raise ccxt.ExchangeNotAvailable(f"[{datetime.now()}] Exchange not available: {type(e).__name__, str(e)}")
        except ccxt.NetworkError as e:
            time.sleep(60)
            raise ccxt.NetworkError(f"[{datetime.now()}] Network error: {type(e).__name__, str(e)}")
        except ccxt.BaseError as ex_error:
            raise ccxt.BaseError(f"Failed to get data for {formattedSymbol} from {exchange}: {ex_error}")
    
    coinExchange: str = COIN_EXCHANGE.get(symbol, "")
    if coinExchange == "" or coinExchange == "binance":
        try:
            return TryFromBinance()
        except Exception as e:
            print(f"Binance does not support symbol {symbol}. Trying alternative exchanges...")
            for ex_name in CCXT_EXCHANGES.keys():
                try:
                    return TryExchange(ex_name)
                except ccxt.BaseError as ex_error:
                    print(ex_error)
                        
            raise e
    else:
        return TryExchange(coinExchange)
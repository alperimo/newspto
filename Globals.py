from collections import defaultdict
from typing import Any
from binance.client import Client
import pandas as pd

binanceClient: Client = None

topCoinNameBySymbol: dict[str, str] = {}

scrapData: dict[str, dict[str, Any]] = {}

coinHistoricalDataByInterval: dict[str, dict[str, pd.DataFrame]] = defaultdict(dict)

eventValidations: pd.DataFrame | None = None
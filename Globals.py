from collections import defaultdict
from typing import Any
import pandas as pd

topCoinNameBySymbol: dict[str, str] = {}

scrapData: dict[str, dict[str, Any]] = {}

coinHistoricalDataByInterval: dict[str, dict[str, pd.DataFrame]] = defaultdict(dict)

eventValidations: pd.DataFrame | None = None
from dataclasses import dataclass, field

"""
    CMC: CoinMarketCal
"""

@dataclass
class CMCEvent:
    coin: str = ""
    date: str = ""
    title: str = ""
    description: str = ""
    coinChangeDollar: str = ""
    coinChangePercent: str = ""
    aiAnalysis: str = ""
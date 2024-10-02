from __future__ import annotations
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
    
    confidencePct: int = 0
    votes: int = 0
    
    # All coin price values 1-2-3-4-5-7-14-30 days after the event
    coinChangesByDay: list[str] = field(default_factory=list)
    
    # All coin price values 1-6-12-24 hours after the event
    coinChangesByHour: list[str] = field(default_factory=list)
    
@dataclass
class CMCEventValidation:
    confidencePct: int = 0
    votes: int = 0
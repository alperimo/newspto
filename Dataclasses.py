from __future__ import annotations
from dataclasses import dataclass, field

"""
    CMC: CoinMarketCal
"""

@dataclass
class CMCEvent:
    id: str = ""
    category: str = ""
    coins: list[str] = field(default_factory=list)
    date: str = ""
    title: str = ""
    description: str = ""
    coinChangeDollarsOnRetrieve: list[str] = field(default_factory=list)
    coinChangePercentsOnRetrieve: list[str] = field(default_factory=list)
    aiAnalysis: str = ""
    
    confidencePct: int = 0
    votes: int = 0
    
    proofImage: str = ""
    sourceHref: str = ""
    
    # All coin price values 1-2-3-4-5-7-14-30 days after the event
    coinChangesByDay: list[str] = field(default_factory=list)
    
    # All coin price values 1-6-12-24 hours after the event
    coinChangesByHour: list[str] = field(default_factory=list)
    
@dataclass
class CMCEventValidation:
    confidencePct: int = 0
    votes: int = 0
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
    
    """
        Date Format Examples:
            mm: Jan, Feb, (Mar, March), (Apr, April), May, (Jun, June), Jul, Aug, Sep, Oct, Nov, Dec

            Mar 2024
            31 Mar 2024 | 31 Mar 2024 or earlier | 31 Mar 2024 (or earlier)
            From 29 Dec to 31 Mar 2024
            Q1 yyyy | Q2 yyyy | Q3 yyyy | Q4 yyyy
            
    """
    date: str = ""
    
    title: str = ""
    description: str = ""
    coinChangeDollarsOnRetrieve: list[str] = field(default_factory=list)
    coinChangePercentsOnRetrieve: list[str] = field(default_factory=list)
    aiAnalysis: str = ""
    
    confidencePct: float = 0.0
    votes: int = 0
    
    proofImage: str = ""
    sourceHref: str = ""
    
    """
        b3d: list[int], 3 days before the event for every hour
        b2d: list[int], 2 days before the event for every hour
        b1d: list[int], 1 day before the event for every hour
        d: list[int], the day of the event for every hour
        a1d: list[int], 1 day after the event for every hour
        a2d: list[int], 2 days after the event for every hour
        ...
    """
    # All coin price values (-2),(-1),0-1-2-3-4-5-7-10-14-21-30 days after the event
    coinChangesByDay: dict[str, list[int]] = field(default_factory=list)
    
@dataclass
class CMCEventValidation:
    confidencePct: float = 0
    votes: int = 0
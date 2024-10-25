from enum import auto, Enum

class DateType(Enum):
    EXACT = auto() # 31 Mar 2024
    MONTH = auto() # Mar 2024
    RANGE = auto() # From 29 Dec to 31 Mar 2024
    QUARTER = auto() # Q1 2024
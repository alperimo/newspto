import re
from datetime import datetime, timedelta

from Enums import DateType
import Constants

MONTHS = {
    "Jan": ("01", 31), "January": ("01", 31),
    "Feb": ("02", 28), "February": ("02", 28),
    "Mar": ("03", 31), "March": ("03", 31),
    "Apr": ("04", 30), "April": ("04", 30), "May": ("05", 31), 
    "Jun": ("06", 30), "June": ("06", 30), 
    "Jul": ("07", 31), "July": ("07", 31),
    "Aug": ("08", 31), "August": ("08", 31),
    "Sep": ("09", 30), "September": ("09", 30),
    "Oct": ("10", 31), "October": ("10", 31),
    "Nov": ("11", 30), "November": ("11", 30), 
    "Dec": ("12", 31), "December": ("12", 31)
}

MONTH_PATTERN = r"(Jan|January|Feb|February|Mar|March|Apr|April|May|Jun|June|Jul|July|Aug|August|Sep|September|Oct|October|Nov|November|Dec|December)"

@staticmethod
def CalculateDateFromInterval(base_date: datetime, interval: str) -> str:
    """
        Example interval: b1m, b2w, b3d, a1m, a1w, a3d, d, a1w, ...
    """
    
    if interval == "d":
        return base_date.strftime(Constants.UTC_FORMAT)
    
    try:
        multiplier = int(interval[1:-1])
        unit = interval[-1]
        
        days = {'m': 30, 'w': 7, 'd': 1}.get(unit, 1)
        sign = 1 if interval[0] == 'a' else -1
        
        return (base_date + timedelta(days = sign * days * multiplier)).strftime(Constants.UTC_FORMAT)
    except:
        return base_date.strftime(Constants.UTC_FORMAT)

@staticmethod
def GetDateType(string: str) -> tuple[DateType, re.Match] | None:
    if match := re.search(r"From\s+(\d{1,2})\s+" + MONTH_PATTERN + r"\s+to\s+(\d{1,2})\s+" + MONTH_PATTERN + r"\s+(\d{4})", string):
        return DateType.RANGE, match
    
    if match := re.search(r"(\d{1,2})\s+" + MONTH_PATTERN + r"\s+(\d{4})", string):
        return DateType.EXACT, match
    
    if match := re.search(MONTH_PATTERN + r"\s+(\d{4})", string):
        return DateType.MONTH, match
    
    if match := re.search(r"(Q[1-4])\s+(\d{4})", string):
        return DateType.QUARTER, match

@staticmethod
def GetCorrectFormattedDate(string: str) -> str | tuple[str, str] | None:
    """
        Returns string in yyyy-dd-mm (utc-format)
    """
    
    dateType, match = GetDateType(string)
    
    match dateType:
        case DateType.EXACT:
            day = match.group(1).zfill(2)
            month = MONTHS[match.group(2)][0] 
            year = match.group(3)
            
            return f"{year}-{month}-{day}"
        
        case DateType.MONTH:
            month = match.group(1)
            year = int(match.group(2))
            
            day = MONTHS[month][1]
            if month == "Feb" and IsLeapYear(year):
                day = 29
            
            return f"{year}-{MONTHS[month][0]}-{day:02d}"
        
        case DateType.RANGE:
            startDay = match.group(1).zfill(2)
            startMonth = MONTHS[match.group(2)][0] 
            
            endDay = match.group(3).zfill(2)
            endMonth = MONTHS[match.group(4)][0] 
            endYear = match.group(5)
            
            if endMonth < startMonth:
                startYear = int(endYear) - 1
            else:
                startYear = endYear
            
            return f"{startYear}-{startMonth}-{startDay}", f"{endYear}-{endMonth}-{endDay}"
        
        case DateType.QUARTER:
            quarter = match.group(1)
            year = match.group(2)
            quarter_middle = {
                "Q1": "02-15",
                "Q2": "05-15",
                "Q3": "08-15",
                "Q4": "11-15"
            }
            
            return f"{year}-{quarter_middle[quarter]}"
    
@staticmethod
def IsLeapYear(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

# Examples

"""
print(GetCorrectFormattedDate("31 Mar 2024"))  # 2024-03-31
print(GetCorrectFormattedDate("From 29 Dec to 31 Mar 2024"))  # (2023-12-29, 2024-31-03)
print(GetCorrectFormattedDate("31 Mar 2024 or earlier"))  # 2024-03-31
print(GetCorrectFormattedDate("31 Mar 2024 (or earlier)"))  # 2024-03-31
print(GetCorrectFormattedDate("Q1 2024"))  # 2024-02-15
print(GetCorrectFormattedDate("Mar 2024"))  # 2024-03-31
print(GetCorrectFormattedDate("Apr 2023"))  # 2023-04-30
"""
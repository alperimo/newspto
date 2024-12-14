from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import math
import ccxt
from datasets import load_dataset
from dataclasses import asdict
from typing import Any

from binance.exceptions import BinanceAPIException
import pandas as pd, os, re
import time, pytz

from Dataclasses import CMCEvent
from Enums import DateType
import Constants, CoinUtils, DataUtils, DateUtils, Globals

class DatasetHelper:
    def ToConversationalStyle(row: pd.Series) -> dict[str, Any] | None:
        """conversations = [
            [
                {
                    "role": "system",
                    "value": "You are an assistant skilled at analyzing cryptocurrency events and predicting price movements based on historical and event-driven data."
                }
            ]
        ]"""
        
        if isinstance(row, list):
            isConversational = False
            for e in row:
                if all([e.get("role"), e.get("value")]):
                    isConversational = True
                    break
            
            if isConversational:
                print(f"Skipping row: {row} as it is already in conversational style.")
                return row
        
        conversations = []
        conversations.append({
            "role": "user",
            "value": (
                f"Analyze the impact of the following crypto event on coins/tokens in 2-3 sentences and directly predict its impact on prices: "
                f"ID: {row['id']}, "
                f"Category: {row['category']} event, "
                f"Date: {row['date']} (UTC: {DateUtils.GetCorrectFormattedDate(row['date'])}), "
                f"Title: {row['title']}, "
                f"Coins involved: {', '.join(row['coins'])}, "
                f"Description: {row['description']}, "
                f"Proof image URL: {row['proofImage']}, "
                f"Source link: {row['sourceHref']}, "
                f"Votes: {row['votes']} (indicating community confidence of {row['confidencePct']}%), "
                f"Please provide an analysis, any relevant historical price data and your prediction for the price movement of the coins involved."
            ).strip().replace(r'\/', '/')
        })
        
        priceAnalysis = DatasetHelper.CalculateCoinsPriceChangesRelativeToEvent(row)
        """
        coinsPricesByDate = row.get("coinsPricesByDate")
        if coinsPricesByDate:
            for coin, allPrices in coinsPricesByDate.items():
                if allPrices is None or not allPrices:
                    continue
                
                priceAnalysis += f"Historical and forecasted price data for {coin}: "
                for date, datePrices in allPrices.items():
                    if datePrices is None:
                        price_points = f"{date}: Unknown"
                        continue
                    
                    datePrices = datePrices.tolist()
                    if isinstance(datePrices, list) and len(datePrices) > 1:
                        price_points = f"{date} (00:00 to 23:00): ${', $'.join(map(str, datePrices))}"
                        #price_points = f"{date} (per hour): " + ", ".join(f"at {str(i).zfill(2)}:00 ${price}" for i, price in enumerate(datePrices))
                    else:
                        price_points = f"{date}: ${datePrices[0]}"
                    
                    priceAnalysis += price_points + "; "
        """

        aiAnalysis = row.get("aiAnalysis") and f"Analysis: {row['aiAnalysis']}" or ""
        
        if not aiAnalysis and not priceAnalysis:
            return None
        
        conversations.append({
            "role": "assistant",
            "value": (
                ", ".join(filter(None, [aiAnalysis, priceAnalysis]))
            ).strip().replace(r'\/', '/')
        })

        data = {
            "conversations": conversations,
            "image_path": row['proofImage'],
            "source_link": row['sourceHref']
        }

        return data
    
    @staticmethod
    def AddUpcomingEvents(entries: list[CMCEvent], datasetPath: str) -> pd.DataFrame:
        if not entries:
            print("No entries to update dataset!")
            return
        
        if not os.path.exists(datasetPath):
            print(f"Dataset file {datasetPath} does not exist.")
            return
        
        newEventsDf: pd.DataFrame = pd.DataFrame([asdict(entry) for entry in entries])
        df = pd.read_json(datasetPath, orient = 'records', lines = True)
        
        if df.empty:
            df = newEventsDf
        else:
            newEventsDf = newEventsDf[~newEventsDf['id'].isin(df['id'])]
            df = pd.concat([df, newEventsDf], ignore_index = True)
            
        df.to_json(datasetPath, orient = 'records', lines = True)
        
        todayDate = datetime.now(pytz.timezone('Europe/Berlin')).strftime("%d %b %Y")
        newEventsInputPromptDf = pd.DataFrame(columns = ["input"])
        for _, row in newEventsDf.iterrows():
            inputPrompt = f"Category: {row['category']}, Title: {row['title']}, Date: {row['date']}, Today's Date: {todayDate}, Coins: [{', '.join(row['coins'])}], Description: {row['description']}"
            newEventsInputPromptDf.loc[len(newEventsInputPromptDf)] = {"input": inputPrompt}
            
        newEventsInputPromptDf.to_csv(f"{Constants.UPCOMING_EVENTS_PATH}/{datetime.now().strftime("%d%m%Y_%H%M%S")}.csv", index = False)
        return newEventsDf

    @staticmethod
    def CalculateCoinsPriceChangesRelativeToEvent(row: pd.Series):
        coinsPricesByDate = row.get("coinsPricesByDate")
        coinsPriceChangesRelativeToEvent = ""

        if coinsPricesByDate:
            for coin, allPrices in coinsPricesByDate.items():
                if allPrices is None or not allPrices:
                    continue
                
                eventDate: str = DateUtils.GetCorrectFormattedDate(row['date'])
                coinPricesByDaysRelativeToEvent = {}
                for date, datePrices in allPrices.items():
                    if datePrices is None:
                        continue

                    if isinstance(eventDate, tuple):
                        eventDate = eventDate[0]
                        
                    dayDiff = DateUtils.CalculateRelativeDaysBetweenDates(date, eventDate)
                    coinPricesByDaysRelativeToEvent[dayDiff] = datePrices
                
                # Sort the dictionary by days
                coinPricesByDaysRelativeToEvent = dict(sorted(coinPricesByDaysRelativeToEvent.items()))
                
                # Calculate prices changes
                priceAnalysis = ""
                priceAtEventDate = coinPricesByDaysRelativeToEvent.get(0)
                if priceAtEventDate is None:
                    continue
                
                if priceAtEventDate.any():
                    priceAtEventDate = sum(priceAtEventDate) / len(priceAtEventDate) 
                    
                pricesByMonth, pricesByWeek, pricesByDay = {}, {}, {}
                priceChangeRelativeToEventByMonth, priceChangeRelativeToEventByWeek, priceChangeRelativeToEventByDay = {}, {}, {}
                for dayDiff in list(coinPricesByDaysRelativeToEvent.keys()):
                    price = sum(coinPricesByDaysRelativeToEvent[dayDiff]) / len(coinPricesByDaysRelativeToEvent[dayDiff])
                    
                    absDayDiff = abs(dayDiff)
                    # Monthly prices
                    if absDayDiff >= 30:
                        month = dayDiff // 30
                        if month not in pricesByMonth:
                            pricesByMonth[month] = []
                            
                        pricesByMonth[month].append(price)
                    # Weekly prices
                    elif absDayDiff >= 7:
                        week = dayDiff // 7
                        if week not in pricesByWeek:
                            pricesByWeek[week] = []
                            
                        pricesByWeek[week].append(price)
                    # Daily prices
                    else:
                        if dayDiff not in pricesByDay:
                            pricesByDay[dayDiff] = []
                            
                        pricesByDay[dayDiff].append(price)
                        
                def getBestTradingVariation():
                    variations: dict[str, int] = {}
                    #newsAddedDate = row.get("newsAddedDate")
                    for buyingDay in sorted(coinPricesByDaysRelativeToEvent.keys()):
                        # Ignore buying days that are at least 10 days before the event
                        if buyingDay < -10:
                            continue
                        
                        for sellingDay in sorted(coinPricesByDaysRelativeToEvent.keys()):
                            if buyingDay >= sellingDay:
                                continue
                            
                            # Ignore selling days that are at least 10 days after the event
                            if sellingDay > 14:
                                continue
                            
                            #if buyingDay < newsAddedDate:
                            #    continue
                            
                            buyingPrice = sum(coinPricesByDaysRelativeToEvent[buyingDay]) / len(coinPricesByDaysRelativeToEvent[buyingDay])
                            sellingPrice = sum(coinPricesByDaysRelativeToEvent[sellingDay]) / len(coinPricesByDaysRelativeToEvent[sellingDay])
                            variation = ((sellingPrice - buyingPrice) / buyingPrice) * 100
                            variations[f"{buyingDay},{sellingDay}"] = variation
                            
                    # Find the highest positive increase and negative decrease trading variations
                    highestPositiveVariation, highestNegativeVariation = ("", 0), ("", 0)
                    for variation in variations.items():
                        if variation[1] > highestPositiveVariation[1]:
                            highestPositiveVariation = variation
                        elif variation[1] < highestNegativeVariation[1]:
                            highestNegativeVariation = variation
                            
                    return highestPositiveVariation, highestNegativeVariation
                
                def formatTheDay(day, suffix = "before"):
                    if day == 0:
                        return "on the event day"
                    elif day == 1:
                        return f"1 day {suffix}"
                    elif day > 1:
                        return f"{day} days {suffix}"
                
                highestPositiveVariation, highestNegativeVariation = getBestTradingVariation()
                if highestPositiveVariation[0] != "":
                    bestDayToBuy, bestDayToSell = map(lambda x: abs(int(x)), highestPositiveVariation[0].split(","))
                    bestDayToBuy = formatTheDay(bestDayToBuy, "before")
                    bestDayToSell = formatTheDay(bestDayToSell, "after the event")
                else:
                    bestDayToBuy, bestDayToSell = '-', '-'
                    
                if highestNegativeVariation[0] != "":
                    worstDayToBuy, worstDayToSell = map(lambda x: abs(int(x)), highestNegativeVariation[0].split(","))
                    worstDayToBuy = formatTheDay(worstDayToBuy, "before")
                    worstDayToSell = formatTheDay(worstDayToSell, "after the event")
                else:
                    worstDayToBuy, worstDayToSell = '-', '-'
                
                if highestPositiveVariation[1] >= 25:
                    priceAnalysis += f"Huge gain potential: Buy {bestDayToBuy} and sell {bestDayToSell} for a {highestPositiveVariation[1]:.2f}% gain. "
                elif highestPositiveVariation[1] >= 10:
                    priceAnalysis += f"Significant gain potential: Buy {bestDayToBuy} and sell {bestDayToSell} for a {highestPositiveVariation[1]:.2f}% gain. "
                elif highestNegativeVariation[1] <= -25:
                    priceAnalysis += f"Huge loss risk: Avoid buying {worstDayToBuy} and selling {worstDayToSell} to prevent a {highestNegativeVariation[1]:.2f}% loss. "
                elif highestNegativeVariation[1] <= -10:
                    priceAnalysis += f"Significant loss risk: Avoid buying {worstDayToBuy} and selling {worstDayToSell} to prevent a {highestNegativeVariation[1]:.2f}% loss. "
                elif highestPositiveVariation[1] >= 5:
                    priceAnalysis += f"Small gain potential: Buy {bestDayToBuy} and sell {bestDayToSell} for a {highestPositiveVariation[1]:.2f}% gain. "
                elif highestNegativeVariation[1] <= -2:
                    priceAnalysis += f"Small loss risk: Avoid buying {worstDayToBuy} and selling {worstDayToSell} to prevent a {highestNegativeVariation[1]:.2f}% loss. "
                else:
                    priceAnalysis += f"Neutral: Maybe buy {bestDayToBuy} and sell {bestDayToSell} for a {highestPositiveVariation[1]:.2f}% gain. "
                
                if priceAnalysis:
                    coinsPriceChangesRelativeToEvent += f"Forecasted prices for {coin}: {priceAnalysis.strip(", ")} "
                    continue
                
                def analyseInDepth():
                    forecastedMonthlyAnalysis: list[str] = []
                    forecastedWeeklyAnalysis: list[str] = []
                    # Calculate average price changes for each month
                    for month in sorted(pricesByMonth.keys()):
                        monthAvgPrice = sum(pricesByMonth[month]) / len(pricesByMonth[month])
                        priceChangePct = ((monthAvgPrice - priceAtEventDate) / priceAtEventDate) * 100
                        if month < 0:
                            if priceChangePct < 0:
                                priceAnalysis += f"Price difference of the previous {abs(month)} month(s) relative to the event date was {priceChangePct:.2f}% (lower, consider buying). "
                                #priceAnalysis += ", indicating that the coin was undervalued before the event. It may have been a good buying opportunity. "
                            else:
                                priceAnalysis += f"Price difference of the previous {abs(month)} month(s) relative to the event date was {priceChangePct:.2f}% (higher, consider selling). "
                                #priceAnalysis += ", suggesting that the coin had already appreciated before the event. It may not have been the best time to buy. "
                        else:
                            forecastedMonthlyAnalysis.append(f"Forecasted change in next {month} month(s) after the event: {priceChangePct:.2f}%, ")

                        priceChangeRelativeToEventByMonth[month] = priceChangePct
                    
                    # Calculate average price changes for each week
                    for week in sorted(pricesByWeek.keys()):
                        weekAvgPrice = sum(pricesByWeek[week]) / len(pricesByWeek[week])
                        priceChangePct = ((weekAvgPrice - priceAtEventDate) / priceAtEventDate) * 100
                        if week < 0:
                            if priceChangePct < 0:
                                priceAnalysis += f"Price difference of the previous {abs(week)} week(s) relative to the event date was {priceChangePct:.2f}% (lower, consider buying). "
                                #priceAnalysis += ", indicating that the coin was undervalued before the event. It may have been a good buying opportunity."
                            else:
                                priceAnalysis += f"Price difference of the previous {abs(week)} week(s) relative to the event date was {priceChangePct:.2f}% (higher, consider selling). "
                                #priceAnalysis += ", suggesting that the coin had already appreciated before the event. It may not have been the best time to buy."
                        else:
                            forecastedWeeklyAnalysis.append(f"Forecasted change in next {week} week(s) after the event: {priceChangePct:.2f}%, ")
                            
                        priceChangeRelativeToEventByWeek[week] = priceChangePct
                            
                    def getPriceAnalysis(priceChangePct, day):
                        """
                        Generates a price analysis message based on the percentage change.
                        This function returns different strings depending on the priceChangePct.
                        """
                        analysis_message = f"Forecasted change in {day} day(s) after the event: {priceChangePct:.2f}% - "

                        if priceChangePct > 30:
                            analysis_message += "very high growth potential. Strong buy recommendation. "
                        elif priceChangePct > 10:
                            analysis_message += "positive growth. Good opportunity for investment. "
                        elif priceChangePct > 5:
                            analysis_message += "moderate growth, solid opportunity. "
                        elif priceChangePct > 2:
                            analysis_message += "slight growth. Consider if you're looking for safer investments. "
                        elif priceChangePct > 0:
                            analysis_message += "slight increase, consider watching closely for further developments. "
                        elif priceChangePct < -30:
                            analysis_message += "significant negative change. Strong sell recommendation. "
                        elif priceChangePct < -10:
                            analysis_message += "notable decline, consider selling if you want to minimize losses. "
                        elif priceChangePct < -5:
                            analysis_message += "moderate decline, evaluate whether you want to hold or sell. "
                        elif priceChangePct < 0:
                            analysis_message += "slight decline, keep monitoring the situation. "

                        return analysis_message
                            
                    # Calculate average price changes for each day
                    for day in sorted(pricesByDay.keys()):
                        dayAvgPrice = sum(pricesByDay[day]) / len(pricesByDay[day])
                        priceChangePct = ((dayAvgPrice - priceAtEventDate) / priceAtEventDate) * 100
                        if day < 0:
                            priceChangePct *= -1
                            priceAnalysis += f"Forecasted change from {abs(day)} day(s) before until to the event: {priceChangePct:.2f}%, "
                        elif day == 0:
                            # Calculate forecasted price change in 24 hours after the event
                            openPrice = coinPricesByDaysRelativeToEvent[day][0]
                            priceChangePct = ((dayAvgPrice - openPrice) / openPrice) * 100
                            priceAnalysis += f"Forecasted change during the event day (first 24 hours): {priceChangePct:.2f}%, "
                        else:
                            priceAnalysis += f"Forecasted change in next {day} day(s) after the event: {priceChangePct:.2f}%, "
                            
                        priceChangeRelativeToEventByDay[day] = priceChangePct
                        
                    for forecasted in forecastedWeeklyAnalysis:
                        priceAnalysis += forecasted
                    
                    for forecasted in forecastedMonthlyAnalysis:
                        priceAnalysis += forecasted
                        
                    subMidTermChanges, midTermChanges, longTermChanges = [], [], []
                    
                    priceTwoWeeksBefore, priceOneWeekBefore, priceOneWeekAfter, priceTwoWeeksAfter = pricesByWeek.get(-2), pricesByWeek.get(-1), pricesByWeek.get(1), pricesByWeek.get(2)
                    if priceOneWeekBefore and priceOneWeekAfter:
                        priceOneWeekBefore = sum(priceOneWeekBefore) / len(priceOneWeekBefore)
                        priceOneWeekAfter = sum(priceOneWeekAfter) / len(priceOneWeekAfter)
                        shortTermImpact = ((priceOneWeekAfter - priceOneWeekBefore) / priceOneWeekBefore) * 100
                        priceAnalysis += f"Short-term impact (buying 1 week before and selling 1 week after the event): {shortTermImpact:.2f}%, "
                    
                    # Calculate short-term impact
                    if priceTwoWeeksBefore and priceTwoWeeksAfter:
                        priceTwoWeeksBefore = sum(priceTwoWeeksBefore) / len(priceTwoWeeksBefore)
                        priceTwoWeeksAfter = sum(priceTwoWeeksAfter) / len(priceTwoWeeksAfter)
                        shortTermImpact = ((priceTwoWeeksAfter - priceTwoWeeksBefore) / priceTwoWeeksBefore) * 100
                        priceAnalysis += f"Short-term impact (buying two 2 weeks before and selling 2 weeks after the event): {shortTermImpact:.2f}%, "
                    
                    # Calculate immediate impact
                    pricesBeforeEvent, pricesAfterEvent = [], []
                    for closeTermDay in range(-3, 4):  # Including the event day itself
                        if closeTermDay in pricesByDay:
                            if closeTermDay < 0:
                                pricesBeforeEvent.append(sum(pricesByDay[closeTermDay]) / len(pricesByDay[closeTermDay]))
                            else:
                                pricesAfterEvent.append(sum(pricesByDay[closeTermDay]) / len(pricesByDay[closeTermDay]))

                    if pricesBeforeEvent and pricesAfterEvent:
                        priceBeforeEvent = sum(pricesBeforeEvent) / len(pricesBeforeEvent)
                        priceAfterEvent = sum(pricesAfterEvent) / len(pricesAfterEvent)
                        immediateImpact = ((priceAfterEvent - priceBeforeEvent) / priceBeforeEvent) * 100
                        priceAnalysis += f"Immediate impact (buying 3 days before and selling 3 days after the event): {immediateImpact:.2f}%, "

                    # Calculate Post sub-mid-term week impact
                    for subMidTermWeek in range(1, 4):
                        if subMidTermWeek in pricesByWeek:
                            subMidTermChanges.append(sum(pricesByWeek[subMidTermWeek]) / len(pricesByWeek[subMidTermWeek]))
                        
                    if subMidTermChanges: 
                        subMidTermAvgChange = sum(subMidTermChanges) / len(subMidTermChanges)
                        subMidTermImpact = ((subMidTermAvgChange - priceAtEventDate) / priceAtEventDate) * 100
                        priceAnalysis += f"Post Sub-mid-term impact (Buying on the event day and selling in {len(subMidTermChanges)} week(s) after the event): {subMidTermImpact:.2f}%, "
                    
                    # Calculate Post Mid-term impact
                    for midTermMonth in range(1, 2):
                        if midTermMonth in pricesByMonth:
                            midTermChanges.append(sum(pricesByMonth[midTermMonth]) / len(pricesByMonth[midTermMonth]))
                            
                    if midTermChanges:
                        midTermAvgChange = sum(midTermChanges) / len(midTermChanges)
                        midTermImpact = ((midTermAvgChange - priceAtEventDate) / priceAtEventDate) * 100
                        priceAnalysis += f"Post Mid-term impact (Buying on the event day and selling in 1 month after the event): {midTermImpact:.2f}%, "

                    # Calculate Pre-Post Mid-term Week impact
                    def getPrePostMidTermWeekImpact(preEventWeek, postEventWeek):
                        if preEventWeek in pricesByWeek and postEventWeek in pricesByWeek:
                            preEventPrice = sum(pricesByWeek[preEventWeek]) / len(pricesByWeek[preEventWeek])
                            postEventPrice = sum(pricesByWeek[postEventWeek]) / len(pricesByWeek[postEventWeek])
                            prePostEventImpact = ((postEventPrice - preEventPrice) / preEventPrice) * 100
                            return f"Pre-Post Mid-term Weekly impact (buying {abs(preEventWeek)} weeks before and selling {abs(postEventWeek)} weeks after the event): {prePostEventImpact:.2f}%, "
                            
                    priceAnalysis += getPrePostMidTermWeekImpact(-2, 2) or ""
                    priceAnalysis += getPrePostMidTermWeekImpact(-3, 3) or ""
                    
                    # Calculate Pre-Post Mid-term Month Strategy
                    def getPrePostMidTermMonthImpact(preEventMonth, postEventMonth):
                        if preEventMonth in pricesByMonth and postEventMonth in pricesByMonth:
                            preEventPrice = sum(pricesByMonth[preEventMonth]) / len(pricesByMonth[preEventMonth])
                            postEventPrice = sum(pricesByMonth[postEventMonth]) / len(pricesByMonth[postEventMonth])
                            prePostEventImpact = ((postEventPrice - preEventPrice) / preEventPrice) * 100
                            return f"Pre-Post Mid-term Monthly impact (buying {abs(preEventMonth)} month(s) before and selling {abs(postEventMonth)} month(s) after the event): {prePostEventImpact:.2f}%, "
                    
                    priceAnalysis += getPrePostMidTermMonthImpact(-1, 1) or ""
                    priceAnalysis += getPrePostMidTermMonthImpact(-2, 2) or ""
                    
                    # Calculate long-term impact
                    for longTermMonth in range(2, 6):
                        if longTermMonth in pricesByMonth:
                            longTermChanges.append(sum(pricesByMonth[longTermMonth]) / len(pricesByMonth[longTermMonth]))
                    
                    if longTermChanges:
                        longTermAvgChange = sum(longTermChanges) / len(longTermChanges)
                        longTermImpact = ((longTermAvgChange - priceAtEventDate) / priceAtEventDate) * 100
                        priceAnalysis += f"Long-term impact (Buying on the event day and selling in 2-6 months after the event): {longTermImpact:.2f}%, "
                        
                    # Investment Insights
                    lastMonthChangePct, lastTwoWeeksChangePct, lastWeekChangePct = priceChangeRelativeToEventByMonth.get(-1), priceChangeRelativeToEventByWeek.get(-2), priceChangeRelativeToEventByWeek.get(-1)
                    last3DaysChangePct, lastDayChangePct, duringEventChangePct = priceChangeRelativeToEventByDay.get(-3), priceChangeRelativeToEventByDay.get(-1), priceChangeRelativeToEventByDay.get(0)
                    after1DayChangePct, after1WeekChangePct, after2WeeksChangePct = priceChangeRelativeToEventByDay.get(1), priceChangeRelativeToEventByWeek.get(1), priceChangeRelativeToEventByWeek.get(2)
                    after1MonthChangePct, after2MonthsChangePct, after3MonthsChangePct = priceChangeRelativeToEventByMonth.get(1), priceChangeRelativeToEventByMonth.get(2), priceChangeRelativeToEventByMonth.get(3)
                    
                    def investmentRecommendation(changePct):
                        if changePct >= 30:
                            return "The change is extremely positive, with a potential for very high returns. This is an excellent opportunity for a strong investment!"
                        elif changePct >= 10:
                            return "The change is strong, suggesting the potential for significant gains. A good opportunity for investors looking for strong returns."
                        elif changePct >= 5:
                            return "The change is moderate, but still a solid opportunity for investment with reasonable returns."
                        elif changePct >= 2:
                            return "There is a slight positive change, suggesting a modest opportunity for growth. If you're looking for safer investments, this may be a good option."

                        elif changePct <= -30:
                            return "The change is extremely negative, with a high potential for significant losses. It may be a high-risk investment, and caution is advised."
                        elif changePct <= -10:
                            return "The change is negative, indicating a high risk of losses. This may not be a good time to invest, as the potential for recovery seems low."
                        elif changePct <= -5:
                            return "The change is moderate negative, suggesting a potential for moderate losses. It may be a good idea to wait for a recovery or look for more stable investments."
                        elif changePct <= -2:
                            return "There is a slight negative change, suggesting modest losses. If you're looking for safer investments, it might be better to avoid this for now."

                        else:
                            return "The change is negligible or neutral, suggesting little to no opportunity for growth or loss. It may be best to monitor the situation for further developments."

                    def classifyChangeSize(changePct):
                        """
                        Classifies the size of the change into categories:
                        'very large', 'large', 'medium', 'small', 'very small'
                        for both positive and negative changes.
                        """
                        # Positive Change Classification
                        if changePct >= 30:
                            return "very large"
                        elif changePct >= 15:
                            return "large"
                        elif changePct >= 10:
                            return "medium"
                        elif changePct >= 8:
                            return "small-medium"
                        elif changePct >= 5:
                            return "small"
                        elif changePct > 0:
                            return "very small"  # For small positive changes
                        
                        # Negative Change Classification
                        elif changePct <= -30:
                            return "very large negative"
                        elif changePct <= -15:
                            return "large negative"
                        elif changePct <= -10:
                            return "medium negative"
                        elif changePct <= -8:
                            return "small-medium negative"
                        elif changePct <= -5:
                            return "small negative"
                        elif changePct <= -1:
                            return "very small negative"  # For small negative changes
                        elif changePct < 0:
                            return "extremely small negative"  # Slight negative change

                        # Zero case
                        else:
                            return "no change"

                    def analyzeInvestmentTrend(lastChangePct, futureChangePct, period):
                        """
                        Analyzes the change percentage over time to provide buy/sell recommendations.
                        Adds categories based on the size of the change.
                        """
                        # Classifying change sizes for both past and future
                        lastChangeSize = classifyChangeSize(lastChangePct)
                        futureChangeSize = classifyChangeSize(futureChangePct)

                        # If the previous change was positive and the forecast is positive
                        if lastChangePct > 5:
                            if futureChangePct > lastChangePct:
                                return f"The coin has been performing well over the past {period} with a {lastChangePct:.2f}% increase. The trend is expected to strengthen with a {futureChangePct:.2f}% increase. Consider holding or buying more, as the future growth is expected to be {futureChangeSize}."
                            elif futureChangePct < lastChangePct:
                                return f"The coin has been performing well, but the future growth might slow down. The forecast suggests a {futureChangePct:.2f}% increase, which is {futureChangeSize} compared to the previous {lastChangePct:.2f}%. Consider selling or taking profits if the price starts to drop."
                            elif futureChangePct == lastChangePct:
                                return f"The coin has been performing well with a {lastChangePct:.2f}% increase. The forecast suggests the trend will remain steady with a {futureChangePct:.2f}% change. Holding is a reasonable option for a steady gain."

                        # If the previous change was negative and the forecast is negative
                        elif lastChangePct < -5:
                            if futureChangePct < lastChangePct:
                                return f"The coin has been underperforming with a {abs(lastChangePct):.2f}% decrease. The negative trend is expected to continue with a {futureChangePct:.2f}% decrease, which is {futureChangeSize} negative. It may be better to avoid buying and wait for recovery."
                            elif futureChangePct > lastChangePct:
                                return f"The coin has been underperforming with a {abs(lastChangePct):.2f}% decrease, but the forecast suggests a potential recovery with a {futureChangePct:.2f}% increase. This is a {futureChangeSize} increase, indicating that recovery is possible. Monitor the price closely and consider buying if the trend improves."
                            elif futureChangePct == lastChangePct:
                                return f"The coin has been underperforming with a {abs(lastChangePct):.2f}% decrease. The forecast suggests the trend will remain steady with a {futureChangePct:.2f}% change. It's better to avoid significant moves until a clear trend emerges."

                        # If the previous change was between -5 and 0 (indicating a slight negative performance followed by improvement)
                        elif -5 < lastChangePct <= 0:
                            if futureChangePct > lastChangePct:
                                return f"The coin has had a slight negative change of {abs(lastChangePct):.2f}%. However, the forecast suggests a {futureChangePct:.2f}% positive increase, which is a significant improvement. This indicates a recovery trend. Consider buying or holding as the price seems to be improving."
                            elif futureChangePct == lastChangePct:
                                return f"The coin has had a slight negative change of {abs(lastChangePct):.2f}%. The forecast suggests the trend will stay the same with a {futureChangePct:.2f}% change. It's a neutral situation, consider holding until a clearer trend emerges."
                            elif futureChangePct < lastChangePct:
                                return f"The coin has had a slight negative change of {abs(lastChangePct):.2f}%. The forecast suggests the price may decline further with a {futureChangePct:.2f}% decrease. It may be better to avoid buying until recovery is more apparent."

                        # If the previous change was moderate or small
                        elif 0 < lastChangePct <= 5:
                            if futureChangePct > lastChangePct:
                                return f"The coin has had a small positive change of {lastChangePct:.2f}%. The forecast shows that the price will increase slightly further with a {futureChangePct:.2f}% rise. The future change is expected to be small, consider holding for a small but steady gain."
                            elif futureChangePct == lastChangePct:
                                return f"The coin has had a small positive change of {lastChangePct:.2f}%. The forecast suggests that the trend will stay the same with a {futureChangePct:.2f}% change. This is a good time to monitor and hold, but avoid taking major risks."
                            elif futureChangePct < lastChangePct:
                                return f"The coin has had a small positive change of {lastChangePct:.2f}%. However, the future change is predicted to be a small decline. Consider selling and taking profits if the price begins to drop."

                        # For small or no changes
                        return f"The performance is neutral or minor with a {lastChangePct:.2f}% change. The forecast suggests the trend will be {futureChangeSize}. Keep monitoring the price movement closely to make an informed decision."

                    def generateInvestmentInsights():
                        investmentInsights = ""

                        # 1 Month Before the Event
                        if lastMonthChangePct:
                            investmentInsights += f"Change in the last month: {lastMonthChangePct:.2f}% - {investmentRecommendation(lastMonthChangePct)} "
                            if after1WeekChangePct:
                                investmentInsights += f"Forecasted change in 1 week after the event: {after1WeekChangePct:.2f}% - {investmentRecommendation(after1WeekChangePct)} "
                            if after2WeeksChangePct:
                                investmentInsights += f"Forecasted change in 2 weeks after the event: {after2WeeksChangePct:.2f}% - {investmentRecommendation(after2WeeksChangePct)} "
                            
                            investmentInsights += analyzeInvestmentTrend(lastMonthChangePct, after1WeekChangePct, "month")

                        # 2 Weeks Before the Event
                        if lastTwoWeeksChangePct:
                            investmentInsights += f"Change in the last 2 weeks: {lastTwoWeeksChangePct:.2f}% - {investmentRecommendation(lastTwoWeeksChangePct)} "
                            if after1WeekChangePct:
                                investmentInsights += f"Forecasted change in 1 week after the event: {after1WeekChangePct:.2f}% - {investmentRecommendation(after1WeekChangePct)} "
                            if after2WeeksChangePct:
                                investmentInsights += f"Forecasted change in 2 weeks after the event: {after2WeeksChangePct:.2f}% - {investmentRecommendation(after2WeeksChangePct)} "
                            
                            investmentInsights += analyzeInvestmentTrend(lastTwoWeeksChangePct, after1WeekChangePct, "week")

                        # 1 Week Before the Event
                        if lastWeekChangePct:
                            investmentInsights += f"Change in the last week: {lastWeekChangePct:.2f}% - {investmentRecommendation(lastWeekChangePct)} "
                            # Analyze 1 week after the event based on this
                            if after1WeekChangePct:
                                investmentInsights += f"Forecasted change in 1 week after the event: {after1WeekChangePct:.2f}% - {investmentRecommendation(after1WeekChangePct)} "
                            # Detailed suggestion based on trend continuation
                            investmentInsights += analyzeInvestmentTrend(lastWeekChangePct, after1WeekChangePct, "week")

                        # 3 Days and 1 Day Before the Event
                        if last3DaysChangePct:
                            investmentInsights += f"Change in the last 3 days: {last3DaysChangePct:.2f}% - {investmentRecommendation(last3DaysChangePct)} "
                        if lastDayChangePct:
                            investmentInsights += f"Change in the last day: {lastDayChangePct:.2f}% - {investmentRecommendation(lastDayChangePct)} "
                            # Analyze 24-hour change and event performance
                            if duringEventChangePct:
                                investmentInsights += f"Forecasted change during the event day: {duringEventChangePct:.2f}% - {investmentRecommendation(duringEventChangePct)} "
                                if duringEventChangePct < 5:
                                    investmentInsights += "Performance may peak during the event, consider selling during the event or right after if the price drops."

                        # After Event - 1 Day, 1 Week, 2 Weeks, 1 Month
                        if after1DayChangePct:
                            investmentInsights += f"Forecasted change 1 day after the event: {after1DayChangePct:.2f}% - {investmentRecommendation(after1DayChangePct)} "
                        if after1WeekChangePct:
                            investmentInsights += f"Forecasted change 1 week after the event: {after1WeekChangePct:.2f}% - {investmentRecommendation(after1WeekChangePct)} "
                        if after2WeeksChangePct:
                            investmentInsights += f"Forecasted change 2 weeks after the event: {after2WeeksChangePct:.2f}% - {investmentRecommendation(after2WeeksChangePct)} "
                        if after1MonthChangePct:
                            investmentInsights += f"Forecasted change 1 month after the event: {after1MonthChangePct:.2f}% - {investmentRecommendation(after1MonthChangePct)} "

                        return investmentInsights
                    
                    """
                    investmentInsights = generateInvestmentInsights()
                    if investmentInsights:
                        priceAnalysis += f"Investment Insights: {investmentInsights}"
                    """
                    
                    if priceAnalysis:
                        coinsPriceChangesRelativeToEvent += f"Forecasted prices for {coin}: {priceAnalysis.strip(", ")}"

        # TODO: remove this
        print(coinsPriceChangesRelativeToEvent)
        
        return coinsPriceChangesRelativeToEvent
    
    @staticmethod
    def CreateEvents(entries: list[dict[str, Any]], outputPath: str) -> pd.DataFrame:
        if not entries:
            print("No entries to create dataset!")
            return
        
        df: pd.DataFrame = pd.DataFrame([asdict(entry) for entry in entries])
        df.to_json(outputPath, orient='records', lines=True, force_ascii=True)
        print(f"Dataset created at {outputPath} as JSON format with {len(entries)} entries!")
        
        if not Constants.SCRAP_MODE:
            event_entries_dataset = load_dataset('json', data_files=outputPath, split='train')
            return event_entries_dataset

    @staticmethod
    def ConcatAll():
        files = [f for f in os.listdir(Constants.SCRAP_OUTPUTS_PATH) if f.endswith(".json")]
        if not files:
            print("No files to concatenate!")
            return
        
        currentPage, processedPages, chunkSize = Globals.scrapData["ConcatCurrentPage"], 0, 100
        concatenated_df = pd.DataFrame()
        
        files = sorted(
            [f for f in os.listdir(Constants.SCRAP_OUTPUTS_PATH) 
            if os.path.isfile(os.path.join(Constants.SCRAP_OUTPUTS_PATH, f))],
            key = lambda x: int(x.split("_")[0])
        )
        
        for file in files:
            if file.endswith(".json") and int(file.split("_")[0]) >= currentPage:
                file_path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, file)
                df = pd.read_json(file_path, orient='records', lines=True)
                concatenated_df = pd.concat([concatenated_df, df])
                
                print(f"Concatenated {file}!")
                
                processedPages += 1
                Globals.scrapData["ConcatCurrentPage"] += 1
                DataUtils.SaveScrapData()
                
                if processedPages >= chunkSize:
                    break
        
        concatenatedFileName = f"{currentPage}-{currentPage + chunkSize - 1}.json"
        concatenated_df.to_json(os.path.join(Constants.SCRAP_OUTPUTS_PATH, concatenatedFileName), orient='records', lines=True, force_ascii=True)
        print(f"Concatenated {len(files)} files into {concatenatedFileName}!")
        
    @staticmethod
    def ConvertAllToConversationalStyle():
        currentPage, pagesToProcess = Globals.scrapData["ConversationalStyleCurrentPage"], Globals.scrapData["ConversationalStylePagesToProcess"]
        processedPages = 0
        files = sorted(
            [f for f in os.listdir(Constants.SCRAP_OUTPUTS_PATH) 
            if os.path.isfile(os.path.join(Constants.SCRAP_OUTPUTS_PATH, f))],
            key = lambda x: int(x.split("_")[0])
        )
        
        outputDatasetPath = os.path.join(Constants.SCRAP_OUTPUTS_PATH, "conversational-style", "past-events.jsonl")
        for file in files:
            if file.endswith(".json") and int(file.split("_")[0]) >= currentPage:
                path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, file)
                output_path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, "conversational-style", file)
                
                DatasetHelper.NormalizeJSON(path)
                dataset = load_dataset('json', data_files=path, split='train')
                df = dataset.to_pandas()
                
                rows, knowledgeTableRows = [], []
                for _, row in df.iterrows():
                    row = DatasetHelper.ToConversationalStyle(row)
                    if not row:
                        continue
                    
                    rows.append(row)
                    knowledgeTableRows.append({
                        "title": row["conversations"][0]["value"], # user
                        "text": row["conversations"][1]["value"] # assistant
                    })

                conversational_df = pd.DataFrame(rows)
                knowledgeTable_df = pd.DataFrame(knowledgeTableRows)
                #knowledgeTable_df.to_csv(output_path.replace(".json", ".csv"), index=False, quotechar='"')    
                
                conversationalData = conversational_df.to_dict(orient='records')
                
                """outputCurrentData = []
                if os.path.exists(outputDatasetPath):
                    with open(outputDatasetPath, 'r') as f:
                        outputCurrentData = json.load(f)
                    
                outputCurrentData.extend(conversationalData) 
                with open(outputDatasetPath, 'w', encoding='utf-8') as f:
                    json.dump(outputCurrentData, f, ensure_ascii=True, indent=4)"""
                
                # Writing into jsonl format
                with open(outputDatasetPath, 'a', encoding='utf-8') as f:
                    for entry in conversationalData:
                        json.dump(entry, f, ensure_ascii=False)
                        f.write('\n')
                    
                print(f"Converted dataset {file} to conversational style!")
                
                processedPages += 1
                Globals.scrapData["ConversationalStyleCurrentPage"] += 1
                DataUtils.SaveScrapData()
                
                if processedPages >= pagesToProcess:
                    break
                
    @staticmethod
    def NormalizeJSON(inputPath):
        with open(inputPath, 'r') as infile:
            lines = infile.readlines()
        
        normalizedLines = []
        for line in lines:
            data = json.loads(line)
            
            if 'coinsPricesByDate' in data and data['coinsPricesByDate']:
                for coin, dates in data['coinsPricesByDate'].items():
                    if dates is None:
                        continue
                    
                    for date, price in dates.items():
                        if isinstance(price, (int, float)):
                            dates[date] = [price]
            
            normalizedLines.append(json.dumps(data))
        
        with open(inputPath, 'w') as outfile:
            outfile.write('\n'.join(normalizedLines) + '\n')
        
    @staticmethod
    def UpdateAllEventsValidation():
        for file in os.listdir(Constants.SCRAP_OUTPUTS_PATH):
            if file.endswith(".json"):
                path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, file)
                dataset = load_dataset('json', data_files=path, split='train')
                df = dataset.to_pandas()
                df = pd.merge(df, Globals.eventValidations, on='id', how='left', suffixes=("_x", "_y"))
                df.drop(df.filter(regex='_x$').columns.tolist(), axis=1, inplace=True)
                df.rename(columns=lambda col: col.replace('_y', ''), inplace=True)
                df.to_json(path, orient='records', lines=True, force_ascii=True)

                print(f"Updated {file} with event validations!")
                
    @staticmethod
    def UpdateAllEventsCoinData():
        currentPage, pagesToProcess = Globals.scrapData["CoinUpdateCurrentPage"], Globals.scrapData["CoinUpdatePagesToProcess"]
        processedPages = 0
        files = sorted(
            [f for f in os.listdir(Constants.SCRAP_OUTPUTS_PATH) 
            if os.path.isfile(os.path.join(Constants.SCRAP_OUTPUTS_PATH, f))],
            key = lambda x: int(x.split("_")[0])
        )
        
        for file in files:
            if file.endswith(".json") and int(file.split("_")[0]) >= currentPage:
                path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, file)
                DatasetHelper.NormalizeJSON(path)
                dataset = load_dataset('json', data_files=path, split='train')
                df = dataset.to_pandas()
                
                # Remove "or earlier" or "(or earlier)" from the date column
                df['date'] = df['date'].str.replace(r"\(or earlier\)|or earlier", "", regex=True).str.strip()
                
                df.drop(columns=['coinChangesByDay', 'coinChangesByHour'], inplace=True, errors='ignore')
                
                for _, row in df.iterrows():
                    if row.get("coinsPricesByDate"):
                        continue
                    
                    date: str = DateUtils.GetCorrectFormattedDate(row['date'])
                    dateType = DateUtils.GetDateType(row['date'])[0]
                
                    if dateType == DateType.RANGE:
                        start_date = datetime.strptime(date[0], Constants.UTC_FORMAT)
                        end_date = datetime.strptime(date[1], Constants.UTC_FORMAT)
                        date_diff = (end_date - start_date).days
                        
                        intervals = Constants.EVENT_DATE_INTERVALS[DateType.RANGE]["short" if date_diff <= 30 else "long"]
                        base_date = start_date
                    else:
                        base_date = datetime.strptime(date, Constants.UTC_FORMAT)
                        intervals = Constants.EVENT_DATE_INTERVALS[dateType]
                    
                    coinsPricesByDate: dict[str, dict[str, float | list[float]]] = defaultdict(dict)
                    for coin in row["coins"]:
                        coinSymbolGroup = re.findall(r"\(([^)]+)\)", coin)
                        coinSymbol: str = coinSymbolGroup and coinSymbolGroup[-1] or coin
                        if not coinSymbol.endswith("USDT"):
                            coinSymbol += "USDT"
                            
                        coinSymbol = coinSymbol.replace("$", "")
                            
                        coinPricesByDate = coinsPricesByDate[coinSymbol]
                        for interval in intervals:
                            coinDate: str = DateUtils.CalculateDateFromInterval(base_date, interval)
                            if coinDate is None:
                                print(f"Failed to calculate date for {interval} interval.")
                                continue
                            
                            coinInterval = "1d"
                            
                            # Check if interval is d or in bxd or axd format where x is less than 7
                            if interval == 'd' or (interval[0] in ['a', 'b'] and interval[2] == "d" and int(interval[1]) < 7):
                                coinInterval = "1h"
                            
                            maxRetries, retries, shouldStopForCoin = 3, 0, False
                            while retries < maxRetries:
                                try:
                                    start_date = datetime.strptime(coinDate, Constants.UTC_FORMAT)
                                    start_date = start_date.replace(hour = 0, minute = 0, second = 0, microsecond = 0, tzinfo = timezone.utc)
                                    
                                    end_date = start_date + timedelta(hours = 23, minutes = 59)
                                    historicalData: pd.DataFrame = CoinUtils.GetHistoricalData(coinSymbol, coinInterval, start_date.timestamp() * 1000, end_date.timestamp() * 1000)
                                    coinPricesByDate[coinDate] = CoinUtils.GetAvgHistoricalData(historicalData)
                                    
                                    break
                                except BinanceAPIException as e:
                                    if e.code == -1121:
                                        print(f"Error: {e.message}. No exchange found for coin: {coinSymbol}")
                                        shouldStopForCoin = True
                                        break
                                    
                                    if e.status_code == 429: 
                                        print("Rate limit exceeded. Retrying after 1 minute...")
                                        time.sleep(60)
                                    
                                    print(f"Failed to get historical data for {coinSymbol} at {coinDate} with interval {coinInterval}. Error code: {e.code}. Message: {e.message}")
                                except Exception as e:
                                    print(f"Unexpected error for {coinSymbol} at {coinDate} {interval}. Error: {e}")
                                    
                                finally:
                                    retries += 1
                                
                            if shouldStopForCoin:
                                break 
                     
                    df.loc[df['id'] == row['id'], 'coinsPricesByDate'] = [dict(coinsPricesByDate)]
                    print(f"For {row['id']}: Date type: {dateType}, Event date {date}, Intervals {intervals} to be scrapped, Prices by date {coinsPricesByDate}")
                
                    # Save the updated dataset
                    df.to_json(path, orient='records', lines=True, force_ascii=True)
                      
                processedPages += 1
                Globals.scrapData["CoinUpdateCurrentPage"] += 1
                DataUtils.SaveScrapData()
                
                if processedPages >= pagesToProcess:
                    break
    
    @staticmethod
    def UpdateCoinsHistoricalData(coinNewHistoricalDataByInterval: dict[str, dict[str, pd.DataFrame]]):
        for interval, coinHistoricalData in coinNewHistoricalDataByInterval.items():
            for symbol, df in coinHistoricalData.items():
                folderName = interval[::-1].upper()
                dataframePath = f'data/coin-historical-data/{folderName}/{symbol}USDT_{folderName}.csv'
                current_df = pd.read_csv(dataframePath, sep=',')
                current_df = pd.concat([current_df, df])
                current_df.drop_duplicates(subset=['datetime'], keep='last', inplace=True)
                current_df.to_csv(dataframePath, sep=',', mode='a', index=False)
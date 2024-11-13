from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import ccxt
from datasets import load_dataset
from dataclasses import asdict
from typing import Any

from binance.exceptions import BinanceAPIException
import pandas as pd, os, re
import time

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
                f"Analyze the following cryptocurrency event: "
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
        
        priceAnalysis = ""
        coinPricesByDate = row.get("coinsPricesByDate")
        if coinPricesByDate:
            for coin, allPrices in coinPricesByDate.items():
                if allPrices:
                    priceAnalysis += f"Historical and forecasted price data for {coin}: "
                    for date, datePrices in allPrices.items():
                        datePrices = datePrices.tolist()
                        if isinstance(datePrices, list) and len(datePrices) > 1:
                            price_points = f"{date} (per hour): ${', '.join(map(str, datePrices))}"
                        else:
                            price_points = f"{date}: ${datePrices[0]}"
                        
                        priceAnalysis += price_points + "; "

        aiAnalysis = row.get("aiAnalysis") and f"Analysis: {row['aiAnalysis']}, " or ""
        
        if not aiAnalysis and not priceAnalysis:
            return None
        
        conversations.append({
            "role": "assistant",
            "value": (
                f"{aiAnalysis}"
                f"{priceAnalysis}"
            ).strip().replace(r'\/', '/')
        })

        data = {
            "conversations": conversations,
            "image_path": row['proofImage'],
            "source_link": row['sourceHref']
        }
        
        return data
    
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
                knowledgeTable_df.to_csv(output_path.replace(".json", ".csv"), index=False, quotechar='"')    
                
                conversational_list = conversational_df.to_dict(orient='records')
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(conversational_list, f, ensure_ascii=True, indent=4)
                    
                print(f"Converted dataset {file} to conversational style!")
                
                processedPages += 1
                Globals.scrapData["ConversationalStyleCurrentPage"] += 1
                #DataUtils.SaveScrapData()
                
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
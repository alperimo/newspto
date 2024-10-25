from datasets import load_dataset
from dataclasses import asdict
from typing import Any

import pandas as pd, os

import Constants, DataUtils, Globals

class DatasetHelper:
    @staticmethod
    def ToConversationalStyle(dataset: pd.DataFrame) -> pd.DataFrame:
        # TODO
        pass
    
    @staticmethod
    def CreateEvents(entries: list[dict[str, Any]], outputPath: str) -> pd.DataFrame:
        if len(entries) == 0:
            print("No entries to create dataset!")
            return None
        
        df: pd.DataFrame = pd.DataFrame([asdict(entry) for entry in entries])
        df.to_json(outputPath, orient='records', lines=True, force_ascii=True)
        print(f"Dataset created at {outputPath} as JSON format with {len(entries)} entries!")
        
        if not Constants.SCRAP_MODE:
            event_entries_dataset = load_dataset('json', data_files=outputPath, split='train')
            return event_entries_dataset
        
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
    def UpdateAllEventsCoinData(events: pd.DataFrame) -> pd.DataFrame:
        currentPage = Globals.scrapData["CoinUpdateCurrentPage"]
        pagesToProcess = Globals.scrapData["CoinUpdatePagesToProcess"]
        processedPages = 0
        for file in os.listdir(Constants.SCRAP_OUTPUTS_PATH):
            if file.endswith(".json") and int(file.split("_")[0]) >= currentPage:
                path = os.path.join(Constants.SCRAP_OUTPUTS_PATH, file)
                dataset = load_dataset('json', data_files=path, split='train')
                df = dataset.to_pandas()
                
                # Remove "or earlier" or "(or earlier)" from the date column
                df['date'] = df['date'].str.replace(r"\(or earlier\)|or earlier", "", regex=True).str.strip()
                
                """
                    31 Mar 2024 | 31 Mar 2024 or earlier | 31 Mar 2024 (or earlier)
                        b1m: int
                        b2w: int
                        b1w: int
                        b3d: list[int], b2d: list[int], b1d: list[int], 
                        d: list[int], 
                        a1d: list[int], a2d: list[int], a3d: list[int]
                        a4d: list[int], a5d: list[int], a7d: list[int], 
                        a10d: list[int], a14d: list[int],
                        a21d: list[int], a30d: list[int]
                        
                    Mar 2024:
                        b1m: int
                        b2w: int
                        b1w: int
                        b3d: list[int], b2d: list[int], b1d: list[int],
                        m1: list[int], m2: list[int], m3: list[int], m7: list[int],
                        m10: list[int], m14: list[int], m21: list[int], m30: list[int]
                        a1d: list[int], a2d: list[int], a3d: list[int]
                        a7d: list[int], a10d: list[int], a14d: list[int],
                        a21d: list[int], a30d: list[int]
                        a35d: list[int], a40d: list[int], a45d: list[int],
                        a60d: list[int]
                        
                    From 29 Dec to 31 Mar 2024:
                        if less than 1 month:
                            b1m from start: int
                            b2w from start: int
                            b1w from start: int
                            b3d from start: list[int], b2d from start: list[int], b1d from start: list[int],
                            d from start: list[int],
                            a1d from start: list[int], a2d from start: list[int], a3d from start: list[int]
                            a7d from start: list[int], a10d from start: list[int], a14d from start: list[int],
                            a21d from start: list[int], a30d from start: list[int]
                            
                        otherwise:
                            b1m from start: int
                            b2w from start: int
                            b1w from start: int
                            b3d from start: list[int], b2d from start: list[int], b1d from start: list[int],
                            d from start: list[int],
                            a1d from start: list[int], a2d from start: list[int], a3d from start: list[int]
                            a7d from start: list[int], a10d from start: list[int], a14d from start: list[int],
                            a21d from start: list[int], 
                            a30d from start: list[int]
                            a40d from start: int
                            a45d from start: int
                            a50d from start: int
                            a60d from start: int
                            a65d from start: int
                            a70d from start: int
                            a80d from start: int
                            a90d from start: int
                            a100d from start: int
                            a120d from start: int
                            
                    Q1 yyyy | Q2 yyyy | Q3 yyyy | Q4 yyyy
                        - find the start and end dates for the quarter (Q1: Jan-Mar, Q2: Apr-Jun, Q3: Jul-Sep, Q4: Oct-Dec)
                        - apply the same logic as the previous example for the date range
                            extra:
                            - a135d from start: int, a150d from start: int, a165d from start: int, a180d from start: int
                """
                
                processedPages += 1
                if processedPages > pagesToProcess:
                    break
          
        DataUtils.SaveScrapData()
    
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
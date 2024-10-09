from datasets import load_dataset
from dataclasses import asdict
from typing import Any

import pandas as pd, os

import Constants, Globals

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
            if file.startswith("1"):
                continue
            
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
    def UpdateEventsCoinData(events: pd.DataFrame) -> pd.DataFrame:
        # TODO
        pass
    
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
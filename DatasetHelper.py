from datasets import load_dataset
from dataclasses import asdict
from typing import Any

import pandas as pd

import Constants

class DatasetHelper:
    @staticmethod
    def ToConversationalStyle(dataset: pd.DataFrame) -> pd.DataFrame:
        # TODO
        pass
    
    @staticmethod
    def CreateEventEntriesDataset(entries: list[dict[str, Any]], outputPath: str) -> pd.DataFrame:
        if len(entries) == 0:
            print("No entries to create dataset!")
            return None
        
        df: pd.DataFrame = pd.DataFrame([asdict(entry) for entry in entries])
        df.to_json(outputPath, orient='records', lines=True, force_ascii=True)
        print(f"Dataset created at {outputPath} as JSON format with {len(entries)} entries!")
        
        if not Constants.SCRAP_MODE:
            event_entries_dataset = load_dataset('json', data_files=outputPath, split='train')
            return event_entries_dataset
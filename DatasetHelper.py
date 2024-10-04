from datasets import load_dataset
from dataclasses import asdict
from typing import Any

import pandas as pd

class DatasetHelper:
    @staticmethod
    def ToConversationalStyle(dataset: pd.DataFrame) -> pd.DataFrame:
        # TODO
        pass
    
    @staticmethod
    def CreateEventEntriesDataset(entries: list[dict[str, Any]], outputPath: str):
        if len(entries) == 0:
            print("No entries to create dataset!")
            return None
        
        df: pd.DataFrame = pd.DataFrame([asdict(entry) for entry in entries])
        df.to_json(outputPath, orient='records', lines=True)
        print(f"Dataset created at {outputPath} as JSON format with {len(entries)} entries!")
        event_entries_dataset = load_dataset('json', data_files=outputPath, split='train')
        print(event_entries_dataset)
        return event_entries_dataset
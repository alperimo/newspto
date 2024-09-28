from datasets import load_dataset
from typing import Any

import pandas as pd

DATASET_PATH = 'data/coin-news.json'

class DatasetHelper:
    @staticmethod
    def CreateEventEntriesDataset(entries: list[dict[str, Any]]):
        df: pd.DataFrame = pd.DataFrame.from_records(entries)
        df.to_json(DATASET_PATH, orient='records', lines=True)
        print(f"Dataset created at {DATASET_PATH} as JSON format with {len(entries)} entries!")
        event_entries_dataset = load_dataset('json', data_files=DATASET_PATH, split='train')
        return event_entries_dataset
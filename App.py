from Finetuner import Finetuner
from DatasetHelper import DatasetHelper
from Scrap import Scrap

CMC_DATASET_PATH = 'data/cmc_coin_pastevents.json'

if __name__ == '__main__':
    scrap = Scrap()
    events = scrap.RetrieveEvents()
    dataset = DatasetHelper.CreateEventEntriesDataset(events, CMC_DATASET_PATH)
    fineTuner = Finetuner(dataset)
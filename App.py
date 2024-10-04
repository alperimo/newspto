#from Finetuner import Finetuner
from DatasetHelper import DatasetHelper
from Scrap import Scrap

import datetime

CMC_DATASET_PATH = 'data/{}_cmc_coin_pastevents.json'

def main():
    scrap = Scrap()
    events = scrap.RetrieveEvents(dateRange="02/10/2022 - 02/10/2023")
    if events is None:
        print("Failed to retrieve events.")
        return
        
    dataset = DatasetHelper.CreateEventEntriesDataset(events, CMC_DATASET_PATH.format(datetime.datetime.now().strftime("%d%m%Y_%H%M")))
    #fineTuner = Finetuner(dataset)

if __name__ == '__main__':
    main()
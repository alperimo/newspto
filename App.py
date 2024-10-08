#from Finetuner import Finetuner
from DatasetHelper import DatasetHelper
from Scrap import Scrap

import datetime

import Constants, Globals, DataUtils

def main():
    DataUtils.Load()
    scrap = Scrap()
    
    currentPage: int = int(Globals.scrapData["CurrentPage"])
    dateRange: str = Globals.scrapData["DateRange"]
    scrapedPageCount: int = 0
    triesOnFail: int = 0
    while scrapedPageCount < Globals.scrapData["PagesToScrape"]:
        events = scrap.RetrieveEvents(dateRange = dateRange, coins = [""], page = currentPage)
        if events is None:
            print(f"Failed to retrieve events for the page {currentPage} between the dates {dateRange}.")
            break
            
        dataset = DatasetHelper.CreateEventEntriesDataset(events, Constants.CMC_DATASET_PATH.format(currentPage, datetime.datetime.now().strftime("%d%m%Y_%H%M")))

        scrapedPageCount += 1
        currentPage += 1
        
        Globals.scrapData["CurrentPage"] = currentPage
        DataUtils.SaveScrapData()
    
    #fineTuner = Finetuner(dataset)

if __name__ == '__main__':
    main()
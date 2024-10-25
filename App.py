from datasets import load_dataset
from dataclasses import asdict

#from Finetuner import Finetuner
from DatasetHelper import DatasetHelper
from Scrap import Scrap

import datetime
import Constants, Globals, DataUtils, DateUtils
import CoinUtils

def ScrapEvents():
    scrap = Scrap()
    
    currentPage: int = int(Globals.scrapData["CurrentPage"])
    dateRange: str = Globals.scrapData["DateRange"]
    scrapedPageCount: int = 0
    
    while scrapedPageCount < Globals.scrapData["PagesToScrape"]:
        events = scrap.RetrieveEvents(dateRange = dateRange, coins = [""], page = currentPage)
        if events is None:
            print(f"Failed to retrieve events for the page {currentPage} between the dates {dateRange}.")
            break
        
        dataset = DatasetHelper.CreateEvents(events, Constants.CMC_DATASET_PATH.format(currentPage, datetime.datetime.now().strftime("%d%m%Y_%H%M")))

        scrapedPageCount += 1
        currentPage += 1
        
        Globals.scrapData["CurrentPage"] = currentPage
        DataUtils.SaveScrapData()

def main():
    DataUtils.Load()
    #ScrapEvents()
    
    #test = CoinUtils.GetHistoricalData("BTCUSDT", "1h", "2024-10-14")
    
    #DatasetHelper.UpdateAllEventsCoinData()
    #DatasetHelper.UpdateCoinsHistoricalData(Globals.coinHistoricalDataByInterval)
    
    #fineTuner = Finetuner(dataset)

if __name__ == '__main__':
    main()
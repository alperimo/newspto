from datasets import load_dataset

import json, os
import Constants, Globals

@staticmethod
def LoadEventValidations():
    filePath = f"{Constants.DATA_PATH}/EventValidations.json"
    if not os.path.exists(filePath):
        return
    
    Globals.eventValidations = load_dataset('json', data_files=filePath, split='train').to_pandas()

@staticmethod
def LoadTopCoinNames():
    with open(f"{Constants.DATA_PATH}/TopCoinNames.json", encoding="utf-8") as f:
        Globals.topCoinNameBySymbol = json.load(f)
        
    Globals.topCoinNameBySymbol = {k: v for k, v in Globals.topCoinNameBySymbol.items() if v}

@staticmethod
def LoadScrapData():
    with open(f"{Constants.DATA_PATH}/ScrapData.json", encoding="utf-8") as f:
        Globals.scrapData = json.load(f)

@staticmethod
def Load():
    LoadTopCoinNames()
    LoadScrapData()
    
@staticmethod
def SaveScrapData():
    with open(f"{Constants.DATA_PATH}/ScrapData.json", 'w', encoding="utf-8") as f:
        json.dump(Globals.scrapData, f, indent=4)
import json
import Constants, Globals

@staticmethod
def LoadTopCoinNames():
    with open(f"{Constants.DATA_PATH}/TopCoinNames.json", encoding="utf-8") as f:
        Globals.topCoinNameBySymbol = json.load(f)
        
    Globals.topCoinNameBySymbol = {k: v for k, v in Globals.topCoinNameBySymbol.items() if v}
    
    print(f"Loaded {len(Globals.topCoinNameBySymbol)} top coin names.")

@staticmethod
def Load():
    LoadTopCoinNames()
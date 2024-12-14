from Enums import DateType

DATA_PATH = "data"
SCRAP_OUTPUTS_PATH = "data/scrap-outputs"
UPCOMING_EVENTS_PATH = SCRAP_OUTPUTS_PATH + '/upcoming-events'
CMC_DATASET_PATH = SCRAP_OUTPUTS_PATH + '/{}_{}_cmc_coin_pastevents.json'
CMC_DATASET_UPCOMING_PATH = UPCOMING_EVENTS_PATH + '/cmc_coin_upcomingevents.json'

EVENT_DATE_INTERVALS = {
    DateType.EXACT: ['b1m', 'b2w', 'b1w', 'b3d', 'b2d', 'b1d', 'd', 'a1d', 'a2d', 'a3d', 'a4d', 
                     'a5d', 'a7d', 'a10d', 'a14d', 'a21d', 'a30d'],
    
    DateType.MONTH: ['b1m', 'b2w', 'b1w', 'b3d', 'b2d', 'b1d', 'm1', 'm2', 'm3', 'm7', 'm10', 
                     'm14', 'm21', 'm30', 'a1d', 'a2d', 'a3d', 'a7d', 'a10d', 'a14d', 'a21d', 
                     'a30d', 'a35d', 'a40d', 'a45d', 'a60d'],
    
    DateType.RANGE: {
        "short": ['b1m', 'b2w', 'b1w', 'b3d', 'b2d', 'b1d', 'd', 'a1d', 'a2d', 'a3d', 'a7d', 
                  'a10d', 'a14d', 'a21d', 'a30d'],
        
        "long": ['b1m', 'b2w', 'b1w', 'b3d', 'b2d', 'b1d', 'd', 'a1d', 'a2d', 'a3d', 'a7d', 
                 'a10d', 'a14d', 'a21d', 'a30d', 'a40d', 'a45d', 'a50d', 'a60d', 'a65d', 
                 'a70d', 'a80d', 'a90d', 'a100d', 'a120d']
    },
    
    DateType.QUARTER: ['b1m', 'b2w', 'b1w', 'b3d', 'b2d', 'b1d', 'd', 'a1d', 'a2d', 'a3d', 'a7d', 
                       'a10d', 'a14d', 'a21d', 'a30d', 'a40d', 'a45d', 'a50d', 'a60d', 'a65d', 
                       'a70d', 'a80d', 'a90d', 'a100d', 'a120d', 'a135d', 'a150d', 'a165d', 'a180d']
}

SCRAP_DATE_RANGE = {"From": "25/11/2017", "To": "01/01/2024", "Interval": "1m"}
SCRAP_MODE = True

UTC_FORMAT = "%Y-%m-%d"

BNC_API_KEY = ""
BNC_API_SECRET_KEY = ""
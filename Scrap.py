from typing import Any
from bs4 import BeautifulSoup
from bs4.element import PageElement, ResultSet

from Dataclasses import CMCEvent, CMCEventValidation

import datetime, os, re, requests

import Constants

class Scrap:
    def __init__(self):
        self.baseUrl = 'https://coinmarketcal.com'
        self.headers = {
            'Authority': 'coinmarketcal.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Cookie': '_ga=GA1.1.786695681.1726145331; device_view=full; cf_clearance=KEwPVYlyKH2eHHQzB53vyTZxM4zFPGGTN4ZUVHp8rdw-1734169922-1.2.1.1-CASaC.c1AULJkev8IkkCo8wPjJsbE7dzJbmAXRh186cOZOLJrYNRR7phiSsjCEJTYgth5AJ_cwletHwBLGIExJ2lGPDOEDA58ScfzzKZk9s2_I35lH19npabU.w8m33tPiq.WwU_Z8AEB_R.zB6jh.NcF1sssZum.kyj1MQTr35vfW241drSGH4e3q_l74OnBhTNdYYnQsSWvJCl7onIZLU4FnaK8gZEPoef_t63yYrOkaDbqCrqCDyAGof92ilh8k1Z5MKlgJlyBp.cmcpI.58Vak2iKxQuJKoW8FITOu1MJxCwrD6bXqor21y8UYoG3KuwbZR7MAiANkGwqAUtaNSQcY4KP_MV7mjnYDSSlHUTv3uzF73nq4tJ1zwpYwJNbC6qlosQPaWn04wl52lsiI2bbN7HPUVKesxsiDW..t2WyJQoUmwRzaguQvCWw3RE; PHPSESSID=eup0v6efcm3k80n4iri4offvo3; AWSALB=UBDTZs7XMQvHGAsaLRhz8311ARw1vAlzhumSkEX6bOLAtj50Qf2wp3k6yrgTxIIxS8nilN3rureuPHiLv4U6OVMG4epWBA9ORyEb/tjnuyohFe0E2lEMn/uBTRnt; _ga_90JJS7QB1F=GS1.1.1734169922.66.1.1734169927.0.0.0'
        }
        
        self.imagesPath = Constants.SCRAP_OUTPUTS_PATH + '/images'
        
    def RetrieveEvents(self, route: str = "en/pastevents", dateRange: str = "", coins: list[str] = [""], page: int = 1) -> list[CMCEvent]:
        print(f"Retrieving events for the page {page} between the dates {dateRange}.")
        
        params = {
            'form[date_range]': dateRange,
            'form[keyword]': '',
            'form[coin][]': coins,
            'form[sort_by]': '',
            'form[submit]': '',
            'form[show_reset]': '',
            'page': page
        }
        
        response = requests.get(f"{self.baseUrl}/{route}", headers = self.headers, params = params)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            event_entries: ResultSet[PageElement] = soup.find_all('article', class_='col-xl-3 col-lg-4 col-md-6 py-3')    
            entries: list[CMCEvent] = []
            
            for index, event in enumerate(event_entries, start=1):
                eventBody = event.find_next('div', class_="card__body")
                
                """if coin := eventBody.find_next('h5', class_="card__coins"):
                    coin = coin.find('a').get_text(strip=True)"""
                
                if date := eventBody.find_next('h5', class_="card__date mt-0"):
                    date = date.get_text(strip=True)
                    
                if title := eventBody.find_next('span', class_="card__text text-truncate text-nowrap mr-1"):
                    title = title.get_text(strip=True)
                    
                if description := eventBody.find_next('p', class_="card__description"):
                    description = description.get_text(strip=True)
                
                eventId, category, coins, coinChangeDollars, coinChangePercents, sourceHref, aiAnalysis, validation, addedDate, updatedDate = self.RetrieveEventDetails(page, eventBody)
                
                entries.append(CMCEvent(
                    id = eventId,
                    category = category,
                    coins = coins,
                    date = date,
                    addedDate = addedDate,
                    updatedDate = updatedDate,
                    title = title,
                    description = description,
                    coinChangeDollarsOnRetrieve = coinChangeDollars,
                    coinChangePercentsOnRetrieve = coinChangePercents,
                    aiAnalysis = aiAnalysis or "",
                    confidencePct = validation.confidencePct,
                    votes = validation.votes,
                    proofImage= f"{self.imagesPath}/{page}/{eventId}.png".replace("\\/", "/"),
                    sourceHref = sourceHref or ""
                ))
                
                #print(f"{index}. Event: coins {coins} with title {title} for the date {date} retrieved.")
            
            return entries
        else:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
            
    def RetrieveEventDetails(self, page: int, eventBody: PageElement) -> tuple[str, str, list[str], list[str], list[str], str, str, CMCEventValidation, str, str]:
        """
            Enters the event page and retrieves more details about the event such as coin change dollar, coin change percent and AI analysis.
        """
        
        eventHref = eventBody.find_all('a', class_="link-detail")[-1]['href']
        response = requests.get(f"{self.baseUrl}{eventHref}", headers = self.headers)
        
        eventId = eventHref.split('/')[-1]
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            eventDetail = soup.find('section', id="event-detail")
            
            coinNames, coinChangeDollars, coinChangePercents = [], [], []
            category = aiAnalysis = proofHref = sourceHref = validation = None
            addedDate = updatedDate = None
            
            if categories := eventDetail.find('div', class_="categories"):
                category = categories.find('a').get_text(strip=True)
            
            coinListItems = eventDetail.find_all('div', class_="coin-list-item")
            if coinListItems:
                for coinListItem in coinListItems:
                    coinNames.append(coinListItem.find('span', class_="name fz-16 ellipsis").get_text(strip=True))
                    try:
                        coinChangeDollars.append(coinListItem.find('span', class_="change-dollar").get_text(strip=True))
                        coinChangePercents.append(re.sub(r'\s+%', '%', coinListItem.find('span', class_="change-percent").find('span').get_text(strip=True)))
                    except AttributeError:
                        coinChangeDollars.append("")
                        coinChangePercents.append("")
                
            if description := eventDetail.find('div', id="description", class_="my-4"):
                if badge := description.find('span', class_="badge"):
                    if aiAnalysis := badge.next_sibling:
                        aiAnalysis = aiAnalysis.get_text(strip=True)
                        
            if refs := eventDetail.find('div', class_="mt-1"):
                imageFolderPath = f"{self.imagesPath}/{page}"
                imagePath = f"{imageFolderPath}/{eventId}.png"
                if not os.path.exists(imageFolderPath):
                    os.makedirs(imageFolderPath)
                  
                refs = refs.find_all('a')  
                if not os.path.exists(imagePath):
                    proofHref = refs[0]['href']
                    proofImage = requests.get(proofHref, headers = self.headers)
                    if proofImage.status_code == 200:
                        with open(imagePath, 'wb') as f:
                            f.write(proofImage.content)
                    else:
                        print(f"Failed to retrieve proof image {eventId}. Status code: {proofImage.status_code}")
                
                if len(refs) > 1:
                    sourceHref = refs[1]['href']
                        
            if validationContainer := eventDetail.find('div', class_="mb-3 p-4 card"):
                valConfidencePct = valVotes = 0
                
                if valConfidencePctContainer := validationContainer.find('div', id="confidence-index").find('span', class_="count-to"):
                    valConfidencePct = float(valConfidencePctContainer.get("data-countto"))
                
                if valVotesContainer := validationContainer.find('div', id="vote-number").find('span', class_="count-to"):
                    valVotes = int(valVotesContainer.get("data-countto"))
                    
                validation = CMCEventValidation(
                    confidencePct = valConfidencePct,
                    votes = valVotes
                )
                
            if addedContainer := eventDetail.find('div', class_="card p-4"):
                if addedDate := addedContainer.find('p', class_="added-date "):
                    addedDate = addedDate.get_text(strip=True).replace("Added", "").strip()
                    if updatedDate := addedContainer.find('p', class_="added-date mb-1"):
                        updatedDate = updatedDate.get_text(strip=True).replace("Updated", "").strip()
                else:
                    addedDate = addedContainer.find('p', class_="added-date mb-1").get_text(strip=True).replace("Added", "").strip()
                             
            return eventId, category, coinNames, coinChangeDollars, coinChangePercents, sourceHref, aiAnalysis, validation, addedDate, updatedDate
        else:
            print(f"Failed to retrieve event details ")
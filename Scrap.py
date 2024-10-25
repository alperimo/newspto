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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Cookie': 'device_view=full; _ga=GA1.1.786695681.1726145331; cmcalmode=dark; PHPSESSID=p7i4tvdrvt9o1jigs04vp2iqr6; AWSALB=rpU2unve5z0Xwa4A6L4QdVKrldqms5aFg4RJTLv4siMYocmuYN+MKGEnFw3edQGaGiOk0afr2CXN3D6BnNgZeFiGioFKi4FQCLLeDpnpw2ByLrMvwY8k3T7gMo11; _ga_90JJS7QB1F=GS1.1.1728419432.32.1.1728419438.0.0.0; cf_clearance=CG8pJa46S5MlUe0pVVxfhw04v_S4dGkxTBmPz1iGuOU-1728419441-1.2.1.1-ErEvy5ShJ9FpMzKTSn5UCwB3mD_10rv7JudqBcw9iyeSIJmlwVumslD38i147TYbK1T_9HemGc4cK00mUIY.3iFcuO9BgO46RwJf7NradYzUvlfbLnlaYdvptuxQk0O3YqG8aC75IN8KKsYWBP5Fl.rBWa.ej7eg5dhx5B6.GPCMSax1KOaj_so6gOlA_6U42qbSDLDmINi61t3CPNEDqrfy5kPJcdhDn6e23F5Uo55Bu1nblEiMqII8V0soAmrb4Q_fF8O._WbXqzYt5tDJis_b5IMKNFU4RKtpkz4FG6aT09uS21T0lpsSB_qdKq4amUW8TAz_D3IMiWbMTU0pyElhcvXn2uGQKZoE4IanEjWOFLIoKYpS5PPDqrfRAviUYMhEqQp7ZkeamvKIjQKb4mieZoF26REML1sHy1euZMmOesY8Dk3pJ_mAWwXErC9Y'
        }
        
        self.imagesPath = Constants.SCRAP_OUTPUTS_PATH + '/images'
        
    def RetrieveEvents(self, dateRange: str = "", coins: list[str] = [""], page: int = 1) -> list[CMCEvent]:
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
        
        response = requests.get(f"{self.baseUrl}/en/pastevents", headers = self.headers, params = params)
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
                    
                if title := eventBody.find_next('h5', class_="card__title mb-0 ellipsis"):
                    title = title.get_text(strip=True)
                    
                if description := eventBody.find_next('p', class_="card__description"):
                    description = description.get_text(strip=True)
                
                eventId, category, coins, coinChangeDollars, coinChangePercents, sourceHref, aiAnalysis, validation = self.RetrieveEventDetails(page, eventBody)
                
                entries.append(CMCEvent(
                    id = eventId,
                    category = category,
                    coins = coins,
                    date = date,
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
            
    def RetrieveEventDetails(self, page: int, eventBody: PageElement) -> tuple[str, str, list[str], list[str], list[str], str, str, CMCEventValidation]:
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
                             
            return eventId, category, coinNames, coinChangeDollars, coinChangePercents, sourceHref, aiAnalysis, validation
        else:
            print(f"Failed to retrieve event details ")
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
            'Cookie': 'device_view=full; _ga=GA1.1.786695681.1726145331; PHPSESSID=4dfj58q64ht5qvuvgt7ui23ops; cf_clearance=lXJAvrGPGOGs97J5EkRwubzv5fsm4Zd.ddgp9Cmh9IY-1728177531-1.2.1.1-XN.xX_DnhAjTdgKZc8A0poKN_NkuWTR_112MmS2qbHjv3ylTwLE2XOBZL8yrVRw98ASUeuupD5qBf2343lJa1X6jep6RLRhwpJYSi36am5J_o5zj7jDlRkqkQ93dwWfabmpF2Fgo_8QaXg8fQ5QkbBMJuR92YOnIFk__bjGbd7YADvQHnKBBCiWuso4G_40c98mQ9M_FAsvps4hDDbycSK5ttz6qgrMwtS5dnG46QvR9moX3EiAXC953kdAGultAk_8m03HcgsObE9v5VuMLxpu3zLd.HkMHaJH.BNzDI4xinmLBTkQUOl_iCVt5RlbYWje.7AdFy39wmIVuk03rwTDYyRaBkN5smVj40Dzf9S3V4WoaZlrBCauUoCmB8MEYmb5l7npNHXh310DKWKimoz9ljcZkNu9LxmL94Mqrse_aUJgk2yZe0ZplHPWSMou9; AWSALB=oRdBQVSvQgQzjGe+p5hxAhwVARwPujpMyhQ58FvVVLkUIdic6tAWzIf1T//WMVWVk6g95x2iELb/Jyn2MVKB5IgYEwdR+6rrYq2Bfz8QIfGIn5DSNJBaKmK0U8w7; _ga_90JJS7QB1F=GS1.1.1728175738.16.1.1728177805.0.0.0'
        }
        
        self.imagesPath = Constants.SCRAP_OUTPUTS_PATH + '/images'
        
    def RetrieveEvents(self, dateRange: str = "", coins: list[str] = [""], page: int = 1) -> list[CMCEvent]:
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
            
            for event in event_entries:
                eventBody = event.find_next('div', class_="card__body")
                
                if coin := eventBody.find_next('h5', class_="card__coins"):
                    # TODO: Handle other coins in the string
                    coin = coin.find('a').get_text(strip=True)
                
                if date := eventBody.find_next('h5', class_="card__date mt-0"):
                    date = date.get_text(strip=True)
                    
                if title := eventBody.find_next('h5', class_="card__title mb-0 ellipsis"):
                    title = title.get_text(strip=True)
                    
                if description := eventBody.find_next('p', class_="card__description"):
                    description = description.get_text(strip=True)
                
                eventId, coinChangeDollar, coinChangePercent, aiAnalysis, validation = self.RetrieveEventDetails(eventBody)
                
                entries.append(CMCEvent(
                    id = eventId,
                    coin = coin,
                    date = date,
                    title = title,
                    description = description,
                    coinChangeDollar = coinChangeDollar,
                    coinChangePercent = coinChangePercent,
                    aiAnalysis = aiAnalysis or "",
                    confidencePct = validation.confidencePct,
                    votes = validation.votes,
                    proofImage= f"{self.imagesPath}/{eventId}.png".replace("\/", "/")
                ))
                
            return entries
        else:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
            
    def RetrieveEventDetails(self, eventBody: PageElement) -> tuple[str, str, str, str, CMCEventValidation]:
        """
            Enters the event page and retrieves more details about the event such as coin change dollar, coin change percent and AI analysis.
        """
        
        eventHref = eventBody.find_all('a', class_="link-detail")[-1]['href']
        response = requests.get(f"{self.baseUrl}{eventHref}", headers = self.headers)
        
        eventId = eventHref.split('/')[-1]
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            eventDetail = soup.find('section', id="event-detail")
            
            coinChangeDollar = coinChangePercent = aiAnalysis = proofHref = validation = None
            
            if coinListItem := eventDetail.find('div', class_="coin-list-item"):
                try:
                    coinChangeDollar = coinListItem.find('span', class_="change-dollar").get_text(strip=True)
                    coinChangePercent = re.sub(r'\s+%', '%', coinListItem.find('span', class_="change-percent").find('span').get_text(strip=True))
                except AttributeError:
                    coinChangeDollar = None
                    coinChangePercent = None
                
            if description := eventDetail.find('div', id="description", class_="my-4"):
                if badge := description.find('span', class_="badge"):
                    if aiAnalysis := badge.next_sibling:
                        aiAnalysis = aiAnalysis.get_text(strip=True)
                        print(f"AI Analysis: {aiAnalysis}")
                        
            if ref := eventDetail.find('div', class_="mt-1"):
                date: str = datetime.datetime.now().strftime("%d%m%Y-%H%M")
                imageFolderPath = f"{self.imagesPath}"
                imagePath = f"{imageFolderPath}/{eventId}.png"
                if not os.path.exists(imageFolderPath):
                    os.makedirs(imageFolderPath)
                    
                if not os.path.exists(imagePath):
                    proofHref = ref.find('a')['href']
                    proofImage = requests.get(proofHref, headers = self.headers)
                    if proofImage.status_code == 200:
                        with open(imagePath, 'wb') as f:
                            f.write(proofImage.content)
                    else:
                        print(f"Failed to retrieve proof image {eventId}. Status code: {proofImage.status_code}")
                        
            if validationContainer := eventDetail.find('div', class_="mb-3 p-4 card"):
                valConfidencePct = valVotes = 0
                
                if valConfidencePctContainer := validationContainer.find('div', id="confidence-index").find('span', class_="count-to"):
                    valConfidencePct = valConfidencePctContainer.get_text(strip=True)
                
                if valVotesContainer := validationContainer.find('div', id="vote-number").find('span', class_="count-to"):
                    valVotes = valVotesContainer.get_text(strip=True)
                
                validation = CMCEventValidation(
                    confidencePct = int(valConfidencePct),
                    votes = int(valVotes)
                )
                        
            return eventId, coinChangeDollar, coinChangePercent, aiAnalysis, validation
        else:
            print(f"Failed to retrieve event details ")
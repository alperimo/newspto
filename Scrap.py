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
            'Cookie': 'device_view=full; _ga=GA1.1.786695681.1726145331; AWSALB=7D8sZY+UNs8F8VcBefWtg6IAakwFhW0P4hbAe+bPQF9oDKKSo8opRWn01/XB6Fhpj2RqWsQsPiEA55opTFtz/oGF5F9zzZz3eveQvEgUknGAFHAo/kK0+QujEY8d; _ga_90JJS7QB1F=GS1.1.1728077005.14.1.1728077867.0.0.0; cf_clearance=VyMvh1PzBuGJczdznK8wJfvYstKCzIhHercAAokuRqs-1728077869-1.2.1.1-Iaf32p_UCTdd4M30hlv_iLS8C3Kptv.b4tV2BSakm_qORryLv05kcaEaUASJJtXrDTtU2Zs7VsXsePTXrh0ITXkeN3AvjlA.g8m2XGzkxwWX8HKMO1c.MFuxp3zyCZ5nmWpo5Oc_sKjVtQbmOPv510KOlL2nR880e77x741BAvrPs_jRxh0x2GBZH3BRT5LYXPoyPz_Dxs7k506x7v1QmbL0JWF1f7ni6iXwrNgt2C51hpoQX0bZYrNK42TBqllTJPKJYzBdxHACIpNHhEuOJIf3m_oqh7Nc6oVnabBnqP65B5bnrrK2nUuHohA8F3mZsn3v_r.2Jr8C9u6svzW0PaI27xEUOE.rofZJ7NOIiKba9FMs0NLj5p2FcI2RbY3oV04yBARJWjqoC3lXpwz70Fwfc3zd4hEb44f9JRUk25sPQgwAz0woM75HTONOf8Kt'
        }
        
        self.imagesPath = Constants.SCRAP_OUTPUTS_PATH + '/images'
        
    def RetrieveEvents(self, dateRange: str = "", coins: list[str] = ["top300"]) -> list[CMCEvent]:
        params = {
            'form[date_range]': dateRange,
            'form[keyword]': '',
            'form[coin][]': coins,
            'form[sort_by]': '',
            'form[submit]': '',
            'form[show_reset]': ''
        }
        
        response = requests.get(f"{self.baseUrl}/en/pastevents", headers = self.headers, params = params)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            event_entries: ResultSet[PageElement] = soup.find_all('article', class_='col-xl-3 col-lg-4 col-md-6 py-3')
            
            entries: list[CMCEvent] = []
            
            for event in event_entries[:10]:
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
                    votes = validation.votes
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
                date: str = datetime.datetime.now().strftime("%d%m%Y_%H%M")
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
                valConfidencePct = validationContainer.find('div', id="confidence-index").find('span', class_="count-to").get_text(strip=True)
                valVotes = validationContainer.find('div', id="vote-number").find('span', class_="count-to").get_text(strip=True)
                
                validation = CMCEventValidation(
                    confidencePct = int(valConfidencePct),
                    votes = int(valVotes)
                )
                        
            return eventId, coinChangeDollar, coinChangePercent, aiAnalysis, validation
        else:
            print(f"Failed to retrieve event details ")
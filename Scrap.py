from typing import Any
from bs4 import BeautifulSoup
from bs4.element import PageElement, ResultSet

from Dataclasses import CMCEvent, CMCEventValidation

import os, re, requests

class Scrap:
    def __init__(self):
        self.baseUrl = 'https://coinmarketcal.com'
        self.headers = {
            'Authority': 'coinmarketcal.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Cookie': 'device_view=full; _ga=GA1.1.786695681.1726145331; cf_clearance=jdaHqd5mPaaUK_PMgQ0h48wqF1Qi3MXU6bRpVSTCXm8-1727531865-1.2.1.1-rNLpshqx6X1AP04dHy9LJMFJ.53SJQFmK6DZ.LNFfoqvoOihy3fYJEBip_7CoNtFSBrl3CatJw1vUIo8JgM4MqUnZhagJKG4jm.XfnFSpvfeGp24t7V5g4TfpuMAXtlqMFr70bpmx83LTwSAFnfhR4THdZCphgv8oNid7pE5rGF_1c5ImZ9cK0HB17CyGCalnJEx0g2Zsc2EB4X5_PDa9qdDkuZyeJIIsYo9CmGW2x3MwsWQSlqUgvRXrSpTn50SedVCBmkHCCOqUlF.gNJ4M6ZWlfbsvTqIo5BHdhkdE7u7Hv5ZDamMZscd2ftEsmNj9e.6I7UUYWNI0SQfuifVoEa6iZ16UyCJk2hjiTFxdZQuRg2VsYDlOHfit2l7C7PeMOVbrPeQIpTvyYo1lnF2QSqUq._YGbg0wYeb.b6OFsGAIy5lQ3YJLeJijMJW1xNz; PHPSESSID=0tn5m1et2f8i3cbo1ie6l6e8vj; AWSALB=R3OW55qP/GXDVRRWhPbgU5BIG7BF+pHCMi9JEBr9epHTmIy/ekKWp8Rq0TpgJJv6o4s1mggpZanZKN+HhTFWtMoHx7EKMPTExsWBKr2PDH50KpF/53Tt1ESnOpSl; _ga_90JJS7QB1F=GS1.1.1727531860.6.1.1727531926.0.0.0',
            'Referer': 'https://coinmarketcal.com/en/?form%5Bdate_range%5D=26%2F09%2F2024+-+30%2F07%2F2027&form%5Bkeyword%5D=&form%5Bcoin%5D%5B%5D=top300&form%5Bsort_by%5D=&form%5Bsubmit%5D=',
        }
        
        self.imagesPath = 'images'
        
    def RetrieveEvents(self):
        response = requests.get(f"{self.baseUrl}/en/pastevents", headers = self.headers)
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
                
                coinChangeDollar, coinChangePercent, aiAnalysis, validation = self.RetrieveEventDetails(eventBody)
                
                entries.append(CMCEvent(
                    coin = coin,
                    date = date,
                    title = title,
                    description = description,
                    coinChangeDollar = coinChangeDollar,
                    coinChangePercent = coinChangePercent,
                    aiAnalysis = aiAnalysis,
                    confidencePct = validation.confidencePct,
                    votes = validation.votes
                ))
                
            return entries
        else:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
            
    def RetrieveEventDetails(self, eventBody: PageElement) -> tuple[str, str, str, CMCEventValidation]:
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
                coinChangeDollar = coinListItem.find('span', class_="change-dollar").get_text(strip=True)
                coinChangePercent = re.sub(r'\s+%', '%', coinListItem.find('span', class_="change-percent").find('span').get_text(strip=True))
                
            if description := eventDetail.find('div', id="description", class_="my-4"):
                if badge := description.find('span', class_="badge"):
                    if aiAnalysis := badge.next_sibling:
                        aiAnalysis = aiAnalysis.get_text(strip=True)
                        print(f"AI Analysis: {aiAnalysis}")
                        
            if ref := eventDetail.find('div', class_="mt-1"):
                if not os.path.exists(f"{self.imagesPath}/{eventId}.png"):
                    proofHref = ref.find('a')['href']
                    proofImage = requests.get(proofHref, headers = self.headers)
                    if proofImage.status_code == 200:
                        with open(f"{eventId}.png", 'wb') as f:
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
                        
            return coinChangeDollar, coinChangePercent, aiAnalysis, validation
        else:
            print(f"Failed to retrieve event details ")
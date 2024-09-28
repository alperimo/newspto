from typing import Any
from bs4 import BeautifulSoup
from bs4.element import PageElement, ResultSet

import re, requests

class Scrap:
    def __init__(self):
        self.baseUrl = 'https://coinmarketcal.com'
        self.headers = {
            'Authority': 'coinmarketcal.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Cookie': 'device_view=full; _ga=GA1.1.786695681.1726145331; PHPSESSID=35qedd7g673cobnhj1jun6gr8j; cf_clearance=1Gn5zXEi7p3TZJ91_j8Rtoqktl6LRVQXo9cpV.FHL7M-1727395227-1.2.1.1-cfd9mSuLqp1S3xWCfrab8_Mxu2a3BenHM1zH2.Uq_ibHb_ClucccddyY8ADgwuqVDOBnf8uvvsdLxWXwW4kJbVZqWTS6XEamd7up5mT6gMUHDllSUzUEb_DACstPkj8F7S6yIAhYhkZCe56Fym_d7Zc35.DrYGrDOeAY35F65F4Qfa6LDhzpS.GnSNP7sJKKRwNzfNSvmcibSDcWFVY.dpE.eV0u0WyoDuuSp1fmYAzmMrdDWMLsXCqJwjZ5345njRqXTXeAOiVzG_xxR8Fys8iHehHUPHzOqlRa5yqcQMOcHUfC.I9b65L6BOc7sMK2CaT9KAX1mzGEdxqiKRBbhz4QobifjV1xiU2dcg6yJBXqAEQWwTXDp3ShLSZ2Hr1nusxmyS87xufnNJ0bu2eGJIGIClFhvFm3c_8BXilSlm6PAE_u2th3U9OEEJe2sXtH; AWSALB=8FQm6x2MRiseVCHHmw6meB9XWcBIPGuIcmjRrnxBinr5VdPHnbRt5KlOjDAPDL/kPCK16rcATT0upnJrZ3r/HQLlV3KBPnmnWmVJaMqlMHFK3RjexYEHm1vKt6ox; _ga_90JJS7QB1F=GS1.1.1727392119.5.1.1727395689.0.0.0',
            'Referer': 'https://coinmarketcal.com/en/?form%5Bdate_range%5D=26%2F09%2F2024+-+30%2F07%2F2027&form%5Bkeyword%5D=&form%5Bcoin%5D%5B%5D=top300&form%5Bsort_by%5D=&form%5Bsubmit%5D=',
        }
        
    def RetrieveEvents(self):
        response = requests.get(f"{self.baseUrl}/en/pastevents", headers = self.headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            event_entries: ResultSet[PageElement] = soup.find_all('article', class_='col-xl-3 col-lg-4 col-md-6 py-3')
            
            entries: list[dict[str, Any]] = []
            
            for event in event_entries[:1]:
                eventBody = event.find_next('div', class_="card__body")
                
                if coin := eventBody.find_next('h5', class_="card__coins"):
                    coin = coin.find('a').get_text(strip=True)
                
                if date := eventBody.find_next('h5', class_="card__date mt-0"):
                    date = date.get_text(strip=True)
                    
                if exchangePlatform := eventBody.find_next('h5', class_="card__title mb-0 ellipsis"):
                    exchangePlatform = exchangePlatform.get_text(strip=True)
                    
                if description := eventBody.find_next('p', class_="card__description"):
                    description = description.get_text(strip=True)
                
                print(f"Coin: {coin}")
                print(f"Date: {date}")
                print(f"Exchange Platform: {exchangePlatform}")
                print(f"Description: {description}")
                
                coinChangeDollar, coinChangePercent, aiAnalysis = self.RetrieveEventDetails()
                
                entries.append({
                    'coin': coin,
                    'date': date,
                    'exchangePlatform': exchangePlatform,
                    'description': description,
                    'coinChangeDollar': coinChangeDollar,
                    'coinChangePercent': coinChangePercent,
                    'aiAnalysis': aiAnalysis
                })
                
                print("-" * 40)
        else:
            print(f"Failed to retrieve page. Status code: {response.status_code}")
            
    def RetrieveEventDetails(self, eventBody: PageElement) -> tuple[str, str, str]:
        """
            Enters the event page and retrieves more details about the event such as coin change dollar, coin change percent and AI analysis.
        """
        
        eventHref = eventBody.find_all('a', class_="link-detail")[-1]['href']
        response = requests.get(f"{self.baseUrl}{eventHref}", headers = self.headers)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            if coinListItem := soup.find('div', class_="coin-list-item"):
                coinChangeDollar = coinListItem.find('span', class_="change-dollar").get_text(strip=True)
                coinChangePercent = re.sub(r'\s+%', '%', coinListItem.find('span', class_="change-percent").find('span').get_text(strip=True))
                
                print(f"Change Dollar: {coinChangeDollar} Change Percent: {coinChangePercent}")
                
            if description := soup.find('div', id="description", class_="my-4"):
                if badge := description.find('span', class_="badge"):
                    if aiAnalysis := badge.next_sibling:
                        aiAnalysis = aiAnalysis.get_text(strip=True)
                        print(f"AI Analysis: {aiAnalysis}")
                        
            return coinChangeDollar, coinChangePercent, aiAnalysis
        else:
            print(f"Failed to retrieve event details ")
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List
import re
from datetime import datetime
import yfinance as yf
import pandas as pd
from GoogleNews import GoogleNews

class ExchangeRateCollector:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Google News 초기화
        self.gn = GoogleNews()
        self.gn.set_lang('en')
        self.gn.set_period('1d')  # 오늘 하루의 뉴스만 수집

    def get_exchange_rate_data(self) -> Dict:
        """야후 파이낸스에서 USD/KRW 환율 데이터를 수집합니다."""
        try:
            # USD/KRW 환율 데이터 가져오기
            ticker = yf.Ticker("USDKRW=X")  # USD/KRW 환율의 야후 파이낸스 심볼
            hist = ticker.history(period="2d")  # 2일치 데이터를 가져와서 변동폭 계산
            
            if hist.empty:
                self.logger.error("환율 데이터를 찾을 수 없습니다.")
                return {}
            
            # 가장 최근 데이터 가져오기
            latest = hist.iloc[-1]
            
            # 환율과 변동폭 계산
            rate = latest['Close']  # USDKRW=X는 이미 USD/KRW 비율이므로 그대로 사용
            
            # 전일 종가로 변동폭 계산
            if len(hist) > 1:
                prev_rate = hist.iloc[-2]['Close']
                change_value = rate - prev_rate
                change_percent = (change_value / prev_rate) * 100
            else:
                change_value = 0
                change_percent = 0
            
            result = {
                'Date': latest.name.to_pydatetime(),
                'Close': rate,
                'Change': change_value,
                'ChangePercent': change_percent
            }
            
            self.logger.info(f"수집된 환율 데이터: {rate:.2f}원 (변동: {change_value:+.2f}원, {change_percent:+.2f}%)")
            return result
            
        except Exception as e:
            self.logger.error(f"환율 데이터 수집 중 오류: {str(e)}")
            return {}

    def get_exchange_rate_news(self) -> List[Dict]:
        """네이버 금융, Yahoo Finance, Google News에서 환율 관련 뉴스를 수집합니다."""
        try:
            news_items = []
            
            # 1. 네이버 금융 뉴스 수집
            exchange_url = "https://finance.naver.com/marketindex/exchangeDetail.naver?marketindexCd=FX_USDKRW"
            response = requests.get(exchange_url, headers=self.headers)
            response.encoding = 'euc-kr'
            soup = BeautifulSoup(response.text, 'html.parser')
            
            news_list = soup.select('#content > div.section_news._replaceNewsLink > ul > li')
            
            for news in news_list[:3]:  # 최근 3개 뉴스만 수집
                title_element = news.select_one('dl > dt > a')
                content_element = news.select_one('dl > dd')
                
                if all([title_element, content_element]):
                    title = title_element.text.strip()
                    link = title_element.get('href')
                    if link and not link.startswith('http'):
                        link = f"https://finance.naver.com{link}"
                    
                    content = content_element.text.strip()
                    date = datetime.now()
                    
                    news_items.append({
                        'title': title,
                        'content': content,
                        'link': link,
                        'time': date,
                        'source': '네이버 금융',
                        'importance': 'high'  # 네이버 금융 뉴스는 중요도가 높음
                    })
            
            # 2. Yahoo Finance 뉴스 수집
            yahoo_url = "https://finance.yahoo.com/quote/USDKRW=X/news"
            response = requests.get(yahoo_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            yahoo_news = soup.select('div[data-test="content-viewer"] article')
            for news in yahoo_news[:3]:  # 최근 3개 뉴스만 수집
                title_element = news.select_one('h3 a')
                content_element = news.select_one('p')
                
                if all([title_element, content_element]):
                    title = title_element.text.strip()
                    link = title_element.get('href')
                    if link and not link.startswith('http'):
                        link = f"https://finance.yahoo.com{link}"
                    
                    content = content_element.text.strip()
                    date = datetime.now()
                    
                    news_items.append({
                        'title': title,
                        'content': content,
                        'link': link,
                        'time': date,
                        'source': 'Yahoo Finance',
                        'importance': 'high'  # Yahoo Finance 뉴스도 중요도가 높음
                    })
            
            # 3. Google News 뉴스 수집
            try:
                # Google News 설정
                self.gn.clear()
                self.gn.set_time_range(start=datetime.now().strftime("%m/%d/%Y"))
                self.gn.get_news()
                
                # 결과를 DataFrame으로 변환
                results = self.gn.results()
                if results:
                    df = pd.DataFrame(results)[['title', 'datetime']]
                    df['date'] = df['datetime'].dt.date
                    
                    # 중요 키워드 정의
                    priority_keywords = {
                        'high': ['tariff', 'trade', 'fed', 'interest rate', 'inflation', 'economy', 'market', 'exchange rate', 'USD/KRW'],
                        'medium': ['earnings', 'stock', 'company', 'industry', 'export', 'import'],
                        'low': ['product', 'service', 'individual stock']
                    }
                    
                    # 뉴스 데이터 변환
                    for _, row in df.iterrows():
                        title = row['title']
                        
                        # 뉴스 중요도 평가
                        importance = 'low'
                        for level, keywords in priority_keywords.items():
                            if any(keyword.lower() in title.lower() for keyword in keywords):
                                importance = level
                                break
                        
                        news_items.append({
                            'title': title,
                            'content': '',  # Google News는 본문이 없음
                            'link': '',  # Google News는 링크가 없음
                            'time': row['date'].strftime('%Y-%m-%d'),
                            'source': 'Google News',
                            'importance': importance
                        })
            except Exception as e:
                self.logger.error(f"Google News 수집 중 오류: {str(e)}")
            
            # 중요도에 따라 정렬
            importance_order = {'high': 0, 'medium': 1, 'low': 2}
            news_items.sort(key=lambda x: importance_order[x['importance']])
            
            self.logger.info(f"수집된 뉴스: {len(news_items)}개 (네이버 금융: {len(news_list[:3])}개, Yahoo Finance: {len(yahoo_news[:3])}개, Google News: {len(news_items) - len(news_list[:3]) - len(yahoo_news[:3])}개)")
            return news_items
            
        except Exception as e:
            self.logger.error(f"뉴스 데이터 수집 중 오류: {str(e)}")
            return []

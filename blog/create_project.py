import os
import yaml

# 프로젝트 생성 스크립트
def create_project():
    # 기본 디렉토리 구조 생성
    directories = [
        'blog',
        'blog/src',
        'blog/config',
        'blog/logs'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created directory: {directory}")

    # environment.yml 생성
    environment_content = '''name: blog
channels:
  - conda-forge
  - defaults
dependencies:
  - python=3.9
  - pandas=2.1.4
  - numpy=1.26.2
  - requests=2.31.0
  - selenium=4.16.0
  - beautifulsoup4=4.12.2
  - python-dotenv=1.0.0
  - pyyaml=6.0.1
  - pip=23.3.1
  - pip:
    - yfinance==0.2.36
    - pandas-datareader==0.10.0
    - webdriver-manager==4.0.1
    - schedule==1.2.1
'''
    
    with open('blog/environment.yml', 'w') as f:
        f.write(environment_content)
    print("Created environment.yml")

    # .env 생성
    env_content = '''DEEPSEEK_API_KEY=sk-99ce251b47c64df8af4245d881d5935f
NAVER_USERNAME=jsy830
NAVER_PASSWORD=tpDUDdl830!
'''
    
    with open('blog/.env', 'w') as f:
        f.write(env_content)
    print("Created .env")

    # config.yaml 생성
    config_content = '''data_collection:
  yfinance:
    history_days: 3
    indices:
      - ^GSPC  # S&P 500
      - ^DJI   # Dow Jones
      - ^IXIC  # NASDAQ
      - ^RUT   # Russell 2000
  
  market_data:
    categories:
      - gainers
      - losers
      - most_active
      - top_etfs

blog_settings:
  platform: naver
  category_id: default
  tags_limit: 10
  auto_publish: true

logging:
  level: INFO
  file: logs/app.log
'''
    
    with open('blog/config/config.yaml', 'w') as f:
        f.write(config_content)
    print("Created config.yaml")

    # Python 파일들 생성
    python_files = {
        'blog/src/__init__.py': '',
        
        'blog/src/data_collector.py': '''import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import logging
from typing import Dict, List

class MarketDataCollector:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def get_market_data(self) -> Dict[str, pd.DataFrame]:
        urls = {
            'gainers': 'https://finance.yahoo.com/gainers',
            'losers': 'https://finance.yahoo.com/losers',
            'most_active': 'https://finance.yahoo.com/most-active',
            'top_etfs': 'https://finance.yahoo.com/etfs'
        }

        market_data = {}
        for category, url in urls.items():
            try:
                response = requests.get(url, headers=self.headers)
                df = pd.read_html(response.text)[0]
                market_data[category] = df[['Symbol', 'Name', 'Price (Intraday)', '% Change']]
            except Exception as e:
                self.logger.error(f"Error collecting {category} data: {e}")
                market_data[category] = pd.DataFrame()

        return market_data

    def get_market_news(self) -> List[Dict]:
        url = "https://finance.yahoo.com/news/"
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            news_items = []
            
            for article in soup.select('div.Cf'):
                title = article.select_one('h3')
                if title:
                    news_items.append({
                        'title': title.text,
                        'time': datetime.now().strftime('%Y-%m-%d')
                    })
            return news_items[:5]
        except Exception as e:
            self.logger.error(f"Error collecting news: {e}")
            return []
''',
        
        'blog/src/market_analyzer.py': '''import pandas as pd
import logging
from typing import Dict, List
import os
import requests

class MarketAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('DEEPSEEK_API_KEY')

    def analyze_market_trend(self, market_data: Dict[str, pd.DataFrame], news: List[Dict]) -> Dict:
        try:
            # 데이터 준비
            analysis_data = {
                'top_gainers': market_data['gainers'].head(5).to_dict('records'),
                'top_losers': market_data['losers'].head(5).to_dict('records'),
                'most_active': market_data['most_active'].head(5).to_dict('records'),
                'top_etfs': market_data['top_etfs'].head(5).to_dict('records'),
                'recent_news': news[:5]
            }

            # DeepSeek API를 통한 분석
            prompt = self._create_analysis_prompt(analysis_data)
            analysis = self._get_deepseek_analysis(prompt)

            return {
                'raw_data': analysis_data,
                'analysis': analysis
            }
        except Exception as e:
            self.logger.error(f"Error analyzing market data: {e}")
            return {}

    def _create_analysis_prompt(self, data: Dict) -> str:
        return f"""Analyze today's market trends based on the following data:

Top Gainers:
{self._format_stock_list(data['top_gainers'])}

Top Losers:
{self._format_stock_list(data['top_losers'])}

Most Active Stocks:
{self._format_stock_list(data['most_active'])}

Recent News:
{self._format_news_list(data['recent_news'])}

Please provide a comprehensive analysis focusing on:
1. The most significant market movement today
2. Potential reasons for these movements
3. Key trends to watch
4. Interesting correlations between different market segments
"""

    def _format_stock_list(self, stocks: List[Dict]) -> str:
        return "\n".join([f"- {stock['Name']} ({stock['Symbol']}): {stock['% Change']}" 
                         for stock in stocks])

    def _format_news_list(self, news: List[Dict]) -> str:
        return "\n".join([f"- {item['title']}" for item in news])

    def _get_deepseek_analysis(self, prompt: str) -> str:
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                'https://api.deepseek.com/v1/completions',
                headers=headers,
                json={
                    'prompt': prompt,
                    'max_tokens': 1000,
                    'temperature': 0.7
                }
            )
            
            if response.status_code == 200:
                return response.json()['choices'][0]['text']
            else:
                self.logger.error(f"DeepSeek API error: {response.text}")
                return "분석 중 오류가 발생했습니다."
        except Exception as e:
            self.logger.error(f"Error calling DeepSeek API: {e}")
            return "분석 중 오류가 발생했습니다."
''',
        
        'blog/src/blog_poster.py': '''from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import os
from dotenv import load_dotenv
from typing import List

class NaverBlogPoster:
    def __init__(self, config: dict):
        load_dotenv()
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.username = os.getenv('NAVER_USERNAME')
        self.password = os.getenv('NAVER_PASSWORD')
        self.driver = None

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=options)

    def login(self):
        try:
            self.driver.get('https://nid.naver.com/nidlogin.login')
            
            # JavaScript를 통한 로그인
            self.driver.execute_script(
                f"document.getElementsByName('id')[0].value='{self.username}'")
            self.driver.execute_script(
                f"document.getElementsByName('pw')[0].value='{self.password}'")
            
            # 로그인 버튼 클릭
            self.driver.find_element(By.CLASS_NAME, 'btn_login').click()
            return True
        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def create_post(self, title: str, content: str, tags: List[str]) -> bool:
        try:
            self.driver.get('https://blog.naver.com/posting/post.nhn')
            
            # 제목 입력
            title_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'subject'))
            )
            title_input.send_keys(title)
            
            # 내용 입력
            self.driver.switch_to.frame('mainFrame')
            content_editor = self.driver.find_element(By.CLASS_NAME, 'se-component-content')
            content_editor.send_keys(content)
            
            # 태그 입력
            for tag in tags[:self.config['blog_settings']['tags_limit']]:
                tag_input = self.driver.find_element(By.CLASS_NAME, 'tag-input')
                tag_input.send_keys(f"#{tag} ")
            
            # 발행
            if self.config['blog_settings']['auto_publish']:
                publish_button = self.driver.find_element(By.CLASS_NAME, 'publish-btn')
                publish_button.click()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to create post: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()
''',
        
        'blog/src/main.py': '''import yaml
import logging
import schedule
import time
from data_collector import MarketDataCollector
from market_analyzer import MarketAnalyzer
from blog_poster import NaverBlogPoster
from datetime import datetime

def setup_logging(config):
    logging.basicConfig(
        level=config['logging']['level'],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename=config['logging']['file']
    )

def main():
    # 설정 로드
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # 로깅 설정
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    try:
        # 데이터 수집
        collector = MarketDataCollector(config)
        market_data = collector.get_market_data()
        news = collector.get_market_news()
        
        # 시장 분석
        analyzer = MarketAnalyzer(config)
        analysis = analyzer.analyze_market_trend(market_data, news)
        
        # 블로그 포스팅
        poster = NaverBlogPoster(config)
        poster.setup_driver()
        
        if poster.login():
            title = f"오늘의 시장 동향 분석 - {datetime.now().strftime('%Y-%m-%d')}"
            content = analysis['analysis']
            tags = ["주식", "시장분석", "투자", "경제", "미국주식"]
            
            success = poster.create_post(title, content, tags)
            if success:
                logger.info("Blog post created successfully")
            else:
                logger.error("Failed to create blog post")
        
        poster.close()
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}")

if __name__ == "__main__":
    # 매일 장 마감 후 실행 (한국 시간 기준 아침 7시)
    schedule.every().day.at("07:00").do(main)
    
    while True:
        schedule.run_pending()
        time.sleep(60)
'''
    }

    for file_path, content in python_files.items():
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Created {file_path}")

    # README.md 생성
    readme_content = '''# Market Analysis Blog Automation

This project automatically collects market data, analyzes it using DeepSeek AI, and posts the analysis to a Naver blog.

## Setup

1. Create conda environment:
```bash
conda env create -f environment.yml
```

2. Activate environment:
```bash
conda activate blog
```

3. Run the script:
```bash
python src/main.py
```

## Configuration

- Edit `config/config.yaml` for customizing data collection and blog posting settings
- Environment variables are stored in `.env` file

## Features

- Collects market data from Yahoo Finance
- Analyzes market trends using DeepSeek AI
- Automatically posts analysis to Naver blog
- Scheduled execution at market close
'''

    with open('blog/README.md', 'w') as f:
        f.write(readme_content)
    print("Created README.md")

if __name__ == "__main__":
    create_project()
    print("\nProject creation completed!")
    print("\nTo get started:")
    print("1. cd blog")
    print("2. conda env create -f environment.yml")
    print("3. conda activate blog")
    print("4. python src/main.py")
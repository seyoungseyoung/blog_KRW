import pandas as pd
import logging
from typing import Dict, List, Any
import os
import requests
import json
from utils import parse_price_string
import time
from datetime import datetime
import pytz

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

class ExchangeRateAnalyzer:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.api_key = os.getenv('DEEPSEEK_API_KEY')
        
        if not self.api_key:
            raise ValueError("DeepSeek API key not found in environment variables")

    def analyze_market(self, market_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """시장 분석을 수행합니다."""
        try:
            # 데이터 준비
            prepared_data = self._prepare_analysis_data(market_data)
            if not prepared_data:
                return None
            
            # 분석 수행 (자동 진행)
            analysis_result = self._perform_analysis(prepared_data)
            if not analysis_result:
                return None
            
            return analysis_result
        
        except Exception as e:
            self.logger.error(f"시장 분석 중 오류 발생: {e}")
            return None

    def analyze_market_trend(self, market_data: Dict, news: List[Dict]) -> Dict:
        """시장 데이터와 뉴스를 분석하여 트렌드를 파악합니다."""
        try:
            # 데이터 유효성 검사
            if not isinstance(market_data, dict) or not all(key in market_data for key in ['Close', 'Change', 'ChangePercent', 'Date']):
                self.logger.error("잘못된 시장 데이터 형식입니다.")
                return self._create_fallback_content()
            
            # 데이터 준비
            prepared_data = {
                'current_rate': market_data['Close'],
                'daily_change': market_data['ChangePercent'],
                'change_value': market_data['Change'],
                'date': market_data['Date']
            }
            
            if news:
                prepared_data['naver_news'] = news
            
            # 종합적인 시장 논평 생성
            print("- 시장 논평 작성 중...")
            market_commentary = self._get_deepseek_analysis(self._create_market_commentary_prompt(prepared_data))
            if not market_commentary or "분석 내용 생성에 실패" in market_commentary:
                return self._create_fallback_content(prepared_data)
            print("✓ 시장 논평 작성 완료")
            
            # 논평을 바탕으로 제목 생성
            print("- 제목 생성 중...")
            title = self._get_deepseek_analysis(self._create_title_from_commentary_prompt(market_commentary))
            if not title or "분석 내용 생성에 실패" in title:
                title = self._create_fallback_title(prepared_data)
            print("✓ 제목 생성 완료")
            
            # 태그 생성
            print("- 태그 생성 중...")
            tags = self._create_tags_from_content(title, market_commentary)
            print("✓ 태그 생성 완료")
            
            # 분석 결과 구조 통일
            return {
                "title": title,
                "commentary": market_commentary,
                "tags": tags
            }
            
        except Exception as e:
            self.logger.error(f"시장 분석 중 오류 발생: {e}", exc_info=True)
            return self._create_fallback_content()

    def _prepare_analysis_data(self, market_data: Dict[str, pd.DataFrame], news: List[Dict] = None) -> Dict:
        """시장 데이터를 분석용으로 가공합니다."""
        try:
            # 데이터 유효성 검증
            if not isinstance(market_data, pd.DataFrame):
                self.logger.error("Invalid market data format")
                return None
            
            # 환율 데이터 처리
            significant_moves = {}
            
            # 현재 환율과 변동 정보 추출
            if not market_data.empty:
                current_rate = float(market_data['Close'].iloc[0])
                daily_change = float(market_data['ChangePercent'].iloc[0])
                
                significant_moves['current_rate'] = current_rate
                significant_moves['daily_change'] = daily_change
                
                self.logger.info(f"Current exchange rate: {current_rate:.2f}원 (Change: {daily_change:+.2f}%)")
            
            # 뉴스 데이터 처리
            if news:
                current_date = datetime.now().strftime('%Y-%m-%d')
                processed_news = []
                for item in news[:5]:  # 최대 5개 뉴스만 처리
                    if isinstance(item, dict):
                        # 뉴스 항목에 date 필드 추가 (time을 date로 변환)
                        news_item = item.copy()
                        news_item['date'] = item.get('time', current_date)  # time이 있으면 사용, 없으면 현재 날짜
                        processed_news.append(news_item)
                
                if processed_news:
                    significant_moves['naver_news'] = processed_news
                    self.logger.info(f"Processed {len(processed_news)} news items with date: {current_date}")
            
            print("\n처리된 데이터:")
            for key, value in significant_moves.items():
                if key != 'naver_news':
                    print(f"\n{key}:")
                    print(f"- {value}")
            
            return significant_moves
            
        except Exception as e:
            self.logger.error(f"Error preparing analysis data: {e}")
            print(f"데이터 처리 중 오류 발생: {e}")
            return None

    # 개별 시장 분석 관련 메서드 주석 처리

    def _create_market_commentary_prompt(self, data: Dict) -> str:
        """시장 데이터를 바탕으로 종합적인 논평을 생성하는 프롬프트를 만듭니다."""
        current_date = datetime.now(KST).strftime('%Y-%m-%d')
        current_time = datetime.now(KST).strftime('%H:%M')
        
        template = f"""다음 원달러 환율 데이터를 바탕으로 {current_date} {current_time} KST 기준 환율 동향을 분석해주세요.

[환율 정보]
현재 환율: {data['current_rate']:.2f}원
전일 대비: {data['daily_change']:+.2f}%

[주요 뉴스]"""

        if 'naver_news' in data and data['naver_news']:
            template += "\n네이버 금융 뉴스:"
            for news in data['naver_news']:
                template += f"\n- {news['title']}"
                if 'content' in news and news['content']:
                    template += f"\n  {news['content'][:100]}..."  # 뉴스 본문 일부 포함
        else:
            template += "\n- 오늘의 주요 뉴스가 없습니다."

        template += """

작성 요구사항:
1. 환율 동향 분석 (300자 이상)
   - 오늘의 원달러 환율 움직임을 상세히 설명
   - 전일 대비 변동폭과 그 의미를 깊이 있게 분석
   - 주요 변동 요인을 상세히 설명
   - 장중 변동폭과 특징적인 움직임 설명

2. 뉴스 기반 분석 (300자 이상)
   - 주요 뉴스 내용을 상세히 분석
   - 각 뉴스가 환율에 미친 영향 설명
   - 시장 참여자들의 반응과 심리 분석
   - 관련 산업 및 기업에 미치는 영향

3. 실무적 시사점 (300자 이상)
   - 기업 관점의 시사점 상세 분석
   - 개인 투자자 관점의 시사점 상세 분석
   - 단기적 대응 방안 제시
   - 중장기 전망과 주의점

작성 스타일:
- 전체 분량: 1,500자 이상
- 문단별 소제목 포함
- 전문용어는 반드시 쉽게 풀어서 설명
- 일반 직장인도 이해하기 쉽게 작성
- 객관적이고 중립적인 톤 유지
- 구체적인 수치와 팩트 중심으로 작성

참고사항:
- 투자 조언이나 확정적 전망은 피할 것
- 근거 없는 추측성 내용 배제
- 정확한 수치와 팩트 중심으로 작성
"""
        return template

    def _create_title_from_commentary_prompt(self, analysis: str) -> str:
        """분석 내용을 바탕으로 제목 생성 프롬프트를 만듭니다."""
        current_date = datetime.now(KST).strftime('%m/%d')
        current_time = datetime.now(KST).strftime('%H:%M')
        
        return f"""다음 환율 분석을 바탕으로 블로그 포스팅 제목을 작성해주세요.

분석 내용: {analysis}

제목 요구사항:
1. 필수 포함 요소
   - '[{current_date} {current_time} 환율분석]' 접두어
   - 날짜와 KST시간 표시 ({current_date} {current_time} KST)
   - 핵심 환율 동향 또는 주요 영향 요인

2. 작성 스타일
   - 전체 길이: 30자 내외
   - 명확하고 간결한 표현
   - 구체적인 수치나 데이터 포함
   - 객관적이고 중립적인 톤 유지

3. 제목 예시
- [{current_date} {current_time} 환율분석] KST 원달러 1,456원, 美 관세 유예에 하락세
- [{current_date} {current_time} 환율분석]  환율 27.7원↓…수출기업 달러매도 증가
- [{current_date} {current_time} 환율분석] 원달러 1.85% 급락…美 관세 유예 영향

4. 유의사항
- 제목 선정이유 반드시 제거하기 (예 : 프롬프트의 내용을 반영했다는 글)
- 제목은 반드시 하나만 출력하기
"""

    def _format_news_list(self, news: List[Dict]) -> str:
        """뉴스 목록을 포맷팅합니다."""
        return "\n".join([f"- {item['title']}" for item in news])

    def _get_deepseek_analysis(self, prompt: str, max_retries=3, timeout=60) -> str:
        """DeepSeek API를 호출하여 분석 결과를 얻습니다."""
        for attempt in range(max_retries):
            try:
                headers = {
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                }
                
                print(f"분석 생성 중... (시도 {attempt+1}/{max_retries})")
                response = requests.post(
                    'https://api.deepseek.com/v1/chat/completions',
                    headers=headers,
                    json=payload,
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    result = response.json()['choices'][0]['message']['content']
                    # 결과에서 별표(*) 제거
                    result = result.replace('*', '')
                    
                    # 제목 생성의 경우 추가 다듬기 없이 바로 반환
                    if "제목을 작성해주세요" in prompt:
                        return result
                    
                    # 본문 내용인 경우에만 다듬기 진행
                    refinement_prompt = f"""다음 내용을 더 자연스럽고 전문적인 블로그 스타일로 다듬어주세요.
원문: {result}

다듬기 요구사항:
1. 하루 5번 게시되기에 현재 시황에 집중
2. 하나의 이슈에 대해서만 깊이있게 줄글로 작성하기
3. 소비자들에게 불필요한 설명이나 내용, 강조표시를 제거하기 (예 : 프롬프트의 내용을 반영했다는 글)
4. 전문적이지만 조언 금지
5. 핵심 내용은 유지하면서 자연스러운 흐름으로 재구성
6. 별표(*)나 다른 특수문자는 절대 사용하지 않음
"""
                    
                    refinement_payload = {
                        "model": "deepseek-chat",
                        "messages": [
                            {
                                "role": "user",
                                "content": refinement_prompt
                            }
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1500
                    }
                    
                    print("결과 다듬기 중...")
                    refinement_response = requests.post(
                        'https://api.deepseek.com/v1/chat/completions',
                        headers=headers,
                        json=refinement_payload,
                        timeout=timeout
                    )
                    
                    if refinement_response.status_code == 200:
                        refined_result = refinement_response.json()['choices'][0]['message']['content']
                        # 결과에서 별표(*) 제거
                        refined_result = refined_result.replace('*', '')
                        return refined_result
                    else:
                        self.logger.error(f"다듬기 API 오류: {refinement_response.status_code} - {refinement_response.text}")
                        return result
                else:
                    self.logger.error(f"API 오류 (시도 {attempt+1}): {response.status_code} - {response.text}")
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"재시도 대기 중... ({wait_time}초)")
                        time.sleep(wait_time)
                        continue
                    
                    return "시장 분석 생성에 실패했습니다. 잠시 후 다시 시도해 주세요."
                    
            except requests.exceptions.Timeout:
                self.logger.error(f"API 타임아웃 (시도 {attempt+1})")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"타임아웃 발생, 재시도 중... ({wait_time}초)")
                    time.sleep(wait_time)
                else:
                    return "시장 분석 생성에 실패했습니다. 서버 응답이 지연되고 있습니다."
                    
            except Exception as e:
                self.logger.error(f"API 호출 오류 (시도 {attempt+1}): {e}", exc_info=True)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"오류 발생, 재시도 중... ({wait_time}초)")
                    time.sleep(wait_time)
                else:
                    return "시장 분석 생성에 실패했습니다. 시스템 오류가 발생했습니다."
        
        return "시장 분석 생성에 실패했습니다. 여러 번 시도했으나 응답을 받지 못했습니다."

    def _create_fallback_content(self, data: Dict = None) -> Dict:
        """분석 실패 시 대체 내용을 생성합니다."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if data:
            # 데이터가 있는 경우 이를 활용한 대체 내용 생성
            fallback_title = f"{current_date} 글로벌 시장 동향"
            
            fallback_commentary = f"""오늘의 시장 동향을 분석해보겠습니다.

주요 시장 지표:
"""
            if 'current_rate' in data:
                fallback_commentary += f"""
- 현재 환율: {data['current_rate']:.2f}원
"""
            if 'daily_change' in data:
                fallback_commentary += f"""
- 전일 대비 변동폭: {data['daily_change']:+.2f}%
"""
            if 'naver_news' in data:
                fallback_commentary += "\n주요 시장 뉴스:\n"
                for item in data['naver_news']:
                    fallback_commentary += f"- {item['title']}\n"
        else:
            # 데이터가 없는 경우 기본 대체 내용
            fallback_title = f"오늘의 시장 동향 분석 - {current_date}"
            fallback_commentary = "시스템 오류로 인해 분석을 완료하지 못했습니다. 잠시 후 다시 시도해 주시기 바랍니다."
        
        return {
            "title": fallback_title,
            "commentary": fallback_commentary
        }

    def _create_fallback_title(self, data: Dict) -> str:
        """분석 실패 시 대체 제목을 생성합니다."""
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        if 'current_rate' in data and 'daily_change' in data:
            return f"{current_date} 글로벌 시장: 환율 동향 분석"
        else:
            return f"{current_date} 글로벌 시장 동향"

    def analyze_market_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """시장 데이터를 분석합니다."""
        try:
            # 데이터 요약 출력 (확인 프롬프트 제거)
            print("\n처리된 데이터:\n")
            
            # Gainer 정보
            biggest_gainer = self._get_biggest_mover(market_data['gainers'], 'Change %', ascending=False)
            print("biggest_gainer:")
            print(f"- Name: {biggest_gainer['Name']}")
            print(f"- Symbol: {biggest_gainer['Symbol']}")
            print(f"- Price: {biggest_gainer['Price']}")
            print(f"- Change_Pct: +{abs(biggest_gainer['Change %']):.2f}\n")
            
            # Loser 정보
            biggest_loser = self._get_biggest_mover(market_data['losers'], 'Change %', ascending=True)
            print("biggest_loser:")
            print(f"- Name: {biggest_loser['Name']}")
            print(f"- Symbol: {biggest_loser['Symbol']}")
            print(f"- Price: {biggest_loser['Price']}")
            print(f"- Change_Pct: {biggest_loser['Change %']:.2f}\n")
            
            # Most Active 정보
            biggest_most_active = self._get_biggest_mover(market_data['most_active'], 'Change %', ascending=False)
            print("biggest_most_activ:")
            print(f"- Name: {biggest_most_active['Name']}")
            print(f"- Symbol: {biggest_most_active['Symbol']}")
            print(f"- Price: {biggest_most_active['Price']}")
            print(f"- Change_Pct: {biggest_most_active['Change %']:.2f}\n")
            
            print("시장 분석 진행 중...")
            
            # 분석 진행 (자동)
            analysis_data = {
                'biggest_gainer': biggest_gainer,
                'biggest_loser': biggest_loser,
                'biggest_most_active': biggest_most_active,
                'market_data': market_data
            }
            
            return analysis_data
            
        except Exception as e:
            self.logger.error(f"데이터 분석 중 오류 발생: {e}")
            return None

    def format_blog_content(self, content: str) -> str:
        """블로그 포스팅용으로 콘텐츠를 포맷팅합니다."""
        try:
            # 원본 콘텐츠를 그대로 반환
            return content.strip()
            
        except Exception as e:
            self.logger.error(f"Content formatting error: {e}")
            return content  # 에러 발생 시 원본 콘텐츠 반환

    def _create_tags_from_content(self, title: str, content: str) -> List[str]:
        """제목과 본문 내용을 기반으로 태그를 생성합니다."""
        try:
            # 기본 태그 세트
            base_tag_sets = {
                "주식": ["주식", "주식투자", "주식시장", "주식분석", "주식공부"],
                "시장": ["시장분석", "시장동향", "시장전망", "시장이슈", "시장리뷰"],
                "투자": ["투자", "투자전략", "투자분석", "투자이슈", "투자전망"],
                "경제": ["경제", "경제동향", "경제이슈", "경제전망", "글로벌경제"],
                "미국": ["미국주식", "미국시장", "미국경제", "나스닥", "S&P500", "다우존스"],
                "거시경제": ["거시경제", "금리", "인플레이션", "고용", "GDP", "무역", "관세", "정책"],
                "글로벌": ["글로벌시장", "글로벌경제", "국제무역", "환율", "원자재", "에너지"]
            }
            
            # 섹터/산업 키워드 세트
            sector_sets = {
                "테크": ["테크", "기술", "AI", "반도체", "소프트웨어", "하드웨어", "클라우드", "메타버스"],
                "금융": ["금융", "은행", "증권", "보험", "핀테크", "디지털금융"],
                "에너지": ["에너지", "석유", "가스", "재생에너지", "태양광", "풍력", "원자력"],
                "소비재": ["소비재", "유통", "식품", "의류", "화장품", "패션", "소매"],
                "헬스케어": ["헬스케어", "바이오", "제약", "의료", "건강", "의료기기"],
                "산업재": ["산업재", "제조", "자동차", "항공", "방위", "기계", "건설"],
                "유틸리티": ["유틸리티", "전기", "가스", "수도", "인프라"],
                "부동산": ["부동산", "REITs", "상업용부동산", "주거용부동산"],
                "통신": ["통신", "텔레콤", "5G", "인터넷", "미디어", "엔터테인먼트"],
                "재료": ["재료", "화학", "철강", "비철금속", "플라스틱"]
            }
            
            # 기본 태그 선택 (각 세트에서 랜덤하게 1-2개 선택)
            base_tags = []
            for tag_set in base_tag_sets.values():
                import random
                selected = random.sample(tag_set, min(2, len(tag_set)))
                base_tags.extend(selected)
            
            # 제목에서 키워드 추출 (특수문자 제거)
            title_keywords = []
            for word in title.split():
                # 특수문자 제거
                clean_word = ''.join(c for c in word if c.isalnum() or c.isspace())
                if len(clean_word) > 1:
                    title_keywords.append(clean_word)
            
            # 본문에서 주요 키워드 추출 (특수문자 제거)
            content_keywords = []
            for line in content.split('\n'):
                if ':' in line:  # 주요 지표나 종목 정보가 있는 줄
                    key = line.split(':')[0].strip()
                    # 특수문자 제거
                    clean_key = ''.join(c for c in key if c.isalnum() or c.isspace())
                    if len(clean_key) > 1:
                        content_keywords.append(clean_key)
                elif len(line.strip()) > 0:  # 일반 텍스트 줄
                    words = line.strip().split()
                    for word in words:
                        # 특수문자 제거
                        clean_word = ''.join(c for c in word if c.isalnum() or c.isspace())
                        if len(clean_word) > 1:
                            content_keywords.append(clean_word)
            
            # 거시경제 키워드 우선 추출
            macro_keywords = []
            macro_indicators = ["금리", "인플레이션", "고용", "GDP", "소비자물가", "생산자물가", 
                              "무역", "관세", "정책", "환율", "원자재", "에너지", "글로벌경제"]
            for indicator in macro_indicators:
                if any(indicator in word for word in title_keywords + content_keywords):
                    macro_keywords.append(indicator)
            
            # 종목 심볼 추출 (특수문자 제거)
            symbols = []
            for word in title_keywords + content_keywords:
                if word.isupper() and len(word) <= 5:  # 대문자로 된 5자 이하의 단어는 종목 심볼로 간주
                    symbols.append(word)
            
            # 섹터/산업 키워드 추출 (특수문자 제거)
            sector_keywords = []
            for word in title_keywords + content_keywords:
                for sector, indicators in sector_sets.items():
                    for indicator in indicators:
                        if indicator in word:
                            sector_keywords.append(indicator)
                            break
            
            # 최종 태그 구성 (특수문자 제거)
            final_tags = []
            # 거시경제 키워드를 우선적으로 추가
            final_tags.extend(macro_keywords)
            # 나머지 태그 추가
            for tag in (base_tags + symbols + sector_keywords):
                # 특수문자 제거
                clean_tag = ''.join(c for c in tag if c.isalnum() or c.isspace())
                if len(clean_tag) > 1:
                    final_tags.append(clean_tag)
            
            # 중복 제거 및 정렬
            final_tags = sorted(list(set(final_tags)))
            
            # 태그 개수 제한 (최대 15개)
            return final_tags[:15]
            
        except Exception as e:
            self.logger.error(f"태그 생성 중 오류 발생: {e}")
            # 오류 발생 시 기본 태그 세트에서 랜덤하게 선택 (특수문자 제거)
            import random
            base_tags = ["주식", "시장분석", "투자", "경제", "미국주식", "거시경제", "글로벌경제"]
            return random.sample(base_tags, 3)

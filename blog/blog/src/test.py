import os
from datetime import datetime
from blog_poster import NaverBlogPoster
from dotenv import load_dotenv
import yaml
from pathlib import Path
from typing import List
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

def load_config():
    """설정 파일을 로드합니다."""
    try:
        # 경로 수정: src의 상위 디렉토리에서 config 폴더 찾기
        current_dir = Path(__file__).parent.parent
        config_path = current_dir / 'config' / 'config.yaml'
        print(f"설정 파일 경로: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"설정 파일 로드 실패: {e}")
        # 기본 설정 반환
        return {
            'logging': {
                'file': 'logs/app.log',
                'level': 'INFO'
            },
            'blog': {
                'url': 'https://blog.naver.com/gongnyangi',
                'category': '오늘의 이슈'
            },
            'settings': {
                'auto_confirm': True,
                'auto_post': True
            }
        }

def create_test_content():
    """테스트용 블로그 콘텐츠를 생성합니다."""
    today = datetime.now().strftime('%Y년 %m월 %d일')
    
    test_content = f'''
📈 오늘의 시장 분석 ({today})

1. 주요 지수 동향
S&P 500: 4,783.45 (+1.2%)
나스닥: 14,843.77 (+0.9%)
다우존스: 32,654.32 (+0.7%)

2. 핵심 이슈
① 연준 금리 동결 가능성 상승
② 기업 실적 시즌 개막
③ 원자재 가격 상승세

3. 시장 영향
- 기술주 중심 상승세
- 금융주 혼조세
- 에너지 섹터 강세

4. 투자 전략
1) 단기: 변동성 확대 대비
2) 중기: 우량주 중심 포트폴리오 구성
3) 장기: 배당주 비중 확대 검토

※ 본 분석은 투자 참고 자료입니다.
'''
    
    return test_content

def main():
    """테스트 실행 함수"""
    try:
        print("\n=== 네이버 블로그 포스팅 테스트 시작 ===\n")
        
        # 환경 변수 로드
        load_dotenv()
        
        # 설정 로드
        config = load_config()
        
        # 테스트용 포스팅 정보
        title = f"테스트 포스팅 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        content = create_test_content()
        tags = ["테스트", "블로그", "자동화", "HTML", "포맷팅테스트"]
        
        # 블로그 포스터 초기화 (config 전달)
        poster = NaverBlogPoster(config)
        
        # 웹드라이버 설정
        print("- 웹드라이버 설정 중...")
        if not poster.setup_driver():
            print("✗ 웹드라이버 설정 실패")
            return
            
        # 로그인
        print("- 네이버 로그인 시도 중...")
        if not poster.login():
            print("✗ 로그인 실패")
            return
            
        # 포스팅 정보 출력
        print("\n포스팅 정보:")
        print(f"- 제목: {title}")
        print(f"- 태그: {', '.join(tags)}")
        print(f"- 본문 길이: {len(content)}자\n")
        
        # 포스팅 시도
        print("- 블로그 글 작성 및 발행 중...")
        if poster.create_post(title, content, tags):
            print("✓ 테스트 포스팅 성공!")
        else:
            print("✗ 테스트 포스팅 실패")
            
    except Exception as e:
        print(f"\n✗ 테스트 중 오류 발생: {str(e)}")
    finally:
        if 'poster' in locals():
            poster.close()
        
    print("\n=== 테스트 종료 ===")

if __name__ == "__main__":
    main()

import yaml
import logging
import os
from pathlib import Path
from data_collector import ExchangeRateCollector  # 클래스 이름 변경
from market_analyzer import ExchangeRateAnalyzer
from blog_poster import NaverBlogPoster
from datetime import datetime
import pytz
from utils import load_environment, setup_logging
import schedule
import time

# 한국 시간대 설정
KST = pytz.timezone('Asia/Seoul')

def get_kst_time():
    """현재 한국 시간을 반환합니다."""
    return datetime.now(KST)

def main():
    """메인 실행 함수"""
    # 함수 실행 전, 시간 먼저 확인
    now = get_kst_time()
    weekday = now.weekday() # Monday is 0, Sunday is 6
    hour = now.hour

    # 주말 실행 제외 로직 (토요일 10:00 ~ 월요일 05:00)
    if (weekday == 5 and hour >= 10) or weekday == 6 or (weekday == 0 and hour < 5):
        # 주말 휴식 시간에는 아무것도 하지 않고 조용히 종료
        return

    # --- 주말이 아닐 경우에만 아래 로직 실행 ---
    try:
        print("\n=== 환율 분석 및 블로그 포스팅 프로그램 시작 ===\n")
        print(f"현재 한국 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 환경 변수 로드
        if not load_environment():
            print("✗ 환경 변수 설정에 실패했습니다. 프로그램을 종료합니다.")
            return
        
        # 설정 파일 로드
        current_dir = Path(__file__).parent.parent
        config_path = current_dir / 'config' / 'config.yaml'
        
        if not config_path.exists():
            print(f"✗ 설정 파일을 찾을 수 없습니다: {config_path}")
            return
            
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 로깅 설정
        logger = setup_logging(config)
        logger.info("프로그램 초기화 완료")
        
        # 데이터 수집
        print("\n1. 환율 데이터 수집 시작...")
        collector = ExchangeRateCollector(config)
        exchange_data = collector.get_exchange_rate_data()
        exchange_news = collector.get_exchange_rate_news()
        
        if not exchange_data:
            print("✗ 오류: 환율 데이터 수집에 실패했습니다.")
            return
            
        if not exchange_news:
            print("✗ 경고: 뉴스 데이터 수집에 실패했습니다.")
        
        # 수집된 데이터 확인
        print("\n수집된 데이터 요약:")
        print(f"- 환율: {exchange_data['Close']:.2f}원 (변동: {exchange_data['Change']:+.2f}원, {exchange_data['ChangePercent']:+.2f}%)")
        print(f"- 네이버 뉴스: {len(exchange_news)}개 기사")
        
        # 환율 분석
        print("\n2. 환율 분석 시작...")
        analyzer = ExchangeRateAnalyzer(config)
        analysis = analyzer.analyze_market_trend(exchange_data, exchange_news)
        
        # 분석 결과 확인
        print("\n=== 분석 결과 ===")
        print(f"\n제목: {analysis.get('title', '제목 생성 실패')}")
        print("\n본문 미리보기:")
        content = analysis.get('commentary', '본문 생성 실패')
        preview = content[:500] + "..." if len(content) > 500 else content
        print(preview)
        
        # 블로그 포스팅
        print("\n3. 블로그 포스팅 시작...")
        poster = NaverBlogPoster(config)
        
        try:
            print("- 웹드라이버 설정 중...")
            if not poster.setup_driver():
                print("✗ 웹드라이버 설정에 실패했습니다.")
                return
                
            print("- 네이버 로그인 시도 중...")
            if poster.login():
                title = analysis['title']
                content = analysis['commentary']
                tags = analysis.get('tags', [])
                
                print(f"\n포스팅 정보:")
                print(f"- 제목: {title}")
                print(f"- 본문 길이: {len(content)}자")
                
                print("\n- 블로그 글 작성 및 발행 중...")
                success = poster.create_post(title, content, tags)
                if success:
                    print("✓ 블로그 포스팅 완료!")
                    logger.info(f"블로그 포스팅 성공: {title}")
                else:
                    print("✗ 블로그 포스팅 실패")
                    logger.error("블로그 포스팅 실패")
            else:
                print("✗ 네이버 로그인 실패")
                logger.error("네이버 로그인 실패")
        except Exception as e:
            print(f"✗ 블로그 포스팅 중 오류 발생: {str(e)}")
            logger.error(f"블로그 포스팅 중 오류: {str(e)}", exc_info=True)
        finally:
            poster.close()
        
    except Exception as e:
        print(f"\n✗ 오류 발생: {str(e)}")
        if 'logger' in locals():
            logger.error(f"프로그램 실행 중 오류 발생: {str(e)}", exc_info=True)
        else:
            print(f"로깅 초기화 전 오류 발생: {str(e)}")
    
    print("\n=== 프로그램 종료 ===")

if __name__ == "__main__":
    # 한국 시간 기준 3시간 간격으로 실행 (23:59, 02:59, 05:59, 08:59, 11:59, 14:59, 17:59, 20:59)
    schedule.every().day.at("23:58").do(main)
    schedule.every().day.at("02:58").do(main)
    schedule.every().day.at("05:58").do(main)
    schedule.every().day.at("08:58").do(main)
    schedule.every().day.at("11:58").do(main)
    schedule.every().day.at("14:58").do(main)
    schedule.every().day.at("17:58").do(main)
    schedule.every().day.at("20:58").do(main)
    
    print(f"스케줄러 설정 완료. 매일 한국 시간 기준 3시간 간격으로 자동 실행됩니다.")
    print(f"현재 한국 시간: {get_kst_time().strftime('%Y-%m-%d %H:%M:%S')}")
    
    while True:
        schedule.run_pending()
        time.sleep(60)
    # main()  # 테스트용 직접 실행 주석 처리
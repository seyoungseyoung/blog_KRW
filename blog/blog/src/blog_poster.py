from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging
import os
import time
import pickle
from pathlib import Path
from typing import List
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from datetime import datetime
from selenium.webdriver.common.action_chains import ActionChains

class NaverBlogPoster:
    def __init__(self, config: dict):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.username = os.getenv('NAVER_USERNAME')
        self.password = os.getenv('NAVER_PASSWORD')
        self.driver = None
        self.cookies_file = Path(__file__).parent.parent / 'config' / 'naver_cookies.pkl'
        
        if not self.username or not self.password:
            self.logger.error("Naver credentials not found in environment variables")
            raise ValueError("네이버 로그인 정보가 환경변수에 설정되지 않았습니다.")

    def setup_driver(self):
        """Selenium WebDriver를 초기화합니다."""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--no-sandbox')
            options.add_argument('--start-maximized')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # User-Agent 설정
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36')
            
            # ChromeDriver 경로 직접 지정
            chromedriver_path = Path(__file__).parent / 'chromedriver' / 'chromedriver-win64' / 'chromedriver.exe'
            service = Service(executable_path=str(chromedriver_path))
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(30)
            
            # JavaScript 코드 실행하여 웹드라이버 감지 방지
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}", exc_info=True)
            print(f"✗ 웹드라이버 설정 실패: {str(e)}")
            return False

    def login(self):
        """네이버에 로그인합니다."""
        try:
            # 네이버 로그인 페이지로 이동
            self.driver.get('https://nid.naver.com/nidlogin.login')
            time.sleep(2)
            
            # JavaScript를 통한 로그인 정보 입력
            self.driver.execute_script(
                f"document.getElementsByName('id')[0].value='{self.username}'")
            time.sleep(0.5)
            
            self.driver.execute_script(
                f"document.getElementsByName('pw')[0].value='{self.password}'")
            time.sleep(0.5)
            
            # 로그인 버튼 클릭
            login_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.CLASS_NAME, 'btn_login'))
            )
            login_button.click()
            
            # 로그인 성공 확인
            try:
                WebDriverWait(self.driver, 5).until(
                    lambda d: 'nid.naver.com/nidlogin.login' not in d.current_url
                )
                print("✓ 네이버 로그인 성공")
                return True
            except TimeoutException:
                print("✗ 로그인 실패: 아이디 또는 비밀번호를 확인해주세요.")
                return False
                
        except Exception as e:
            self.logger.error(f"Login failed: {e}", exc_info=True)
            print(f"✗ 로그인 실패: {str(e)}")
            return False

    def check_login_status(self):
        """현재 로그인 상태를 확인합니다."""
        try:
            self.driver.get('https://blog.naver.com/gongnyangi')
            time.sleep(2)
            
            # 로그인 버튼이 있는지 확인
            login_buttons = self.driver.find_elements(By.CLASS_NAME, 'log_btn')
            return len(login_buttons) == 0
            
        except Exception:
            return False

    def generate_market_tags(self, title: str, content: str) -> List[str]:
        """글의 내용에 따라 적절한 태그를 생성합니다."""
        # 기본 태그 (항상 포함)
        base_tags = [
            "주식시장", "증권", "주식투자", "미국주식", "글로벌경제",
            "시장분석", "투자정보", "주식정보", "시장동향", "금융시장"
        ]
        
        # 시장 상황별 태그
        market_condition_tags = {
            "상승": ["주식상승", "매수전략", "상승장", "강세장", "매수기회"],
            "하락": ["주식하락", "매도전략", "하락장", "약세장", "리스크관리"],
            "변동성": ["변동성장세", "리스크관리", "투자전략", "자산관리", "포트폴리오"]
        }
        
        # 자산군 태그
        asset_tags = {
            "주식": ["개별주식", "성장주", "가치주", "배당주", "기술주"],
            "원자재": ["원자재", "금", "은", "원유", "commodities"],
            "채권": ["채권", "국채", "회사채", "금리", "채권투자"],
            "환율": ["환율", "달러", "외환시장", "달러인덱스", "외환"]
        }
        
        # 글의 내용에서 키워드 분석
        content_lower = content.lower()
        selected_tags = set(base_tags)  # 중복 방지를 위해 set 사용
        
        # 시장 상황 태그 추가
        if any(word in content_lower for word in ["상승", "급등", "강세", "매수"]):
            selected_tags.update(market_condition_tags["상승"])
        if any(word in content_lower for word in ["하락", "급락", "약세", "매도"]):
            selected_tags.update(market_condition_tags["하락"])
        if any(word in content_lower for word in ["변동성", "불확실성", "리스크"]):
            selected_tags.update(market_condition_tags["변동성"])
        
        # 자산군 태그 추가
        for asset_type, tags in asset_tags.items():
            if asset_type.lower() in content_lower:
                selected_tags.update(tags)
        
        # 현재 날짜 태그 추가
        today = datetime.now()
        date_tags = [
            today.strftime("%Y년%m월"),
            today.strftime("%Y년%m월%d일"),
            "데일리브리핑",
            "시장브리핑"
        ]
        selected_tags.update(date_tags)
        
        # 태그 리스트로 변환 및 최대 30개로 제한
        final_tags = list(selected_tags)[:30]
        return final_tags

    def format_blog_content(self, content: str) -> str:
        """블로그 포스팅용으로 콘텐츠를 포맷팅합니다."""
        try:
            # 문단을 나누고 포맷팅
            paragraphs = content.split('\n\n')
            formatted_content = []
            
            for para in paragraphs:
                if para.strip():
                    # 소제목 처리 (숫자로 시작하거나 특수문자로 시작하는 경우)
                    if any(para.strip().startswith(prefix) for prefix in ['1.', '2.', '3.', '#', '■', '▶']):
                        formatted_content.append(f'<h2 style="font-size: 1.5em; color: #333; margin: 30px 0 15px 0; border-bottom: 2px solid #f0f0f0; padding-bottom: 10px;">{para.strip()}</h2>')
                    
                    # 중요 문구 강조 (따옴표 안의 내용)
                    elif para.strip().startswith('"') and para.strip().endswith('"'):
                        formatted_content.append(f'<blockquote style="font-size: 1.1em; color: #666; margin: 20px 0; padding: 15px; background: #f9f9f9; border-left: 4px solid #0068c3;">{para.strip()}</blockquote>')
                    
                    # 일반 문단
                    else:
                        # 볼드 처리된 텍스트 유지 (**text**)
                        para = para.replace('**', '<strong style="color: #0068c3;">')
                        para = para.replace('**', '</strong>', 1)
                        formatted_content.append(f'<p style="font-size: 1.1em; line-height: 1.8; margin: 15px 0; color: #333;">{para.strip()}</p>')

            # 구분선 추가
            divider = '<hr style="border: 0; height: 1px; background: #eee; margin: 30px 0;">'
            
            # 헤더 추가
            header = f'''
            <div style="background: #f8f9fa; padding: 20px; margin-bottom: 30px; border-radius: 5px;">
                <h1 style="font-size: 1.8em; color: #1a1a1a; margin-bottom: 15px;">📈 오늘의 시장 분석</h1>
                <p style="color: #666; font-size: 1.1em;">작성일: {datetime.now().strftime('%Y년 %m월 %d일')}</p>
            </div>
            '''
            
            # 푸터 추가
            footer = f'''
            <div style="background: #f8f9fa; padding: 20px; margin-top: 30px; border-radius: 5px;">
                <p style="color: #666; font-size: 0.9em; margin: 0;">
                    ※ 본 분석은 투자 권유가 아닌 정보 제공을 목적으로 합니다.<br>
                    ※ 투자는 투자자 본인의 판단과 책임하에 진행하시기 바랍니다.
                </p>
            </div>
            '''
            
            # 최종 콘텐츠 조합
            final_content = header + '\n'.join(formatted_content) + footer
            return final_content
            
        except Exception as e:
            self.logger.error(f"Content formatting error: {e}")
            return content  # 에러 발생 시 원본 콘텐츠 반환

    def create_post(self, title: str, content: str, tags: List[str] = None) -> bool:
        """블로그 포스트를 작성합니다."""
        try:
            # 글쓰기 페이지로 이동
            self.driver.get("https://blog.naver.com/gongnyangi/postwrite")
            time.sleep(5)
            
            print(f"현재 URL: {self.driver.current_url}")
            
            # 페이지 및 팝업 로드를 위한 충분한 대기 시간
            time.sleep(3)
            
            # 이전 글 작성 확인 팝업이 있는지 확인하고 처리 (최우선)
            try:
                # 팝업 확인 (명시적 대기 없이 빠르게 확인)
                cancel_buttons = self.driver.find_elements(By.CLASS_NAME, 'se-popup-button-text')
                if cancel_buttons:
                    for button in cancel_buttons:
                        if button.text == '취소':
                            button.click()
                            time.sleep(2)
                            print("- 이전 글 취소 처리 완료")
                            break
            except Exception as e:
                print("이전 글 팝업 없음 - 계속 진행")
            
            # 도움말 닫기 버튼이 있다면 클릭
            try:
                help_buttons = self.driver.find_elements(By.TAG_NAME, 'button')
                for button in help_buttons:
                    try:
                        if button.get_attribute('class') and '닫기' in button.get_attribute('class'):
                            button.click()
                            time.sleep(1)
                            print("- 도움말 닫기 완료")
                            break
                    except:
                        continue
            except Exception as e:
                print("도움말 팝업 없음 - 계속 진행")
            
            # 제목 입력 (새로운 방식)
            try:
                # 제목 영역 찾기 시도 1: placeholder로 찾기
                title_area = None
                try:
                    title_area = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'span.se-placeholder.__se_placeholder.se-ff-nanumgothic.se-fs32'))
                    )
                except:
                    print("제목 영역을 placeholder로 찾지 못함 - 다른 방법 시도")
                
                # 제목 영역 찾기 시도 2: 직접 클래스로 찾기
                if not title_area:
                    try:
                        title_area = self.driver.find_element(By.CSS_SELECTOR, 'span.se-ff-nanumgothic.se-fs32.__se-node')
                    except:
                        print("제목 영역을 클래스로 찾지 못함")
                
                if not title_area:
                    print("제목 영역을 찾을 수 없습니다")
                    return False
                
                # 제목 영역 클릭 및 입력
                title_area.click()
                time.sleep(1)
                
                # 제목 입력
                actions = ActionChains(self.driver)
                actions.send_keys(title).perform()
                print("- 제목 입력 완료")
                time.sleep(1)
                
                # Enter 키를 눌러 본문 영역으로 이동
                actions.send_keys(Keys.ENTER).perform()
                time.sleep(1)
                
            except Exception as e:
                print(f"제목 입력 실패: {e}")
                return False
            
            # 본문 입력
            try:
                # 본문 입력 (Tab으로 이동했으므로 바로 입력 가능)
                actions = ActionChains(self.driver)
                # 본문을 그대로 입력
                actions.send_keys(content.strip())  # 앞뒤 공백만 제거하고 그대로 입력
                actions.perform()
                print("- 본문 입력 완료")
                time.sleep(2)
            except Exception as e:
                print(f"본문 입력 실패: {e}")
                return False
            
            # 첫 번째 발행 버튼 클릭
            time.sleep(3)
            try:
                publish_script = """
                    var publishBtn = document.querySelector('button.publish_btn__m9KHH');
                    if (publishBtn) {
                        publishBtn.click();
                        return true;
                    }
                    return false;
                """
                if self.driver.execute_script(publish_script):
                    print("- 첫 번째 발행 버튼 클릭 완료")
                    time.sleep(3)
                    
                    # 카테고리 선택
                    try:
                        # 도움말 이미지 닫기
                        try:
                            help_image = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, 'img.se-help-carousel-image'))
                            )
                            # JavaScript로 도움말 이미지 숨기기
                            self.driver.execute_script("""
                                var helpImage = document.querySelector('img.se-help-carousel-image');
                                if (helpImage) {
                                    helpImage.style.display = 'none';
                                }
                            """)
                            print("- 도움말 이미지 숨김 처리 완료")
                            time.sleep(2)
                        except:
                            print("도움말 이미지 없음 - 계속 진행")
                        
                        # 카테고리 목록 버튼 클릭
                        category_button = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'button.selectbox_button__jb1Dt'))
                        )
                        # JavaScript로 클릭
                        self.driver.execute_script("arguments[0].click();", category_button)
                        print("- 카테고리 목록 버튼 클릭 완료")
                        time.sleep(2)
                        
                        # 출퇴근 환율분석 카테고리 선택
                        category_label = WebDriverWait(self.driver, 10).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, 'label[for="15_출퇴근 환율분석"]'))
                        )
                        # JavaScript로 클릭
                        self.driver.execute_script("arguments[0].click();", category_label)
                        print("- 출퇴근 환율분석 카테고리 선택 완료")
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"카테고리 선택 실패: {e}")
                        return False
                    
                    # 태그 입력
                    if tags:
                        try:
                            for tag in tags:
                                tag_input = WebDriverWait(self.driver, 10).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, 'input#tag-input.tag_input__rvUB5'))
                                )
                                tag_input.clear()  # 기존 입력값 제거
                                tag_input.send_keys(tag)
                                time.sleep(0.5)
                                tag_input.send_keys(Keys.ENTER)
                                time.sleep(1)
                                print(f"- 태그 입력 완료: {tag}")
                            print("- 모든 태그 입력 완료")
                            time.sleep(2)
                        except Exception as e:
                            print(f"태그 입력 실패: {e}")
                    
                    # 최종 발행 버튼 클릭 (정확한 선택자 사용)
                    final_publish_script = """
                        var finalBtn = document.querySelector('button.confirm_btn__WEaBq[data-testid="seOnePublishBtn"]');
                        if (finalBtn) {
                            finalBtn.click();
                            return true;
                        }
                        return false;
                    """
                    if self.driver.execute_script(final_publish_script):
                        print("- 최종 발행 버튼 클릭 완료")
                        time.sleep(3)
                        return True
                    else:
                        print("최종 발행 버튼을 찾을 수 없습니다")
                        return False
                    
            except Exception as e:
                print(f"발행 과정 실패: {e}")
                return False
            
        except Exception as e:
            print(f"포스팅 실패: {e}")
            return False

    def manual_login(self) -> bool:
        """자동으로 로그인을 진행합니다."""
        try:
            # 로그인 시도
            return self.login()
        except Exception as e:
            self.logger.error(f"로그인 실패: {e}")
            return False

    def close(self):
        """WebDriver를 종료합니다."""
        if self.driver:
            try:
                self.driver.quit()
                print("- 웹드라이버 종료 완료")
            except WebDriverException as e:
                self.logger.warning(f"WebDriver close error: {e}")

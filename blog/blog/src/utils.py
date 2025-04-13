import os
import logging
from pathlib import Path
from dotenv import load_dotenv

def load_environment():
    """환경 변수를 로드하고 필요한 API 키가 있는지 확인합니다."""
    # 현재 스크립트 위치 기준으로 .env 파일 경로 설정
    current_dir = Path(__file__).parent.parent
    env_path = current_dir / '.env'
    
    # .env 파일 존재 확인
    if not env_path.exists():
        print(f"✗ Error: .env 파일을 찾을 수 없습니다. 경로: {env_path}")
        return False
        
    # .env 파일 로드
    load_dotenv(env_path)
    
    # 필수 환경변수 확인
    required_vars = ['DEEPSEEK_API_KEY', 'NAVER_USERNAME', 'NAVER_PASSWORD']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"✗ Error: 다음 환경변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
        return False
    
    return True

def setup_logging(config):
    """로깅 설정을 초기화합니다."""
    log_dir = Path(config['logging']['file']).parent
    log_dir.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config['logging']['file'], encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

def parse_price_string(price_str):
    """가격 문자열에서 가격과 변화율을 추출합니다.
    예: "92.17 -2.14 (-2.27%)" -> (92.17, -2.27)
    """
    try:
        parts = price_str.split()
        price = float(parts[0])
        
        # 변화율 추출
        for part in parts:
            if '%' in part:
                change_pct = part.strip('()%')
                return price, change_pct
                
        # 변화율을 찾지 못한 경우
        return price, '0'
    except Exception as e:
        logging.error(f"Error parsing price string '{price_str}': {e}")
        return 0.0, '0'

def confirm_action(message: str) -> bool:
    """사용자 확인을 항상 True로 반환합니다."""
    return True

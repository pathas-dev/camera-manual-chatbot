"""
텔레그램 봇 설정 및 공통 상수
"""

import os
import logging
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 환경변수
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")

# 대화 상태 상수
CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)

# 키보드 레이아웃
reply_keyboard_models = [
    ["X-T30", "Z5II", "D-LUX7"],
]

reply_keyboard_commands = [
    ["DONE"],
]

reply_markup_models = ReplyKeyboardMarkup(
    reply_keyboard_models, one_time_keyboard=True, resize_keyboard=True
)

reply_markup_commands = ReplyKeyboardMarkup(
    reply_keyboard_commands, one_time_keyboard=True, resize_keyboard=True
)

# 지원하는 카메라 모델
SUPPORTED_MODELS = ["X-T30", "Z5II", "D-LUX7"]

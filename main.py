# Copilot이 생성한 코드
# filepath: c:\Users\pathas\project\by_python\camera_manual_bot\main.py
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv, dotenv_values
import uvicorn
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# 텔레그램 봇 토큰 가져오기
BOT_TOKEN = dotenv_values().get("BOT_TOKEN")
WEBHOOK_URL = dotenv_values().get(
    "WEBHOOK_URL", ""
)  # 예: https://your-domain.com/webhook

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")

# 전역 변수
telegram_app: Optional[Application] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 앱의 시작과 종료 시 실행되는 컨텍스트 매니저"""
    global telegram_app

    # 시작 시 텔레그램 봇 초기화
    logger.info("텔레그램 봇 초기화 중...")
    telegram_app = Application.builder().token(BOT_TOKEN).build()

    # 핸들러 등록
    telegram_app.add_handler(CommandHandler("start", start_command))
    telegram_app.add_handler(CommandHandler("help", help_command))
    telegram_app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    # 봇 초기화
    await telegram_app.initialize()
    await telegram_app.start()

    # 웹훅 설정 (선택사항)
    if WEBHOOK_URL:
        await telegram_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
        logger.info(f"웹훅 설정 완료: {WEBHOOK_URL}/webhook")

    logger.info("텔레그램 봇 시작 완료")

    yield

    # 종료 시 정리
    logger.info("텔레그램 봇 종료 중...")
    if telegram_app:
        await telegram_app.stop()
        await telegram_app.shutdown()
    logger.info("텔레그램 봇 종료 완료")


# FastAPI 앱 생성
app = FastAPI(
    title="Camera Manual Bot",
    description="카메라 매뉴얼 텔레그램 봇 API",
    version="1.0.0",
    lifespan=lifespan,
)


async def start_command(update: Update, context) -> None:
    """'/start' 명령어 처리"""
    user = update.effective_user
    welcome_message = (
        f"안녕하세요 {user.mention_html()}님! 👋\n\n"
        "카메라 매뉴얼 봇에 오신 것을 환영합니다!\n"
        "/help 명령어로 사용법을 확인하세요."
    )
    await update.message.reply_html(welcome_message)


async def help_command(update: Update, context) -> None:
    """'/help' 명령어 처리"""
    help_text = (
        "📸 <b>카메라 매뉴얼 봇 사용법</b>\n\n"
        "🔹 /start - 봇 시작\n"
        "🔹 /help - 도움말 보기\n"
        "🔹 텍스트 메시지 - 카메라 관련 질문하기\n\n"
        "질문이나 카메라 모델명을 보내주시면 도움을 드리겠습니다!"
    )
    await update.message.reply_html(help_text)


async def handle_message(update: Update, context) -> None:
    """일반 메시지 처리"""
    user_message = update.message.text
    user_name = update.effective_user.first_name

    logger.info(f"메시지 수신 - 사용자: {user_name}, 내용: {user_message}")

    # 간단한 응답 로직 (향후 AI 기능 추가 가능)
    response = f"안녕하세요 {user_name}님! 📸\n\n'{user_message}'에 대한 답변을 준비 중입니다.\n현재는 기본 응답만 제공됩니다."

    await update.message.reply_text(response)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Camera Manual Bot API",
        "status": "running",
        "bot_info": "Telegram bot for camera manuals",
    }


@app.post("/webhook")
async def webhook(request: Request):
    """텔레그램 웹훅 엔드포인트"""
    if not telegram_app:
        raise HTTPException(status_code=503, detail="봇이 초기화되지 않았습니다")

    try:
        # 웹훅 데이터 파싱
        data = await request.json()
        update = Update.de_json(data, telegram_app.bot)

        # 업데이트 처리
        await telegram_app.process_update(update)

        return {"status": "ok"}
    except Exception as e:
        logger.error(f"웹훅 처리 오류: {e}")
        raise HTTPException(status_code=400, detail="웹훅 처리 실패")


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "bot_status": "running" if telegram_app else "not_initialized",
    }


def main():
    """메인 함수 - uvicorn 서버 시작"""
    logger.info("카메라 매뉴얼 봇 서버 시작...")

    # 개발 환경 설정
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    uvicorn.run("main:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    main()

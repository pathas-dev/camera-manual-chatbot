"""
개발용 스크립트 - 텔레그램 봇 로컬 실행
웹훅 없이 롱 폴링 방식으로 봇을 실행합니다.
"""

import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters


# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN 환경변수가 설정되지 않았습니다.")


async def start_command(update: Update, context) -> None:
    """'/start' 명령어 처리"""

    if not update.message:
        logger.warning("업데이트에 메시지가 없습니다.")
        return

    if not update.effective_user:
        logger.warning("업데이트에 사용자 정보가 없습니다.")
        return

    user = update.effective_user
    welcome_message = (
        f"안녕하세요 {user.mention_html()}님! 👋\n\n"
        "카메라 매뉴얼 봇에 오신 것을 환영합니다!\n"
        "/help 명령어로 사용법을 확인하세요."
    )

    await update.message.reply_html(welcome_message)


async def help_command(update: Update, context) -> None:
    """'/help' 명령어 처리"""
    if not update.message:
        logger.warning("업데이트에 메시지가 없습니다.")
        return

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
    if not update.message:
        logger.warning("업데이트에 메시지가 없습니다.")
        return

    if not update.effective_user:
        logger.warning("업데이트에 사용자 정보가 없습니다.")
        return

    user_message = update.message.text
    user_name = update.effective_user.first_name

    logger.info(f"메시지 수신 - 사용자: {user_name}, 내용: {user_message}")

    response = f"안녕하세요 {user_name}님! 📸\n\n'{user_message}'에 대한 답변을 준비 중입니다.\n현재는 기본 응답만 제공됩니다."

    await update.message.reply_text(response)


def main() -> None:
    """메인 함수 - 롱 폴링 방식으로 봇 실행"""
    logger.info("카메라 매뉴얼 봇 시작 (롱 폴링 모드)...")

    if not BOT_TOKEN:
        return logger.error("BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # 핸들러 등록
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    try:
        # 업데이터 시작
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except KeyboardInterrupt:
        logger.info("봇 종료 중...")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
    finally:
        logger.info("봇 종료 완료")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("프로그램 종료")

"""
개발용 스크립트 - 텔레그램 봇 로컬 실행
웹훅 없이 롱 폴링 방식으로 봇을 실행합니다.
"""

import os
import logging
import pprint
from dotenv import load_dotenv
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import re


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


CHOOSING, TYPING_REPLY, TYPING_CHOICE = range(3)


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
        f"안녕하세요 {user.name}님! 👋\n\n"
        "카메라 매뉴얼 봇에 오신 것을 환영합니다!\n"
        "/help 명령어로 사용법을 확인하세요."
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup_models)


async def help_command(update: Update, context) -> None:
    """'/help' 명령어 처리"""
    if not update.message:
        logger.warning("업데이트에 메시지가 없습니다.")
        return

    help_text = (
        "📸 <b>카메라 매뉴얼 봇 사용법</b>\n\n"
        "🔹 /start - 봇 시작\n"
        "🔹 /help - 도움말 보기\n"
        "🔹 /manual - 설명서 검색\n\n"
        "/manual 명령어로 시작해 주세요!"
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


async def start_manual_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Start the conversation and ask user for input."""
    if not update.message or not update.effective_user:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return ConversationHandler.END

    await update.message.reply_text(
        "다음 카메라 모델 중 하나를 선택해주세요:\n",
        reply_markup=reply_markup_models,
    )

    return CHOOSING


async def camera_model_choice(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Ask the user for info about the selected predefined choice."""
    if not update.message or context.user_data is None:
        logger.warning("메시지가 없습니다.")
        return TYPING_CHOICE

    model = update.message.text

    context.user_data.update({"choice": model})

    await update.message.reply_text(f"{model}의 어떤 점에 대해 알고 싶으신가요?")

    return TYPING_REPLY


async def handle_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ask the user for a description of a custom category."""
    if not update.message or not update.effective_user:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return TYPING_CHOICE

    await update.message.reply_text(
        "X-T30, Z5II, D-LUX7 중 하나를 선택하세요.\n",
        reply_markup=reply_markup_models,
    )

    return CHOOSING


def facts_to_str(user_data: dict[str, str]) -> str:
    """Helper function for formatting the gathered user info."""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])


async def query_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store info provided by user and ask for the next category."""

    if not update.message or not context.user_data:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return TYPING_CHOICE

    query = update.message.text
    model = context.user_data["choice"]

    help_text = (
        f"📸 ~~{model}에 대한 질문을 받았습니다: {query}\n\n"
        "🔹 더 궁금한 게 있으신가요?\n"
        "🔹 'DONE' 을 선택해서 대화를 종료할 수 있습니다.\n"
    )

    # TODO 여기서 모델에 맞는 매뉴얼 조회해서 결과 리턴
    await update.message.reply_html(
        help_text,
        reply_markup=reply_markup_commands,
    )

    return TYPING_REPLY


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display the gathered info and end the conversation."""

    if not update.message or not context.user_data:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return ConversationHandler.END

    user_data = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    await update.message.reply_text(
        f"🤖 대화가 종료되었습니다! ",
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


def main() -> None:
    """메인 함수 - 롱 폴링 방식으로 봇 실행"""
    logger.info("카메라 매뉴얼 봇 시작 (롱 폴링 모드)...")

    if not BOT_TOKEN:
        return logger.error("BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    # 핸들러 등록
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("done", done))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("manual", start_manual_conversation)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex(re.compile(r"^(X-T30|Z5II|D-LUX7)$", re.IGNORECASE)),
                    camera_model_choice,
                ),
                MessageHandler(filters.Regex("^Something else...$"), handle_fallback),
            ],
            TYPING_CHOICE: [
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
                    camera_model_choice,
                )
            ],
            TYPING_REPLY: [
                MessageHandler(
                    filters.Regex(
                        re.compile(r"^Done$", re.IGNORECASE),
                    ),
                    done,
                ),
                MessageHandler(
                    filters.TEXT & ~(filters.COMMAND | filters.Regex("^Done$")),
                    query_manual,
                ),
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Done$"), done)],
    )

    application.add_handler(conv_handler)

    try:
        # 업데이터 시작
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
        )

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

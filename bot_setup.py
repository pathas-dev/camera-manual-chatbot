"""
텔레그램 봇 설정 및 핸들러 등록
"""

import re
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
)

from bot_config import (
    BOT_TOKEN,
    CHOOSING,
    TYPING_CHOICE,
    TYPING_REPLY,
    SUPPORTED_MODELS,
)
from handlers import (
    start_command,
    help_command,
    handle_message,
    start_manual_conversation,
    camera_model_choice,
    handle_fallback,
    query_manual,
    done,
)


def create_bot_application() -> Application:
    """텔레그램 봇 애플리케이션 생성 및 핸들러 등록"""
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN이 설정되지 않았습니다.")

    application = Application.builder().token(BOT_TOKEN).build()

    # 기본 명령어 핸들러
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("done", done))

    # 대화형 핸들러 (매뉴얼 검색)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("manual", start_manual_conversation)],
        states={
            CHOOSING: [
                MessageHandler(
                    filters.Regex(
                        re.compile(rf"^({'|'.join(SUPPORTED_MODELS)})$", re.IGNORECASE)
                    ),
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
                    filters.Regex(re.compile(r"^Done$", re.IGNORECASE)),
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

    # 일반 메시지 핸들러 (가장 마지막에 등록)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    return application

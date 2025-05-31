"""
텔레그램 봇 핸들러 함수들
"""

import re
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from bot_config import (
    logger,
    reply_markup_models,
    reply_markup_commands,
    CHOOSING,
    TYPING_REPLY,
    TYPING_CHOICE,
    SUPPORTED_MODELS,
)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'/start' 명령어 처리"""
    if not update.message or not update.effective_user:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return

    user = update.effective_user
    welcome_message = (
        f"안녕하세요 {user.name}님! 👋\n\n"
        "카메라 매뉴얼 봇에 오신 것을 환영합니다!\n"
        "/help 명령어로 사용법을 확인하세요."
    )

    await update.message.reply_text(welcome_message, reply_markup=reply_markup_models)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """일반 메시지 처리"""
    if not update.message or not update.effective_user:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return

    user_message = update.message.text
    user_name = update.effective_user.first_name

    logger.info(f"메시지 수신 - 사용자: {user_name}, 내용: {user_message}")

    response = (
        f"안녕하세요 {user_name}님! 📸\n\n"
        f"'{user_message}'에 대한 답변을 준비 중입니다.\n"
        "현재는 기본 응답만 제공됩니다."
    )

    await update.message.reply_text(response)


async def start_manual_conversation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """매뉴얼 검색 대화 시작"""
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
    """카메라 모델 선택 처리"""
    if not update.message or context.user_data is None:
        logger.warning("메시지나 사용자 데이터가 없습니다.")
        return TYPING_CHOICE

    model = update.message.text

    # 지원하는 모델인지 확인
    if model not in SUPPORTED_MODELS:
        await update.message.reply_text(
            f"지원하지 않는 모델입니다. {', '.join(SUPPORTED_MODELS)} 중에서 선택해주세요.",
            reply_markup=reply_markup_models,
        )
        return CHOOSING

    context.user_data.update({"choice": model})

    await update.message.reply_text(f"{model}의 어떤 점에 대해 알고 싶으신가요?")

    return TYPING_REPLY


async def handle_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """잘못된 입력 처리"""
    if not update.message or not update.effective_user:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return TYPING_CHOICE

    await update.message.reply_text(
        f"{', '.join(SUPPORTED_MODELS)} 중 하나를 선택하세요.\n",
        reply_markup=reply_markup_models,
    )

    return CHOOSING


async def query_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """매뉴얼 질문 처리"""
    if not update.message or not context.user_data:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return TYPING_CHOICE

    query = update.message.text
    model = context.user_data.get("choice", "Unknown")

    help_text = (
        f"📸 {model}에 대한 질문을 받았습니다: {query}\n\n"
        "🔹 더 궁금한 게 있으신가요?\n"
        "🔹 'DONE'을 선택해서 대화를 종료할 수 있습니다.\n"
    )

    # TODO: 실제 매뉴얼 검색 로직 구현
    await update.message.reply_html(
        help_text,
        reply_markup=reply_markup_commands,
    )

    return TYPING_REPLY


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """대화 종료"""
    if not update.message or not context.user_data:
        logger.warning("업데이트에 메시지나 사용자 정보가 없습니다.")
        return ConversationHandler.END

    user_data = context.user_data
    if "choice" in user_data:
        del user_data["choice"]

    await update.message.reply_text(
        "🤖 대화가 종료되었습니다!",
        reply_markup=ReplyKeyboardRemove(),
    )

    user_data.clear()
    return ConversationHandler.END


def facts_to_str(user_data: dict[str, str]) -> str:
    """사용자 데이터 포맷팅 헬퍼 함수"""
    facts = [f"{key} - {value}" for key, value in user_data.items()]
    return "\n".join(facts).join(["\n", "\n"])

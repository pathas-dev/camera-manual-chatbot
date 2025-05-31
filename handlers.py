"""
텔레그램 봇 핸들러 함수들
"""

from langchain_ollama import OllamaEmbeddings
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from langchain_community.vectorstores import FAISS
from bot_config import (
    logger,
    reply_markup_models,
    reply_markup_commands,
    CHOOSING,
    TYPING_REPLY,
    TYPING_CHOICE,
    SUPPORTED_MODELS,
)

FAISS_INDEX_PATH = "faiss_ai_sample_index"


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

    if not query or not model:
        await update.message.reply_text(
            "질문이 비어있거나 모델이 선택되지 않았습니다. 다시 시도해주세요.",
            reply_markup=reply_markup_models,
        )
        return TYPING_CHOICE

    embeddings_ollama = OllamaEmbeddings(model="bge-m3")
    local_faiss = FAISS.load_local(
        FAISS_INDEX_PATH,
        embeddings_ollama,
        allow_dangerous_deserialization=True,
    )

    retriever = local_faiss.as_retriever(
        search_kwargs={"k": 1, "temperature": 0.1, "filter": {"model": model}}
    )

    docs = retriever.invoke(query)

    formatted_docs = []

    for i, (doc) in enumerate(docs):
        metadata = doc.metadata if hasattr(doc, "metadata") else {}

        source_info = []

        if "model" in metadata:
            source_info.append(f"모델: {metadata['model']}")

        if "page_no" in metadata:
            source_info.append(f"페이지: {metadata['page_no']}")

        if len(source_info) > 0:
            formatted_docs.append(
                f"📚 참고 페이지 {metadata['page_no']}\n"
                f"• {' | '.join(source_info) if source_info else '출처 정보 없음'}\n"
                # f"• 내용: {doc.page_content[:100]}{'...' if len(doc.page_content) > 100 else ''}"
            )

    result = ""
    for i, doc in enumerate(docs):
        result += "<code>\n"
        result += f">> {doc.page_content}\n\n"
        result += f"{formatted_docs[i]}"
        result += "</code>"

    help_text = (
        f"🔍 {model}: {query}\n\n"
        "🔹 <b>검색 결과</b>:\n"
        f"{result}\n\n"
        "🔹 더 궁금한 게 있으신가요?\n"
        "🔹 'DONE'을 선택해서 대화를 종료할 수 있습니다.\n"
    )

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

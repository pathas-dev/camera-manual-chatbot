"""
텔레그램 봇 핸들러 함수들
"""

import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from pinecone import Pinecone, ServerlessSpec
from telegram import ReplyKeyboardRemove, Update
from telegram.ext import ContextTypes, ConversationHandler

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from bot_config import (
    logger,
    reply_markup_models,
    reply_markup_commands,
    CHOOSING,
    TYPING_REPLY,
    TYPING_CHOICE,
    SUPPORTED_MODELS,
)

PINECONE_INDEX_NAME = "telegram-camera-bot-index"


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

    await update.message.reply_html(
        "🔍 <b>검색 중...</b>\n\n",
        reply_markup=reply_markup_models,
    )

    pinecone_db = None

    embeddings_model = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
    try:
        pinecone_api_key = os.environ.get("PINECONE_API_KEY")
        pc = Pinecone(api_key=pinecone_api_key)

        if not pc.has_index(PINECONE_INDEX_NAME):
            pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=1024,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        index = pc.Index(PINECONE_INDEX_NAME)
        pinecone_db = PineconeVectorStore(index=index, embedding=embeddings_model)

        logger.info(f"로컬 PINECONE DB 로드 완료: {PINECONE_INDEX_NAME}")
    except Exception as e:
        logger.error(f"PINECONE DB 로드 실패: {e}")
        await update.message.reply_html(
            "답변 생성에 실패했습니다. 나중에 다시 시도해주세요.",
            reply_markup=reply_markup_models,
        )

    if not pinecone_db:
        await update.message.reply_html(
            "Database 연결에 실패했습니다. 나중에 다시 시도해주세요.",
            reply_markup=reply_markup_models,
        )
        return TYPING_CHOICE

    retriever = pinecone_db.as_retriever(
        search_kwargs={"k": 1, "filter": {"model": model}}
    )

    llm = ChatGroq(
        model="gemma2-9b-it",
        temperature=0.2,
        max_tokens=None,
        timeout=None,
        max_retries=2,
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

    prompt = PromptTemplate.from_template(
        """당신은 카메라 매뉴얼 전문가입니다. 
        주어진 컨텍스트를 바탕으로 사용자의 질문에 정확하고 도움이 되는 답변을 제공해주세요.
        
        컨텍스트: {context}
        
        질문: {question}
        
        답변:"""
    )

    chain = (
        {"context": lambda _: result, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    answer = chain.invoke(query)

    help_text = (
        f"🔍 {model}: {query}\n\n"
        "🔹 <b>검색 결과</b>:\n"
        f"{answer}\n\n"
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

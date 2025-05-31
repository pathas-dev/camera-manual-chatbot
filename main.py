import os
import asyncio
import tempfile
from contextlib import asynccontextmanager
from typing import Optional
import uuid

import faiss
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
)
import uvicorn
from telegram import Update
from telegram.ext import Application

# 봇 설정 모듈 import
from bot_config import BOT_TOKEN, logger
from bot_setup import create_bot_application

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_ollama import OllamaEmbeddings

# 전역 변수
telegram_app: Optional[Application] = None
bot_task: Optional[asyncio.Task] = None
faiss_db: Optional[FAISS] = None
FAISS_INDEX_PATH = "faiss_ai_sample_index"


async def start_telegram_bot() -> None:
    """텔레그램 봇을 백그라운드에서 폴링 방식으로 시작"""
    global telegram_app

    if not BOT_TOKEN:
        logger.error("BOT_TOKEN이 설정되지 않았습니다.")
        return

    logger.info("🤖 텔레그램 봇 백그라운드 시작 (폴링 모드)")

    # 봇 애플리케이션 생성
    telegram_app = create_bot_application()

    # 봇 초기화 및 시작
    await telegram_app.initialize()
    await telegram_app.start()

    try:
        # 수동 폴링 방식으로 변경
        logger.info("폴링 시작...")
        offset = 0

        while True:
            try:
                # 업데이트 가져오기
                updates = await telegram_app.bot.get_updates(
                    offset=offset, timeout=10, allowed_updates=Update.ALL_TYPES
                )

                # 업데이트 처리
                for update in updates:
                    await telegram_app.process_update(update)
                    offset = update.update_id + 1

                # 잠시 대기
                await asyncio.sleep(1)

            except Exception as poll_error:
                logger.error(f"폴링 중 오류: {poll_error}")
                await asyncio.sleep(5)  # 오류 시 5초 대기 후 재시도

    except Exception as e:
        print(e)
        logger.error(f"봇 실행 중 오류: {e}")
        raise
    finally:
        logger.info("봇 함수 종료 중...")
        # lifespan에서 처리하므로 여기서는 로그만 남김


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 앱의 시작과 종료 시 실행되는 컨텍스트 매니저"""
    global bot_task, telegram_app

    # 시작 시 텔레그램 봇을 백그라운드 태스크로 실행
    logger.info("FastAPI 서버 및 텔레그램 봇 시작 중...")
    bot_task = asyncio.create_task(start_telegram_bot())

    # 봇이 시작될 시간을 줌
    await asyncio.sleep(3)
    logger.info("FastAPI 서버 시작 완료")

    yield

    # 종료 시 정리
    logger.info("서버 종료 중...")

    # 봇 먼저 정리
    if telegram_app:
        try:
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("텔레그램 봇 정리 완료")
        except Exception as e:
            logger.error(f"봇 정리 중 오류: {e}")

    # 태스크 취소
    if bot_task and not bot_task.done():
        bot_task.cancel()
        try:
            await bot_task
        except asyncio.CancelledError:
            logger.info("봇 태스크 취소 완료")
        except Exception as e:
            logger.error(f"태스크 취소 중 오류: {e}")

    logger.info("서버 종료 완료")


# FastAPI 앱 생성
app = FastAPI(
    title="Camera Manual Bot API",
    description="카메라 매뉴얼 텔레그램 봇 웹 API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "Camera Manual Bot API",
        "status": "running",
        "mode": "polling",
        "bot_info": "Telegram bot for camera manuals",
    }


@app.get("/bot/status")
async def bot_status():
    """봇 상태 확인 엔드포인트"""
    global telegram_app, bot_task

    bot_running = telegram_app is not None and telegram_app.running
    task_running = bot_task is not None and not bot_task.done()

    return {
        "bot_initialized": telegram_app is not None,
        "bot_running": bot_running,
        "task_running": task_running,
        "mode": "polling",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    global telegram_app, bot_task

    bot_healthy = telegram_app is not None and telegram_app.running
    task_healthy = bot_task is not None and not bot_task.done()

    return {
        "status": "healthy" if bot_healthy and task_healthy else "unhealthy",
        "bot_status": "running" if bot_healthy else "not_running",
        "task_status": "running" if task_healthy else "not_running",
    }


@app.post("/pdf/upload")
async def upload_pdf(
    file: UploadFile = File(...), model: str = Query(..., description="PDF 파일의 이름")
):
    """PDF 파일 업로드 및 FAISS DB에 저장"""
    if not file.filename or not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    try:
        global faiss_db

        embeddings_ollama = OllamaEmbeddings(model="bge-m3")
        try:
            local_faiss = FAISS.load_local(
                FAISS_INDEX_PATH,
                embeddings_ollama,
                allow_dangerous_deserialization=True,
            )

            faiss_db = local_faiss
            logger.info(f"로컬 FAISS DB 로드 완료: {FAISS_INDEX_PATH}")
        except Exception as e:
            dim = 1024  # 임베딩 차원
            faiss_index = faiss.IndexFlatL2(dim)

            # FAISS 벡터 저장소 생성
            faiss_db = FAISS(
                embedding_function=embeddings_ollama,
                index=faiss_index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )

        saved_docs = faiss_db.similarity_search(
            model,
            k=1,
            filter={"$and": [{"model": model}, {"source": file.filename}]},
        )

        if saved_docs:
            logger.info(
                f"이미 저장된 PDF: {file.filename}, 이름: {model}, "
                f"저장된 문서 개수: {len(saved_docs)}"
            )
            return JSONResponse(
                status_code=200,
                content={
                    "message": "이미 저장된 PDF입니다.",
                    "filename": file.filename,
                    "name": model,
                },
            )

        # 임시 파일에 업로드된 PDF 저장
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name

        loader = PyPDFLoader(tmp_file_path)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,  # 토큰 수를 기준으로 분할
            separators=["\n\n", "\n", " ", ""],  # 구분자 - 재귀적으로 순차적으로 적용
        )
        texts = text_splitter.split_documents(documents)
        doc_ids = [str(uuid.uuid4()) for _ in range(len(texts))]

        for i, text in enumerate(texts):
            text.metadata["model"] = model
            text.metadata["source"] = file.filename
            text.metadata["page_no"] = i + 1

        added_doc_ids = faiss_db.add_documents(
            documents=texts,  # 문서 리스트
            doc_ids=doc_ids,  # 문서 id 리스트
        )

        faiss_db.save_local(FAISS_INDEX_PATH)

        logger.info(
            f"PDF 업로드 완료: {file.filename}, 이름: {model}, FAISS DB 저장 개수: {len(added_doc_ids)}"
        )

        return JSONResponse(
            status_code=200,
            content={
                "message": "PDF 업로드 및 처리 완료",
                "filename": file.filename,
                "name": model,
            },
        )

    except Exception as e:
        logger.error(f"PDF 업로드 실패: {e}")
        raise HTTPException(
            status_code=500, detail=f"PDF 처리 중 오류가 발생했습니다: {str(e)}"
        )


def main() -> None:
    """메인 함수 - FastAPI 서버와 텔레그램 봇 통합 실행"""
    logger.info("🚀 카메라 매뉴얼 봇 서버 시작...")
    logger.info("모드: FastAPI + 백그라운드 폴링")

    # 개발 환경 설정
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() == "true"

    logger.info(f"서버 주소: http://{host}:{port}")
    logger.info(f"API 문서: http://{host}:{port}/docs")

    uvicorn.run("main:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    main()

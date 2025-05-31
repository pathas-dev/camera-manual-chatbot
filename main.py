import os
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI
import uvicorn
from telegram import Update
from telegram.ext import Application

# 봇 설정 모듈 import
from bot_config import BOT_TOKEN, logger
from bot_setup import create_bot_application

# 전역 변수
telegram_app: Optional[Application] = None
bot_task: Optional[asyncio.Task] = None


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

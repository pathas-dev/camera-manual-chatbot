from telegram import Update

from bot_config import logger, BOT_TOKEN
from bot_setup import create_bot_application


def run_telegram_bot() -> None:
    """텔레그램 봇을 롱 폴링 방식으로 실행"""
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN이 설정되지 않았습니다. .env 파일을 확인하세요.")
        return

    logger.info("🤖 카메라 매뉴얼 봇 시작 (롱 폴링 모드)")
    logger.info("봇이 메시지를 기다리고 있습니다...")
    logger.info("종료하려면 Ctrl+C를 누르세요")

    # 봇 애플리케이션 생성 및 핸들러 등록
    application = create_bot_application()

    try:
        # 롱 폴링으로 봇 실행
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            poll_interval=1.0,  # 1초마다 폴링
            timeout=10,  # 타임아웃 10초
        )

    except KeyboardInterrupt:
        logger.info("사용자가 봇을 종료했습니다.")
    except Exception as e:
        logger.error(f"봇 실행 중 오류 발생: {e}")
        raise
    finally:
        logger.info("🤖 봇 종료 완료")


def main() -> None:
    """메인 함수 - 롱 폴링 방식으로 봇 실행"""
    run_telegram_bot()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("프로그램 종료")

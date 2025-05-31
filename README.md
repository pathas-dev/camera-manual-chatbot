# Camera Manual Bot

FastAPI와 python-telegram-bot을 사용한 카메라 매뉴얼 텔레그램 봇입니다.

## 기능

- 텔레그램 봇을 통한 메시지 주고받기
- FastAPI 웹 서버와 통합
- 웹훅 및 롱 폴링 지원
- 기본 명령어 처리 (/start, /help)

## 설정

1. `.env` 파일에서 `BOT_TOKEN`을 실제 봇 토큰으로 변경하세요.
2. BotFather(@BotFather)에서 새 봇을 생성하고 토큰을 받으세요.

## 실행 방법

### 방법 1: FastAPI + 웹훅 (프로덕션용)

```bash
# 의존성 설치
uv sync

# FastAPI 서버 실행
uv run python main.py
```

서버가 http://127.0.0.1:8000 에서 실행됩니다.

### 방법 2: 롱 폴링 (개발용)

```bash
# 롱 폴링 방식으로 봇 실행
uv run python bot_polling.py
```

### 방법 3: uvicorn 직접 실행

```bash
# uvicorn으로 직접 실행
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

## API 엔드포인트

- `GET /` - 루트 엔드포인트
- `POST /webhook` - 텔레그램 웹훅 엔드포인트
- `GET /health` - 헬스 체크

## 웹훅 설정 (선택사항)

ngrok을 사용하여 로컬 개발 시 웹훅을 테스트할 수 있습니다:

```bash
# ngrok 설치 후 실행
ngrok http 8000

# .env 파일에 ngrok URL 추가
WEBHOOK_URL=https://your-ngrok-url.ngrok.io
```

## 봇 명령어

- `/start` - 봇 시작 및 환영 메시지
- `/help` - 도움말 보기
- 일반 텍스트 - 카메라 관련 질문

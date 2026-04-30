# XRPL DEX API

XRPL 내장 DEX를 활용한 토큰 스왑 API 서버입니다. FastAPI와 xrpl-py를 사용하여 구현되었습니다.

## 🚀 기능

- **📖 오더북 조회**: XRPL DEX의 매수/매도 호가 확인
- **💱 토큰 스왑**: XRP, USD 등의 토큰 교환
- **💰 스왑 견적**: 실제 스왑 전 예상 금액 조회 (수수료 포함)
- **🔐 API 인증**: X-API-Key 기반 인증
- **📊 사용량 제한**: 월 100건 사용량 제한

## 🛠️ 기술 스택

- **FastAPI**: 웹 프레임워크
- **xrpl-py**: XRPL 라이브러리  
- **aiosqlite**: 비동기 SQLite 데이터베이스
- **Uvicorn**: ASGI 서버
- **WebSocket**: XRPL 테스트넷 연결

## 📋 시작하기

### 1. 사전 요구사항

- Python 3.8 이상
- pip

### 2. 설치

```bash
# 저장소 복사
git clone <repository-url>
cd XRPL_DEX/XRPL_DEX

# 가상 환경 생성 (권장)
python -m venv venv

# 가상 환경 활성화
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 설정합니다.

```bash
cp .env.example .env
```

`.env` 파일에 다음 값을 설정합니다:

```env
# XRPL 테스트넷 노드
XRPL_NODE=wss://s.altnet.rippletest.net:51233

# 발신 주소 (테스트넷 주소)
SENDER_ADDRESS=rYourAddressHere

# 시크릿 키 (테스트넷 시크릿)
SENDER_SECRET=sYourSecretHere

# 수수료 수신 계정
FEE_ACCOUNT=rFeeAccountHere

# DEX 수수료율 (0.3%)
DEX_FEE_RATE=0.003

# API 서버 설정
HOST=0.0.0.0
PORT=8000

# 데이터베이스 (사용량 제한 추적용)
DB_PATH=./usage.db

# API 인증 키 (콤마로 구분)
API_KEYS=test-api-key-1,demo-key-2
```

### 4. XRPL 테스트넷 주소 생성

[XRPL 지갑 생성기](https://xrpl.org/xrp-testnet-faucet.html)에서 테스트넷 주소와 시크릿 키를 생성할 수 있습니다.

### 5. 서버 실행

```bash
# 개발 모드 (자동 재시작)
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는
python app/main.py
```

서버가 시작되면 `http://localhost:8000`에서 접속할 수 있습니다.

## 📡 API 사용법

### 기본 설정

모든 요청은 헤더에 API 키를 포함해야 합니다:

```
X-API-Key: your-api-key
```

### API 엔드포인트

#### 1. 오더북 조회

XRPL DEX의 매수/매도 호가를 조회합니다.

```http
GET /dex/orderbook?base=XRP&quote=USD&limit=20
```

**파라미터:**
- `base`: 기본 통화 (예: XRP, USD)
- `quote`: 상대 통화 (예: XRP, USD)
- `limit`: 반환할 호가 수 (기본값: 20, 최대: 100)

**응답 예시:**
```json
{
  "base": "XRP",
  "quote": "USD",
  "bids": [
    {
      "price": "1.0025",
      "amount": "1000",
      "account": "rAddress1",
      "sequence": 123
    }
  ],
  "asks": [
    {
      "price": "1.0030",
      "amount": "500",
      "account": "rAddress2",
      "sequence": 456
    }
  ],
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl 예시:**
```bash
curl -X GET "http://localhost:8000/dex/orderbook?base=XRP&quote=USD&limit=5" \
  -H "X-API-Key: test-api-key-1"
```

#### 2. 스왑 견적 조회

실제 스왑 전 예상 금액을 조회합니다.

```http
GET /dex/quote?from_currency=XRP&to_currency=USD&amount=100
```

**파라미터:**
- `from_currency`: 출금 통화
- `to_currency`: 입금 통화
- `amount`: 조회 금액

**응답 예시:**
```json
{
  "from_currency": "XRP",
  "to_currency": "USD",
  "from_amount": "100",
  "to_amount": "99.700000",
  "fee": "0.300000",
  "fee_rate": "0.003",
  "estimated_amount": "99.400000",
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl 예시:**
```bash
curl -X GET "http://localhost:8000/dex/quote?from_currency=XRP&to_currency=USD&amount=100" \
  -H "X-API-Key: test-api-key-1"
```

#### 3. 토큰 스왑 실행

XRPL DEX에서 토큰 스왑을 실행합니다. (현재 데모 모드)

```http
POST /dex/swap
Content-Type: application/json
X-API-Key: your-api-key

{
  "from_currency": "XRP",
  "to_currency": "USD",
  "amount": "100"
}
```

**요청 바디:**
- `from_currency`: 출금 통화
- `to_currency`: 입금 통화  
- `amount`: 스왑 금액

**응답 예시:**
```json
{
  "success": true,
  "tx_hash": "demo_tx_1234567890",  # 데모 트랜잭션 해시
  "from_currency": "XRP",
  "to_currency": "USD",
  "from_amount": "100",
  "to_amount": "99.700000",
  "fee": "0.300000",
  "fee_rate": "0.003",
  "error": null,
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl 예시:**
```bash
curl -X POST "http://localhost:8000/dex/swap" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: test-api-key-1" \
  -d '{
    "from_currency": "XRP",
    "to_currency": "USD", 
    "amount": "50"
  }'
```

#### 4. 지원 토큰 목록 조회

지원하는 토큰 목록을 반환합니다.

```http
GET /dex/tokens
```

**응답 예시:**
```json
{
  "tokens": [
    {
      "currency": "XRP",
      "issuer": null,
      "name": "XRP",
      "decimals": 6
    },
    {
      "currency": "USD",
      "issuer": "rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg",
      "name": "USD (Bitstamp)",
      "decimals": 6
    }
  ],
  "count": 2,
  "timestamp": "2026-04-30T12:00:00"
}
```

**curl 예시:**
```bash
curl -X GET "http://localhost:8000/dex/tokens"
```

#### 5. API 사용량 조회

현재 API 키의 사용량 통계를 조회합니다.

```http
GET /dex/usage
X-API-Key: your-api-key
```

**응답 예시:**
```json
{
  "this_month": 45,
  "last_month": 120,
  "total": 165,
  "monthly_limit": 100,
  "remaining": 55
}
```

## 💰 수수료 정책

- **기본 수수료율**: 0.3% (DEX_FEE_RATE)
- 수수료는 자동으로 스왑 금액에서 차감됩니다
- 수수료는 FEE_ACCOUNT로 전송됩니다 (향후 구현 예정)

## 🎯 지원 토큰

현재 **테스트넷**에서 다음 토큰을 지원합니다:

- **XRP**: 네이티브 토큰
- **USD**: Bitstamp 발행 USD (rvYAfWj5gh67QVQisdnQzVQZ75Y2uTxgg)

## 🛣️ 개발 환경

### 프로젝트 구조

```
XRPL_DEX/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI 애플리케이션
│   ├── models.py         # Pydantic 데이터 모델
│   ├── dex_client.py     # XRPL DEX 클라이언트
│   ├── auth.py           # API 인증 미들웨어
│   └── *.py              # 기타 헬퍼 파일
├── requirements.txt
├── .env.example
├── .env                  # 환경변수 (git에 포함하지 않음)
└── README.md
```

### API 문서

서버 실행 후 다음 URL에서 API 문서를 확인할 수 있습니다:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## 🔐 보안 권장사항

1. **API 키 보안**: API 키를 절대 코드에 포함하거나 공개하지 마세요
2. **HTTPS 사용**: 프로덕션에서는 HTTPS를 사용하세요
3. **환경변수 관리**: `.env` 파일을 `.gitignore`에 추가하세요
4. **CORS 설정**: 프로덕션에서는 구체 origins로 제한하세요
5. **사용량 모니터링**: 정기적으로 사용량을 확인하고 제한을 조정하세요

## 🗺️ 로드맵

### 단계 1: 메인넷 배포
- 현재 **테스트넷**에서 운영 중
- 프로덕션 환경 변수로 메인넷 전환
- 실제 트랜잭션 제출 구현

### 단계 2: RLUSD 통합
- **RLUSD (리버리 USD)** 지원
- official USDC와 다른 스테이블코인 통화 추가
- 멀티-콜래티럴 스왑 기능

### 단계 3: 실제 스왑 구현
- 현재 **데모 모드** (`demo_tx_*` 해시)
- 실제 OfferCreate 트랜잭션 제출
- 트랜잭션 상태 추적
- 자동 재시도 로직

### 단계 4: 고급 기능
- 리미트 오더 (Limit Order) 지원
- 부분 체결 스왑
- 슬리피지지 유동성
- 가스 최적화

## ⚠️ 현재 제한사항

- **테스트넷 전용**: 현재 XRPL 테스트넷에서만 작동
- **데모 모드**: 스왑 기능은 데모 트랜잭션 해시 반환
- **수수료 처리**: 현재는 수수료 차감만 처리, 실제 전송 미구현
- **오더북**: 테스트넷 특성상 오더북이 비어있을 수 있음

## 📝 변경사항

### v1.0.0 (2026-04-30)
- 초기 릴리스
- 오더북 조회, 스왑, 견적 조회 기능 구현
- API 인증 및 사용량 제한 기능 추가
- WebSocket 기반 XRPL 연결
- XRP/USD 페어 지원 (Bitstamp)
- 한국어 문서화

## 📄 라이선스

MIT License

## 🆘 지원

문제가 있으면 Issue를 생성하거나 관리자에게 문의하세요.

---

**⚡ 트레이딩 & 스왑 플랫폼에서의 안전한 투자를 위험 관리하세요!**
